# Copyright (c) 2024 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

"""
Job history persistence module.

Runs a background thread that periodically snapshots active jobs and writes
terminal-state jobs once to PostgreSQL.  The main request path is never blocked.
"""

import threading
import logging
import time
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# States considered terminal – once seen, a job is never written again.
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

# UPSERT: 以 (job_id, submit_time) 为唯一键。
# 若记录已存在则更新可变字段；不存在则插入。
# submit_time 为 NULL 的作业（极少数情况）会退化为每次 INSERT，
# 因为 NULL != NULL，UNIQUE 索引不会触发冲突。
_UPSERT_SQL = """
INSERT INTO job_snapshots (
    snapshot_time, job_id, job_name, job_state, state_reason,
    user_name, account, "group", partition, qos,
    nodes, node_count, cpus, priority,
    tres_req_str, tres_per_job, tres_per_node, gres_detail,
    submit_time, start_time, end_time, time_limit_minutes,
    exit_code, working_directory, command
) VALUES (
    NOW(), %(job_id)s, %(job_name)s, %(job_state)s, %(state_reason)s,
    %(user_name)s, %(account)s, %(group)s, %(partition)s, %(qos)s,
    %(nodes)s, %(node_count)s, %(cpus)s, %(priority)s,
    %(tres_req_str)s, %(tres_per_job)s, %(tres_per_node)s, %(gres_detail)s,
    %(submit_time)s, %(start_time)s, %(end_time)s, %(time_limit_minutes)s,
    %(exit_code)s, %(working_directory)s, %(command)s
)
ON CONFLICT (job_id, submit_time) DO UPDATE SET
    snapshot_time      = NOW(),
    job_state          = EXCLUDED.job_state,
    state_reason       = EXCLUDED.state_reason,
    nodes              = EXCLUDED.nodes,
    node_count         = EXCLUDED.node_count,
    cpus               = EXCLUDED.cpus,
    priority           = EXCLUDED.priority,
    start_time         = EXCLUDED.start_time,
    end_time           = EXCLUDED.end_time,
    exit_code          = EXCLUDED.exit_code,
    gres_detail        = EXCLUDED.gres_detail
"""

_CLEANUP_SQL = "DELETE FROM job_snapshots WHERE snapshot_time < NOW() - INTERVAL '%s days'"


def _ts(value):
    """Convert a Slurm epoch integer to a timezone-aware datetime, or None."""
    if not value or value <= 0:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (OSError, OverflowError, ValueError):
        return None


def _extract(job: dict) -> dict:
    """Extract the fields we care about from a raw slurmrestd job dict."""
    states = job.get("job_state", [])
    if isinstance(states, list):
        state_str = ",".join(states)
    else:
        state_str = str(states)

    # tres fields may be dicts or strings depending on slurmrestd version
    def _tres_str(v):
        if isinstance(v, dict):
            return ",".join(f"{k}={val}" for k, val in v.items())
        return str(v) if v else None

    gres_detail = job.get("gres_detail", [])
    if isinstance(gres_detail, list):
        gres_str = ",".join(gres_detail) if gres_detail else None
    else:
        gres_str = str(gres_detail) if gres_detail else None

    exit_code = job.get("exit_code", {})
    if isinstance(exit_code, dict):
        exit_str = f"{exit_code.get('return_code', '')}:{exit_code.get('signal', {}).get('signal_id', '')}"
    else:
        exit_str = str(exit_code) if exit_code else None

    # node_count / cpus may be nested dicts in newer slurmrestd
    def _int_field(v):
        if isinstance(v, dict):
            return v.get("number") or v.get("set") or None
        try:
            return int(v) if v is not None else None
        except (TypeError, ValueError):
            return None

    return {
        "job_id": job.get("job_id"),
        "job_name": job.get("name"),
        "job_state": state_str,
        "state_reason": job.get("state_reason"),
        "user_name": job.get("user_name"),
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
        "gres_detail": gres_str,
        "submit_time": _ts(job.get("submit_time")),
        "start_time": _ts(job.get("start_time")),
        "end_time": _ts(job.get("end_time")),
        "time_limit_minutes": _int_field(job.get("time_limit")),
        "exit_code": exit_str,
        "working_directory": job.get("current_working_directory"),
        "command": job.get("command"),
    }


