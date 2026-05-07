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
from slurmweb.models.db import sqlalchemy_url
from slurmweb.models.modes import JobSnapshot, User
from slurmweb.persistence.jobs_store import _extract_detail, _is_not_found_error


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


def _snapshot_record(snapshot, username=None):
    return {
        "id": snapshot.id,
        "job_id": snapshot.job_id,
        "submit_time": snapshot.submit_time,
        "job_name": snapshot.job_name,
        "job_state": snapshot.job_state,
        "state_reason": snapshot.state_reason,
        "user_id": snapshot.user_id,
        "user_name": username,
        "account": snapshot.account,
        "group": snapshot.group,
        "partition": snapshot.partition,
        "qos": snapshot.qos,
        "nodes": snapshot.nodes,
        "node_count": snapshot.node_count,
        "cpus": snapshot.cpus,
        "priority": snapshot.priority,
        "tres_req_str": snapshot.tres_req_str,
        "tres_per_job": snapshot.tres_per_job,
        "tres_per_node": snapshot.tres_per_node,
        "gres_detail": snapshot.gres_detail,
        "tres_requested": snapshot.tres_requested,
        "tres_allocated": snapshot.tres_allocated,
        "start_time": snapshot.start_time,
        "end_time": snapshot.end_time,
        "eligible_time": snapshot.eligible_time,
        "last_sched_evaluation_time": snapshot.last_sched_evaluation_time,
        "time_limit_minutes": snapshot.time_limit_minutes,
        "used_memory_gb": snapshot.used_memory_gb,
        "usage_stats": snapshot.usage_stats,
        "used_cpu_cores_avg": snapshot.used_cpu_cores_avg,
        "exit_code": snapshot.exit_code,
        "working_directory": snapshot.working_directory,
        "command": snapshot.command,
    }


def backfill_query(session, args):
    query = (
        session.query(JobSnapshot, User.username)
        .outerjoin(User, User.id == JobSnapshot.user_id)
        .filter(sa.func.upper(JobSnapshot.job_state) == "COMPLETED")
        .filter(
            sa.or_(
                JobSnapshot.used_memory_gb.is_(None),
                JobSnapshot.used_cpu_cores_avg.is_(None),
            )
        )
    )
    if args.start:
        query = query.filter(JobSnapshot.submit_time >= _day_start(args.start))
    if args.end:
        query = query.filter(JobSnapshot.submit_time < _day_end(args.end))
    if args.user:
        query = query.filter(User.username == args.user)
    if args.job_id is not None:
        query = query.filter(JobSnapshot.job_id == args.job_id)
    query = query.order_by(JobSnapshot.submit_time.asc(), JobSnapshot.job_id.asc())
    if args.limit is not None:
        query = query.limit(args.limit)
    return query


def _format_value(value):
    if value is None:
        return "null"
    return str(value)


def _print_row(snapshot, username, old_memory, new_memory, old_cpu, new_cpu, decision, reason):
    print(
        "job_snapshot_usage row: id={id} job_id={job_id} username={username} "
        "old_memory={old_memory} new_memory={new_memory} old_cpu={old_cpu} "
        "new_cpu={new_cpu} decision={decision} reason={reason}".format(
            id=snapshot.id,
            job_id=snapshot.job_id,
            username=username or "-",
            old_memory=_format_value(old_memory),
            new_memory=_format_value(new_memory),
            old_cpu=_format_value(old_cpu),
            new_cpu=_format_value(new_cpu),
            decision=decision,
            reason=reason,
        )
    )


def _apply_detail(snapshot, username, detail):
    record = _snapshot_record(snapshot, username)
    row = _extract_detail(detail, record)
    if not row.get("job_id") or not row.get("submit_time"):
        return False, "missing_detail_key", None, None
    if row.get("submit_time") != snapshot.submit_time:
        return False, "submit_time_mismatch", None, None

    new_memory = row.get("used_memory_gb")
    new_cpu = row.get("used_cpu_cores_avg")
    memory_update = snapshot.used_memory_gb is None and new_memory is not None
    cpu_update = snapshot.used_cpu_cores_avg is None and new_cpu is not None
    if not memory_update and not cpu_update:
        if snapshot.used_memory_gb is None and new_memory is None:
            return False, "missing_used_memory_gb", new_memory, new_cpu
        if snapshot.used_cpu_cores_avg is None and new_cpu is None:
            return False, "missing_used_cpu_cores_avg", new_memory, new_cpu
        return False, "no_usage_updates", new_memory, new_cpu
    return True, "ok", new_memory, new_cpu


def backfill(session_factory, slurmrestd, args):
    scanned = 0
    updated = 0
    skipped = 0
    with session_factory() as session:
        rows = backfill_query(session, args).all()
        for snapshot, username in rows:
            scanned += 1
            old_memory = snapshot.used_memory_gb
            old_cpu = snapshot.used_cpu_cores_avg
            try:
                detail = slurmrestd.job(snapshot.job_id)
            except Exception as err:
                skipped += 1
                reason = "not_found" if _is_not_found_error(err) else "detail_error"
                _print_row(
                    snapshot,
                    username,
                    old_memory,
                    None,
                    old_cpu,
                    None,
                    "skipped",
                    reason,
                )
                continue

            can_update, reason, new_memory, new_cpu = _apply_detail(
                snapshot,
                username,
                detail,
            )
            if not can_update:
                skipped += 1
                _print_row(
                    snapshot,
                    username,
                    old_memory,
                    new_memory,
                    old_cpu,
                    new_cpu,
                    "skipped",
                    reason,
                )
                continue

            if not args.dry_run:
                if snapshot.used_memory_gb is None:
                    snapshot.used_memory_gb = new_memory
                if snapshot.used_cpu_cores_avg is None:
                    snapshot.used_cpu_cores_avg = new_cpu
            updated += 1
            _print_row(
                snapshot,
                username,
                old_memory,
                new_memory if old_memory is None else old_memory,
                old_cpu,
                new_cpu if old_cpu is None else old_cpu,
                "updated",
                reason,
            )

        if args.dry_run:
            session.rollback()
        else:
            session.commit()

    return {"scanned": scanned, "updated": updated, "skipped": skipped}


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
