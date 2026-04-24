# Copyright (c) 2023 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from typing import Any, Tuple
import logging

from flask import Response, current_app, jsonify, abort, request
from rfl.web.tokens import rbac_action, check_jwt

from ..version import get_version
from ..errors import SlurmwebCacheError, SlurmwebMetricsDBError
from ..persistence.jobs_store import normalize_history_exit_code

from ..slurmrestd.errors import (
    SlurmrestdNotFoundError,
    SlurmrestdInvalidResponseError,
    SlurmrestConnectionError,
    SlurmrestdAuthenticationError,
    SlurmrestdInternalError,
)


logger = logging.getLogger(__name__)


def _positive_int_query_arg(name: str, default: int) -> int:
    value = request.args.get(name, default)
    try:
        return max(int(value), 1)
    except (TypeError, ValueError):
        return default


def _normalize_job_history_record(record: dict) -> dict:
    data = dict(record)
    data["exit_code"] = normalize_history_exit_code(data.get("exit_code"))
    return data


def _sorted_strings(values) -> list:
    return sorted(str(value) for value in values if value not in (None, ""))


def _permission_payload(user) -> dict:
    if hasattr(current_app.policy, "roles_actions_sources"):
        merged = current_app.policy.roles_actions_sources(user)
    else:
        roles, actions = current_app.policy.roles_actions(user)
        merged = {
            "roles": set(roles),
            "actions": set(actions),
            "sources": {
                "policy": {
                    "roles": set(roles),
                    "actions": set(actions),
                },
                "custom": {
                    "roles": set(),
                    "actions": set(),
                },
            },
        }
    return {
        "roles": _sorted_strings(merged["roles"]),
        "actions": _sorted_strings(merged["actions"]),
        "sources": {
            "policy": {
                "roles": _sorted_strings(merged["sources"]["policy"]["roles"]),
                "actions": _sorted_strings(merged["sources"]["policy"]["actions"]),
            },
            "custom": {
                "roles": _sorted_strings(merged["sources"]["custom"]["roles"]),
                "actions": _sorted_strings(merged["sources"]["custom"]["actions"]),
            },
        },
    }


def _require_access_control():
    if not getattr(current_app, "access_control_enabled", False) or current_app.access_control_store is None:
        error = "Access control is disabled"
        logger.warning(error)
        abort(501, error)


def _access_page_args():
    page = _positive_int_query_arg("page", 1)
    page_size = min(_positive_int_query_arg("page_size", 50), 200)
    username = request.args.get("username")
    return username, page, page_size


def _role_payload():
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()
    if not name:
        abort(400, "Role name is required")
    actions = payload.get("actions")
    if not isinstance(actions, list):
        abort(400, "Role actions must be a list")
    actions = _sorted_strings(actions)
    invalid_actions = sorted(set(actions) - current_app.policy.definition_actions)
    if invalid_actions:
        abort(400, f"Unknown role actions: {', '.join(invalid_actions)}")
    return {
        "name": name,
        "description": payload.get("description"),
        "actions": actions,
    }


def racksdb_get_version():
    """Get RacksDB version if available, or return 'N/A' if not installed."""
    try:
        from racksdb.version import get_version

        return get_version()
    except ModuleNotFoundError:
        return "N/A (not installed)"


def version():
    return Response(f"Slurm-web agent v{get_version()}\n", mimetype="text/plain")


