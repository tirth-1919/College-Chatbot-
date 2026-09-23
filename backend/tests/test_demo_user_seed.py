"""Demo user seed + login test.

Verifies:
1. The demo student account exists exactly once after seeding (idempotent).
2. Login through the normal auth flow succeeds (JWT issued).
3. Plaintext password is never stored in the database.
"""
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.user import User
from backend.app.scripts.seed_ait_data import seed_initial_ait_knowledge

DEMO_EMAIL = "1@gmail.com"
DEMO_PASSWORD = "1"  # test-only; the production/demo value is identical by design
SECOND_DEMO_EMAIL = "2@gmail.com"
SECOND_DEMO_PASSWORD = "2"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_demo_user_seeded_idempotent(client):
    db = SessionLocal()
    try:
        seed_initial_ait_knowledge(db)
        seed_initial_ait_knowledge(db)  # second run must not duplicate
        users = db.query(User).filter(User.email == DEMO_EMAIL).all()
        assert len(users) == 1
        demo = users[0]
        assert demo.role == "STUDENT"
        assert demo.is_active is True
        # Never store plaintext
        assert demo.hashed_password != DEMO_PASSWORD
        assert demo.hashed_password.startswith("$2")
    finally:
        db.close()


def test_demo_user_login(client):
    resp = client.post("/api/v1/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["user"]["email"] == DEMO_EMAIL
    # 1@gmail.com is seeded as a demo STUDENT under the multi-college architecture
    # (see seed_ait_data.py); must match the seeder, not the old demo-admin setup.
    assert body["user"]["role"] == "STUDENT"
    # Password must not leak through the API response
    assert "hashed_password" not in resp.text
    assert "password" not in resp.json().get("user", {})


def test_second_demo_user_login(client):
    resp = client.post("/api/v1/auth/login", json={"email": SECOND_DEMO_EMAIL, "password": SECOND_DEMO_PASSWORD})
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["user"]["email"] == SECOND_DEMO_EMAIL
    # 2@gmail.com is seeded as a demo COLLEGE_ADMIN under the multi-college
    # architecture (see seed_ait_data.py); must match the seeder.
    assert body["user"]["role"] == "COLLEGE_ADMIN"
    assert "hashed_password" not in resp.text
