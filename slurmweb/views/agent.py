# Copyright (c) 2023 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from functools import wraps
from typing import Any, Callable, Iterable, Tuple, Union
import logging
from datetime import datetime, timezone

from flask import Response, current_app, jsonify, abort, request, stream_with_context
from rfl.web.tokens import _get_token_user, check_jwt
from rfl.authentication.user import AnonymousUser

from ..ai.service import AIProviderValidationError, AIRequestError
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
from ..permission_rules import access_control_catalog, permission_rules_to_legacy_actions


logger = logging.getLogger(__name__)


def _positive_int_query_arg(name: str, default: int) -> int:
    value = request.args.get(name, default)
    try:
        return max(int(value), 1)
    except (TypeError, ValueError):
        return default


def _parse_iso_datetime_query_arg(name: str):
    value = request.args.get(name)
    if value in (None, ""):
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as err:
        raise ValueError(f"{name} must be a valid ISO 8601 datetime") from err
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _parse_metrics_window_query_args():
    start_time = _parse_iso_datetime_query_arg("start")
    end_time = _parse_iso_datetime_query_arg("end")
    if start_time is None and end_time is None:
        return None, None
    if start_time is None or end_time is None:
        raise ValueError("start and end must both be provided")
    if start_time >= end_time:
        raise ValueError("start must be earlier than end")
    return start_time, end_time


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
            "rules": set(),
            "sources": {
                "policy": {
                    "roles": set(roles),
                    "actions": set(actions),
                    "rules": set(),
                },
                "custom": {
                    "roles": set(),
                    "actions": set(),
                },
                "merged": {
                    "roles": set(roles),
                    "actions": set(actions),
                    "rules": set(),
                },
            },
        }
    return {
        "roles": _sorted_strings(merged["roles"]),
        "actions": _sorted_strings(merged["actions"]),
        "rules": _sorted_strings(merged.get("rules", [])),
        "sources": {
            "policy": {
                "roles": _sorted_strings(merged["sources"]["policy"]["roles"]),
                "actions": _sorted_strings(merged["sources"]["policy"]["actions"]),
                "rules": _sorted_strings(merged["sources"]["policy"].get("rules", [])),
            },
            "custom": {
                "roles": _sorted_strings(merged["sources"]["custom"]["roles"]),
                "actions": _sorted_strings(merged["sources"]["custom"]["actions"]),
                "rules": _sorted_strings(merged["sources"]["custom"].get("rules", [])),
            },
            "merged": {
                "roles": _sorted_strings(merged["sources"]["merged"]["roles"]),
                "actions": _sorted_strings(merged["sources"]["merged"]["actions"]),
                "rules": _sorted_strings(merged["sources"]["merged"].get("rules", [])),
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
    actions = payload.get("actions") or []
    if not isinstance(actions, list):
        abort(400, "Role actions must be a list")
    actions = _sorted_strings(actions)
    permissions = payload.get("permissions") or []
    if not isinstance(permissions, list):
        abort(400, "Role permissions must be a list")
    permissions = current_app.policy.normalize_rules(
        list(permissions) + current_app.policy.action_rules(actions)
    )
    invalid_actions = sorted(set(actions) - current_app.policy.definition_actions)
    if invalid_actions:
        abort(400, f"Unknown role actions: {', '.join(invalid_actions)}")
    if not actions:
        actions = permission_rules_to_legacy_actions(
            permissions,
            current_app.policy.legacy_permission_map,
        )
    return {
        "name": name,
        "description": payload.get("description"),
        "actions": actions,
        "permissions": permissions,
    }


def _require_ai():
    if not getattr(current_app, "ai_enabled", False) or current_app.ai_service is None:
        error = "AI assistant is disabled"
        logger.warning(error)
        abort(501, error)


def _ai_model_payload():
    payload = request.get_json(silent=True) or {}
    try:
        return payload, current_app.ai_service
    except Exception:
        abort(500, "AI service is unavailable")


def _resolved_scope(scope: Union[str, Callable[..., str]], *args, **kwargs) -> str:
    if callable(scope):
        return scope(*args, **kwargs)
    return scope


def _user_login() -> Union[str, None]:
    return getattr(request.user, "login", None)


def _allowed_permission(resource: str, operation: str, scope: str = "*") -> bool:
    return current_app.policy.allowed_user_permission(
        request.user,
        resource,
        operation,
        scope,
    )


def _require_permission_scope(resource: str, operation: str) -> str:
    if _allowed_permission(resource, operation, "*"):
        return "*"
    if _allowed_permission(resource, operation, "self"):
        login = _user_login()
        if not login:
            abort(403, "Access not permitted")
        return "self"
    abort(403, "Access not permitted")


def _filter_jobs_for_owner(jobs: Iterable[dict], owner: str) -> list:
    return [job for job in jobs if _job_owner(job) == owner]


def _job_owner(job_data: dict) -> Union[str, None]:
    association = job_data.get("association")
    if isinstance(association, dict):
        owner = association.get("user")
        if owner:
            return owner
    for key in ("user_name", "user"):
        owner = job_data.get(key)
        if owner:
            return owner
    return None


def _job_payload() -> dict:
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        abort(400, "Request body must be a JSON object")
    return payload


def _ensure_write_supported(operation: str):
    _, _, api_version = current_app.slurmrestd.discover()
    if current_app.slurmrestd.supports_write_operations():
        return api_version
    response = {
        "code": "unsupported_on_version",
        "supported": False,
        "operation": operation,
        "target": None,
        "api_version": api_version,
        "warnings": [],
        "errors": [f"{operation} is unsupported on slurmrestd API {api_version}"],
        "result": None,
    }
    return jsonify(response), 501


def _operation_response(operation: str, target, response: dict, status: int = 200):
    api_version = current_app.slurmrestd.api_version or current_app.slurmrestd.discover()[2]
    result = {
        key: value
        for key, value in response.items()
        if key not in {"meta", "warnings", "errors"}
    }
    return jsonify(
        {
            "supported": True,
            "operation": operation,
            "target": target,
            "api_version": api_version,
            "warnings": response.get("warnings", []),
            "errors": response.get("errors", []),
            "result": result,
        }
    ), status


def _authorize_job_owner(job_id: int, operation: str) -> dict:
    scope = _require_permission_scope("jobs", operation)
    job_data = current_app.slurmrestd.job(job_id)
    if scope == "*":
        return job_data
    owner = _job_owner(job_data)
    if owner is None or owner != _user_login():
        abort(403, "Access not permitted")
    return job_data


def permission_required(*requirements: Tuple[str, str, str], legacy_action: str = None):
    def decorator(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            _get_token_user(request)
            user = request.user
            if user is None:
                logger.warning("Unauthorized access without bearer token")
                abort(403, "Not allowed to access endpoint without bearer token")
            if user.is_anonymous() and current_app.policy.access_control_available:
                logger.warning("Unauthorized anonymous access to %s", func.__name__)
                abort(
                    403,
                    (
                        f"Anonymous role is not allowed to perform action {legacy_action}"
                        if legacy_action
                        else "Access not permitted"
                    ),
                )
            for resource, operation, scope in requirements:
                if current_app.policy.allowed_user_permission(
                    user,
                    resource,
                    operation,
                    _resolved_scope(scope, *args, **kwargs),
                ):
                    return func(*args, **kwargs)
            logger.warning(
                "Unauthorized access from user %s to %s (%s)",
                user,
                func.__name__,
                requirements,
            )
            if user.is_anonymous() and legacy_action:
                abort(403, f"Anonymous role is not allowed to perform action {legacy_action}")
            abort(403, "Access not permitted")

        return wrapped

    return decorator


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
        "node_metrics": current_app.node_metrics_db is not None,
        "ai": (
            current_app.ai_service.capabilities()
            if getattr(current_app, "ai_enabled", False) and current_app.ai_service is not None
            else {
                "enabled": False,
                "configurable": False,
                "streaming": False,
                "persistence": False,
                "available_models_count": 0,
                "default_model_id": None,
                "providers": [],
                "tool_mode": "mixed",
            }
        ),
        "capabilities": {
            "job_history": current_app.jobs_store is not None,
            "ldap_cache": current_app.users_store is not None,
            "access_control": bool(getattr(current_app, "access_control_enabled", False)),
            "node_metrics": current_app.node_metrics_db is not None,
            "ai": (
                current_app.ai_service.capabilities()
                if getattr(current_app, "ai_enabled", False) and current_app.ai_service is not None
                else {
                    "enabled": False,
                    "configurable": False,
                    "streaming": False,
                    "persistence": False,
                    "available_models_count": 0,
                    "default_model_id": None,
                    "providers": [],
                    "tool_mode": "mixed",
                }
            ),
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

    @wraps(func)
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
@permission_required(("analysis", "view", "*"), legacy_action="view-stats")
def analysis_ping():
    return jsonify({"pings": current_app.slurmrestd.ping_data()})


@handle_slurmrestd_errors
@permission_required(("analysis", "view", "*"), legacy_action="view-stats")
def analysis_diag():
    return jsonify({"statistics": current_app.slurmrestd.diag()})

@handle_slurmrestd_errors
def slurmrest(method: str, *args: Tuple[Any, ...]):
    return getattr(current_app.slurmrestd, method)(*args)


@permission_required(
    ("dashboard", "view", "*"),
    ("analysis", "view", "*"),
    legacy_action="view-stats",
)
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


@handle_slurmrestd_errors
@permission_required(
    ("jobs", "view", "*"),
    ("jobs", "view", "self"),
    legacy_action="view-jobs",
)
def jobs():
    scope = _require_permission_scope("jobs", "view")
    node = request.args.get("node")
    if node:
        result = slurmrest("jobs_by_node", node)
    elif scope == "self":
        result = current_app.slurmrestd.jobs(query={"user": _user_login()})
    else:
        result = slurmrest("jobs")
    if scope == "self":
        result = _filter_jobs_for_owner(result, _user_login())
    return jsonify(result)


@handle_slurmrestd_errors
@permission_required(
    ("jobs", "view", "*"),
    ("jobs", "view", "self"),
    legacy_action="view-jobs",
)
def job(job: int):
    result = _authorize_job_owner(job, "view")
    return jsonify(result)


@handle_slurmrestd_errors
@permission_required(
    ("jobs", "edit", "*"),
    ("jobs", "edit", "self"),
    legacy_action="view-jobs",
)
def job_submit():
    supported = _ensure_write_supported("jobs.submit")
    if not isinstance(supported, str):
        return supported
    response = current_app.slurmrestd.job_submit(_job_payload())
    return _operation_response("jobs.submit", None, response, status=201)


@handle_slurmrestd_errors
@permission_required(
    ("jobs", "edit", "*"),
    ("jobs", "edit", "self"),
    legacy_action="view-jobs",
)
def job_update(job: int):
    supported = _ensure_write_supported("jobs.update")
    if not isinstance(supported, str):
        return supported
    _authorize_job_owner(job, "edit")
    response = current_app.slurmrestd.job_update(job, _job_payload())
    return _operation_response("jobs.update", {"job_id": job}, response)


@handle_slurmrestd_errors
@permission_required(
    ("jobs", "delete", "*"),
    ("jobs", "delete", "self"),
    legacy_action="view-jobs",
)
def job_cancel(job: int):
    supported = _ensure_write_supported("jobs.cancel")
    if not isinstance(supported, str):
        return supported
    _authorize_job_owner(job, "delete")
    response = current_app.slurmrestd.job_cancel(job, request.get_json(silent=True))
    return _operation_response("jobs.cancel", {"job_id": job}, response)


@permission_required(("resources", "view", "*"), legacy_action="view-nodes")
def nodes():
    return jsonify(slurmrest("nodes"))


@permission_required(("resources", "view", "*"), legacy_action="view-nodes")
def node(name: str):
    return jsonify(slurmrest("node", name))


@handle_slurmrestd_errors
@permission_required(("resources", "edit", "*"), legacy_action="view-nodes")
def node_update(name: str):
    supported = _ensure_write_supported("resources.node.update")
    if not isinstance(supported, str):
        return supported
    response = current_app.slurmrestd.node_update(name, _job_payload())
    return _operation_response("resources.node.update", {"node": name}, response)


@handle_slurmrestd_errors
@permission_required(("resources", "delete", "*"), legacy_action="view-nodes")
def node_delete(name: str):
    supported = _ensure_write_supported("resources.node.delete")
    if not isinstance(supported, str):
        return supported
    response = current_app.slurmrestd.node_delete(name)
    return _operation_response("resources.node.delete", {"node": name}, response)


@permission_required(
    ("jobs/filter-partitions", "view", "*"),
    ("resources/filter-partitions", "view", "*"),
    legacy_action="view-partitions",
)
def partitions():
    return jsonify(slurmrest("partitions"))


@permission_required(
    ("qos", "view", "*"),
    ("jobs/filter-qos", "view", "*"),
    legacy_action="view-qos",
)
def qos():
    return jsonify(slurmrest("qos"))


@permission_required(("reservations", "view", "*"), legacy_action="view-reservations")
def reservations():
    return jsonify(slurmrest("reservations"))


@handle_slurmrestd_errors
@permission_required(("reservations", "edit", "*"), legacy_action="view-reservations")
def reservation_create():
    supported = _ensure_write_supported("reservations.create")
    if not isinstance(supported, str):
        return supported
    response = current_app.slurmrestd.reservation_create(_job_payload())
    return _operation_response("reservations.create", None, response, status=201)


@handle_slurmrestd_errors
@permission_required(("reservations", "edit", "*"), legacy_action="view-reservations")
def reservation_update(name: str):
    supported = _ensure_write_supported("reservations.update")
    if not isinstance(supported, str):
        return supported
    response = current_app.slurmrestd.reservation_update(name, _job_payload())
    return _operation_response("reservations.update", {"reservation": name}, response)


@handle_slurmrestd_errors
@permission_required(
    ("reservations", "delete", "*"),
    legacy_action="view-reservations",
)
def reservation_delete(name: str):
    supported = _ensure_write_supported("reservations.delete")
    if not isinstance(supported, str):
        return supported
    response = current_app.slurmrestd.reservation_delete(name)
    return _operation_response("reservations.delete", {"reservation": name}, response)


@permission_required(
    ("accounts", "view", "*"),
    ("jobs/filter-accounts", "view", "*"),
    legacy_action="view-accounts",
)
def accounts():
    return jsonify(slurmrest("accounts"))


@handle_slurmrestd_errors
@permission_required(("accounts", "view", "*"), legacy_action="associations-view")
def account(name: str):
    return jsonify(current_app.slurmrestd.account(name))


@handle_slurmrestd_errors
@permission_required(("accounts", "edit", "*"), legacy_action="associations-view")
def accounts_update():
    supported = _ensure_write_supported("accounts.update")
    if not isinstance(supported, str):
        return supported
    response = current_app.slurmrestd.accounts_update(_job_payload())
    return _operation_response("accounts.update", None, response)


@handle_slurmrestd_errors
@permission_required(("accounts", "delete", "*"), legacy_action="associations-view")
def account_delete(name: str):
    supported = _ensure_write_supported("accounts.delete")
    if not isinstance(supported, str):
        return supported
    response = current_app.slurmrestd.account_delete(name)
    return _operation_response("accounts.delete", {"account": name}, response)


@permission_required(
    ("accounts", "view", "*"),
    ("user/profile", "view", "*"),
    legacy_action="associations-view",
)
def associations():
    return jsonify(slurmrest("associations"))


@handle_slurmrestd_errors
@permission_required(("users-admin", "view", "*"), legacy_action="associations-view")
def users():
    return jsonify(current_app.slurmrestd.users())


@handle_slurmrestd_errors
@permission_required(("users-admin", "view", "*"), legacy_action="associations-view")
def user(name: str):
    return jsonify(current_app.slurmrestd.user(name))


@handle_slurmrestd_errors
@permission_required(("users-admin", "edit", "*"), legacy_action="associations-view")
def users_update():
    supported = _ensure_write_supported("users.update")
    if not isinstance(supported, str):
        return supported
    response = current_app.slurmrestd.users_update(_job_payload())
    return _operation_response("users.update", None, response)


@handle_slurmrestd_errors
@permission_required(("users-admin", "delete", "*"), legacy_action="associations-view")
def user_delete(name: str):
    supported = _ensure_write_supported("users.delete")
    if not isinstance(supported, str):
        return supported
    response = current_app.slurmrestd.user_delete(name)
    return _operation_response("users.delete", {"user": name}, response)


@handle_slurmrestd_errors
@permission_required(("qos", "edit", "*"), legacy_action="view-qos")
def qos_update():
    supported = _ensure_write_supported("qos.update")
    if not isinstance(supported, str):
        return supported
    response = current_app.slurmrestd.qos_update(_job_payload())
    return _operation_response("qos.update", None, response)


@handle_slurmrestd_errors
@permission_required(("qos", "delete", "*"), legacy_action="view-qos")
def qos_delete(name: str):
    supported = _ensure_write_supported("qos.delete")
    if not isinstance(supported, str):
        return supported
    response = current_app.slurmrestd.qos_delete(name)
    return _operation_response("qos.delete", {"qos": name}, response)


@handle_slurmrestd_errors
@permission_required(("accounts", "edit", "*"), legacy_action="associations-view")
def associations_update():
    supported = _ensure_write_supported("accounts.associations.update")
    if not isinstance(supported, str):
        return supported
    response = current_app.slurmrestd.associations_update(_job_payload())
    return _operation_response("accounts.associations.update", None, response)


@handle_slurmrestd_errors
@permission_required(("accounts", "delete", "*"), legacy_action="associations-view")
def associations_delete():
    supported = _ensure_write_supported("accounts.associations.delete")
    if not isinstance(supported, str):
        return supported
    response = current_app.slurmrestd.associations_delete(_job_payload())
    return _operation_response("accounts.associations.delete", None, response)


@permission_required(("admin/cache", "view", "*"), legacy_action="cache-view")
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


@permission_required(("admin/cache", "edit", "*"), legacy_action="cache-reset")
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
    metrics_permissions = {
        "nodes": ("resources", "view", "*"),
        "cores": ("resources", "view", "*"),
        "gpus": ("resources", "view", "*"),
        "memory": ("resources", "view", "*"),
        "jobs": ("jobs", "view", "*"),
        "users": ("jobs", "view", "*"),
        "cache": ("admin/cache", "view", "*"),
    }

    # Check metric is supported or send HTTP/404
    if metric not in metrics_permissions.keys():
        abort(404, f"Metric {metric} not found")

    if metric == "users":
        if not getattr(current_app, "user_metrics_enabled", False):
            error = "User metrics is disabled"
            logger.warning(error)
            abort(501, error)

    # Check permission to request metric or send HTTP/403
    resource, operation, scope = metrics_permissions[metric]
    if not current_app.policy.allowed_user_permission(
        request.user,
        resource,
        operation,
        scope,
    ):
        logger.warning(
            "Unauthorized access from user %s to %s metric (missing permission on %s:%s:%s)",
            request.user,
            metric,
            resource,
            operation,
            scope,
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


@permission_required(("jobs-history", "view", "*"), legacy_action="view-history-jobs")
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


@permission_required(("jobs-history", "view", "*"), legacy_action="view-history-jobs")
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


@permission_required(("admin/ldap-cache", "view", "*"), legacy_action="cache-view")
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


@permission_required(("admin/access-control", "view", "*"))
def access_catalog():
    _require_access_control()
    return jsonify(access_control_catalog())


@permission_required(("admin/access-control", "view", "*"))
def access_roles():
    _require_access_control()
    try:
        return jsonify({"items": current_app.access_control_store.list_roles()})
    except Exception as err:
        logger.warning("Unable to list access control roles: %s", err)
        abort(500, str(err))


@permission_required(("admin/access-control", "edit", "*"))
def create_access_role():
    _require_access_control()
    role = _role_payload()
    try:
        created = current_app.access_control_store.create_role(
            role["name"],
            role["description"],
            role["actions"],
            role["permissions"],
        )
        return jsonify(created), 201
    except ValueError as err:
        abort(400, str(err))
    except Exception as err:
        logger.warning("Unable to create access control role: %s", err)
        abort(500, str(err))


@permission_required(("admin/access-control", "edit", "*"))
def update_access_role(role_id: int):
    _require_access_control()
    role = _role_payload()
    try:
        updated = current_app.access_control_store.update_role(
            role_id,
            role["name"],
            role["description"],
            role["actions"],
            role["permissions"],
        )
    except ValueError as err:
        abort(400, str(err))
    except Exception as err:
        logger.warning("Unable to update access control role %s: %s", role_id, err)
        abort(500, str(err))

    if updated is None:
        abort(404, f"Access control role {role_id} not found")
    return jsonify(updated)


@permission_required(("admin/access-control", "delete", "*"))
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


@permission_required(("admin/access-control", "view", "*"))
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


@permission_required(("admin/access-control", "view", "*"))
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


@permission_required(("admin/access-control", "edit", "*"))
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


@permission_required(("admin/ai", "view", "*"))
def ai_configs():
    _require_ai()
    return jsonify({"items": current_app.ai_service.list_configs()})


@permission_required(("admin/ai", "edit", "*"))
def create_ai_config():
    _require_ai()
    payload, _ = _ai_model_payload()
    try:
        created = current_app.ai_service.create_model_config(payload)
        return jsonify(created), 201
    except AIProviderValidationError as err:
        abort(400, str(err))
    except Exception as err:
        logger.warning("Unable to create AI model config: %s", err)
        abort(500, str(err))


@permission_required(("admin/ai", "edit", "*"))
def update_ai_config(config_id: int):
    _require_ai()
    payload, _ = _ai_model_payload()
    try:
        updated = current_app.ai_service.update_model_config(config_id, payload)
    except AIProviderValidationError as err:
        abort(400, str(err))
    except Exception as err:
        logger.warning("Unable to update AI model config %s: %s", config_id, err)
        abort(500, str(err))
    if updated is None:
        abort(404, f"AI model config {config_id} not found")
    return jsonify(updated)


@permission_required(("admin/ai", "delete", "*"))
def delete_ai_config(config_id: int):
    _require_ai()
    try:
        deleted = current_app.ai_service.delete_model_config(config_id)
    except Exception as err:
        logger.warning("Unable to delete AI model config %s: %s", config_id, err)
        abort(500, str(err))
    if not deleted:
        abort(404, f"AI model config {config_id} not found")
    return jsonify({"result": "AI model config deleted"})


@permission_required(("admin/ai", "edit", "*"))
def validate_ai_config(config_id: int):
    _require_ai()
    try:
        result = current_app.ai_service.validate_model_config(config_id)
    except AIProviderValidationError as err:
        abort(400, str(err))
    except Exception as err:
        logger.warning("Unable to validate AI model config %s: %s", config_id, err)
        abort(500, str(err))
    if result is None:
        abort(404, f"AI model config {config_id} not found")
    return jsonify(result)


@permission_required(("ai", "view", "*"))
def ai_chat_stream():
    _require_ai()
    payload = request.get_json(silent=True) or {}
    try:
        generator = current_app.ai_service.stream_chat(request.user, payload)
    except (AIRequestError, AIProviderValidationError) as err:
        abort(400, str(err))
    except Exception as err:
        logger.warning("Unable to start AI chat stream: %s", err)
        abort(500, str(err))
    return Response(
        stream_with_context(generator()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@permission_required(("ai", "view", "*"))
def ai_conversations():
    _require_ai()
    try:
        return jsonify(current_app.ai_service.list_conversations(request.user))
    except Exception as err:
        logger.warning("Unable to list AI conversations for %s: %s", request.user, err)
        abort(500, str(err))


@permission_required(("ai", "view", "*"))
def ai_conversation_detail(conversation_id: int):
    _require_ai()
    try:
        details = current_app.ai_service.get_conversation_detail(
            request.user,
            conversation_id,
        )
    except Exception as err:
        logger.warning("Unable to query AI conversation %s: %s", conversation_id, err)
        abort(500, str(err))
    if details is None:
        abort(404, f"AI conversation {conversation_id} not found")
    return jsonify(details)


@permission_required(
    (
        "user/analysis",
        "view",
        lambda username: "self" if getattr(request.user, "login", None) == username else "*",
    ),
    ("jobs", "view", "*"),
    legacy_action="view-jobs",
)
def user_metrics_history(username: str):
    if not getattr(current_app, "user_metrics_enabled", False) or current_app.user_metrics_store is None:
        error = "User metrics is disabled"
        logger.warning(error)
        abort(501, error)
    try:
        start_time, end_time = _parse_metrics_window_query_args()
        return jsonify(
            current_app.user_metrics_store.user_metrics_history(
                username,
                request.args.get("range", "hour"),
                start_time=start_time,
                end_time=end_time,
            )
        )
    except ValueError as err:
        logger.warning("Invalid user metrics history query for %s: %s", username, err)
        abort(400, str(err))
    except Exception as err:
        logger.warning("Unable to query user metrics history for %s: %s", username, err)
        abort(500, str(err))


@permission_required(
    (
        "user/analysis",
        "view",
        lambda username: "self" if getattr(request.user, "login", None) == username else "*",
    ),
    ("jobs", "view", "*"),
    legacy_action="view-jobs",
)
def user_tools_analysis(username: str):
    if not getattr(current_app, "user_metrics_enabled", False) or current_app.user_metrics_store is None:
        error = "User metrics is disabled"
        logger.warning(error)
        abort(501, error)
    try:
        start_time, end_time = _parse_metrics_window_query_args()
        if start_time is None or end_time is None:
            raise ValueError("start and end must both be provided")
        return jsonify(
            current_app.user_metrics_store.user_tool_analysis(
                username,
                start_time=start_time,
                end_time=end_time,
            )
        )
    except ValueError as err:
        logger.warning("Invalid user tools analysis query for %s: %s", username, err)
        abort(400, str(err))
    except Exception as err:
        logger.warning("Unable to query user tools analysis for %s: %s", username, err)
        abort(500, str(err))


@permission_required(("resources", "view", "*"), legacy_action="view-nodes")
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


@permission_required(("resources", "view", "*"), legacy_action="view-nodes")
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
