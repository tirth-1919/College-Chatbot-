'''Add idempotency constraints for documents and chunks.

Revision ID: 20260927_004
Revises: 20260927_003
'''
from alembic import op
import sqlalchemy as sa
revision = "20260927_004"
down_revision = "20260927_003"
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {idx["name"] for idx in inspector.get_indexes("documents")}
    if "uq_documents_college_hash_visibility" not in indexes:
        duplicates = bind.execute(sa.text("""
            SELECT college_id, content_hash, visibility, COUNT(*)
            FROM documents GROUP BY college_id, content_hash, visibility HAVING COUNT(*) > 1
        """)).fetchall()
        if duplicates:
            raise RuntimeError("Unresolved duplicate documents; clean data before applying 20260927_004")
        op.create_unique_constraint("uq_documents_college_hash_visibility", "documents", ["college_id", "content_hash", "visibility"])
    chunk_indexes = {idx["name"] for idx in inspector.get_indexes("document_chunks")}
    if "uq_document_chunks_document_index" not in chunk_indexes:
        duplicates = bind.execute(sa.text("""
            SELECT document_id, chunk_index, COUNT(*) FROM document_chunks
            GROUP BY document_id, chunk_index HAVING COUNT(*) > 1
        """)).fetchall()
        if duplicates:
            raise RuntimeError("Unresolved duplicate chunks; clean data before applying 20260927_004")
        op.create_unique_constraint("uq_document_chunks_document_index", "document_chunks", ["document_id", "chunk_index"])

def downgrade():
    op.drop_constraint("uq_document_chunks_document_index", "document_chunks", type_="unique")
    op.drop_constraint("uq_documents_college_hash_visibility", "documents", type_="unique")
