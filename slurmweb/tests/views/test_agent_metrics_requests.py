# Copyright (c) 2024 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT


from unittest import mock

from slurmweb.version import get_version
from slurmweb.errors import SlurmwebMetricsDBError

from ..lib.agent import TestAgentBase, RemoveActionInPolicy
from ..lib.utils import mock_prometheus_response


class TestAgentMetricsRequest(TestAgentBase):
    def setUp(self):
        self.setup_client(metrics=True)

    def tearDown(self):
        self.app.metrics_collector.unregister()

    def _enable_custom_rules(self, *rules):
        self.app.access_control_enabled = True
        self.app.access_control_store = mock.Mock()
        self.app.access_control_store.user_permissions.return_value = ([], [], list(rules))
        self.app.policy._access_control_enabled = True
        self.app.policy.set_access_control_store(self.app.access_control_store)

    def test_request_metrics_error(self):
        self.app.metrics_db.request = mock.Mock(
            side_effect=SlurmwebMetricsDBError("fake metrics request error")
        )
        with self.assertLogs("slurmweb", level="WARNING") as cm:
            response = self.client.get(f"/v{get_version()}/metrics/nodes")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json,
            {
                "code": 500,
                "description": "fake metrics request error",
                "name": "Internal Server Error",
            },
        )
        self.assertEqual(
            cm.output, ["WARNING:slurmweb.views.agent:fake metrics request error"]
        )

    @mock.patch("slurmweb.metrics.db.aiohttp.ClientSession.get")
    def test_request_metrics_nodes(self, mock_get):
        _, mock_get.return_value = mock_prometheus_response("nodes-hour")
        response = self.client.get(f"/v{get_version()}/metrics/nodes")
        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(
            response.json.keys(),
            ["allocated", "down", "drain", "idle", "mixed", "unknown"],
        )

    @mock.patch("slurmweb.metrics.db.aiohttp.ClientSession.get")
    def test_request_metrics_cores(self, mock_get):
        _, mock_get.return_value = mock_prometheus_response("cores-hour")
        response = self.client.get(f"/v{get_version()}/metrics/cores")
        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(
            response.json.keys(),
            ["allocated", "down", "drain", "idle", "unknown"],
        )

    @mock.patch("slurmweb.metrics.db.aiohttp.ClientSession.get")
    def test_request_metrics_gpus(self, mock_get):
        _, mock_get.return_value = mock_prometheus_response("gpus-hour")
        response = self.client.get(f"/v{get_version()}/metrics/gpus")
        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(
            response.json.keys(),
            ["allocated", "down", "drain", "idle", "unknown"],
        )

    @mock.patch("slurmweb.metrics.db.aiohttp.ClientSession.get")
    def test_request_metrics_memory(self, mock_get):
        _, mock_get.return_value = mock_prometheus_response("memory-hour")
        response = self.client.get(f"/v{get_version()}/metrics/memory")
        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(
            response.json.keys(),
            ["allocated", "idle"],
        )

    @mock.patch("slurmweb.metrics.db.aiohttp.ClientSession.get")
    def test_request_metrics_jobs(self, mock_get):
        self._enable_custom_rules("jobs:view:*")
        _, mock_get.return_value = mock_prometheus_response("jobs-hour")
        response = self.client.get(f"/v{get_version()}/metrics/jobs")
        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(
            response.json.keys(),
            [
                "cancelled",
                "completed",
                "completing",
                "failed",
                "timeout",
                "pending",
                "running",
                "unknown",
            ],
        )

    @mock.patch("slurmweb.metrics.db.aiohttp.ClientSession.get")
    def test_request_metrics_cache(self, mock_get):
        self._enable_custom_rules("admin/cache:view:*")
        _, mock_get.return_value = mock_prometheus_response("cache-hour")
        response = self.client.get(f"/v{get_version()}/metrics/cache")
        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(
            response.json.keys(),
            [
                "hit",
                "miss",
            ],
        )

    def test_request_metrics_users_disabled_when_user_analytics_disabled(self):
        response = self.client.get(f"/v{get_version()}/metrics/users")
        self.assertEqual(response.status_code, 501)
        self.assertEqual(
            response.json,
            {
                "code": 501,
                "description": "User metrics is disabled",
                "name": "Not Implemented",
            },
        )

    @mock.patch("slurmweb.metrics.db.aiohttp.ClientSession.get")
    def test_request_metrics_users(self, mock_get):
        self.app.user_metrics_enabled = True
        self._enable_custom_rules("jobs:view:*")
        _, mock_get.return_value = mock_prometheus_response("users-hour")
        response = self.client.get(f"/v{get_version()}/metrics/users")
        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(response.json.keys(), ["alice", "bob"])

    def test_request_user_metrics_history_disabled(self):
        self._enable_custom_rules("user/analysis:view:self")
        response = self.client.get(
            f"/v{get_version()}/user/{self.user.login}/metrics/history?range=hour"
        )
        self.assertEqual(response.status_code, 501)
        self.assertEqual(response.json["description"], "User metrics is disabled")

    def test_request_user_metrics_history(self):
        self.app.user_metrics_enabled = True
        self.app.user_metrics_store = mock.Mock()
        self._enable_custom_rules("user/analysis:view:self")
        self.app.user_metrics_store.user_metrics_history.return_value = {
            "submissions": [[1713956400000, 2]]
        }

        response = self.client.get(
            f"/v{get_version()}/user/{self.user.login}/metrics/history?range=hour"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"submissions": [[1713956400000, 2]]})
        self.app.user_metrics_store.user_metrics_history.assert_called_once_with(
            self.user.login, "hour"
        )

    def test_request_user_activity_summary(self):
        self.app.user_metrics_enabled = True
        self.app.user_metrics_store = mock.Mock()
        self._enable_custom_rules("user/analysis:view:self")
        self.app.user_metrics_store.user_activity_summary.return_value = {
            "username": "alice",
            "profile": {"fullname": "Alice Doe", "groups": [], "ldap_synced_at": None, "ldap_found": True},
            "generated_at": "2026-04-24T00:00:00+00:00",
            "totals": {"submitted_jobs_today": 3},
            "tool_breakdown": [],
        }

        response = self.client.get(
            f"/v{get_version()}/user/{self.user.login}/activity/summary"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["username"], "alice")
        self.assertEqual(response.json["totals"]["submitted_jobs_today"], 3)

    def test_request_metrics_nodes_denied(self):
        with RemoveActionInPolicy(self.app.policy, "user", "view-nodes"):
            with self.assertLogs("slurmweb", level="WARNING") as cm:
                response = self.client.get(f"/v{get_version()}/metrics/nodes")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json,
            {
                "code": 403,
                "description": "Access to nodes metric not permitted",
                "name": "Forbidden",
            },
        )
        self.assertEqual(
            cm.output,
            [
                "WARNING:slurmweb.views.agent:Unauthorized access from user test (∅) "
                "[group] to nodes metric (missing permission on resources:view:*)"
            ],
        )

    def test_request_metrics_cores_denied(self):
        with RemoveActionInPolicy(self.app.policy, "user", "view-nodes"):
            with self.assertLogs("slurmweb", level="WARNING") as cm:
                response = self.client.get(f"/v{get_version()}/metrics/cores")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json,
            {
                "code": 403,
                "description": "Access to cores metric not permitted",
                "name": "Forbidden",
            },
        )
        self.assertEqual(
            cm.output,
            [
                "WARNING:slurmweb.views.agent:Unauthorized access from user test (∅) "
                "[group] to cores metric (missing permission on resources:view:*)"
            ],
        )

    def test_request_metrics_memory_denied(self):
        with RemoveActionInPolicy(self.app.policy, "user", "view-nodes"):
            with self.assertLogs("slurmweb", level="WARNING") as cm:
                response = self.client.get(f"/v{get_version()}/metrics/memory")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json,
            {
                "code": 403,
                "description": "Access to memory metric not permitted",
                "name": "Forbidden",
            },
        )
        self.assertEqual(len(cm.output), 1)
        self.assertIn(
            "Unauthorized access from user test",
            cm.output[0],
        )
        self.assertIn(
            "to memory metric (missing permission on resources:view:*)",
            cm.output[0],
        )

    def test_request_metrics_jobs_denied(self):
        with self.assertLogs("slurmweb", level="WARNING") as cm:
            response = self.client.get(f"/v{get_version()}/metrics/jobs")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json,
            {
                "code": 403,
                "description": "Access to jobs metric not permitted",
                "name": "Forbidden",
            },
        )
        self.assertEqual(
            cm.output,
            [
                "WARNING:slurmweb.views.agent:Unauthorized access from user test (∅) "
                "[group] to jobs metric (missing permission on jobs:view:*)"
            ],
        )

    def test_request_metrics_cache_denied(self):
        with self.assertLogs("slurmweb", level="WARNING") as cm:
            response = self.client.get(f"/v{get_version()}/metrics/cache")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json,
            {
                "code": 403,
                "description": "Access to cache metric not permitted",
                "name": "Forbidden",
            },
        )
        self.assertEqual(
            cm.output,
            [
                "WARNING:slurmweb.views.agent:Unauthorized access from user test (∅) "
                "[group] to cache metric (missing permission on admin/cache:view:*)"
            ],
        )

    @mock.patch("slurmweb.metrics.db.aiohttp.ClientSession.get")
    def test_request_metrics_unexpected(self, mock_get):
        self._enable_custom_rules("jobs:view:*")
        _, mock_get.return_value = mock_prometheus_response("unknown-metric")
        response = self.client.get(f"/v{get_version()}/metrics/jobs")
        self.assertEqual(response.status_code, 500)
        self.assertRegex(response.json["description"], "^Empty result for query .*$")

    def test_request_metrics_unexisting(self):
        response = self.client.get(f"/v{get_version()}/metrics/fail")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json,
            {
                "code": 404,
                "description": "Metric fail not found",
                "name": "Not Found",
            },
        )