def info():
    user_metrics_enabled = bool(getattr(current_app, "user_metrics_enabled", False))
    user_metrics_capabilities = {
        "enabled": user_metrics_enabled,
        "history_api": user_metrics_enabled,
        "summary_api": user_metrics_enabled,
    }
    data = {
        "cluster": current_app.settings.service.cluster,
        "metrics": current_app.settings.metrics.enabled,
        "cache": current_app.settings.cache.enabled,
        "database": current_app.users_store is not None,
        "user_metrics": user_metrics_enabled,
        "racksdb": {
            "enabled": current_app.settings.racksdb.enabled,
            "infrastructure": current_app.settings.racksdb.infrastructure,
            "version": racksdb_get_version(),
        },
        "version": get_version(),
        "persistence": current_app.jobs_store is not None,
        "access_control": bool(getattr(current_app, "access_control_enabled", False)),
        "node_metrics": current_app.settings.node_metrics.enabled,
        "capabilities": {
            "job_history": current_app.jobs_store is not None,
            "ldap_cache": current_app.users_store is not None,
            "access_control": bool(getattr(current_app, "access_control_enabled", False)),
            "node_metrics": current_app.settings.node_metrics.enabled,
            "user_metrics": user_metrics_capabilities,
            "user_analytics": {
                "enabled": user_metrics_enabled,
                "prometheus_user_metrics": user_metrics_enabled,
                "user_activity_api": user_metrics_enabled,
            },
        },
    }
    return jsonify(data)


@check_jwt
def permissions():
    return jsonify(_permission_payload(request.user))


def handle_slurmrestd_errors(func):
    """Wrapper function to handle slurmrestd-related exceptions consistently.

    Handles all slurmrestd exceptions and converts them to appropriate HTTP
    error responses. Also handles SlurmwebCacheError for cache-related issues.
    """

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SlurmrestdNotFoundError as err:
            msg = f"URL not found on slurmrestd: {err}"
            logger.error(msg)
            abort(404, msg)
        except SlurmrestdInvalidResponseError as err:
            msg = f"Invalid response from slurmrestd: {err}"
            logger.error(msg)
            abort(500, msg)
        except SlurmrestConnectionError as err:
            msg = f"Unable to connect to slurmrestd: {err}"
            logger.error(msg)
            abort(500, msg)
        except SlurmrestdAuthenticationError as err:
            msg = f"Authentication error on slurmrestd: {err}"
            logger.error(msg)
            abort(401, msg)
        except SlurmrestdInternalError as err:
            msg = f"slurmrestd error: {err.description} ({err.source})"
            if err.error != -1:
                msg += f" [{err.message}/{err.error}]"
            logger.error(msg)
            abort(500, msg)
        except SlurmwebCacheError as err:
            msg = f"Cache error: {str(err)}"
            logger.error(msg)
            abort(500, msg)

    return wrapper


@handle_slurmrestd_errors
def ping():
    """Ping endpoint that discovers slurmrestd API version and returns it along with
    Slurm version information."""
    # Discover and save both API version and Slurm version
    _, slurm_version, api_version = current_app.slurmrestd.discover()

    return jsonify(
        {
            "versions": {
                "slurm": slurm_version,
                "api": api_version,
            },
        }
    )


@handle_slurmrestd_errors
def slurmrest(method: str, *args: Tuple[Any, ...]):
    return getattr(current_app.slurmrestd, method)(*args)


@rbac_action("view-stats")
def stats():
    total = 0
    running = 0

    for job in slurmrest("jobs"):
        total += 1
        if "RUNNING" in job["job_state"]:
            running += 1

    nodes = 0
    cores = 0
    memory = 0
    memory_allocated = 0
    gpus = 0
    nodes_getter = getattr(current_app.slurmrestd, "nodes_unfiltered", None)
    nodes_data = nodes_getter() if callable(nodes_getter) else slurmrest("nodes")
    for node in nodes_data:
        nodes += 1
        cores += node["cpus"]
        node_memory = max(node.get("real_memory", 0), 0)
        memory += node_memory
        node_memory_allocated = max(
            current_app.slurmrestd._optional_number_value(
                node.get("alloc_memory"),
                0,
            ),
            0,
        )
        node_memory_allocated = min(node_memory, node_memory_allocated)
        memory_allocated += node_memory_allocated
        gpus += current_app.slurmrestd.node_gres_extract_gpus(node["gres"])
    memory_available = max(memory - memory_allocated, 0)
    return jsonify(
        {
            "resources": {
                "nodes": nodes,
                "cores": cores,
                "memory": memory,
                "memory_allocated": memory_allocated,
                "memory_available": memory_available,
                "gpus": gpus,
            },
            "jobs": {"running": running, "total": total},
        }
    )


