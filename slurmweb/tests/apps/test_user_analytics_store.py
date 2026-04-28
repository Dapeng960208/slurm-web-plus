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
    _aggregate_daily_stat_rows,
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

        self.assertEqual(result["totals"]["completed_jobs"], 3)
        self.assertEqual(result["totals"]["active_tools"], 2)
        self.assertEqual(result["totals"]["busiest_tool"], "rna-seq")
        self.assertEqual(result["totals"]["busiest_tool_jobs"], 2)
        self.assertAlmostEqual(result["totals"]["avg_max_memory_mb"], (40.0 / 3.0) * 1024.0)
        self.assertAlmostEqual(result["totals"]["avg_max_memory_gb"], 40.0 / 3.0)
        self.assertAlmostEqual(result["totals"]["avg_cpu_cores"], 6.0)
        self.assertAlmostEqual(
            result["totals"]["avg_runtime_hours"], ((3600 + 5400 + 1800) / 3.0) / 3600.0
        )
        self.assertAlmostEqual(
            result["totals"]["avg_runtime_seconds"], (3600 + 5400 + 1800) / 3.0
        )
        self.assertEqual(result["tool_breakdown"][0]["tool"], "rna-seq")
        self.assertEqual(result["tool_breakdown"][0]["jobs"], 2)
        self.assertAlmostEqual(result["tool_breakdown"][0]["avg_max_memory_gb"], 10.0)
        self.assertAlmostEqual(result["tool_breakdown"][0]["avg_runtime_hours"], 1.25)

    def test_aggregate_rows_accepts_legacy_singular_cpu_key(self):
        result = _aggregate_rows(
            [
                {
                    "job_name": "blast",
                    "command": "blastp",
                    "submit_line": None,
                    "used_memory_gb": 2.0,
                    "used_cpu_core_avg": 3.5,
                    "start_time": datetime(2026, 4, 24, 1, 0, tzinfo=timezone.utc),
                    "end_time": datetime(2026, 4, 24, 3, 0, tzinfo=timezone.utc),
                    "usage_stats": None,
                }
            ]
        )

        self.assertEqual(result["totals"]["completed_jobs"], 1)
        self.assertEqual(result["totals"]["avg_cpu_cores"], 3.5)
        self.assertEqual(result["totals"]["avg_runtime_hours"], 2.0)

    def test_aggregate_rows_falls_back_to_usage_stats_memory_and_cpu(self):
        result = _aggregate_rows(
            [
                {
                    "job_name": "blast",
                    "command": "blastp",
                    "submit_line": None,
                    "used_memory_gb": None,
                    "used_cpu_cores_avg": None,
                    "start_time": datetime(2026, 4, 24, 1, 0, tzinfo=timezone.utc),
                    "end_time": datetime(2026, 4, 24, 3, 0, tzinfo=timezone.utc),
                    "usage_stats": {
                        "memory": {"value_gb": 12.5, "source": "consumed.max.mem"},
                        "cpu": {
                            "estimated_cores_avg": 6.25,
                            "job_elapsed_seconds": 7200,
                        },
                    },
                }
            ]
        )

        self.assertEqual(result["totals"]["completed_jobs"], 1)
        self.assertEqual(result["totals"]["avg_max_memory_gb"], 12.5)
        self.assertEqual(result["totals"]["avg_max_memory_mb"], 12.5 * 1024.0)
        self.assertEqual(result["totals"]["avg_cpu_cores"], 6.25)
        self.assertEqual(result["tool_breakdown"][0]["avg_max_memory_gb"], 12.5)
        self.assertEqual(result["tool_breakdown"][0]["avg_cpu_cores"], 6.25)

    def test_aggregate_daily_stat_rows_weights_persisted_tool_stats(self):
        result = _aggregate_daily_stat_rows(
            [
                ("blast", 2, 4.0, 8.0, 3600.0, 2, 2, 2),
                ("blast", 1, 10.0, 2.0, 7200.0, 1, 1, 1),
                ("bwa", 1, None, None, None, 0, 0, 0),
            ]
        )

        self.assertEqual(result["totals"]["completed_jobs"], 4)
        self.assertEqual(result["totals"]["active_tools"], 2)
        self.assertEqual(result["totals"]["busiest_tool"], "blast")
        self.assertAlmostEqual(result["tool_breakdown"][0]["avg_max_memory_gb"], 6.0)
        self.assertAlmostEqual(result["tool_breakdown"][0]["avg_cpu_cores"], 6.0)
        self.assertAlmostEqual(result["tool_breakdown"][0]["avg_runtime_hours"], 1.3333333333333333)


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

    def test_user_tool_analysis_includes_profile(self):
        settings = SimpleNamespace(aggregation_interval=3600, tool_mapping_file=None)
        users_store = mock.Mock()
        users_store.get_ldap_user.return_value = {
            "username": "alice",
            "fullname": "Alice Doe",
            "groups": ["users"],
            "ldap_synced_at": datetime(2026, 4, 24, 9, 0, tzinfo=timezone.utc),
        }
        store = UserAnalyticsStore(settings=settings, users_store=users_store)
        store._refresh_user_tool_daily_stats = mock.Mock()
        store._user_tool_daily_summary = mock.Mock(
            return_value={
                "totals": {
                    "completed_jobs": 1,
                    "active_tools": 1,
                    "avg_max_memory_gb": 2.0,
                    "avg_max_memory_mb": 2048.0,
                    "avg_cpu_cores": 4.0,
                    "avg_runtime_hours": 0.5,
                    "avg_runtime_seconds": 1800.0,
                    "busiest_tool": "blast",
                    "busiest_tool_jobs": 1,
                },
                "tool_breakdown": [
                    {
                        "tool": "blast",
                        "jobs": 1,
                        "avg_max_memory_gb": 2.0,
                        "avg_max_memory_mb": 2048.0,
                        "avg_cpu_cores": 4.0,
                        "avg_runtime_hours": 0.5,
                        "avg_runtime_seconds": 1800.0,
                    }
                ],
            }
        )

        result = store.user_tool_analysis(
            "alice",
            start_time=datetime(2026, 4, 24, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(result["profile"]["fullname"], "Alice Doe")
        self.assertEqual(result["profile"]["groups"], ["users"])
        self.assertTrue(result["profile"]["ldap_found"])
        self.assertEqual(result["totals"]["completed_jobs"], 1)
        self.assertEqual(result["tool_breakdown"][0]["tool"], "blast")
        self.assertEqual(result["window"]["start"], "2026-04-24T00:00:00+00:00")
        store._refresh_user_tool_daily_stats.assert_called_once_with(
            "alice",
            date(2026, 4, 24),
            date(2026, 4, 24),
        )
        store._user_tool_daily_summary.assert_called_once_with(
            "alice",
            date(2026, 4, 24),
            date(2026, 4, 24),
        )


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

    def test_refresh_current_day_summary_uses_usage_stats_resource_fallback(self):
        self.store._current_day_completed_rows = mock.Mock(
            return_value=[
                {
                    "activity_date": date(2026, 4, 24),
                    "user_id": 1,
                    "job_name": "blast",
                    "command": "blastp",
                    "used_memory_gb": None,
                    "used_cpu_cores_avg": None,
                    "start_time": datetime(2026, 4, 24, 8, 0, tzinfo=timezone.utc),
                    "end_time": datetime(2026, 4, 24, 9, 0, tzinfo=timezone.utc),
                    "last_seen": datetime(2026, 4, 24, 9, 0, tzinfo=timezone.utc),
                    "usage_stats": {
                        "memory": {"value_gb": "16.0"},
                        "cpu": {"estimated_cores_avg": "8.0"},
                    },
                }
            ]
        )
        self.store._upsert_current_day_summary = mock.Mock()

        self.store.refresh_current_day_summary()

        payload = self.store._upsert_current_day_summary.call_args.args[0]
        self.assertEqual(payload[0]["avg_max_memory_gb"], 16.0)
        self.assertEqual(payload[0]["avg_cpu_cores"], 8.0)
        self.assertEqual(payload[0]["memory_samples"], 1)
        self.assertEqual(payload[0]["cpu_samples"], 1)

    def test_refresh_user_tool_daily_stats_replaces_persisted_rows(self):
        self.store._completed_jobs_rows_for_activity_dates = mock.Mock(
            return_value=[
                {
                    "activity_date": date(2026, 4, 24),
                    "user_id": 1,
                    "job_name": "blast",
                    "command": "blastp",
                    "used_memory_gb": 10.0,
                    "used_cpu_cores_avg": 5.0,
                    "start_time": datetime(2026, 4, 24, 8, 0, tzinfo=timezone.utc),
                    "end_time": datetime(2026, 4, 24, 10, 0, tzinfo=timezone.utc),
                    "last_seen": datetime(2026, 4, 24, 10, 0, tzinfo=timezone.utc),
                    "usage_stats": None,
                }
            ]
        )
        self.store._replace_user_tool_daily_stats = mock.Mock()

        self.store._refresh_user_tool_daily_stats(
            "alice",
            date(2026, 4, 24),
            date(2026, 4, 24),
        )

        payload = self.store._replace_user_tool_daily_stats.call_args.args[3]
        self.assertEqual(payload[0]["tool"], "blast")
        self.assertEqual(payload[0]["jobs_count"], 1)
        self.assertEqual(payload[0]["avg_max_memory_gb"], 10.0)
        self.assertEqual(payload[0]["avg_cpu_cores"], 5.0)
        self.assertEqual(payload[0]["memory_samples"], 1)
        self.assertEqual(payload[0]["cpu_samples"], 1)
        self.assertEqual(payload[0]["runtime_samples"], 1)

    def test_user_tool_daily_summary_reads_persisted_table(self):
        self.cursor.fetchall.return_value = [
            ("blast", 2, 4.0, 8.0, 3600.0, 2, 2, 2),
            ("blast", 1, 10.0, 2.0, 7200.0, 1, 1, 1),
        ]

        result = self.store._user_tool_daily_summary(
            "alice",
            date(2026, 4, 24),
            date(2026, 4, 25),
        )

        sql = self.cursor.execute.call_args.args[0]
        params = self.cursor.execute.call_args.args[1]
        self.assertIn("FROM user_tool_daily_stats uds", sql)
        self.assertEqual(params, ("alice", date(2026, 4, 24), date(2026, 4, 25)))
        self.assertEqual(result["totals"]["completed_jobs"], 3)
        self.assertAlmostEqual(result["totals"]["avg_max_memory_gb"], 6.0)
        self.assertAlmostEqual(result["totals"]["avg_cpu_cores"], 6.0)

    def test_completed_jobs_window_query_filters_by_time_range(self):
        start_time = datetime(2026, 4, 24, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)

        self.store._completed_jobs_rows_window("alice", start_time, end_time)

        sql = self.cursor.execute.call_args.args[0]
        params = self.cursor.execute.call_args.args[1]
        self.assertIn("COALESCE(js.end_time, js.last_seen) >= %s", sql)
        self.assertIn("COALESCE(js.end_time, js.last_seen) <= %s", sql)
        self.assertEqual(params[0], "alice")
        self.assertEqual(params[1], start_time)
        self.assertEqual(params[2], end_time)
        self.assertIn("UPPER(js.job_state) LIKE %s", sql)

    def test_submission_timeline_uses_fallback_time_when_submit_time_missing(self):
        start_time = datetime(2026, 4, 24, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2026, 4, 24, 3, 0, tzinfo=timezone.utc)

        self.store.submission_timeline("alice", start_time=start_time, end_time=end_time)

        sql = self.cursor.execute.call_args.args[0]
        self.assertIn("COALESCE(js.submit_time, js.start_time, js.last_seen) >= %s", sql)
        self.assertIn("COALESCE(js.submit_time, js.start_time, js.last_seen) <= %s", sql)
        self.assertIn(
            "date_trunc(%s, COALESCE(js.submit_time, js.start_time, js.last_seen) AT TIME ZONE 'UTC')",
            sql,
        )

    def test_completion_timeline_uses_utc_bucket(self):
        start_time = datetime(2026, 4, 24, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2026, 4, 24, 3, 0, tzinfo=timezone.utc)

        self.store.completion_timeline("alice", start_time=start_time, end_time=end_time)

        sql = self.cursor.execute.call_args.args[0]
        self.assertIn(
            "date_trunc(%s, COALESCE(js.end_time, js.last_seen) AT TIME ZONE 'UTC')",
            sql,
        )

    def test_user_metrics_history_seven_day_window_matches_naive_utc_buckets(self):
        start_time = datetime(2026, 4, 17, 12, 30, tzinfo=timezone.utc)
        end_time = datetime(2026, 4, 24, 12, 30, tzinfo=timezone.utc)
        submission_bucket = datetime(2026, 4, 18)
        completion_bucket = datetime(2026, 4, 19)
        self.cursor.fetchall.side_effect = [
            [(submission_bucket, 3)],
            [(completion_bucket, 2)],
        ]

        result = self.store.user_metrics_history(
            "alice",
            start_time=start_time,
            end_time=end_time,
        )

        submission_bucket_ms = int(
            datetime(2026, 4, 18, tzinfo=timezone.utc).timestamp() * 1000
        )
        completion_bucket_ms = int(
            datetime(2026, 4, 19, tzinfo=timezone.utc).timestamp() * 1000
        )
        self.assertEqual(result["totals"]["submitted_jobs"], 3)
        self.assertEqual(result["totals"]["completed_jobs"], 2)
        self.assertIn([submission_bucket_ms, 3], result["submissions"])
        self.assertIn([completion_bucket_ms, 2], result["completions"])
        submission_sql = self.cursor.execute.call_args_list[0].args[0]
        completion_sql = self.cursor.execute.call_args_list[1].args[0]
        self.assertIn("AT TIME ZONE 'UTC'", submission_sql)
        self.assertIn("AT TIME ZONE 'UTC'", completion_sql)

    def test_completion_timeline_matches_terminal_states_case_insensitively(self):
        start_time = datetime(2026, 4, 24, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2026, 4, 24, 3, 0, tzinfo=timezone.utc)

        self.store.completion_timeline("alice", start_time=start_time, end_time=end_time)

        sql = self.cursor.execute.call_args.args[0]
        self.assertIn("UPPER(js.job_state) LIKE %s", sql)
