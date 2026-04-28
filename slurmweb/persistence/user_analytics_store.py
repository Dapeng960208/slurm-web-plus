# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

import logging
import ntpath
import posixpath
import re
import shlex
import threading
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

import yaml

from ..models.db import psycopg_connect_kwargs
from .jobs_store import TERMINAL_STATES


logger = logging.getLogger(__name__)


_SUMMARY_RANGE_WINDOWS = {
    "hour": timedelta(hours=1),
    "day": timedelta(days=1),
    "week": timedelta(days=7),
}


def _now_utc():
    return datetime.now(tz=timezone.utc)


def _basename_token(token: str) -> str:
    normalized = str(token).strip().strip("\"'")
    normalized = ntpath.basename(normalized)
    normalized = posixpath.basename(normalized)
    return normalized.strip()


def _normalize_candidate(candidate):
    if candidate is None:
        return None
    value = str(candidate).strip().strip("\"'")
    if not value:
        return None
    value = value.split()[0]
    value = _basename_token(value)
    value = value.rsplit(".", 1)[0] or value
    value = re.sub(r"[^0-9A-Za-z._+-]+", "-", value)
    value = value.strip("-_.+").lower()
    return value or None


def _command_first_tool_token(command):
    if not command:
        return None
    try:
        tokens = shlex.split(str(command))
    except ValueError:
        tokens = str(command).split()
    for token in tokens:
        token = token.strip()
        if not token:
            continue
        if token.startswith("-"):
            continue
        if "=" in token and "/" not in token and "\\" not in token:
            continue
        return _normalize_candidate(token)
    return None


