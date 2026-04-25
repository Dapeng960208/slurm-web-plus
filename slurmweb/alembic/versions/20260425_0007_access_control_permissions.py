# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260425_0007"
down_revision = "20260424_0006"
branch_labels = None
depends_on = None


def _column_exists(bind, table_name, column_name):
    inspector = sa.inspect(bind)
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade():
    bind = op.get_bind()

    if not _column_exists(bind, "roles", "permissions"):
        op.add_column(
            "roles",
            sa.Column(
                "permissions",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
        )


def downgrade():
    bind = op.get_bind()

    if _column_exists(bind, "roles", "permissions"):
        op.drop_column("roles", "permissions")
