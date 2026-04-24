# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260424_0006"
down_revision = "20260424_0005"
branch_labels = None
depends_on = None


def _table_exists(bind, name):
    return sa.inspect(bind).has_table(name)


def _index_exists(bind, name):
    result = bind.execute(
        sa.text("SELECT 1 FROM pg_indexes WHERE indexname = :name"),
        {"name": name},
    )
    return result.scalar() is not None


def _constraint_exists(bind, name):
    result = bind.execute(
        sa.text("SELECT 1 FROM pg_constraint WHERE conname = :name"),
        {"name": name},
    )
    return result.scalar() is not None


def upgrade():
    bind = op.get_bind()

    if not _table_exists(bind, "ai_model_configs"):
        op.create_table(
            "ai_model_configs",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("cluster", sa.Text(), nullable=False),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("provider", sa.Text(), nullable=False),
            sa.Column("model", sa.Text(), nullable=False),
            sa.Column("display_name", sa.Text(), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("base_url", sa.Text(), nullable=True),
            sa.Column("deployment", sa.Text(), nullable=True),
            sa.Column("api_version", sa.Text(), nullable=True),
            sa.Column("request_timeout", sa.Integer(), nullable=True),
            sa.Column("temperature", sa.Float(), nullable=True),
            sa.Column("system_prompt", sa.Text(), nullable=True),
            sa.Column(
                "extra_options",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column("secret_ciphertext", sa.Text(), nullable=True),
            sa.Column("secret_mask", sa.Text(), nullable=True),
            sa.Column("last_validated_at", sa.TIMESTAMP(timezone=True), nullable=True),
            sa.Column("last_validation_error", sa.Text(), nullable=True),
            sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
            sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
            sa.UniqueConstraint("cluster", "name", name="uq_ai_model_configs_cluster_name"),
        )
    if not _index_exists(bind, "idx_ai_model_configs_cluster_enabled"):
        op.create_index(
            "idx_ai_model_configs_cluster_enabled",
            "ai_model_configs",
            ["cluster", "enabled"],
        )
    if not _index_exists(bind, "uq_ai_model_configs_cluster_default"):
        op.execute(
            """
            CREATE UNIQUE INDEX uq_ai_model_configs_cluster_default
            ON ai_model_configs (cluster)
            WHERE is_default = TRUE
            """
        )

    if not _table_exists(bind, "ai_conversations"):
        op.create_table(
            "ai_conversations",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("cluster", sa.Text(), nullable=False),
            sa.Column("username", sa.Text(), nullable=False),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("model_config_id", sa.BigInteger(), nullable=True),
            sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
            sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
            sa.ForeignKeyConstraint(
                ["model_config_id"],
                ["ai_model_configs.id"],
                ondelete="SET NULL",
                name="fk_ai_conversations_model_config_id",
            ),
        )
    if not _index_exists(bind, "idx_ai_conversations_cluster_user"):
        op.create_index(
            "idx_ai_conversations_cluster_user",
            "ai_conversations",
            ["cluster", "username"],
        )
    if not _index_exists(bind, "idx_ai_conversations_updated_at"):
        op.execute(
            "CREATE INDEX idx_ai_conversations_updated_at ON ai_conversations (updated_at DESC)"
        )

    if not _table_exists(bind, "ai_messages"):
        op.create_table(
            "ai_messages",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("conversation_id", sa.BigInteger(), nullable=False),
            sa.Column("role", sa.Text(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("model_config_id", sa.BigInteger(), nullable=True),
            sa.Column(
                "metadata",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
            sa.ForeignKeyConstraint(
                ["conversation_id"],
                ["ai_conversations.id"],
                ondelete="CASCADE",
                name="fk_ai_messages_conversation_id",
            ),
            sa.ForeignKeyConstraint(
                ["model_config_id"],
                ["ai_model_configs.id"],
                ondelete="SET NULL",
                name="fk_ai_messages_model_config_id",
            ),
        )
    if not _index_exists(bind, "idx_ai_messages_conversation_id"):
        op.create_index("idx_ai_messages_conversation_id", "ai_messages", ["conversation_id"])
    if not _index_exists(bind, "idx_ai_messages_created_at"):
        op.execute("CREATE INDEX idx_ai_messages_created_at ON ai_messages (created_at ASC)")

    if not _table_exists(bind, "ai_tool_calls"):
        op.create_table(
            "ai_tool_calls",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("conversation_id", sa.BigInteger(), nullable=False),
            sa.Column("message_id", sa.BigInteger(), nullable=True),
            sa.Column("cluster", sa.Text(), nullable=False),
            sa.Column("username", sa.Text(), nullable=False),
            sa.Column("tool_name", sa.Text(), nullable=False),
            sa.Column("permission", sa.Text(), nullable=False),
            sa.Column(
                "input_payload",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column("result_summary", sa.Text(), nullable=True),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("duration_ms", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
            sa.ForeignKeyConstraint(
                ["conversation_id"],
                ["ai_conversations.id"],
                ondelete="CASCADE",
                name="fk_ai_tool_calls_conversation_id",
            ),
            sa.ForeignKeyConstraint(
                ["message_id"],
                ["ai_messages.id"],
                ondelete="SET NULL",
                name="fk_ai_tool_calls_message_id",
            ),
        )
    if not _index_exists(bind, "idx_ai_tool_calls_conversation_id"):
        op.create_index("idx_ai_tool_calls_conversation_id", "ai_tool_calls", ["conversation_id"])
    if not _index_exists(bind, "idx_ai_tool_calls_username"):
        op.create_index("idx_ai_tool_calls_username", "ai_tool_calls", ["username"])


def downgrade():
    bind = op.get_bind()

    if _index_exists(bind, "idx_ai_tool_calls_username"):
        op.drop_index("idx_ai_tool_calls_username", table_name="ai_tool_calls")
    if _index_exists(bind, "idx_ai_tool_calls_conversation_id"):
        op.drop_index("idx_ai_tool_calls_conversation_id", table_name="ai_tool_calls")
    if _table_exists(bind, "ai_tool_calls"):
        op.drop_table("ai_tool_calls")

    if _index_exists(bind, "idx_ai_messages_created_at"):
        op.drop_index("idx_ai_messages_created_at", table_name="ai_messages")
    if _index_exists(bind, "idx_ai_messages_conversation_id"):
        op.drop_index("idx_ai_messages_conversation_id", table_name="ai_messages")
    if _table_exists(bind, "ai_messages"):
        op.drop_table("ai_messages")

    if _index_exists(bind, "idx_ai_conversations_updated_at"):
        op.drop_index("idx_ai_conversations_updated_at", table_name="ai_conversations")
    if _index_exists(bind, "idx_ai_conversations_cluster_user"):
        op.drop_index("idx_ai_conversations_cluster_user", table_name="ai_conversations")
    if _table_exists(bind, "ai_conversations"):
        op.drop_table("ai_conversations")

    if _index_exists(bind, "idx_ai_model_configs_cluster_enabled"):
        op.drop_index("idx_ai_model_configs_cluster_enabled", table_name="ai_model_configs")
    if _index_exists(bind, "uq_ai_model_configs_cluster_default"):
        op.drop_index("uq_ai_model_configs_cluster_default", table_name="ai_model_configs")
    if _table_exists(bind, "ai_model_configs"):
        op.drop_table("ai_model_configs")
