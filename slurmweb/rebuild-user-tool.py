#!/usr/bin/env python3
# Temporary maintenance script. Remove after user_tool_daily_stats is rebuilt.

import argparse
import re
import sys
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace


PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rfl.settings import RuntimeSettings

from slurmweb.apps._defaults import SlurmwebAppDefaults
from slurmweb.models.db import psycopg_connect_kwargs
from slurmweb.persistence.jobs_store import TERMINAL_STATES
from slurmweb.persistence.user_analytics_store import (
    aggregate_user_tool_daily_rows,
    ToolNameMapper,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Delete all user_tool_daily_stats rows and rebuild daily tool stats "
            "from job_snapshots. Run from the backend directory with: "
            "python rebuild-user-tool.py"
        )
    )
    parser.add_argument(
        "--conf-defs",
        type=Path,
        default=SlurmwebAppDefaults.AGENT.settings_definition,
        help="Agent settings definition YAML (default: %(default)s)",
    )
    parser.add_argument(
        "--conf",
        type=Path,
        default=SlurmwebAppDefaults.AGENT.site_configuration,
        help="Agent site configuration INI (default: %(default)s)",
    )
    parser.add_argument(
        "--mapping-file",
        type=Path,
        help="Optional tool mapping YAML; defaults to [user_metrics].tool_mapping_file",
    )
    parser.add_argument(
        "--rewrite-pattern",
        default=r"^regr([_-].*)?$",
        help="Regex matching classified tool names to collapse (default: %(default)s)",
    )
    parser.add_argument(
        "--rewrite-tool",
        default="regr",
        help="Target tool name for matching rewrite-pattern values (default: regr)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would change without deleting or writing stats",
    )
    return parser.parse_args()


def load_settings(args):
    settings = RuntimeSettings.yaml_definition(args.conf_defs)
    settings.override_ini(args.conf)
    if hasattr(settings.database, "enabled") and not settings.database.enabled:
        raise RuntimeError("[database].enabled is false; nothing can be rebuilt")
    user_metrics = getattr(settings, "user_metrics", SimpleNamespace())
    mapping_file = args.mapping_file or getattr(user_metrics, "tool_mapping_file", None)
    return SimpleNamespace(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.database,
        user=settings.database.user,
        password=settings.database.password,
        tool_mapping_file=mapping_file,
    )


def terminal_where_clause():
    clause = " OR ".join(["UPPER(js.job_state) LIKE %s"] * len(TERMINAL_STATES))
    params = [f"%{state}%" for state in TERMINAL_STATES]
    return clause, params


def completed_date_bounds(conn):
    where_terminal, terminal_params = terminal_where_clause()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                MIN(DATE(COALESCE(js.end_time, js.last_seen) AT TIME ZONE 'UTC')) AS start_date,
                MAX(DATE(COALESCE(js.end_time, js.last_seen) AT TIME ZONE 'UTC')) AS end_date
            FROM job_snapshots js
            WHERE js.user_id IS NOT NULL
              AND COALESCE(js.end_time, js.last_seen) IS NOT NULL
              AND (
            """
            + where_terminal
            + """
              )
            """,
            terminal_params,
        )
        return cur.fetchone()


def completed_rows_for_date(conn, activity_date):
    import psycopg2.extras

    where_terminal, terminal_params = terminal_where_clause()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT DISTINCT ON (js.job_id, js.submit_time)
                DATE(COALESCE(js.end_time, js.last_seen) AT TIME ZONE 'UTC') AS activity_date,
                js.user_id,
                js.job_name,
                js.command,
                js.tres_req_str,
                js.tres_per_job,
                js.tres_per_node,
                js.tres_requested,
                js.tres_allocated,
                js.used_memory_gb,
                js.used_cpu_cores_avg,
                js.start_time,
                js.end_time,
                js.usage_stats
            FROM job_snapshots js
            WHERE js.user_id IS NOT NULL
              AND DATE(COALESCE(js.end_time, js.last_seen) AT TIME ZONE 'UTC') = %s
              AND (
            """
            + where_terminal
            + """
              )
            ORDER BY js.job_id, js.submit_time, js.last_seen DESC
            """,
            [activity_date] + terminal_params,
        )
        return list(cur.fetchall())


