# Copyright (c) 2024 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

"""
Job history persistence module.

Runs a background thread that periodically snapshots active jobs and writes
them to PostgreSQL via UPSERT. The main request path is never blocked.
"""

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Optional

from ..models.db import psycopg_connect_kwargs


logger = logging.getLogger(__name__)

TERMINAL_STATES = frozenset(
    [
        "COMPLETED",
        "FAILED",
        "CANCELLED",
        "TIMEOUT",
        "NODE_FAIL",
        "DEADLINE",
        "OUT_OF_MEMORY",
        "PREEMPTED",
        "BOOT_FAIL",
    ]
)

BATCH_CHUNK = 500
_LOOKUP_FAILED = object()

_UPSERT_SQL = """
INSERT INTO job_snapshots (
    job_id, submit_time,
    first_seen, last_seen,
    job_name, job_state, state_reason,
    user_id, account, "group", partition, qos,
    nodes, node_count, cpus, priority,
    tres_req_str, tres_per_job, tres_per_node, gres_detail,
    tres_requested, tres_allocated,
    start_time, end_time, eligible_time, last_sched_evaluation_time,
    time_limit_minutes, used_memory_gb,
    exit_code, working_directory, command
) VALUES %s
ON CONFLICT (job_id, submit_time) DO UPDATE SET
    last_seen          = NOW(),
    job_state          = EXCLUDED.job_state,
    state_reason       = EXCLUDED.state_reason,
    nodes              = EXCLUDED.nodes,
    node_count         = EXCLUDED.node_count,
    cpus               = EXCLUDED.cpus,
    priority           = EXCLUDED.priority,
    start_time         = EXCLUDED.start_time,
    end_time           = EXCLUDED.end_time,
    eligible_time      = COALESCE(EXCLUDED.eligible_time, job_snapshots.eligible_time),
    last_sched_evaluation_time = COALESCE(
        EXCLUDED.last_sched_evaluation_time,
        job_snapshots.last_sched_evaluation_time
    ),
    tres_requested     = COALESCE(EXCLUDED.tres_requested, job_snapshots.tres_requested),
    tres_allocated     = COALESCE(EXCLUDED.tres_allocated, job_snapshots.tres_allocated),
    used_memory_gb     = COALESCE(EXCLUDED.used_memory_gb, job_snapshots.used_memory_gb),
    exit_code          = EXCLUDED.exit_code,
    gres_detail        = EXCLUDED.gres_detail,
    partition          = EXCLUDED.partition,
    qos                = EXCLUDED.qos,
    time_limit_minutes = EXCLUDED.time_limit_minutes,
    working_directory  = EXCLUDED.working_directory,
    command            = EXCLUDED.command,
    user_id            = EXCLUDED.user_id
"""

_ROW_TEMPLATE = (
    "(%(job_id)s, %(submit_time)s, NOW(), NOW(), %(job_name)s, %(job_state)s, "
    "%(state_reason)s, %(user_id)s, %(account)s, %(group)s, %(partition)s, %(qos)s, "
    "%(nodes)s, %(node_count)s, %(cpus)s, %(priority)s, %(tres_req_str)s, "
    "%(tres_per_job)s, %(tres_per_node)s, %(gres_detail)s, %(tres_requested)s, "
    "%(tres_allocated)s, %(start_time)s, %(end_time)s, %(eligible_time)s, "
    "%(last_sched_evaluation_time)s, %(time_limit_minutes)s, %(used_memory_gb)s, "
    "%(exit_code)s, %(working_directory)s, %(command)s)"
)

_SELECT_COLUMNS = """
js.id,
js.job_id,
js.submit_time,
js.first_seen,
js.last_seen AS snapshot_time,
js.job_name,
js.job_state,
js.state_reason,
js.user_id,
u.username AS user_name,
js.account,
js."group",
js.partition,
js.qos,
js.nodes,
js.node_count,
js.cpus,
js.priority,
js.tres_req_str,
js.tres_per_job,
js.tres_per_node,
js.gres_detail,
js.tres_requested,
js.tres_allocated,
js.start_time,
js.end_time,
js.eligible_time,
js.last_sched_evaluation_time,
js.time_limit_minutes,
js.used_memory_gb,
js.exit_code,
js.working_directory,
js.command
"""

