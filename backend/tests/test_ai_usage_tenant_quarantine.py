"Tenant analytics must exclude legacy NULL-tenant usage rows."""
from types import SimpleNamespace
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.app.core.database import Base
from backend.app.models.admin_system import AiUsageLog
from backend.app.api.v1.admin.ai_control import tenant_scoped_usage_query

def test_null_tenant_usage_is_excluded_for_super_admin():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        db.add_all([
            AiUsageLog(id="ambiguous", college_id=None, provider_name="test", model_identifier="m"),
            AiUsageLog(id="ait", college_id="ait-default-tenant-0001", provider_name="test", model_identifier="m"),
        ])
        db.commit()
        user = SimpleNamespace(role="SUPER_ADMIN", college_id=None)
        assert [row.id for row in tenant_scoped_usage_query(db, user).all()] == ["ait"]
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def test_college_admin_usage_is_scoped_and_excludes_null_tenant():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        db.add_all([
            AiUsageLog(id="ambiguous", college_id=None, provider_name="test", model_identifier="m"),
            AiUsageLog(id="ait", college_id="ait-default-tenant-0001", provider_name="test", model_identifier="m"),
            AiUsageLog(id="rcti", college_id="a607d280-e365-4fc3-b964-d6260983be89", provider_name="test", model_identifier="m"),
        ])
        db.commit()
        user = SimpleNamespace(role="COLLEGE_ADMIN", college_id="a607d280-e365-4fc3-b964-d6260983be89")
        assert [row.id for row in tenant_scoped_usage_query(db, user).all()] == ["rcti"]
    finally:
        db.close()
        Base.metadata.drop_all(engine)
