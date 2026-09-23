"""
College Context & RCTI tenant tests (Part A / Part G / Part H).

Covers:
  §11 aliases   §12 typo tolerance / no silent ambiguity
  §13 normalization  §6/§27 conversation retention  §57-§62 user flows
  §52/§53/§55 tenant isolation (DB + RAG + conversations)
  §23/§61 safe-switch (default never silently changed)
"""
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base, get_db
from backend.app.core.security import create_access_token, get_password_hash
from backend.app.main import app


@pytest.fixture(scope="module")
def db_session():
    from sqlalchemy.pool import StaticPool
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # one shared connection: async endpoints see the same DB
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
    ait = College(id="ait-1", name="Ahmedabad Institute of Technology",
                  code="AIT", slug="ait", status="ACTIVE", created_at=now)
    rcti = College(id="rcti-1", name="R.C. Technical Institute",
                   code="RCTI", slug="rcti", status="ACTIVE",
                   official_website="https://www.rcti.ac.in/",
                   city="Ahmedabad", state="Gujarat", created_at=now)
    db_session.add_all([ait, rcti])

    aliases = ["RC Technical", "RCT", "R.C. Technical", "R C Technical",
               "RC Technical Institute", "R.C. Technical Institute", "rcti"]
    from backend.app.chat.college_context import normalize
    for a in aliases:
        db_session.add(CollegeAlias(college_id=rcti.id, alias=a, normalized_alias=normalize(a)))

    # Tenant-scoped knowledge facts (§53)
    db_session.add(AitEntity(
        id="e-ait-fact", college_id=ait.id, category="demo", name="AIT Only Fact",
        code="AITFACT", details={"value": "AIT unique test fact alpha"},
        source_url="https://www.aitindia.in/x", content_hash="h1", is_verified=True))
    db_session.add(AitEntity(
        id="e-rcti-fact", college_id=rcti.id, category="demo", name="Demo Counselling Hours",
        code="DEMO-CH", details={"value": "Monday to Friday, 4:00 PM - 5:00 PM"},
        source_url="DEMO://rcti/synthetic", content_hash="h2", is_verified=True,
        authority="DEMO — Non-official development test data"))

    user = User(id="user-u1", email="u1@test.com", full_name="Test User", role="STUDENT",
                is_active=True, hashed_password="x")  # no default_college_id
    db_session.add(user)
    db_session.commit()
    return {"db": db_session, "ait": ait, "rcti": rcti, "user": user}


def _headers(user):
    return {"Authorization": f"Bearer {create_access_token({'sub': user.id})}"}


# ──────────────── §72: Resolver unit tests ────────────

def test_resolve_exact_and_normalized(env):
    from backend.app.chat.college_context import college_context_manager
    db = env["db"]
    for q in ["RC Technical", "rc technical", "RC TECHNICAL", "R.C. Technical",
              "R C Technical", "R.C. Technical Institute", "RCT", "rcti"]:
        res = college_context_manager.resolve(db, q)
        assert res["status"] == "RESOLVED", f"{q!r} failed: {res}"
        assert res["college_id"] == env["rcti"].id


def test_resolve_typo(env):
    from backend.app.chat.college_context import college_context_manager
    res = college_context_manager.resolve(env["db"], "RC Techanical")
    assert res["status"] == "RESOLVED"
    assert res["college_id"] == env["rcti"].id


def test_resolve_unknown_never_guesses(env):
    from backend.app.chat.college_context import college_context_manager
    res = college_context_manager.resolve(env["db"], "Zzzqwx Nonexistent University")
    assert res["status"] == "NOT_FOUND"
    assert res["college_id"] is None


# ──────────────── §56-§60: User flow through chat API ────────────

def test_first_message_asks_college_then_resolves(client, env):
    conv_id = f"conv-{uuid.uuid4().hex[:8]}"

    # First message from a user with NO default college: onboarding question
    res = client.post("/api/v1/chat/stream", headers=_headers(env["user"]),
                      json={"conversation_id": conv_id, "message": "hello there"})
    assert res.status_code == 200
    from backend.app.models.conversation import Conversation, Message
    db = env["db"]
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    msgs = db.query(Message).filter(Message.conversation_id == conv_id).all()
    assistant = [m for m in msgs if m.sender == "assistant"]
    assert any("Which college information do you want" in m.content for m in assistant)
    assert conv.college_id is None

    # User types the college name naturally -> resolved + persisted (§57).
    # §4/§5: the college belongs to THIS conversation only — the user's global
    # default is never auto-modified by in-chat selection.
    res = client.post("/api/v1/chat/stream", headers=_headers(env["user"]),
                      json={"conversation_id": conv_id, "message": "R.C. Technical Institute"})
    assert res.status_code == 200
    db.refresh(conv)
    db.refresh(env["user"])
    assert conv.college_id == env["rcti"].id
    assert env["user"].default_college_id is None
    msgs = db.query(Message).filter(Message.conversation_id == conv_id).all()
    assert any("Connected to R.C. Technical Institute" in m.content
               for m in msgs if m.sender == "assistant")