_CLEANUP_SQL = "DELETE FROM job_snapshots WHERE submit_time < NOW() - INTERVAL '%s days'"


def _state_str(value) -> Optional[str]:
    if isinstance(value, list):
        states = [state for state in value if state]
        return ",".join(states) if states else None
    if value in (None, ""):
        return None
    return str(value)


def _tres_str(value):
    if isinstance(value, dict):
        return ",".join(f"{key}={val}" for key, val in value.items())
    return str(value) if value else None


def _gres_str(value):
    if isinstance(value, list):
        return ",".join(value) if value else None
    return str(value) if value else None


def _exit_str(value):
    if isinstance(value, dict):
        return "{}:{}".format(
            value.get("return_code", ""),
            value.get("signal", {}).get("signal_id", ""),
        )
    return str(value) if value else None


def _int_field(value):
    if isinstance(value, dict):
        if not value.get("set", True):
            return None
        if value.get("infinite", False):
            return None
        value = value.get("number")
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _float_field(value):
    if isinstance(value, dict):
        if not value.get("set", True):
            return None
        if value.get("infinite", False):
            return None
        value = value.get("number")
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _state_values(value) -> list:
    state_str = _state_str(value)
    if state_str is None:
        return []
    return [state.strip() for state in state_str.split(",") if state.strip()]


def _is_terminal_state(value) -> bool:
    return any(state in TERMINAL_STATES for state in _state_values(value))


def _is_not_found_error(err: Exception) -> bool:
    return err.__class__.__name__ == "SlurmrestdNotFoundError"


def _ts(value):
    """Convert a Slurm epoch integer to a timezone-aware datetime, or None."""
    if isinstance(value, dict):
        if not value.get("set", True):
            return None
        value = value.get("number")

    if value in (None, ""):
        return None

    try:
        value = int(value)
    except (TypeError, ValueError):
        return None

    if value <= 0:
        return None
    try:
        return datetime.fromtimestamp(value, tz=timezone.utc)
    except (OSError, OverflowError, ValueError):
        return None


def _tres_json(value):
    return value if isinstance(value, list) else None


def _time_value(time_data, key: str, fallback_value=None):
    if isinstance(time_data, dict):
        return time_data.get(key, fallback_value)
    return fallback_value


def _used_memory_gb(job: dict, job_state) -> Optional[float]:
    if not _is_terminal_state(job_state):
        return None

    steps = job.get("steps")
    if not isinstance(steps, list):
        return None

    def _step_memory_kb(step: dict) -> Optional[float]:
        if not isinstance(step, dict):
            return None
        tres = step.get("tres")
        consumed = tres.get("consumed") if isinstance(tres, dict) else None
        total = consumed.get("total") if isinstance(consumed, dict) else None

        if isinstance(total, dict):
            return _float_field(total.get("count"))

        if not isinstance(total, list) or not total:
            return None

        candidates = [
            item
            for item in total
            if isinstance(item, dict)
            and (item.get("type") == "mem" or item.get("id") == 2)
        ]
        if not candidates and len(total) > 1 and isinstance(total[1], dict):
            candidates = [total[1]]

        for item in candidates:
            count = _float_field(item.get("count"))
            if count is not None:
                return count
        return None

    counts = []
    for index in (1, 2):
        if len(steps) <= index:
            continue
        count = _step_memory_kb(steps[index])
        if count is not None:
            counts.append(count)

    if not counts:
        return None

    # Slurm reports consumed memory here in KB; persist GB.
    return round(max(counts) / 1024**2, 2)


