"""E2E smoke test: knowledge-db categories & records APIs (admin RBAC + retrieval mirroring)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from fastapi.testclient import TestClient
from fastapi import HTTPException
from backend.app.main import app
from backend.app.core.database import get_db, SessionLocal
from backend.app.core.permissions import get_current_admin_user
from backend.app.models.user import User
from backend.app.models.knowledge import AitEntity

# Override admin auth for test
admin_user = User(id="test-admin", email="admin@test.local", full_name="Test Admin", role="SUPER_ADMIN", is_active=True)
app.dependency_overrides[get_current_admin_user] = lambda: admin_user

client = TestClient(app, raise_server_exceptions=False)
db = SessionLocal()
ok = fail = 0

def run_checks():
    return 0 if fail == 0 else 1

def test_knowledge_db_e2e():
    assert fail == 0, f"{fail} knowledge-db checks failed"

def check(name, cond):
    global ok, fail
    print(("PASS  " if cond else "FAIL  ") + name)
    ok, fail = ok + (1 if cond else 0), fail + (0 if cond else 1)

# --- Categories ---
r = client.get("/api/v1/admin/knowledge-db/categories")
check("list categories 200", r.status_code == 200 and r.json()["total"] >= 22)
cats = {c["key"]: c for c in r.json()["items"]}
sch = cats["scholarships"]

r = client.post("/api/v1/admin/knowledge-db/categories", json={"name": "Hostel", "key": "hostel", "description": "AIT hostel information", "display_order": 23})
check("create category (future category test)", r.status_code == 200)
hostel_id = r.json().get("id")

r = client.post("/api/v1/admin/knowledge-db/categories", json={"name": "Scholarships", "key": "scholarships"})
check("duplicate category rejected 409", r.status_code == 409)

r = client.post("/api/v1/admin/knowledge-db/categories", json={"name": "Bad Key!", "key": "Bad Key!"})
check("unsafe key rejected 422", r.status_code == 422)

r = client.patch(f"/api/v1/admin/knowledge-db/categories/{hostel_id}", json={"description": "Updated hostel desc"})
check("edit category", r.status_code == 200)

r = client.patch(f"/api/v1/admin/knowledge-db/categories/{hostel_id}", json={"status": "INACTIVE"})
check("disable category", r.status_code == 200)
r = client.patch(f"/api/v1/admin/knowledge-db/categories/{hostel_id}", json={"status": "ACTIVE"})
check("enable category", r.status_code == 200)

# --- Records (scholarship flow) ---
rec_payload = {
    "title": "Test Merit Scholarship", "course": "BCA", "academic_year": "2026-27",
    "value": "Test value", "description": "Test scholarship",
    "metadata": {"type": "Merit", "benefit_type": "Fee Waiver", "amount": "25000", "eligibility": "85%+ in 12th"},
    "source_type": "ADMIN_VERIFIED", "verified": True, "status": "ACTIVE",
}
r = client.post(f"/api/v1/admin/knowledge-db/categories/{sch['id']}/records", json=rec_payload)
check("create scholarship record", r.status_code == 200)
rec_id = r.json()["id"]

# retrieval mirror: ACTIVE+verified record appears in ait_entities for chatbot
mirrored = db.query(AitEntity).filter(AitEntity.source_page == f"knowledge-record:{rec_id}").first()
check("record mirrored to chatbot retrieval store", mirrored is not None and mirrored.authority == "Admin Verified Database" and mirrored.is_verified)

r = client.get(f"/api/v1/admin/knowledge-db/records/{rec_id}")
check("view record detail", r.status_code == 200 and r.json()["title"] == "Test Merit Scholarship")

r = client.patch(f"/api/v1/admin/knowledge-db/records/{rec_id}", json={"value": "Updated value"})
check("edit record", r.status_code == 200 and "Updated" in r.json()["message"])

r = client.post(f"/api/v1/admin/knowledge-db/records/{rec_id}/duplicate")
check("duplicate record -> draft", r.status_code == 200)
dup_id = r.json()["id"]
r = client.get(f"/api/v1/admin/knowledge-db/records/{dup_id}")
check("duplicate is Draft+unverified", r.json()["status"] == "DRAFT" and not r.json()["verified"])

r = client.post(f"/api/v1/admin/knowledge-db/records/{rec_id}/disable")
check("disable record", r.status_code == 200)
mirrored = db.query(AitEntity).filter(AitEntity.source_page == f"knowledge-record:{rec_id}").first()
check("disabled record removed from retrieval", mirrored is None)
r = client.post(f"/api/v1/admin/knowledge-db/records/{rec_id}/enable")
check("enable record", r.status_code == 200)

# search/filter/pagination
r = client.get(f"/api/v1/admin/knowledge-db/categories/{sch['id']}/records", params={"search": "Merit"})
check("search records", r.status_code == 200 and r.json()["total"] >= 2)
r = client.get(f"/api/v1/admin/knowledge-db/categories/{sch['id']}/records", params={"course": "BCA", "academic_year": "2026-27", "source_type": "ADMIN_VERIFIED", "record_status": "ACTIVE"})
check("combined filters", r.status_code == 200 and r.json()["total"] >= 1)
r = client.get(f"/api/v1/admin/knowledge-db/categories/{sch['id']}/records", params={"limit": 1, "skip": 0})
check("pagination fields", r.json()["total"] >= 1 and len(r.json()["items"]) == 1)

# delete protections
r = client.delete(f"/api/v1/admin/knowledge-db/records/{rec_id}")
check("delete verified record as SUPER_ADMIN ok", r.status_code == 200)
client.patch(f"/api/v1/admin/knowledge-db/records/{dup_id}", json={"verified": True})
r = client.delete(f"/api/v1/admin/knowledge-db/records/{dup_id}")
check("delete verified record ok (super admin)", r.status_code == 200)

# category containing records cannot be deleted
r = client.post(f"/api/v1/admin/knowledge-db/categories/{sch['id']}/records", json={"title": "blocker", "status": "DRAFT"})
bid = r.json()["id"]
r = client.delete(f"/api/v1/admin/knowledge-db/categories/{sch['id']}")
check("category with records NOT deletable (409)", r.status_code == 409)
client.delete(f"/api/v1/admin/knowledge-db/records/{bid}")

# empty category delete
r = client.delete(f"/api/v1/admin/knowledge-db/categories/{hostel_id}")
check("delete empty category", r.status_code == 200)

# --- RBAC: student must be denied ---
def deny():
    raise HTTPException(status_code=403, detail="Access denied. Administrator privileges required.")
app.dependency_overrides[get_current_admin_user] = deny
r = client.get("/api/v1/admin/knowledge-db/categories")
check("unauthorized access rejected 403", r.status_code == 403)
app.dependency_overrides.clear()

db.close()


def test_knowledge_db_e2e():
    assert fail == 0, f"{fail} knowledge-db checks failed"

if __name__ == "__main__":
    print(f"\n{ok} passed, {fail} failed")
    raise SystemExit(run_checks())
