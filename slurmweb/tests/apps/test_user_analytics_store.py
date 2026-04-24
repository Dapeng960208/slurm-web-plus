# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
import os
import tempfile
import types
import unittest
from unittest import mock

from slurmweb.persistence.user_analytics_store import (
    _aggregate_rows,
    normalize_tool_name,
    ToolNameMapper,
    UserAnalyticsStore,
)


class TestUserMetricsToolName(unittest.TestCase):
    def test_normalize_tool_name_prefers_job_name(self):
        self.assertEqual(
            normalize_tool_name(job_name="AlphaTool batch", command="/opt/bin/blastp -db nr"),
            "alphatool",
        )

    def test_normalize_tool_name_falls_back_to_command(self):
        self.assertEqual(
            normalize_tool_name(job_name=None, command="/opt/app/bin/blastp --db nr"),
            "blastp",
        )

    def test_normalize_tool_name_falls_back_to_submit_line(self):
        self.assertEqual(
            normalize_tool_name(job_name="", command=None, submit_line="/work/run/rnaseq.py --input a"),
            "rnaseq",
        )

    def test_tool_mapping_file_overrides_defaults(self):
        with tempfile.NamedTemporaryFile("w+", suffix=".yml", delete=False) as fh:
            fh.write("- pattern: '^alphatool$'\n  tool: 'pipeline'\n")
            fh.flush()
            path = fh.name
        try:
            mapper = ToolNameMapper(path)
            self.assertEqual(
                mapper.classify(job_name="AlphaTool run", command="blastp"),
                "pipeline",
            )
        finally:
            os.unlink(path)

    def test_normalize_tool_name_unknown(self):
        self.assertEqual(normalize_tool_name(None, None, None), "unknown")


class TestUserMetricsAggregation(unittest.TestCase):
    def test_aggregate_rows(self):
        rows = [
            {
                "job_name": "rna-seq",
                "command": "python /apps/rna_seq.py",
                "submit_line": None,
                "used_memory_gb": 8.0,
                "used_cpu_cores_avg": 4.0,
                "start_time": datetime(2026, 4, 24, 1, 0, tzinfo=timezone.utc),
                "end_time": datetime(2026, 4, 24, 2, 0, tzinfo=timezone.utc),
                "usage_stats": None,
            },
            {
                "job_name": "rna-seq",
                "command": "python /apps/rna_seq.py",
                "submit_line": None,
                "used_memory_gb": 12.0,
                "used_cpu_cores_avg": 6.0,
                "start_time": datetime(2026, 4, 24, 3, 0, tzinfo=timezone.utc),
                "end_time": datetime(2026, 4, 24, 4, 30, tzinfo=timezone.utc),
                "usage_stats": None,
            },
            {
                "job_name": "blast",
                "command": "blastp --db nr",
                "submit_line": None,
                "used_memory_gb": 20.0,
                "used_cpu_cores_avg": 8.0,
                "start_time": datetime(2026, 4, 24, 5, 0, tzinfo=timezone.utc),
                "end_time": datetime(2026, 4, 24, 5, 30, tzinfo=timezone.utc),
                "usage_stats": None,
            },
        ]

        result = _aggregate_rows(rows)

        self.assertEqual(result["totals"]["completed_jobs_today"], 3)
        self.assertEqual(result["totals"]["active_tools"], 2)
        self.assertEqual(result["totals"]["busiest_tool"], "rna-seq")
        self.assertEqual(result["totals"]["busiest_tool_jobs"], 2)
        self.assertAlmostEqual(result["totals"]["avg_max_memory_mb"], (40.0 / 3.0) * 1024.0)
        self.assertAlmostEqual(result["totals"]["avg_cpu_cores"], 6.0)
        self.assertAlmostEqual(
            result["totals"]["avg_runtime_seconds"], (3600 + 5400 + 1800) / 3.0
        )
        self.assertEqual(result["tool_breakdown"][0]["tool"], "rna-seq")
        self.assertEqual(result["tool_breakdown"][0]["jobs"], 2)