def _extract(job: dict) -> dict:
    """Extract and normalize fields from a raw slurmrestd job dict."""
    return {
        "job_id": job.get("job_id"),
        "job_name": job.get("name"),
        "job_state": _state_str(job.get("job_state")),
        "state_reason": job.get("state_reason"),
        "user_name": job.get("user_name"),
        "user_id": None,
        "account": job.get("account"),
        "group": job.get("group"),
        "partition": job.get("partition"),
        "qos": job.get("qos"),
        "nodes": job.get("nodes"),
        "node_count": _int_field(job.get("node_count")),
        "cpus": _int_field(job.get("cpus")),
        "priority": _int_field(job.get("priority")),
        "tres_req_str": _tres_str(job.get("tres_req_str") or job.get("tres_per_job")),
        "tres_per_job": _tres_str(job.get("tres_per_job")),
        "tres_per_node": _tres_str(job.get("tres_per_node")),
        "gres_detail": _gres_str(job.get("gres_detail")),
        "tres_requested": None,
        "tres_allocated": None,
        "submit_time": _ts(job.get("submit_time")),
        "start_time": _ts(job.get("start_time")),
        "end_time": _ts(job.get("end_time")),
        "eligible_time": _ts(job.get("eligible_time")),
        "last_sched_evaluation_time": _ts(job.get("last_sched_evaluation")),
        "time_limit_minutes": _int_field(job.get("time_limit")),
        "used_memory_gb": None,
        "exit_code": _exit_str(job.get("exit_code")),
        "working_directory": job.get("current_working_directory"),
        "command": job.get("command"),
    }


def _extract_detail(job: dict, fallback: Optional[dict] = None) -> dict:
    """Extract fields from merged slurmdb/slurmctld job details."""
    fallback = fallback or {}
    association = job.get("association", {})
    state = job.get("state", {})
    time_data = job.get("time", {})
    tres = job.get("tres", {})
    job_state = _state_str(
        state.get("current", job.get("job_state"))
        if isinstance(state, dict)
        else job.get("job_state")
    ) or fallback.get("job_state")

    row = {
        "job_id": job.get("job_id", fallback.get("job_id")),
        "job_name": job.get("name", fallback.get("job_name")),
        "job_state": job_state,
        "state_reason": (
            state.get("reason") if isinstance(state, dict) else job.get("state_reason")
        )
        or fallback.get("state_reason"),
        "user_name": job.get("user")
        or job.get("user_name")
        or (association.get("user") if isinstance(association, dict) else None)
        or fallback.get("user_name"),
        "user_id": fallback.get("user_id"),
        "account": association.get("account", job.get("account"))
        if isinstance(association, dict)
        else job.get("account"),
        "group": job.get("group")
        or job.get("group_name")
        or fallback.get("group"),
        "partition": job.get("partition", fallback.get("partition")),
        "qos": job.get("qos", fallback.get("qos")),
        "nodes": job.get("nodes", fallback.get("nodes")),
        "node_count": _int_field(job.get("node_count")),
        "cpus": _int_field(job.get("cpus")),
        "priority": _int_field(job.get("priority")),
        "tres_req_str": _tres_str(job.get("tres_req_str") or job.get("tres_per_job")),
        "tres_per_job": _tres_str(job.get("tres_per_job")),
        "tres_per_node": _tres_str(job.get("tres_per_node")),
        "gres_detail": _gres_str(job.get("gres_detail")),
        "submit_time": _ts(
            _time_value(time_data, "submission", job.get("submit_time"))
        ),
        "start_time": _ts(
            _time_value(time_data, "start", job.get("start_time"))
        ),
        "end_time": _ts(
            _time_value(time_data, "end", job.get("end_time"))
        ),
        "eligible_time": _ts(
            _time_value(time_data, "eligible", job.get("eligible_time"))
        ),
        "last_sched_evaluation_time": _ts(job.get("last_sched_evaluation")),
        "tres_requested": _tres_json(
            tres.get("requested") if isinstance(tres, dict) else None
        ),
        "tres_allocated": _tres_json(
            tres.get("allocated") if isinstance(tres, dict) else None
        ),
        "time_limit_minutes": _int_field(
            _time_value(time_data, "limit", job.get("time_limit"))
        ),
        "used_memory_gb": _used_memory_gb(job, job_state),
        "exit_code": _exit_str(job.get("exit_code") or job.get("derived_exit_code")),
        "working_directory": job.get("current_working_directory")
        or job.get("working_directory")
        or fallback.get("working_directory"),
        "command": job.get("command")
        or job.get("submit_line")
        or fallback.get("command"),
    }

    for key in (
        "account",
        "partition",
        "qos",
        "nodes",
        "node_count",
        "cpus",
        "priority",
        "tres_req_str",
        "tres_per_job",
        "tres_per_node",
        "gres_detail",
        "eligible_time",
        "last_sched_evaluation_time",
        "tres_requested",
        "tres_allocated",
        "used_memory_gb",
        "time_limit_minutes",
    ):
        if row[key] is None:
            row[key] = fallback.get(key)

    if row["submit_time"] is None:
        row["submit_time"] = fallback.get("submit_time")

    return row


