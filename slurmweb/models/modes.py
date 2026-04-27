# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = sa.Column(sa.BigInteger(), primary_key=True, autoincrement=True)
    username = sa.Column(sa.Text(), nullable=False, unique=True)
    fullname = sa.Column(sa.Text(), nullable=True)
    groups = sa.Column(
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=False,
        server_default=sa.text("'[]'::jsonb"),
    )
    policy_roles = sa.Column(
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=False,
        server_default=sa.text("'[]'::jsonb"),
    )
    policy_actions = sa.Column(
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=False,
        server_default=sa.text("'[]'::jsonb"),
    )
    ldap_synced_at = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True)
    permission_synced_at = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True)
    created_at = sa.Column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sa.text("NOW()"),
    )
    updated_at = sa.Column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sa.text("NOW()"),
    )


class Role(Base):
    __tablename__ = "roles"
    __table_args__ = (
        sa.UniqueConstraint("name", name="uq_roles_name"),
    )

    id = sa.Column(sa.BigInteger(), primary_key=True, autoincrement=True)
    name = sa.Column(sa.Text(), nullable=False)
    description = sa.Column(sa.Text(), nullable=True)
    actions = sa.Column(
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=False,
        server_default=sa.text("'[]'::jsonb"),
    )
    permissions = sa.Column(
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=False,
        server_default=sa.text("'[]'::jsonb"),
    )
    created_at = sa.Column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sa.text("NOW()"),
    )
    updated_at = sa.Column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sa.text("NOW()"),
    )


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (
        sa.PrimaryKeyConstraint("user_id", "role_id", name="pk_user_roles"),
        sa.Index("idx_user_roles_role_id", "role_id"),
    )

    user_id = sa.Column(
        sa.BigInteger(),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role_id = sa.Column(
        sa.BigInteger(),
        sa.ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = sa.Column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sa.text("NOW()"),
    )


class JobSnapshot(Base):
    __tablename__ = "job_snapshots"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", "submit_time"),
        sa.Index("idx_js_job_submit", "job_id", "submit_time", unique=True),
        sa.Index("idx_js_last_seen", sa.text("last_seen DESC")),
        sa.Index("idx_js_user_id", "user_id"),
        sa.Index("idx_js_account", "account"),
        sa.Index("idx_js_partition", "partition"),
        sa.Index("idx_js_job_state", "job_state"),
        {"postgresql_partition_by": "RANGE (submit_time)"},
    )

    id = sa.Column(sa.BigInteger(), autoincrement=True)
    job_id = sa.Column(sa.Integer(), nullable=False)
    submit_time = sa.Column(sa.TIMESTAMP(timezone=True), nullable=False)
    first_seen = sa.Column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sa.text("NOW()"),
    )
    last_seen = sa.Column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sa.text("NOW()"),
    )
    job_name = sa.Column(sa.Text(), nullable=True)
    job_state = sa.Column(sa.Text(), nullable=True)
    state_reason = sa.Column(sa.Text(), nullable=True)
    user_id = sa.Column(sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True)
    account = sa.Column(sa.Text(), nullable=True)
    group = sa.Column("group", sa.Text(), nullable=True)
    partition = sa.Column(sa.Text(), nullable=True)
    qos = sa.Column(sa.Text(), nullable=True)
    nodes = sa.Column(sa.Text(), nullable=True)
    node_count = sa.Column(sa.Integer(), nullable=True)
    cpus = sa.Column(sa.Integer(), nullable=True)
    priority = sa.Column(sa.Integer(), nullable=True)
    tres_req_str = sa.Column(sa.Text(), nullable=True)
    tres_per_job = sa.Column(sa.Text(), nullable=True)
    tres_per_node = sa.Column(sa.Text(), nullable=True)
    gres_detail = sa.Column(sa.Text(), nullable=True)
    tres_requested = sa.Column(postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    tres_allocated = sa.Column(postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    start_time = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True)
    end_time = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True)
    eligible_time = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True)
    last_sched_evaluation_time = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True)
    time_limit_minutes = sa.Column(sa.Integer(), nullable=True)
    used_memory_gb = sa.Column(sa.Float(), nullable=True)
    usage_stats = sa.Column(postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    used_cpu_cores_avg = sa.Column(sa.Float(), nullable=True)
    exit_code = sa.Column(sa.Text(), nullable=True)
    working_directory = sa.Column(sa.Text(), nullable=True)
    command = sa.Column(sa.Text(), nullable=True)


class AIModelConfig(Base):
    __tablename__ = "ai_model_configs"
    __table_args__ = (
        sa.UniqueConstraint("cluster", "name", name="uq_ai_model_configs_cluster_name"),
        sa.Index("idx_ai_model_configs_cluster_enabled", "cluster", "enabled"),
        sa.Index(
            "uq_ai_model_configs_cluster_default",
            "cluster",
            unique=True,
            postgresql_where=sa.text("is_default = TRUE"),
        ),
    )

    id = sa.Column(sa.BigInteger(), primary_key=True, autoincrement=True)
    cluster = sa.Column(sa.Text(), nullable=False)
    name = sa.Column(sa.Text(), nullable=False)
    provider = sa.Column(sa.Text(), nullable=False)
    model = sa.Column(sa.Text(), nullable=False)
    display_name = sa.Column(sa.Text(), nullable=False)
    enabled = sa.Column(
        sa.Boolean(),
        nullable=False,
        server_default=sa.text("TRUE"),
    )
    is_default = sa.Column(
        sa.Boolean(),
        nullable=False,
        server_default=sa.text("FALSE"),
    )
    sort_order = sa.Column(
        sa.Integer(),
        nullable=False,
        server_default=sa.text("0"),
    )
    base_url = sa.Column(sa.Text(), nullable=True)
    deployment = sa.Column(sa.Text(), nullable=True)
    api_version = sa.Column(sa.Text(), nullable=True)
    request_timeout = sa.Column(sa.Integer(), nullable=True)
    temperature = sa.Column(sa.Float(), nullable=True)
    system_prompt = sa.Column(sa.Text(), nullable=True)
    extra_options = sa.Column(
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=False,
        server_default=sa.text("'{}'::jsonb"),
    )
    secret_ciphertext = sa.Column(sa.Text(), nullable=True)
    secret_mask = sa.Column(sa.Text(), nullable=True)
    last_validated_at = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True)
    last_validation_error = sa.Column(sa.Text(), nullable=True)
    created_at = sa.Column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sa.text("NOW()"),
    )
    updated_at = sa.Column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sa.text("NOW()"),
    )


