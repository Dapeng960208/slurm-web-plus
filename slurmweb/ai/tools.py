# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import time
from typing import Callable, Dict


def _truncate_text(value, limit=2400):
    text = json.dumps(value, default=str, ensure_ascii=True)
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


class AIToolPermissionError(PermissionError):
    pass


class AIToolExecutionError(RuntimeError):
    pass


class AIToolRegistry:
    def __init__(self, app, conversation_store):
        self.app = app
        self.conversation_store = conversation_store

    def definitions(self):
        return [
            {
                "name": "get_cluster_stats",
                "permission": "view-stats",
                "description": "Get overall cluster resource and job statistics.",
            },
            {
                "name": "list_jobs",
                "permission": "view-jobs",
                "description": "List active jobs with optional node filter and result limit.",
            },
            {
                "name": "get_job",
                "permission": "view-jobs",
                "description": "Get details for one job by numeric job_id.",
            },
            {
                "name": "list_nodes",
                "permission": "view-nodes",
                "description": "List compute nodes with optional result limit.",
            },
            {
                "name": "get_node",
                "permission": "view-nodes",
                "description": "Get details for one node by name.",
            },
            {
                "name": "get_node_metrics",
                "permission": "view-nodes",
                "description": "Get real-time metrics for a node.",
            },
            {
                "name": "get_node_metrics_history",
                "permission": "view-nodes",
                "description": "Get historical node metrics for range hour/day/week.",
            },
            {
                "name": "list_partitions",
                "permission": "view-partitions",
                "description": "List cluster partitions.",
            },
            {
                "name": "list_qos",
                "permission": "view-qos",
                "description": "List configured QoS records.",
            },
            {
                "name": "list_reservations",
                "permission": "view-reservations",
                "description": "List active reservations.",
            },
            {
                "name": "list_accounts",
                "permission": "view-accounts",
                "description": "List accounts.",
            },
            {
                "name": "list_associations",
                "permission": "associations-view",
                "description": "List account/user associations and limits.",
            },
            {
                "name": "list_job_history",
                "permission": "view-history-jobs",
                "description": "Query persisted job history with optional filters.",
            },
            {
                "name": "call_readonly_api",
                "permission": "view-stats",
                "description": "Fallback read-only adapter for safe internal methods only.",
            },
        ]

    def _require_permission(self, user, action: str):
        if not self.app.policy.allowed_user_action(user, action):
            raise AIToolPermissionError(f"Missing permission {action}")

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

    def _stats(self):
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
        return {
            "resources": {
                "nodes": nodes,
                "cores": cores,
                "memory": memory,
                "memory_allocated": memory_allocated,
                "memory_available": max(memory - memory_allocated, 0),
                "gpus": gpus,
            },
            "jobs": {"running": running, "total": total},
        }

    def _call_readonly_method(self, method_name: str, args: dict):
        safe_methods: Dict[str, tuple[str, Callable[[dict], object]]] = {
            "stats": ("view-stats", lambda _: self._stats()),
            "jobs": ("view-jobs", lambda payload: self._limit(self.app.slurmrestd.jobs(), payload.get("limit"))),
            "job": ("view-jobs", lambda payload: self.app.slurmrestd.job(int(payload["job_id"]))),
            "nodes": ("view-nodes", lambda payload: self._limit(self.app.slurmrestd.nodes(), payload.get("limit"))),
            "node": ("view-nodes", lambda payload: self.app.slurmrestd.node(payload["name"])),
            "partitions": ("view-partitions", lambda _: self.app.slurmrestd.partitions()),
            "qos": ("view-qos", lambda _: self.app.slurmrestd.qos()),
            "reservations": ("view-reservations", lambda _: self.app.slurmrestd.reservations()),
            "accounts": ("view-accounts", lambda _: self.app.slurmrestd.accounts()),
            "associations": ("associations-view", lambda payload: self._limit(self.app.slurmrestd.associations(), payload.get("limit"))),
        }
        if method_name not in safe_methods:
            raise AIToolExecutionError(f"Unsupported read-only method {method_name}")
        return safe_methods[method_name]

    def execute(self, user, conversation_id: int, tool_name: str, arguments: dict, message_id=None):
        arguments = arguments or {}
        started = time.time()
        permission = "view-stats"
        try:
            if tool_name == "get_cluster_stats":
                permission = "view-stats"
                self._require_permission(user, permission)
                result = self._stats()
            elif tool_name == "list_jobs":
                permission = "view-jobs"
                self._require_permission(user, permission)
                node = arguments.get("node")
                jobs = self.app.slurmrestd.jobs_by_node(node) if node else self.app.slurmrestd.jobs()
                result = self._limit(jobs, arguments.get("limit"))
            elif tool_name == "get_job":
                permission = "view-jobs"
                self._require_permission(user, permission)
                result = self.app.slurmrestd.job(int(arguments["job_id"]))
            elif tool_name == "list_nodes":
                permission = "view-nodes"
                self._require_permission(user, permission)
                result = self._limit(self.app.slurmrestd.nodes(), arguments.get("limit"))
            elif tool_name == "get_node":
                permission = "view-nodes"
                self._require_permission(user, permission)
                result = self.app.slurmrestd.node(arguments["name"])
            elif tool_name == "get_node_metrics":
                permission = "view-nodes"
                self._require_permission(user, permission)
                if self.app.node_metrics_db is None:
                    raise AIToolExecutionError("Node metrics are disabled")
                result = self.app.node_metrics_db.node_instant_metrics(
                    arguments["name"],
                    self.app.settings.node_metrics.node_hostname_label,
                )
            elif tool_name == "get_node_metrics_history":
                permission = "view-nodes"
                self._require_permission(user, permission)
                if self.app.node_metrics_db is None:
                    raise AIToolExecutionError("Node metrics are disabled")
                result = self.app.node_metrics_db.node_history_metrics(
                    arguments["name"],
                    arguments.get("range", "hour"),
                    self.app.settings.node_metrics.node_hostname_label,
                )
            elif tool_name == "list_partitions":
                permission = "view-partitions"
                self._require_permission(user, permission)
                result = self.app.slurmrestd.partitions()
            elif tool_name == "list_qos":
                permission = "view-qos"
                self._require_permission(user, permission)
                result = self.app.slurmrestd.qos()
            elif tool_name == "list_reservations":
                permission = "view-reservations"
                self._require_permission(user, permission)
                result = self.app.slurmrestd.reservations()
            elif tool_name == "list_accounts":
                permission = "view-accounts"
                self._require_permission(user, permission)
                result = self.app.slurmrestd.accounts()
            elif tool_name == "list_associations":
                permission = "associations-view"
                self._require_permission(user, permission)
                result = self._limit(self.app.slurmrestd.associations(), arguments.get("limit"))
            elif tool_name == "list_job_history":
                permission = "view-history-jobs"
                self._require_permission(user, permission)
                if self.app.jobs_store is None:
                    raise AIToolExecutionError("Job history is disabled")
                query = {
                    "job_id": arguments.get("job_id"),
                    "user": arguments.get("user"),
                    "state": arguments.get("state"),
                    "keyword": arguments.get("keyword"),
                    "page": 1,
                    "page_size": min(max(int(arguments.get("limit", 10)), 1), 50),
                }
                result = self.app.jobs_store.query(query)
            elif tool_name == "call_readonly_api":
                method_name = str(arguments.get("method", "")).strip()
                permission, callback = self._call_readonly_method(
                    method_name,
                    arguments.get("arguments") or {},
                )
                self._require_permission(user, permission)
                result = callback(arguments.get("arguments") or {})
            else:
                raise AIToolExecutionError(f"Unsupported tool {tool_name}")
            duration_ms = int((time.time() - started) * 1000)
            self.conversation_store.record_tool_call(
                conversation_id=conversation_id,
                message_id=message_id,
                cluster=self.app.settings.service.cluster,
                username=user.login,
                tool_name=tool_name,
                permission=permission,
                input_payload=arguments,
                result_summary=_truncate_text(result, limit=1200),
                status="ok",
                error=None,
                duration_ms=duration_ms,
            )
            return {
                "tool_name": tool_name,
                "permission": permission,
                "arguments": arguments,
                "result": result,
                "result_summary": _truncate_text(result, limit=2400),
                "duration_ms": duration_ms,
            }
        except Exception as err:
            duration_ms = int((time.time() - started) * 1000)
            self.conversation_store.record_tool_call(
                conversation_id=conversation_id,
                message_id=message_id,
                cluster=self.app.settings.service.cluster,
                username=user.login,
                tool_name=tool_name,
                permission=permission,
                input_payload=arguments,
                result_summary=None,
                status="error",
                error=str(err),
                duration_ms=duration_ms,
            )
            raise