class ToolNameMapper:
    def __init__(self, mapping_file=None):
        self.mapping_file = str(mapping_file) if mapping_file else None
        self._rules = []
        if self.mapping_file:
            self._rules = self._load_rules(self.mapping_file)

    def _load_rules(self, mapping_file):
        with open(mapping_file, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or []
        if not isinstance(raw, list):
            raise ValueError("Tool mapping file must contain a YAML list")
        rules = []
        for idx, item in enumerate(raw):
            if not isinstance(item, dict):
                raise ValueError(f"Tool mapping rule #{idx + 1} must be a mapping")
            pattern = item.get("pattern")
            tool = item.get("tool")
            if not pattern or not tool:
                raise ValueError(
                    f"Tool mapping rule #{idx + 1} must define pattern and tool"
                )
            rules.append((re.compile(str(pattern)), _normalize_candidate(tool) or "unknown"))
        return rules

    def classify(self, job_name=None, command=None, submit_line=None):
        job_name_tool = _normalize_candidate(job_name)
        command_tool = _command_first_tool_token(command) or _command_first_tool_token(
            submit_line
        )
        for candidate in (job_name_tool, command_tool):
            if not candidate:
                continue
            for pattern, tool in self._rules:
                if pattern.search(candidate):
                    return tool
        return job_name_tool or command_tool or "unknown"


def normalize_tool_name(job_name=None, command=None, submit_line=None, mapper=None) -> str:
    mapper = mapper or ToolNameMapper()
    return mapper.classify(job_name=job_name, command=command, submit_line=submit_line)


def _runtime_seconds(row: dict):
    start_time = row.get("start_time")
    end_time = row.get("end_time")
    if start_time is not None and end_time is not None and end_time >= start_time:
        return float((end_time - start_time).total_seconds())

    usage_stats = row.get("usage_stats")
    if isinstance(usage_stats, dict):
        cpu_stats = usage_stats.get("cpu")
        if isinstance(cpu_stats, dict):
            value = cpu_stats.get("job_elapsed_seconds")
            try:
                if value is not None:
                    return float(value)
            except (TypeError, ValueError):
                return None
    return None


def _memory_mb(value_gb):
    if value_gb is None:
        return None
    return float(value_gb) * 1024.0


def _runtime_hours(value_seconds):
    if value_seconds is None:
        return None
    return float(value_seconds) / 3600.0


def _bucket_epoch_ms(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return int(value.timestamp() * 1000)


def _avg(total, samples):
    if samples <= 0:
        return None
    return float(total) / float(samples)


def _aggregate_rows(rows, mapper=None):
    mapper = mapper or ToolNameMapper()
    tools = defaultdict(
        lambda: {
            "jobs": 0,
            "memory_total": 0.0,
            "memory_samples": 0,
            "cpu_total": 0.0,
            "cpu_samples": 0,
            "runtime_total": 0.0,
            "runtime_samples": 0,
        }
    )
    summary = {
        "jobs": 0,
        "memory_total": 0.0,
        "memory_samples": 0,
        "cpu_total": 0.0,
        "cpu_samples": 0,
        "runtime_total": 0.0,
        "runtime_samples": 0,
    }

    for row in rows:
        tool = mapper.classify(
            job_name=row.get("job_name"),
            command=row.get("command"),
            submit_line=row.get("submit_line"),
        )
        bucket = tools[tool]
        bucket["jobs"] += 1
        summary["jobs"] += 1

        memory_value = row.get("used_memory_gb")
        if memory_value is not None:
            bucket["memory_total"] += float(memory_value)
            bucket["memory_samples"] += 1
            summary["memory_total"] += float(memory_value)
            summary["memory_samples"] += 1

        cpu_value = row.get("used_cpu_cores_avg", row.get("used_cpu_core_avg"))
        if cpu_value is not None:
            bucket["cpu_total"] += float(cpu_value)
            bucket["cpu_samples"] += 1
            summary["cpu_total"] += float(cpu_value)
            summary["cpu_samples"] += 1

        runtime_value = _runtime_seconds(row)
        if runtime_value is not None:
            bucket["runtime_total"] += float(runtime_value)
            bucket["runtime_samples"] += 1
            summary["runtime_total"] += float(runtime_value)
            summary["runtime_samples"] += 1

    tool_breakdown = []
    for tool, values in tools.items():
        avg_memory_gb = _avg(values["memory_total"], values["memory_samples"])
        avg_runtime_seconds = _avg(
            values["runtime_total"], values["runtime_samples"]
        )
        tool_breakdown.append(
            {
                "tool": tool,
                "jobs": values["jobs"],
                "avg_max_memory_gb": avg_memory_gb,
                "avg_max_memory_mb": _memory_mb(avg_memory_gb),
                "avg_cpu_cores": _avg(values["cpu_total"], values["cpu_samples"]),
                "avg_runtime_hours": _runtime_hours(avg_runtime_seconds),
                "avg_runtime_seconds": avg_runtime_seconds,
            }
        )
    tool_breakdown.sort(key=lambda item: (-item["jobs"], item["tool"]))

    busiest_tool = tool_breakdown[0]["tool"] if tool_breakdown else None
    busiest_tool_jobs = tool_breakdown[0]["jobs"] if tool_breakdown else 0
    avg_summary_memory_gb = _avg(summary["memory_total"], summary["memory_samples"])
    avg_summary_runtime_seconds = _avg(
        summary["runtime_total"], summary["runtime_samples"]
    )

    return {
        "totals": {
            "completed_jobs": summary["jobs"],
            "active_tools": len(tool_breakdown),
            "avg_max_memory_gb": avg_summary_memory_gb,
            "avg_max_memory_mb": _memory_mb(avg_summary_memory_gb),
            "avg_cpu_cores": _avg(summary["cpu_total"], summary["cpu_samples"]),
            "avg_runtime_hours": _runtime_hours(avg_summary_runtime_seconds),
            "avg_runtime_seconds": avg_summary_runtime_seconds,
            "busiest_tool": busiest_tool,
            "busiest_tool_jobs": busiest_tool_jobs,
        },
        "tool_breakdown": tool_breakdown,
    }


class UserAnalyticsStore:
    def __init__(self, settings, users_store=None):
        self._settings = settings
        self._users_store = users_store
        self._pool = None
        self._thread = None
        self._stop_event = threading.Event()
        self._tool_mapper = ToolNameMapper(getattr(settings, "tool_mapping_file", None))

    def _init_pool(self):
        import psycopg2.pool

        self._pool = psycopg2.pool.SimpleConnectionPool(
            1,
            3,
            **psycopg_connect_kwargs(self._settings),
        )
        logger.debug("PostgreSQL user analytics connection pool initialised")

    def _get_conn(self):
        if self._pool is None:
            self._init_pool()
        return self._pool.getconn()

    def _release_conn(self, conn):
        if self._pool is not None:
            self._pool.putconn(conn)

    def start(self):
        self._thread = threading.Thread(
            target=self._run, name="user-metrics-aggregator", daemon=True
        )
        self._thread.start()
        logger.info("User metrics aggregation thread started")

    def stop(self):
        self._stop_event.set()

    def recent_submission_counts(self, window_seconds=60):
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT username, COUNT(*)::int AS job_count
                    FROM (
                        SELECT DISTINCT ON (js.job_id, js.submit_time)
                            u.username
                        FROM job_snapshots js
                        INNER JOIN users u ON u.id = js.user_id
                        WHERE js.submit_time >= NOW() - (%s * INTERVAL '1 second')
                        ORDER BY js.job_id, js.submit_time, js.last_seen DESC
                    ) recent_jobs
                    GROUP BY username
                    ORDER BY username ASC
                    """,
                    (int(window_seconds),),
                )
                return {username: count for username, count in cur.fetchall()}
        finally:
            self._release_conn(conn)

    def _default_analysis_window(self):
        now = _now_utc()
        return now.replace(hour=0, minute=0, second=0, microsecond=0), now

    def _resolve_history_window_and_bucket(
        self, range_name=None, start_time=None, end_time=None
    ):
        if start_time is not None or end_time is not None:
            if start_time is None or end_time is None:
                raise ValueError("start and end must both be provided")
            if start_time >= end_time:
                raise ValueError("start must be earlier than end")
            duration = end_time - start_time
            if duration <= timedelta(hours=48):
                return start_time, end_time, "hour", timedelta(hours=1)
            if duration <= timedelta(days=62):
                return start_time, end_time, "day", timedelta(days=1)
            return start_time, end_time, "week", timedelta(days=7)

        bucket_map = {
            "hour": ("minute", timedelta(minutes=1)),
            "day": ("hour", timedelta(hours=1)),
            "week": ("day", timedelta(days=1)),
        }
        range_name = range_name or "hour"
        if range_name not in bucket_map:
            raise ValueError(f"Unsupported metric range {range_name}")
        bucket_name, resolution = bucket_map[range_name]
        start_time = _now_utc() - _SUMMARY_RANGE_WINDOWS[range_name]
        end_time = _now_utc()
        return start_time, end_time, bucket_name, resolution

    def submission_timeline(self, username, range_name=None, start_time=None, end_time=None):
        start_time, end_time, bucket_name, resolution = (
            self._resolve_history_window_and_bucket(
                range_name=range_name,
                start_time=start_time,
                end_time=end_time,
            )
        )

        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT bucket, COUNT(*)::int AS job_count
                    FROM (
                        SELECT DISTINCT ON (js.job_id, js.submit_time)
                            date_trunc(%s, COALESCE(js.submit_time, js.start_time, js.last_seen) AT TIME ZONE 'UTC') AS bucket,
                            js.job_id,
                            js.submit_time
                        FROM job_snapshots js
                        INNER JOIN users u ON u.id = js.user_id
                        WHERE u.username = %s
                          AND COALESCE(js.submit_time, js.start_time, js.last_seen) >= %s
                          AND COALESCE(js.submit_time, js.start_time, js.last_seen) <= %s
                        ORDER BY js.job_id, js.submit_time, js.last_seen DESC
                    ) submitted_jobs
                    GROUP BY bucket
                    ORDER BY bucket ASC
                    """,
                    (bucket_name, username, start_time, end_time),
                )
                rows = cur.fetchall()
        finally:
            self._release_conn(conn)

        values = {_bucket_epoch_ms(bucket_time): count for bucket_time, count in rows}
        cursor = self._align_bucket(start_time, resolution)
        series = []
        while cursor <= end_time:
            bucket_ms = _bucket_epoch_ms(cursor)
            series.append([bucket_ms, values.get(bucket_ms, 0)])
            cursor += resolution
        return {"submissions": series}

    def completion_timeline(self, username, range_name=None, start_time=None, end_time=None):
        start_time, end_time, bucket_name, resolution = (
            self._resolve_history_window_and_bucket(
                range_name=range_name,
                start_time=start_time,
                end_time=end_time,
            )
        )
        terminal_params = [f"%{state}%" for state in TERMINAL_STATES]
        where_terminal = " OR ".join(["UPPER(js.job_state) LIKE %s"] * len(TERMINAL_STATES))

        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT bucket, COUNT(*)::int AS job_count
                    FROM (
                        SELECT DISTINCT ON (js.job_id, js.submit_time)
                            date_trunc(%s, COALESCE(js.end_time, js.last_seen) AT TIME ZONE 'UTC') AS bucket,
                            js.job_id,
                            js.submit_time
                        FROM job_snapshots js
                        INNER JOIN users u ON u.id = js.user_id
                        WHERE u.username = %s
                          AND COALESCE(js.end_time, js.last_seen) >= %s
                          AND COALESCE(js.end_time, js.last_seen) <= %s
                          AND (
                    """
                    + where_terminal
                    + """
                          )
                        ORDER BY js.job_id, js.submit_time, js.last_seen DESC
                    ) completed_jobs
                    GROUP BY bucket
                    ORDER BY bucket ASC
                    """,
                    [bucket_name, username, start_time, end_time] + terminal_params,
                )
                rows = cur.fetchall()
        finally:
            self._release_conn(conn)

        values = {_bucket_epoch_ms(bucket_time): count for bucket_time, count in rows}
        cursor = self._align_bucket(start_time, resolution)
        series = []
        while cursor <= end_time:
            bucket_ms = _bucket_epoch_ms(cursor)
            series.append([bucket_ms, values.get(bucket_ms, 0)])
            cursor += resolution
        return {"completions": series}

    def user_metrics_history(self, username, range_name=None, start_time=None, end_time=None):
        start_time, end_time, _, _ = self._resolve_history_window_and_bucket(
            range_name=range_name,
            start_time=start_time,
            end_time=end_time,
        )
        submissions = self.submission_timeline(
            username,
            range_name=range_name,
            start_time=start_time,
            end_time=end_time,
        )["submissions"]
        completions = self.completion_timeline(
            username,
            range_name=range_name,
            start_time=start_time,
            end_time=end_time,
        )["completions"]
        return {
            "window": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
            },
            "totals": {
                "submitted_jobs": sum(count for _, count in submissions),
                "completed_jobs": sum(count for _, count in completions),
            },
            "submissions": submissions,
            "completions": completions,
        }

    def latest_submission_count(self, username, window_seconds=60):
        return self.recent_submission_counts(window_seconds).get(username, 0)

    def user_tool_analysis(self, username, start_time=None, end_time=None):
        if start_time is None or end_time is None:
            start_time, end_time = self._default_analysis_window()
        if start_time >= end_time:
            raise ValueError("start must be earlier than end")
        profile = (
            self._users_store.get_ldap_user(username) if self._users_store is not None else None
        )
        rows = self._completed_jobs_rows_window(username, start_time, end_time)
        aggregated = _aggregate_rows(rows, mapper=self._tool_mapper)
        return {
            "username": username,
            "profile": {
                "fullname": profile.get("fullname") if profile else None,
                "groups": profile.get("groups", []) if profile else [],
                "ldap_synced_at": (
                    profile.get("ldap_synced_at").isoformat()
                    if profile and profile.get("ldap_synced_at") is not None
                    else None
                ),
                "ldap_found": bool(profile),
            },
            "generated_at": _now_utc().isoformat(),
            "window": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
            },
            "totals": aggregated["totals"],
            "tool_breakdown": aggregated["tool_breakdown"],
        }

    def user_activity(self, username, last):
        start_time, end_time = self._default_analysis_window()
        summary = self.user_tool_analysis(username, start_time=start_time, end_time=end_time)
        history = self.user_metrics_history(username, last)
        return {
            "username": username,
            "range": last,
            "generated_at": summary["generated_at"],
            "profile": summary["profile"],
            "totals": summary["totals"],
            "tool_breakdown": summary["tool_breakdown"],
            "submission_timeline": [
                {"timestamp": datetime.fromtimestamp(ts / 1000, tz=timezone.utc).isoformat(), "job_count": count}
                for ts, count in history["submissions"]
            ],
            "summary": {
                "job_count": summary["totals"]["completed_jobs"],
                "tool_count": summary["totals"]["active_tools"],
                "avg_max_memory_gb": (
                    summary["totals"]["avg_max_memory_mb"] / 1024.0
                    if summary["totals"]["avg_max_memory_mb"] is not None
                    else None
                ),
                "avg_cpu_cores": summary["totals"]["avg_cpu_cores"],
                "avg_runtime_seconds": summary["totals"]["avg_runtime_seconds"],
                "top_tool": summary["totals"]["busiest_tool"],
            },
            "tools": [
                {
                    "tool": item["tool"],
                    "job_count": item["jobs"],
                    "avg_max_memory_gb": (
                        item["avg_max_memory_mb"] / 1024.0
                        if item["avg_max_memory_mb"] is not None
                        else None
                    ),
                    "avg_cpu_cores": item["avg_cpu_cores"],
                    "avg_runtime_seconds": item["avg_runtime_seconds"],
                }
                for item in summary["tool_breakdown"]
            ],
            "daily_snapshots": self.daily_snapshots(
                username=username,
                start_date=_now_utc().date() - timedelta(days=6),
            ),
        }

    def daily_snapshots(self, username, start_date):
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        activity_date,
                        SUM(jobs_count)::int AS jobs_count,
                        MAX(updated_at) AS updated_at
                    FROM user_tool_daily_stats uds
                    INNER JOIN users u ON u.id = uds.user_id
                    WHERE u.username = %s
                      AND activity_date >= %s
                    GROUP BY activity_date
                    ORDER BY activity_date ASC
                    """,
                    (username, start_date),
                )
                return [
                    {
                        "date": row_date.isoformat(),
                        "job_count": jobs_count,
                        "last_aggregated_at": updated_at.isoformat() if updated_at else None,
                    }
                    for row_date, jobs_count, updated_at in cur.fetchall()
                ]
        finally:
            self._release_conn(conn)

    def _run(self):
        interval = int(getattr(self._settings, "aggregation_interval", 3600))
        try:
            self._init_pool()
        except Exception as err:
            logger.error("Failed to initialise user metrics DB connection pool: %s", err)
            return
        self.refresh_current_day_summary()
        while not self._stop_event.wait(timeout=interval):
            self.refresh_current_day_summary()

    def refresh_current_day_summary(self):
        rows = self._current_day_completed_rows()
        buckets = defaultdict(
            lambda: {
                "jobs_count": 0,
                "memory_total": 0.0,
                "memory_samples": 0,
                "cpu_total": 0.0,
                "cpu_samples": 0,
                "runtime_total": 0.0,
                "runtime_samples": 0,
            }
        )
        for row in rows:
            tool = self._tool_mapper.classify(
                job_name=row.get("job_name"),
                command=row.get("command"),
                submit_line=row.get("submit_line"),
            )
            key = (row["activity_date"], row["user_id"], tool)
            bucket = buckets[key]
            bucket["jobs_count"] += 1
            if row.get("used_memory_gb") is not None:
                bucket["memory_total"] += float(row["used_memory_gb"])
                bucket["memory_samples"] += 1
            if row.get("used_cpu_cores_avg") is not None:
                bucket["cpu_total"] += float(row["used_cpu_cores_avg"])
                bucket["cpu_samples"] += 1
            runtime_value = _runtime_seconds(row)
            if runtime_value is not None:
                bucket["runtime_total"] += float(runtime_value)
                bucket["runtime_samples"] += 1

        payload = []
        for (activity_date, user_id, tool), values in buckets.items():
            payload.append(
                {
                    "activity_date": activity_date,
                    "user_id": user_id,
                    "tool": tool,
                    "jobs_count": values["jobs_count"],
                    "avg_max_memory_gb": _avg(
                        values["memory_total"], values["memory_samples"]
                    ),
                    "avg_cpu_cores": _avg(values["cpu_total"], values["cpu_samples"]),
                    "avg_runtime_seconds": _avg(
                        values["runtime_total"], values["runtime_samples"]
                    ),
                }
            )
        self._upsert_current_day_summary(payload)

    def _submitted_jobs_today(self, username):
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*)::int
                    FROM (
                        SELECT DISTINCT ON (js.job_id, js.submit_time)
                            js.job_id
                        FROM job_snapshots js
                        INNER JOIN users u ON u.id = js.user_id
                        WHERE u.username = %s
                          AND DATE(js.submit_time) = CURRENT_DATE
                        ORDER BY js.job_id, js.submit_time, js.last_seen DESC
                    ) submitted_jobs
                    """,
                    (username,),
                )
                return cur.fetchone()[0]
        finally:
            self._release_conn(conn)

    def _completed_jobs_rows(self, username, activity_date: date):
        import psycopg2.extras

        terminal_params = [f"%{state}%" for state in TERMINAL_STATES]
        where_terminal = " OR ".join(["UPPER(js.job_state) LIKE %s"] * len(TERMINAL_STATES))
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT DISTINCT ON (js.job_id, js.submit_time)
                        js.job_name,
                        js.command,
                        js.used_memory_gb,
                        js.used_cpu_cores_avg,
                        js.start_time,
                        js.end_time,
                        js.last_seen,
                        js.usage_stats
                    FROM job_snapshots js
                    INNER JOIN users u ON u.id = js.user_id
                    WHERE u.username = %s
                      AND DATE(COALESCE(js.end_time, js.last_seen)) = %s
                      AND (
                    """
                    + where_terminal
                    + """
                      )
                    ORDER BY js.job_id, js.submit_time, js.last_seen DESC
                    """,
                    [username, activity_date] + terminal_params,
                )
                return list(cur.fetchall())
        finally:
            self._release_conn(conn)

    def _completed_jobs_rows_window(self, username, start_time, end_time):
        import psycopg2.extras

        terminal_params = [f"%{state}%" for state in TERMINAL_STATES]
        where_terminal = " OR ".join(["UPPER(js.job_state) LIKE %s"] * len(TERMINAL_STATES))
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT DISTINCT ON (js.job_id, js.submit_time)
                        js.job_name,
                        js.command,
                        js.used_memory_gb,
                        js.used_cpu_cores_avg,
                        js.start_time,
                        js.end_time,
                        js.last_seen,
                        js.usage_stats
                    FROM job_snapshots js
                    INNER JOIN users u ON u.id = js.user_id
                    WHERE u.username = %s
                      AND COALESCE(js.end_time, js.last_seen) >= %s
                      AND COALESCE(js.end_time, js.last_seen) <= %s
                      AND (
                    """
                    + where_terminal
                    + """
                      )
                    ORDER BY js.job_id, js.submit_time, js.last_seen DESC
                    """,
                    [username, start_time, end_time] + terminal_params,
                )
                return list(cur.fetchall())
        finally:
            self._release_conn(conn)

    def _current_day_completed_rows(self):
        import psycopg2.extras

        terminal_params = [f"%{state}%" for state in TERMINAL_STATES]
        where_terminal = " OR ".join(["UPPER(js.job_state) LIKE %s"] * len(TERMINAL_STATES))
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT DISTINCT ON (js.job_id, js.submit_time)
                        DATE(COALESCE(js.end_time, js.last_seen)) AS activity_date,
                        js.user_id,
                        js.job_name,
                        js.command,
                        js.used_memory_gb,
                        js.used_cpu_cores_avg,
                        js.start_time,
                        js.end_time,
                        js.last_seen,
                        js.usage_stats
                    FROM job_snapshots js
                    WHERE DATE(COALESCE(js.end_time, js.last_seen)) = CURRENT_DATE
                      AND (
                    """
                    + where_terminal
                    + """
                      )
                    ORDER BY js.job_id, js.submit_time, js.last_seen DESC
                    """,
                    terminal_params,
                )
                return list(cur.fetchall())
        finally:
            self._release_conn(conn)

    def _upsert_current_day_summary(self, payload):
        from psycopg2.extras import execute_values

        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                if payload:
                    execute_values(
                        cur,
                        """
                        INSERT INTO user_tool_daily_stats (
                            activity_date,
                            user_id,
                            tool,
                            jobs_count,
                            avg_max_memory_gb,
                            avg_cpu_cores,
                            avg_runtime_seconds,
                            created_at,
                            updated_at
                        ) VALUES %s
                        ON CONFLICT (activity_date, user_id, tool) DO UPDATE SET
                            jobs_count = EXCLUDED.jobs_count,
                            avg_max_memory_gb = EXCLUDED.avg_max_memory_gb,
                            avg_cpu_cores = EXCLUDED.avg_cpu_cores,
                            avg_runtime_seconds = EXCLUDED.avg_runtime_seconds,
                            updated_at = NOW()
                        """,
                        payload,
                        template=(
                            "(%(activity_date)s, %(user_id)s, %(tool)s, %(jobs_count)s, "
                            "%(avg_max_memory_gb)s, %(avg_cpu_cores)s, "
                            "%(avg_runtime_seconds)s, NOW(), NOW())"
                        ),
                        page_size=max(len(payload), 1),
                    )
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        finally:
            self._release_conn(conn)

    def _align_bucket(self, timestamp, resolution):
        if resolution == timedelta(minutes=1):
            return timestamp.replace(second=0, microsecond=0)
        if resolution == timedelta(hours=1):
            return timestamp.replace(minute=0, second=0, microsecond=0)
        if resolution == timedelta(days=1):
            return timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        if resolution == timedelta(days=7):
            aligned = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
            return aligned - timedelta(days=aligned.weekday())
        return timestamp
