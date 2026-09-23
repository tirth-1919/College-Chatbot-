"""§SPEC RCTI location regression tests.

TEST 1/2/3/5: location questions inside an RCTI conversation must route to
tenant-scoped institutional retrieval and surface the verified RCTI
contact/location record (never AIT's).
TEST 6 + verified-label bug: a refusal answer must NEVER carry
grounding_status "verified" (no "Verified College Fact" badge).
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


@pytest.fixture(scope="module")
def db_session():
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
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(scope="module")
def env(db_session):
    from backend.app.models.college import College, CollegeAlias
    from backend.app.models.knowledge import AitEntity
    from backend.app.models.user import User

    now = datetime.now(timezone.utc)
    ait = College(id="loc-ait", name="Ahmedabad Institute of Technology",
                  code="AIT", slug="ait", status="ACTIVE", created_at=now)
    rcti = College(id="loc-rcti", name="R.C. Technical Institute",
                   code="RCTI", slug="rcti", status="ACTIVE",
                   official_website="https://www.rcti.ac.in/",
                   city="Ahmedabad", state="Gujarat", created_at=now)
    db_session.add_all([ait, rcti])
    for a in ["RC Technical", "RCT", "R.C. Technical", "rcti",
              "R.C. Technical Institute"]:
        from backend.app.chat.college_context import normalize
        db_session.add(CollegeAlias(college_id=rcti.id, alias=a,
                                    normalized_alias=normalize(a)))
    # AIT-only verified location record (must NEVER leak into RCTI answers)
    db_session.add(AitEntity(
        id="e-loc-ait", college_id=ait.id, category="contact",
        name="AIT Official Contact Information", code="CONTACT",
        details={"address": "Gota-Ognaj Road, Ahmedabad - 380060",
                 "location": "Gota, Ahmedabad"},
        source_url="https://www.aitindia.in/contact", content_hash="ha",
        is_verified=True, authority="Official AIT Website"))
    # RCTI verified location record
    db_session.add(AitEntity(
        id="e-loc-rcti", college_id=rcti.id, category="contact",
        name="Official Website & Location", code="CONTACT",
        details={"website": "https://www.rcti.ac.in/",
                 "location": "Sola, Ahmedabad, Gujarat, India"},
        source_url="https://www.rcti.ac.in/", content_hash="hr",
        is_verified=True, authority="Official RCTI Website"))
    user = User(id="loc-user", email="loc@test.com", full_name="T", role="STUDENT",
                is_active=True, hashed_password="x")
    db_session.add(user)
    db_session.commit()
    return {"db": db_session, "ait": ait, "rcti": rcti, "user": user}


def _headers(env):
    return {"Authorization": f"Bearer {create_access_token({'sub': env['user'].id})}"}


def _rcti_conversation(client, env):
    """Establish an RCTI conversation via the normal onboarding flow."""
    conv_id = f"conv-{uuid.uuid4().hex[:8]}"
    client.post("/api/v1/chat/stream", headers=_headers(env),
                json={"conversation_id": conv_id, "message": "hello"})
    client.post("/api/v1/chat/stream", headers=_headers(env),
                json={"conversation_id": conv_id, "message": "R.C. Technical Institute"})
    return conv_id


@pytest.mark.parametrize("question", [
    "Where is R.C. Technical Institute?",
    "Where R.C. Technical Institute?",
    "What is the address of RCTI?",
    "Where is the college located?",
])
def test_rcti_location_uses_tenant_record(client, env, question):
    """TEST 1/2/3: RCTI conversation answers location from RCTI record only."""
    from backend.app.models.conversation import Message
    db = env["db"]
    conv_id = _rcti_conversation(client, env)

    res = client.post("/api/v1/chat/stream", headers=_headers(env),
                      json={"conversation_id": conv_id, "message": question})
    assert res.status_code == 200
    msgs = (db.query(Message)
            .filter(Message.conversation_id == conv_id)
            .order_by(Message.created_at.asc()).all())
    last = [m for m in msgs if m.sender == "assistant"][-1]
    blob = f"{last.content} {str(last.provenance)} {str(last.citations)}".lower()
    # RCTI verified location present
    assert "sola" in blob or "rcti.ac.in" in blob, f"no RCTI location: {last.content[:200]}"
    # AIT location NEVER leaks
    assert "gota-ognaj" not in blob and "380060" not in blob
    # If labeled verified, provenance must be the RCTI source, not AIT
    if last.grounding_status == "verified":
        assert "ait" not in (last.provenance.get("source_domain") or "")
        assert "aitindia" not in str(last.provenance.get("source_url") or "").lower()


def test_refusal_answer_is_never_verified_badge():
    """TEST 6: refusal text must not be grounded 'verified' (no fake badge)."""
    from backend.app.knowledge.grounding import grounding_validator
    out = grounding_validator.validate_answer(
        query="Where is R.C. Technical Institute?",
        route="ait_institutional",
        retrieved_evidence=[{"name": "weak", "details": "x"}],
        candidate_answer="I'm sorry, I couldn't verify the location information "
                         "of R.C. Technical Institute from the available official sources.",
    )
    assert out["grounding_status"] == "unverified"


def test_ait_location_regression(client, env):
    """Regression: AIT conversation location answers still work."""
    from backend.app.models.conversation import Message
    db = env["db"]
    conv_id = f"conv-{uuid.uuid4().hex[:8]}"
    client.post("/api/v1/chat/stream", headers=_headers(env),
                json={"conversation_id": conv_id, "message": "hello"})
    client.post("/api/v1/chat/stream", headers=_headers(env),
                json={"conversation_id": conv_id, "message": "Ahmedabad Institute of Technology"})
    res = client.post("/api/v1/chat/stream", headers=_headers(env),
                      json={"conversation_id": conv_id, "message": "Where is the college located?"})
    assert res.status_code == 200
    msgs = (db.query(Message)
            .filter(Message.conversation_id == conv_id)
            .order_by(Message.created_at.asc()).all())
    last = [m for m in msgs if m.sender == "assistant"][-1]
    blob = f"{last.content} {str(last.provenance)} {str(last.citations)}".lower()
    assert "380060" in blob or "gota" in blob, f"AIT location missing: {last.content[:200]}"
    assert "rcti.ac.in" not in blob and "sola" not in blob
