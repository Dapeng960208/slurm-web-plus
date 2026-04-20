# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from datetime import datetime, timezone
from unittest import mock
import unittest

from slurmweb.persistence.jobs_store import JobsStore, _extract, _extract_detail, _ts


class SlurmrestdNotFoundError(Exception):
    pass


class TestJobsStoreExtract(unittest.TestCase):
    def test_ts_accepts_optional_number_dict(self):
        value = {"set": True, "infinite": False, "number": 1710000000}
        result = _ts(value)
        self.assertEqual(
            result, datetime.fromtimestamp(1710000000, tz=timezone.utc)
        )

    def test_ts_returns_none_for_unset_optional_number_dict(self):
        value = {"set": False, "infinite": True, "number": 0}
        self.assertIsNone(_ts(value))

    def test_extract_handles_object_times_and_optional_numbers(self):
        row = _extract(
            {
                "job_id": 123,
                "name": "test",
                "job_state": ["RUNNING"],
                "submit_time": {"set": True, "infinite": False, "number": 1710000000},
                "start_time": {"set": True, "infinite": False, "number": 1710000300},
                "end_time": {"set": False, "infinite": True, "number": 0},
                "node_count": {"set": True, "infinite": False, "number": 2},
                "cpus": {"set": True, "infinite": False, "number": 48},
                "priority": {"set": True, "infinite": False, "number": 100},
                "time_limit": {"set": True, "infinite": False, "number": 120},
            }
        )

        self.assertEqual(row["job_id"], 123)
        self.assertEqual(
            row["submit_time"], datetime.fromtimestamp(1710000000, tz=timezone.utc)
        )
        self.assertEqual(
            row["start_time"], datetime.fromtimestamp(1710000300, tz=timezone.utc)
        )
        self.assertIsNone(row["end_time"])
        self.assertEqual(row["node_count"], 2)
        self.assertEqual(row["cpus"], 48)
        self.assertEqual(row["priority"], 100)
        self.assertEqual(row["time_limit_minutes"], 120)

    def test_extract_detail_maps_merged_job_fields(self):
        row = _extract_detail(
            {
                "job_id": 123,
                "name": "detail-job",
                "user": "alice",
                "group": "research",
                "association": {"account": "science"},
                "partition": "normal",
                "qos": "debug",
                "nodes": "cn1",
                "node_count": {"set": True, "infinite": False, "number": 0},
                "cpus": {"set": True, "infinite": False, "number": 0},
                "priority": {"set": True, "infinite": False, "number": 42},
                "tres_req_str": "cpu=0",
                "state": {"current": ["RUNNING", "COMPLETING"], "reason": "None"},
                "time": {
                    "submission": 1710000000,
                    "start": 1710000300,
                    "end": 0,
                    "limit": {"set": True, "infinite": False, "number": 0},
                },
                "working_directory": "/tmp/detail",
                "command": "sleep 1",
            }
        )

        self.assertEqual(row["job_state"], "RUNNING,COMPLETING")
        self.assertEqual(row["user_name"], "alice")
        self.assertEqual(row["account"], "science")
        self.assertEqual(row["group"], "research")
        self.assertEqual(row["priority"], 42)
        self.assertEqual(row["node_count"], 0)
        self.assertEqual(row["cpus"], 0)
        self.assertEqual(row["time_limit_minutes"], 0)
        self.assertEqual(
            row["submit_time"], datetime.fromtimestamp(1710000000, tz=timezone.utc)
        )
        self.assertEqual(
            row["start_time"], datetime.fromtimestamp(1710000300, tz=timezone.utc)
        )
        self.assertIsNone(row["end_time"])
        self.assertEqual(row["working_directory"], "/tmp/detail")
        self.assertEqual(row["command"], "sleep 1")


class TestJobsStoreReconcile(unittest.TestCase):
    def setUp(self):
        self.slurmrestd = mock.Mock()
        self.store = JobsStore(settings=mock.Mock(), slurmrestd=self.slurmrestd)
        self.store._active_records = mock.Mock()

    def _record(self):
        return {
            "id": 1,
            "job_id": 123,
            "submit_time": datetime.fromtimestamp(1710000000, tz=timezone.utc),
            "first_seen": datetime.fromtimestamp(1710000000, tz=timezone.utc),
            "snapshot_time": datetime.fromtimestamp(1710000900, tz=timezone.utc),
            "job_name": "history-job",
            "job_state": "RUNNING",
            "state_reason": None,
            "user_id": 7,
            "user_name": "alice",
            "account": "science",
            "group": "research",
            "partition": "normal",
            "qos": "debug",
            "nodes": "cn1",
            "node_count": 1,
            "cpus": 16,
            "priority": 100,
            "tres_req_str": "cpu=16",
            "tres_per_job": None,
            "tres_per_node": None,
            "gres_detail": None,
            "start_time": datetime.fromtimestamp(1710000300, tz=timezone.utc),
            "end_time": None,
            "time_limit_minutes": 60,
            "exit_code": "0:0",
            "working_directory": "/tmp/job",
            "command": "sleep 1",
        }

    def test_reconcile_missing_job_updates_with_detail_lookup(self):
        self.store._active_records.return_value = [self._record()]
        self.slurmrestd.job.return_value = {
            "job_id": 123,
            "name": "history-job",
            "user": "alice",
            "group": "research",
            "association": {"account": "science"},
            "partition": "normal",
            "qos": "debug",
            "nodes": "cn1",
            "node_count": {"set": True, "infinite": False, "number": 1},
            "cpus": {"set": True, "infinite": False, "number": 16},
            "priority": {"set": True, "infinite": False, "number": 100},
            "state": {"current": ["COMPLETED"], "reason": "None"},
            "time": {
                "submission": 1710000000,
                "start": 1710000300,
                "end": 1710000600,
                "limit": {"set": True, "infinite": False, "number": 60},
            },
            "working_directory": "/tmp/job",
            "command": "sleep 1",
        }

        self.store._reconcile_missing_active_jobs([])

        self.assertEqual(len(self.store._pending), 1)
        self.assertEqual(self.store._pending[0]["job_state"], "COMPLETED")
        self.assertEqual(
            self.store._pending[0]["end_time"],
            datetime.fromtimestamp(1710000600, tz=timezone.utc),
        )

    def test_reconcile_missing_job_marks_completed_when_lookup_not_found(self):
        self.store._active_records.return_value = [self._record()]
        self.slurmrestd.job.side_effect = SlurmrestdNotFoundError("missing")

        self.store._reconcile_missing_active_jobs([])

        self.assertEqual(len(self.store._pending), 1)
        self.assertEqual(self.store._pending[0]["job_state"], "COMPLETED")
        self.assertIsNotNone(self.store._pending[0]["end_time"])
        self.assertEqual(
            self.store._pending[0]["state_reason"],
            "Job missing from active queue and detail lookup",
        )

    def test_reconcile_does_not_touch_jobs_still_present_in_snapshot(self):
        record = self._record()
        self.store._active_records.return_value = [record]

        self.store._reconcile_missing_active_jobs(
            [{"job_id": record["job_id"], "submit_time": record["submit_time"]}]
        )

        self.slurmrestd.job.assert_not_called()
        self.assertEqual(self.store._pending, [])
