# Add website versioning and document embedding/index metadata.
# Revision ID: 20260927_003
# Revises: 20260926_002
from alembic import op
import sqlalchemy as sa
revision = "20260927_003"
down_revision = "20260926_002"
branch_labels = None
depends_on = None

def _add(table, column, type_, **kwargs):
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if column not in {c["name"] for c in inspector.get_columns(table)}:
        op.add_column(table, sa.Column(column, type_, **kwargs))


def upgrade():
    _add("website_snapshots", "active", sa.Boolean(), nullable=False, server_default=sa.true())
    _add("website_snapshots", "crawl_error", sa.Text(), nullable=True)
    _add("website_snapshots", "version_number", sa.Integer(), nullable=False, server_default="1")
    _add("document_chunks", "embedding_model", sa.String(length=120), nullable=True)
    _add("document_chunks", "embedding_version", sa.String(length=50), nullable=True)
    _add("document_chunks", "indexed_at", sa.DateTime(), nullable=True)
    _add("document_chunks", "active", sa.Boolean(), nullable=False, server_default=sa.true())
    op.create_table(
        "website_snapshot_versions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("college_id", sa.String(length=36), nullable=False),
        sa.Column("snapshot_id", sa.String(length=36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("text_content", sa.Text(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("captured_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["college_id"], ["colleges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["snapshot_id"], ["website_snapshots.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_website_snapshot_versions_college_id", "website_snapshot_versions", ["college_id"])
    op.create_index("ix_website_snapshot_versions_snapshot_id", "website_snapshot_versions", ["snapshot_id"])
    op.create_index("ix_website_snapshot_versions_content_hash", "website_snapshot_versions", ["content_hash"])


def downgrade():
    op.drop_index("ix_website_snapshot_versions_content_hash", table_name="website_snapshot_versions")
    op.drop_index("ix_website_snapshot_versions_snapshot_id", table_name="website_snapshot_versions")
    op.drop_index("ix_website_snapshot_versions_college_id", table_name="website_snapshot_versions")
    op.drop_table("website_snapshot_versions")
    for table, column in (("document_chunks", "active"), ("document_chunks", "indexed_at"), ("document_chunks", "embedding_version"), ("document_chunks", "embedding_model"), ("website_snapshots", "version_number"), ("website_snapshots", "crawl_error"), ("website_snapshots", "active")):
        try:
            op.drop_column(table, column)
        except Exception:
            pass
