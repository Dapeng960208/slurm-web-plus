# Copyright (c) 2023 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from functools import wraps
from typing import Any, Callable, Iterable, Tuple, Union
import inspect
import logging
from datetime import datetime, timezone

from flask import Response, current_app, jsonify, abort, request, stream_with_context
from rfl.web.tokens import _get_token_user, check_jwt
from rfl.authentication.user import AnonymousUser

from ..ai.service import AIProviderValidationError, AIRequestError
from ..version import get_version
from ..errors import SlurmwebCacheError, SlurmwebMetricsDBError
from ..cache import CacheKey
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


def _cache_get_or_put(key: CacheKey, expiration: int, callback: Callable[[], Any]):
    if current_app.cache is None:
        return callback()
    data = current_app.cache.get(key)
    if data is None:
        data = callback()
        current_app.cache.put(key, data, expiration)
        current_app.cache.count_miss(key)
    else:
        current_app.cache.count_hit(key)
    return data


def _query_values(name: str):
    values = []
    for raw in request.args.getlist(name):
        values.extend(item.strip() for item in str(raw).split(",") if item.strip())
    return values


def _jobs_query_args():
    query = {}
    mapping = {
        "users": "users",
        "states": "states",
        "accounts": "accounts",
        "qos": "qos",
        "partitions": "partitions",
    }
    for arg, key in mapping.items():
        values = _query_values(arg)
        if values:
            query[key] = values
    return query


def _number(value, default=0):
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value, default=0):
    try:
        if value in (None, ""):
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_job_history_record(record: dict) -> dict:
    data = dict(record)
    data["exit_code"] = normalize_history_exit_code(data.get("exit_code"))
    return data


def _history_wait_stats(records: list[dict]) -> dict:
    waits = []
    for record in records:
        submit_time = record.get("submit_time")
        start_time = record.get("start_time")
        if submit_time in (None, "") or start_time in (None, ""):
            continue
        try:
            waits.append(max(int(start_time) - int(submit_time), 0))
        except (TypeError, ValueError):
            continue
    waits.sort()
    if not waits:
        return {
            "samples": 0,
            "median_seconds": None,
            "p90_seconds": None,
            "average_seconds": None,
        }
    last_index = len(waits) - 1
    median_index = last_index // 2
    p90_index = min(int(last_index * 0.9), last_index)
    return {
        "samples": len(waits),
        "median_seconds": waits[median_index],
        "p90_seconds": waits[p90_index],
        "average_seconds": round(sum(waits) / len(waits), 1),
    }


def _top_pending_reasons(jobs: list[dict], limit: int = 5) -> list[dict]:
    counts = {}
    pending_total = 0
    for job in jobs:
        states = job.get("job_state") or []
        if isinstance(states, str):
            states = [states]
        if "PENDING" not in states:
            continue
        pending_total += 1
        reason = job.get("state_reason") or "Unknown"
        counts[reason] = counts.get(reason, 0) + 1
    if pending_total == 0:
        return []
    return [
        {
            "reason": reason,
            "count": count,
            "share": round(count / pending_total, 3),
        }
        for reason, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
    ]


def _node_main_state(state) -> str:
    values = state if isinstance(state, list) else [state]
    normalized = {str(value).upper() for value in values if value not in (None, "")}
    if {"DOWN", "DRAIN", "DRAINED", "FAIL", "FAILING"} & normalized:
        return "down"
    if "IDLE" in normalized:
        return "up"
    if {"ALLOCATED", "MIXED"} & normalized:
        return "busy"
    return "unknown"