@rbac_action("view-jobs")
def jobs():
    node = request.args.get("node")
    if node:
        result = slurmrest("jobs_by_node", node)
    else:
        result = slurmrest("jobs")
    return jsonify(result)


@rbac_action("view-jobs")
def job(job: int):
    return jsonify(slurmrest("job", job))


@rbac_action("view-nodes")
def nodes():
    return jsonify(slurmrest("nodes"))


@rbac_action("view-nodes")
def node(name: str):
    return jsonify(slurmrest("node", name))


@rbac_action("view-partitions")
def partitions():
    return jsonify(slurmrest("partitions"))


@rbac_action("view-qos")
def qos():
    return jsonify(slurmrest("qos"))


@rbac_action("view-reservations")
def reservations():
    return jsonify(slurmrest("reservations"))


@rbac_action("view-accounts")
def accounts():
    return jsonify(slurmrest("accounts"))


@rbac_action("associations-view")
def associations():
    return jsonify(slurmrest("associations"))


@rbac_action("cache-view")
def cache_stats():
    if current_app.cache is None:
        error = "Cache service is disabled, unable to query cache statistics"
        logger.warning(error)
        abort(501, error)
    (cache_hits, cache_misses, total_hits, total_misses) = current_app.cache.metrics()
    return jsonify(
        {
            "hit": {"keys": cache_hits, "total": total_hits},
            "miss": {"keys": cache_misses, "total": total_misses},
        }
    )


@rbac_action("cache-reset")
def cache_reset():
    if current_app.cache is None:
        error = "Cache service is disabled, unable to reset cache"
        logger.warning(error)
        abort(501, error)

    # Reset values in caching service
    current_app.cache.reset()

    # Return fresh values right after reset
    (cache_hits, cache_misses, total_hits, total_misses) = current_app.cache.metrics()
    return jsonify(
        {
            "hit": {"keys": cache_hits, "total": total_hits},
            "miss": {"keys": cache_misses, "total": total_misses},
        }
    )


@check_jwt
def metrics(metric):
    if current_app.metrics_db is None:
        error = "Metrics are disabled, unable to query values"
        logger.warning(error)
        abort(501, error)

    # Dictionnary of metrics and required policy actions associations
    metrics_policy_actions = {
        "nodes": "view-nodes",
        "cores": "view-nodes",
        "gpus": "view-nodes",
        "memory": "view-nodes",
        "jobs": "view-jobs",
        "users": "view-jobs",
        "cache": "cache-view",
    }

    # Check metric is supported or send HTTP/404
    if metric not in metrics_policy_actions.keys():
        abort(404, f"Metric {metric} not found")

    if metric == "users":
        if not getattr(current_app, "user_metrics_enabled", False):
            error = "User metrics is disabled"
            logger.warning(error)
            abort(501, error)

    # Check permission to request metric or send HTTP/403
    action = metrics_policy_actions[metric]
    if not current_app.policy.allowed_user_action(request.user, action):
        logger.warning(
            "Unauthorized access from user %s to %s metric (missing permission on %s)",
            request.user,
            metric,
            action,
        )
        abort(403, f"Access to {metric} metric not permitted")

    # Send metrics from DB

    try:
        return jsonify(
            current_app.metrics_db.request(metric, request.args.get("range", "hour"))
        )
    except SlurmwebMetricsDBError as err:
        logger.warning(str(err))
        abort(500, str(err))


@rbac_action("view-history-jobs")
def jobs_history():
    """Return paginated job history from PostgreSQL."""
    if current_app.jobs_store is None:
        error = "Job history persistence is disabled"
        logger.warning(error)
        abort(501, error)
    filters = {
        "start": request.args.get("start"),
        "end": request.args.get("end"),
        "keyword": request.args.get("keyword"),
        "user": request.args.get("user"),
        "account": request.args.get("account"),
        "partition": request.args.get("partition"),
        "qos": request.args.get("qos"),
        "state": request.args.get("state"),
        "job_id": request.args.get("job_id"),
        "page": request.args.get("page", 1),
        "page_size": request.args.get("page_size", 100),
        "sort": request.args.get("sort"),
        "order": request.args.get("order"),
    }
    try:
        result = current_app.jobs_store.query(filters)
        result["jobs"] = [
            _normalize_job_history_record(record) for record in result.get("jobs", [])
        ]
        return jsonify(result)
    except Exception as err:
        logger.error("Job history query error: %s", err)
        abort(500, str(err))


