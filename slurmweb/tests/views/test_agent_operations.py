# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from unittest import mock

from slurmweb.version import get_version

from ..lib.agent import TestAgentBase


class TestAgentOperations(TestAgentBase):
    def _set_supported_write_version(self):
        self.app.slurmrestd.cluster_name = "foo"
        self.app.slurmrestd.slurm_version = "25.11.0"
        self.app.slurmrestd.api_version = "0.0.44"

    def _enable_self_rules(self, *rules):
        self.app.access_control_enabled = True
        self.app.access_control_store = mock.Mock()
        self.app.access_control_store.user_permissions.return_value = ([], [], list(rules))
        self.app.policy._access_control_enabled = True
        self.app.policy.set_access_control_store(self.app.access_control_store)

    def test_analysis_ping(self):
        self.setup_client()
        self.app.slurmrestd.ping_data = mock.Mock(
            return_value=[{"hostname": "admin", "responding": True}]
        )

        response = self.client.get(f"/v{get_version()}/analysis/ping")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["pings"][0]["hostname"], "admin")

    def test_analysis_diag(self):
        self.setup_client()
        self.app.slurmrestd.diag = mock.Mock(return_value={"parts_packed": 1})

        response = self.client.get(f"/v{get_version()}/analysis/diag")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["statistics"]["parts_packed"], 1)

    def test_analysis_node_hotspots(self):
        self.setup_client(node_metrics=True)
        self.app.settings.node_metrics.node_hostname_label = "instance"
        self.app.slurmrestd.nodes = mock.Mock(
            return_value=[{"name": "cn1"}, {"name": "cn2"}]
        )
        self.app.node_metrics_db.cluster_node_hotspots = mock.Mock(
            return_value={
                "window": {
                    "start": "2026-04-21T00:00:00+00:00",
                    "end": "2026-04-24T00:00:00+00:00",
                },
                "threshold": 80,
                "events": [
                    {
                        "node": "cn1",
                        "metric": "cpu",
                        "start": "2026-04-23T09:00:00+00:00",
                        "end": "2026-04-23T09:20:00+00:00",
                        "duration_seconds": 1200,
                        "peak_usage": 93,
                    }
                ],
            }
        )

        response = self.client.get(
            f"/v{get_version()}/analysis/node-hotspots?start=2026-04-21T00:00:00Z&end=2026-04-24T00:00:00Z"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["events"][0]["node"], "cn1")
        args, _ = self.app.node_metrics_db.cluster_node_hotspots.call_args
        self.assertEqual(args[1], "instance")

    def test_analysis_node_hotspots_requires_window(self):
        self.setup_client(node_metrics=True)

        response = self.client.get(f"/v{get_version()}/analysis/node-hotspots")

        self.assertEqual(response.status_code, 400)
        if response.json is not None:
            self.assertEqual(response.json["description"], "start and end must both be provided")
        else:
            self.assertIn("start and end must both be provided", response.text)

    def test_admin_system_route_removed(self):
        self.setup_client()

        response = self.client.get(f"/v{get_version()}/admin/system/slurmdb/instances")

        self.assertEqual(response.status_code, 404)

    def test_job_cancel_self_allows_owner(self):
        self.setup_client()
        self._set_supported_write_version()
        self._enable_self_rules("jobs:delete:self")
        self.app.slurmrestd.job = mock.Mock(
            return_value={"job_id": 101, "user_name": "test", "state": {"current": ["RUNNING"]}}
        )
        self.app.slurmrestd.job_cancel = mock.Mock(
            return_value={"warnings": [], "errors": [], "job_id": 101}
        )

        response = self.client.delete(
            f"/v{get_version()}/job/101/cancel",
            json={"signal": "TERM"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["supported"])
        self.assertEqual(response.json["operation"], "jobs.cancel")
        self.app.slurmrestd.job_cancel.assert_called_once_with(101, {"signal": "TERM"})

    def test_job_cancel_self_denies_other_user(self):
        self.setup_client()
        self._set_supported_write_version()
        self._enable_self_rules("jobs:delete:self")
        self.app.slurmrestd.job = mock.Mock(
            return_value={"job_id": 202, "user_name": "other", "state": {"current": ["RUNNING"]}}
        )

        response = self.client.delete(f"/v{get_version()}/job/202/cancel")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json["description"], "Access not permitted")

    def test_jobs_view_self_filters_to_current_user(self):
        self.setup_client()
        self._enable_self_rules("jobs:view:self")
        self.app.slurmrestd.jobs = mock.Mock(
            return_value=[
                {"job_id": 101, "user_name": "test"},
                {"job_id": 102, "user_name": "other"},
            ]
        )

        response = self.client.get(f"/v{get_version()}/jobs")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, [{"job_id": 101, "user_name": "test"}])
        self.app.slurmrestd.jobs.assert_called_once_with(query={"user": "test"})

    def test_job_view_self_denies_other_user(self):
        self.setup_client()
        self._enable_self_rules("jobs:view:self")
        self.app.slurmrestd.job = mock.Mock(return_value={"job_id": 202, "user_name": "other"})

        response = self.client.get(f"/v{get_version()}/job/202")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json["description"], "Access not permitted")

    def test_job_submit_returns_not_implemented_on_old_api(self):
        self.setup_client()
        self._enable_self_rules("jobs:edit:self")
        self.app.slurmrestd.cluster_name = "foo"
        self.app.slurmrestd.slurm_version = "23.02.0"
        self.app.slurmrestd.api_version = "0.0.40"

        response = self.client.post(
            f"/v{get_version()}/jobs/submit",
            json={"script": "#!/bin/bash\nhostname\n"},
        )

        self.assertEqual(response.status_code, 501)
        self.assertFalse(response.json["supported"])

    def test_accounts_update_accepts_light_payload(self):
        self.setup_client()
        self._set_supported_write_version()
        self._enable_self_rules("accounts:edit:*")
        self.app.slurmrestd.accounts_update = mock.Mock(
            return_value={"warnings": [], "errors": [], "accounts": []}
        )

        response = self.client.post(
            f"/v{get_version()}/accounts",
            json={"name": "science", "description": "Science"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["operation"], "accounts.update")
        self.app.slurmrestd.accounts_update.assert_called_once_with(
            {"name": "science", "description": "Science"}
        )
