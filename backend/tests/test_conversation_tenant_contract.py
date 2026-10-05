'''Persisted API contract tests for explicit conversation tenancy.'''
import uuid
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.app.api.v1.conversations import router
from backend.app.core.database import Base, get_db
from backend.app.core.security import create_access_token
from backend.app.models.college import College
from backend.app.models.conversation import Conversation
from backend.app.models.user import User
@pytest.fixture
def tenant_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    ait = College(id="test-ait", name="AIT", code="AIT", slug="ait", status="ACTIVE", registration_status="APPROVED")
    rcti = College(id="test-rcti", name="RCTI", code="RCTI", slug="rcti", status="ACTIVE", registration_status="APPROVED")
    user = User(id=str(uuid.uuid4()), email="tenant-user@example.test", full_name="Tenant User", role="STUDENT")
    db.add_all([ait, rcti, user]); db.commit()
    app = FastAPI(); app.include_router(router)
    def override_db():
        request_db = Session()
        try: yield request_db
        finally: request_db.close()
    app.dependency_overrides[get_db] = override_db
    headers = {"Authorization": f"Bearer {create_access_token({'sub': user.id})}"}
    try: yield TestClient(app), db, headers, ait, rcti
    finally: db.close(); Base.metadata.drop_all(engine); engine.dispose()

def test_create_persists_ait_and_rcti(tenant_client):
    client, db, headers, ait, rcti = tenant_client
    a = client.post("/conversations", headers=headers, json={"college_id": ait.id}).json()
    r = client.post("/conversations", headers=headers, json={"college_id": rcti.id}).json()
    assert db.get(Conversation, a["id"]).college_id == ait.id
    assert db.get(Conversation, r["id"]).college_id == rcti.id

def test_create_without_tenant_rejected(tenant_client):
    client, db, headers, _, _ = tenant_client
    response = client.post("/conversations", headers=headers, json={})
    assert response.status_code == 409
    assert db.query(Conversation).count() == 0
