# Copyright (c) 2024 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

"""
Job history persistence module.

Runs a background thread that periodically snapshots active jobs and writes
them to PostgreSQL via UPSERT.  The main request path is never blocked.

Key design decisions:
- Only jobs with both job_id AND submit_time are persisted (others are skipped).
- Table is partitioned by submit_time (monthly) for query performance at scale.
- Bulk UPSERT via execute_values() for throughput; falls back to row-by-row on error.
- A SimpleConnectionPool keeps 1-3 long-lived connections to avoid reconnect overhead.
- _extract() runs in the calling thread (submit()) to spread CPU load.
- Background thread starts an immediate snapshot on startup, then repeats every
  snapshot_interval seconds.
"""

import threading
import logging
import time
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

TERMINAL_STATES = frozenset([
    "COMPLETED", "FAILED", "CANCELLED", "TIMEOUT",
    "NODE_FAIL", "DEADLINE", "OUT_OF_MEMORY", "PREEMPTED", "BOOT_FAIL",
])

BATCH_CHUNK = 500  # rows per execute_values() call

# ---------------------------------------------------------------------------
# SQL templates
# ---------------------------------------------------------------------------

# Bulk UPSERT for jobs that have a non-NULL submit_time.
# Conflict target: (job_id, submit_time) unique index.
_UPSERT_SQL = """
INSERT INTO job_snapshots (
    job_id, submit_time,
    first_seen, last_seen,
    job_name, job_state, state_reason,
    user_name, account, "group", partition, qos,
    nodes, node_count, cpus, priority,
    tres_req_str, tres_per_job, tres_per_node, gres_detail,
    start_time, end_time, time_limit_minutes,
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
    exit_code          = EXCLUDED.exit_code,
    gres_detail        = EXCLUDED.gres_detail,
    partition          = EXCLUDED.partition,
    qos                = EXCLUDED.qos,
    time_limit_minutes = EXCLUDED.time_limit_minutes,
    working_directory  = EXCLUDED.working_directory,
    command            = EXCLUDED.command
"""

# Template for execute_values – one tuple per row, matching column order above.
_ROW_TEMPLATE = "(%(job_id)s, %(submit_time)s, NOW(), NOW(), %(job_name)s, %(job_state)s, %(state_reason)s, %(user_name)s, %(account)s, %(group)s, %(partition)s, %(qos)s, %(nodes)s, %(node_count)s, %(cpus)s, %(priority)s, %(tres_req_str)s, %(tres_per_job)s, %(tres_per_node)s, %(gres_detail)s, %(start_time)s, %(end_time)s, %(time_limit_minutes)s, %(exit_code)s, %(working_directory)s, %(command)s)"

_CLEANUP_SQL = "DELETE FROM job_snapshots WHERE submit_time < NOW() - INTERVAL '%s days'"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ts(value):
    """Convert a Slurm epoch integer to a timezone-aware datetime, or None."""
    if not value or value <= 0:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (OSError, OverflowError, ValueError):
        return None


def _extract(job: dict) -> dict:
    """Extract and normalise fields from a raw slurmrestd job dict."""
    states = job.get("job_state", [])
    state_str = ",".join(states) if isinstance(states, list) else str(states)

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


def _dedup(rows: list) -> list:
    """Keep only the last occurrence of each (job_id, submit_time) in a batch."""
    seen = {}
    for row in rows:
        seen[(row["job_id"], row["submit_time"])] = row
    return list(seen.values())


# ---------------------------------------------------------------------------
# JobsStore
# ---------------------------------------------------------------------------

