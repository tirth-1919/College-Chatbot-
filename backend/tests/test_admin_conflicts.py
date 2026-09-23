"""Focused contract, authorization, and persistence tests for admin conflicts."""
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.api.v1.admin.conflicts import router
from backend.app.core.database import Base, get_db
from backend.app.core.security import create_access_token
from backend.app.core.permissions import PERM_CONFLICTS_REVIEW
from backend.app.models.admin_system import KnowledgeConflict
from backend.app.models.user import User


@pytest.fixture
def conflict_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False)
    db = session_factory()

    admin = User(
        id=str(uuid.uuid4()), email="admin-conflicts@example.test", full_name="Admin",
        role="ADMIN", permissions=[PERM_CONFLICTS_REVIEW]
    )
    super_admin = User(id=str(uuid.uuid4()), email="super-conflicts@example.test", full_name="Super", role="SUPER_ADMIN")
    student = User(id=str(uuid.uuid4()), email="student-conflicts@example.test", full_name="Student", role="STUDENT")
    db.add_all([admin, super_admin, student])
    db.commit()

    app = FastAPI()
    app.include_router(router)

    def override_db():
        request_db = session_factory()
        try:
            yield request_db
        finally:
            request_db.close()

    app.dependency_overrides[get_db] = override_db

    def make_conflict():
        conflict = KnowledgeConflict(
            id=str(uuid.uuid4()), topic="Test conflict", source_a="A", source_b="B",
            value_a="value A", value_b="value B", detected_discrepancy="test", resolution_status="UNRESOLVED",
        )
        db.add(conflict)
        db.commit()
        return conflict.id

    def headers(user):
        return {"Authorization": f"Bearer {create_access_token({'sub': user.id})}"}

    try:
        yield TestClient(app), db, make_conflict, headers(admin), headers(super_admin), headers(student)
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.mark.parametrize("resolution", ["RESOLVED_A", "RESOLVED_B", "SUPERSEDED", "DISMISSED"])
def test_admin_resolution_persists_each_supported_state(conflict_client, resolution):
    client, db, make_conflict, admin_headers, _, _ = conflict_client
    conflict_id = make_conflict()
    response = client.post(f"/conflicts/{conflict_id}/resolve", headers=admin_headers,
                           json={"resolution_status": resolution, "resolution_notes": "reviewed"})
    assert response.status_code == 200
    db.expire_all()
    conflict = db.get(KnowledgeConflict, conflict_id)
    assert conflict.resolution_status == resolution
    assert conflict.resolved_by is not None and conflict.resolved_at is not None


def test_super_admin_can_resolve(conflict_client):
    client, _, make_conflict, _, super_headers, _ = conflict_client
    response = client.post(f"/conflicts/{make_conflict()}/resolve", headers=super_headers,
                           json={"resolution_status": "RESOLVED_A"})
    assert response.status_code == 200


def test_student_cannot_resolve(conflict_client):
    client, _, make_conflict, _, _, student_headers = conflict_client
    response = client.post(f"/conflicts/{make_conflict()}/resolve", headers=student_headers,
                           json={"resolution_status": "RESOLVED_A"})
    assert response.status_code == 403


def test_missing_invalid_and_repeated_resolution_are_safe(conflict_client):
    client, _, make_conflict, admin_headers, _, _ = conflict_client
    assert client.post("/conflicts/missing/resolve", headers=admin_headers,
                       json={"resolution_status": "RESOLVED_A"}).status_code == 404
    conflict_id = make_conflict()
    assert client.post(f"/conflicts/{conflict_id}/resolve", headers=admin_headers,
                       json={"resolution_status": "NOT_A_STATE"}).status_code == 422
    assert client.post(f"/conflicts/{conflict_id}/resolve", headers=admin_headers,
                       json={"resolution_status": "RESOLVED_A"}).status_code == 200
    assert client.post(f"/conflicts/{conflict_id}/resolve", headers=admin_headers,
                       json={"resolution_status": "DISMISSED"}).status_code == 409


def test_unresolved_filter_excludes_resolved_conflicts(conflict_client):
    client, db, make_conflict, admin_headers, _, _ = conflict_client
    resolved_id, unresolved_id = make_conflict(), make_conflict()
    assert client.post(f"/conflicts/{resolved_id}/resolve", headers=admin_headers,
                       json={"resolution_status": "RESOLVED_A"}).status_code == 200
    response = client.get("/conflicts?status_filter=UNRESOLVED", headers=admin_headers)
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [unresolved_id]
