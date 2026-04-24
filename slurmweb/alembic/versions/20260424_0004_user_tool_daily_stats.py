# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from alembic import op
import sqlalchemy as sa


revision = "20260424_0004"
down_revision = "20260422_0003"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS user_tool_daily_stats (
                activity_date DATE NOT NULL,
                user_id BIGINT NOT NULL REFERENCES users(id),
                tool TEXT NOT NULL,
                jobs_count INTEGER NOT NULL,
                avg_max_memory_gb DOUBLE PRECISION NULL,
                avg_cpu_cores DOUBLE PRECISION NULL,
                avg_runtime_seconds DOUBLE PRECISION NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT uq_user_tool_daily_stats UNIQUE (activity_date, user_id, tool)
            )
            """
        )
    )
    bind.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_user_tool_daily_stats_user_id_date "
            "ON user_tool_daily_stats (user_id, activity_date DESC)"
        )
    )


def downgrade():
    bind = op.get_bind()
    bind.execute(
        sa.text("DROP INDEX IF EXISTS idx_user_tool_daily_stats_user_id_date")
    )
    bind.execute(sa.text("DROP TABLE IF EXISTS user_tool_daily_stats"))
