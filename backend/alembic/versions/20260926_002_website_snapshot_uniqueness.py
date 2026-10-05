"""Tenant-aware WebsiteSnapshot uniqueness; refuse unresolved data.

Revision ID: 20260926_002
Revises: 20260926_001
"""
from alembic import op
import sqlalchemy as sa
revision = "20260926_002"
down_revision = "20260926_001"
branch_labels = None
depends_on = None
INDEX = "uq_website_snapshots_college_url"

def upgrade():
    bind = op.get_bind()
    connection = bind if hasattr(bind, "execute") else bind.connect()
    try:
        duplicates = connection.execute(sa.text("""
            SELECT college_id, url, COUNT(*) AS row_count
            FROM website_snapshots
            GROUP BY college_id, url HAVING COUNT(*) > 1
        """)).fetchall()
        if duplicates:
            raise RuntimeError("Unresolved duplicate (college_id, url) rows; migration aborted without modifying data")
        indexes = {idx["name"] for idx in sa.inspect(connection).get_indexes("website_snapshots")}
        if INDEX not in indexes:
            connection.execute(sa.text(f"CREATE UNIQUE INDEX {INDEX} ON website_snapshots (college_id, url)"))
    finally:
        if connection is not bind:
            connection.close()

def downgrade():
    op.drop_index(INDEX, table_name="website_snapshots")