class AIConversation(Base):
    __tablename__ = "ai_conversations"
    __table_args__ = (
        sa.Index("idx_ai_conversations_cluster_user", "cluster", "username"),
        sa.Index("idx_ai_conversations_updated_at", sa.text("updated_at DESC")),
    )

    id = sa.Column(sa.BigInteger(), primary_key=True, autoincrement=True)
    cluster = sa.Column(sa.Text(), nullable=False)
    username = sa.Column(sa.Text(), nullable=False)
    title = sa.Column(sa.Text(), nullable=False)
    model_config_id = sa.Column(
        sa.BigInteger(),
        sa.ForeignKey("ai_model_configs.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = sa.Column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sa.text("NOW()"),
    )
    updated_at = sa.Column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sa.text("NOW()"),
    )


class AIMessage(Base):
    __tablename__ = "ai_messages"
    __table_args__ = (
        sa.Index("idx_ai_messages_conversation_id", "conversation_id"),
        sa.Index("idx_ai_messages_created_at", sa.text("created_at ASC")),
    )

    id = sa.Column(sa.BigInteger(), primary_key=True, autoincrement=True)
    conversation_id = sa.Column(
        sa.BigInteger(),
        sa.ForeignKey("ai_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role = sa.Column(sa.Text(), nullable=False)
    content = sa.Column(sa.Text(), nullable=False)
    model_config_id = sa.Column(
        sa.BigInteger(),
        sa.ForeignKey("ai_model_configs.id", ondelete="SET NULL"),
        nullable=True,
    )
    meta = sa.Column(
        "metadata",
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=False,
        server_default=sa.text("'{}'::jsonb"),
    )
    created_at = sa.Column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sa.text("NOW()"),
    )


class AIToolCall(Base):
    __tablename__ = "ai_tool_calls"
    __table_args__ = (
        sa.Index("idx_ai_tool_calls_conversation_id", "conversation_id"),
        sa.Index("idx_ai_tool_calls_username", "username"),
    )

    id = sa.Column(sa.BigInteger(), primary_key=True, autoincrement=True)
    conversation_id = sa.Column(
        sa.BigInteger(),
        sa.ForeignKey("ai_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    message_id = sa.Column(
        sa.BigInteger(),
        sa.ForeignKey("ai_messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    cluster = sa.Column(sa.Text(), nullable=False)
    username = sa.Column(sa.Text(), nullable=False)
    tool_name = sa.Column(sa.Text(), nullable=False)
    permission = sa.Column(sa.Text(), nullable=False)
    interface_key = sa.Column(sa.Text(), nullable=True)
    status_code = sa.Column(sa.Integer(), nullable=True)
    input_payload = sa.Column(
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=False,
        server_default=sa.text("'{}'::jsonb"),
    )
    result_summary = sa.Column(sa.Text(), nullable=True)
    status = sa.Column(sa.Text(), nullable=False)
    error = sa.Column(sa.Text(), nullable=True)
    duration_ms = sa.Column(sa.Integer(), nullable=True)
    created_at = sa.Column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sa.text("NOW()"),
    )
