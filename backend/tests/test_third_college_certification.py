"Deterministic third-tenant certification without touching AIT/RCTI data."""
import hashlib
import uuid
from datetime import datetime, timezone
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.app.api.v1.chat import router as chat_router
from backend.app.core.database import Base, get_db
from backend.app.core.security import create_access_token, get_password_hash
from backend.app.knowledge.database import knowledge_db
from backend.app.knowledge.rag import rag_engine
from backend.app.models.college import College
from backend.app.models.conversation import Conversation
from backend.app.models.image import AitImage
from backend.app.models.knowledge import AitEntity, AitKnowledgeVersion, WebsiteSnapshot
from backend.app.models.user import User
from backend.app.models.document import VISIBILITY_ADMIN_VERIFIED
THIRD_ID = "3f6b7c8d-9012-4abc-def3-456789012345"
THIRD_ADMIN_ID = "3f6b7c8d-9012-4abc-def3-456789012346"
THIRD_STUDENT_ID = "3f6b7c8d-9012-4abc-def3-456789012347"
THIRD_CODE = "TEST-ENGINEERING"
THIRD_FACT = "Test Engineering College library timing is 8:00 AM to 6:00 PM."


def _hash(value):
    return hashlib.sha256(value.encode()).hexdigest()

@pytest.fixture
def third_tenant():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False)
    db = factory()
    third = College(
        id=THIRD_ID, name="Test Engineering College", code=THIRD_CODE,
        slug="test-engineering-college", official_website=None,
        status="ACTIVE", registration_status="APPROVED",
    )
    ait = College(id="cert-ait", name="Certification AIT", code="CERT-AIT",
                  slug="cert-ait", status="ACTIVE", registration_status="APPROVED")
    rcti = College(id="cert-rcti", name="Certification RCTI", code="CERT-RCTI",
                   slug="cert-rcti", status="ACTIVE", registration_status="APPROVED")
    admin = User(id=THIRD_ADMIN_ID, email="third-admin@cert.test", full_name="Third Admin",
                 role="COLLEGE_ADMIN", college_id=THIRD_ID, hashed_password=get_password_hash("TestPass1!"),
                 is_active=True, is_verified=True)
    student = User(id=THIRD_STUDENT_ID, email="third-student@cert.test", full_name="Third Student",
                   role="STUDENT", college_id=THIRD_ID, hashed_password=get_password_hash("TestPass1!"),
                   is_active=True, is_verified=True)
    db.add_all([third, ait, rcti, admin, student])
    db.flush()
    entity = AitEntity(
        id="3f6b7c8d-9012-4abc-def3-456789012348", college_id=THIRD_ID,
        category="facility", name="Test Engineering College Library Timing",
        details={"library_timing": "8:00 AM to 6:00 PM", "fact": THIRD_FACT},
        source_url="https://test-engineering.example.test/library",
        source_type="ADMIN_VERIFIED", is_official=False, authority="Test Engineering College Verified Database",
        is_verified=True, content_hash=_hash(THIRD_FACT),
    )
    version = AitKnowledgeVersion(
        id="3f6b7c8d-9012-4abc-def3-456789012349", college_id=THIRD_ID,
        entity_id=entity.id, version=1, payload={"fact": THIRD_FACT}, status="PUBLISHED",
        content_hash=_hash(THIRD_FACT),
    )
    snapshot = WebsiteSnapshot(
        id="3f6b7c8d-9012-4abc-def3-456789012350", college_id=THIRD_ID,
        url="https://test-engineering.example.test/library", title="Library",
        content_hash=_hash(THIRD_FACT), text_content=THIRD_FACT, status_code=200,
    )
    db.add_all([entity, version, snapshot])
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
    third_token = create_access_token({"sub": student.id, "role": "STUDENT", "college_id": THIRD_ID})
    third_headers = {"Authorization": f"Bearer {third_token}"}
    try:
        yield {
            "db": db, "client": TestClient(app), "third": third, "ait": ait, "rcti": rcti,
            "admin": admin, "student": student, "headers": third_headers,
            "third_id": THIRD_ID, "fact": THIRD_FACT,
        }
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def _normal(db, user_id, college_id, key):
    conversation = Conversation(id=key, user_id=user_id, college_id=college_id,
                                conversation_type="NORMAL", title="Certification")
    db.add(conversation)
    db.commit()
    return conversation

def test_third_college_fixture_and_conversations_are_persisted(third_tenant):
    db = third_tenant["db"]
    third = db.get(College, THIRD_ID)
    assert third.name == "Test Engineering College"
    assert third.status == "ACTIVE"
    assert third.registration_status == "APPROVED"
    entity = db.query(AitEntity).filter(AitEntity.college_id == THIRD_ID).one()
    assert entity.is_verified is True
    assert entity.details["library_timing"] == "8:00 AM to 6:00 PM"
    assert db.query(WebsiteSnapshot).filter(WebsiteSnapshot.college_id == THIRD_ID).count() == 1
    assert db.query(AitKnowledgeVersion).filter(AitKnowledgeVersion.college_id == THIRD_ID).count() == 1
    conversation = _normal(db, THIRD_STUDENT_ID, THIRD_ID, "third-normal-conversation")
    assert conversation.college_id == THIRD_ID
    assert conversation.conversation_type == "NORMAL"
    assert conversation.college_id is not None

