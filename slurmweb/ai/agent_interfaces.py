from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, Optional

from ..errors import SlurmwebCacheError, SlurmwebMetricsDBError
from ..persistence.jobs_store import normalize_history_exit_code
from ..slurmrestd.errors import (
    SlurmrestConnectionError,
    SlurmrestdAuthenticationError,
    SlurmrestdInternalError,
    SlurmrestdInvalidResponseError,
    SlurmrestdNotFoundError,
)


def _truncate_text(value, limit=1200):
    text = json.dumps(value, default=str, ensure_ascii=True)
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


class AIAgentInterfaceError(RuntimeError):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


@dataclass(frozen=True)
class AIAgentInterfaceResult:
    interface_key: str
    status_code: int
    payload: object
    summary: Optional[str]
    error: Optional[str] = None


@dataclass(frozen=True)
class AIAgentInterfaceDefinition:
    key: str
    method: str
    description: str
    arguments_description: str
    write: bool
    handler: Callable[[object, object, dict], AIAgentInterfaceResult]


def _normalize_job_history_record(record: dict) -> dict:
    data = dict(record)
    data["exit_code"] = normalize_history_exit_code(data.get("exit_code"))
    return data


def _job_owner(job_data: dict) -> Optional[str]:
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


def _filter_jobs_for_owner(jobs: Iterable[dict], owner: str) -> list:
    return [job for job in jobs if _job_owner(job) == owner]


