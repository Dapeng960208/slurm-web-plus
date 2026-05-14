# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from alembic import op
import sqlalchemy as sa


revision = "20260514_0012"
down_revision = "20260507_0011"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "node_metric_samples",
        sa.Column("cluster", sa.Text(), nullable=False),
        sa.Column("node", sa.Text(), nullable=False),
        sa.Column("sampled_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("cpu_usage", sa.Float(), nullable=True),
        sa.Column("memory_usage", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("cluster", "node", "sampled_at", name="pk_node_metric_samples"),
    )
    op.create_index(
        "idx_node_metric_samples_cluster_sampled_at",
        "node_metric_samples",
        ["cluster", sa.text("sampled_at DESC")],
    )
    op.create_index(
        "idx_node_metric_samples_cluster_node_sampled_at",
        "node_metric_samples",
        ["cluster", "node", sa.text("sampled_at DESC")],
    )


def downgrade():
    op.drop_index("idx_node_metric_samples_cluster_node_sampled_at", table_name="node_metric_samples")
    op.drop_index("idx_node_metric_samples_cluster_sampled_at", table_name="node_metric_samples")
    op.drop_table("node_metric_samples")
