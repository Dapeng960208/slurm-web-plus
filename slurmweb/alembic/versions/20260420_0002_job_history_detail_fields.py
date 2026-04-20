# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from alembic import op
import sqlalchemy as sa


revision = "20260420_0002"
down_revision = "20260420_0001"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    statements = (
        "ALTER TABLE job_snapshots ADD COLUMN IF NOT EXISTS eligible_time TIMESTAMPTZ",
        "ALTER TABLE job_snapshots ADD COLUMN IF NOT EXISTS last_sched_evaluation_time TIMESTAMPTZ",
        "ALTER TABLE job_snapshots ADD COLUMN IF NOT EXISTS tres_requested JSONB",
        "ALTER TABLE job_snapshots ADD COLUMN IF NOT EXISTS tres_allocated JSONB",
        "ALTER TABLE job_snapshots ADD COLUMN IF NOT EXISTS used_memory_gb DOUBLE PRECISION",
    )
    for statement in statements:
        bind.execute(sa.text(statement))


def downgrade():
    bind = op.get_bind()
    statements = (
        "ALTER TABLE job_snapshots DROP COLUMN IF EXISTS used_memory_gb",
        "ALTER TABLE job_snapshots DROP COLUMN IF EXISTS tres_allocated",
        "ALTER TABLE job_snapshots DROP COLUMN IF EXISTS tres_requested",
        "ALTER TABLE job_snapshots DROP COLUMN IF EXISTS last_sched_evaluation_time",
        "ALTER TABLE job_snapshots DROP COLUMN IF EXISTS eligible_time",
    )
    for statement in statements:
        bind.execute(sa.text(statement))