class TestAgentMetricsRequestDisabled(TestAgentBase):
    def setUp(self):
        self.setup_client(metrics=False)

    def test_request(self):
        response = self.client.get(f"/v{get_version()}/metrics/jobs")
        self.assertEqual(response.status_code, 501)
        self.assertEqual(
            response.json,
            {
                "code": 501,
                "description": "Metrics are disabled, unable to query values",
                "name": "Not Implemented",
            },
        )


class TestAgentNodeMetricsHistoryRequest(TestAgentBase):
    def setUp(self):
        self.setup_client(node_metrics=True)

    @mock.patch("slurmweb.metrics.db.aiohttp.ClientSession.get")
    def test_request_node_metrics_history(self, mock_get):
        _, response = mock_prometheus_response("node-history-hour")
        mock_get.side_effect = [response, response, response]
        response = self.client.get(
            f"/v{get_version()}/node/cn01/metrics/history?range=hour"
        )
        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(
            response.json.keys(),
            ["cpu_usage", "memory_usage", "disk_usage"],
        )
        self.assertGreater(len(response.json["cpu_usage"]), 0)

    def test_request_node_metrics_history_invalid_range(self):
        response = self.client.get(
            f"/v{get_version()}/node/cn01/metrics/history?range=fail"
        )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json,
            {
                "code": 500,
                "description": "Unsupported metric range fail",
                "name": "Internal Server Error",
            },
        )


