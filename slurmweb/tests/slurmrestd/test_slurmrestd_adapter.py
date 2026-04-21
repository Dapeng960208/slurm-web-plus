# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

import copy
import urllib

from slurmweb.slurmrestd import SlurmrestdAdapter
from slurmweb.slurmrestd.adapters import build_adaptation_chain
from slurmweb.slurmrestd.adapters.v0_0_39 import AdapterV0_0_39
from slurmweb.slurmrestd.adapters.v0_0_40 import AdapterV0_0_40
from ..lib.utils import all_slurm_api_versions
from ..lib.slurmrestd import TestSlurmrestdBase, basic_authentifier


class TestSlurmrestdAdapter(TestSlurmrestdBase):
    SUPPORTED_VERSIONS = [
        "0.0.44",
        "0.0.43",
        "0.0.42",
        "0.0.41",
        "0.0.40",
        "0.0.39",
    ]

    def setUp(self):
        # Use SlurmrestdAdapter with latest version as target
        self.slurmrestd = SlurmrestdAdapter(
            urllib.parse.urlparse("unix:///dev/null"),
            basic_authentifier(),
            self.SUPPORTED_VERSIONS,
            cluster_name_hint="atlas",
        )

    def setup_slurmrestd(self, slurm_version, api_version):
        super().setup_slurmrestd(slurm_version, api_version)
        # Force discovery to build adaptation chain
        self.slurmrestd.discover()

    def adapt(self, from_version, component, key, data, cluster_name_hint="atlas"):
        result = copy.deepcopy(data)
        for adapter in build_adaptation_chain(
            from_version,
            self.SUPPORTED_VERSIONS[0],
            self.SUPPORTED_VERSIONS,
            cluster_name_hint=cluster_name_hint,
        ):
            result = adapter.adapt(component, key, result)
        return result

    @all_slurm_api_versions
    def test_jobs(self, slurm_version, api_version):
        """Test that jobs() returns data with all expected fields after translation."""
        self.setup_slurmrestd(slurm_version, api_version)
        self.mock_slurmrestd_responses(
            slurm_version,
            api_version,
            [("slurm-jobs", "jobs")],
        )

        jobs = self.slurmrestd.jobs()

        # Check that jobs is a list
        self.assertIsInstance(jobs, list)
        self.assertGreater(len(jobs), 0)

        for job in jobs:
            # These fields should be present after AdapterV0_0_42 transformation
            self.assertIn("stderr_expanded", job)
            self.assertIn("stdin_expanded", job)
            self.assertIn("stdout_expanded", job)
            # Source fields should still be present
            self.assertIn("standard_error", job)
            self.assertIn("standard_input", job)
            self.assertIn("standard_output", job)

    @all_slurm_api_versions
    def test_qos(self, slurm_version, api_version):
        """Test that qos() returns data with all expected fields after translation."""
        self.setup_slurmrestd(slurm_version, api_version)
        self.mock_slurmrestd_responses(
            slurm_version,
            api_version,
            [("slurm-qos", "qos")],
        )

        qos_list = self.slurmrestd.qos()

        # Check that qos is a list
        self.assertIsInstance(qos_list, list)
        self.assertGreater(len(qos_list), 0)

        for qos in qos_list:
            # These fields should be present after AdapterV0_0_41 transformation
            self.assertIn("limits", qos)
            self.assertIn("max", qos["limits"])
            self.assertIn("count", qos["limits"]["max"]["jobs"])
            count = qos["limits"]["max"]["jobs"]["count"]
            self.assertIsInstance(count, dict)
            self.assertIn("infinite", count)
            self.assertIn("number", count)
            self.assertIn("set", count)

            self.assertIn("minutes", qos["limits"]["max"]["tres"])
            tres_minutes = qos["limits"]["max"]["tres"]["minutes"]
            self.assertIn("total", tres_minutes)
            self.assertIsInstance(tres_minutes["total"], list)

    @all_slurm_api_versions
    def test_job_slurmdb(self, slurm_version, api_version):
        """Test that slurmdb jobs have all expected fields after translation."""
        self.setup_slurmrestd(slurm_version, api_version)
        self.mock_slurmrestd_responses(
            slurm_version,
            api_version,
            [("slurmdb-job-running", "jobs")],
        )

        job = self.slurmrestd._acctjob(1)

        self.assertIsInstance(job["steps"], list)
        for step in job["steps"]:
            # These fields should be present after AdapterV0_0_42 transformation
            self.assertIn("step", step)
            self.assertIn("time", step)
            step_obj = step["step"]
            self.assertIn("stderr", step_obj)
            self.assertIn("stderr_expanded", step_obj)
            self.assertIn("stdin", step_obj)
            self.assertIn("stdin_expanded", step_obj)
            self.assertIn("stdout", step_obj)
            self.assertIn("stdout_expanded", step_obj)
            self.assertIn("limit", step["time"])
            limit = step["time"]["limit"]
            self.assertIsInstance(limit, dict)
            self.assertIn("set", limit)
            self.assertIn("infinite", limit)
            self.assertIn("number", limit)

    def test_adapter_v0_0_39_slurm_jobs_normalizes_legacy_fields(self):
        adapter = AdapterV0_0_39()
        data = [
            {
                "job_state": "RUNNING",
                "submit_time": 1710000000,
                "start_time": 1710000300,
                "end_time": 0,
                "eligible_time": 1710000200,
                "last_sched_evaluation": 1710000250,
                "exit_code": {
                    "status": "FAILED",
                    "return_code": 9,
                    "signal": {"signal_id": 15, "name": "TERM"},
                },
                "derived_exit_code": {
                    "status": "FAILED",
                    "return_code": 9,
                    "signal": {"signal_id": 0, "name": "NONE"},
                },
            }
        ]

        [job] = adapter.adapt("slurm", "jobs", data)

        self.assertEqual(job["job_state"], ["RUNNING"])
        self.assertEqual(job["submit_time"]["number"], 1710000000)
        self.assertTrue(job["submit_time"]["set"])
        self.assertEqual(job["last_sched_evaluation"]["number"], 1710000250)
        self.assertEqual(job["exit_code"]["status"], ["FAILED"])
        self.assertEqual(job["exit_code"]["return_code"]["number"], 9)
        self.assertEqual(job["exit_code"]["signal"]["id"]["number"], 15)
        self.assertEqual(job["derived_exit_code"]["signal"]["id"]["number"], 0)

    def test_adapter_v0_0_39_slurmdb_jobs_normalizes_steps_and_exit_codes(self):
        adapter = AdapterV0_0_39()
        data = [
            {
                "exit_code": {
                    "status": "FAILED",
                    "return_code": 9,
                    "signal": {"signal_id": 0, "name": "NONE"},
                },
                "derived_exit_code": {
                    "status": "FAILED",
                    "return_code": 9,
                    "signal": {"signal_id": 15, "name": "TERM"},
                },
                "steps": [
                    {
                        "state": "COMPLETED",
                        "exit_code": {
                            "status": "SUCCESS",
                            "return_code": 0,
                            "signal": {"signal_id": 0, "name": "NONE"},
                        },
                        "step": {
                            "id": {
                                "job_id": 321,
                                "step_id": 0,
                                "step_het_component": 99,
                            }
                        },
                    }
                ],
            }
        ]

        [job] = adapter.adapt("slurmdb", "jobs", data)

        self.assertEqual(job["exit_code"]["status"], ["FAILED"])
        self.assertEqual(job["derived_exit_code"]["signal"]["id"]["number"], 15)
        self.assertEqual(job["steps"][0]["state"], ["COMPLETED"])
        self.assertEqual(job["steps"][0]["exit_code"]["status"], ["SUCCESS"])
        self.assertEqual(job["steps"][0]["step"]["id"], "321.0")

    def test_adapter_v0_0_39_nodes_and_reservations_wrap_legacy_times(self):
        adapter = AdapterV0_0_39()
        nodes = [
            {
                "boot_time": 1700000000,
                "last_busy": 1700000100,
                "slurmd_start_time": 1700000200,
                "reason_changed_at": 1700000300,
                "cpu_load": 42,
            }
        ]
        reservations = [{"start_time": 1700000400, "end_time": 1700000500}]

        [node] = adapter.adapt("slurm", "nodes", nodes)
        [reservation] = adapter.adapt("slurm", "reservations", reservations)

        self.assertEqual(node["boot_time"]["number"], 1700000000)
        self.assertEqual(node["reason_changed_at"]["number"], 1700000300)
        self.assertEqual(node["cpu_load"], 42)
        self.assertEqual(reservation["start_time"]["number"], 1700000400)
        self.assertEqual(reservation["end_time"]["number"], 1700000500)

    def test_adapter_v0_0_39_associations_fill_object_id(self):
        adapter = AdapterV0_0_39(cluster_name_hint="atlas")
        data = [{"account": "science", "user": "alice"}]

        [association] = adapter.adapt("slurmdb", "associations", data)

        self.assertEqual(
            association["id"],
            {
                "account": "science",
                "cluster": "atlas",
                "partition": "",
                "user": "alice",
                "id": 0,
            },
        )

    def test_adapter_v0_0_40_slurmdb_jobs_backfill_top_level_fields(self):
        adapter = AdapterV0_0_40()
        data = [{"time": {"submission": 1710000000}, "steps": []}]

        [job] = adapter.adapt("slurmdb", "jobs", data)

        self.assertEqual(job["stdin"], "")
        self.assertEqual(job["stdout_expanded"], "")
        self.assertEqual(
            job["time"]["planned"],
            {"set": False, "infinite": False, "number": 0},
        )

    def test_adapter_v0_0_40_associations_flatten_id(self):
        adapter = AdapterV0_0_40()
        data = [
            {"id": {"account": "science", "cluster": "atlas", "user": "alice", "partition": "", "id": 17}}
        ]

        [association] = adapter.adapt("slurmdb", "associations", data)

        self.assertEqual(association["id"], 17)

    def test_chain_v0_0_39_slurmdb_jobs_reaches_v0_0_44_shape(self):
        data = [
            {
                "job_id": 321,
                "exit_code": {
                    "status": "FAILED",
                    "return_code": 9,
                    "signal": {"signal_id": 0, "name": "NONE"},
                },
                "time": {"submission": 1710000000},
                "steps": [
                    {
                        "state": "COMPLETED",
                        "exit_code": {
                            "status": "SUCCESS",
                            "return_code": 0,
                            "signal": {"signal_id": 0, "name": "NONE"},
                        },
                        "time": {},
                        "step": {
                            "id": {
                                "job_id": 321,
                                "step_id": 0,
                                "step_het_component": 7,
                            }
                        },
                    }
                ],
            }
        ]

        [job] = self.adapt("0.0.39", "slurmdb", "jobs", data)

        self.assertEqual(job["exit_code"]["status"], ["FAILED"])
        self.assertEqual(job["stdin"], "")
        self.assertEqual(job["stdout_expanded"], "")
        self.assertEqual(
            job["time"]["planned"],
            {"set": False, "infinite": False, "number": 0},
        )
        self.assertEqual(job["steps"][0]["state"], ["COMPLETED"])
        self.assertEqual(job["steps"][0]["step"]["id"], "321.0")
        self.assertEqual(job["steps"][0]["step"]["stdin_expanded"], "")
        self.assertEqual(
            job["steps"][0]["time"]["limit"],
            {"set": False, "infinite": True, "number": 0},
        )

    def test_chain_v0_0_40_slurmdb_jobs_reaches_v0_0_44_shape(self):
        data = [
            {
                "job_id": 654,
                "time": {"submission": 1711000000},
                "steps": [{"time": {}, "step": {}}],
            }
        ]

        [job] = self.adapt("0.0.40", "slurmdb", "jobs", data)

        self.assertEqual(job["stdin"], "")
        self.assertEqual(job["stderr_expanded"], "")
        self.assertEqual(
            job["time"]["planned"],
            {"set": False, "infinite": False, "number": 0},
        )
        self.assertEqual(job["steps"][0]["step"]["stdout"], "")
        self.assertEqual(
            job["steps"][0]["time"]["limit"],
            {"set": False, "infinite": True, "number": 0},
        )
