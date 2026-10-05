'''Create the existing SQLAlchemy schema as the Alembic baseline.

Revision ID: 20260926_000
Revises:
'''
from alembic import op
from backend.app.core.database import Base
import backend.app.models  # noqa: F401 - register all mapped tables
revision = "20260926_000"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # This is the one-time baseline for databases that historically used the
    # model schema. Subsequent production changes are explicit Alembic ops.
    Base.metadata.create_all(bind=op.get_bind())


def downgrade():
    # The baseline is not destructively downgraded; later revisions remain
    # independently reversible without dropping production data.
    pass
