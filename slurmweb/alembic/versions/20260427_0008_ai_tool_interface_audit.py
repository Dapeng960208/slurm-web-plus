from alembic import op
import sqlalchemy as sa


revision = "20260427_0008"
down_revision = "20260425_0007"
branch_labels = None
depends_on = None


def _column_exists(bind, table_name, column_name):
    columns = sa.inspect(bind).get_columns(table_name)
    return any(column["name"] == column_name for column in columns)


def _table_exists(bind, name):
    return sa.inspect(bind).has_table(name)


def upgrade():
    bind = op.get_bind()
    if not _table_exists(bind, "ai_tool_calls"):
        return
    if not _column_exists(bind, "ai_tool_calls", "interface_key"):
        op.add_column("ai_tool_calls", sa.Column("interface_key", sa.Text(), nullable=True))
    if not _column_exists(bind, "ai_tool_calls", "status_code"):
        op.add_column("ai_tool_calls", sa.Column("status_code", sa.Integer(), nullable=True))


def downgrade():
    bind = op.get_bind()
    if not _table_exists(bind, "ai_tool_calls"):
        return
    if _column_exists(bind, "ai_tool_calls", "status_code"):
        op.drop_column("ai_tool_calls", "status_code")
    if _column_exists(bind, "ai_tool_calls", "interface_key"):
        op.drop_column("ai_tool_calls", "interface_key")

