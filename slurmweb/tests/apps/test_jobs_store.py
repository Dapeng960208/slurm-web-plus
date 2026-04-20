# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from datetime import datetime, timezone
import types
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
                "eligible_time": {"set": True, "infinite": False, "number": 1710000200},
                "start_time": {"set": True, "infinite": False, "number": 1710000300},
                "last_sched_evaluation": {
                    "set": True,
                    "infinite": False,
                    "number": 1710000250,
                },
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
        self.assertEqual(
            row["eligible_time"], datetime.fromtimestamp(1710000200, tz=timezone.utc)
        )
        self.assertEqual(
            row["last_sched_evaluation_time"],
            datetime.fromtimestamp(1710000250, tz=timezone.utc),
        )
        self.assertIsNone(row["end_time"])
        self.assertEqual(row["node_count"], 2)
        self.assertEqual(row["cpus"], 48)
        self.assertEqual(row["priority"], 100)
        self.assertEqual(row["time_limit_minutes"], 120)
        self.assertIsNone(row["tres_requested"])
        self.assertIsNone(row["tres_allocated"])
        self.assertIsNone(row["used_memory_gb"])

    def test_extract_detail_maps_merged_job_fields(self):
        row = _extract_detail(
            {
                "job_id": 123,
                "name": "detail-job",
                "association": {"account": "science", "user": "alice"},
                "group_name": "research",
                "partition": "normal",
                "qos": "debug",
                "nodes": "cn1",
                "node_count": {"set": True, "infinite": False, "number": 0},
                "cpus": {"set": True, "infinite": False, "number": 0},
                "priority": {"set": True, "infinite": False, "number": 42},
                "tres_req_str": "cpu=0",
                "state": {"current": ["RUNNING", "COMPLETING"], "reason": "None"},
                "last_sched_evaluation": {
                    "set": True,
                    "infinite": False,
                    "number": 1710000280,
                },
                "tres": {
                    "requested": [
                        {"type": "cpu", "count": 0, "id": 1, "name": ""},
                        {"type": "mem", "count": 0, "id": 2, "name": ""},
                    ],
                    "allocated": [
                        {"type": "cpu", "count": 0, "id": 1, "name": ""},
                        {"type": "mem", "count": 0, "id": 2, "name": ""},
                    ],
                },
                "time": {
                    "submission": 1710000000,
                    "eligible": 1710000200,
                    "start": 1710000300,
                    "end": 0,
                    "limit": {"set": True, "infinite": False, "number": 0},
                },
                "working_directory": "/tmp/detail",
                "submit_line": "sleep 1",
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
            row["eligible_time"], datetime.fromtimestamp(1710000200, tz=timezone.utc)
        )
        self.assertEqual(
            row["start_time"], datetime.fromtimestamp(1710000300, tz=timezone.utc)
        )
        self.assertEqual(
            row["last_sched_evaluation_time"],
            datetime.fromtimestamp(1710000280, tz=timezone.utc),
        )
        self.assertIsNone(row["end_time"])
        self.assertEqual(row["working_directory"], "/tmp/detail")
        self.assertEqual(row["command"], "sleep 1")
        self.assertEqual(len(row["tres_requested"]), 2)
        self.assertEqual(len(row["tres_allocated"]), 2)
        self.assertIsNone(row["used_memory_gb"])

    def test_extract_detail_does_not_record_step_memory_as_used_memory(self):
        row = _extract_detail(
            {
                "job_id": 123,
                "state": {"current": ["COMPLETED"], "reason": "None"},
                "time": {"submission": 1710000000, "end": 1710000900},
                "steps": [
                    {},
                    {
                        "tres": {
                            "consumed": {
                                "total": {"count": 4 * 1024**2}
                            }
                        }
                    },
                    {
                        "tres": {
                            "consumed": {
                                "total": [
                                    {"type": "cpu", "count": 32, "id": 1, "name": ""},
                                    {
                                        "type": "mem",
                                        "count": 5 * 1024**2,
                                        "id": 2,
                                        "name": "",
                                    },
                                ]
                            }
                        }
                    }
                ],
            }
        )

        self.assertIsNone(row["used_memory_gb"])


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
            "eligible_time": datetime.fromtimestamp(1710000200, tz=timezone.utc),
            "last_sched_evaluation_time": datetime.fromtimestamp(
                1710000250, tz=timezone.utc
            ),
            "time_limit_minutes": 60,
            "tres_requested": None,
            "tres_allocated": None,
            "used_memory_gb": None,
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
            "tres": {
                "requested": [{"type": "cpu", "count": 16, "id": 1, "name": ""}],
                "allocated": [{"type": "cpu", "count": 16, "id": 1, "name": ""}],
            },
            "time": {
                "submission": 1710000000,
                "eligible": 1710000200,
                "start": 1710000300,
                "end": 1710000600,
                "limit": {"set": True, "infinite": False, "number": 60},
            },
            "steps": [
                {},
                {
                    "tres": {
                        "consumed": {
                            "total": {"count": 2 * 1024**2}
                        }
                    }
                },
                {
                    "tres": {
                        "consumed": {
                            "total": [
                                {"type": "cpu", "count": 16, "id": 1, "name": ""},
                                {
                                    "type": "mem",
                                    "count": 3 * 1024**2,
                                    "id": 2,
                                    "name": "",
                                },
                            ]
                        }
                    }
                }
            ],
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
        self.assertIsNone(self.store._pending[0]["used_memory_gb"])
        self.assertEqual(
            self.store._pending[0]["eligible_time"],
            datetime.fromtimestamp(1710000200, tz=timezone.utc),
        )
        self.assertEqual(len(self.store._pending[0]["tres_requested"]), 1)

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

    def test_needs_detail_enrichment_ignores_used_memory_for_completed_jobs(self):
        running_record = self._record()
        running_record.update(
            {
                "tres_requested": [],
                "tres_allocated": [],
            }
        )
        self.assertFalse(self.store._needs_detail_enrichment(running_record))

        completed_record = self._record()
        completed_record.update(
            {
                "job_state": "COMPLETED",
                "tres_requested": [],
                "tres_allocated": [],
            }
        )
        self.assertFalse(self.store._needs_detail_enrichment(completed_record))


class TestJobsStoreQuerySorting(unittest.TestCase):
    def setUp(self):
        self.store = JobsStore(settings=mock.Mock(), slurmrestd=None)
        self.conn = mock.Mock()
        self.cursor = mock.Mock()
        self.cursor_cm = mock.MagicMock()
        self.cursor_cm.__enter__.return_value = self.cursor
        self.conn.cursor.return_value = self.cursor_cm
        self.store._get_conn = mock.Mock(return_value=self.conn)
        self.store._release_conn = mock.Mock()
        self.cursor.fetchone.return_value = {"count": 0}
        self.cursor.fetchall.return_value = []
        self.psycopg2_patcher = mock.patch.dict(
            "sys.modules",
            {
                "psycopg2": types.SimpleNamespace(
                    extras=types.SimpleNamespace(RealDictCursor=object)
                ),
                "psycopg2.extras": types.SimpleNamespace(RealDictCursor=object),
            },
        )
        self.psycopg2_patcher.start()

    def tearDown(self):
        self.psycopg2_patcher.stop()

    def _run_query(self, filters):
        self.cursor.execute.reset_mock()
        self.store.query(filters)
        return self.cursor.execute.call_args_list[1].args[0]

    def test_query_uses_submit_time_desc_by_default(self):
        sql = self._run_query({})
        self.assertIn(
            "ORDER BY js.submit_time DESC NULLS LAST, js.job_id DESC LIMIT %s OFFSET %s",
            sql,
        )

    def test_query_supports_scalar_history_sort_fields(self):
        cases = {
            ("id", "asc"): "ORDER BY js.job_id ASC NULLS FIRST LIMIT %s OFFSET %s",
            ("state", "desc"): "ORDER BY js.job_state DESC NULLS LAST, js.job_id DESC LIMIT %s OFFSET %s",
            ("user", "asc"): "ORDER BY u.username ASC NULLS FIRST, js.job_id ASC LIMIT %s OFFSET %s",
            ("priority", "desc"): "ORDER BY js.priority DESC NULLS LAST, js.job_id DESC LIMIT %s OFFSET %s",
        }

        for (sort, order), expected in cases.items():
            with self.subTest(sort=sort, order=order):
                sql = self._run_query({"sort": sort, "order": order})
                self.assertIn(expected, sql)

    def test_query_sorts_resources_by_nodes_then_cpus(self):
        sql = self._run_query({"sort": "resources", "order": "asc"})
        self.assertIn(
            "ORDER BY js.node_count ASC NULLS FIRST, js.cpus ASC NULLS FIRST, js.job_id ASC LIMIT %s OFFSET %s",
            sql,
        )
