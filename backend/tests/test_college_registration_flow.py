import uuid
import pytest
from fastapi.testclient import TestClient

from backend.app.core.database import SessionLocal
from backend.app.models.college import College
from backend.app.models.user import User
from backend.app.core.security import get_password_hash, create_access_token
from admin import admin_app
from user import user_app

user_client = TestClient(user_app)
admin_client = TestClient(admin_app)


@pytest.fixture(scope="function")
def db_session():
    db = SessionLocal()
    yield db
    db.close()


def test_public_registration_creates_pending_request_and_no_admin(db_session):
    unique_suffix = str(uuid.uuid4())[:8]
    payload = {
        "college_name": f"Test Institute {unique_suffix}",
        "college_code": f"TI{unique_suffix[:4].upper()}",
        "official_website": f"https://test-{unique_suffix}.edu",
        "official_email": f"info@{unique_suffix}.edu",
        "contact_person": "Dean Testing",
        "contact_email": f"dean@{unique_suffix}.edu",
        "contact_phone": "+91 9876543210",
        "address": "100 Campus Avenue",
        "city": "Ahmedabad",
        "state": "Gujarat",
        "country": "India",
        "university_affiliation": "GTU",
        "description": "Premier testing college"
    }

    # Public registration via user portal (/api/v1/colleges/register)
    res = user_client.post("/api/v1/colleges/register", json=payload)
    assert res.status_code == 201, res.text
    data = res.json()
    assert "application_id" in data
    app_id = data["application_id"]
    assert app_id.startswith("COL-2026-")
    assert data["status"] == "PENDING APPROVAL"

    # Verify directly in DB
    college = db_session.query(College).filter(College.application_id == app_id).first()
    assert college is not None
    assert college.status == "PENDING"
    assert college.registration_status == "PENDING"

    # Verify that NO active College Admin user account exists yet for this college
    admin_user = db_session.query(User).filter(User.college_id == college.id).first()
    assert admin_user is None

    # Verify status check endpoint is publicly queryable
    status_res = user_client.get(f"/api/v1/colleges/registration-status/{app_id}")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["application_id"] == app_id
    assert status_data["status"] == "PENDING"
    assert status_data["status_label"] == "PENDING SUPER ADMIN APPROVAL"


def test_duplicate_registration_rejected(db_session):
    unique_suffix = str(uuid.uuid4())[:8]
    payload = {
        "college_name": f"Duplicate College {unique_suffix}",
        "official_website": f"https://dup-{unique_suffix}.edu",
        "official_email": f"contact@{unique_suffix}.edu",
        "contact_person": "Registrar",
        "contact_email": f"reg@{unique_suffix}.edu",
        "contact_phone": "9876543210",
        "address": "42 Duplicate Lane",
        "city": "Surat",
        "state": "Gujarat"
    }

    res1 = user_client.post("/api/v1/colleges/register", json=payload)
    assert res1.status_code == 201

    # Attempting to submit exact same name again
    res2 = user_client.post("/api/v1/colleges/register", json=payload)
    assert res2.status_code == 400
    assert "already" in res2.json()["detail"].lower()


def test_super_admin_approves_and_provisions_admin(db_session):
    unique_suffix = str(uuid.uuid4())[:8]
    payload = {
        "college_name": f"Approved University {unique_suffix}",
        "official_website": f"https://appr-{unique_suffix}.edu",
        "official_email": f"admin@{unique_suffix}.edu",
        "contact_person": "Chancellor",
        "contact_email": f"chancellor@{unique_suffix}.edu",
        "contact_phone": "9876543210",
        "address": "1 University Plaza",
        "city": "Gandhinagar",
        "state": "Gujarat"
    }

    res = user_client.post("/api/v1/colleges/register", json=payload)
    assert res.status_code == 201
    app_id = res.json()["application_id"]

    college = db_session.query(College).filter(College.application_id == app_id).first()
    assert college is not None
    college_id = college.id

    # Find or create super admin user
    super_admin = db_session.query(User).filter(User.role == "SUPER_ADMIN").first()
    if not super_admin:
        super_admin = User(
            id=str(uuid.uuid4()),
            email="3@gmail.com",
            full_name="Platform Super Admin",
            role="SUPER_ADMIN",
            is_active=True,
            is_admin=True,
            hashed_password=get_password_hash("3")
        )
        db_session.add(super_admin)
        db_session.commit()

    # Create super admin token with real user ID
    super_admin_token = create_access_token({
        "sub": super_admin.id,
        "email": super_admin.email,
        "role": "SUPER_ADMIN",
        "is_admin": True
    })

    # Super Admin approves the college
    approve_res = admin_client.post(
        f"/api/v1/admin/colleges/{college_id}/approve",
        headers={"Authorization": f"Bearer {super_admin_token}"}
    )
    assert approve_res.status_code == 200, approve_res.text
    approve_data = approve_res.json()
    assert "admin_credentials" in approve_data or "credentials" in approve_data

    # Verify college is now ACTIVE
    db_session.refresh(college)
    assert college.status == "ACTIVE"
    assert college.registration_status == "APPROVED"

    # Verify College Admin account was provisioned
    college_admin = db_session.query(User).filter(User.college_id == college_id).first()
    assert college_admin is not None
    assert college_admin.role == "COLLEGE_ADMIN"
    assert college_admin.must_change_password is True