def _partition_pressure_summary(jobs: list[dict], nodes: list[dict], limit: int = 5) -> list[dict]:
    partitions = {}
    for node in nodes:
        for partition_name in node.get("partitions") or []:
            entry = partitions.setdefault(
                partition_name,
                {
                    "name": partition_name,
                    "pending_jobs": 0,
                    "running_jobs": 0,
                    "pending_cpu": 0,
                    "running_cpu": 0,
                    "schedulable_cpu": 0,
                    "total_cpu": 0,
                    "status": "stable",
                },
            )
            cpus = _safe_int(node.get("cpus"), 0)
            entry["total_cpu"] += cpus
            if _node_main_state(node.get("state")) == "up":
                entry["schedulable_cpu"] += cpus
    for job in jobs:
        partition_name = str(job.get("partition") or "unknown")
        entry = partitions.setdefault(
            partition_name,
            {
                "name": partition_name,
                "pending_jobs": 0,
                "running_jobs": 0,
                "pending_cpu": 0,
                "running_cpu": 0,
                "schedulable_cpu": 0,
                "total_cpu": 0,
                "status": "stable",
            },
        )
        states = job.get("job_state") or []
        if isinstance(states, str):
            states = [states]
        cpus = 0
        job_cpus = job.get("cpus")
        if isinstance(job_cpus, dict) and job_cpus.get("set") and not job_cpus.get("infinite"):
            cpus = _safe_int(job_cpus.get("number"), 0)
        if "PENDING" in states:
            entry["pending_jobs"] += 1
            entry["pending_cpu"] += cpus
        if "RUNNING" in states or "COMPLETING" in states:
            entry["running_jobs"] += 1
            entry["running_cpu"] += cpus
    result = []
    for entry in partitions.values():
        schedulable_cpu = entry["schedulable_cpu"]
        pending_pressure = (entry["pending_cpu"] / schedulable_cpu) if schedulable_cpu else 0
        busy_pressure = (entry["running_cpu"] / schedulable_cpu) if schedulable_cpu else 0
        if entry["pending_jobs"] > 0 and (
            pending_pressure > 0.4 or entry["pending_jobs"] > entry["running_jobs"]
        ):
            entry["status"] = "congested"
        elif busy_pressure > 0.72 or entry["pending_jobs"] > 0:
            entry["status"] = "hot"
        else:
            entry["status"] = "stable"
        result.append(entry)
    result.sort(key=lambda item: (-item["pending_cpu"], -item["pending_jobs"], item["name"]))
    return result[:limit]


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
            "node_hotspots": getattr(current_app, "node_hotspot_store", None) is not None,
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


