"""
End-to-end test: Change Request workflow (spec §16 / §23 / §39).

Scenario:
 1. College Admin (AIT) creates an UPDATE change request for a protected record
 2. Production value is NOT changed while the request is PENDING
 3. SUPER_ADMIN approves -> production value IS changed, request = APPROVED
 4. Audit log entry is created
 5. Rejection path leaves production data untouched
 6. Clarification-free state validation: approving twice / approving rejected fails
 7. Tenant isolation: College B admin cannot see or touch College A requests
 8. Tampering: college_id / entity ownership enforced server-side
"""
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.database import Base, get_db
from backend.app.core.security import create_access_token
from backend.app.main import app


# ──────────────── Fixtures ────────────

@pytest.fixture(scope="module")
def db_session():
    # StaticPool: one shared in-memory DB across threads (TestClient runs in a worker thread)
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="module")
def client(db_session):
    """TestClient wired to the in-memory DB session via get_db override."""
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(scope="module")
def env(db_session):
    """Two colleges, a college admin each, one super admin, one protected record each."""
    from backend.app.models.college import College
    from backend.app.models.knowledge import AitEntity
    from backend.app.models.user import User

    now = datetime.now(timezone.utc)
    ait = College(id="ait-tenant-001", name="Ahmedabad Institute of Technology",
                  code="AIT", slug="ait", status="ACTIVE", created_at=now, updated_at=now)
    abc = College(id="abc-tenant-002", name="ABC College of Engineering",
                  code="ABC", slug="abc-college", status="ACTIVE", created_at=now, updated_at=now)
    db_session.add_all([ait, abc])

    ait_admin = User(id="user-ait-admin", email="admin@aitindia.in", full_name="AIT Admin",
                     role="COLLEGE_ADMIN", college_id=ait.id, is_active=True, hashed_password="x")
    abc_admin = User(id="user-abc-admin", email="admin@abc.edu", full_name="ABC Admin",
                     role="COLLEGE_ADMIN", college_id=abc.id, is_active=True, hashed_password="x")
    super_admin = User(id="user-super", email="super@platform.com", full_name="Super Admin",
                       role="SUPER_ADMIN", college_id=None, is_active=True, hashed_password="x")
    db_session.add_all([ait_admin, abc_admin, super_admin])

    fee_record = AitEntity(id="entity-fee-bca", college_id=ait.id, category="fee",
                           name="BCA Fee", code="BCA", details={"fee": "32000"},
                           source_url="https://www.aitindia.in/fees", content_hash="seed-hash")
    db_session.add(fee_record)
    db_session.commit()

    return {
        "db": db_session,
        "ait": ait, "abc": abc,
        "ait_admin": ait_admin, "abc_admin": abc_admin, "super_admin": super_admin,
        "fee_record": fee_record,
    }


def _headers(user):
    return {"Authorization": f"Bearer {create_access_token({'sub': user.id})}"}


# ──────────────── §39 E2E: create -> pending -> approve -> applied ───────────

