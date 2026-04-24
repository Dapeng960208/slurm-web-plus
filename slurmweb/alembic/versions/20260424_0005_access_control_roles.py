# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260424_0005"
down_revision = "20260424_0004"
branch_labels = None
depends_on = None


def _table_exists(bind, name):
    return sa.inspect(bind).has_table(name)


def _column_exists(bind, table_name, column_name):
    inspector = sa.inspect(bind)
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _constraint_exists(bind, name):
    result = bind.execute(
        sa.text("SELECT 1 FROM pg_constraint WHERE conname = :name"),
        {"name": name},
    )
    return result.scalar() is not None


def _index_exists(bind, name):
    result = bind.execute(
        sa.text("SELECT 1 FROM pg_indexes WHERE indexname = :name"),
        {"name": name},
    )
    return result.scalar() is not None


def upgrade():
    bind = op.get_bind()

    if not _column_exists(bind, "users", "policy_roles"):
        op.add_column(
            "users",
            sa.Column(
                "policy_roles",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
        )
    if not _column_exists(bind, "users", "policy_actions"):
        op.add_column(
            "users",
            sa.Column(
                "policy_actions",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
        )
    if not _column_exists(bind, "users", "permission_synced_at"):
        op.add_column(
            "users",
            sa.Column("permission_synced_at", sa.TIMESTAMP(timezone=True), nullable=True),
        )

    if not _table_exists(bind, "roles"):
        op.create_table(
            "roles",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column(
                "actions",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
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
            sa.UniqueConstraint("name", name="uq_roles_name"),
        )

    if not _table_exists(bind, "user_roles"):
        op.create_table(
            "user_roles",
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("role_id", sa.BigInteger(), nullable=False),
            sa.Column(
                "created_at",
                sa.TIMESTAMP(timezone=True),
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["users.id"],
                ondelete="CASCADE",
                name="fk_user_roles_user_id",
            ),
            sa.ForeignKeyConstraint(
                ["role_id"],
                ["roles.id"],
                ondelete="CASCADE",
                name="fk_user_roles_role_id",
            ),
            sa.PrimaryKeyConstraint("user_id", "role_id", name="pk_user_roles"),
        )

    if not _index_exists(bind, "idx_user_roles_role_id"):
        op.create_index("idx_user_roles_role_id", "user_roles", ["role_id"])


def downgrade():
    bind = op.get_bind()

    if _index_exists(bind, "idx_user_roles_role_id"):
        op.drop_index("idx_user_roles_role_id", table_name="user_roles")

    if _table_exists(bind, "user_roles"):
        op.drop_table("user_roles")

    if _table_exists(bind, "roles"):
        op.drop_table("roles")

    if _column_exists(bind, "users", "permission_synced_at"):
        op.drop_column("users", "permission_synced_at")
    if _column_exists(bind, "users", "policy_actions"):
        op.drop_column("users", "policy_actions")
    if _column_exists(bind, "users", "policy_roles"):
        op.drop_column("users", "policy_roles")
