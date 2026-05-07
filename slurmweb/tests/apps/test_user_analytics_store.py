# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
import os
from pathlib import Path
import re
import tempfile
import types
import unittest
from unittest import mock

from slurmweb.persistence.user_analytics_store import (
    _aggregate_daily_stat_rows,
    _aggregate_rows,
    aggregate_user_tool_daily_rows,
    normalize_tool_name,
    ToolNameMapper,
    UserAnalyticsStore,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


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
        self.assertAlmostEqual(result["totals"]["avg_memory_gb"], 40.0 / 3.0)
        self.assertAlmostEqual(result["totals"]["avg_max_memory_gb"], 40.0 / 3.0)
        self.assertAlmostEqual(result["totals"]["max_memory_gb"], 20.0)
        self.assertAlmostEqual(result["totals"]["median_memory_gb"], 12.0)
        self.assertAlmostEqual(result["totals"]["avg_cpu_cores"], 6.0)
        self.assertAlmostEqual(
            result["totals"]["avg_runtime_hours"], ((3600 + 5400 + 1800) / 3.0) / 3600.0
        )
        self.assertAlmostEqual(
            result["totals"]["avg_runtime_seconds"], (3600 + 5400 + 1800) / 3.0
        )
        self.assertEqual(result["tool_breakdown"][0]["tool"], "rna-seq")
        self.assertEqual(result["tool_breakdown"][0]["jobs"], 2)
        self.assertAlmostEqual(result["tool_breakdown"][0]["avg_memory_gb"], 10.0)
        self.assertAlmostEqual(result["tool_breakdown"][0]["avg_max_memory_gb"], 10.0)
        self.assertAlmostEqual(result["tool_breakdown"][0]["max_memory_gb"], 12.0)
        self.assertAlmostEqual(result["tool_breakdown"][0]["median_memory_gb"], 10.0)
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
        self.assertIsNone(result["totals"]["avg_cpu_cores"])
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

        self.assertEqual(result["totals"]["completed_jobs"], 0)
        self.assertIsNone(result["totals"]["avg_memory_gb"])
        self.assertIsNone(result["totals"]["avg_max_memory_gb"])
        self.assertEqual(result["tool_breakdown"], [])

    def test_daily_aggregation_collapses_regr_tools_like_rebuild_script(self):
        rows = [
            {
                "activity_date": date(2026, 4, 24),
                "user_id": 1,
                "job_name": "regr_foo",
                "command": "python task.py",
                "submit_line": None,
                "used_memory_gb": 8.0,
                "used_cpu_cores_avg": 2.0,
                "start_time": datetime(2026, 4, 24, 1, 0, tzinfo=timezone.utc),
                "end_time": datetime(2026, 4, 24, 2, 0, tzinfo=timezone.utc),
                "usage_stats": None,
            },
            {
                "activity_date": date(2026, 4, 24),
                "user_id": 1,
                "job_name": "regr-bar",
                "command": "python task.py",
                "submit_line": None,
                "used_memory_gb": None,
                "used_cpu_cores_avg": None,
                "start_time": datetime(2026, 4, 24, 2, 0, tzinfo=timezone.utc),
                "end_time": datetime(2026, 4, 24, 4, 0, tzinfo=timezone.utc),
                "usage_stats": None,
            },
        ]

        payload, stats = aggregate_user_tool_daily_rows(
            rows,
            ToolNameMapper(),
            raw_mapper=ToolNameMapper(),
            rewrite_pattern=re.compile(r"^regr([_-].*)?$"),
            rewrite_tool="regr",
        )

        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["tool"], "regr")
        self.assertEqual(payload[0]["jobs_count"], 1)
        self.assertEqual(payload[0]["avg_memory_gb"], 8.0)
        self.assertEqual(payload[0]["max_memory_gb"], 8.0)
        self.assertEqual(payload[0]["median_memory_gb"], 8.0)
        self.assertEqual(payload[0]["avg_cpu_cores"], 2.0)
        self.assertEqual(stats["rows_counted"], 1)

    def test_daily_aggregation_counts_jobs_with_used_memory_gb_and_skips_null(self):
        rows = [
            {
                "activity_date": date(2026, 4, 24),
                "user_id": 1,
                "job_name": "blast",
                "command": "blastp",
                "used_memory_gb": 4.0,
                "used_cpu_cores_avg": 2.0,
                "start_time": datetime(2026, 4, 24, 8, 0, tzinfo=timezone.utc),
                "end_time": datetime(2026, 4, 24, 9, 0, tzinfo=timezone.utc),
                "usage_stats": None,
            },
            {
                "activity_date": date(2026, 4, 24),
                "user_id": 1,
                "job_name": "blast",
                "command": "blastp",
                "used_memory_gb": 0.0,
                "used_cpu_cores_avg": 0.0,
                "start_time": datetime(2026, 4, 24, 10, 0, tzinfo=timezone.utc),
                "end_time": datetime(2026, 4, 24, 11, 0, tzinfo=timezone.utc),
                "usage_stats": None,
            },
            {
                "activity_date": date(2026, 4, 24),
                "user_id": 1,
                "job_name": "blast",
                "command": "blastp",
                "used_memory_gb": -1.0,
                "used_cpu_cores_avg": -2.0,
                "start_time": datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc),
                "end_time": datetime(2026, 4, 24, 13, 0, tzinfo=timezone.utc),
                "usage_stats": {
                    "memory": {"value_gb": 100.0},
                    "cpu": {"estimated_cores_avg": 50.0},
                },
            },
            {
                "activity_date": date(2026, 4, 24),
                "user_id": 1,
                "job_name": "blast",
                "command": "blastp",
                "used_memory_gb": 8.0,
                "used_cpu_cores_avg": None,
                "start_time": datetime(2026, 4, 24, 13, 0, tzinfo=timezone.utc),
                "end_time": datetime(2026, 4, 24, 14, 0, tzinfo=timezone.utc),
                "usage_stats": None,
            },
            {
                "activity_date": date(2026, 4, 24),
                "user_id": 1,
                "job_name": "blast",
                "command": "blastp",
                "used_memory_gb": None,
                "used_cpu_cores_avg": 4.0,
                "start_time": datetime(2026, 4, 24, 14, 0, tzinfo=timezone.utc),
                "end_time": datetime(2026, 4, 24, 15, 0, tzinfo=timezone.utc),
                "usage_stats": None,
            },
            {
                "activity_date": date(2026, 4, 24),
                "user_id": 2,
                "job_name": "blast",
                "command": "blastp",
                "used_memory_gb": None,
                "used_cpu_cores_avg": None,
                "start_time": datetime(2026, 4, 24, 14, 0, tzinfo=timezone.utc),
                "end_time": datetime(2026, 4, 24, 15, 0, tzinfo=timezone.utc),
                "usage_stats": {
                    "memory": {"value_gb": 100.0},
                    "cpu": {"estimated_cores_avg": 50.0},
                },
            },
        ]

        payload, stats = aggregate_user_tool_daily_rows(rows, ToolNameMapper())
        payload = sorted(payload, key=lambda item: item["user_id"])

        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["user_id"], 1)
        self.assertEqual(payload[0]["jobs_count"], 4)
        self.assertEqual(payload[0]["avg_memory_gb"], 2.75)
        self.assertEqual(payload[0]["max_memory_gb"], 8.0)
        self.assertEqual(payload[0]["median_memory_gb"], 2.0)
        self.assertEqual(payload[0]["avg_cpu_cores"], 0.5)
        self.assertEqual(stats["rows_counted"], 4)
        self.assertEqual(stats["cpu_missing"], 3)
        self.assertEqual(stats["rows_skipped_memory"], 2)

    def test_daily_aggregation_skips_rows_when_used_memory_gb_is_missing(self):
        rows = [
            {
                "activity_date": date(2026, 4, 24),
                "user_id": 1,
                "job_name": "blast",
                "command": "blastp",
                "used_memory_gb": None,
                "used_cpu_cores_avg": 2.0,
                "start_time": datetime(2026, 4, 24, 8, 0, tzinfo=timezone.utc),
                "end_time": datetime(2026, 4, 24, 9, 0, tzinfo=timezone.utc),
                "usage_stats": {"memory": {"value_gb": 4.0}},
            },
            {
                "activity_date": date(2026, 4, 24),
                "user_id": 1,
                "job_name": "blast",
                "command": "blastp",
                "used_memory_gb": None,
                "used_cpu_cores_avg": None,
                "start_time": datetime(2026, 4, 24, 10, 0, tzinfo=timezone.utc),
                "end_time": datetime(2026, 4, 24, 11, 0, tzinfo=timezone.utc),
                "usage_stats": None,
            },
            {
                "activity_date": date(2026, 4, 24),
                "user_id": 1,
                "job_name": "blast",
                "command": "blastp",
                "used_memory_gb": None,
                "used_cpu_cores_avg": 1.0,
                "start_time": datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc),
                "end_time": datetime(2026, 4, 24, 14, 0, tzinfo=timezone.utc),
                "usage_stats": None,
            },
        ]

        payload, stats = aggregate_user_tool_daily_rows(rows, ToolNameMapper())

        self.assertEqual(payload, [])
        self.assertEqual(stats["rows_counted"], 0)
        self.assertEqual(stats["rows_skipped_memory"], 3)
        self.assertEqual(stats["cpu_missing"], 0)

    def test_daily_aggregation_skips_only_rows_without_used_memory_gb(self):
        rows = [
            {
                "activity_date": date(2026, 4, 24),
                "user_id": 1,
                "job_name": "blast",
                "command": "blastp",
                "used_memory_gb": 0.0,
                "used_cpu_cores_avg": 2.0,
                "start_time": datetime(2026, 4, 24, 8, 0, tzinfo=timezone.utc),
                "end_time": datetime(2026, 4, 24, 9, 0, tzinfo=timezone.utc),
                "usage_stats": None,
            },
            {
                "activity_date": date(2026, 4, 24),
                "user_id": 1,
                "job_name": "blast",
                "command": "blastp",
                "used_memory_gb": 4.0,
                "used_cpu_cores_avg": 0.0,
                "start_time": datetime(2026, 4, 24, 10, 0, tzinfo=timezone.utc),
                "end_time": datetime(2026, 4, 24, 11, 0, tzinfo=timezone.utc),
                "usage_stats": None,
            },
            {
                "activity_date": date(2026, 4, 24),
                "user_id": 1,
                "job_name": "blast",
                "command": "blastp",
                "used_memory_gb": None,
                "used_cpu_cores_avg": None,
                "start_time": datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc),
                "end_time": datetime(2026, 4, 24, 13, 0, tzinfo=timezone.utc),
                "usage_stats": None,
            },
            {
                "activity_date": date(2026, 4, 24),
                "user_id": 1,
                "job_name": "blast",
                "command": "blastp",
                "used_memory_gb": -1.0,
                "used_cpu_cores_avg": -2.0,
                "start_time": datetime(2026, 4, 24, 14, 0, tzinfo=timezone.utc),
                "end_time": datetime(2026, 4, 24, 15, 0, tzinfo=timezone.utc),
                "usage_stats": None,
            },
        ]

        payload, stats = aggregate_user_tool_daily_rows(rows, ToolNameMapper())
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["jobs_count"], 3)
        self.assertEqual(payload[0]["avg_memory_gb"], 1.0)
        self.assertEqual(payload[0]["max_memory_gb"], 4.0)
        self.assertEqual(payload[0]["median_memory_gb"], 0.0)
        self.assertEqual(payload[0]["avg_cpu_cores"], 0.67)
        self.assertEqual(stats["rows_skipped_memory"], 1)
        self.assertEqual(stats["cpu_missing"], 2)

    def test_daily_aggregation_rounds_persisted_metrics_to_two_decimals(self):
        rows = [
            {
                "activity_date": date(2026, 4, 24),
                "user_id": 1,
                "job_name": "blast",
                "command": "blastp",
                "used_memory_gb": 1.111,
                "used_cpu_cores_avg": 2.555,
                "start_time": datetime(2026, 4, 24, 8, 0, tzinfo=timezone.utc),
                "end_time": datetime(2026, 4, 24, 9, 0, tzinfo=timezone.utc),
                "usage_stats": None,
            },
            {
                "activity_date": date(2026, 4, 24),
                "user_id": 1,
                "job_name": "blast",
                "command": "blastp",
                "used_memory_gb": 2.225,
                "used_cpu_cores_avg": 2.555,
                "start_time": datetime(2026, 4, 24, 9, 0, tzinfo=timezone.utc),
                "end_time": datetime(2026, 4, 24, 10, 1, 1, tzinfo=timezone.utc),
                "usage_stats": None,
            },
        ]

        payload, stats = aggregate_user_tool_daily_rows(rows, ToolNameMapper())

        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["jobs_count"], 2)
        self.assertEqual(payload[0]["avg_memory_gb"], 1.67)
        self.assertEqual(payload[0]["max_memory_gb"], 2.23)
        self.assertEqual(payload[0]["median_memory_gb"], 1.67)
        self.assertEqual(payload[0]["avg_cpu_cores"], 2.56)
        self.assertEqual(payload[0]["avg_runtime_seconds"], 3630.5)
        self.assertEqual(stats["rows_counted"], 2)

    def test_daily_aggregation_counts_high_precision_used_memory_gb(self):
        rows = [
            {
                "activity_date": date(2026, 4, 24),
                "user_id": 1,
                "job_name": "blast",
                "command": "blastp",
                "used_memory_gb": 3.2000000001,
                "used_cpu_cores_avg": 2.0,
                "start_time": datetime(2026, 4, 24, 8, 0, tzinfo=timezone.utc),
                "end_time": datetime(2026, 4, 24, 9, 0, tzinfo=timezone.utc),
                "usage_stats": None,
            }
        ]

        payload, stats = aggregate_user_tool_daily_rows(rows, ToolNameMapper())

        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["jobs_count"], 1)
        self.assertEqual(payload[0]["avg_memory_gb"], 3.2)
        self.assertEqual(payload[0]["max_memory_gb"], 3.2)
        self.assertEqual(payload[0]["median_memory_gb"], 3.2)
        self.assertEqual(stats["rows_counted"], 1)
        self.assertEqual(stats["rows_skipped_memory"], 0)

    def test_daily_aggregation_uses_jobs_count_for_cpu_and_runtime_averages(self):
        rows = [
            {
                "activity_date": date(2026, 4, 24),
                "user_id": 1,
                "job_name": "blast",
                "command": "blastp",
                "used_memory_gb": 4.0,
                "used_cpu_cores_avg": 4.0,
                "start_time": datetime(2026, 4, 24, 8, 0, tzinfo=timezone.utc),
                "end_time": datetime(2026, 4, 24, 9, 0, tzinfo=timezone.utc),
                "usage_stats": None,
            },
            {
                "activity_date": date(2026, 4, 24),
                "user_id": 1,
                "job_name": "blast",
                "command": "blastp",
                "used_memory_gb": 8.0,
                "used_cpu_cores_avg": None,
                "start_time": None,
                "end_time": None,
                "usage_stats": None,
            },
        ]

        payload, stats = aggregate_user_tool_daily_rows(rows, ToolNameMapper())

        self.assertEqual(payload[0]["jobs_count"], 2)
        self.assertEqual(payload[0]["avg_cpu_cores"], 2.0)
        self.assertEqual(payload[0]["avg_runtime_seconds"], 1800.0)
        self.assertEqual(stats["cpu_missing"], 1)
        self.assertEqual(stats["runtime_missing"], 1)

    def test_daily_aggregation_counts_only_positive_memory_jobs_in_large_completed_day(self):
        rows = []
        for index in range(1000):
            rows.append(
                {
                    "activity_date": date(2026, 4, 24),
                    "user_id": 1,
                    "job_name": "blast",
                    "command": "blastp",
                    "used_memory_gb": 4.0 if index < 50 else None,
                    "used_cpu_cores_avg": 2.0 if index < 50 else None,
                    "start_time": datetime(2026, 4, 24, 8, 0, tzinfo=timezone.utc),
                    "end_time": datetime(2026, 4, 24, 9, 0, tzinfo=timezone.utc),
                    "usage_stats": None,
                }
            )

        payload, stats = aggregate_user_tool_daily_rows(rows, ToolNameMapper())

        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["jobs_count"], 50)
        self.assertEqual(payload[0]["avg_memory_gb"], 4.0)
        self.assertEqual(payload[0]["max_memory_gb"], 4.0)
        self.assertEqual(payload[0]["median_memory_gb"], 4.0)
        self.assertEqual(payload[0]["avg_cpu_cores"], 2.0)
        self.assertEqual(stats["rows_counted"], 50)
        self.assertEqual(stats["rows_skipped_memory"], 950)

    def test_aggregate_daily_stat_rows_weights_persisted_tool_stats_by_jobs(self):
        result = _aggregate_daily_stat_rows(
            [
                ("blast", 2, 4.0, 8.0, 3600.0, 1, 1, 2),
                ("blast", 1, 10.0, 2.0, 7200.0, 99, 99, 1),
                ("bwa", 1, None, None, None, 0, 0, 0),
            ]
        )

        self.assertEqual(result["totals"]["completed_jobs"], 4)
        self.assertEqual(result["totals"]["active_tools"], 2)
        self.assertEqual(result["totals"]["busiest_tool"], "blast")
        self.assertAlmostEqual(result["tool_breakdown"][0]["avg_memory_gb"], 6.0)
        self.assertAlmostEqual(result["tool_breakdown"][0]["avg_max_memory_gb"], 6.0)
        self.assertAlmostEqual(result["tool_breakdown"][0]["max_memory_gb"], 10.0)
        self.assertAlmostEqual(result["tool_breakdown"][0]["median_memory_gb"], 6.0)
        self.assertAlmostEqual(result["tool_breakdown"][0]["avg_cpu_cores"], 6.0)
        self.assertAlmostEqual(result["totals"]["avg_memory_gb"], 6.0)
        self.assertAlmostEqual(result["totals"]["avg_max_memory_gb"], 6.0)
        self.assertAlmostEqual(result["totals"]["max_memory_gb"], 10.0)
        self.assertAlmostEqual(result["totals"]["median_memory_gb"], 6.0)
        self.assertAlmostEqual(result["totals"]["avg_cpu_cores"], 6.0)
        self.assertAlmostEqual(result["tool_breakdown"][0]["avg_runtime_hours"], 1.3333333333333333)

    def test_aggregate_daily_stat_rows_skips_rows_without_positive_resource_pair(self):
        result = _aggregate_daily_stat_rows(
            [
                ("blast", 2, 4.0, 8.0, 3600.0, 2, 2, 2),
                ("blast", 3, 0.0, 0.0, 1800.0, 0, 0, 3),
            ]
        )

        self.assertEqual(result["totals"]["completed_jobs"], 5)
        self.assertAlmostEqual(result["tool_breakdown"][0]["avg_memory_gb"], 4.0)
        self.assertAlmostEqual(result["tool_breakdown"][0]["avg_max_memory_gb"], 4.0)
        self.assertAlmostEqual(result["tool_breakdown"][0]["max_memory_gb"], 4.0)
        self.assertAlmostEqual(result["tool_breakdown"][0]["median_memory_gb"], 4.0)
        self.assertAlmostEqual(result["tool_breakdown"][0]["avg_cpu_cores"], 8.0)
        self.assertAlmostEqual(result["totals"]["avg_memory_gb"], 4.0)
        self.assertAlmostEqual(result["totals"]["avg_max_memory_gb"], 4.0)
        self.assertAlmostEqual(result["totals"]["max_memory_gb"], 4.0)
        self.assertAlmostEqual(result["totals"]["median_memory_gb"], 4.0)
        self.assertAlmostEqual(result["totals"]["avg_cpu_cores"], 8.0)

    def test_aggregate_daily_stat_rows_keeps_positive_memory_rows_without_cpu(self):
        result = _aggregate_daily_stat_rows(
            [
                ("blast", 2, 4.0, None, 3600.0, 2, 0, 2),
                ("blast", 1, 10.0, 2.0, 7200.0, 1, 1, 1),
            ]
        )

        self.assertEqual(result["totals"]["completed_jobs"], 3)
        self.assertAlmostEqual(result["tool_breakdown"][0]["avg_memory_gb"], 6.0)
        self.assertAlmostEqual(result["tool_breakdown"][0]["avg_max_memory_gb"], 6.0)
        self.assertAlmostEqual(result["tool_breakdown"][0]["max_memory_gb"], 10.0)
        self.assertAlmostEqual(result["tool_breakdown"][0]["median_memory_gb"], 6.0)
        self.assertAlmostEqual(result["tool_breakdown"][0]["avg_cpu_cores"], 2.0)
        self.assertAlmostEqual(result["totals"]["avg_memory_gb"], 6.0)
        self.assertAlmostEqual(result["totals"]["avg_max_memory_gb"], 6.0)
        self.assertAlmostEqual(result["totals"]["max_memory_gb"], 10.0)
        self.assertAlmostEqual(result["totals"]["median_memory_gb"], 6.0)
        self.assertAlmostEqual(result["totals"]["avg_cpu_cores"], 2.0)

    def test_aggregate_daily_stat_rows_uses_jobs_weight_for_legacy_rows_without_samples(self):
        result = _aggregate_daily_stat_rows(
            [
                ("blast", 2, 4.0, 8.0, 3600.0, 0, 0, 2),
                ("blast", 1, 10.0, 2.0, 7200.0, 0, 0, 1),
            ]
        )

        self.assertAlmostEqual(result["tool_breakdown"][0]["avg_memory_gb"], 6.0)
        self.assertAlmostEqual(result["tool_breakdown"][0]["avg_max_memory_gb"], 6.0)
        self.assertAlmostEqual(result["tool_breakdown"][0]["max_memory_gb"], 10.0)
        self.assertAlmostEqual(result["tool_breakdown"][0]["median_memory_gb"], 6.0)
        self.assertAlmostEqual(result["tool_breakdown"][0]["avg_cpu_cores"], 6.0)
        self.assertAlmostEqual(result["totals"]["avg_memory_gb"], 6.0)
        self.assertAlmostEqual(result["totals"]["avg_max_memory_gb"], 6.0)
        self.assertAlmostEqual(result["totals"]["max_memory_gb"], 10.0)
        self.assertAlmostEqual(result["totals"]["median_memory_gb"], 6.0)
        self.assertAlmostEqual(result["totals"]["avg_cpu_cores"], 6.0)

    def test_aggregate_daily_stat_rows_drops_old_zero_rows_from_completed_jobs(self):
        result = _aggregate_daily_stat_rows(
            [
                ("blast", 2, 0.0, 8.0, 3600.0, 2, 2, 2),
                ("blast", 1, 4.0, 0.0, 1800.0, 1, 1, 1),
                ("blast", 3, None, None, 900.0, 0, 0, 3),
            ]
        )

        self.assertEqual(result["totals"]["completed_jobs"], 6)
        self.assertEqual(result["totals"]["active_tools"], 1)
        self.assertEqual(result["totals"]["avg_memory_gb"], 4.0)
        self.assertEqual(result["totals"]["avg_max_memory_gb"], 4.0)
        self.assertEqual(result["totals"]["max_memory_gb"], 4.0)
        self.assertEqual(result["totals"]["median_memory_gb"], 4.0)
        self.assertEqual(result["totals"]["avg_cpu_cores"], 8.0)
        self.assertEqual(len(result["tool_breakdown"]), 1)
        self.assertEqual(result["tool_breakdown"][0]["tool"], "blast")
        self.assertEqual(result["tool_breakdown"][0]["jobs"], 6)
        self.assertEqual(result["tool_breakdown"][0]["avg_memory_gb"], 4.0)
        self.assertEqual(result["tool_breakdown"][0]["avg_max_memory_gb"], 4.0)
        self.assertEqual(result["tool_breakdown"][0]["max_memory_gb"], 4.0)
        self.assertEqual(result["tool_breakdown"][0]["median_memory_gb"], 4.0)
        self.assertEqual(result["tool_breakdown"][0]["avg_cpu_cores"], 8.0)


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
        store._user_tool_daily_summary = mock.Mock(
            return_value={
                "totals": {
                    "completed_jobs": 1,
                    "active_tools": 1,
                    "avg_memory_gb": 2.0,
                    "avg_max_memory_gb": 2.0,
                    "avg_max_memory_mb": 2048.0,
                    "max_memory_gb": 2.0,
                    "median_memory_gb": 2.0,
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
                        "avg_memory_gb": 2.0,
                        "avg_max_memory_gb": 2.0,
                        "avg_max_memory_mb": 2048.0,
                        "max_memory_gb": 2.0,
                        "median_memory_gb": 2.0,
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
        self.store._jobs_store = mock.Mock()

    def tearDown(self):
        self.psycopg2_patcher.stop()

    def test_completed_jobs_rows_reads_from_shared_jobs_store_by_activity_date(self):
        self.store._jobs_store.completed_job_rows_for_activity_date.return_value = [{"job_name": "blast"}]

        rows = self.store._completed_jobs_rows("alice", date(2026, 4, 24))

        self.assertEqual(rows, [{"job_name": "blast"}])
        self.store._jobs_store.completed_job_rows_for_activity_date.assert_called_once_with(
            date(2026, 4, 24),
            username="alice",
        )

    def test_current_day_rows_reads_from_shared_jobs_store(self):
        self.store._jobs_store.completed_job_rows_for_activity_date.return_value = []

        with mock.patch(
            "slurmweb.persistence.user_analytics_store._now_utc",
            return_value=datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc),
        ):
            self.store._current_day_completed_rows()

        self.store._jobs_store.completed_job_rows_for_activity_date.assert_called_once_with(
            date(2026, 4, 24)
        )

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
        self.store._replace_current_day_summary = mock.Mock()

        self.store.refresh_current_day_summary()

        payload = self.store._replace_current_day_summary.call_args.args[0]
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["tool"], "blastp")
        self.assertEqual(payload[0]["jobs_count"], 1)

    def test_refresh_current_day_summary_skips_usage_stats_when_used_memory_is_missing(self):
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
        self.store._replace_current_day_summary = mock.Mock()

        self.store.refresh_current_day_summary()

        payload = self.store._replace_current_day_summary.call_args.args[0]
        self.assertEqual(payload, [])

    def test_refresh_current_day_summary_skips_tres_when_used_memory_is_missing(self):
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
                    "usage_stats": None,
                }
            ]
        )
        self.store._replace_current_day_summary = mock.Mock()

        self.store.refresh_current_day_summary()

        payload = self.store._replace_current_day_summary.call_args.args[0]
        self.assertEqual(payload, [])

    def test_refresh_current_day_summary_keeps_positive_memory_rows_without_cpu(self):
        self.store._current_day_completed_rows = mock.Mock(
            return_value=[
                {
                    "activity_date": date(2026, 4, 24),
                    "user_id": 1,
                    "job_name": "blast",
                    "command": "blastp",
                    "used_memory_gb": 8.0,
                    "used_cpu_cores_avg": None,
                    "start_time": datetime(2026, 4, 24, 8, 0, tzinfo=timezone.utc),
                    "end_time": datetime(2026, 4, 24, 9, 0, tzinfo=timezone.utc),
                    "last_seen": datetime(2026, 4, 24, 9, 0, tzinfo=timezone.utc),
                    "usage_stats": None,
                }
            ]
        )
        self.store._replace_current_day_summary = mock.Mock()

        self.store.refresh_current_day_summary()

        payload = self.store._replace_current_day_summary.call_args.args[0]
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["jobs_count"], 1)
        self.assertEqual(payload[0]["avg_memory_gb"], 8.0)
        self.assertEqual(payload[0]["max_memory_gb"], 8.0)
        self.assertEqual(payload[0]["median_memory_gb"], 8.0)
        self.assertEqual(payload[0]["avg_cpu_cores"], 0.0)

    def test_refresh_user_tool_daily_stats_replaces_persisted_rows(self):
        self.store._jobs_store.completed_job_rows_for_activity_dates.return_value = [
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
        self.store._replace_user_tool_daily_stats = mock.Mock()

        self.store._refresh_user_tool_daily_stats(
            "alice",
            date(2026, 4, 24),
            date(2026, 4, 24),
        )

        payload = self.store._replace_user_tool_daily_stats.call_args.args[3]
        self.assertEqual(payload[0]["tool"], "blast")
        self.assertEqual(payload[0]["jobs_count"], 1)
        self.assertEqual(payload[0]["avg_memory_gb"], 10.0)
        self.assertEqual(payload[0]["max_memory_gb"], 10.0)
        self.assertEqual(payload[0]["median_memory_gb"], 10.0)
        self.assertEqual(payload[0]["avg_cpu_cores"], 5.0)
        self.store._jobs_store.completed_job_rows_for_activity_dates.assert_called_once_with(
            date(2026, 4, 24),
            date(2026, 4, 24),
            username="alice",
        )

    def test_replace_current_day_summary_deletes_existing_day_rows_before_insert(self):
        execute_values = mock.Mock()
        extras_module = types.SimpleNamespace(execute_values=execute_values)
        payload = [
            {
                "activity_date": date(2026, 4, 24),
                "user_id": 1,
                "tool": "blast",
                "jobs_count": 1,
                "avg_memory_gb": 10.0,
                "max_memory_gb": 10.0,
                "median_memory_gb": 10.0,
                "avg_cpu_cores": 5.0,
                "avg_runtime_seconds": 7200.0,
            }
        ]
        with mock.patch.dict(
            "sys.modules",
            {
                "psycopg2": types.SimpleNamespace(extras=extras_module),
                "psycopg2.extras": extras_module,
            },
        ), mock.patch(
            "slurmweb.persistence.user_analytics_store._now_utc",
            return_value=datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc),
        ):
            self.store._replace_current_day_summary(payload)

        delete_sql, delete_params = self.cursor.execute.call_args.args
        self.assertIn("DELETE FROM user_tool_daily_stats", delete_sql)
        self.assertEqual(delete_params, (date(2026, 4, 24),))
        execute_values.assert_called_once()
        self.conn.commit.assert_called_once()

    def test_user_tool_daily_summary_reads_persisted_table(self):
        self.cursor.fetchall.return_value = [
            ("blast", 2, 4.0, 4.0, 4.0, 8.0, 3600.0),
            ("blast", 1, 10.0, 10.0, 10.0, 2.0, 7200.0),
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

    def test_user_tool_daily_summary_skips_old_rows_without_positive_resource_pair(self):
        self.cursor.fetchall.return_value = [
            ("blast", 1, None, None, None, None, None),
        ]

        result = self.store._user_tool_daily_summary(
            "alice",
            date(2026, 4, 24),
            date(2026, 4, 24),
        )

        self.assertEqual(result["totals"]["completed_jobs"], 1)
        self.assertIsNone(result["totals"]["avg_max_memory_gb"])
        self.assertIsNone(result["totals"]["avg_cpu_cores"])
        self.assertEqual(len(result["tool_breakdown"]), 1)
        self.assertEqual(result["tool_breakdown"][0]["jobs"], 1)

    def test_user_tool_daily_summary_skips_null_resource_days_from_resource_averages(self):
        self.cursor.fetchall.return_value = [
            ("blast", 2, 4.0, 4.0, 4.0, 8.0, 3600.0),
            ("blast", 3, None, None, None, None, 1800.0),
        ]

        result = self.store._user_tool_daily_summary(
            "alice",
            date(2026, 4, 24),
            date(2026, 4, 25),
        )

        self.assertEqual(result["totals"]["completed_jobs"], 5)
        self.assertAlmostEqual(result["totals"]["avg_max_memory_gb"], 4.0)
        self.assertAlmostEqual(result["totals"]["avg_cpu_cores"], 8.0)
        self.assertAlmostEqual(result["tool_breakdown"][0]["avg_max_memory_gb"], 4.0)
        self.assertAlmostEqual(result["tool_breakdown"][0]["avg_cpu_cores"], 8.0)

    def test_user_tool_daily_summary_uses_jobs_weight_for_legacy_rows_without_samples(self):
        self.cursor.fetchall.return_value = [
            ("blast", 2, 4.0, 4.0, 4.0, 8.0, 3600.0),
            ("blast", 1, 10.0, 10.0, 10.0, 2.0, 7200.0),
        ]

        result = self.store._user_tool_daily_summary(
            "alice",
            date(2026, 4, 24),
            date(2026, 4, 25),
        )

        self.assertEqual(result["totals"]["completed_jobs"], 3)
        self.assertAlmostEqual(result["totals"]["avg_max_memory_gb"], 6.0)
        self.assertAlmostEqual(result["totals"]["avg_cpu_cores"], 6.0)
        self.assertAlmostEqual(result["tool_breakdown"][0]["avg_max_memory_gb"], 6.0)
        self.assertAlmostEqual(result["tool_breakdown"][0]["avg_cpu_cores"], 6.0)

    def test_completed_jobs_window_reads_submitted_completed_rows_from_shared_jobs_store(self):
        start_time = datetime(2026, 4, 24, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)

        self.store._completed_jobs_rows_window("alice", start_time, end_time)

        self.store._jobs_store.completed_job_rows_by_submit_window.assert_called_once_with(
            username="alice",
            start_time=start_time,
            end_time=end_time + timedelta(microseconds=1),
            activity_date=date(2026, 4, 24),
        )

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


class TestRepairUserToolDailyStatsScript(unittest.TestCase):
    def _load_script(self):
        import importlib.util

        path = REPO_ROOT / "slurmweb" / "scripts" / "repair-user-tool-daily-stats.py"
        spec = importlib.util.spec_from_file_location("repair_user_tool_daily_stats", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_rebuild_dry_run_does_not_write(self):
        script = self._load_script()
        conn = mock.Mock()
        args = SimpleNamespace(
            start=date(2026, 4, 24),
            end=date(2026, 4, 25),
            user="alice",
            dry_run=True,
            rewrite_pattern=r"^regr([_-].*)?$",
            rewrite_tool="regr",
        )

        with mock.patch(
            "slurmweb.persistence.jobs_store.JobsStore.completed_job_rows_for_activity_dates",
            return_value=[
                {
                    "activity_date": date(2026, 4, 24),
                    "user_id": 1,
                    "job_name": "blast",
                    "command": "blastp",
                    "used_memory_gb": 4.0,
                    "used_cpu_cores_avg": 2.0,
                    "start_time": datetime(2026, 4, 24, 8, 0, tzinfo=timezone.utc),
                    "end_time": datetime(2026, 4, 24, 9, 0, tzinfo=timezone.utc),
                    "usage_stats": None,
                }
            ],
        ), mock.patch.object(script, "count_target_rows", return_value=3) as count_target, mock.patch.object(
            script, "replace_target_rows"
        ) as replace_target:
            result = script.rebuild(
                conn,
                args,
                SimpleNamespace(tool_mapping_file=None),
            )

        self.assertEqual(result, {"source_jobs": 1, "deleted": 3, "inserted": 1})
        count_target.assert_called_once_with(
            conn, date(2026, 4, 24), date(2026, 4, 25), username="alice"
        )
        replace_target.assert_not_called()
        conn.commit.assert_not_called()

    def test_rebuild_writes_rebuilt_payload(self):
        script = self._load_script()
        conn = mock.Mock()
        args = SimpleNamespace(
            start=date(2026, 4, 24),
            end=date(2026, 4, 24),
            user=None,
            dry_run=False,
            rewrite_pattern=r"^regr([_-].*)?$",
            rewrite_tool="regr",
        )

        with mock.patch(
            "slurmweb.persistence.jobs_store.JobsStore.completed_job_rows_for_activity_dates",
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
                    "usage_stats": None,
                }
            ],
        ), mock.patch.object(script, "count_target_rows", return_value=0), mock.patch.object(
            script, "replace_target_rows", return_value=2
        ) as replace_target:
            result = script.rebuild(
                conn,
                args,
                SimpleNamespace(tool_mapping_file=None),
            )

        payload = replace_target.call_args.args[3]
        self.assertEqual(result, {"source_jobs": 1, "deleted": 2, "inserted": 0})
        self.assertEqual(payload, [])
        replace_target.assert_called_once()
        conn.commit.assert_called_once()


