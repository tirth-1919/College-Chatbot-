"Regressions for generic temporal evidence retrieval and final chat provenance."""
from datetime import datetime, timezone
import hashlib
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.app.ai.router import ai_router
from backend.app.chat.orchestrator import (
    ADMIN_VERIFIED,
    NO_VERIFIED_INFORMATION,
    OFFICIAL_WEBSITE,
    ChatOrchestrator,
)
from backend.app.core.database import Base, get_db
from backend.app.core.security import create_access_token
from backend.app.intelligence.entities import EntityExtractor
from backend.app.intelligence.intent import intent_classifier
from backend.app.main import app
from backend.app.models.college import College
from backend.app.models.conversation import Conversation, Message
from backend.app.models.knowledge import WebsiteSnapshot
from backend.app.models.user import User
from backend.app.knowledge.database import KnowledgeDatabase
AIT_ID = "latest-events-ait"
RCTI_ID = "latest-events-rcti"
USER_ID = "latest-events-user"

@pytest.fixture
def event_env(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, autoflush=False)()
    now = datetime.now(timezone.utc)
    ait = College(
        id=AIT_ID, name="Ahmedabad Institute of Technology", code="AIT",
        slug="latest-events-ait", status="ACTIVE", registration_status="APPROVED",
        official_website="https://ait.latest.test",
    )
    rcti = College(
        id=RCTI_ID, name="R.C. Technical Institute", code="RCTI",
        slug="latest-events-rcti", status="ACTIVE", registration_status="APPROVED",
        official_website="https://rcti.latest.test",
    )
    user = User(id=USER_ID, email="latest-events@example.test", full_name="Events User",
                role="STUDENT", is_active=True, hashed_password="x")
    conversation = Conversation(id="latest-events-conversation", user_id=USER_ID,
                                college_id=AIT_ID, conversation_type="NORMAL", title="events")
    db.add_all([ait, rcti, user, conversation])
    db.commit()
    calls = []

    async def fake_provider(**kwargs):
        calls.append(kwargs)
        return "An unverified generic answer."

    monkeypatch.setattr(ai_router, "generate_response", fake_provider)
    app.dependency_overrides[get_db] = lambda: db
    try:
        yield {"db": db, "ait": ait, "rcti": rcti, "calls": calls, "engine": engine}
    finally:
        app.dependency_overrides.pop(get_db, None)
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def _snapshot(db, *, id_, college_id=AIT_ID, title="Events", path="events/page",
              body="Students took part in the annual technical celebration.",
              crawled=None, active=True):
    row = WebsiteSnapshot(
        id=id_, college_id=college_id, url=f"https://ait.latest.test/{path}",
        title=title, text_content=body,
        content_hash=hashlib.sha256(id_.encode()).hexdigest(), status_code=200,
        last_crawled_at=crawled or datetime(2026, 1, 1, tzinfo=timezone.utc), active=active,
    )
    db.add(row)
    return row

def _spec(question="latest events in AIT", college_id=AIT_ID):
    intent = intent_classifier.classify_intent(question)
    spec = EntityExtractor.extract_query_understanding(
        question, college_id=college_id, intent=intent["intent"],
    )
    spec.college_name = "Ahmedabad Institute of Technology"
    spec.confidence = intent.get("confidence")
    spec.route = "institutional"
    return spec
@pytest.mark.parametrize("question", [
    "latest events in AIT",
    "recent events at AIT",
    "lateset evnt in ait",
    "latest news/events in AIT",
])
def test_latest_event_query_builds_canonical_institutional_spec(question):
    spec = _spec(question)
    assert spec.college_id == AIT_ID
    assert spec.college_name == "Ahmedabad Institute of Technology"
    assert spec.topic == spec.category == "EVENTS"
    assert spec.temporal_qualifier == "latest"
    assert spec.intent in ("EVENT", "EVENTS")
    assert spec.route == "institutional"
    assert spec.confidence and spec.confidence > 0
@pytest.mark.parametrize("question", [
    "upcoming events at AIT",
    "AIT events",
    "events at Ahmedabad Institute of Technology",
    "recent events in Ahmedabad Institute of Technology",
])
def test_event_query_variants_share_topic_and_temporal_semantics(question):
    spec = _spec(question)
    assert spec.topic == "EVENTS"
    assert spec.temporal_qualifier == ("upcoming" if "upcoming" in question else ("latest" if "recent" in question else None))
    assert spec.intent in ("EVENT", "EVENTS")

