# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = sa.Column(sa.BigInteger(), primary_key=True, autoincrement=True)
    username = sa.Column(sa.Text(), nullable=False, unique=True)
    fullname = sa.Column(sa.Text(), nullable=True)
    groups = sa.Column(
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=False,
        server_default=sa.text("'[]'::jsonb"),
    )
    ldap_synced_at = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True)
    created_at = sa.Column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sa.text("NOW()"),
    )
    updated_at = sa.Column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sa.text("NOW()"),
    )


class JobSnapshot(Base):
    __tablename__ = "job_snapshots"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", "submit_time"),
        sa.Index("idx_js_job_submit", "job_id", "submit_time", unique=True),
        sa.Index("idx_js_last_seen", sa.text("last_seen DESC")),
        sa.Index("idx_js_user_id", "user_id"),
        sa.Index("idx_js_account", "account"),
        sa.Index("idx_js_partition", "partition"),
        sa.Index("idx_js_job_state", "job_state"),
        {"postgresql_partition_by": "RANGE (submit_time)"},
    )

    id = sa.Column(sa.BigInteger(), autoincrement=True)
    job_id = sa.Column(sa.Integer(), nullable=False)
    submit_time = sa.Column(sa.TIMESTAMP(timezone=True), nullable=False)
    first_seen = sa.Column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sa.text("NOW()"),
    )
    last_seen = sa.Column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sa.text("NOW()"),
    )
    job_name = sa.Column(sa.Text(), nullable=True)
    job_state = sa.Column(sa.Text(), nullable=True)
    state_reason = sa.Column(sa.Text(), nullable=True)
    user_id = sa.Column(sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True)
    account = sa.Column(sa.Text(), nullable=True)
    group = sa.Column("group", sa.Text(), nullable=True)
    partition = sa.Column(sa.Text(), nullable=True)
    qos = sa.Column(sa.Text(), nullable=True)
    nodes = sa.Column(sa.Text(), nullable=True)
    node_count = sa.Column(sa.Integer(), nullable=True)
    cpus = sa.Column(sa.Integer(), nullable=True)
    priority = sa.Column(sa.Integer(), nullable=True)
    tres_req_str = sa.Column(sa.Text(), nullable=True)
    tres_per_job = sa.Column(sa.Text(), nullable=True)
    tres_per_node = sa.Column(sa.Text(), nullable=True)
    gres_detail = sa.Column(sa.Text(), nullable=True)
    tres_requested = sa.Column(postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    tres_allocated = sa.Column(postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    start_time = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True)
    end_time = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True)
    eligible_time = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True)
    last_sched_evaluation_time = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True)
    time_limit_minutes = sa.Column(sa.Integer(), nullable=True)
    used_memory_gb = sa.Column(sa.Float(), nullable=True)
    usage_stats = sa.Column(postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    used_cpu_cores_avg = sa.Column(sa.Float(), nullable=True)
    exit_code = sa.Column(sa.Text(), nullable=True)
    working_directory = sa.Column(sa.Text(), nullable=True)
    command = sa.Column(sa.Text(), nullable=True)
