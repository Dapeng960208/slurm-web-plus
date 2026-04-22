# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from alembic import op
import sqlalchemy as sa


revision = "20260422_0003"
down_revision = "20260420_0002"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    statements = (
        "ALTER TABLE job_snapshots ADD COLUMN IF NOT EXISTS usage_stats JSONB",
        "ALTER TABLE job_snapshots ADD COLUMN IF NOT EXISTS used_cpu_cores_avg DOUBLE PRECISION",
    )
    for statement in statements:
        bind.execute(sa.text(statement))


def downgrade():
    bind = op.get_bind()
    statements = (
        "ALTER TABLE job_snapshots DROP COLUMN IF EXISTS used_cpu_cores_avg",
        "ALTER TABLE job_snapshots DROP COLUMN IF EXISTS usage_stats",
    )
    for statement in statements:
        bind.execute(sa.text(statement))
