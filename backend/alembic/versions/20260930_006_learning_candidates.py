'''Add learning_candidates table with pgvector embedding support.

Revision ID: 20260930_006
Revises: 20260927_005
'''
from alembic import op
import sqlalchemy as sa
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    from sqlalchemy import JSON as Vector

revision = "20260930_006"
down_revision = "20260927_005"
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if "learning_candidates" not in tables:
        op.create_table(
            "learning_candidates",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("college_id", sa.String(36), sa.ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("question", sa.Text(), nullable=False),
            sa.Column("normalized_question", sa.Text(), nullable=False, index=True),
            sa.Column("detected_intent", sa.String(100), nullable=True, index=True),
            sa.Column("category", sa.String(100), nullable=True, index=True),
            sa.Column("generated_answer", sa.Text(), nullable=True),
            sa.Column("answer_source", sa.String(50), nullable=True, index=True),
            sa.Column("verification_status", sa.String(50), default="UNVERIFIED", nullable=False),
            sa.Column("status", sa.String(30), default="PENDING_REVIEW", nullable=False, index=True),
            sa.Column("occurrence_count", sa.Integer(), default=1, nullable=False),
            sa.Column("variations", sa.JSON(), nullable=True),
            sa.Column("first_asked_at", sa.DateTime(), nullable=False),
            sa.Column("last_asked_at", sa.DateTime(), nullable=False),
            sa.Column("embedding_json", sa.Text(), nullable=True),
            sa.Column("embedding_vector", Vector(64) if dialect == "postgresql" else sa.JSON(), nullable=True),
            sa.Column("conversation_id", sa.String(36), sa.ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True),
            sa.Column("metadata", sa.JSON(), nullable=True),
            sa.Column("positive_feedback_count", sa.Integer(), default=0, nullable=False),
            sa.Column("negative_feedback_count", sa.Integer(), default=0, nullable=False),
            sa.Column("reviewed_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
            sa.Column("reviewed_at", sa.DateTime(), nullable=True),
            sa.Column("rejection_reason", sa.Text(), nullable=True),
            sa.Column("change_request_id", sa.String(36), sa.ForeignKey("change_requests.id", ondelete="SET NULL"), nullable=True, index=True),
            sa.Column("similar_candidate_id", sa.String(36), sa.ForeignKey("learning_candidates.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )

        if dialect == "postgresql":
            bind.execute(sa.text(
                "CREATE INDEX IF NOT EXISTS ix_learning_candidates_embedding_hnsw "
                "ON learning_candidates USING hnsw (embedding_vector vector_cosine_ops)"
            ))

def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    if "learning_candidates" in tables:
        op.drop_table("learning_candidates")