def test_new_chat_starts_without_college_and_forget(client, env):
    db = env["db"]

    # §12: a NEW chat must NOT inherit any college — it starts NULL and the
    # college question is asked again inside the new conversation.
    res = client.post("/api/v1/conversations", headers=_headers(env["user"]), json={})
    assert res.status_code == 201
    assert res.json()["college_id"] is None

    # Chat stream with a NEW conversation id also starts NULL (§12)
    conv_id = f"conv-{uuid.uuid4().hex[:8]}"
    res = client.post("/api/v1/chat/stream", headers=_headers(env["user"]),
                      json={"conversation_id": conv_id, "message": "hello"})
    assert res.status_code == 200
    from backend.app.models.conversation import Conversation
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    assert conv.college_id is None

    # The deliberate default-change action still exists for users who want it
    res = client.post("/api/v1/college-context/default/change", headers=_headers(env["user"]),
                      json={"college_name": "RC Technical"})
    assert res.status_code == 200
    db.refresh(env["user"])
    assert env["user"].default_college_id == env["rcti"].id

    # §12: even with a saved default, a brand-new conversation stays NULL
    res = client.post("/api/v1/conversations", headers=_headers(env["user"]), json={})
    assert res.status_code == 201
    assert res.json()["college_id"] is None

    # Forget default (§26) -> saved preference cleared
    res = client.post("/api/v1/college-context/default/forget", headers=_headers(env["user"]))
    assert res.status_code == 200
    db.refresh(env["user"])
    assert env["user"].default_college_id is None


def test_safe_switch_does_not_change_default(client, env):
    db = env["db"]
    db.refresh(env["user"])
    # §12/§4: in-chat selection never writes the global default.
    assert env["user"].default_college_id is None

    conv_id = f"conv-{uuid.uuid4().hex[:8]}"
    # §12: establish the RCTI context explicitly inside THIS conversation.
    client.post("/api/v1/chat/stream", headers=_headers(env["user"]),
                json={"conversation_id": conv_id, "message": "hello"})
    client.post("/api/v1/chat/stream", headers=_headers(env["user"]),
                json={"conversation_id": conv_id, "message": "R.C. Technical Institute"})
    # Ask about AIT from an RCTI context (§61): mention detected, safe-switch prompt
    res = client.post("/api/v1/chat/stream", headers=_headers(env["user"]),
                      json={"conversation_id": conv_id, "message": "What is the BCA fee at AIT?"})
    assert res.status_code == 200
    from backend.app.models.conversation import Conversation, Message
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    db.refresh(conv)
    db.refresh(env["user"])
    assert conv.college_id == env["rcti"].id, "must not silently switch"
    assert env["user"].default_college_id is None, "default never changes silently"
    msgs = db.query(Message).filter(Message.conversation_id == conv_id).all()
    last_assistant = [m for m in msgs if m.sender == "assistant"][-1]
    assert "switch this conversation to Ahmedabad Institute of Technology" in last_assistant.content

    # Deliberate switch: conversation changes, default stays (§23)
    res = client.post("/api/v1/college-context/switch", headers=_headers(env["user"]),
                      json={"conversation_id": conv_id, "college_name": "AIT"})
    assert res.status_code == 200
    db.refresh(conv)
    db.refresh(env["user"])
    assert conv.college_id == env["ait"].id
    assert env["user"].default_college_id is None


# ──────────────── §52/§53: Retrieval isolation ────────────

def test_db_retrieval_tenant_isolated(env):
    from backend.app.knowledge.database import knowledge_db
    db = env["db"]
    rcti_hits = knowledge_db.query_entities(db, "Demo Counselling Hours", college_id=env["rcti"].id)
    assert any(h["name"] == "Demo Counselling Hours" for h in rcti_hits)
    ait_hits = knowledge_db.query_entities(db, "Demo Counselling Hours", college_id=env["ait"].id)
    assert rcti_hits and not any(h["name"] == "Demo Counselling Hours" for h in ait_hits)


def test_rag_tenant_isolated(env):
    from backend.app.knowledge.rag import rag_engine
    from backend.app.models.document import Document, DocumentChunk, VISIBILITY_ADMIN_VERIFIED
    db = env["db"]
    for cid, fact in [(env["ait"].id, "AIT RAG marker zeta"),
                      (env["rcti"].id, "RCTI RAG marker omega")]:
        d = Document(title=f"fact-{cid}", doc_type="txt", college_id=cid,
                     content_hash=uuid.uuid4().hex, visibility=VISIBILITY_ADMIN_VERIFIED,
                     source_url="test://x")
        db.add(d)
        db.flush()
        db.add(DocumentChunk(document_id=d.id, college_id=cid, chunk_index=0, content=fact))
    db.commit()
    ait_res = rag_engine.search(db, "AIT RAG marker zeta", college_id=env["ait"].id)
    rcti_res = rag_engine.search(db, "RCTI RAG marker omega", college_id=env["rcti"].id)
    assert ait_res and all(r["college_id"] == env["ait"].id for r in ait_res)
    assert rcti_res and all(r["college_id"] == env["rcti"].id for r in rcti_res)
    assert not any("omega" in r["content"] for r in ait_res)


def test_demo_provenance_not_official(env):
    """§44/§79: DEMO records carry non-official authority."""
    from backend.app.knowledge.database import knowledge_db
    db = env["db"]
    hits = knowledge_db.query_entities(db, "Demo Counselling Hours", college_id=env["rcti"].id)
    demo_hit = next(h for h in hits if h["name"] == "Demo Counselling Hours")
    assert "DEMO" in (demo_hit.get("authority") or "").upper()
