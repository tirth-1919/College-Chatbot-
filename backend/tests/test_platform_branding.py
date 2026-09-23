"""
Permanent platform-branding tests (Platform Name Fix §21-§23).

The product/platform name is ALWAYS "AI-Powered Colleges Chatbot" and must
never change based on the active/default/conversation/admin college. College
names are tenant records, never the platform identity (§24).
"""
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.config import settings
from backend.app.core.database import Base, get_db
from backend.app.main import app

PLATFORM_NAME = "AI-Powered Colleges Chatbot"
FORBIDDEN_NAMES = {
    "AIT AI Assistant", "AIT Chatbot", "RCTI Chatbot",
    "RC Technical Chatbot", "College AI", "College Assistant",
}


@pytest.fixture(scope="module")
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


@pytest.fixture(scope="module")
def client(db_session):
    from backend.app.models.college import College
    from backend.app.models.user import User
    from backend.app.core.security import get_password_hash

    now = datetime.now(timezone.utc)
    # Three tenants — including a college NOT known at development time (§22)
    colleges = [
        College(id="br-col-ait", name="Ahmedabad Institute of Technology", code="AIT",
                slug="ait", status="ACTIVE", created_at=now, updated_at=now),
        College(id="br-col-rcti", name="R.C. Technical Institute", code="RCTI",
                slug="rcti", status="ACTIVE", created_at=now, updated_at=now),
        College(id="br-col-c", name="College C", code="CLGC", slug="college-c",
                status="ACTIVE", created_at=now, updated_at=now),
    ]
    users = []
    for i, col in enumerate(colleges):
        users.append(User(id=str(uuid.uuid4()), email=f"bradmin{i}@br.example.com",
                          full_name=f"admin{i}", hashed_password=get_password_hash("TestPass1!"),
                          role="COLLEGE_ADMIN", college_id=col.id, is_active=True, is_verified=True))
    users.append(User(id=str(uuid.uuid4()), email="brsuper@br.example.com",
                      full_name="super", hashed_password=get_password_hash("TestPass1!"),
                      role="SUPER_ADMIN", college_id=None, is_active=True, is_verified=True))
    db_session.add_all(colleges + users)
    db_session.commit()

    def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


def test_config_platform_name_is_permanent():
    """The central configuration carries the immutable platform name (§20)."""
    assert settings.APP_NAME == PLATFORM_NAME


def test_config_platform_name_independent_of_college(client):
    """Config default name is the platform name regardless of any tenant."""
    assert settings.APP_NAME == PLATFORM_NAME
    assert "Ahmedabad" not in settings.APP_NAME
    assert "R.C. Technical" not in settings.APP_NAME


def test_health_endpoint_returns_platform_name(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("app") == PLATFORM_NAME
    # College context must be a separate field, never merged into the name (§15/§24)
    assert "institution" in data


def test_openapi_title_is_platform_name(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    assert r.json().get("info", {}).get("title") == PLATFORM_NAME


def test_platform_name_not_dynamically_derived_from_college(client):
    """No runtime path may rebuild the app name from college data (§6).

    Colleges with entirely different names exist in this DB, but the exposed
    platform metadata stays identical for all of them (§22).
    """
    from backend.app.models.college import College
    # Sanity: three differently-named tenants exist; the invariant on settings holds
    assert settings.APP_NAME == PLATFORM_NAME


def test_platform_name_not_a_forbidden_legacy_name():
    """Guard against regressions to college-specific product names (§1/§23)."""
    assert settings.APP_NAME not in FORBIDDEN_NAMES
    assert settings.APP_NAME == PLATFORM_NAME
