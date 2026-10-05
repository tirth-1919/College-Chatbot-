"Focused P1-3 authorization tests for admin operational routes."""
import uuid
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.app.api.v1.admin.alerts import router as alerts_router
from backend.app.api.v1.admin.automation import router as automation_router
from backend.app.api.v1.admin.conflicts import router as conflicts_router
from backend.app.api.v1.admin.dashboard import router as dashboard_router
from backend.app.api.v1.admin.evaluation import router as evaluation_router
from backend.app.api.v1.admin.monitoring import router as monitoring_router
from backend.app.api.v1.admin.settings import router as settings_router
from backend.app.core.database import Base, get_db
from backend.app.core.permissions import PERM_CONFLICTS_REVIEW
from backend.app.core.security import create_access_token
from backend.app.models.admin_system import KnowledgeConflict
from backend.app.models.college import College
from backend.app.models.user import User
@pytest.fixture
def operational_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False)
    db = factory()

    college_a = College(id=str(uuid.uuid4()), name="College A", code="COLA", slug="college-a",
                        status="ACTIVE", registration_status="APPROVED")
    college_b = College(id=str(uuid.uuid4()), name="College B", code="COLB", slug="college-b",
                        status="ACTIVE", registration_status="APPROVED")
    admin_a = User(id=str(uuid.uuid4()), email="admin-a@example.test", full_name="Admin A",
                   role="COLLEGE_ADMIN", college_id=college_a.id,
                   permissions=[PERM_CONFLICTS_REVIEW], is_active=True)
    admin_b = User(id=str(uuid.uuid4()), email="admin-b@example.test", full_name="Admin B",
                   role="COLLEGE_ADMIN", college_id=college_b.id,
                   permissions=[PERM_CONFLICTS_REVIEW], is_active=True)
    super_admin = User(id=str(uuid.uuid4()), email="super@example.test", full_name="Super",
                       role="SUPER_ADMIN", college_id=None, is_active=True)
    db.add_all([college_a, college_b, admin_a, admin_b, super_admin])
    db.commit()

    conflict_a = KnowledgeConflict(
        id=str(uuid.uuid4()), college_id=college_a.id, topic="A conflict", source_a="A",
        source_b="B", value_a="a", value_b="b", detected_discrepancy="a/b",
        resolution_status="UNRESOLVED")
    conflict_b = KnowledgeConflict(
        id=str(uuid.uuid4()), college_id=college_b.id, topic="B conflict", source_a="A",
        source_b="B", value_a="a", value_b="b", detected_discrepancy="a/b",
        resolution_status="UNRESOLVED")
    null_conflict = KnowledgeConflict(
        id=str(uuid.uuid4()), college_id=None, topic="Global legacy conflict", source_a="A",
        source_b="B", value_a="a", value_b="b", detected_discrepancy="a/b",
        resolution_status="UNRESOLVED")
    db.add_all([conflict_a, conflict_b, null_conflict])
    db.commit()

    app = FastAPI()
    for router in (alerts_router, automation_router, conflicts_router, dashboard_router,
                   evaluation_router, monitoring_router, settings_router):
        app.include_router(router)

    def override_db():
        request_db = factory()
        try:
            yield request_db
        finally:
            request_db.close()

    app.dependency_overrides[get_db] = override_db
    def headers(user):
        return {"Authorization": f"Bearer {create_access_token({'sub': user.id})}"}

    try:
        yield {
            "client": TestClient(app), "db": db, "a": college_a, "b": college_b,
            "admin_a": headers(admin_a), "admin_b": headers(admin_b),
            "super": headers(super_admin), "conflict_a": conflict_a.id,
            "conflict_b": conflict_b.id, "null_conflict": null_conflict.id,
        }
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_college_admin_cannot_access_platform_global_operational_routes(operational_client):
    client = operational_client["client"]
    headers = operational_client["admin_a"]
    for path in ("/alerts", "/alerts/security-events", "/automation/jobs",
                 "/automation/dead-letter", "/evaluation/results", "/settings/prompts",
                 "/settings/feature-flags", "/settings/backups", "/monitoring/live-stream"):
        assert client.get(path, headers=headers).status_code == 403

def test_super_admin_can_access_platform_global_operational_routes(operational_client):
    client = operational_client["client"]
    headers = operational_client["super"]
    for path in ("/alerts", "/alerts/security-events", "/automation/jobs",
                 "/automation/dead-letter", "/evaluation/results", "/settings/prompts",
                 "/settings/feature-flags", "/settings/backups"):
        assert client.get(path, headers=headers).status_code == 200

def test_conflicts_are_tenant_scoped_and_null_tenant_is_hidden(operational_client):
    client = operational_client["client"]
    response = client.get("/conflicts", headers=operational_client["admin_a"])
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert operational_client["conflict_a"] in ids
    assert operational_client["conflict_b"] not in ids
    assert operational_client["null_conflict"] not in ids

def test_college_admin_cannot_resolve_another_college_conflict(operational_client):
    client = operational_client["client"]
    response = client.post(
        f"/conflicts/{operational_client['conflict_b']}/resolve",
        headers=operational_client["admin_a"],
        json={"resolution_status": "RESOLVED_A"},
    )
    assert response.status_code == 404
    db = operational_client["db"]
    record = db.get(KnowledgeConflict, operational_client["conflict_b"])
    assert record.resolution_status == "UNRESOLVED"


def test_super_admin_can_access_all_conflicts(operational_client):
    response = operational_client["client"].get("/conflicts", headers=operational_client["super"])
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert {operational_client["conflict_a"], operational_client["conflict_b"], operational_client["null_conflict"]} <= ids
