'''Add native pgvector storage while retaining the JSON backfill source.

Revision ID: 20260927_005
Revises: 20260927_004
'''
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
revision = "20260927_005"
down_revision = "20260927_004"
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect != "postgresql":
        return
    bind.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("document_chunks")}
    if "embedding_vector" not in columns:
        op.add_column(
            "document_chunks",
            sa.Column("embedding_vector", Vector(64), nullable=True),
        )
    indexes = {index["name"] for index in inspector.get_indexes("document_chunks")}
    if "ix_document_chunks_embedding_vector_hnsw" not in indexes:
        bind.execute(sa.text(
            "CREATE INDEX ix_document_chunks_embedding_vector_hnsw "
            "ON document_chunks USING hnsw (embedding_vector vector_cosine_ops)"
        ))


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    bind.execute(sa.text("DROP INDEX IF EXISTS ix_document_chunks_embedding_vector_hnsw"))
    inspector = sa.inspect(bind)
    if "embedding_vector" in {column["name"] for column in inspector.get_columns("document_chunks")}:
        op.drop_column("document_chunks", "embedding_vector")
