# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from alembic import op
import sqlalchemy as sa


revision = "20260428_0010"
down_revision = "20260428_0009"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    for column in (
        "memory_samples",
        "cpu_samples",
        "runtime_samples",
    ):
        bind.execute(
            sa.text(
                f"""
                ALTER TABLE user_tool_daily_stats
                ADD COLUMN IF NOT EXISTS {column} INTEGER NOT NULL DEFAULT 0
                """
            )
        )


def downgrade():
    bind = op.get_bind()
    for column in (
        "runtime_samples",
        "cpu_samples",
        "memory_samples",
    ):
        bind.execute(
            sa.text(
                f"""
                ALTER TABLE user_tool_daily_stats
                DROP COLUMN IF EXISTS {column}
                """
            )
        )
