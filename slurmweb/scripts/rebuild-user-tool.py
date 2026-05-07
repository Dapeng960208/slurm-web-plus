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
from slurmweb.persistence.jobs_store import JobsStore
from slurmweb.persistence.user_analytics_store import (
    aggregate_user_tool_daily_rows,
    ToolNameMapper,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Delete all user_tool_daily_stats rows and rebuild daily tool stats "
            "from job_snapshots. Run from the repository root with: "
            "python slurmweb/scripts/rebuild-user-tool.py"
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


def aggregate_daily_rows(rows, mapped_mapper, raw_mapper, rewrite_pattern, rewrite_tool):
    payload, stats = aggregate_user_tool_daily_rows(
        rows,
        mapped_mapper,
        raw_mapper=raw_mapper,
        rewrite_pattern=rewrite_pattern,
        rewrite_tool=rewrite_tool,
    )
    usernames = {}
    for row in rows:
        username = row.get("username")
        if username:
            usernames[row.get("user_id")] = username
    for item in payload:
        item["username"] = usernames.get(item["user_id"])
    return payload, stats


def completed_rows_for_rebuild_day(jobs_store, activity_date):
    rows = jobs_store.completed_job_rows_for_activity_date(activity_date)
    normalized_rows = []
    for row in rows:
        normalized_row = dict(row)
        normalized_row["activity_date"] = activity_date
        normalized_rows.append(normalized_row)
    return normalized_rows


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
    return rows_deleted


def _format_metric(value):
    if value is None:
        return "null"
    return str(value)


def print_rebuild_day_summary(activity_date, source_rows, rows_to_insert, stats=None):
    stats = stats or {}
    print(
        "user_tool_daily_stats day: date={date} source_jobs={source_jobs} counted={counted} "
        "skipped_memory={skipped_memory} missing_identity={missing_identity} "
        "cpu_missing={cpu_missing} runtime_missing={runtime_missing} rows={rows}".format(
            date=activity_date,
            source_jobs=source_rows,
            counted=stats.get("rows_counted", "-"),
            skipped_memory=stats.get("rows_skipped_memory", "-"),
            missing_identity=stats.get("rows_missing_identity", "-"),
            cpu_missing=stats.get("cpu_missing", "-"),
            runtime_missing=stats.get("runtime_missing", "-"),
            rows=len(rows_to_insert),
        )
    )


def print_rebuild_row(item):
    print(
        "user_tool_daily_stats row: date={date} user_id={user_id} username={username} "
        "tool={tool} jobs_count={jobs_count} avg_memory_gb={avg_memory_gb} "
        "max_memory_gb={max_memory_gb} "
        "median_memory_gb={median_memory_gb} avg_cpu_cores={avg_cpu_cores} "
        "avg_runtime_seconds={avg_runtime_seconds}".format(
            date=item["activity_date"],
            user_id=item["user_id"],
            username=item.get("username") or "-",
            tool=item["tool"],
            jobs_count=item["jobs_count"],
            avg_memory_gb=_format_metric(item.get("avg_memory_gb")),
            max_memory_gb=_format_metric(item.get("max_memory_gb")),
            median_memory_gb=_format_metric(item.get("median_memory_gb")),
            avg_cpu_cores=_format_metric(item.get("avg_cpu_cores")),
            avg_runtime_seconds=_format_metric(item.get("avg_runtime_seconds")),
        )
    )


def print_rebuild_preview(start_date, end_date, days, source_jobs, rows_deleted, rows_inserted):
    print(
        "user_tool_daily_stats preview: start={start} end={end} days={days} "
        "source_jobs={source_jobs} delete_rows={deleted} insert_rows={inserted}".format(
            start=start_date or "-",
            end=end_date or "-",
            days=days,
            source_jobs=source_jobs,
            deleted=rows_deleted,
            inserted=rows_inserted,
        )
    )


def rebuild(conn, args):
    db_settings = load_settings(args)
    jobs_store = JobsStore(db_settings, slurmrestd=None)
    rewrite_pattern = re.compile(args.rewrite_pattern)
    rewrite_tool = args.rewrite_tool.strip().lower() or "regr"
    mapped_mapper = ToolNameMapper(db_settings.tool_mapping_file)
    raw_mapper = ToolNameMapper()

    first_date, last_date = jobs_store.completed_date_bounds()
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
        rows = completed_rows_for_rebuild_day(jobs_store, cursor)
        source_jobs += len(rows)
        day_payload, day_stats = aggregate_daily_rows(
            rows,
            mapped_mapper,
            raw_mapper,
            rewrite_pattern,
            rewrite_tool,
        )
        print_rebuild_day_summary(cursor, len(rows), day_payload, day_stats)
        for item in day_payload:
            print_rebuild_row(item)
        payload.extend(day_payload)
        cursor += timedelta(days=1)
        days += 1

    rows_deleted = count_existing_rows(conn)
    print_rebuild_preview(first_date, last_date, days, source_jobs, rows_deleted, len(payload))
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