def test_event_snapshot_relevance_uses_body_not_title_and_not_first_row(event_env):
    db = event_env["db"]
    _snapshot(db, id_="irrelevant-first", title="Events", path="events/unrelated",
              body="Library opening information, quiet reading rooms, borrowing and books." * 3)
    about = _snapshot(db, id_="relevant-about", title="About", path="about",
                      body="During 2025 students attended a campus seminar, technical workshop, and student festival." * 2)
    db.commit()
    results = KnowledgeDatabase.query_website_snapshots(
        db, "latest events in AIT", college_id=AIT_ID, query_spec=_spec(),
    )
    assert [item["id"] for item in results] == [about.id]


def test_latest_relevant_snapshot_outranks_older_and_only_relevant_old_still_works(event_env):
    db = event_env["db"]
    old = _snapshot(db, id_="older-relevant", title="Campus Activities", path="activities/older",
                    body="Students joined the campus seminar and technical workshop in 2024, with presentations and project demonstrations for the college community.",
                    crawled=datetime(2026, 1, 1, tzinfo=timezone.utc))
    new = _snapshot(db, id_="newer-relevant", title="Latest News", path="news/newer",
                    body="Students attended a campus seminar and technical workshop in 2025, featuring presentations and project demonstrations for the college community.",
                    crawled=datetime(2026, 2, 1, tzinfo=timezone.utc))
    db.commit()
    rows = KnowledgeDatabase.query_website_snapshots(
        db, "latest events in AIT", college_id=AIT_ID, query_spec=_spec(),
    )
    assert [row["id"] for row in rows] == [new.id, old.id]
    assert "2025" in rows[0]["content"]
    assert "2024" in rows[1]["content"]

    db.delete(new)
    db.commit()
    rows = KnowledgeDatabase.query_website_snapshots(
        db, "latest events in AIT", college_id=AIT_ID, query_spec=_spec(),
    )
    assert len(rows) == 1 and rows[0]["id"] == old.id

def test_event_retrieval_rejects_inactive_and_other_tenant_snapshots(event_env):
    db = event_env["db"]
    _snapshot(db, id_="rcti-event", college_id=RCTI_ID, path="events/rcti",
              body="RCTI students participated in a campus seminar and festival." * 2)
    _snapshot(db, id_="inactive-ait-event", active=False, path="events/inactive",
              body="AIT students participated in a campus seminar and festival." * 2)
    _snapshot(db, id_="active-ait-unrelated", title="Library", path="library",
              body="Books and reading rooms support students at the campus." * 2)
    db.commit()
    rows = KnowledgeDatabase.query_website_snapshots(
        db, "latest events in AIT", college_id=AIT_ID, query_spec=_spec(),
    )
    assert rows == []


