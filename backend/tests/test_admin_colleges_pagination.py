from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.app.core.database import Base, get_db
from backend.app.core.permissions import require_super_admin
from backend.app.main import app
from backend.app.models.college import College
@pytest.fixture
def colleges_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    now = datetime.now(timezone.utc)
    db.add_all([
        College(id="college-a", name="College A", code="A", slug="college-a", status="ACTIVE", registration_status="APPROVED", created_at=now),
        College(id="college-b", name="College B", code="B", slug="college-b", status="ACTIVE", registration_status="APPROVED", created_at=now),
    ])
    db.commit()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[require_super_admin] = lambda: object()
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(require_super_admin, None)
        db.close()


def test_college_list_supports_normal_pagination(colleges_client):
    response = colleges_client.get("/api/v1/admin/colleges/?page=1&per_page=20")
    assert response.status_code == 200
    assert response.json()["per_page"] == 20
    assert len(response.json()["colleges"]) == 2

def test_college_list_rejects_values_above_supported_maximum(colleges_client):
    response = colleges_client.get("/api/v1/admin/colleges/?per_page=200")
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == "per_page"


def test_college_list_requires_super_admin():
    response = TestClient(app).get("/api/v1/admin/colleges/?per_page=20")
    assert response.status_code == 401