def _analysis_context_payload():
    jobs = slurmrest("jobs")
    nodes_getter = getattr(current_app.slurmrestd, "nodes_unfiltered", None)
    nodes = nodes_getter() if callable(nodes_getter) else slurmrest("nodes")
    stats_payload = _collect_stats(None)

    availability = {
        "jobs": True,
        "nodes": True,
        "metrics": current_app.metrics_db is not None,
        "job_history": current_app.jobs_store is not None,
        "node_hotspots": getattr(current_app, "node_hotspot_store", None) is not None,
        "analysis_ping": True,
        "analysis_diag": True,
    }
    warnings = []

    jobs_metrics = None
    core_metrics = None
    memory_metrics = None
    gpu_metrics = None
    if current_app.metrics_db is not None:
        try:
            jobs_metrics = current_app.metrics_db.request("jobs", "hour")
            core_metrics = current_app.metrics_db.request("cores", "hour")
            memory_metrics = current_app.metrics_db.request("memory", "hour")
            gpu_metrics = current_app.metrics_db.request("gpus", "hour")
        except Exception as err:
            availability["metrics"] = False
            warnings.append(f"metrics unavailable: {err}")

    history_window = None
    history_records = []
    wait_stats = {
        "samples": 0,
        "median_seconds": None,
        "p90_seconds": None,
        "average_seconds": None,
    }
    if current_app.jobs_store is not None:
        end_time = datetime.now(timezone.utc)
        start_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
        start_time = start_time.replace(day=max(1, start_time.day - 1))
        history_window = {
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
        }
        try:
            query_result = current_app.jobs_store.query(
                {
                    "start": history_window["start"],
                    "end": history_window["end"],
                    "state": "COMPLETED",
                    "sort": "submit_time",
                    "order": "desc",
                    "page": 1,
                    "page_size": 200,
                }
            )
            history_records = [
                _normalize_job_history_record(record) for record in query_result.get("jobs", [])
            ]
            wait_stats = _history_wait_stats(history_records)
        except Exception as err:
            availability["job_history"] = False
            warnings.append(f"job history unavailable: {err}")
    else:
        availability["job_history"] = False

    hotspot_window_start = datetime.now(timezone.utc).timestamp() - 3 * 24 * 60 * 60
    hotspot_window_end = datetime.now(timezone.utc).timestamp()
    hotspot_payload = {"window": None, "events": []}
    hotspot_store = getattr(current_app, "node_hotspot_store", None)
    if hotspot_store is not None:
        try:
            hotspot_result = hotspot_store.cluster_node_hotspots(
                start_time=datetime.fromtimestamp(hotspot_window_start, tz=timezone.utc),
                end_time=datetime.fromtimestamp(hotspot_window_end, tz=timezone.utc),
            )
            hotspot_payload = {
                "window": hotspot_result.get("window"),
                "events": hotspot_result.get("events", [])[:10],
            }
        except Exception as err:
            availability["node_hotspots"] = False
            warnings.append(f"node hotspots unavailable: {err}")
    else:
        availability["node_hotspots"] = False

    ping_cards = [
        {
            "controller": ping.get("hostname") or ping.get("host") or ping.get("name"),
            "mode": ping.get("mode"),
            "latency_ms": ping.get("latency_ms"),
            "status": ping.get("status"),
        }
        for ping in current_app.slurmrestd.ping_data()[:5]
    ]
    diag_statistics = current_app.slurmrestd.diag()
    scheduler_diag = {
        key: diag_statistics.get(key)
        for key in (
            "jobs_submitted",
            "jobs_started",
            "jobs_completed",
            "jobs_canceled",
            "schedule_cycle_last",
            "schedule_cycle_max",
            "schedule_cycle_mean",
            "bf_backfilled_jobs",
            "bf_last_backfilled_jobs",
            "bf_queue_len",
        )
        if key in diag_statistics
    }

    running_jobs = 0
    pending_jobs = 0
    running_cpu = 0
    pending_cpu = 0
    schedulable_nodes = 0
    unavailable_nodes = 0
    total_nodes = len(nodes)
    for node in nodes:
        node_state = _node_main_state(node.get("state"))
        if node_state == "up":
            schedulable_nodes += 1
        elif node_state == "down":
            unavailable_nodes += 1
    for job in jobs:
        states = job.get("job_state") or []
        if isinstance(states, str):
            states = [states]
        job_cpus = job.get("cpus")
        cpus = 0
        if isinstance(job_cpus, dict) and job_cpus.get("set") and not job_cpus.get("infinite"):
            cpus = _safe_int(job_cpus.get("number"), 0)
        if "RUNNING" in states or "COMPLETING" in states:
            running_jobs += 1
            running_cpu += cpus
        if "PENDING" in states:
            pending_jobs += 1
            pending_cpu += cpus

    score = 100
    if pending_jobs > running_jobs and pending_jobs > 0:
        score -= 18
    elif pending_jobs > 0:
        score -= 8
    if wait_stats["median_seconds"] is not None:
        if wait_stats["median_seconds"] >= 3600:
            score -= 16
        elif wait_stats["median_seconds"] >= 1200:
            score -= 8
    if total_nodes > 0 and unavailable_nodes / total_nodes >= 0.15:
        score -= 10
    score = max(0, min(100, score))
    if score >= 85:
        score_label = "efficient"
        score_summary = "Cluster capacity is healthy with low contention."
    elif score >= 70:
        score_label = "stable"
        score_summary = "Cluster is stable but shows moderate scheduling pressure."
    elif score >= 55:
        score_label = "pressured"
        score_summary = "Cluster is under visible pressure from queueing or unavailable capacity."
    else:
        score_label = "constrained"
        score_summary = "Cluster is constrained and likely needs operator attention."

    resources = stats_payload.get("resources", {})
    cpu_total = _safe_int(resources.get("cores"), 0)
    memory_total = _number(resources.get("memory"), 0)
    memory_allocated = _number(resources.get("memory_allocated"), 0)
    cpu_utilization = round((running_cpu / cpu_total), 3) if cpu_total else None
    memory_utilization = round((memory_allocated / memory_total), 3) if memory_total else None
    schedulable_ratio = round((schedulable_nodes / total_nodes), 3) if total_nodes else None

    summary_cards = [
        {
            "id": "cpu_occupancy",
            "label": "CPU occupancy",
            "value": None if cpu_utilization is None else f"{round(cpu_utilization * 100, 1)}%",
            "detail": f"Running CPU {running_cpu} / total CPU {cpu_total}",
            "tone": "warning" if cpu_utilization is not None and cpu_utilization >= 0.8 else "neutral",
        },
        {
            "id": "queue_pressure",
            "label": "Queue pressure",
            "value": "low" if pending_jobs == 0 else f"{round((pending_jobs / max(running_jobs, 1)), 1)}x",
            "detail": f"Pending jobs {pending_jobs}, running jobs {running_jobs}",
            "tone": "danger" if pending_jobs > running_jobs and pending_jobs > 0 else "neutral",
        },
        {
            "id": "wait_sample",
            "label": "Wait sample",
            "value": "--" if wait_stats["median_seconds"] is None else f"{wait_stats['median_seconds']} s",
            "detail": f"Completed job samples {wait_stats['samples']}",
            "tone": "warning" if wait_stats["median_seconds"] is not None and wait_stats["median_seconds"] >= 1200 else "neutral",
        },
        {
            "id": "recovery",
            "label": "Schedulable nodes",
            "value": f"{schedulable_nodes}/{total_nodes}",
            "detail": f"Unavailable nodes {unavailable_nodes}",
            "tone": "warning" if unavailable_nodes > 0 else "success",
        },
    ]
    capacity_metrics = [
        {
            "id": "cpu",
            "label": "CPU",
            "value": cpu_utilization,
            "detail": f"{running_cpu} running CPU / {cpu_total} total CPU",
        },
        {
            "id": "memory",
            "label": "Memory",
            "value": memory_utilization,
            "detail": f"{round(memory_allocated / 1024, 1) if memory_allocated else 0} GB allocated / {round(memory_total / 1024, 1) if memory_total else 0} GB total",
        },
        {
            "id": "nodes",
            "label": "Nodes",
            "value": schedulable_ratio,
            "detail": f"{schedulable_nodes} schedulable / {total_nodes} total nodes",
        },
    ]
    recommendations = []
    if pending_jobs > running_jobs and pending_jobs > 0:
        recommendations.append(
            {
                "id": "queue_backlog",
                "title": "Investigate queue backlog",
                "summary": "Pending demand is higher than active throughput.",
                "evidence": f"Pending jobs {pending_jobs}, running jobs {running_jobs}, pending CPU {pending_cpu}.",
                "tone": "warning",
            }
        )
    if wait_stats["median_seconds"] is not None and wait_stats["median_seconds"] >= 1200:
        recommendations.append(
            {
                "id": "wait_time",
                "title": "Review queue wait time",
                "summary": "Completed jobs show elevated queue delay.",
                "evidence": f"Median wait {wait_stats['median_seconds']} seconds across {wait_stats['samples']} completed jobs.",
                "tone": "warning",
            }
        )
    if unavailable_nodes > 0:
        recommendations.append(
            {
                "id": "node_availability",
                "title": "Recover unavailable nodes",
                "summary": "Part of the cluster is not schedulable.",
                "evidence": f"{unavailable_nodes} of {total_nodes} nodes are unavailable.",
                "tone": "danger",
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window": {
            "metrics_range": "hour",
            "history": history_window,
            "hotspots": {
                "start": datetime.fromtimestamp(hotspot_window_start, tz=timezone.utc).isoformat(),
                "end": datetime.fromtimestamp(hotspot_window_end, tz=timezone.utc).isoformat(),
            },
        },
        "score": score,
        "score_label": score_label,
        "score_summary": score_summary,
        "summary_cards": summary_cards,
        "capacity_metrics": capacity_metrics,
        "wait_stats": wait_stats,
        "top_pending_reasons": _top_pending_reasons(jobs),
        "partition_pressure": _partition_pressure_summary(jobs, nodes),
        "node_hotspots": hotspot_payload,
        "controller_health": ping_cards,
        "scheduler_diag": scheduler_diag,
        "recommendations": recommendations,
        "data_availability": availability,
        "warnings": warnings,
        "evidence": {
            "jobs": {
                "running": stats_payload.get("jobs", {}).get("running", running_jobs),
                "total": stats_payload.get("jobs", {}).get("total", len(jobs)),
                "pending": pending_jobs,
                "running_cpu": running_cpu,
                "pending_cpu": pending_cpu,
            },
            "resources": resources,
            "metrics": {
                "jobs": jobs_metrics,
                "cores": core_metrics,
                "memory": memory_metrics,
                "gpus": gpu_metrics,
            },
        },
    }