def test_direct_ranking_keeps_relevance_ahead_of_recency_and_source_priority():
    spec = _spec()
    unrelated_official = {
        "college_id": AIT_ID, "source_type": "website_snapshot", "active": True,
        "status": "ACTIVE", "verified": True, "title": "Library",
        "details": "Books and reading rooms are open to students.",
        "last_crawled_at": datetime(2026, 3, 1, tzinfo=timezone.utc),
    }
    older_relevant_admin = {
        "college_id": AIT_ID, "source_type": ADMIN_VERIFIED, "active": True,
        "status": "ACTIVE", "verified": True, "title": "Campus Seminar",
        "category": "EVENTS", "topic": "EVENTS",
        "details": "Students attended a campus seminar and workshop.",
        "last_crawled_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
    }
    newer_relevant_official = {
        "college_id": AIT_ID, "source_type": "website_snapshot", "active": True,
        "status": "ACTIVE", "verified": True, "title": "Campus Seminar",
        "category": "EVENTS", "topic": "EVENTS",
        "details": "Students attended a campus seminar and workshop.",
        "last_crawled_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }
    ranked = []
    from backend.app.chat.response_builder import evidence_relevance
    from backend.app.chat.orchestrator import SOURCE_PRIORITY
    for item in (unrelated_official, older_relevant_admin, newer_relevant_official):
        score = evidence_relevance(item, spec)
        if score is not None:
            ranked.append((item, score))
    ranked.sort(key=lambda row: (row[1], row[0]["last_crawled_at"], SOURCE_PRIORITY.get(row[0]["source_type"], 0)), reverse=True)
    assert ranked[0][0] is newer_relevant_official
    assert all(item is not unrelated_official for item, _ in ranked)

def test_event_source_label_requires_content_not_title_or_url():
    spec = _spec()
    from backend.app.chat.response_builder import evidence_relevance
    for title, url in (("Events", "/events"), ("About", "/about")):
        unrelated = {
            "college_id": AIT_ID, "source_type": "website_snapshot", "active": True,
            "status": "ACTIVE", "title": title, "source_url": f"https://ait.test{url}",
            "details": "Library opening hours, books and quiet reading rooms.",
        }
        assert evidence_relevance(unrelated, spec) is None
@pytest.mark.asyncio
async def test_live_chat_sse_selects_official_event_and_does_not_call_gemini(event_env, monkeypatch):
    db = event_env["db"]
    _snapshot(db, id_="irrelevant-first", title="Events", path="events/unrelated",
              body="Library opening information, quiet reading rooms, borrowing and books." * 3)
    official = _snapshot(db, id_="relevant-about", title="About", path="about",
                         body="During 2025 AIT students attended a campus seminar and technical workshop." * 2)
    db.commit()

    async def no_live_page(*args, **kwargs):
        return None
    monkeypatch.setattr("backend.app.knowledge.crawler.AitWebsiteCrawler.fetch_relevant_page", no_live_page)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/chat/stream",
            headers={"Authorization": f"Bearer {create_access_token({'sub': USER_ID})}"},
            json={"conversation_id": "latest-events-conversation", "message": "latest events in AIT"},
        )
    assert response.status_code == 200
    assert "seminar" in response.text.lower() and "workshop" in response.text.lower()
    assert "quiet reading rooms" not in response.text
    assert '"source_type": "OFFICIAL_WEBSITE"' in response.text
    assert event_env["calls"] == []
    assistant = db.query(Message).filter_by(
        conversation_id="latest-events-conversation", sender="assistant",
    ).order_by(Message.created_at.desc()).first()
    assert assistant.provenance["source_type"] == OFFICIAL_WEBSITE
    assert assistant.provenance["verified"] is True
    assert assistant.provenance["source_url"] == official.url
    citation_items = [item for block in assistant.blocks if block.get("type") == "citation" for item in block.get("items", [])]
    assert any(item.get("source_type") == OFFICIAL_WEBSITE and item.get("source_url") == official.url for item in citation_items)
@pytest.mark.asyncio
async def test_live_chat_no_relevant_event_returns_no_verified_information(event_env, monkeypatch):
    db = event_env["db"]
    _snapshot(db, id_="irrelevant-events-title", title="Events", path="events/unrelated",
              body="Library opening information, quiet reading rooms, borrowing and books." * 3)
    _snapshot(db, id_="rcti-event", college_id=RCTI_ID, path="events/rcti",
              body="RCTI students participated in a campus seminar and festival." * 2)
    db.commit()

    async def no_live_page(*args, **kwargs):
        return None
    monkeypatch.setattr("backend.app.knowledge.crawler.AitWebsiteCrawler.fetch_relevant_page", no_live_page)
    result = await ChatOrchestrator.process_chat(
        db, "latest-events-conversation", "latest events in AIT", user_id=USER_ID, college_id=AIT_ID,
    )
    expected = "The latest information about events at Ahmedabad Institute of Technology could not be verified from the available official website or admin-verified records."
    assert result["text_content"] == expected
    assert result["source_type"] == NO_VERIFIED_INFORMATION
    assert result["verified"] is False
    assert "GEMINI_UNVERIFIED" != result["source_type"]
    assert event_env["calls"] == []
    assistant = db.query(Message).filter_by(
        conversation_id="latest-events-conversation", sender="assistant",
    ).order_by(Message.created_at.desc()).first()
    assert assistant.provenance["source_type"] == NO_VERIFIED_INFORMATION
    assert assistant.provenance["verified"] is False
    assert result["blocks"]
    provenance = next(block for block in result["blocks"] if block.get("type") == "provenance")
    assert provenance["source_type"] == NO_VERIFIED_INFORMATION
    assert provenance["verified"] is False