def aggregate_daily_rows(rows, mapped_mapper, raw_mapper, rewrite_pattern, rewrite_tool):
    return aggregate_user_tool_daily_rows(
        rows,
        mapped_mapper,
        raw_mapper=raw_mapper,
        rewrite_pattern=rewrite_pattern,
        rewrite_tool=rewrite_tool,
    )


def count_existing_rows(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*)::int FROM user_tool_daily_stats")
        return cur.fetchone()[0]


def replace_all_rows(conn, payload):
    from psycopg2.extras import execute_values

    with conn.cursor() as cur:
        cur.execute("DELETE FROM user_tool_daily_stats")
        rows_deleted = cur.rowcount
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
                    memory_samples,
                    cpu_samples,
                    runtime_samples,
                    created_at,
                    updated_at
                ) VALUES %s
                ON CONFLICT (activity_date, user_id, tool) DO UPDATE SET
                    jobs_count = EXCLUDED.jobs_count,
                    avg_max_memory_gb = EXCLUDED.avg_max_memory_gb,
                    avg_cpu_cores = EXCLUDED.avg_cpu_cores,
                    avg_runtime_seconds = EXCLUDED.avg_runtime_seconds,
                    memory_samples = EXCLUDED.memory_samples,
                    cpu_samples = EXCLUDED.cpu_samples,
                    runtime_samples = EXCLUDED.runtime_samples,
                    updated_at = NOW()
                """,
                payload,
                template=(
                    "(%(activity_date)s, %(user_id)s, %(tool)s, %(jobs_count)s, "
                    "%(avg_max_memory_gb)s, %(avg_cpu_cores)s, "
                    "%(avg_runtime_seconds)s, %(memory_samples)s, "
                    "%(cpu_samples)s, %(runtime_samples)s, NOW(), NOW())"
                ),
                page_size=1000,
            )
    return rows_deleted


def rebuild(conn, args):
    db_settings = load_settings(args)
    rewrite_pattern = re.compile(args.rewrite_pattern)
    rewrite_tool = args.rewrite_tool.strip().lower() or "regr"
    mapped_mapper = ToolNameMapper(db_settings.tool_mapping_file)
    raw_mapper = ToolNameMapper()

    first_date, last_date = completed_date_bounds(conn)
    if first_date is None or last_date is None:
        rows_deleted = count_existing_rows(conn)
        if not args.dry_run:
            rows_deleted = replace_all_rows(conn, [])
            conn.commit()
        return {
            "start_date": None,
            "end_date": None,
            "days": 0,
            "source_jobs": 0,
            "rows_deleted": rows_deleted,
            "rows_inserted": 0,
        }

    payload = []
    source_jobs = 0
    cursor = first_date
    days = 0
    while cursor <= last_date:
        rows = completed_rows_for_date(conn, cursor)
        source_jobs += len(rows)
        payload.extend(
            aggregate_daily_rows(
                rows,
                mapped_mapper,
                raw_mapper,
                rewrite_pattern,
                rewrite_tool,
            )
        )
        cursor += timedelta(days=1)
        days += 1

    rows_deleted = count_existing_rows(conn)
    if not args.dry_run:
        rows_deleted = replace_all_rows(conn, payload)
        conn.commit()

    return {
        "start_date": first_date,
        "end_date": last_date,
        "days": days,
        "source_jobs": source_jobs,
        "rows_deleted": rows_deleted,
        "rows_inserted": len(payload),
    }


def main():
    import psycopg2

    args = parse_args()
    db_settings = load_settings(args)
    conn = psycopg2.connect(**psycopg_connect_kwargs(db_settings))
    try:
        result = rebuild(conn, args)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    mode = "dry-run" if args.dry_run else "rebuilt"
    print(
        "user_tool_daily_stats {mode}: start={start} end={end} days={days} "
        "source_jobs={source_jobs} deleted={deleted} inserted={inserted}".format(
            mode=mode,
            start=result["start_date"] or "-",
            end=result["end_date"] or "-",
            days=result["days"],
            source_jobs=result["source_jobs"],
            deleted=result["rows_deleted"],
            inserted=result["rows_inserted"],
        )
    )


if __name__ == "__main__":
    main()