@handle_slurmrestd_errors
@permission_required(("analysis", "view", "*"), legacy_action="view-stats")
def analysis_context():
    return jsonify(_analysis_context_payload())


@permission_required(("analysis", "view", "*"), legacy_action="view-stats")
def analysis_node_hotspots():
    if current_app.node_metrics_db is None and getattr(current_app, "node_hotspot_store", None) is None:
        error = "Node metrics is disabled"
        logger.warning(error)
        abort(501, error)
    try:
        start_time, end_time = _parse_metrics_window_query_args()
        if start_time is None or end_time is None:
            raise ValueError("start and end must both be provided")
        key = CacheKey(
            f"analysis-node-hotspots-{start_time.isoformat()}-{end_time.isoformat()}",
            "analysis",
        )

        def collect_hotspots():
            store = getattr(current_app, "node_hotspot_store", None)
            if store is not None:
                return store.cluster_node_hotspots(
                    start_time=start_time,
                    end_time=end_time,
                )
            if current_app.node_metrics_db is None:
                error = "Node hotspot persistence is disabled"
                logger.warning(error)
                abort(501, error)
            error = "Node hotspot persistence is unavailable"
            logger.warning(error)
            abort(501, error)

        result = _cache_get_or_put(
            key, current_app.settings.cache.analysis, collect_hotspots
        )
        return jsonify(result)
    except ValueError as err:
        logger.warning("Invalid node hotspot query: %s", err)
        abort(400, str(err))
    except SlurmwebMetricsDBError as err:
        logger.warning("Unable to query node hotspots: %s", err)
        abort(500, str(err))

