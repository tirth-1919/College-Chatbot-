"""Add visibility column to documents table

Revision ID: 20260912_doc_visibility
Revises: initial_schema
Create Date: 2026-09-12

P2-10: Formal migration script adding visibility column to documents table
with default value 'ADMIN_VERIFIED' and non-nullable constraint.
"""
from alembic import op
import sqlalchemy as sa

revision = '20260912_doc_visibility'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add visibility column with default
    op.add_column(
        'documents',
        sa.Column('visibility', sa.String(length=32), nullable=False, server_default='ADMIN_VERIFIED')
    )
    # Ensure existing documents are set properly
    op.execute("UPDATE documents SET visibility = 'ADMIN_VERIFIED' WHERE visibility IS NULL")

def downgrade() -> None:
    op.drop_column('documents', 'visibility')
