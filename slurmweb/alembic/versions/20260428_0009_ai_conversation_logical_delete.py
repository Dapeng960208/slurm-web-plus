from alembic import op
import sqlalchemy as sa


revision = "20260428_0009"
down_revision = "20260427_0008"
branch_labels = None
depends_on = None


def _table_exists(bind, name):
    return sa.inspect(bind).has_table(name)


def _column_exists(bind, table_name, column_name):
    columns = sa.inspect(bind).get_columns(table_name)
    return any(column["name"] == column_name for column in columns)


def _index_exists(bind, name):
    result = bind.execute(
        sa.text("SELECT 1 FROM pg_indexes WHERE indexname = :name"),
        {"name": name},
    )
    return result.scalar() is not None


def upgrade():
    bind = op.get_bind()
    if not _table_exists(bind, "ai_conversations"):
        return
    if not _column_exists(bind, "ai_conversations", "deleted_at"):
        op.add_column(
            "ai_conversations",
            sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        )
    if not _column_exists(bind, "ai_conversations", "deleted_by"):
        op.add_column("ai_conversations", sa.Column("deleted_by", sa.Text(), nullable=True))
    if not _index_exists(bind, "idx_ai_conversations_deleted_at"):
        op.execute(
            "CREATE INDEX idx_ai_conversations_deleted_at ON ai_conversations (deleted_at)"
        )


def downgrade():
    bind = op.get_bind()
    if not _table_exists(bind, "ai_conversations"):
        return
    if _index_exists(bind, "idx_ai_conversations_deleted_at"):
        op.drop_index("idx_ai_conversations_deleted_at", table_name="ai_conversations")
    if _column_exists(bind, "ai_conversations", "deleted_by"):
        op.drop_column("ai_conversations", "deleted_by")
    if _column_exists(bind, "ai_conversations", "deleted_at"):
        op.drop_column("ai_conversations", "deleted_at")
