"""Require explicit tenant on normal conversations; quarantine legacy NULL rows.

Revision ID: 20260926_001
Revises: 20260926_000
"""
from alembic import op
import sqlalchemy as sa
revision = "20260926_001"
down_revision = "20260926_000"
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("conversations")}
    if "conversation_type" not in columns:
        op.add_column("conversations", sa.Column("conversation_type", sa.String(length=24), nullable=False, server_default="NORMAL"))
    # Legacy NULL rows remain preserved but are explicitly marked onboarding and
    # therefore excluded from normal conversation endpoints. No ownership guess.
    bind.execute(sa.text("UPDATE conversations SET conversation_type = 'ONBOARDING' WHERE college_id IS NULL"))
    bind.execute(sa.text("UPDATE conversations SET conversation_type = 'NORMAL' WHERE college_id IS NOT NULL AND (conversation_type IS NULL OR conversation_type = 'ONBOARDING')"))
    indexes = {idx["name"] for idx in inspector.get_indexes("conversations")}
    if "ix_conversations_conversation_type" not in indexes:
        op.create_index("ix_conversations_conversation_type", "conversations", ["conversation_type"], unique=False)
    # SQLite cannot issue ALTER COLUMN; the baseline already has the model
    # default and the default is harmless for the compatibility database.
    if bind.dialect.name != "sqlite":
        op.alter_column("conversations", "conversation_type", server_default=None)


def downgrade():
    op.drop_index("ix_conversations_conversation_type", table_name="conversations")
    op.drop_column("conversations", "conversation_type")