def _dedup(rows: list) -> list:
    """Keep only the last occurrence of each (job_id, submit_time) in a batch."""
    seen = {}
    for row in rows:
        seen[(row["job_id"], row["submit_time"])] = row
    return list(seen.values())


def _serialize_datetimes(row: dict) -> dict:
    data = dict(row)
    for key, value in data.items():
        if isinstance(value, datetime):
            data[key] = value.isoformat()
    return data


def _prepare_db_row(row: dict) -> dict:
    from psycopg2.extras import Json

    data = dict(row)
    for key in ("tres_requested", "tres_allocated"):
        if data.get(key) is not None:
            data[key] = Json(data[key])
    return data


class JobsStore:
    """
    Manage PostgreSQL persistence for job snapshots.

    Usage:
        store = JobsStore(settings, slurmrestd)
        store.start()
        store.submit(jobs_list)
        store.query(filters)
        store.stop()
    """

    def __init__(self, settings, slurmrestd=None):
        self._settings = settings
        self._slurmrestd = slurmrestd
        self._lock = threading.Lock()
        self._pending = []
        self._thread = None  # type: Optional[threading.Thread]
        self._stop_event = threading.Event()
        self._last_cleanup = 0.0
        self._pool = None

    def start(self):
        self._thread = threading.Thread(
            target=self._run, name="jobs-store-writer", daemon=True
        )
        self._thread.start()
        logger.info("Job history persistence thread started")

    def stop(self):
        self._stop_event.set()

    def submit(self, jobs: list):
        self._queue_rows(self._prepare_rows(jobs))

    def query(self, filters: dict) -> dict:
        import psycopg2.extras

        page = max(1, int(filters.get("page", 1)))
        page_size = min(500, max(1, int(filters.get("page_size", 100))))
        offset = (page - 1) * page_size

        where_clauses = []
        params = []

        if filters.get("start"):
            where_clauses.append("js.submit_time >= %s")
            params.append(filters["start"])
        if filters.get("end"):
            where_clauses.append("js.submit_time <= %s")
            params.append(filters["end"])
        if filters.get("user"):
            where_clauses.append("u.username = %s")
            params.append(filters["user"])
        if filters.get("account"):
            where_clauses.append("js.account = %s")
            params.append(filters["account"])
        if filters.get("partition"):
            where_clauses.append("js.partition = %s")
            params.append(filters["partition"])
        if filters.get("qos"):
            where_clauses.append("js.qos = %s")
            params.append(filters["qos"])
        if filters.get("state"):
            where_clauses.append("js.job_state LIKE %s")
            params.append(f"%{filters['state']}%")
        if filters.get("job_id"):
            where_clauses.append("js.job_id = %s")
            params.append(int(filters["job_id"]))

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT COUNT(*) "
                    "FROM job_snapshots js "
                    "LEFT JOIN users u ON u.id = js.user_id "
                    f"{where_sql}",
                    params,
                )
                total = cur.fetchone()["count"]
                cur.execute(
                    "SELECT "
                    + _SELECT_COLUMNS
                    + " FROM job_snapshots js "
                    + "LEFT JOIN users u ON u.id = js.user_id "
                    + f"{where_sql} "
                    + "ORDER BY js.submit_time DESC LIMIT %s OFFSET %s",
                    params + [page_size, offset],
                )
                rows = cur.fetchall()
        finally:
            self._release_conn(conn)

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "jobs": [_serialize_datetimes(row) for row in rows],
        }

    def get_by_id(self, record_id: int, enrich: bool = True) -> Optional[dict]:
        import psycopg2.extras

        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT "
                    + _SELECT_COLUMNS
                    + " FROM job_snapshots js "
                    + "LEFT JOIN users u ON u.id = js.user_id "
                    + "WHERE js.id = %s",
                    (record_id,),
                )
                row = cur.fetchone()
        finally:
            self._release_conn(conn)

        if row is None:
            return None
        if enrich:
            enriched = self._maybe_enrich_record(row)
            if enriched is not None:
                row = enriched
        return _serialize_datetimes(row)

    def _init_pool(self):
        import psycopg2.pool

        self._pool = psycopg2.pool.SimpleConnectionPool(
            1,
            3,
            **psycopg_connect_kwargs(self._settings),
        )
        logger.debug("PostgreSQL connection pool initialised")

    def _get_conn(self):
        if self._pool is None:
            self._init_pool()
        return self._pool.getconn()

    def _release_conn(self, conn):
        if self._pool is not None:
            self._pool.putconn(conn)

    def _run(self):
        interval = getattr(self._settings, "snapshot_interval", 60)
        retention = getattr(self._settings, "retention_days", 180)

        try:
            self._init_pool()
        except Exception as err:
            logger.error("Failed to initialise DB connection pool: %s", err)
            return

        self._ensure_partitions()
        self._scheduled_snapshot()
        self._flush()

        while not self._stop_event.wait(timeout=interval):
            self._ensure_partitions()
            self._scheduled_snapshot()
            self._flush()
            self._maybe_cleanup(retention)

        self._flush()

    def _scheduled_snapshot(self):
        if self._slurmrestd is None:
            return
        try:
            if hasattr(self._slurmrestd, "jobs_unfiltered"):
                jobs = self._slurmrestd.jobs_unfiltered()
            else:
                jobs = self._slurmrestd.jobs()
            rows = self._prepare_rows(jobs)
            self._queue_rows(rows)
            self._reconcile_missing_active_jobs(rows)
            logger.debug("Scheduled snapshot: fetched %d jobs", len(jobs))
        except Exception as err:
            logger.warning("Scheduled snapshot failed: %s", err)

    def _prepare_rows(self, jobs: list) -> list:
        valid = []
        for job in jobs:
            row = _extract(job)
            if not row["job_id"] or not row["submit_time"]:
                logger.debug(
                    "Skipping job with missing job_id or submit_time: job_id=%s",
                    row.get("job_id"),
                )
                continue
            valid.append(row)
        return valid

    def _queue_rows(self, rows: list):
        if rows:
            with self._lock:
                self._pending.extend(rows)

    def _active_records(self) -> list:
        import psycopg2.extras

        terminal_params = [f"%{state}%" for state in TERMINAL_STATES]
        where_sql = " OR ".join(["js.job_state LIKE %s"] * len(TERMINAL_STATES))

        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT "
                    + _SELECT_COLUMNS
                    + " FROM job_snapshots js "
                    + "LEFT JOIN users u ON u.id = js.user_id "
                    + "WHERE js.job_state IS NULL OR NOT ("
                    + where_sql
                    + ") "
                    + "ORDER BY js.last_seen DESC",
                    terminal_params,
                )
                return cur.fetchall()
        finally:
            self._release_conn(conn)

    def _reconcile_missing_active_jobs(self, current_rows: list):
        if self._slurmrestd is None:
            return

        current_keys = {(row["job_id"], row["submit_time"]) for row in current_rows}
        queued_rows = []
        observed_at = datetime.now(tz=timezone.utc)

        for record in self._active_records():
            key = (record["job_id"], record["submit_time"])
            if key in current_keys:
                continue

            updated_row = self._refresh_missing_active_job(record)
            if updated_row is _LOOKUP_FAILED:
                continue
            if updated_row is None:
                queued_rows.append(self._complete_missing_job(record, observed_at))
            else:
                queued_rows.append(updated_row)

        self._queue_rows(queued_rows)

    def _refresh_missing_active_job(self, record: dict):
        try:
            job = self._slurmrestd.job(record["job_id"])
        except Exception as err:
            if not _is_not_found_error(err):
                logger.warning(
                    "Unable to refresh missing active job %s: %s",
                    record["job_id"],
                    err,
                )
                return _LOOKUP_FAILED
            logger.info(
                "Job %s missing from active queue and detail lookup; marking completed",
                record["job_id"],
            )
            return None

        row = _extract_detail(job, record)
        if not row["job_id"] or not row["submit_time"]:
            logger.warning(
                "Ignoring detail refresh for job %s due to missing key fields",
                record["job_id"],
            )
            return _LOOKUP_FAILED

        record_submit_time = record.get("submit_time")
        if (
            record_submit_time is not None
            and row["submit_time"] is not None
            and row["submit_time"] != record_submit_time
        ):
            logger.warning(
                "Ignoring detail refresh for job %s due to submit_time mismatch",
                record["job_id"],
            )
            return None

        return row

    def _needs_detail_enrichment(self, record: dict) -> bool:
        detail_fields = (
            "eligible_time",
            "last_sched_evaluation_time",
            "tres_requested",
            "tres_allocated",
        )
        if any(record.get(field) is None for field in detail_fields):
            return True
        return (
            record.get("job_state") is not None
            and "COMPLETED" in _state_values(record.get("job_state"))
            and record.get("used_memory_gb") is None
        )

    def _maybe_enrich_record(self, record: dict) -> Optional[dict]:
        if self._slurmrestd is None or not self._needs_detail_enrichment(record):
            return None

        try:
            job = self._slurmrestd.job(record["job_id"])
        except Exception as err:
            if not _is_not_found_error(err):
                logger.warning(
                    "Unable to enrich history record %s for job %s: %s",
                    record.get("id"),
                    record.get("job_id"),
                    err,
                )
            return None

        row = _extract_detail(job, record)
        if not row.get("job_id") or not row.get("submit_time"):
            return None

        if row.get("submit_time") != record.get("submit_time"):
            logger.warning(
                "Ignoring history detail enrichment for job %s due to submit_time mismatch",
                record.get("job_id"),
            )
            return None

        if self._flush_chunk([row]):
            return None

        return self.get_by_id(record["id"], enrich=False)

    def _complete_missing_job(self, record: dict, observed_at: datetime) -> dict:
        return {
            "job_id": record.get("job_id"),
            "job_name": record.get("job_name"),
            "job_state": "COMPLETED",
            "state_reason": record.get("state_reason")
            or "Job missing from active queue and detail lookup",
            "user_name": record.get("user_name"),
            "user_id": record.get("user_id"),
            "account": record.get("account"),
            "group": record.get("group"),
            "partition": record.get("partition"),
            "qos": record.get("qos"),
            "nodes": record.get("nodes"),
            "node_count": record.get("node_count"),
            "cpus": record.get("cpus"),
            "priority": record.get("priority"),
            "tres_req_str": record.get("tres_req_str"),
            "tres_per_job": record.get("tres_per_job"),
            "tres_per_node": record.get("tres_per_node"),
            "gres_detail": record.get("gres_detail"),
            "tres_requested": record.get("tres_requested"),
            "tres_allocated": record.get("tres_allocated"),
            "submit_time": record.get("submit_time"),
            "start_time": record.get("start_time"),
            "end_time": record.get("end_time") or observed_at,
            "eligible_time": record.get("eligible_time"),
            "last_sched_evaluation_time": record.get("last_sched_evaluation_time"),
            "time_limit_minutes": record.get("time_limit_minutes"),
            "used_memory_gb": record.get("used_memory_gb"),
            "exit_code": record.get("exit_code"),
            "working_directory": record.get("working_directory"),
            "command": record.get("command"),
        }

    def _ensure_partitions(self):
        """Create monthly partitions for the current month and next month if missing."""
        try:
            from dateutil.relativedelta import relativedelta
        except ImportError:
            logger.debug("python-dateutil not available, skipping auto-partition creation")
            return

        now = datetime.now(tz=timezone.utc)
        conn = self._get_conn()
        try:
            for delta in (0, 1):
                month_start = (
                    now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                    + relativedelta(months=delta)
                )
                month_end = month_start + relativedelta(months=1)
                table = f"job_snapshots_{month_start.strftime('%Y_%m')}"
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        CREATE TABLE IF NOT EXISTS {table}
                        PARTITION OF job_snapshots
                        FOR VALUES FROM (%(start)s) TO (%(end)s)
                        """,
                        {"start": month_start.isoformat(), "end": month_end.isoformat()},
                    )
                conn.commit()
                logger.debug("Ensured partition %s", table)
        except Exception as err:
            logger.warning("Failed to ensure partitions: %s", err)
            try:
                conn.rollback()
            except Exception:
                pass
        finally:
            self._release_conn(conn)

    def _ensure_users(self, conn, rows: list):
        from psycopg2.extras import execute_values

        usernames = sorted(
            {row["user_name"] for row in rows if row.get("user_name")}
        )
        if not usernames:
            for row in rows:
                row.setdefault("user_id", None)
            return

        payload = [(username,) for username in usernames]
        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO users (username, groups, created_at, updated_at)
                VALUES %s
                ON CONFLICT (username) DO NOTHING
                """,
                payload,
                template="(%s, '[]'::jsonb, NOW(), NOW())",
                page_size=len(payload),
            )
            cur.execute(
                "SELECT id, username FROM users WHERE username = ANY(%s)",
                (usernames,),
            )
            mapping = {username: user_id for user_id, username in cur.fetchall()}

        for row in rows:
            row["user_id"] = mapping.get(row.get("user_name"))

    def _flush(self):
        with self._lock:
            batch = self._pending[:]
            self._pending.clear()

        if not batch:
            return

        batch = _dedup(batch)
        failed = []
        for i in range(0, len(batch), BATCH_CHUNK):
            chunk = batch[i : i + BATCH_CHUNK]
            failed.extend(self._flush_chunk(chunk))

        if failed:
            logger.warning("Re-queuing %d failed job rows for retry", len(failed))
            with self._lock:
                self._pending = failed + self._pending

        logger.debug(
            "Persisted %d job snapshots (%d failed)",
            len(batch) - len(failed),
            len(failed),
        )

    def _flush_chunk(self, chunk: list) -> list:
        from psycopg2.extras import execute_values

        conn = self._get_conn()
        try:
            self._ensure_users(conn, chunk)
            db_chunk = [_prepare_db_row(row) for row in chunk]
            with conn.cursor() as cur:
                execute_values(
                    cur,
                    _UPSERT_SQL,
                    db_chunk,
                    template=_ROW_TEMPLATE,
                    page_size=len(db_chunk),
                )
            conn.commit()
            return []
        except Exception as bulk_err:
            logger.warning(
                "Bulk UPSERT failed for %d jobs, falling back to row-by-row: %s",
                len(chunk),
                bulk_err,
            )
            try:
                conn.rollback()
            except Exception:
                pass

            failed = []
            for row in chunk:
                try:
                    self._ensure_users(conn, [row])
                    db_row = _prepare_db_row(row)
                    with conn.cursor() as cur:
                        execute_values(
                            cur,
                            _UPSERT_SQL,
                            [db_row],
                            template=_ROW_TEMPLATE,
                            page_size=1,
                        )
                    conn.commit()
                except Exception as row_err:
                    logger.warning(
                        "Failed to upsert job_id=%s submit_time=%s: %s",
                        row.get("job_id"),
                        row.get("submit_time"),
                        row_err,
                    )
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    failed.append(row)
            return failed
        finally:
            self._release_conn(conn)

    def _maybe_cleanup(self, retention_days: int):
        now = time.time()
        if now - self._last_cleanup < 86400:
            return
        self._last_cleanup = now
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(_CLEANUP_SQL % retention_days)
                deleted = cur.rowcount
            conn.commit()
            if deleted:
                logger.info(
                    "Cleaned up %d job snapshot records older than %d days",
                    deleted,
                    retention_days,
                )
        except Exception as err:
            logger.error("Job persistence cleanup error: %s", err)
            try:
                conn.rollback()
            except Exception:
                pass
        finally:
            self._release_conn(conn)