@handle_slurmrestd_errors
def slurmrest(method: str, *args: Tuple[Any, ...]):
    return getattr(current_app.slurmrestd, method)(*args)


@permission_required(
    ("dashboard", "view", "*"),
    ("analysis", "view", "*"),
    legacy_action="view-stats",
)
def stats():
    partition = request.args.get("partition")
    query = {"partition": partition} if partition else None

    key = CacheKey(f"stats-partition-{partition}", "stats") if partition else CacheKey("stats")
    return jsonify(
        _cache_get_or_put(
            key,
            current_app.settings.cache.stats,
            lambda: _collect_stats(query),
        )
    )


def _collect_stats(query):
    total = 0
    running = 0

    jobs = (
        current_app.slurmrestd.jobs(query=query)
        if query is not None
        else slurmrest("jobs")
    )
    for job in jobs:
        total += 1
        if "RUNNING" in job["job_state"]:
            running += 1

    nodes = 0
    cores = 0
    memory = 0
    memory_allocated = 0
    gpus = 0
    nodes_getter = getattr(current_app.slurmrestd, "nodes_unfiltered", None)
    if callable(nodes_getter):
        nodes_data = nodes_getter(query=query) if query is not None else nodes_getter()
    else:
        nodes_data = (
            current_app.slurmrestd.nodes(query=query)
            if query is not None
            else slurmrest("nodes")
        )
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
    return {
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
        query = _jobs_query_args()
        result = current_app.slurmrestd.jobs(query=query) if query else slurmrest("jobs")
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
        metric_range = request.args.get("range", "hour")
        partition = request.args.get("partition")
        start_time, end_time = _parse_metrics_window_query_args()
        metrics_request = current_app.metrics_db.request
        request_signature = inspect.signature(metrics_request)
        supports_partition = False
        if partition is not None:
            supports_partition = "partition" in request_signature.parameters or any(
                parameter.kind == inspect.Parameter.VAR_KEYWORD
                for parameter in request_signature.parameters.values()
            )
        kwargs = {}
        if start_time is not None and end_time is not None:
            kwargs["start_time"] = start_time
            kwargs["end_time"] = end_time
        if partition is not None and supports_partition:
            kwargs["partition"] = partition
        return jsonify(metrics_request(metric, metric_range, **kwargs))
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


@permission_required(("admin/ldap-users", "view", "*"), legacy_action="cache-view")
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


@permission_required(("ai", "view", "*"))
def ai_models():
    _require_ai()
    try:
        return jsonify(current_app.ai_service.list_model_summaries())
    except Exception as err:
        logger.warning("Unable to list AI model summaries: %s", err)
        abort(500, str(err))


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


@permission_required(("ai", "view", "*"))
def delete_ai_conversation(conversation_id: int):
    _require_ai()
    try:
        deleted = current_app.ai_service.delete_conversation(request.user, conversation_id)
    except Exception as err:
        logger.warning("Unable to delete AI conversation %s: %s", conversation_id, err)
        abort(500, str(err))
    if not deleted:
        abort(404, f"AI conversation {conversation_id} not found")
    return jsonify({"result": "AI conversation deleted"})


@permission_required(("admin/ai", "view", "*"))
def admin_ai_conversations():
    _require_ai()
    try:
        limit = min(_positive_int_query_arg("limit", 200), 500)
        return jsonify(current_app.ai_service.list_all_conversations(limit=limit))
    except Exception as err:
        logger.warning("Unable to list AI conversation audit records: %s", err)
        abort(500, str(err))


@permission_required(("admin/ai", "view", "*"))
def admin_ai_conversation_detail(conversation_id: int):
    _require_ai()
    try:
        details = current_app.ai_service.get_any_conversation_detail(conversation_id)
    except Exception as err:
        logger.warning("Unable to audit AI conversation %s: %s", conversation_id, err)
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
        start_time, end_time = _parse_metrics_window_query_args()
        result = current_app.node_metrics_db.node_history_metrics(
            name,
            request.args.get("range", "hour"),
            current_app.settings.node_metrics.node_hostname_label,
            start_time=start_time,
            end_time=end_time,
        )
        return jsonify(result)
    except ValueError as err:
        logger.warning("Invalid node metrics history query for %s: %s", name, err)
        return jsonify(
            {
                "code": 400,
                "description": str(err),
                "name": "Bad Request",
            }
        ), 400
    except SlurmwebMetricsDBError as err:
        logger.warning("Node metrics history query error for %s: %s", name, err)
        abort(500, str(err))