class TestUserMetricsTimeline(unittest.TestCase):
    def test_align_bucket(self):
        store = UserAnalyticsStore(settings=SimpleNamespace())
        timestamp = datetime(2026, 4, 24, 12, 34, 56, tzinfo=timezone.utc)

        self.assertEqual(
            store._align_bucket(timestamp, timedelta(minutes=1)),
            datetime(2026, 4, 24, 12, 34, tzinfo=timezone.utc),
        )
        self.assertEqual(
            store._align_bucket(timestamp, timedelta(hours=1)),
            datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(
            store._align_bucket(timestamp, timedelta(days=1)),
            datetime(2026, 4, 24, 0, 0, tzinfo=timezone.utc),
        )

    def test_user_activity_summary_includes_profile(self):
        settings = SimpleNamespace(aggregation_interval=3600, tool_mapping_file=None)
        users_store = mock.Mock()
        users_store.get_ldap_user.return_value = {
            "username": "alice",
            "fullname": "Alice Doe",
            "groups": ["users"],
            "ldap_synced_at": datetime(2026, 4, 24, 9, 0, tzinfo=timezone.utc),
        }
        store = UserAnalyticsStore(settings=settings, users_store=users_store)
        store._completed_jobs_rows = mock.Mock(
            return_value=[
                {
                    "job_name": "blast",
                    "command": "blastp",
                    "submit_line": None,
                    "used_memory_gb": 2.0,
                    "used_cpu_cores_avg": 4.0,
                    "start_time": datetime(2026, 4, 24, 8, 0, tzinfo=timezone.utc),
                    "end_time": datetime(2026, 4, 24, 8, 30, tzinfo=timezone.utc),
                    "usage_stats": None,
                }
            ]
        )
        store._submitted_jobs_today = mock.Mock(return_value=3)
        store.latest_submission_count = mock.Mock(return_value=1)

        result = store.user_activity_summary("alice")

        self.assertEqual(result["profile"]["fullname"], "Alice Doe")
        self.assertEqual(result["profile"]["groups"], ["users"])
        self.assertTrue(result["profile"]["ldap_found"])
        self.assertEqual(result["totals"]["submitted_jobs_today"], 3)
        self.assertEqual(result["totals"]["completed_jobs_today"], 1)
        self.assertEqual(result["tool_breakdown"][0]["tool"], "blast")


class TestUserMetricsQueries(unittest.TestCase):
    def setUp(self):
        self.store = UserAnalyticsStore(settings=SimpleNamespace(tool_mapping_file=None))
        self.conn = mock.Mock()
        self.cursor = mock.Mock()
        self.cursor.fetchall.return_value = []
        self.cursor_cm = mock.MagicMock()
        self.cursor_cm.__enter__.return_value = self.cursor
        self.conn.cursor.return_value = self.cursor_cm
        self.store._get_conn = mock.Mock(return_value=self.conn)
        self.store._release_conn = mock.Mock()
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

    def test_completed_jobs_query_does_not_select_submit_line(self):
        self.store._completed_jobs_rows("alice", date(2026, 4, 24))

        sql = self.cursor.execute.call_args.args[0]
        self.assertNotIn("js.submit_line", sql)
        self.assertIn("js.command", sql)

    def test_current_day_query_does_not_select_submit_line(self):
        self.store._current_day_completed_rows()

        sql = self.cursor.execute.call_args.args[0]
        self.assertNotIn("js.submit_line", sql)
        self.assertIn("js.command", sql)

    def test_refresh_current_day_summary_handles_rows_without_submit_line(self):
        self.store._current_day_completed_rows = mock.Mock(
            return_value=[
                {
                    "activity_date": date(2026, 4, 24),
                    "user_id": 1,
                    "job_name": "",
                    "command": "/opt/app/bin/blastp --db nr",
                    "used_memory_gb": 4.0,
                    "used_cpu_cores_avg": 2.0,
                    "start_time": datetime(2026, 4, 24, 8, 0, tzinfo=timezone.utc),
                    "end_time": datetime(2026, 4, 24, 8, 15, tzinfo=timezone.utc),
                    "last_seen": datetime(2026, 4, 24, 8, 15, tzinfo=timezone.utc),
                    "usage_stats": None,
                }
            ]
        )
        self.store._upsert_current_day_summary = mock.Mock()

        self.store.refresh_current_day_summary()

        payload = self.store._upsert_current_day_summary.call_args.args[0]
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["tool"], "blastp")
        self.assertEqual(payload[0]["jobs_count"], 1)
