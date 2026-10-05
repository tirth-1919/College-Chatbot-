'''Normalize Smart Upload confidence scores to probabilities.

Revision ID: 20261002_008
Revises: 20260930_007
'''
from alembic import op
import sqlalchemy as sa
revision = "20261002_008"
down_revision = "20260930_007"
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"]: column for column in inspector.get_columns("staged_upload_records")}
    if "confidence_score" in columns:
        # Existing values were percentages (e.g. 85/92); convert them once.
        op.execute("UPDATE staged_upload_records SET confidence_score = confidence_score / 100.0 WHERE confidence_score > 1")
        with op.batch_alter_table("staged_upload_records") as batch:
            batch.alter_column("confidence_score", existing_type=sa.Integer(), type_=sa.Float(), existing_nullable=True)


def downgrade():
    with op.batch_alter_table("staged_upload_records") as batch:
        batch.alter_column("confidence_score", existing_type=sa.Float(), type_=sa.Integer(), existing_nullable=True)
    op.execute("UPDATE staged_upload_records SET confidence_score = ROUND(confidence_score * 100)")
