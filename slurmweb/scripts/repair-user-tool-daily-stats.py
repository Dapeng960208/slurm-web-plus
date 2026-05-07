#!/usr/bin/env python3

import argparse
import re
import sys
from datetime import date, datetime, timedelta, timezone
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
    ToolNameMapper,
    aggregate_user_tool_daily_rows,
)
from slurmweb.slurmrestd import Slurmrestd
from slurmweb.slurmrestd.auth import SlurmrestdAuthentifier


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
        slurmrestd_uri=settings.slurmrestd.uri,
        slurmrestd_auth=settings.slurmrestd.auth,
        slurmrestd_jwt_mode=settings.slurmrestd.jwt_mode,
        slurmrestd_jwt_user=settings.slurmrestd.jwt_user,
        slurmrestd_jwt_key=settings.slurmrestd.jwt_key,
        slurmrestd_jwt_lifespan=settings.slurmrestd.jwt_lifespan,
        slurmrestd_jwt_token=settings.slurmrestd.jwt_token,
        slurmrestd_versions=settings.slurmrestd.versions,
        service_cluster=getattr(settings.service, "cluster", None),
    )


def make_slurmrestd(settings):
    return Slurmrestd(
        settings.slurmrestd_uri,
        SlurmrestdAuthentifier(
            settings.slurmrestd_auth,
            settings.slurmrestd_jwt_mode,
            settings.slurmrestd_jwt_user,
            settings.slurmrestd_jwt_key,
            settings.slurmrestd_jwt_lifespan,
            settings.slurmrestd_jwt_token,
        ),
        settings.slurmrestd_versions,
        cluster_name_hint=settings.service_cluster,
    )


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
    jobs_store = JobsStore(db_settings, slurmrestd=None)
    slurmrestd = make_slurmrestd(db_settings)
    mapper = ToolNameMapper(db_settings.tool_mapping_file)
    raw_mapper = ToolNameMapper()
    jobs_store.backfill_usage_fields(
        slurmrestd=slurmrestd,
        start_time=datetime.combine(args.start, datetime.min.time(), tzinfo=timezone.utc),
        end_time=datetime.combine(
            args.end + timedelta(days=1),
            datetime.min.time(),
            tzinfo=timezone.utc,
        ),
        username=args.user,
        dry_run=args.dry_run,
    )
    rows = jobs_store.completed_job_rows_for_activity_dates(
        args.start,
        args.end,
        username=args.user,
    )
    payload, _ = aggregate_user_tool_daily_rows(
        rows,
        mapper,
        raw_mapper=raw_mapper,
        rewrite_pattern=re.compile(args.rewrite_pattern),
        rewrite_tool=args.rewrite_tool.strip().lower() or "regr",
    )
    existing = count_target_rows(conn, args.start, args.end, username=args.user)
    if args.dry_run:
        return {"source_jobs": len(rows), "deleted": existing, "inserted": len(payload)}
    deleted = replace_target_rows(conn, args.start, args.end, payload, username=args.user)
    conn.commit()
    return {"source_jobs": len(rows), "deleted": deleted, "inserted": len(payload)}


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
