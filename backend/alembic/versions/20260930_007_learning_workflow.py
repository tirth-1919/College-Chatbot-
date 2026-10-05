'''Add continuous-learning ChangeRequest provenance fields.

Revision ID: 20260930_007
Revises: 20260930_006
'''
from alembic import op
import sqlalchemy as sa
revision = "20260930_007"
down_revision = "20260930_006"
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("change_requests")}
    for name, typ in (("proposal_origin", sa.String(50)), ("learning_candidate_id", sa.String(36)), ("provenance", sa.JSON())):
        if name not in columns:
            op.add_column("change_requests", sa.Column(name, typ, nullable=True))
    existing_indexes = {i["name"] for i in inspector.get_indexes("change_requests")}
    if "ix_change_requests_proposal_origin" not in existing_indexes:
        op.create_index("ix_change_requests_proposal_origin", "change_requests", ["proposal_origin"], unique=False)
    if "ix_change_requests_learning_candidate_id" not in existing_indexes:
        op.create_index("ix_change_requests_learning_candidate_id", "change_requests", ["learning_candidate_id"], unique=False)

def downgrade():
    op.drop_index("ix_change_requests_learning_candidate_id", table_name="change_requests")
    op.drop_index("ix_change_requests_proposal_origin", table_name="change_requests")
    op.drop_column("change_requests", "provenance")
    op.drop_column("change_requests", "learning_candidate_id")
    op.drop_column("change_requests", "proposal_origin")