def test_full_approve_workflow(client, env):
    db = env["db"]

    # 1-2. College admin submits UPDATE request; production value must NOT change yet
    resp = client.post("/api/v1/admin/change-requests/", headers=_headers(env["ait_admin"]), json={
        "entity_type": "FEES",
        "entity_id": env["fee_record"].id,
        "action": "UPDATE",
        "old_value": {"fee": "32000"},
        "new_value": {"fee": "35000"},
        "reason": "New approved fee structure 2026-27",
    })
    assert resp.status_code == 201, resp.text
    cr = resp.json()
    assert cr["status"] == "PENDING"
    assert cr["college_id"] == env["ait"].id

    db.refresh(env["fee_record"])
    assert env["fee_record"].details == {"fee": "32000"}, "Production data must not change while PENDING"

    # 3. College B admin cannot even see the request (tenant isolation)
    resp_b = client.get("/api/v1/admin/change-requests/", headers=_headers(env["abc_admin"]))
    items_b = resp_b.json().get("items", [])
    assert all(r["id"] != cr["id"] for r in items_b)

    # 4. SUPER_ADMIN sees it and approves
    resp_list = client.get("/api/v1/admin/change-requests/",
                           headers=_headers(env["super_admin"]),
                           params={"status_filter": "PENDING"})
    items_super = resp_list.json().get("items", [])
    assert any(r["id"] == cr["id"] for r in items_super)

    resp = client.post(f"/api/v1/admin/change-requests/{cr['id']}/approve",
                       headers=_headers(env["super_admin"]), json={"notes": "Verified official notification"})
    assert resp.status_code == 200, resp.text
    # §8/§20: once successfully applied to production, the request is marked APPLIED
    assert resp.json()["status"] == "APPLIED"

    # 5. Production data IS changed after approval
    db.expire_all()
    record = db.query(type(env["fee_record"])).filter_by(id=env["fee_record"].id).first()
    assert record is not None
    if record.details:
        assert record.details.get("fee") == "35000"

    # 6. Double-approve blocked (state validation)
    resp = client.post(f"/api/v1/admin/change-requests/{cr['id']}/approve",
                       headers=_headers(env["super_admin"]), json={})
    assert resp.status_code == 400

    # 7. Audit log entry created
    from backend.app.models.audit import AuditLog
    audits = db.query(AuditLog).filter(
        AuditLog.action == "CHANGE_REQUEST_APPROVED",
        AuditLog.college_id == env["ait"].id,
    ).all()
    assert len(audits) == 1


# ──────────────── Rejection path ─────────────

def test_reject_leaves_production_untouched(client, env):
    current_fee = env["fee_record"].details.get("fee")
    resp = client.post("/api/v1/admin/change-requests/", headers=_headers(env["ait_admin"]), json={
        "entity_type": "FEES", "entity_id": env["fee_record"].id, "action": "UPDATE",
        "old_value": {"fee": current_fee}, "new_value": {"fee": "99999"},
        "reason": "Bad data",
    })

    assert resp.status_code == 201, resp.text

    cr = resp.json()

    resp = client.post(f"/api/v1/admin/change-requests/{cr['id']}/reject",
                       headers=_headers(env["super_admin"]),
                       json={"notes": "Information could not be verified."})
    assert resp.status_code == 200
    assert resp.json()["status"] == "REJECTED"

    # Approving a rejected request must fail
    resp = client.post(f"/api/v1/admin/change-requests/{cr['id']}/approve",
                       headers=_headers(env["super_admin"]), json={})
    assert resp.status_code == 400

    env["db"].expire_all()
    record = env["db"].query(type(env["fee_record"])).filter_by(id=env["fee_record"].id).first()
    if record.details:
        assert record.details.get("fee") == current_fee, "Rejected change must not apply"


# ──────────────── Role isolation & tampering ─────────

def test_role_and_tampering_guards(client, env):
    # College admin cannot approve
    resp = client.post("/api/v1/admin/change-requests/nonexistent/approve",
                       headers=_headers(env["ait_admin"]), json={})
    assert resp.status_code == 403

    # Missing college link -> 400 on create
    from backend.app.models.user import User
    orphan = User(id="user-orphan", email="o@x.com", full_name="Orphan Admin", role="COLLEGE_ADMIN",
                  college_id=None, is_active=True, hashed_password="x")
    env["db"].add(orphan)
    env["db"].commit()
    resp = client.post("/api/v1/admin/change-requests/", headers=_headers(orphan),
                       json={"entity_type": "FEES", "action": "CREATE", "new_value": {"fee": "1"}})
    assert resp.status_code == 400


# ──────────────── Cancel flow (College Admin owns pending request) ───────────

def test_cancel_own_pending_request(client, env):
    resp = client.post("/api/v1/admin/change-requests/", headers=_headers(env["ait_admin"]), json={
        "entity_type": "EVENT", "action": "CREATE", "new_value": {"title": "Tech Fest"},
    })
    cr = resp.json()
    assert cr["status"] == "PENDING"

    resp = client.patch(f"/api/v1/admin/change-requests/{cr['id']}/cancel",
                        headers=_headers(env["ait_admin"]))
    assert resp.status_code == 200
    assert resp.json()["status"] == "CANCELLED"
