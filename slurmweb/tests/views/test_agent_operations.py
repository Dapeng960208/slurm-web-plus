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

    def test_admin_system_instances_returns_empty_list_when_slurmdb_has_no_instances(self):
        self.setup_client()
        self._enable_self_rules("admin/system:view:*")
        self.app.slurmrestd.instances = mock.Mock(return_value=[])

        response = self.client.get(f"/v{get_version()}/admin/system/slurmdb/instances")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"instances": []})

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