class JobsStore:
    """
    Manages PostgreSQL persistence for job snapshots.

    Usage:
        store = JobsStore(settings, slurmrestd)
        store.start()           # start background thread
        store.submit(jobs_list) # called from /jobs view (optional supplement)
        store.query(filters)    # called from /jobs/history view
        store.stop()            # on shutdown (optional)
    """

    def __init__(self, settings, slurmrestd=None):
        self._settings = settings
        self._slurmrestd = slurmrestd
        self._lock = threading.Lock()
        self._pending: list = []
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_cleanup = 0.0
        self._pool = None  # initialised lazily in background thread

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self):
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
        Extracts fields immediately and enqueues valid rows.
        Jobs missing job_id or submit_time are silently skipped.
        """
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
        if valid:
            with self._lock:
                self._pending.extend(valid)

    def query(self, filters: dict) -> dict:
        """Query job_snapshots with optional filters."""
        import psycopg2.extras

        page = max(1, int(filters.get("page", 1)))
        page_size = min(500, max(1, int(filters.get("page_size", 100))))
        offset = (page - 1) * page_size

        where_clauses, params = [], []

        if filters.get("start"):
            where_clauses.append("submit_time >= %s")
            params.append(filters["start"])
        if filters.get("end"):
            where_clauses.append("submit_time <= %s")
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

        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(f"SELECT COUNT(*) FROM job_snapshots {where_sql}", params)
                total = cur.fetchone()["count"]
                cur.execute(
                    f"SELECT * FROM job_snapshots {where_sql} "
                    f"ORDER BY submit_time DESC LIMIT %s OFFSET %s",
                    params + [page_size, offset],
                )
                rows = cur.fetchall()
        finally:
            self._release_conn(conn)

        jobs_out = []
        for row in rows:
            d = dict(row)
            for k, v in d.items():
                if isinstance(v, datetime):
                    d[k] = v.isoformat()
            jobs_out.append(d)

        return {"total": total, "page": page, "page_size": page_size, "jobs": jobs_out}

    def get_by_id(self, record_id: int) -> Optional[dict]:
        import psycopg2.extras

        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM job_snapshots WHERE id = %s", (record_id,))
                row = cur.fetchone()
        finally:
            self._release_conn(conn)

        if row is None:
            return None
        d = dict(row)
        for k, v in d.items():
            if isinstance(v, datetime):
                d[k] = v.isoformat()
        return d

    # ------------------------------------------------------------------
    # Connection pool
    # ------------------------------------------------------------------

    def _init_pool(self):
        import psycopg2.pool

        s = self._settings
        self._pool = psycopg2.pool.SimpleConnectionPool(
            1, 3,
            host=s.host,
            port=s.port,
            dbname=s.database,
            user=s.user,
            password=s.password,
        )
        logger.debug("PostgreSQL connection pool initialised")

    def _get_conn(self):
        if self._pool is None:
            self._init_pool()
        return self._pool.getconn()

    def _release_conn(self, conn):
        if self._pool is not None:
            self._pool.putconn(conn)

    # ------------------------------------------------------------------
    # Background thread
    # ------------------------------------------------------------------

    def _run(self):
        interval = getattr(self._settings, "snapshot_interval", 60)
        retention = getattr(self._settings, "retention_days", 180)

        # Initialise pool inside the thread so psycopg2 connections are
        # owned by the thread that uses them.
        try:
            self._init_pool()
        except Exception as e:
            logger.error("Failed to initialise DB connection pool: %s", e)
            return

        # Ensure partitions exist before first write
        self._ensure_partitions()

        # Immediate first snapshot
        self._scheduled_snapshot()
        self._flush()

        while not self._stop_event.wait(timeout=interval):
            self._ensure_partitions()
            self._scheduled_snapshot()
            self._flush()
            self._maybe_cleanup(retention)

        # Final flush on shutdown
        self._flush()

    def _scheduled_snapshot(self):
        """Fetch all current jobs from slurmrestd (unfiltered) and enqueue them."""
        if self._slurmrestd is None:
            return
        try:
            # Use jobs_unfiltered() to get complete field set for persistence
            if hasattr(self._slurmrestd, "jobs_unfiltered"):
                jobs = self._slurmrestd.jobs_unfiltered()
            else:
                jobs = self._slurmrestd.jobs()
            self.submit(jobs)
            logger.debug("Scheduled snapshot: fetched %d jobs", len(jobs))
        except Exception as e:
            logger.warning("Scheduled snapshot failed: %s", e)

    # ------------------------------------------------------------------
    # Partition management
    # ------------------------------------------------------------------

    def _ensure_partitions(self):
        """Create monthly partitions for the current month and next month if missing."""
        try:
            from dateutil.relativedelta import relativedelta
        except ImportError:
            # dateutil not available – skip auto-partition creation
            logger.debug("python-dateutil not available, skipping auto-partition creation")
            return

        now = datetime.now(tz=timezone.utc)
        conn = self._get_conn()
        try:
            for delta in (0, 1):
                month_start = (now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                               + relativedelta(months=delta))
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
        except Exception as e:
            logger.warning("Failed to ensure partitions: %s", e)
            try:
                conn.rollback()
            except Exception:
                pass
        finally:
            self._release_conn(conn)

    # ------------------------------------------------------------------
    # Flush logic
    # ------------------------------------------------------------------

    def _flush(self):
        with self._lock:
            batch = self._pending[:]
            self._pending.clear()

        if not batch:
            return

        # Deduplicate within this batch
        batch = _dedup(batch)

        failed = []
        for i in range(0, len(batch), BATCH_CHUNK):
            chunk = batch[i: i + BATCH_CHUNK]
            chunk_failed = self._flush_chunk(chunk)
            failed.extend(chunk_failed)

        if failed:
            logger.warning("Re-queuing %d failed job rows for retry", len(failed))
            with self._lock:
                self._pending = failed + self._pending

        logger.debug("Persisted %d job snapshots (%d failed)", len(batch) - len(failed), len(failed))

    def _flush_chunk(self, chunk: list) -> list:
        """
        Attempt bulk UPSERT for a chunk.  On failure, fall back to row-by-row
        without rolling back successfully committed rows.
        Returns list of rows that ultimately failed.
        """
        from psycopg2.extras import execute_values

        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                execute_values(cur, _UPSERT_SQL, chunk, template=_ROW_TEMPLATE, page_size=len(chunk))
            conn.commit()
            return []
        except Exception as bulk_err:
            logger.warning(
                "Bulk UPSERT failed for %d jobs, falling back to row-by-row: %s",
                len(chunk), bulk_err,
            )
            try:
                conn.rollback()
            except Exception:
                pass

            # Row-by-row fallback – each row is its own transaction
            failed = []
            for row in chunk:
                try:
                    with conn.cursor() as cur:
                        execute_values(
                            cur, _UPSERT_SQL, [row],
                            template=_ROW_TEMPLATE, page_size=1,
                        )
                    conn.commit()
                except Exception as row_err:
                    logger.warning(
                        "Failed to upsert job_id=%s submit_time=%s: %s",
                        row.get("job_id"), row.get("submit_time"), row_err,
                    )
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    failed.append(row)
            return failed
        finally:
            self._release_conn(conn)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

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
                    deleted, retention_days,
                )
        except Exception as e:
            logger.error("Job persistence cleanup error: %s", e)
            try:
                conn.rollback()
            except Exception:
                pass
        finally:
            self._release_conn(conn)
