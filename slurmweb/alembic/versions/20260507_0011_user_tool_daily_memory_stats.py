# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from alembic import op
import sqlalchemy as sa


revision = "20260507_0011"
down_revision = "20260428_0010"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    statements = [
        """
        ALTER TABLE user_tool_daily_stats
        RENAME COLUMN avg_max_memory_gb TO avg_memory_gb
        """,
        """
        ALTER TABLE user_tool_daily_stats
        ADD COLUMN IF NOT EXISTS max_memory_gb DOUBLE PRECISION NULL
        """,
        """
        ALTER TABLE user_tool_daily_stats
        ADD COLUMN IF NOT EXISTS median_memory_gb DOUBLE PRECISION NULL
        """,
        """
        UPDATE user_tool_daily_stats
        SET max_memory_gb = COALESCE(max_memory_gb, avg_memory_gb),
            median_memory_gb = COALESCE(median_memory_gb, avg_memory_gb)
        """,
        """
        ALTER TABLE user_tool_daily_stats
        DROP COLUMN IF EXISTS memory_samples
        """,
        """
        ALTER TABLE user_tool_daily_stats
        DROP COLUMN IF EXISTS cpu_samples
        """,
        """
        ALTER TABLE user_tool_daily_stats
        DROP COLUMN IF EXISTS runtime_samples
        """,
    ]
    for statement in statements:
        bind.execute(sa.text(statement))


def downgrade():
    bind = op.get_bind()
    statements = [
        """
        ALTER TABLE user_tool_daily_stats
        ADD COLUMN IF NOT EXISTS memory_samples INTEGER NOT NULL DEFAULT 0
        """,
        """
        ALTER TABLE user_tool_daily_stats
        ADD COLUMN IF NOT EXISTS cpu_samples INTEGER NOT NULL DEFAULT 0
        """,
        """
        ALTER TABLE user_tool_daily_stats
        ADD COLUMN IF NOT EXISTS runtime_samples INTEGER NOT NULL DEFAULT 0
        """,
        """
        UPDATE user_tool_daily_stats
        SET memory_samples = jobs_count,
            cpu_samples = CASE WHEN avg_cpu_cores IS NULL THEN 0 ELSE jobs_count END,
            runtime_samples = CASE WHEN avg_runtime_seconds IS NULL THEN 0 ELSE jobs_count END
        """,
        """
        ALTER TABLE user_tool_daily_stats
        DROP COLUMN IF EXISTS median_memory_gb
        """,
        """
        ALTER TABLE user_tool_daily_stats
        DROP COLUMN IF EXISTS max_memory_gb
        """,
        """
        ALTER TABLE user_tool_daily_stats
        RENAME COLUMN avg_memory_gb TO avg_max_memory_gb
        """,
    ]
    for statement in statements:
        bind.execute(sa.text(statement))
