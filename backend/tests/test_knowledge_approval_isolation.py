"P0 approval and Smart Upload tenant-isolation integration tests."""
import io
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.app.core.database import Base, get_db
from backend.app.core.security import create_access_token
from backend.app.main import app
from backend.app.models.college import College, ChangeRequest, StagedUploadRecord
from backend.app.models.knowledge import AitEntity
from backend.app.models.knowledge_categories import KnowledgeCategory, KnowledgeRecord
from backend.app.models.user import User
@pytest.fixture(scope="module")
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()

@pytest.fixture(scope="module")
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)

@pytest.fixture(scope="module")
def env(db_session):
    now = datetime.now(timezone.utc)
    college_a = College(id="approval-college-a", name="Approval College A", code="APPA", slug="approval-a", status="ACTIVE", registration_status="APPROVED", created_at=now, updated_at=now)
    college_b = College(id="approval-college-b", name="Approval College B", code="APPB", slug="approval-b", status="ACTIVE", registration_status="APPROVED", created_at=now, updated_at=now)
    db_session.add_all([college_a, college_b])
    admin_permissions = ["knowledge.create", "knowledge.update", "knowledge.delete", "knowledge.read"]
    admin_a = User(id="approval-admin-a", email="approval-a@test.local", full_name="Admin A", role="COLLEGE_ADMIN", college_id=college_a.id, permissions=admin_permissions, is_active=True, hashed_password="x")
    admin_b = User(id="approval-admin-b", email="approval-b@test.local", full_name="Admin B", role="COLLEGE_ADMIN", college_id=college_b.id, permissions=admin_permissions, is_active=True, hashed_password="x")
    super_a = User(id="approval-super-a", email="approval-super-a@test.local", full_name="Super A", role="SUPER_ADMIN", college_id=college_a.id, is_active=True, hashed_password="x")
    super_b = User(id="approval-super-b", email="approval-super-b@test.local", full_name="Super B", role="SUPER_ADMIN", college_id=college_b.id, is_active=True, hashed_password="x")
    category_a = KnowledgeCategory(id="approval-category-a", name="Approval Category A", key="approval-category-a", college_id=college_a.id, status="ACTIVE")
    category_b = KnowledgeCategory(id="approval-category-b", name="Approval Category B", key="approval-category-b", college_id=college_b.id, status="ACTIVE")
    record_a = KnowledgeRecord(id="approval-record-a", college_id=college_a.id, category_id=category_a.id, title="Approval Fee A", field_name="fee", value="100", status="ACTIVE", verified=True)
    db_session.add_all([admin_a, admin_b, super_a, super_b, category_a, category_b, record_a])
    db_session.commit()
    return locals()


def headers(user):
    return {"Authorization": f"Bearer {create_access_token({'sub': user.id})}"}


def latest_request(db, action=None, entity_type=None):
    query = db.query(ChangeRequest).order_by(ChangeRequest.created_at.desc())
    if action:
        query = query.filter(ChangeRequest.action == action)
    if entity_type:
        query = query.filter(ChangeRequest.entity_type == entity_type)
    return query.first()


