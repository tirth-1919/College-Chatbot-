"""
Cross-Tenant Security Test Suite

Verifies that College Admin users cannot access, modify, or delete
data belonging to other colleges.

Tests the tenant isolation fixes from the 2026-09-24 security audit.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.college import College
from backend.app.models.user import User
from backend.app.models.knowledge_categories import KnowledgeCategory, KnowledgeRecord
from backend.app.scripts.seed_knowledge_categories import seed_knowledge_categories

client = TestClient(app, raise_server_exceptions=True)
db = SessionLocal()

# Test Data Setup
college_a = None
college_b = None
admin_a = None
admin_b = None
super_admin = None
category_a = None
category_b = None
record_a = None
record_b = None


def setup_module():
    """Create two colleges with separate admins and data"""
    global college_a, college_b, admin_a, admin_b, super_admin
    global category_a, category_b, record_a, record_b
    
    # Clean up any existing test data
    db.query(KnowledgeRecord).filter(KnowledgeRecord.title.like("SECURITY_TEST%")).delete()
    db.query(KnowledgeCategory).filter(KnowledgeCategory.name.like("SECURITY_TEST%")).delete()
    db.query(User).filter(User.email.like("security_test%")).delete()
    db.query(College).filter(College.code.like("SEC%")).delete()
    db.commit()
    
    # Create College A
    college_a = College(
        id="sec-test-college-a",
        name="Security Test College A",
        code="SECA",
        slug="sec-test-a",
        official_email="admin@sectesta.edu",
        official_website="https://sectesta.edu",
        status="ACTIVE",
        registration_status="APPROVED"
    )
    db.add(college_a)
    
    # Create College B
    college_b = College(
        id="sec-test-college-b",
        name="Security Test College B",
        code="SECB",
        slug="sec-test-b",
        official_email="admin@sectestb.edu",
        official_website="https://sectestb.edu",
        status="ACTIVE",
        registration_status="APPROVED"
    )
    db.add(college_b)
    db.commit()
    
    # Seed categories for both colleges
    seed_knowledge_categories(db, college_id=college_a.id)
    seed_knowledge_categories(db, college_id=college_b.id)
    
    # Create specific test categories
    category_a = KnowledgeCategory(
        id="sec-cat-a",
        name="SECURITY_TEST Category A",
        key="security_test_a",
        college_id=college_a.id,
        status="ACTIVE"
    )
    db.add(category_a)
    
    category_b = KnowledgeCategory(
        id="sec-cat-b",
        name="SECURITY_TEST Category B",
        key="security_test_b",
        college_id=college_b.id,
        status="ACTIVE"
    )
    db.add(category_b)
    db.commit()
    
    # Create test records
    record_a = KnowledgeRecord(
        id="sec-rec-a",
        category_id=category_a.id,
        college_id=college_a.id,
        title="SECURITY_TEST Record A",
        value="Secret Data for College A",
        status="ACTIVE",
        verified=True
    )
    db.add(record_a)
    
    record_b = KnowledgeRecord(
        id="sec-rec-b",
        category_id=category_b.id,
        college_id=college_b.id,
        title="SECURITY_TEST Record B",
        value="Secret Data for College B",
        status="ACTIVE",
        verified=True
    )
    db.add(record_b)
    db.commit()
    
    # Create admins
    admin_a = User(
        id="sec-admin-a",
        email="security_test_admin_a@test.local",
        full_name="Security Test Admin A",
        role="COLLEGE_ADMIN",
        college_id=college_a.id,
        is_active=True
    )
    
    admin_b = User(
        id="sec-admin-b",
        email="security_test_admin_b@test.local",
        full_name="Security Test Admin B",
        role="COLLEGE_ADMIN",
        college_id=college_b.id,
        is_active=True
    )
    
    super_admin = User(
        id="sec-super-admin",
        email="security_test_super@test.local",
        full_name="Security Test Super Admin",
        role="SUPER_ADMIN",
        is_active=True
    )
    
    print(f"[SECURITY TEST] Setup complete:")
    print(f"  College A: {college_a.id}, Admin: {admin_a.id}")
    print(f"  College B: {college_b.id}, Admin: {admin_b.id}")
    print(f"  Category A: {category_a.id}, Record A: {record_a.id}")
    print(f"  Category B: {category_b.id}, Record B: {record_b.id}")


def teardown_module():
    """Clean up test data"""
    db.query(KnowledgeRecord).filter(KnowledgeRecord.title.like("SECURITY_TEST%")).delete()
    db.query(KnowledgeCategory).filter(KnowledgeCategory.name.like("SECURITY_TEST%")).delete()
    db.query(User).filter(User.email.like("security_test%")).delete()
    db.query(College).filter(College.code.like("SEC%")).delete()
    db.commit()
    db.close()


# ====================================================================
# CATEGORY TESTS
# ====================================================================

def test_cross_tenant_category_read():
    """College A Admin cannot read College B category"""
    from backend.app.core.permissions import get_current_admin_user
    app.dependency_overrides[get_current_admin_user] = lambda: admin_a
    
    # Admin A tries to read College B category
    r = client.get(f"/api/v1/admin/knowledge-db/categories/{category_b.id}")
    assert r.status_code == 404, f"Expected 404, got {r.status_code}: College A admin should not see College B category"
    
    # Admin A CAN read their own category
    r = client.get(f"/api/v1/admin/knowledge-db/categories/{category_a.id}")
    assert r.status_code == 200, "Admin A should be able to read their own category"
    
    app.dependency_overrides.clear()


def test_cross_tenant_category_update():
    """College A Admin cannot update College B category"""
    from backend.app.core.permissions import get_current_admin_user
    app.dependency_overrides[get_current_admin_user] = lambda: admin_a
    
    # Admin A tries to update College B category
    r = client.patch(f"/api/v1/admin/knowledge-db/categories/{category_b.id}", 
                     json={"description": "HACKED BY COLLEGE A"})
    assert r.status_code == 404, f"Expected 404, got {r.status_code}: Cross-tenant category update should fail"
    
    # Verify College B category was NOT modified
    app.dependency_overrides[get_current_admin_user] = lambda: admin_b
    r = client.get(f"/api/v1/admin/knowledge-db/categories/{category_b.id}")
    assert r.status_code == 200
    desc = r.json().get("description") or ""
    assert "HACKED" not in desc, "College B category should not be modified"
    
    app.dependency_overrides.clear()


def test_cross_tenant_category_delete():
    """College A Admin cannot delete College B category"""
    from backend.app.core.permissions import get_current_admin_user
    
    # Create a temporary category in College B
    app.dependency_overrides[get_current_admin_user] = lambda: admin_b
    r = client.post("/api/v1/admin/knowledge-db/categories", 
                    json={
                        "name": "SECURITY_TEST Temp B",
                        "key": "security-test-temp-b",
                        "description": "Temp category"
                    })
    assert r.status_code == 200, f"Failed to create temp category: {r.status_code} {r.text}"
    temp_cat_b_id = r.json()["id"]
    
    # Admin A tries to delete College B's temporary category
    app.dependency_overrides[get_current_admin_user] = lambda: admin_a
    r = client.delete(f"/api/v1/admin/knowledge-db/categories/{temp_cat_b_id}")
    assert r.status_code == 404, f"Expected 404, got {r.status_code}: Cross-tenant category delete should fail"
    
    # Verify category still exists
    app.dependency_overrides[get_current_admin_user] = lambda: admin_b
    r = client.get(f"/api/v1/admin/knowledge-db/categories/{temp_cat_b_id}")
    assert r.status_code == 200, "College B category should still exist"
    
    # Cleanup
    client.delete(f"/api/v1/admin/knowledge-db/categories/{temp_cat_b_id}")
    app.dependency_overrides.clear()


# ====================================================================
# RECORD TESTS
# ====================================================================

def test_cross_tenant_record_read():
    """College A Admin cannot read College B record"""
    from backend.app.core.permissions import get_current_admin_user
    app.dependency_overrides[get_current_admin_user] = lambda: admin_a
    
    # Admin A tries to read College B record
    r = client.get(f"/api/v1/admin/knowledge-db/records/{record_b.id}")
    assert r.status_code == 404, f"Expected 404, got {r.status_code}: College A admin should not see College B record"
    
    # Admin A CAN read their own record
    r = client.get(f"/api/v1/admin/knowledge-db/records/{record_a.id}")
    assert r.status_code == 200, "Admin A should be able to read their own record"
    data = r.json()
    assert data["value"] == "Secret Data for College A"
    
    app.dependency_overrides.clear()


def test_cross_tenant_record_update():
    """College A Admin cannot update College B record"""
    from backend.app.core.permissions import get_current_admin_user
    app.dependency_overrides[get_current_admin_user] = lambda: admin_a
    
    # Admin A tries to update College B record
    r = client.patch(f"/api/v1/admin/knowledge-db/records/{record_b.id}", 
                     json={"value": "HACKED BY COLLEGE A"})
    assert r.status_code == 404, f"Expected 404, got {r.status_code}: Cross-tenant record update should fail"
    
    # Verify College B record was NOT modified
    app.dependency_overrides[get_current_admin_user] = lambda: admin_b
    r = client.get(f"/api/v1/admin/knowledge-db/records/{record_b.id}")
    assert r.status_code == 200
    assert r.json()["value"] == "Secret Data for College B", "College B record should not be modified"
    
    app.dependency_overrides.clear()


def test_cross_tenant_record_delete():
    """College A Admin cannot delete College B record"""
    from backend.app.core.permissions import get_current_admin_user
    
    # Create a temporary record in College B
    app.dependency_overrides[get_current_admin_user] = lambda: admin_b
    r = client.post(f"/api/v1/admin/knowledge-db/categories/{category_b.id}/records", 
                    json={
                        "title": "SECURITY_TEST Temp Record B",
                        "value": "temp",
                        "status": "DRAFT"
                    })
    assert r.status_code == 200
    temp_rec_b_id = r.json()["id"]
    
    # Admin A tries to delete College B's temporary record
    app.dependency_overrides[get_current_admin_user] = lambda: admin_a
    r = client.delete(f"/api/v1/admin/knowledge-db/records/{temp_rec_b_id}")
    assert r.status_code == 404, f"Expected 404, got {r.status_code}: Cross-tenant record delete should fail"
    
    # Verify record still exists
    app.dependency_overrides[get_current_admin_user] = lambda: admin_b
    r = client.get(f"/api/v1/admin/knowledge-db/records/{temp_rec_b_id}")
    assert r.status_code == 200, "College B record should still exist"
    
    # Cleanup
    client.delete(f"/api/v1/admin/knowledge-db/records/{temp_rec_b_id}")
    app.dependency_overrides.clear()


def test_cross_tenant_record_duplicate():
    """College A Admin cannot duplicate College B record"""
    from backend.app.core.permissions import get_current_admin_user
    app.dependency_overrides[get_current_admin_user] = lambda: admin_a
    
    # Admin A tries to duplicate College B record
    r = client.post(f"/api/v1/admin/knowledge-db/records/{record_b.id}/duplicate")
    assert r.status_code == 404, f"Expected 404, got {r.status_code}: Cross-tenant record duplicate should fail"
    
    app.dependency_overrides.clear()


def test_cross_tenant_record_verify():
    """College A Admin cannot verify College B record"""
    from backend.app.core.permissions import get_current_admin_user
    app.dependency_overrides[get_current_admin_user] = lambda: admin_a
    
    # Admin A tries to verify College B record
    r = client.post(f"/api/v1/admin/knowledge-db/records/{record_b.id}/verify")
    assert r.status_code == 404, f"Expected 404, got {r.status_code}: Cross-tenant record verify should fail"
    
    app.dependency_overrides.clear()


def test_cross_tenant_record_enable_disable():
    """College A Admin cannot enable/disable College B record"""
    from backend.app.core.permissions import get_current_admin_user
    app.dependency_overrides[get_current_admin_user] = lambda: admin_a
    
    # Admin A tries to disable College B record
    r = client.post(f"/api/v1/admin/knowledge-db/records/{record_b.id}/disable")
    assert r.status_code == 404, f"Expected 404, got {r.status_code}: Cross-tenant record disable should fail"
    
    # Admin A tries to enable College B record
    r = client.post(f"/api/v1/admin/knowledge-db/records/{record_b.id}/enable")
    assert r.status_code == 404, f"Expected 404, got {r.status_code}: Cross-tenant record enable should fail"
    
    app.dependency_overrides.clear()


def test_cross_tenant_record_creation_in_wrong_category():
    """College A Admin cannot create records in College B category"""
    from backend.app.core.permissions import get_current_admin_user
    app.dependency_overrides[get_current_admin_user] = lambda: admin_a
    
    # Admin A tries to create record in College B category
    r = client.post(f"/api/v1/admin/knowledge-db/categories/{category_b.id}/records", 
                    json={
                        "title": "MALICIOUS Record",
                        "value": "Should not be created",
                        "status": "ACTIVE"
                    })
    assert r.status_code in [403, 404], f"Expected 403 or 404, got {r.status_code}: Cross-tenant record creation should fail"
    
    app.dependency_overrides.clear()


# ====================================================================
# SUPER ADMIN TESTS
# ====================================================================

def test_super_admin_can_access_all_colleges():
    """Super Admin can access data from all colleges"""
    from backend.app.core.permissions import get_current_admin_user
    app.dependency_overrides[get_current_admin_user] = lambda: super_admin
    
    # Super Admin can read College A record
    r = client.get(f"/api/v1/admin/knowledge-db/records/{record_a.id}")
    assert r.status_code == 200, "Super Admin should access College A record"
    
    # Super Admin can read College B record
    r = client.get(f"/api/v1/admin/knowledge-db/records/{record_b.id}")
    assert r.status_code == 200, "Super Admin should access College B record"
    
    # Super Admin can update College A record
    r = client.patch(f"/api/v1/admin/knowledge-db/records/{record_a.id}", 
                     json={"description": "Updated by Super Admin"})
    assert r.status_code == 200, "Super Admin should update any record"
    
    app.dependency_overrides.clear()


# ====================================================================
# COLLEGE_ID ASSIGNMENT TESTS
# ====================================================================

def test_record_creation_assigns_college_id():
    """Verify new records receive correct college_id"""
    from backend.app.core.permissions import get_current_admin_user
    app.dependency_overrides[get_current_admin_user] = lambda: admin_a
    
    # Create record in College A
    r = client.post(f"/api/v1/admin/knowledge-db/categories/{category_a.id}/records", 
                    json={
                        "title": "SECURITY_TEST New Record A",
                        "value": "Test value",
                        "status": "DRAFT"
                    })
    assert r.status_code == 200
    new_rec_id = r.json()["id"]
    
    # Verify record has correct college_id in database
    rec = db.query(KnowledgeRecord).filter(KnowledgeRecord.id == new_rec_id).first()
    assert rec is not None, "Record should exist in database"
    assert rec.college_id == college_a.id, f"Record college_id should be {college_a.id}, got {rec.college_id}"
    
    # Cleanup
    client.delete(f"/api/v1/admin/knowledge-db/records/{new_rec_id}")
    app.dependency_overrides.clear()


def test_record_duplication_preserves_college_id():
    """Verify duplicated records preserve college_id"""
    from backend.app.core.permissions import get_current_admin_user
    app.dependency_overrides[get_current_admin_user] = lambda: admin_a
    
    # Duplicate record in College A
    r = client.post(f"/api/v1/admin/knowledge-db/records/{record_a.id}/duplicate")
    assert r.status_code == 200
    dup_rec_id = r.json()["id"]
    
    # Verify duplicate has correct college_id in database
    dup = db.query(KnowledgeRecord).filter(KnowledgeRecord.id == dup_rec_id).first()
    assert dup is not None, "Duplicate record should exist in database"
    assert dup.college_id == college_a.id, f"Duplicate college_id should be {college_a.id}, got {dup.college_id}"
    assert dup.college_id == record_a.college_id, "Duplicate should have same college_id as original"
    
    # Cleanup
    client.delete(f"/api/v1/admin/knowledge-db/records/{dup_rec_id}")
    app.dependency_overrides.clear()


# ====================================================================
# RUN ALL TESTS
# ====================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