class JobsStore:
    """
    Manages PostgreSQL persistence for job snapshots.

    Usage:
        store = JobsStore(settings)
        store.start()                    # start background thread
        store.submit(jobs_list)          # called from /jobs view
        store.query(filters) -> dict     # called from /jobs/history view
        store.stop()                     # on shutdown (optional)
    """

    def __init__(self, settings, slurmrestd=None):
        self._settings = settings
        self._slurmrestd = slurmrestd   # optional: used for scheduled snapshots
        self._lock = threading.Lock()
        self._pending: list = []          # jobs waiting to be written
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_cleanup = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self):
        """Start the background writer thread."""
        self._thread = threading.Thread(
            target=self._run, name="jobs-store-writer", daemon=True
        )
        self._thread.start()
        logger.info("Job history persistence thread started")

    def stop(self):
        self._stop_event.set()

    def submit(self, jobs: list):
        """
        Called from the /jobs view after slurmrestd returns data.
        Enqueues all jobs for UPSERT (database handles deduplication).
        """
        with self._lock:
            for job in jobs:
                if job.get("job_id") is not None:
                    self._pending.append(job)

    def get_by_id(self, record_id: int) -> Optional[dict]:
        """Return a single job_snapshots row by primary key, or None."""
        import psycopg2
        import psycopg2.extras

        conn = self._connect()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM job_snapshots WHERE id = %s", (record_id,))
                row = cur.fetchone()
        finally:
            conn.close()

        if row is None:
            return None
        d = dict(row)
        for k, v in d.items():
            if isinstance(v, datetime):
                d[k] = v.isoformat()
        return d

    def query(self, filters: dict) -> dict:
        """
        Query job_snapshots with optional filters.
        filters keys: start, end, user, account, partition, qos, state, job_id,
                      page (1-based), page_size
        Returns {"total": N, "page": P, "page_size": S, "jobs": [...]}
        """
        import psycopg2
        import psycopg2.extras

        page = max(1, int(filters.get("page", 1)))
        page_size = min(500, max(1, int(filters.get("page_size", 100))))
        offset = (page - 1) * page_size

        where_clauses = []
        params = []

        if filters.get("start"):
            where_clauses.append("snapshot_time >= %s")
            params.append(filters["start"])
        if filters.get("end"):
            where_clauses.append("snapshot_time <= %s")
            params.append(filters["end"])
        if filters.get("user"):
            where_clauses.append("user_name = %s")
            params.append(filters["user"])
        if filters.get("account"):
            where_clauses.append("account = %s")
            params.append(filters["account"])
        if filters.get("partition"):
            where_clauses.append("partition = %s")
            params.append(filters["partition"])
        if filters.get("qos"):
            where_clauses.append("qos = %s")
            params.append(filters["qos"])
        if filters.get("state"):
            where_clauses.append("job_state LIKE %s")
            params.append(f"%{filters['state']}%")
        if filters.get("job_id"):
            where_clauses.append("job_id = %s")
            params.append(int(filters["job_id"]))

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        conn = self._connect()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    f"SELECT COUNT(*) FROM job_snapshots {where_sql}",
                    params,
                )
                total = cur.fetchone()["count"]

                cur.execute(
                    f"SELECT * FROM job_snapshots {where_sql} "
                    f"ORDER BY snapshot_time DESC LIMIT %s OFFSET %s",
                    params + [page_size, offset],
                )
                rows = cur.fetchall()
        finally:
            conn.close()

        # Convert datetime objects to ISO strings for JSON serialisation
        jobs_out = []
        for row in rows:
            d = dict(row)
            for k, v in d.items():
                if isinstance(v, datetime):
                    d[k] = v.isoformat()
            jobs_out.append(d)

        return {"total": total, "page": page, "page_size": page_size, "jobs": jobs_out}

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _connect(self):
        import psycopg2

        s = self._settings
        return psycopg2.connect(
            host=s.host,
            port=s.port,
            dbname=s.database,
            user=s.user,
            password=s.password,
        )

    def _run(self):
        """Background thread: snapshot jobs every snapshot_interval seconds."""
        interval = getattr(self._settings, "snapshot_interval", 60)
        retention = getattr(self._settings, "retention_days", 180)

        while not self._stop_event.wait(timeout=interval):
            self._scheduled_snapshot()
            self._flush()
            self._maybe_cleanup(retention)

        # Final flush on shutdown
        self._flush()

    def _scheduled_snapshot(self):
        """Proactively fetch all current jobs from slurmrestd and enqueue them."""
        if self._slurmrestd is None:
            return
        try:
            jobs = self._slurmrestd.jobs()
            self.submit(jobs)
            logger.debug("Scheduled snapshot: fetched %d jobs from slurmrestd", len(jobs))
        except Exception as e:
            logger.warning("Scheduled snapshot failed: %s", e)

    def _flush(self):
        with self._lock:
            batch = self._pending[:]
            self._pending.clear()

        if not batch:
            return

        try:
            import psycopg2

            conn = self._connect()
            try:
                with conn.cursor() as cur:
                    for job in batch:
                        try:
                            cur.execute(_UPSERT_SQL, _extract(job))
                        except Exception as e:
                            logger.warning(
                                "Failed to upsert job %s: %s",
                                job.get("job_id"),
                                e,
                            )
                conn.commit()
                logger.debug("Persisted %d job snapshots", len(batch))
            finally:
                conn.close()
        except Exception as e:
            logger.error("Job persistence flush error: %s", e)
            # Put failed jobs back so they are retried next cycle
            with self._lock:
                self._pending = batch + self._pending

    def _maybe_cleanup(self, retention_days: int):
        now = time.time()
        if now - self._last_cleanup < 86400:
            return
        self._last_cleanup = now
        try:
            conn = self._connect()
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
            finally:
                conn.close()
        except Exception as e:
            logger.error("Job persistence cleanup error: %s", e)