@rbac_action("view-history-jobs")
def job_history_detail(record_id: int):
    """Return a single job history record by its DB primary key."""
    if current_app.jobs_store is None:
        error = "Job history persistence is disabled"
        logger.warning(error)
        abort(501, error)
    try:
        record = current_app.jobs_store.get_by_id(record_id)
    except Exception as err:
        logger.error("Job history detail query error: %s", err)
        abort(500, str(err))
    if record is None:
        abort(404, f"Job history record {record_id} not found")
    return jsonify(_normalize_job_history_record(record))


@check_jwt
def cache_authenticated_user():
    """Cache the authenticated user details in the local users table."""
    if current_app.users_store is None:
        error = "User cache persistence is disabled"
        logger.warning(error)
        abort(501, error)

    payload = request.get_json(silent=True) or {}
    username = payload.get("username") or request.user.login
    fullname = payload.get("fullname")
    if "fullname" not in payload:
        fullname = getattr(request.user, "fullname", None)
        if fullname is None and hasattr(request.user, "_details"):
            fullname = request.user._details.get("fullname")
    groups = payload.get("groups")
    if groups is None:
        groups = getattr(request.user, "groups", [])

    try:
        policy_roles, policy_actions = current_app.policy.file_roles_actions(request.user)
        current_app.users_store.upsert_ldap_user(
            username,
            fullname,
            groups,
            policy_roles=_sorted_strings(policy_roles),
            policy_actions=_sorted_strings(policy_actions),
        )
    except Exception as err:
        logger.warning("Unable to cache authenticated user %s: %s", request.user, err)
        abort(500, str(err))

    return jsonify({"result": "User cache updated"})


@rbac_action("cache-view")
def ldap_cache_users():
    """Return cached LDAP users stored in the local database."""
    if current_app.users_store is None:
        error = "User cache persistence is disabled"
        logger.warning(error)
        abort(501, error)

    page = _positive_int_query_arg("page", 1)
    page_size = _positive_int_query_arg("page_size", 50)
    username = request.args.get("username")

    try:
        return jsonify(
            current_app.users_store.list_ldap_users(
                username=username,
                page=page,
                page_size=page_size,
            )
        )
    except Exception as err:
        logger.warning("Unable to list cached LDAP users: %s", err)
        abort(500, str(err))


@rbac_action("roles-view")
def access_roles():
    _require_access_control()
    try:
        return jsonify({"items": current_app.access_control_store.list_roles()})
    except Exception as err:
        logger.warning("Unable to list access control roles: %s", err)
        abort(500, str(err))


@rbac_action("roles-manage")
def create_access_role():
    _require_access_control()
    role = _role_payload()
    try:
        created = current_app.access_control_store.create_role(
            role["name"],
            role["description"],
            role["actions"],
        )
        return jsonify(created), 201
    except ValueError as err:
        abort(400, str(err))
    except Exception as err:
        logger.warning("Unable to create access control role: %s", err)
        abort(500, str(err))


@rbac_action("roles-manage")
def update_access_role(role_id: int):
    _require_access_control()
    role = _role_payload()
    try:
        updated = current_app.access_control_store.update_role(
            role_id,
            role["name"],
            role["description"],
            role["actions"],
        )
    except ValueError as err:
        abort(400, str(err))
    except Exception as err:
        logger.warning("Unable to update access control role %s: %s", role_id, err)
        abort(500, str(err))

    if updated is None:
        abort(404, f"Access control role {role_id} not found")
    return jsonify(updated)


