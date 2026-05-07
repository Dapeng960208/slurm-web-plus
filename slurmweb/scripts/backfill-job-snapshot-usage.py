#!/usr/bin/env python3

import argparse
import sys
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker


PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rfl.settings import RuntimeSettings

from slurmweb.apps._defaults import SlurmwebAppDefaults
from slurmweb.persistence.jobs_store import JobsStore, fetch_job_detail


def parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as err:
        raise argparse.ArgumentTypeError("expected YYYY-MM-DD") from err


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Backfill job_snapshots.used_memory_gb and used_cpu_cores_avg from "
            "Slurm REST job details for completed jobs."
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
    parser.add_argument("--start", type=parse_date, help="Submit date start YYYY-MM-DD")
    parser.add_argument("--end", type=parse_date, help="Submit date end YYYY-MM-DD")
    parser.add_argument("--user", help="Only backfill records for this username")
    parser.add_argument("--job-id", type=int, help="Only backfill this Slurm job id")
    parser.add_argument("--limit", type=int, help="Maximum records to scan")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print changes without updating job_snapshots",
    )
    args = parser.parse_args()
    if args.start and args.end and args.start > args.end:
        parser.error("--start must be earlier than or equal to --end")
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be greater than 0")
    return args


def load_settings(args):
    settings = RuntimeSettings.yaml_definition(args.conf_defs)
    settings.override_ini(args.conf)
    if hasattr(settings.database, "enabled") and not settings.database.enabled:
        raise RuntimeError("[database].enabled is false; nothing can be backfilled")
    return SimpleNamespace(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.database,
        user=settings.database.user,
        password=settings.database.password,
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
    from slurmweb.slurmrestd import Slurmrestd
    from slurmweb.slurmrestd.auth import SlurmrestdAuthentifier

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


def make_session_factory(settings):
    engine = sa.create_engine(sqlalchemy_url(settings), future=True)
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)


def _day_start(value):
    if value is None:
        return None
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def _day_end(value):
    if value is None:
        return None
    return datetime.combine(value + timedelta(days=1), time.min, tzinfo=timezone.utc)


def backfill_query(session, args):
    store = JobsStore(SimpleNamespace(host=None, port=None, database=None, user=None, password=None), slurmrestd=None)
    query = store.usage_backfill_rows_query(
        session,
        start_time=_day_start(args.start),
        end_time=_day_end(args.end),
        username=args.user,
        job_id=args.job_id,
        limit=args.limit,
        missing_only=True,
    )
    return query


def _format_value(value):
    if value is None:
        return "null"
    return str(value)


def _format_error(err):
    if err is None:
        return "null", "null"
    message = str(err).replace("\r", " ").replace("\n", " ")
    if len(message) > 240:
        message = message[:237] + "..."
    return err.__class__.__name__, message or "-"


def _print_row(
    snapshot,
    username,
    old_memory,
    new_memory,
    old_cpu,
    new_cpu,
    decision,
    reason,
    error=None,
):
    error_type, error_message = _format_error(error)
    print(
        "job_snapshot_usage row: id={id} job_id={job_id} username={username} "
        "old_memory={old_memory} new_memory={new_memory} old_cpu={old_cpu} "
        "new_cpu={new_cpu} decision={decision} reason={reason} "
        "error_type={error_type} error={error}".format(
            id=snapshot.id,
            job_id=snapshot.job_id,
            username=username or "-",
            old_memory=_format_value(old_memory),
            new_memory=_format_value(new_memory),
            old_cpu=_format_value(old_cpu),
            new_cpu=_format_value(new_cpu),
            decision=decision,
            reason=reason,
            error_type=error_type,
            error=error_message,
        )
    )


def backfill(session_factory, slurmrestd, args):
    store = JobsStore(
        SimpleNamespace(
            host=None,
            port=None,
            database=None,
            user=None,
            password=None,
        ),
        slurmrestd=None,
    )
    return store.backfill_usage_fields(
        slurmrestd=slurmrestd,
        start_time=_day_start(args.start),
        end_time=_day_end(args.end),
        username=args.user,
        job_id=args.job_id,
        limit=args.limit,
        dry_run=args.dry_run,
        session_factory=session_factory,
        logger_fn=lambda **kwargs: _print_row(
            kwargs["snapshot"],
            kwargs["username"],
            kwargs["old_memory"],
            kwargs["new_memory"],
            kwargs["old_cpu"],
            kwargs["new_cpu"],
            kwargs["decision"],
            kwargs["reason"],
            error=kwargs.get("error"),
        ),
    )


def main():
    args = parse_args()
    settings = load_settings(args)
    session_factory = make_session_factory(settings)
    slurmrestd = make_slurmrestd(settings)
    result = backfill(session_factory, slurmrestd, args)
    mode = "dry-run" if args.dry_run else "updated"
    print(
        "job_snapshot_usage {mode}: scanned={scanned} updated={updated} "
        "skipped={skipped}".format(mode=mode, **result)
    )


if __name__ == "__main__":
    main()