class AIAgentInterfaceRegistry:
    def __init__(self, app):
        self.app = app
        self._definitions: Dict[str, AIAgentInterfaceDefinition] = {}
        self._register_definitions()

    def _register_definitions(self):
        for definition in (
            AIAgentInterfaceDefinition(
                key="stats",
                method="GET",
                description="Get overall cluster resource usage and live job totals.",
                arguments_description="No arguments.",
                write=False,
                handler=self._stats,
            ),
            AIAgentInterfaceDefinition(
                key="jobs",
                method="GET",
                description="List live jobs, optionally filtered by node name.",
                arguments_description="Optional: node, limit.",
                write=False,
                handler=self._jobs,
            ),
            AIAgentInterfaceDefinition(
                key="job",
                method="GET",
                description="Get one live job by numeric job_id.",
                arguments_description="Required: job_id.",
                write=False,
                handler=self._job,
            ),
            AIAgentInterfaceDefinition(
                key="jobs/history",
                method="GET",
                description="Query persisted job history with filters such as job_id, user, account, state, keyword, and pagination.",
                arguments_description="Optional: job_id, user, account, partition, qos, state, keyword, start, end, sort, order, page, page_size, limit.",
                write=False,
                handler=self._jobs_history,
            ),
            AIAgentInterfaceDefinition(
                key="jobs/history/detail",
                method="GET",
                description="Get one persisted job history record by database record_id.",
                arguments_description="Required: record_id.",
                write=False,
                handler=self._job_history_detail,
            ),
            AIAgentInterfaceDefinition(
                key="nodes",
                method="GET",
                description="List compute nodes with current state and resources.",
                arguments_description="Optional: limit.",
                write=False,
                handler=self._nodes,
            ),
            AIAgentInterfaceDefinition(
                key="node",
                method="GET",
                description="Get one compute node by name.",
                arguments_description="Required: name.",
                write=False,
                handler=self._node,
            ),
            AIAgentInterfaceDefinition(
                key="node/metrics",
                method="GET",
                description="Get real-time metrics for a node.",
                arguments_description="Required: name.",
                write=False,
                handler=self._node_metrics,
            ),
            AIAgentInterfaceDefinition(
                key="node/metrics/history",
                method="GET",
                description="Get historical metrics for a node.",
                arguments_description="Required: name. Optional: range=hour|day|week.",
                write=False,
                handler=self._node_metrics_history,
            ),
            AIAgentInterfaceDefinition(
                key="partitions",
                method="GET",
                description="List cluster partitions.",
                arguments_description="No arguments.",
                write=False,
                handler=self._partitions,
            ),
            AIAgentInterfaceDefinition(
                key="qos",
                method="GET",
                description="List configured QoS records.",
                arguments_description="No arguments.",
                write=False,
                handler=self._qos,
            ),
            AIAgentInterfaceDefinition(
                key="reservations",
                method="GET",
                description="List active reservations.",
                arguments_description="No arguments.",
                write=False,
                handler=self._reservations,
            ),
            AIAgentInterfaceDefinition(
                key="accounts",
                method="GET",
                description="List cluster accounts.",
                arguments_description="No arguments.",
                write=False,
                handler=self._accounts,
            ),
            AIAgentInterfaceDefinition(
                key="account",
                method="GET",
                description="Get one account by name.",
                arguments_description="Required: name.",
                write=False,
                handler=self._account,
            ),
            AIAgentInterfaceDefinition(
                key="associations",
                method="GET",
                description="List account-user associations and limits.",
                arguments_description="Optional: limit.",
                write=False,
                handler=self._associations,
            ),
            AIAgentInterfaceDefinition(
                key="users",
                method="GET",
                description="List SlurmDB users.",
                arguments_description="Optional: limit.",
                write=False,
                handler=self._users,
            ),
            AIAgentInterfaceDefinition(
                key="user",
                method="GET",
                description="Get one SlurmDB user by name.",
                arguments_description="Required: name.",
                write=False,
                handler=self._user,
            ),
            AIAgentInterfaceDefinition(
                key="user/metrics/history",
                method="GET",
                description="Get submission and completion history for one user.",
                arguments_description="Required: username. Optional: range=hour|day|week.",
                write=False,
                handler=self._user_metrics_history,
            ),
            AIAgentInterfaceDefinition(
                key="user/activity/summary",
                method="GET",
                description="Get aggregated user activity summary, including tool usage and recent behavior.",
                arguments_description="Required: username.",
                write=False,
                handler=self._user_activity_summary,
            ),
            AIAgentInterfaceDefinition(
                key="job/submit",
                method="POST",
                description="Submit a new job with the same payload accepted by the agent job submit interface.",
                arguments_description="Required: payload.",
                write=True,
                handler=self._job_submit,
            ),
            AIAgentInterfaceDefinition(
                key="job/update",
                method="POST",
                description="Update one job by numeric job_id using the agent update payload.",
                arguments_description="Required: job_id, payload.",
                write=True,
                handler=self._job_update,
            ),
            AIAgentInterfaceDefinition(
                key="job/cancel",
                method="DELETE",
                description="Cancel one job by numeric job_id.",
                arguments_description="Required: job_id. Optional: payload.",
                write=True,
                handler=self._job_cancel,
            ),
            AIAgentInterfaceDefinition(
                key="node/update",
                method="POST",
                description="Update one node by name using the agent update payload.",
                arguments_description="Required: name, payload.",
                write=True,
                handler=self._node_update,
            ),
            AIAgentInterfaceDefinition(
                key="node/delete",
                method="DELETE",
                description="Delete one node by name.",
                arguments_description="Required: name.",
                write=True,
                handler=self._node_delete,
            ),
            AIAgentInterfaceDefinition(
                key="reservation/create",
                method="POST",
                description="Create one reservation using the agent reservation payload.",
                arguments_description="Required: payload.",
                write=True,
                handler=self._reservation_create,
            ),
            AIAgentInterfaceDefinition(
                key="reservation/update",
                method="POST",
                description="Update one reservation by name using the agent reservation payload.",
                arguments_description="Required: name, payload.",
                write=True,
                handler=self._reservation_update,
            ),
            AIAgentInterfaceDefinition(
                key="reservation/delete",
                method="DELETE",
                description="Delete one reservation by name.",
                arguments_description="Required: name.",
                write=True,
                handler=self._reservation_delete,
            ),
            AIAgentInterfaceDefinition(
                key="account/update",
                method="POST",
                description="Create or update accounts using the agent accounts payload.",
                arguments_description="Required: payload.",
                write=True,
                handler=self._accounts_update,
            ),
            AIAgentInterfaceDefinition(
                key="account/delete",
                method="DELETE",
                description="Delete one account by name.",
                arguments_description="Required: name.",
                write=True,
                handler=self._account_delete,
            ),
            AIAgentInterfaceDefinition(
                key="association/update",
                method="POST",
                description="Create or update associations using the agent associations payload.",
                arguments_description="Required: payload.",
                write=True,
                handler=self._associations_update,
            ),
            AIAgentInterfaceDefinition(
                key="association/delete",
                method="DELETE",
                description="Delete associations using the agent associations payload.",
                arguments_description="Required: payload.",
                write=True,
                handler=self._associations_delete,
            ),
            AIAgentInterfaceDefinition(
                key="user/update",
                method="POST",
                description="Create or update SlurmDB users using the agent users payload.",
                arguments_description="Required: payload.",
                write=True,
                handler=self._users_update,
            ),
            AIAgentInterfaceDefinition(
                key="user/delete",
                method="DELETE",
                description="Delete one SlurmDB user by name.",
                arguments_description="Required: name.",
                write=True,
                handler=self._user_delete,
            ),
            AIAgentInterfaceDefinition(
                key="qos/update",
                method="POST",
                description="Create or update QoS using the agent qos payload.",
                arguments_description="Required: payload.",
                write=True,
                handler=self._qos_update,
            ),
            AIAgentInterfaceDefinition(
                key="qos/delete",
                method="DELETE",
                description="Delete one QoS by name.",
                arguments_description="Required: name.",
                write=True,
                handler=self._qos_delete,
            ),
        ):
            self._definitions[definition.key] = definition

    def _allowed(self, user, resource: str, operation: str, scope: str = "*") -> bool:
        return self.app.policy.allowed_user_permission(user, resource, operation, scope)

    @staticmethod
    def _user_login(user) -> Optional[str]:
        return getattr(user, "login", None)

    def _require_permission_scope(self, user, resource: str, operation: str) -> str:
        if self._allowed(user, resource, operation, "*"):
            return "*"
        if self._allowed(user, resource, operation, "self"):
            login = self._user_login(user)
            if login:
                return "self"
        raise AIAgentInterfaceError(403, "Access not permitted")

    def _require_any(self, user, requirements):
        for resource, operation, scope in requirements:
            if self._allowed(user, resource, operation, scope):
                return
        raise AIAgentInterfaceError(403, "Access not permitted")

    def _require_permission(self, user, resource: str, operation: str, scope: str = "*"):
        if not self._allowed(user, resource, operation, scope):
            raise AIAgentInterfaceError(403, "Access not permitted")

    def _ensure_write_supported(self, operation: str):
        _, _, api_version = self.app.slurmrestd.discover()
        if self.app.slurmrestd.supports_write_operations():
            return api_version
        raise AIAgentInterfaceError(
            501,
            f"{operation} is unsupported on slurmrestd API {api_version}",
        )

    def _handle_backend_error(self, err: Exception):
        if isinstance(err, AIAgentInterfaceError):
            raise err
        if isinstance(err, SlurmrestdNotFoundError):
            raise AIAgentInterfaceError(404, f"URL not found on slurmrestd: {err}") from err
        if isinstance(err, SlurmrestdInvalidResponseError):
            raise AIAgentInterfaceError(500, f"Invalid response from slurmrestd: {err}") from err
        if isinstance(err, SlurmrestConnectionError):
            raise AIAgentInterfaceError(500, f"Unable to connect to slurmrestd: {err}") from err
        if isinstance(err, SlurmrestdAuthenticationError):
            raise AIAgentInterfaceError(401, f"Authentication error on slurmrestd: {err}") from err
        if isinstance(err, SlurmrestdInternalError):
            message = f"slurmrestd error: {err.description} ({err.source})"
            if err.error != -1:
                message += f" [{err.message}/{err.error}]"
            raise AIAgentInterfaceError(500, message) from err
        if isinstance(err, SlurmwebCacheError):
            raise AIAgentInterfaceError(500, f"Cache error: {err}") from err
        if isinstance(err, SlurmwebMetricsDBError):
            raise AIAgentInterfaceError(500, str(err)) from err
        raise err

    def _result(self, interface_key: str, payload, status_code: int = 200):
        return AIAgentInterfaceResult(
            interface_key=interface_key,
            status_code=status_code,
            payload=payload,
            summary=_truncate_text(payload),
            error=None,
        )

    @staticmethod
    def _limit(items, limit):
        if not isinstance(items, list):
            return items
        if limit is None:
            return items
        try:
            limit = max(1, min(int(limit), 50))
        except (TypeError, ValueError):
            limit = 10
        return items[:limit]

    @staticmethod
    def _int_argument(arguments: dict, key: str) -> int:
        try:
            return int(arguments[key])
        except (KeyError, TypeError, ValueError) as err:
            raise AIAgentInterfaceError(400, f"{key} must be an integer") from err

    @staticmethod
    def _string_argument(arguments: dict, key: str) -> str:
        value = str(arguments.get(key, "")).strip()
        if not value:
            raise AIAgentInterfaceError(400, f"{key} is required")
        return value

    @staticmethod
    def _payload_argument(arguments: dict) -> dict:
        payload = arguments.get("payload")
        if not isinstance(payload, dict):
            raise AIAgentInterfaceError(400, "payload must be an object")
        return payload

    def _normalize_operation_result(self, operation: str, target, response: dict, status_code: int = 200):
        api_version = self.app.slurmrestd.api_version or self.app.slurmrestd.discover()[2]
        result = {
            key: value
            for key, value in response.items()
            if key not in {"meta", "warnings", "errors"}
        }
        payload = {
            "supported": True,
            "operation": operation,
            "target": target,
            "api_version": api_version,
            "warnings": response.get("warnings", []),
            "errors": response.get("errors", []),
            "result": result,
        }
        return payload, status_code

    def _stats(self, user, arguments: dict):
        self._require_any(user, (("dashboard", "view", "*"), ("analysis", "view", "*")))
        total = 0
        running = 0
        for job in self.app.slurmrestd.jobs():
            total += 1
            if "RUNNING" in job["job_state"]:
                running += 1
        nodes = 0
        cores = 0
        memory = 0
        memory_allocated = 0
        gpus = 0
        nodes_data = (
            self.app.slurmrestd.nodes_unfiltered()
            if callable(getattr(self.app.slurmrestd, "nodes_unfiltered", None))
            else self.app.slurmrestd.nodes()
        )
        for node in nodes_data:
            nodes += 1
            cores += node["cpus"]
            node_memory = max(node.get("real_memory", 0), 0)
            memory += node_memory
            allocated = max(
                self.app.slurmrestd._optional_number_value(node.get("alloc_memory"), 0),
                0,
            )
            allocated = min(node_memory, allocated)
            memory_allocated += allocated
            gpus += self.app.slurmrestd.node_gres_extract_gpus(node["gres"])
        return self._result(
            "stats",
            {
                "resources": {
                    "nodes": nodes,
                    "cores": cores,
                    "memory": memory,
                    "memory_allocated": memory_allocated,
                    "memory_available": max(memory - memory_allocated, 0),
                    "gpus": gpus,
                },
                "jobs": {"running": running, "total": total},
            },
        )

    def _jobs(self, user, arguments: dict):
        scope = self._require_permission_scope(user, "jobs", "view")
        node = arguments.get("node")
        if node:
            jobs = self.app.slurmrestd.jobs_by_node(str(node))
        elif scope == "self":
            jobs = self.app.slurmrestd.jobs(query={"user": self._user_login(user)})
        else:
            jobs = self.app.slurmrestd.jobs()
        if scope == "self":
            jobs = _filter_jobs_for_owner(jobs, self._user_login(user))
        return self._result("jobs", self._limit(jobs, arguments.get("limit")))

    def _job(self, user, arguments: dict):
        job_id = self._int_argument(arguments, "job_id")
        scope = self._require_permission_scope(user, "jobs", "view")
        job_data = self.app.slurmrestd.job(job_id)
        if scope == "self":
            owner = _job_owner(job_data)
            if owner is None or owner != self._user_login(user):
                raise AIAgentInterfaceError(403, "Access not permitted")
        return self._result("job", job_data)

    def _jobs_history(self, user, arguments: dict):
        if not self._allowed(user, "jobs-history", "view", "*"):
            raise AIAgentInterfaceError(403, "Access not permitted")
        if self.app.jobs_store is None:
            raise AIAgentInterfaceError(501, "Job history persistence is disabled")
        page_size = arguments.get("page_size", arguments.get("limit", 50))
        filters = {
            "start": arguments.get("start"),
            "end": arguments.get("end"),
            "keyword": arguments.get("keyword"),
            "user": arguments.get("user"),
            "account": arguments.get("account"),
            "partition": arguments.get("partition"),
            "qos": arguments.get("qos"),
            "state": arguments.get("state"),
            "job_id": arguments.get("job_id"),
            "page": arguments.get("page", 1),
            "page_size": min(max(int(page_size), 1), 100),
            "sort": arguments.get("sort"),
            "order": arguments.get("order"),
        }
        result = self.app.jobs_store.query(filters)
        result["jobs"] = [
            _normalize_job_history_record(record) for record in result.get("jobs", [])
        ]
        return self._result("jobs/history", result)

    def _job_history_detail(self, user, arguments: dict):
        if not self._allowed(user, "jobs-history", "view", "*"):
            raise AIAgentInterfaceError(403, "Access not permitted")
        if self.app.jobs_store is None:
            raise AIAgentInterfaceError(501, "Job history persistence is disabled")
        record_id = self._int_argument(arguments, "record_id")
        record = self.app.jobs_store.get_by_id(record_id)
        if record is None:
            raise AIAgentInterfaceError(404, f"Job history record {record_id} not found")
        return self._result("jobs/history/detail", _normalize_job_history_record(record))

    def _nodes(self, user, arguments: dict):
        self._require_any(user, (("resources", "view", "*"),))
        return self._result("nodes", self._limit(self.app.slurmrestd.nodes(), arguments.get("limit")))

    def _node(self, user, arguments: dict):
        self._require_any(user, (("resources", "view", "*"),))
        return self._result("node", self.app.slurmrestd.node(self._string_argument(arguments, "name")))

    def _node_metrics(self, user, arguments: dict):
        self._require_any(user, (("resources", "view", "*"),))
        if self.app.node_metrics_db is None:
            raise AIAgentInterfaceError(501, "Node real-time metrics is disabled")
        name = self._string_argument(arguments, "name")
        return self._result(
            "node/metrics",
            self.app.node_metrics_db.node_instant_metrics(
                name,
                self.app.settings.node_metrics.node_hostname_label,
            ),
        )

    def _node_metrics_history(self, user, arguments: dict):
        self._require_any(user, (("resources", "view", "*"),))
        if self.app.node_metrics_db is None:
            raise AIAgentInterfaceError(501, "Node real-time metrics is disabled")
        name = self._string_argument(arguments, "name")
        return self._result(
            "node/metrics/history",
            self.app.node_metrics_db.node_history_metrics(
                name,
                arguments.get("range", "hour"),
                self.app.settings.node_metrics.node_hostname_label,
            ),
        )

    def _partitions(self, user, arguments: dict):
        self._require_any(
            user,
            (
                ("jobs/filter-partitions", "view", "*"),
                ("resources/filter-partitions", "view", "*"),
            ),
        )
        return self._result("partitions", self.app.slurmrestd.partitions())

    def _qos(self, user, arguments: dict):
        self._require_any(
            user,
            (
                ("qos", "view", "*"),
                ("jobs/filter-qos", "view", "*"),
            ),
        )
        return self._result("qos", self.app.slurmrestd.qos())

    def _reservations(self, user, arguments: dict):
        self._require_any(user, (("reservations", "view", "*"),))
        return self._result("reservations", self.app.slurmrestd.reservations())

    def _accounts(self, user, arguments: dict):
        self._require_any(
            user,
            (
                ("accounts", "view", "*"),
                ("jobs/filter-accounts", "view", "*"),
            ),
        )
        return self._result("accounts", self.app.slurmrestd.accounts())

    def _account(self, user, arguments: dict):
        self._require_any(user, (("accounts", "view", "*"),))
        return self._result("account", self.app.slurmrestd.account(self._string_argument(arguments, "name")))

    def _associations(self, user, arguments: dict):
        self._require_any(
            user,
            (
                ("accounts", "view", "*"),
                ("user/profile", "view", "*"),
            ),
        )
        return self._result(
            "associations",
            self._limit(self.app.slurmrestd.associations(), arguments.get("limit")),
        )

    def _users(self, user, arguments: dict):
        self._require_any(user, (("users-admin", "view", "*"),))
        return self._result("users", self._limit(self.app.slurmrestd.users(), arguments.get("limit")))

    def _user(self, user, arguments: dict):
        self._require_any(user, (("users-admin", "view", "*"),))
        return self._result("user", self.app.slurmrestd.user(self._string_argument(arguments, "name")))

    def _user_analysis_allowed(self, user, username: str) -> bool:
        if username == self._user_login(user) and self._allowed(user, "user/analysis", "view", "self"):
            return True
        if self._allowed(user, "user/analysis", "view", "*"):
            return True
        return self._allowed(user, "jobs", "view", "*")

    def _user_metrics_history(self, user, arguments: dict):
        username = self._string_argument(arguments, "username")
        if not self._user_analysis_allowed(user, username):
            raise AIAgentInterfaceError(403, "Access not permitted")
        if not getattr(self.app, "user_metrics_enabled", False) or self.app.user_metrics_store is None:
            raise AIAgentInterfaceError(501, "User metrics is disabled")
        return self._result(
            "user/metrics/history",
            self.app.user_metrics_store.user_metrics_history(
                username,
                arguments.get("range", "hour"),
            ),
        )

    def _user_activity_summary(self, user, arguments: dict):
        username = self._string_argument(arguments, "username")
        if not self._user_analysis_allowed(user, username):
            raise AIAgentInterfaceError(403, "Access not permitted")
        if not getattr(self.app, "user_metrics_enabled", False) or self.app.user_metrics_store is None:
            raise AIAgentInterfaceError(501, "User metrics is disabled")
        return self._result(
            "user/activity/summary",
            self.app.user_metrics_store.user_activity_summary(username),
        )

    def _authorize_job_write(self, user, job_id: int, operation: str):
        scope = self._require_permission_scope(user, "jobs", operation)
        if scope == "*":
            return
        job_data = self.app.slurmrestd.job(job_id)
        owner = _job_owner(job_data)
        if owner is None or owner != self._user_login(user):
            raise AIAgentInterfaceError(403, "Access not permitted")

    def _job_submit(self, user, arguments: dict):
        self._require_permission_scope(user, "jobs", "edit")
        self._ensure_write_supported("jobs.submit")
        payload, status_code = self._normalize_operation_result(
            "jobs.submit",
            None,
            self.app.slurmrestd.job_submit(self._payload_argument(arguments)),
            status_code=201,
        )
        return self._result("job/submit", payload, status_code=status_code)

    def _job_update(self, user, arguments: dict):
        self._ensure_write_supported("jobs.update")
        job_id = self._int_argument(arguments, "job_id")
        self._authorize_job_write(user, job_id, "edit")
        payload, status_code = self._normalize_operation_result(
            "jobs.update",
            {"job_id": job_id},
            self.app.slurmrestd.job_update(job_id, self._payload_argument(arguments)),
        )
        return self._result("job/update", payload, status_code=status_code)

    def _job_cancel(self, user, arguments: dict):
        self._ensure_write_supported("jobs.cancel")
        job_id = self._int_argument(arguments, "job_id")
        self._authorize_job_write(user, job_id, "delete")
        payload, status_code = self._normalize_operation_result(
            "jobs.cancel",
            {"job_id": job_id},
            self.app.slurmrestd.job_cancel(job_id, arguments.get("payload")),
        )
        return self._result("job/cancel", payload, status_code=status_code)

    def _node_update(self, user, arguments: dict):
        self._require_permission(user, "resources", "edit", "*")
        self._ensure_write_supported("resources.node.update")
        name = self._string_argument(arguments, "name")
        payload, status_code = self._normalize_operation_result(
            "resources.node.update",
            {"node": name},
            self.app.slurmrestd.node_update(name, self._payload_argument(arguments)),
        )
        return self._result("node/update", payload, status_code=status_code)

    def _node_delete(self, user, arguments: dict):
        self._require_permission(user, "resources", "delete", "*")
        self._ensure_write_supported("resources.node.delete")
        name = self._string_argument(arguments, "name")
        payload, status_code = self._normalize_operation_result(
            "resources.node.delete",
            {"node": name},
            self.app.slurmrestd.node_delete(name),
        )
        return self._result("node/delete", payload, status_code=status_code)

    def _reservation_create(self, user, arguments: dict):
        self._require_permission(user, "reservations", "edit", "*")
        self._ensure_write_supported("reservations.create")
        payload, status_code = self._normalize_operation_result(
            "reservations.create",
            None,
            self.app.slurmrestd.reservation_create(self._payload_argument(arguments)),
            status_code=201,
        )
        return self._result("reservation/create", payload, status_code=status_code)

    def _reservation_update(self, user, arguments: dict):
        self._require_permission(user, "reservations", "edit", "*")
        self._ensure_write_supported("reservations.update")
        name = self._string_argument(arguments, "name")
        payload, status_code = self._normalize_operation_result(
            "reservations.update",
            {"reservation": name},
            self.app.slurmrestd.reservation_update(name, self._payload_argument(arguments)),
        )
        return self._result("reservation/update", payload, status_code=status_code)

    def _reservation_delete(self, user, arguments: dict):
        self._require_permission(user, "reservations", "delete", "*")
        self._ensure_write_supported("reservations.delete")
        name = self._string_argument(arguments, "name")
        payload, status_code = self._normalize_operation_result(
            "reservations.delete",
            {"reservation": name},
            self.app.slurmrestd.reservation_delete(name),
        )
        return self._result("reservation/delete", payload, status_code=status_code)

    def _accounts_update(self, user, arguments: dict):
        self._require_permission(user, "accounts", "edit", "*")
        self._ensure_write_supported("accounts.update")
        payload, status_code = self._normalize_operation_result(
            "accounts.update",
            None,
            self.app.slurmrestd.accounts_update(self._payload_argument(arguments)),
        )
        return self._result("account/update", payload, status_code=status_code)

    def _account_delete(self, user, arguments: dict):
        self._require_permission(user, "accounts", "delete", "*")
        self._ensure_write_supported("accounts.delete")
        name = self._string_argument(arguments, "name")
        payload, status_code = self._normalize_operation_result(
            "accounts.delete",
            {"account": name},
            self.app.slurmrestd.account_delete(name),
        )
        return self._result("account/delete", payload, status_code=status_code)

    def _associations_update(self, user, arguments: dict):
        self._require_permission(user, "accounts", "edit", "*")
        self._ensure_write_supported("accounts.associations.update")
        payload, status_code = self._normalize_operation_result(
            "accounts.associations.update",
            None,
            self.app.slurmrestd.associations_update(self._payload_argument(arguments)),
        )
        return self._result("association/update", payload, status_code=status_code)

    def _associations_delete(self, user, arguments: dict):
        self._require_permission(user, "accounts", "delete", "*")
        self._ensure_write_supported("accounts.associations.delete")
        payload, status_code = self._normalize_operation_result(
            "accounts.associations.delete",
            None,
            self.app.slurmrestd.associations_delete(self._payload_argument(arguments)),
        )
        return self._result("association/delete", payload, status_code=status_code)

    def _users_update(self, user, arguments: dict):
        self._require_permission(user, "users-admin", "edit", "*")
        self._ensure_write_supported("users.update")
        payload, status_code = self._normalize_operation_result(
            "users.update",
            None,
            self.app.slurmrestd.users_update(self._payload_argument(arguments)),
        )
        return self._result("user/update", payload, status_code=status_code)

    def _user_delete(self, user, arguments: dict):
        self._require_permission(user, "users-admin", "delete", "*")
        self._ensure_write_supported("users.delete")
        name = self._string_argument(arguments, "name")
        payload, status_code = self._normalize_operation_result(
            "users.delete",
            {"user": name},
            self.app.slurmrestd.user_delete(name),
        )
        return self._result("user/delete", payload, status_code=status_code)

    def _qos_update(self, user, arguments: dict):
        self._require_permission(user, "qos", "edit", "*")
        self._ensure_write_supported("qos.update")
        payload, status_code = self._normalize_operation_result(
            "qos.update",
            None,
            self.app.slurmrestd.qos_update(self._payload_argument(arguments)),
        )
        return self._result("qos/update", payload, status_code=status_code)

    def _qos_delete(self, user, arguments: dict):
        self._require_permission(user, "qos", "delete", "*")
        self._ensure_write_supported("qos.delete")
        name = self._string_argument(arguments, "name")
        payload, status_code = self._normalize_operation_result(
            "qos.delete",
            {"qos": name},
            self.app.slurmrestd.qos_delete(name),
        )
        return self._result("qos/delete", payload, status_code=status_code)

    def catalog(self, user) -> list[dict]:
        catalog = []
        for definition in self._definitions.values():
            catalog.append(
                {
                    "key": definition.key,
                    "method": definition.method,
                    "description": definition.description,
                    "arguments_description": definition.arguments_description,
                    "write": definition.write,
                }
            )
        return sorted(catalog, key=lambda item: (item["write"], item["key"]))

    def execute(self, user, interface_key: str, arguments: dict | None = None) -> AIAgentInterfaceResult:
        definition = self._definitions.get(interface_key)
        if definition is None:
            raise AIAgentInterfaceError(400, f"Unsupported agent interface {interface_key}")
        arguments = arguments or {}
        try:
            return definition.handler(user, arguments)
        except Exception as err:
            self._handle_backend_error(err)