@rbac_action("roles-manage")
def delete_access_role(role_id: int):
    _require_access_control()
    try:
        deleted = current_app.access_control_store.delete_role(role_id)
    except Exception as err:
        logger.warning("Unable to delete access control role %s: %s", role_id, err)
        abort(500, str(err))
    if not deleted:
        abort(404, f"Access control role {role_id} not found")
    return jsonify({"result": "Role deleted"})


@rbac_action("roles-view")
def access_users():
    _require_access_control()
    username, page, page_size = _access_page_args()
    try:
        return jsonify(
            current_app.access_control_store.list_users(
                username=username,
                page=page,
                page_size=page_size,
            )
        )
    except Exception as err:
        logger.warning("Unable to list access control users: %s", err)
        abort(500, str(err))


@rbac_action("roles-view")
def access_user_roles(username: str):
    _require_access_control()
    try:
        details = current_app.access_control_store.get_user_roles(username)
    except Exception as err:
        logger.warning("Unable to query access control roles for %s: %s", username, err)
        abort(500, str(err))
    if details is None:
        abort(404, f"User {username} not found")
    return jsonify(details)


@rbac_action("roles-manage")
def update_access_user_roles(username: str):
    _require_access_control()
    payload = request.get_json(silent=True) or {}
    role_ids = payload.get("role_ids")
    if not isinstance(role_ids, list):
        abort(400, "role_ids must be a list")
    try:
        role_ids = [int(role_id) for role_id in role_ids]
    except (TypeError, ValueError):
        abort(400, "role_ids must contain integers")
    try:
        details = current_app.access_control_store.set_user_roles(username, role_ids)
    except ValueError as err:
        abort(400, str(err))
    except Exception as err:
        logger.warning("Unable to update access control roles for %s: %s", username, err)
        abort(500, str(err))
    return jsonify(details)


@rbac_action("view-jobs")
def user_metrics_history(username: str):
    if not getattr(current_app, "user_metrics_enabled", False) or current_app.user_metrics_store is None:
        error = "User metrics is disabled"
        logger.warning(error)
        abort(501, error)
    try:
        return jsonify(
            current_app.user_metrics_store.user_metrics_history(
                username, request.args.get("range", "hour")
            )
        )
    except ValueError as err:
        logger.warning("Unsupported user metrics history range for %s: %s", username, err)
        abort(400, str(err))
    except Exception as err:
        logger.warning("Unable to query user metrics history for %s: %s", username, err)
        abort(500, str(err))


@rbac_action("view-jobs")
def user_activity_summary(username: str):
    if not getattr(current_app, "user_metrics_enabled", False) or current_app.user_metrics_store is None:
        error = "User metrics is disabled"
        logger.warning(error)
        abort(501, error)
    try:
        return jsonify(current_app.user_metrics_store.user_activity_summary(username))
    except Exception as err:
        logger.warning("Unable to query user activity summary for %s: %s", username, err)
        abort(500, str(err))


@rbac_action("view-nodes")
def node_metrics(name: str):
    """Return real-time resource metrics for a node from Prometheus."""
    if current_app.node_metrics_db is None:
        error = "Node real-time metrics is disabled"
        logger.warning(error)
        abort(501, error)
    try:
        result = current_app.node_metrics_db.node_instant_metrics(
            name,
            current_app.settings.node_metrics.node_hostname_label,
        )
        return jsonify(result)
    except SlurmwebMetricsDBError as err:
        logger.warning("Node metrics query error for %s: %s", name, err)
        abort(500, str(err))


@rbac_action("view-nodes")
def node_metrics_history(name: str):
    """Return historical resource metrics for a node from Prometheus."""
    if current_app.node_metrics_db is None:
        error = "Node real-time metrics is disabled"
        logger.warning(error)
        abort(501, error)
    try:
        result = current_app.node_metrics_db.node_history_metrics(
            name,
            request.args.get("range", "hour"),
            current_app.settings.node_metrics.node_hostname_label,
        )
        return jsonify(result)
    except SlurmwebMetricsDBError as err:
        logger.warning("Node metrics history query error for %s: %s", name, err)
        abort(500, str(err))