def test_knowledge_create_update_delete_are_pending_and_production_unchanged(client, env):
    db = env["db_session"]
    h = headers(env["admin_a"])

    created = client.post("/api/v1/admin/knowledge-db/categories/approval-category-a/records", headers=h, json={"title": "Pending Fee", "field_name": "fee", "value": "200", "status": "ACTIVE"})
    assert created.status_code == 200
    assert created.json()["status"] == "PENDING"
    assert db.query(KnowledgeRecord).filter(KnowledgeRecord.title == "Pending Fee").first() is None
    updated = client.patch("/api/v1/admin/knowledge-db/records/approval-record-a", headers=h, json={"value": "150"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "PENDING"
    db.refresh(env["record_a"])
    assert env["record_a"].value == "100"

    deleted = client.delete("/api/v1/admin/knowledge-db/records/approval-record-a", headers=h)
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "PENDING"
    db.refresh(env["record_a"])
    assert env["record_a"].status == "ACTIVE"


def test_college_admin_cannot_approve_knowledge_request(client, env):
    db = env["db_session"]
    request = db.query(ChangeRequest).filter(ChangeRequest.college_id == env["college_a"].id, ChangeRequest.entity_type == "KNOWLEDGE").order_by(ChangeRequest.created_at.desc()).first()
    response = client.post(f"/api/v1/admin/change-requests/{request.id}/approve", headers=headers(env["admin_a"]), json={})
    assert response.status_code == 403

def test_super_admin_approval_materializes_and_preserves_request_tenant(client, env):
    db = env["db_session"]
    response = client.post("/api/v1/admin/knowledge-db/categories/approval-category-a/records", headers=headers(env["admin_a"]), json={"title": "Approved Fee", "field_name": "fee", "value": "250", "status": "ACTIVE"})
    request_id = response.json()["request_id"]
    approved = client.post(f"/api/v1/admin/change-requests/{request_id}/approve", headers=headers(env["super_b"]), json={})
    assert approved.status_code == 200
    record = db.query(KnowledgeRecord).filter(KnowledgeRecord.title == "Approved Fee").one()
    assert record.college_id == env["college_a"].id
    assert record.status == "ACTIVE"
    assert db.query(AitEntity).filter(AitEntity.source_page == f"knowledge-record:{record.id}", AitEntity.college_id == env["college_a"].id).one()


def test_category_create_update_delete_approval_and_cross_tenant_payload(client, env):
    db = env["db_session"]
    h = headers(env["admin_a"])
    create = client.post("/api/v1/admin/knowledge-db/categories", headers=h, json={"name": "Pending Category", "key": "pending-category", "college_id": env["college_b"].id})
    assert create.status_code == 200
    assert create.json()["status"] == "PENDING"
    request = db.query(ChangeRequest).filter(ChangeRequest.id == create.json()["request_id"]).one()
    assert request.college_id == env["college_a"].id
    assert db.query(KnowledgeCategory).filter(KnowledgeCategory.key == "pending-category").first() is None
    assert client.post(f"/api/v1/admin/change-requests/{request.id}/approve", headers=headers(env["super_b"]), json={}).status_code == 200
    category = db.query(KnowledgeCategory).filter(KnowledgeCategory.key == "pending-category").one()
    assert category.college_id == env["college_a"].id
    update = client.patch(f"/api/v1/admin/knowledge-db/categories/{category.id}", headers=h, json={"description": "new"})
    assert update.json()["status"] == "PENDING"
    db.refresh(category)
    assert category.description != "new"
    update_request = db.query(ChangeRequest).filter(ChangeRequest.id == update.json()["request_id"]).one()
    assert client.post(f"/api/v1/admin/change-requests/{update_request.id}/approve", headers=headers(env["super_b"]), json={}).status_code == 200
    db.refresh(category)
    assert category.description == "new"

    delete = client.delete(f"/api/v1/admin/knowledge-db/categories/{category.id}", headers=h)
    assert delete.json()["status"] == "PENDING"
    delete_request = db.query(ChangeRequest).filter(ChangeRequest.id == delete.json()["request_id"]).one()
    assert client.post(f"/api/v1/admin/change-requests/{delete_request.id}/approve", headers=headers(env["super_b"]), json={}).status_code == 200
    db.refresh(category)
    assert category.status == "INACTIVE"


def upload(client, user, filename="fees.txt", text="BCA tuition fee is INR 50000"):
    return client.post("/api/v1/admin/smart-upload/upload", headers=headers(user), files={"files": (filename, io.BytesIO(text.encode()), "text/plain")})


def test_smart_upload_pending_and_college_admin_cannot_approve(client, env):
    db = env["db_session"]
    response = upload(client, env["admin_a"])
    assert response.status_code == 200
    staged_id = response.json()["records"][0]["id"]
    staged = db.query(StagedUploadRecord).filter_by(id=staged_id).one()
    assert staged.status == "PENDING_REVIEW"
    assert db.query(KnowledgeRecord).filter(KnowledgeRecord.source_title == "fees.txt").first() is None
    assert client.post(f"/api/v1/admin/smart-upload/staged/{staged_id}/approve", headers=headers(env["admin_a"])).status_code == 403

def test_smart_upload_approval_rejection_and_tenant_preservation(client, env):
    db = env["db_session"]
    approved = upload(client, env["admin_a"], "approved.txt")
    approved_id = approved.json()["records"][0]["id"]
    response = client.post(f"/api/v1/admin/smart-upload/staged/{approved_id}/approve", headers=headers(env["super_b"]))
    assert response.status_code == 200
    staged = db.query(StagedUploadRecord).filter_by(id=approved_id).one()
    assert staged.status == "APPROVED" and staged.college_id == env["college_a"].id
    published = db.query(KnowledgeRecord).filter(KnowledgeRecord.source_title == "approved.txt").one()
    assert published.college_id == env["college_a"].id and published.verified is True
    rejected = upload(client, env["admin_a"], "rejected.txt")
    rejected_id = rejected.json()["records"][0]["id"]
    response = client.post(f"/api/v1/admin/smart-upload/staged/{rejected_id}/reject", headers=headers(env["super_b"]))
    assert response.status_code == 200
    assert db.query(StagedUploadRecord).filter_by(id=rejected_id).one().status == "REJECTED"
    assert db.query(KnowledgeRecord).filter(KnowledgeRecord.source_title == "rejected.txt").first() is None

def test_smart_upload_tenant_listing_and_no_default_tenant(client, env):
    db = env["db_session"]
    a_id = upload(client, env["admin_a"], "tenant-a.txt").json()["records"][0]["id"]
    b_id = upload(client, env["admin_b"], "tenant-b.txt").json()["records"][0]["id"]
    a_rows = {row["id"] for row in client.get("/api/v1/admin/smart-upload/staged", headers=headers(env["admin_a"])).json()}
    b_rows = {row["id"] for row in client.get("/api/v1/admin/smart-upload/staged", headers=headers(env["admin_b"])).json()}
    assert a_id in a_rows and b_id not in a_rows
    assert b_id in b_rows and a_id not in b_rows
    no_tenant = User(id="approval-super-no-tenant", email="no-tenant@test.local", full_name="No Tenant Super", role="SUPER_ADMIN", college_id=None, is_active=True, hashed_password="x")
    db.add(no_tenant)
    db.commit()
    assert upload(client, no_tenant, "ambiguous.txt").status_code == 400
