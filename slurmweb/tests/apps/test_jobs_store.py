# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from datetime import datetime, timezone
import json
import types
from unittest import mock
import unittest

from slurmweb.persistence.jobs_store import (
    JobsStore,
    _extract,
    _extract_detail,
    _max_memory_gb,
    _ts,
    normalize_history_exit_code,
)


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
                "exit_code": {
                    "return_code": {"set": True, "infinite": False, "number": 9},
                    "signal": {
                        "id": {"set": True, "infinite": False, "number": 0},
                        "name": "NONE",
                    },
                    "status": ["FAILED"],
                },
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
        self.assertEqual(
            json.loads(row["exit_code"]),
            {
                "return_code": {"set": True, "infinite": False, "number": 9},
                "signal": {
                    "id": {"set": True, "infinite": False, "number": 0},
                    "name": "NONE",
                },
                "status": ["FAILED"],
            },
        )
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
                "steps": [
                    {
                        "tres": {
                            "consumed": {
                                "max": [
                                    {
                                        "type": "mem",
                                        "count": 2 * 1024**3,
                                        "id": 2,
                                        "name": "",
                                    }
                                ]
                            }
                        }
                    }
                ],
                "working_directory": "/tmp/detail",
                "submit_line": "sleep 1",
                "exit_code": {
                    "return_code": {"set": True, "infinite": False, "number": 0},
                    "signal": {
                        "id": {"set": True, "infinite": False, "number": 0},
                        "name": "NONE",
                    },
                    "status": ["SUCCESS"],
                },
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
        self.assertEqual(
            json.loads(row["exit_code"]),
            {
                "return_code": {"set": True, "infinite": False, "number": 0},
                "signal": {
                    "id": {"set": True, "infinite": False, "number": 0},
                    "name": "NONE",
                },
                "status": ["SUCCESS"],
            },
        )
        self.assertEqual(len(row["tres_requested"]), 2)
        self.assertEqual(len(row["tres_allocated"]), 2)
        self.assertEqual(row["used_memory_gb"], 2.0)

    def test_extract_detail_ignores_step_total_memory_for_used_memory(self):
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

    def test_max_memory_gb_uses_max_mem_across_steps(self):
        result = _max_memory_gb(
            {
                "steps": [
                    {
                        "tres": {
                            "consumed": {
                                "max": [
                                    {"type": "cpu", "count": 32, "id": 1, "name": ""},
                                    {
                                        "type": "mem",
                                        "count": 2 * 1024**3,
                                        "id": 2,
                                        "name": "",
                                    },
                                ]
                            }
                        }
                    },
                    {
                        "tres": {
                            "consumed": {
                                "max": [
                                    {
                                        "type": "mem",
                                        "count": 5 * 1024**3,
                                        "id": 2,
                                        "name": "",
                                    }
                                ]
                            }
                        }
                    },
                ]
            }
        )

        self.assertEqual(result, 5.0)

    def test_max_memory_gb_returns_none_without_valid_mem_values(self):
        result = _max_memory_gb(
            {
                "steps": [
                    {"tres": {"consumed": {"max": []}}},
                    {
                        "tres": {
                            "consumed": {
                                "max": [
                                    {
                                        "type": "mem",
                                        "count": -1,
                                        "id": 2,
                                        "name": "",
                                    }
                                ]
                            }
                        }
                    },
                    {
                        "tres": {
                            "consumed": {
                                "max": [
                                    {
                                        "type": "mem",
                                        "count": {"set": False, "infinite": False, "number": 0},
                                        "id": 2,
                                        "name": "",
                                    }
                                ]
                            }
                        }
                    },
                ]
            }
        )

        self.assertIsNone(result)


