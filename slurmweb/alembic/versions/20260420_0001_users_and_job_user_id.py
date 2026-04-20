# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260420_0001"
down_revision = None
branch_labels = None
depends_on = None


def _constraint_exists(bind, name):
    result = bind.execute(
        sa.text("SELECT 1 FROM pg_constraint WHERE conname = :name"),
        {"name": name},
    )
    return result.scalar() is not None


def _table_exists(bind, name):
    return sa.inspect(bind).has_table(name)


def upgrade():
    bind = op.get_bind()

    if not _table_exists(bind, "users"):
        op.create_table(
            "users",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("username", sa.Text(), nullable=False),
            sa.Column("fullname", sa.Text(), nullable=True),
            sa.Column(
                "groups",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
            sa.Column("ldap_synced_at", sa.TIMESTAMP(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.TIMESTAMP(timezone=True),
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
            sa.Column(
                "updated_at",
                sa.TIMESTAMP(timezone=True),
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
            sa.UniqueConstraint("username", name="uq_users_username"),
        )

    if not _table_exists(bind, "job_snapshots"):
        op.create_table(
            "job_snapshots",
            sa.Column("id", sa.BigInteger(), autoincrement=True),
            sa.Column("job_id", sa.Integer(), nullable=False),
            sa.Column("submit_time", sa.TIMESTAMP(timezone=True), nullable=False),
            sa.Column(
                "first_seen",
                sa.TIMESTAMP(timezone=True),
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
            sa.Column(
                "last_seen",
                sa.TIMESTAMP(timezone=True),
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
            sa.Column("job_name", sa.Text(), nullable=True),
            sa.Column("job_state", sa.Text(), nullable=True),
            sa.Column("state_reason", sa.Text(), nullable=True),
            sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("account", sa.Text(), nullable=True),
            sa.Column("group", sa.Text(), nullable=True),
            sa.Column("partition", sa.Text(), nullable=True),
            sa.Column("qos", sa.Text(), nullable=True),
            sa.Column("nodes", sa.Text(), nullable=True),
            sa.Column("node_count", sa.Integer(), nullable=True),
            sa.Column("cpus", sa.Integer(), nullable=True),
            sa.Column("priority", sa.Integer(), nullable=True),
            sa.Column("tres_req_str", sa.Text(), nullable=True),
            sa.Column("tres_per_job", sa.Text(), nullable=True),
            sa.Column("tres_per_node", sa.Text(), nullable=True),
            sa.Column("gres_detail", sa.Text(), nullable=True),
            sa.Column("start_time", sa.TIMESTAMP(timezone=True), nullable=True),
            sa.Column("end_time", sa.TIMESTAMP(timezone=True), nullable=True),
            sa.Column("time_limit_minutes", sa.Integer(), nullable=True),
            sa.Column("exit_code", sa.Text(), nullable=True),
            sa.Column("working_directory", sa.Text(), nullable=True),
            sa.Column("command", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("id", "submit_time"),
            postgresql_partition_by="RANGE (submit_time)",
        )
    else:
        bind.execute(sa.text("ALTER TABLE job_snapshots ADD COLUMN IF NOT EXISTS user_id BIGINT"))
        if not _constraint_exists(bind, "fk_job_snapshots_user_id"):
            bind.execute(
                sa.text(
                    """
                    ALTER TABLE job_snapshots
                    ADD CONSTRAINT fk_job_snapshots_user_id
                    FOREIGN KEY (user_id) REFERENCES users(id)
                    """
                )
            )
        bind.execute(sa.text("DROP INDEX IF EXISTS idx_js_user_name"))
        bind.execute(sa.text('ALTER TABLE job_snapshots DROP COLUMN IF EXISTS user_name'))

    for statement in (
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_js_job_submit ON job_snapshots (job_id, submit_time)",
        "CREATE INDEX IF NOT EXISTS idx_js_last_seen ON job_snapshots (last_seen DESC)",
        "CREATE INDEX IF NOT EXISTS idx_js_user_id ON job_snapshots (user_id)",
        "CREATE INDEX IF NOT EXISTS idx_js_account ON job_snapshots (account)",
        "CREATE INDEX IF NOT EXISTS idx_js_partition ON job_snapshots (partition)",
        "CREATE INDEX IF NOT EXISTS idx_js_job_state ON job_snapshots (job_state)",
        "CREATE TABLE IF NOT EXISTS job_snapshots_default PARTITION OF job_snapshots DEFAULT",
    ):
        bind.execute(sa.text(statement))


def downgrade():
    bind = op.get_bind()

    if _table_exists(bind, "job_snapshots"):
        bind.execute(sa.text("DROP INDEX IF EXISTS idx_js_user_id"))
        if _constraint_exists(bind, "fk_job_snapshots_user_id"):
            bind.execute(
                sa.text(
                    "ALTER TABLE job_snapshots DROP CONSTRAINT fk_job_snapshots_user_id"
                )
            )
        bind.execute(sa.text("ALTER TABLE job_snapshots ADD COLUMN IF NOT EXISTS user_name TEXT"))
        bind.execute(
            sa.text("CREATE INDEX IF NOT EXISTS idx_js_user_name ON job_snapshots (user_name)")
        )
        bind.execute(sa.text("ALTER TABLE job_snapshots DROP COLUMN IF EXISTS user_id"))

    if _table_exists(bind, "users"):
        op.drop_table("users")
