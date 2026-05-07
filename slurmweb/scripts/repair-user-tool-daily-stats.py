#!/usr/bin/env python3

import argparse
import re
import sys
from datetime import date
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
    ToolNameMapper,
    aggregate_user_tool_daily_rows,
)


def parse_date(value):
    try:
        return date.fromisoformat(value)
    except ValueError as err:
        raise argparse.ArgumentTypeError("expected YYYY-MM-DD") from err


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Rebuild user_tool_daily_stats from persisted job_snapshots for a date range."
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
    parser.add_argument("--start", type=parse_date, required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", type=parse_date, required=True, help="End date YYYY-MM-DD")
    parser.add_argument("--user", help="Optional username to rebuild")
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing")
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
    args = parser.parse_args()
    if args.start > args.end:
        parser.error("--start must be earlier than or equal to --end")
    return args


def load_settings(args):
    settings = RuntimeSettings.yaml_definition(args.conf_defs)
    settings.override_ini(args.conf)
    if hasattr(settings.database, "enabled") and not settings.database.enabled:
        raise RuntimeError("[database].enabled is false; nothing can be rebuilt")
    user_metrics = getattr(settings, "user_metrics", SimpleNamespace())
    return SimpleNamespace(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.database,
        user=settings.database.user,
        password=settings.database.password,
        tool_mapping_file=args.mapping_file or getattr(user_metrics, "tool_mapping_file", None),
    )


def terminal_where_clause():
    clause = " OR ".join(["UPPER(js.job_state) LIKE %s"] * len(TERMINAL_STATES))
    return clause, [f"%{state}%" for state in TERMINAL_STATES]


def completed_rows(conn, start_date, end_date, username=None):
    import psycopg2.extras

    where_terminal, terminal_params = terminal_where_clause()
    user_filter = "AND u.username = %s" if username else ""
    params = []
    if username:
        params.append(username)
    params.extend([start_date, end_date])
    params.extend(terminal_params)
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT DISTINCT ON (js.job_id, js.submit_time)
                DATE(COALESCE(js.end_time, js.last_seen) AT TIME ZONE 'UTC') AS activity_date,
                js.user_id,
                u.username,
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
                js.last_seen,
                js.usage_stats
            FROM job_snapshots js
            INNER JOIN users u ON u.id = js.user_id
            WHERE js.user_id IS NOT NULL
              {user_filter}
              AND COALESCE(js.end_time, js.last_seen) IS NOT NULL
              AND DATE(COALESCE(js.end_time, js.last_seen) AT TIME ZONE 'UTC') >= %s
              AND DATE(COALESCE(js.end_time, js.last_seen) AT TIME ZONE 'UTC') <= %s
              AND (
            """.format(user_filter=user_filter)
            + where_terminal
            + """
              )
            ORDER BY js.job_id, js.submit_time, js.last_seen DESC
            """,
            params,
        )
        return list(cur.fetchall())


def count_target_rows(conn, start_date, end_date, username=None):
    user_filter = "AND u.username = %s" if username else ""
    params = [start_date, end_date]
    if username:
        params.append(username)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*)::int
            FROM user_tool_daily_stats uds
            INNER JOIN users u ON u.id = uds.user_id
            WHERE uds.activity_date >= %s
              AND uds.activity_date <= %s
              {user_filter}
            """.format(user_filter=user_filter),
            params,
        )
        return cur.fetchone()[0]


def replace_target_rows(conn, start_date, end_date, payload, username=None):
    from psycopg2.extras import execute_values

    user_filter = "AND u.username = %s" if username else ""
    params = []
    if username:
        params.append(username)
    params.extend([start_date, end_date])
    with conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM user_tool_daily_stats uds
            USING users u
            WHERE u.id = uds.user_id
              {user_filter}
              AND uds.activity_date >= %s
              AND uds.activity_date <= %s
            """.format(user_filter=user_filter),
            params,
        )
        deleted = cur.rowcount
        if payload:
            execute_values(
                cur,
                """
                INSERT INTO user_tool_daily_stats (
                    activity_date,
                    user_id,
                    tool,
                    jobs_count,
                    avg_memory_gb,
                    max_memory_gb,
                    median_memory_gb,
                    avg_cpu_cores,
                    avg_runtime_seconds,
                    created_at,
                    updated_at
                ) VALUES %s
                ON CONFLICT (activity_date, user_id, tool) DO UPDATE SET
                    jobs_count = EXCLUDED.jobs_count,
                    avg_memory_gb = EXCLUDED.avg_memory_gb,
                    max_memory_gb = EXCLUDED.max_memory_gb,
                    median_memory_gb = EXCLUDED.median_memory_gb,
                    avg_cpu_cores = EXCLUDED.avg_cpu_cores,
                    avg_runtime_seconds = EXCLUDED.avg_runtime_seconds,
                    updated_at = NOW()
                """,
                payload,
                template=(
                    "(%(activity_date)s, %(user_id)s, %(tool)s, %(jobs_count)s, "
                    "%(avg_memory_gb)s, %(max_memory_gb)s, %(median_memory_gb)s, "
                    "%(avg_cpu_cores)s, %(avg_runtime_seconds)s, NOW(), NOW())"
                ),
                page_size=1000,
            )
    return deleted


def rebuild(conn, args, db_settings):
    mapper = ToolNameMapper(db_settings.tool_mapping_file)
    raw_mapper = ToolNameMapper()
    payload, _ = aggregate_user_tool_daily_rows(
        completed_rows(conn, args.start, args.end, username=args.user),
        mapper,
        raw_mapper=raw_mapper,
        rewrite_pattern=re.compile(args.rewrite_pattern),
        rewrite_tool=args.rewrite_tool.strip().lower() or "regr",
    )
    existing = count_target_rows(conn, args.start, args.end, username=args.user)
    if args.dry_run:
        return {"source_jobs": sum(item["jobs_count"] for item in payload), "deleted": existing, "inserted": len(payload)}
    deleted = replace_target_rows(conn, args.start, args.end, payload, username=args.user)
    conn.commit()
    return {"source_jobs": sum(item["jobs_count"] for item in payload), "deleted": deleted, "inserted": len(payload)}


def main():
    import psycopg2

    args = parse_args()
    db_settings = load_settings(args)
    conn = psycopg2.connect(**psycopg_connect_kwargs(db_settings))
    try:
        result = rebuild(conn, args, db_settings)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    mode = "dry-run" if args.dry_run else "rebuilt"
    user = args.user or "*"
    print(
        "user_tool_daily_stats {mode}: start={start} end={end} user={user} "
        "source_jobs={source_jobs} deleted={deleted} inserted={inserted}".format(
            mode=mode,
            start=args.start,
            end=args.end,
            user=user,
            **result,
        )
    )


if __name__ == "__main__":
    main()