class TestRebuildUserToolScript(unittest.TestCase):
    def _load_script(self):
        import importlib.util

        path = REPO_ROOT / "slurmweb" / "scripts" / "rebuild-user-tool.py"
        spec = importlib.util.spec_from_file_location("rebuild_user_tool", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_rebuild_dry_run_prints_day_preview_and_row_logs(self):
        script = self._load_script()
        conn = mock.Mock()
        args = SimpleNamespace(
            mapping_file=None,
            rewrite_pattern=r"^regr([_-].*)?$",
            rewrite_tool="regr",
            dry_run=True,
            date=None,
            user=None,
            user_id=None,
        )
        row = {
            "activity_date": date(2026, 4, 23),
            "job_id": 101,
            "job_state": "COMPLETED",
            "submit_time": datetime(2026, 4, 24, 8, 0, tzinfo=timezone.utc),
            "user_id": 1,
            "username": "alice",
            "job_name": "blast",
            "command": "blastp",
            "used_memory_gb": 4.0,
            "used_cpu_cores_avg": 2.0,
            "start_time": datetime(2026, 4, 24, 8, 0, tzinfo=timezone.utc),
            "end_time": datetime(2026, 4, 24, 9, 0, tzinfo=timezone.utc),
            "usage_stats": None,
        }

        with mock.patch.object(
            script, "load_settings", return_value=SimpleNamespace(tool_mapping_file=None)
        ), mock.patch(
            "slurmweb.persistence.jobs_store.JobsStore.completed_date_bounds",
            return_value=(date(2026, 4, 24), date(2026, 4, 24)),
        ), mock.patch(
            "slurmweb.persistence.jobs_store.JobsStore.completed_job_rows_for_activity_date",
            return_value=[row],
        ) as completed_rows, mock.patch.object(
            script, "count_existing_rows", return_value=3
        ), mock.patch.object(
            script, "replace_all_rows"
        ) as replace_all_rows, mock.patch("builtins.print") as mock_print:
            result = script.rebuild(conn, args)

        self.assertEqual(
            result,
            {
                "start_date": date(2026, 4, 24),
                "end_date": date(2026, 4, 24),
                "days": 1,
                "source_jobs": 1,
                "rows_deleted": 3,
                "rows_inserted": 1,
            },
        )
        completed_rows.assert_called_once_with(date(2026, 4, 24), username=None)
        replace_all_rows.assert_not_called()
        conn.commit.assert_not_called()
        printed = "\n".join(str(call.args[0]) for call in mock_print.call_args_list)
        self.assertIn(
            "user_tool_daily_stats day: date=2026-04-24 memory_source=used_memory_gb "
            "source_jobs=1 counted=1 skipped_memory=0 missing_identity=0 cpu_missing=0 "
            "runtime_missing=0 rows=1",
            printed,
        )
        self.assertIn(
            "user_tool_daily_stats preview: start=2026-04-24 end=2026-04-24 days=1 "
            "source_jobs=1 delete_rows=3 insert_rows=1",
            printed,
        )
        self.assertIn("user_tool_daily_stats row: date=2026-04-24 user_id=1 username=alice", printed)
        self.assertIn("tool=blast", printed)
        self.assertIn("jobs_count=1", printed)
        self.assertIn("avg_memory_gb=4.0", printed)
        self.assertIn("max_memory_gb=4.0", printed)
        self.assertIn("median_memory_gb=4.0", printed)
        self.assertIn("avg_cpu_cores=2.0", printed)
        self.assertIn("avg_runtime_seconds=3600.0", printed)
        self.assertIn(
            "user_tool_daily_stats query: date=2026-04-24 user=- user_id=- "
            "submit_start=2026-04-24T00:00:00+00:00 submit_end=2026-04-25T00:00:00+00:00 "
            "source_jobs=1",
            printed,
        )
        self.assertIn(
            "user_tool_daily_stats job: date=2026-04-24 job_id=101 submit_time=2026-04-24T08:00:00+00:00 "
            "state=COMPLETED user_id=1 username=alice tool=blast memory_source=used_memory_gb "
            "used_memory_gb=4.0 used_cpu_cores_avg=2.0 runtime_seconds=3600.0 "
            "decision=counted reason=ok",
            printed,
        )

    def test_rebuild_skips_rows_without_used_memory_gb_even_with_fallback_memory(self):
        script = self._load_script()
        conn = mock.Mock()
        args = SimpleNamespace(
            mapping_file=None,
            rewrite_pattern=r"^regr([_-].*)?$",
            rewrite_tool="regr",
            dry_run=True,
            date=None,
            user=None,
            user_id=None,
        )
        rows = [
            {
                "activity_date": date(2026, 4, 24),
                "job_id": 102,
                "job_state": "COMPLETED",
                "submit_time": datetime(2026, 4, 24, 8, 0, tzinfo=timezone.utc),
                "user_id": 1,
                "username": "alice",
                "job_name": "blast",
                "command": "blastp",
                "used_memory_gb": None,
                "used_cpu_cores_avg": 2.0,
                "start_time": datetime(2026, 4, 24, 8, 0, tzinfo=timezone.utc),
                "end_time": datetime(2026, 4, 24, 9, 0, tzinfo=timezone.utc),
                "usage_stats": {"memory": {"value_gb": 16.0}},
            }
        ]

        with mock.patch.object(
            script, "load_settings", return_value=SimpleNamespace(tool_mapping_file=None)
        ), mock.patch(
            "slurmweb.persistence.jobs_store.JobsStore.completed_date_bounds",
            return_value=(date(2026, 4, 24), date(2026, 4, 24)),
        ), mock.patch(
            "slurmweb.persistence.jobs_store.JobsStore.completed_job_rows_for_activity_date",
            return_value=rows,
        ), mock.patch.object(
            script, "count_existing_rows", return_value=3
        ), mock.patch.object(
            script, "replace_all_rows"
        ) as replace_all_rows, mock.patch("builtins.print") as mock_print:
            result = script.rebuild(conn, args)

        self.assertEqual(result["source_jobs"], 1)
        self.assertEqual(result["rows_inserted"], 0)
        replace_all_rows.assert_not_called()
        printed = "\n".join(str(call.args[0]) for call in mock_print.call_args_list)
        self.assertIn(
            "user_tool_daily_stats day: date=2026-04-24 memory_source=used_memory_gb "
            "source_jobs=1 counted=0 skipped_memory=1 missing_identity=0 cpu_missing=0 "
            "runtime_missing=0 rows=0",
            printed,
        )
        self.assertNotIn("user_tool_daily_stats row:", printed)
        self.assertIn("decision=skipped reason=missing_used_memory_gb", printed)

    def test_rebuild_write_mode_prints_multiple_row_logs_and_commits(self):
        script = self._load_script()
        conn = mock.Mock()
        args = SimpleNamespace(
            mapping_file=None,
            rewrite_pattern=r"^regr([_-].*)?$",
            rewrite_tool="regr",
            dry_run=False,
            date=None,
            user=None,
            user_id=None,
        )
        rows = [
            {
                "activity_date": date(2026, 4, 24),
                "user_id": 1,
                "username": "alice",
                "job_name": "blast",
                "command": "blastp",
                "used_memory_gb": 4.0,
                "used_cpu_cores_avg": 2.0,
                "start_time": datetime(2026, 4, 24, 8, 0, tzinfo=timezone.utc),
                "end_time": datetime(2026, 4, 24, 9, 0, tzinfo=timezone.utc),
                "usage_stats": None,
            },
            {
                "activity_date": date(2026, 4, 24),
                "user_id": 2,
                "username": "bob",
                "job_name": "bwa",
                "command": "bwa mem",
                "used_memory_gb": 8.0,
                "used_cpu_cores_avg": None,
                "start_time": datetime(2026, 4, 24, 10, 0, tzinfo=timezone.utc),
                "end_time": datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc),
                "usage_stats": None,
            },
        ]

        with mock.patch.object(
            script, "load_settings", return_value=SimpleNamespace(tool_mapping_file=None)
        ), mock.patch(
            "slurmweb.persistence.jobs_store.JobsStore.completed_date_bounds",
            return_value=(date(2026, 4, 24), date(2026, 4, 24)),
        ), mock.patch(
            "slurmweb.persistence.jobs_store.JobsStore.completed_job_rows_for_activity_date",
            return_value=rows,
        ), mock.patch.object(
            script, "count_existing_rows", return_value=5
        ), mock.patch.object(
            script, "replace_all_rows", return_value=5
        ) as replace_all_rows, mock.patch("builtins.print") as mock_print:
            result = script.rebuild(conn, args)

        self.assertEqual(result["rows_inserted"], 2)
        replace_all_rows.assert_called_once()
        conn.commit.assert_called_once()
        payload = replace_all_rows.call_args.args[1]
        self.assertEqual(len(payload), 2)
        self.assertEqual(payload[0]["username"], "alice")
        self.assertEqual(payload[1]["username"], "bob")
        printed = "\n".join(str(call.args[0]) for call in mock_print.call_args_list)
        self.assertIn("username=alice", printed)
        self.assertIn("username=bob", printed)
        self.assertIn("tool=blast", printed)
        self.assertIn("tool=bwa", printed)
        self.assertIn("avg_runtime_seconds=3600.0", printed)
        self.assertIn("avg_runtime_seconds=7200.0", printed)

    def test_rebuild_date_and_user_filters_query_single_day(self):
        script = self._load_script()
        conn = mock.Mock()
        args = SimpleNamespace(
            mapping_file=None,
            rewrite_pattern=r"^regr([_-].*)?$",
            rewrite_tool="regr",
            dry_run=True,
            date="20260504",
            user="lizenghui",
            user_id=None,
        )
        rows = [
            {
                "activity_date": date(2026, 5, 4),
                "job_id": 2001,
                "job_state": "COMPLETED",
                "submit_time": datetime(2026, 5, 4, 12, 0, tzinfo=timezone.utc),
                "user_id": 21,
                "username": "lizenghui",
                "job_name": "regr-test",
                "command": "run-regr",
                "used_memory_gb": None,
                "used_cpu_cores_avg": 0.98,
                "start_time": datetime(2026, 5, 4, 12, 0, tzinfo=timezone.utc),
                "end_time": datetime(2026, 5, 4, 12, 10, tzinfo=timezone.utc),
                "usage_stats": None,
            }
        ]

        with mock.patch.object(
            script, "load_settings", return_value=SimpleNamespace(tool_mapping_file=None)
        ), mock.patch(
            "slurmweb.persistence.jobs_store.JobsStore.completed_date_bounds"
        ) as completed_date_bounds, mock.patch(
            "slurmweb.persistence.jobs_store.JobsStore.completed_job_rows_for_activity_date",
            return_value=rows,
        ) as completed_rows, mock.patch.object(
            script, "count_existing_rows"
        ) as count_existing_rows, mock.patch.object(
            script, "count_target_rows", return_value=10
        ) as count_target_rows, mock.patch.object(
            script, "replace_all_rows"
        ) as replace_all_rows, mock.patch("builtins.print") as mock_print:
            result = script.rebuild(conn, args)

        completed_date_bounds.assert_not_called()
        completed_rows.assert_called_once_with(date(2026, 5, 4), username="lizenghui")
        count_existing_rows.assert_not_called()
        count_target_rows.assert_called_once_with(
            conn,
            date(2026, 5, 4),
            date(2026, 5, 4),
            username="lizenghui",
            user_id=None,
        )
        replace_all_rows.assert_not_called()
        self.assertEqual(result["start_date"], date(2026, 5, 4))
        self.assertEqual(result["end_date"], date(2026, 5, 4))
        self.assertEqual(result["source_jobs"], 1)
        self.assertEqual(result["rows_inserted"], 0)
        printed = "\n".join(str(call.args[0]) for call in mock_print.call_args_list)
        self.assertIn(
            "user_tool_daily_stats query: date=2026-05-04 user=lizenghui user_id=- "
            "submit_start=2026-05-04T00:00:00+00:00 submit_end=2026-05-05T00:00:00+00:00 "
            "source_jobs=1",
            printed,
        )
        self.assertIn(
            "user_tool_daily_stats job: date=2026-05-04 job_id=2001 submit_time=2026-05-04T12:00:00+00:00 "
            "state=COMPLETED user_id=21 username=lizenghui tool=regr memory_source=used_memory_gb "
            "used_memory_gb=null used_cpu_cores_avg=0.98 runtime_seconds=600.0 "
            "decision=skipped reason=missing_used_memory_gb",
            printed,
        )

    def test_rebuild_scoped_user_with_no_jobs_does_not_delete_all_rows(self):
        script = self._load_script()
        conn = mock.Mock()
        args = SimpleNamespace(
            mapping_file=None,
            rewrite_pattern=r"^regr([_-].*)?$",
            rewrite_tool="regr",
            dry_run=False,
            date=None,
            user="missing-user",
            user_id=None,
        )

        with mock.patch.object(
            script, "load_settings", return_value=SimpleNamespace(tool_mapping_file=None)
        ), mock.patch(
            "slurmweb.persistence.jobs_store.JobsStore.completed_date_bounds",
            return_value=(None, None),
        ), mock.patch.object(
            script, "count_existing_rows"
        ) as count_existing_rows, mock.patch.object(
            script, "replace_all_rows"
        ) as replace_all_rows, mock.patch.object(
            script, "replace_target_rows"
        ) as replace_target_rows:
            result = script.rebuild(conn, args)

        self.assertEqual(result["rows_deleted"], 0)
        self.assertEqual(result["rows_inserted"], 0)
        count_existing_rows.assert_not_called()
        replace_all_rows.assert_not_called()
        replace_target_rows.assert_not_called()
        conn.commit.assert_not_called()

    def test_rebuild_does_not_initialize_slurmrestd_or_enrich_daily_rows(self):
        script = self._load_script()
        conn = mock.Mock()
        args = SimpleNamespace(
            mapping_file=None,
            rewrite_pattern=r"^regr([_-].*)?$",
            rewrite_tool="regr",
            dry_run=True,
            date="20260504",
            user="lizenghui",
            user_id=None,
        )

        with mock.patch.object(
            script,
            "load_settings",
            return_value=SimpleNamespace(tool_mapping_file=None),
        ), mock.patch(
            "slurmweb.persistence.jobs_store.JobsStore.completed_job_rows_for_activity_date",
            return_value=[],
        ) as completed_rows, mock.patch.object(
            script, "count_target_rows", return_value=0
        ), mock.patch("builtins.print"):
            script.rebuild(conn, args)

        self.assertFalse(hasattr(script, "make_slurmrestd"))
        completed_rows.assert_called_once_with(date(2026, 5, 4), username="lizenghui")