class TestJobsStoreReconcile(unittest.TestCase):
    def setUp(self):
        self.slurmrestd = mock.Mock()
        self.store = JobsStore(settings=mock.Mock(), slurmrestd=self.slurmrestd)
        self.store._active_records = mock.Mock()

    def _pending_rows(self):
        return list(self.store._pending.values())

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
                            "max": [
                                {
                                    "type": "mem",
                                    "count": 2 * 1024**3,
                                    "id": 2,
                                    "name": "",
                                }
                            ]
                        }
                    }
                },
                {
                    "tres": {
                        "consumed": {
                            "max": [
                                {"type": "cpu", "count": 16, "id": 1, "name": ""},
                                {
                                    "type": "mem",
                                    "count": 3 * 1024**3,
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
        [pending_row] = self._pending_rows()
        self.assertEqual(pending_row["job_state"], "COMPLETED")
        self.assertEqual(
            pending_row["end_time"],
            datetime.fromtimestamp(1710000600, tz=timezone.utc),
        )
        self.assertEqual(pending_row["used_memory_gb"], 3.0)
        self.assertEqual(
            pending_row["eligible_time"],
            datetime.fromtimestamp(1710000200, tz=timezone.utc),
        )
        self.assertEqual(len(pending_row["tres_requested"]), 1)

    def test_reconcile_missing_job_marks_completed_when_lookup_not_found(self):
        self.store._active_records.return_value = [self._record()]
        self.slurmrestd.job.side_effect = SlurmrestdNotFoundError("missing")

        self.store._reconcile_missing_active_jobs([])

        self.assertEqual(len(self.store._pending), 1)
        [pending_row] = self._pending_rows()
        self.assertEqual(pending_row["job_state"], "COMPLETED")
        self.assertIsNotNone(pending_row["end_time"])
        self.assertEqual(
            pending_row["state_reason"],
            "Job missing from active queue and detail lookup",
        )

    def test_reconcile_does_not_touch_jobs_still_present_in_snapshot(self):
        record = self._record()
        self.store._active_records.return_value = [record]

        self.store._reconcile_missing_active_jobs(
            [{"job_id": record["job_id"], "submit_time": record["submit_time"]}]
        )

        self.slurmrestd.job.assert_not_called()
        self.assertEqual(self.store._pending, {})

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

    def test_query_searches_keyword_in_workdir_or_command(self):
        sql = self._run_query({"keyword": "sleep"})
        self.assertIn(
            "(COALESCE(js.working_directory, '') ILIKE %s OR COALESCE(js.command, '') ILIKE %s)",
            sql,
        )
        params = self.cursor.execute.call_args_list[1].args[1]
        self.assertEqual(params[:2], ["%sleep%", "%sleep%"])


class TestJobsStorePendingQueue(unittest.TestCase):
    def setUp(self):
        self.store = JobsStore(settings=mock.Mock(), slurmrestd=None)

    def _row(self, job_id=123, submit_ts=1710000000, job_state="PENDING"):
        return {
            "job_id": job_id,
            "job_name": f"job-{job_id}",
            "job_state": job_state,
            "state_reason": None,
            "user_name": "alice",
            "user_id": None,
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
            "tres_requested": None,
            "tres_allocated": None,
            "submit_time": datetime.fromtimestamp(submit_ts, tz=timezone.utc),
            "start_time": None,
            "end_time": None,
            "eligible_time": None,
            "last_sched_evaluation_time": None,
            "time_limit_minutes": 60,
            "used_memory_gb": None,
            "exit_code": "0:0",
            "working_directory": "/tmp/job",
            "command": "sleep 1",
        }

    def test_queue_rows_keeps_last_occurrence_for_same_job_and_submit_time(self):
        self.store._queue_rows(
            [
                self._row(job_state="PENDING"),
                self._row(job_state="RUNNING"),
            ]
        )

        self.assertEqual(len(self.store._pending), 1)
        [pending_row] = self.store._pending.values()
        self.assertEqual(pending_row["job_state"], "RUNNING")

    def test_queue_rows_keeps_distinct_submit_times_for_same_job(self):
        self.store._queue_rows(
            [
                self._row(submit_ts=1710000000),
                self._row(submit_ts=1710000060),
            ]
        )

        self.assertEqual(len(self.store._pending), 2)

    def test_flush_batches_unique_pending_rows_once(self):
        self.store._queue_rows(
            [
                self._row(job_state="PENDING"),
                self._row(job_state="RUNNING"),
                self._row(job_id=124, job_state="COMPLETED"),
            ]
        )
        self.store._flush_chunk = mock.Mock(return_value=[])

        self.store._flush()

        self.store._flush_chunk.assert_called_once()
        flushed_rows = self.store._flush_chunk.call_args.args[0]
        self.assertEqual(len(flushed_rows), 2)
        states = {row["job_id"]: row["job_state"] for row in flushed_rows}
        self.assertEqual(states[123], "RUNNING")
        self.assertEqual(states[124], "COMPLETED")
        self.assertEqual(self.store._pending, {})

    def test_flush_requeues_failed_rows_without_overwriting_newer_pending_rows(self):
        stale_row = self._row(job_state="PENDING")
        newer_row = self._row(job_state="RUNNING")
        self.store._queue_rows([stale_row])

        def flush_side_effect(chunk):
            self.store._queue_rows([newer_row])
            return [stale_row]

        self.store._flush_chunk = mock.Mock(side_effect=flush_side_effect)

        self.store._flush()

        self.assertEqual(len(self.store._pending), 1)
        self.assertEqual(
            self.store._pending[(123, stale_row["submit_time"])]["job_state"],
            "RUNNING",
        )

    def test_queue_rows_scales_with_unique_keys_under_repeated_submissions(self):
        repeated_rows = []
        for submit_offset in range(200):
            for state in ("PENDING", "RUNNING", "COMPLETED"):
                repeated_rows.append(
                    self._row(
                        job_id=1000 + submit_offset,
                        submit_ts=1710000000 + submit_offset,
                        job_state=state,
                    )
                )

        self.store._queue_rows(repeated_rows)

        self.assertEqual(len(self.store._pending), 200)
        self.assertTrue(
            all(row["job_state"] == "COMPLETED" for row in self.store._pending.values())
        )


class TestHistoryExitCodeNormalization(unittest.TestCase):
    def test_normalize_history_exit_code_from_legacy_string(self):
        result = normalize_history_exit_code("0:0")
        self.assertEqual(result["return_code"]["number"], 0)
        self.assertEqual(result["signal"]["id"]["number"], 0)
        self.assertEqual(result["status"], ["SUCCESS"])

    def test_normalize_history_exit_code_from_json_string(self):
        result = normalize_history_exit_code(
            json.dumps(
                {
                    "return_code": {"set": True, "infinite": False, "number": 9},
                    "signal": {
                        "id": {"set": True, "infinite": False, "number": 0},
                        "name": "NONE",
                    },
                    "status": ["FAILED"],
                }
            )
        )
        self.assertEqual(result["return_code"]["number"], 9)
        self.assertEqual(result["signal"]["id"]["number"], 0)
        self.assertEqual(result["status"], ["FAILED"])