def test_third_database_and_document_isolation(third_tenant):
    db = third_tenant["db"]
    third_id = third_tenant["third_id"]
    own = knowledge_db.query_entities(db, "library timing", college_id=third_id)
    assert any("8:00 AM to 6:00 PM" in str(row["details"]) for row in own)
    assert knowledge_db.query_entities(db, "library timing", college_id=third_tenant["ait"].id) == []
    assert knowledge_db.query_entities(db, "library timing", college_id=third_tenant["rcti"].id) == []

    document = rag_engine.index_document(
        db, "Test Engineering College Library Document", THIRD_FACT,
        college_id=third_id, visibility=VISIBILITY_ADMIN_VERIFIED,
    )
    assert document.college_id == third_id
    assert rag_engine.search(db, "library timing", college_id=third_id)[0]["college_id"] == third_id
    assert rag_engine.search(db, "library timing", college_id=third_tenant["ait"].id) == []
    assert rag_engine.search(db, "library timing", college_id=third_tenant["rcti"].id) == []


def test_third_image_is_tenant_owned(third_tenant):
    db = third_tenant["db"]
    image = AitImage(
        id="3f6b7c8d-9012-4abc-def3-456789012351", college_id=THIRD_ID,
        title="Third College Library", category="library",
        image_url="https://test-engineering.example.test/library.png",
        source_url="https://test-engineering.example.test/library",
        source_type="OFFICIAL_WEBSITE", source_domain="test-engineering.example.test",
        content_hash=_hash("third-library-image"), verified=True,
    )
    db.add(image)
    db.commit()
    assert db.query(AitImage).filter(AitImage.college_id == THIRD_ID).one().college_id == THIRD_ID
    assert db.query(AitImage).filter(AitImage.college_id == third_tenant["ait"].id).count() == 0
    assert db.query(AitImage).filter(AitImage.college_id == third_tenant["rcti"].id).count() == 0

def test_real_sse_third_college_returns_verified_tenant_fact(third_tenant):
    db = third_tenant["db"]
    conversation = _normal(db, THIRD_STUDENT_ID, THIRD_ID, "third-sse-conversation")
    response = third_tenant["client"].post(
        "/api/v1/chat/stream", headers=third_tenant["headers"],
        json={"conversation_id": conversation.id, "message": "What are the library timing hours?"},
    )
    assert response.status_code == 200
    assert "message_complete" in response.text
    db.refresh(conversation)
    assistant = db.query(__import__("backend.app.models.conversation", fromlist=["Message"]).Message).filter_by(
        conversation_id=conversation.id, sender="assistant"
    ).one()
    assert "8:00 AM to 6:00 PM" in assistant.content
    assert assistant.provenance.get("source_type") == "ADMIN_VERIFIED"
    assert assistant.provenance.get("verified") is True
    assert THIRD_ID == conversation.college_id

def test_third_sse_cannot_retrieve_rcti_fact(third_tenant):
    db = third_tenant["db"]
    conversation = _normal(db, THIRD_STUDENT_ID, THIRD_ID, "third-cross-tenant-sse")
    response = third_tenant["client"].post(
        "/api/v1/chat/stream", headers=third_tenant["headers"],
        json={"conversation_id": conversation.id, "message": "Tell me the RCTI information."},
    )
    assert response.status_code == 200
    assert "message_complete" in response.text
    assert "Facilities – R. C. Technical Institute" not in response.text
    assert "rcti.ac.in" not in response.text

def test_same_question_is_scoped_by_college(third_tenant):
    db = third_tenant["db"]
    ait = AitEntity(
        id="3f6b7c8d-9012-4abc-def3-456789012352", college_id=third_tenant["ait"].id,
        category="facility", name="AIT Library Timing", details={"library_timing": "9:00 AM to 5:00 PM"},
        source_url="https://cert-ait.test/library", source_type="ADMIN_VERIFIED",
        is_verified=True, content_hash=_hash("ait-library-timing"),
    )
    db.add(ait)
    db.commit()
    ait_answer = knowledge_db.query_entities(db, "library timing", college_id=third_tenant["ait"].id)
    third_answer = knowledge_db.query_entities(db, "library timing", college_id=THIRD_ID)
    assert "9:00 AM to 5:00 PM" in str(ait_answer)
    assert "8:00 AM to 6:00 PM" in str(third_answer)
    assert "8:00 AM to 6:00 PM" not in str(ait_answer)
    assert "9:00 AM to 5:00 PM" not in str(third_answer)