class TestBackfillJobSnapshotUsageScript(unittest.TestCase):
    class SlurmrestdNotFoundError(Exception):
        pass

    class FakeQuery:
        def __init__(self, rows):
            self.rows = rows
            self.limit_value = None
            self.filter_calls = 0

        def outerjoin(self, *args, **kwargs):
            return self

        def filter(self, *args, **kwargs):
            self.filter_calls += 1
            return self

        def order_by(self, *args, **kwargs):
            return self

        def limit(self, value):
            self.limit_value = value
            self.rows = self.rows[:value]
            return self

        def all(self):
            return self.rows

    class FakeSession:
        def __init__(self, rows):
            self.rows = rows
            self.query_obj = None
            self.commit = mock.Mock()
            self.rollback = mock.Mock()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def query(self, *args):
            self.query_obj = TestBackfillJobSnapshotUsageScript.FakeQuery(self.rows)
            return self.query_obj

    def _load_script(self):
        import importlib.util

        path = REPO_ROOT / "slurmweb" / "scripts" / "backfill-job-snapshot-usage.py"
        spec = importlib.util.spec_from_file_location("backfill_job_snapshot_usage", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _snapshot(self, record_id=1, job_id=996542, memory=None, cpu=None):
        submit_time = datetime.fromtimestamp(1710000000, tz=timezone.utc)
        return SimpleNamespace(
            id=record_id,
            job_id=job_id,
            submit_time=submit_time,
            job_name="regr",
            job_state="COMPLETED",
            state_reason=None,
            user_id=21,
            account="science",
            group="research",
            partition="normal",
            qos="normal",
            nodes="cn1",
            node_count=1,
            cpus=16,
            priority=100,
            tres_req_str=None,
            tres_per_job=None,
            tres_per_node=None,
            gres_detail=None,
            tres_requested=None,
            tres_allocated=None,
            start_time=datetime.fromtimestamp(1710000100, tz=timezone.utc),
            end_time=datetime.fromtimestamp(1710000530, tz=timezone.utc),
            eligible_time=None,
            last_sched_evaluation_time=None,
            time_limit_minutes=60,
            used_memory_gb=memory,
            usage_stats=None,
            used_cpu_cores_avg=cpu,
            exit_code="0:0",
            working_directory="/tmp/job",
            command="run-regr",
        )

    def _detail(self, job_id=996542, submit_ts=1710000000, include_usage=True):
        detail = {
            "job_id": job_id,
            "name": "regr",
            "user": "lizenghui",
            "group": "research",
            "association": {"account": "science"},
            "partition": "normal",
            "qos": "normal",
            "nodes": "cn1",
            "node_count": {"set": True, "infinite": False, "number": 1},
            "cpus": {"set": True, "infinite": False, "number": 16},
            "priority": {"set": True, "infinite": False, "number": 100},
            "state": {"current": ["COMPLETED"], "reason": "None"},
            "time": {
                "submission": submit_ts,
                "start": 1710000100,
                "end": 1710000530,
                "limit": {"set": True, "infinite": False, "number": 60},
            },
            "steps": [],
            "working_directory": "/tmp/job",
            "command": "run-regr",
        }
        if include_usage:
            detail["steps"] = [
                {
                    "time": {
                        "elapsed": 430,
                        "total": {"seconds": 386, "microseconds": 0},
                    },
                    "step": {"id": f"{job_id}.batch", "name": "batch"},
                    "tres": {
                        "consumed": {
                            "max": [
                                {
                                    "type": "mem",
                                    "count": 2575364096,
                                    "id": 2,
                                    "name": "",
                                }
                            ]
                        }
                    },
                }
            ]
        return detail

    def _args(self, **overrides):
        values = {
            "start": None,
            "end": None,
            "user": None,
            "job_id": None,
            "limit": None,
            "dry_run": False,
        }
        values.update(overrides)
        return SimpleNamespace(**values)

    def test_backfill_dry_run_logs_rows_without_committing_updates(self):
        script = self._load_script()
        snapshot = self._snapshot()
        session = self.FakeSession([(snapshot, "lizenghui")])
        slurmrestd = mock.Mock()
        slurmrestd.job.return_value = self._detail()

        with mock.patch("builtins.print") as mock_print:
            result = script.backfill(lambda: session, slurmrestd, self._args(dry_run=True))

        self.assertEqual(result, {"scanned": 1, "updated": 1, "skipped": 0})
        self.assertIsNone(snapshot.used_memory_gb)
        self.assertIsNone(snapshot.used_cpu_cores_avg)
        session.rollback.assert_called_once()
        session.commit.assert_not_called()
        printed = "\n".join(str(call.args[0]) for call in mock_print.call_args_list)
        self.assertIn(
            "job_snapshot_usage row: id=1 job_id=996542 username=lizenghui "
            "old_memory=null new_memory=2.3984947204589844 old_cpu=null "
            "new_cpu=0.8976744186046511 decision=updated reason=ok "
            "error_type=null error=null",
            printed,
        )

    def test_backfill_updates_missing_usage_fields_and_commits(self):
        script = self._load_script()
        snapshot = self._snapshot()
        session = self.FakeSession([(snapshot, "lizenghui")])
        slurmrestd = mock.Mock()
        slurmrestd.job.return_value = self._detail()

        result = script.backfill(lambda: session, slurmrestd, self._args())

        self.assertEqual(result, {"scanned": 1, "updated": 1, "skipped": 0})
        self.assertEqual(snapshot.used_memory_gb, 2.3984947204589844)
        self.assertEqual(snapshot.used_cpu_cores_avg, 0.8976744186046511)
        session.commit.assert_called_once()
        session.rollback.assert_not_called()

    def test_backfill_query_applies_date_user_job_and_limit_filters(self):
        script = self._load_script()
        session = self.FakeSession([(self._snapshot(), "lizenghui")])
        args = self._args(
            start=date(2026, 5, 4),
            end=date(2026, 5, 4),
            user="lizenghui",
            job_id=996542,
            limit=1,
        )

        query = script.backfill_query(session, args)

        self.assertEqual(query.limit_value, 1)
        self.assertGreaterEqual(query.filter_calls, 6)
        self.assertEqual(len(query.all()), 1)

    def test_backfill_logs_skipped_reasons(self):
        script = self._load_script()
        missing_usage = self._snapshot(record_id=1, job_id=1)
        missing_detail = self._snapshot(record_id=2, job_id=2)
        mismatch = self._snapshot(record_id=3, job_id=3)
        session = self.FakeSession(
            [
                (missing_usage, "alice"),
                (missing_detail, "bob"),
                (mismatch, "carol"),
            ]
        )
        slurmrestd = mock.Mock()
        no_usage_detail = self._detail(job_id=1, include_usage=False)
        no_usage_detail["time"]["end"] = None
        slurmrestd.job.side_effect = [
            no_usage_detail,
            self.SlurmrestdNotFoundError("missing"),
            self._detail(job_id=3, submit_ts=1710000999),
        ]

        with mock.patch("builtins.print") as mock_print:
            result = script.backfill(lambda: session, slurmrestd, self._args(dry_run=True))

        self.assertEqual(result, {"scanned": 3, "updated": 0, "skipped": 3})
        printed = "\n".join(str(call.args[0]) for call in mock_print.call_args_list)
        self.assertIn("job_id=1 username=alice", printed)
        self.assertIn("decision=skipped reason=missing_used_memory_gb", printed)
        self.assertIn("job_id=2 username=bob", printed)
        self.assertIn("decision=skipped reason=not_found", printed)
        self.assertIn("error_type=SlurmrestdNotFoundError error=missing", printed)
        self.assertIn("job_id=3 username=carol", printed)
        self.assertIn("decision=skipped reason=submit_time_mismatch", printed)

    def test_fetch_job_detail_supports_base_slurmrestd_without_job_method(self):
        script = self._load_script()
        slurmrestd = SimpleNamespace()
        slurmrestd._acctjob = mock.Mock(return_value={"job_id": 996542, "name": "regr"})
        slurmrestd._ctldjob = mock.Mock(return_value={"partition": "normal"})

        detail = script.fetch_job_detail(slurmrestd, 996542)

        self.assertEqual(detail["job_id"], 996542)
        self.assertEqual(detail["partition"], "normal")
        slurmrestd._acctjob.assert_called_once_with(996542)
        slurmrestd._ctldjob.assert_called_once_with(996542, ignore_notfound=True)

    def test_backfill_detail_error_log_includes_exception_type_and_message(self):
        script = self._load_script()
        snapshot = self._snapshot()
        session = self.FakeSession([(snapshot, "lizenghui")])
        slurmrestd = mock.Mock()
        slurmrestd.job.side_effect = AttributeError("'Slurmrestd' object has no attribute 'job'")

        with mock.patch("builtins.print") as mock_print:
            result = script.backfill(lambda: session, slurmrestd, self._args(dry_run=True))

        self.assertEqual(result, {"scanned": 1, "updated": 0, "skipped": 1})
        printed = "\n".join(str(call.args[0]) for call in mock_print.call_args_list)
        self.assertIn("decision=skipped reason=detail_error", printed)
        self.assertIn("error_type=AttributeError", printed)
        self.assertIn("no attribute 'job'", printed)

    def test_backfill_updates_cpu_even_when_detail_memory_is_still_missing(self):
        script = self._load_script()
        snapshot = self._snapshot()
        session = self.FakeSession([(snapshot, "lizenghui")])
        slurmrestd = mock.Mock()
        detail = self._detail(include_usage=False)
        detail["steps"] = [
            {
                "time": {
                    "elapsed": 430,
                    "total": {"seconds": 386, "microseconds": 0},
                },
                "step": {"id": "996542.batch", "name": "batch"},
                "tres": {"consumed": {"max": []}},
            }
        ]
        slurmrestd.job.return_value = detail

        result = script.backfill(lambda: session, slurmrestd, self._args())

        self.assertEqual(result, {"scanned": 1, "updated": 1, "skipped": 0})
        self.assertIsNone(snapshot.used_memory_gb)
        self.assertEqual(snapshot.used_cpu_cores_avg, 0.8976744186046511)
