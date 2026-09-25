from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.app.core.database import Base, get_db
from backend.app.core.permissions import require_super_admin
from backend.app.main import app
@pytest.fixture
def diagnostic_client():
    from backend.app.models.college import College
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    now = datetime.now(timezone.utc)
    session.add_all([
        College(
            id="diag-ait",
            name="Ahmedabad Institute of Technology",
            code="AIT",
            slug="ait",
            status="ACTIVE",
            registration_status="APPROVED",
            created_at=now,
        ),
        College(
            id="diag-rcti",
            name="R.C. Technical Institute",
            code="RCTI",
            slug="rcti",
            status="ACTIVE",
            registration_status="APPROVED",
            created_at=now,
        ),
    ])
    session.commit()

    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[require_super_admin] = lambda: object()
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(require_super_admin, None)
        session.close()


def test_college_resolution_diagnostic_response_structure(diagnostic_client):
    response = diagnostic_client.get("/api/v1/admin/colleges/diagnostics/college-resolution")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "environment",
        "database",
        "college_summary",
        "known_college_matches",
        "resolver_revision",
    }
    assert set(payload["database"]) == {"dialect", "driver", "database_configured"}
    assert payload["database"]["dialect"] == "sqlite"
    assert payload["database"]["database_configured"] is True
    assert payload["college_summary"] == {
        "total_colleges": 2,
        "active_colleges": 2,
        "approved_colleges": 2,
    }
    assert {row["code"] for row in payload["known_college_matches"]} == {"AIT", "RCTI"}
    assert all(set(row) == {"name", "code", "slug", "status", "registration_status"}
               for row in payload["known_college_matches"])
    assert payload["resolver_revision"] == {"token_boundary_match_present": True}