class TestAgentNodeMetricsHistoryRequestDisabled(TestAgentBase):
    def setUp(self):
        self.setup_client(node_metrics=False)

    def test_request_node_metrics_history_disabled(self):
        response = self.client.get(
            f"/v{get_version()}/node/cn01/metrics/history?range=hour"
        )
        self.assertEqual(response.status_code, 501)
        self.assertEqual(
            response.json,
            {
                "code": 501,
                "description": "Node real-time metrics is disabled",
                "name": "Not Implemented",
            },
        )


class TestAgentUserMetricsRequests(TestAgentBase):
    def setUp(self):
        self.setup_client(metrics=True)

    def tearDown(self):
        self.app.metrics_collector.unregister()

    def _enable_custom_rules(self, *rules):
        self.app.access_control_enabled = True
        self.app.access_control_store = mock.Mock()
        self.app.access_control_store.user_permissions.return_value = ([], [], list(rules))
        self.app.policy._access_control_enabled = True
        self.app.policy.set_access_control_store(self.app.access_control_store)

    def test_request_user_metrics_history_disabled(self):
        self._enable_custom_rules("user/analysis:view:self")
        response = self.client.get(
            f"/v{get_version()}/user/{self.user.login}/metrics/history?range=hour"
        )
        self.assertEqual(response.status_code, 501)
        self.assertEqual(
            response.json,
            {
                "code": 501,
                "description": "User metrics is disabled",
                "name": "Not Implemented",
            },
        )

    def test_request_user_metrics_history(self):
        self.app.user_metrics_enabled = True
        self.app.user_metrics_store = mock.Mock()
        self._enable_custom_rules("user/analysis:view:self")
        self.app.user_metrics_store.user_metrics_history.return_value = {
            "submissions": [[1713956400000, 2]]
        }

        response = self.client.get(
            f"/v{get_version()}/user/{self.user.login}/metrics/history?range=hour"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"submissions": [[1713956400000, 2]]})
        self.app.user_metrics_store.user_metrics_history.assert_called_once_with(
            self.user.login, "hour"
        )

    def test_request_user_metrics_history_invalid_range(self):
        self.app.user_metrics_enabled = True
        self.app.user_metrics_store = mock.Mock()
        self._enable_custom_rules("user/analysis:view:self")
        self.app.user_metrics_store.user_metrics_history.side_effect = ValueError(
            "Unsupported metric range month"
        )

        with self.assertLogs("slurmweb", level="WARNING") as cm:
            response = self.client.get(
                f"/v{get_version()}/user/{self.user.login}/metrics/history?range=month"
            )

        self.assertEqual(response.status_code, 400)
        if response.json is not None:
            self.assertEqual(
                response.json,
                {
                    "code": 400,
                    "description": "Unsupported metric range month",
                    "name": "Bad Request",
                },
            )
        else:
            self.assertIn("Unsupported metric range month", response.text)
        self.assertEqual(
            cm.output,
            [
                f"WARNING:slurmweb.views.agent:Unsupported user metrics history range for {self.user.login}: Unsupported metric range month"
            ],
        )

    def test_request_user_activity_summary_disabled(self):
        self._enable_custom_rules("user/analysis:view:self")
        response = self.client.get(
            f"/v{get_version()}/user/{self.user.login}/activity/summary"
        )
        self.assertEqual(response.status_code, 501)
        self.assertEqual(
            response.json,
            {
                "code": 501,
                "description": "User metrics is disabled",
                "name": "Not Implemented",
            },
        )

    def test_request_user_activity_summary(self):
        self.app.user_metrics_enabled = True
        self.app.user_metrics_store = mock.Mock()
        self._enable_custom_rules("user/analysis:view:self")
        self.app.user_metrics_store.user_activity_summary.return_value = {
            "username": "alice",
            "profile": {
                "fullname": "Alice Doe",
                "groups": ["users"],
                "ldap_synced_at": "2026-04-24T09:00:00+00:00",
                "ldap_found": True,
            },
            "generated_at": "2026-04-24T10:00:00+00:00",
            "totals": {
                "submitted_jobs_today": 3,
                "completed_jobs_today": 2,
                "active_tools": 1,
                "latest_submissions_per_minute": 1,
                "avg_max_memory_mb": 2048,
                "avg_cpu_cores": 4,
                "avg_runtime_seconds": 600,
                "busiest_tool": "blast",
                "busiest_tool_jobs": 2,
            },
            "tool_breakdown": [],
        }

        response = self.client.get(
            f"/v{get_version()}/user/{self.user.login}/activity/summary"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["username"], "alice")
        self.assertEqual(response.json["totals"]["submitted_jobs_today"], 3)
        self.app.user_metrics_store.user_activity_summary.assert_called_once_with(
            self.user.login
        )

    def test_request_user_activity_summary_error(self):
        self.app.user_metrics_enabled = True
        self.app.user_metrics_store = mock.Mock()
        self._enable_custom_rules("user/analysis:view:self")
        self.app.user_metrics_store.user_activity_summary.side_effect = RuntimeError(
            "boom"
        )

        with self.assertLogs("slurmweb", level="WARNING") as cm:
            response = self.client.get(
                f"/v{get_version()}/user/{self.user.login}/activity/summary"
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json,
            {
                "code": 500,
                "description": "boom",
                "name": "Internal Server Error",
            },
        )
        self.assertEqual(
            cm.output,
            [
                f"WARNING:slurmweb.views.agent:Unable to query user activity summary for {self.user.login}: boom"
            ],
        )
