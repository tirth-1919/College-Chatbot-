"Deterministic end-to-end AIT tenant regression."""
import hashlib
from datetime import datetime, timezone
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.app.api.v1.chat import router as chat_router
from backend.app.core.database import Base, get_db
from backend.app.core.security import create_access_token
from backend.app.models.college import College
from backend.app.models.conversation import Conversation
from backend.app.models.knowledge import AitEntity, WebsiteSnapshot
from backend.app.models.user import User
from backend.app.ai.router import ai_router
AIT_ID = "regression-ait"
RCTI_ID = "regression-rcti"
THIRD_ID = "regression-third"
USER_ID = "regression-ait-user"
AIT_FACT = "Ahmedabad Institute of Technology library timing is 07:17 AM to 07:19 PM."
RCTI_FACT = "R.C. Technical Institute library timing is 11:11 AM to 05:11 PM."
THIRD_FACT = "Test Engineering College library timing is 01:13 PM to 06:13 PM."


def _hash(value):
    return hashlib.sha256(value.encode()).hexdigest()

@pytest.fixture
def ait_regression():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False)
    db = factory()
    now = datetime.now(timezone.utc)
    ait = College(id=AIT_ID, name="Ahmedabad Institute of Technology", code="AIT",
                  slug="regression-ait", status="ACTIVE", registration_status="APPROVED", created_at=now)
    rcti = College(id=RCTI_ID, name="R.C. Technical Institute", code="RCTI",
                   slug="regression-rcti", status="ACTIVE", registration_status="APPROVED", created_at=now)
    third = College(id=THIRD_ID, name="Test Engineering College", code="TEST-ENGINEERING",
                    slug="regression-third", status="ACTIVE", registration_status="APPROVED", created_at=now)
    user = User(id=USER_ID, email="ait-regression@example.test", full_name="AIT Regression",
                role="STUDENT", is_active=True, hashed_password="x")
    db.add_all([ait, rcti, third, user])
    db.flush()
    for college, fact, key in ((ait, AIT_FACT, "ait"), (rcti, RCTI_FACT, "rcti"), (third, THIRD_FACT, "third")):
        db.add(AitEntity(
            id=f"regression-{key}-entity", college_id=college.id, category="facility",
            name=f"{college.name} Library Timing", details={"library_timing": fact, "fact": fact},
            source_url=f"https://{key}.regression.test/quantum-lab", source_type="ADMIN_VERIFIED",
            is_official=False, authority=f"{college.name} Verified Database", is_verified=True,
            content_hash=_hash(fact),
        ))
    conversation = Conversation(id="regression-ait-conversation", user_id=USER_ID,
                                college_id=AIT_ID, conversation_type="NORMAL", title="AIT regression")
    db.add(conversation)
    db.commit()

    app = FastAPI()
    app.include_router(chat_router, prefix="/api/v1")

    def override_db():
        request_db = factory()
        try:
            yield request_db
        finally:
            request_db.close()

    app.dependency_overrides[get_db] = override_db
    try:
        yield {"db": db, "client": TestClient(app), "ait": ait, "rcti": rcti,
               "third": third, "conversation": conversation,
               "headers": {"Authorization": f"Bearer {create_access_token({'sub': USER_ID})}"}}
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


EXACT_SUPPORT_QUESTION = "Which student support or counselling services are available at Ahmedabad Institute of Technology?"


def _add_ait_event_snapshots(db):
    for title, slug, text in (
        ("De-addiction Awareness Walkathon", "walkathon", "Students joined a de-addiction awareness campaign and walkathon."),
        ("Institute Level Hackathon", "hackathon", "Students participated in the institute-level hackathon."),
        ("Celebration Days", "celebration-days", "Students celebrated institute celebration days and campus events."),
    ):
        db.add(WebsiteSnapshot(
            college_id=AIT_ID, url=f"https://ait.regression.test/events/{slug}", title=title,
            text_content=text, content_hash=slug, status_code=200,
        ))
    db.commit()


def test_ait_student_support_question_rejects_event_snapshots_and_skips_gemini(ait_regression, monkeypatch):
    env = ait_regression
    _add_ait_event_snapshots(env["db"])
    calls = []

    async def forbidden_provider(**kwargs):
        calls.append(kwargs)
        raise AssertionError("Gemini must not be used for missing student-support evidence")

    monkeypatch.setattr(ai_router, "generate_response", forbidden_provider)
    response = env["client"].post(
        "/api/v1/chat/stream", headers=env["headers"],
        json={"conversation_id": env["conversation"].id, "message": EXACT_SUPPORT_QUESTION},
    )
    assert response.status_code == 200
    assert "Walkathon" not in response.text
    assert "Hackathon" not in response.text
    assert "Celebration" not in response.text
    assert '"source_type": "NO_VERIFIED_INFORMATION"' in response.text
    assert calls == []

    from backend.app.models.conversation import Message
    assistant = env["db"].query(Message).filter_by(
        conversation_id=env["conversation"].id, sender="assistant").one()
    assert "student support or counselling services could not be verified" in assistant.content
    assert assistant.provenance.get("source_type") == "NO_VERIFIED_INFORMATION"
    assert assistant.provenance.get("verified") is False

def test_ait_student_support_question_accepts_explicit_counselling_record(ait_regression):
    env = ait_regression
    entity = AitEntity(
        id="regression-ait-counselling", college_id=AIT_ID, category="student_support",
        name="Student Counselling and Mentoring Services",
        details={"services": "Professional counselling, student guidance, mentoring, and student welfare support."},
        source_url="https://ait.regression.test/student-support/counselling",
        source_type="ADMIN_VERIFIED", authority="Ahmedabad Institute of Technology Verified Database",
        is_verified=True, content_hash="counselling-support",
    )
    env["db"].add(entity)
    env["db"].commit()
    response = env["client"].post(
        "/api/v1/chat/stream", headers=env["headers"],
        json={"conversation_id": env["conversation"].id, "message": EXACT_SUPPORT_QUESTION},
    )
    assert response.status_code == 200
    assert "Professional counselling" in response.text
    assert '"source_type": "ADMIN_VERIFIED"' in response.text
    assert '"source_type": "NO_VERIFIED_INFORMATION"' not in response.text

def test_ait_end_to_end_is_explicitly_scoped_and_grounded(ait_regression):
    env = ait_regression
    response = env["client"].post(
        "/api/v1/chat/stream", headers=env["headers"],
        json={"conversation_id": env["conversation"].id,
              "message": "What are the library timing hours?"},
    )
    assert response.status_code == 200
    assert "message_complete" in response.text
    assert "Ahmedabad Institute of Technology" in response.text, response.text
    assert "07:17" in response.text
    assert "07:19 PM" in response.text
    assert "R.C. Technical Institute" not in response.text
    assert "11:11" not in response.text
    assert "Test Engineering College" not in response.text
    assert "13:13" not in response.text
    assert "provider is currently unavailable" not in response.text.lower()
    assert "general-ai" not in response.text.lower()

    from backend.app.models.conversation import Message
    assistant = env["db"].query(Message).filter_by(
        conversation_id=env["conversation"].id, sender="assistant").one()
    assert AIT_FACT in assistant.content
    assert assistant.provenance.get("source_type") == "ADMIN_VERIFIED"
    assert assistant.provenance.get("source_url") == "https://ait.regression.test/quantum-lab"
    assert assistant.provenance.get("authority") == "Ahmedabad Institute of Technology Verified Database"
    assert assistant.provenance.get("verified") is True
    assert assistant.grounding_status == "verified"
    assert env["conversation"].college_id == AIT_ID
