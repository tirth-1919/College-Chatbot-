"""
Universal in-chat college selection flow tests (§34).

Covers the generic multi-college conversation-context system:
  T1 new chat NULL + question   T2/T3 AIT/RCTI selection   T4 alias
  T5 invalid never guesses      T6 no re-asking             T7 new chat resets
  T8 existing chat restores     T13 future college generic  T14 ambiguous
  T15 frontend tampering ignored
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
from backend.app.chat.college_context import normalize


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
    from backend.app.models.user import User

    now = datetime.now(timezone.utc)
    ait = College(id="ait-x", name="Ahmedabad Institute of Technology",
                  code="AIT", slug="ait", status="ACTIVE", created_at=now)
    rcti = College(id="rcti-x", name="R.C. Technical Institute",
                   code="RCTI", slug="rcti", status="ACTIVE",
                   official_website="https://www.rcti.ac.in/",
                   city="Ahmedabad", state="Gujarat", created_at=now)
    db_session.add_all([ait, rcti])
    for a in ["RC Technical", "RCT", "R.C. Technical", "R C Technical",
              "RC Technical Institute", "R.C. Technical Institute", "rcti",
              "RC Technical"]:
        db_session.add(CollegeAlias(college_id=rcti.id, alias=a,
                                    normalized_alias=normalize(a)))
    user = User(id="user-sel", email="sel@test.com", full_name="Sel User",
                role="STUDENT", is_active=True, hashed_password="x")
    db_session.add(user)
    db_session.commit()
    return {"db": db_session, "ait": ait, "rcti": rcti, "user": user}


def _headers(user):
    return {"Authorization": f"Bearer {create_access_token({'sub': user.id})}"}


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Tests share one client IP; the 30/min chat limiter would otherwise make
    later tests order-dependent. Clear its state before each test."""
    from backend.app.security.rate_limiter import rate_limiter
    rate_limiter._history.clear()
    yield
    rate_limiter._history.clear()


def _last_assistant(db, conv_id):
    from backend.app.models.conversation import Message
    msgs = [m for m in db.query(Message).filter(
        Message.conversation_id == conv_id, Message.sender == "assistant").all()]
    return msgs[-1] if msgs else None


def _new_conv(client, env):
    """Create a fresh conversation via the API and return its id."""
    res = client.post("/api/v1/conversations", headers=_headers(env["user"]), json={})
    assert res.status_code == 201
    return res.json()["id"]


# ── T1: new chat starts NULL and asks ────────────────────────────────────────

def test_t1_new_chat_null_and_asks(client, env):
    db = env["db"]
    conv_id = _new_conv(client, env)
    res = client.post("/api/v1/chat/stream", headers=_headers(env["user"]),
                      json={"conversation_id": conv_id, "message": "hello there"})
    assert res.status_code == 200
    reply = _last_assistant(db, conv_id)
    assert "Which college information do you want" in reply.content
    from backend.app.models.conversation import Conversation
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    assert conv.college_id is None


# ── T2/T3: select AIT / RCTI ────────────────────────────────────────────────

def test_t2_select_ait(client, env):
    db = env["db"]
    conv_id = _new_conv(client, env)
    client.post("/api/v1/chat/stream", headers=_headers(env["user"]),
                json={"conversation_id": conv_id, "message": "hi"})
    res = client.post("/api/v1/chat/stream", headers=_headers(env["user"]),
                      json={"conversation_id": conv_id,
                            "message": "Ahmedabad Institute of Technology"})
    assert res.status_code == 200
    from backend.app.models.conversation import Conversation
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    db.refresh(conv)
    assert conv.college_id == env["ait"].id
    assert "Connected to Ahmedabad Institute of Technology" in _last_assistant(db, conv_id).content


def test_t3_select_rcti(client, env):
    db = env["db"]
    conv_id = _new_conv(client, env)
    client.post("/api/v1/chat/stream", headers=_headers(env["user"]),
                json={"conversation_id": conv_id, "message": "hi"})
    client.post("/api/v1/chat/stream", headers=_headers(env["user"]),
                json={"conversation_id": conv_id, "message": "R.C. Technical Institute"})
    from backend.app.models.conversation import Conversation
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    db.refresh(conv)
    assert conv.college_id == env["rcti"].id


def test_t4_alias_resolves_same_college(client, env):
    db = env["db"]
    from backend.app.models.conversation import Conversation
    for alias in ["RC Technical", "R C Technical Institute", "RCTI", "rcti"]:
        conv_id = _new_conv(client, env)
        client.post("/api/v1/chat/stream", headers=_headers(env["user"]),
                    json={"conversation_id": conv_id, "message": "hi"})
        client.post("/api/v1/chat/stream", headers=_headers(env["user"]),
                    json={"conversation_id": conv_id, "message": alias})
        conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
        db.refresh(conv)
        assert conv.college_id == env["rcti"].id, alias


# ── T5: invalid college never guesses ───────────────────────────────────────

def test_t5_invalid_college_not_guessed(client, env):
    db = env["db"]
    conv_id = _new_conv(client, env)
    client.post("/api/v1/chat/stream", headers=_headers(env["user"]),
                json={"conversation_id": conv_id, "message": "hi"})
    res = client.post("/api/v1/chat/stream", headers=_headers(env["user"]),
                      json={"conversation_id": conv_id, "message": "XYZ Unknown College"})
    assert res.status_code == 200
    from backend.app.models.conversation import Conversation
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    db.refresh(conv)
    assert conv.college_id is None
    assert "couldn’t find that college" in _last_assistant(db, conv_id).content


# ── T6: asked only once per conversation ────────────────────────────────────

def test_t6_no_reasking_after_selection(client, env):
    db = env["db"]
    conv_id = _new_conv(client, env)
    client.post("/api/v1/chat/stream", headers=_headers(env["user"]),
                json={"conversation_id": conv_id, "message": "hi"})
    client.post("/api/v1/chat/stream", headers=_headers(env["user"]),
                json={"conversation_id": conv_id, "message": "R.C. Technical Institute"})
    for q in ["What courses are available?", "What is the BCA fee?",
              "Who is the principal?", "Where is the library?"]:
        client.post("/api/v1/chat/stream", headers=_headers(env["user"]),
                    json={"conversation_id": conv_id, "message": q})
    from backend.app.models.conversation import Conversation, Message
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    db.refresh(conv)
    assert conv.college_id == env["rcti"].id
    prompts = [m for m in db.query(Message).filter(
        Message.conversation_id == conv_id,
        Message.sender == "assistant").all()
        if "Which college information do you want" in m.content]
    assert len(prompts) == 1


# ── T7: new chat after an assigned chat resets context ──────────────────────

def test_t7_new_chat_resets_context(client, env):
    db = env["db"]
    conv1 = _new_conv(client, env)
    client.post("/api/v1/chat/stream", headers=_headers(env["user"]),
                json={"conversation_id": conv1, "message": "hi"})
    client.post("/api/v1/chat/stream", headers=_headers(env["user"]),
                json={"conversation_id": conv1, "message": "RCTI"})
    conv2 = _new_conv(client, env)
    from backend.app.models.conversation import Conversation
    c1 = db.query(Conversation).filter(Conversation.id == conv1).first()
    c2 = db.query(Conversation).filter(Conversation.id == conv2).first()
    assert c1.college_id == env["rcti"].id
    assert c2.college_id is None, "college must NOT carry over to chat 2"
    res = client.post("/api/v1/chat/stream", headers=_headers(env["user"]),
                      json={"conversation_id": conv2, "message": "hello"})
    assert res.status_code == 200
    assert "Which college information do you want" in _last_assistant(db, conv2).content


# ── T8: existing chat restores context (no re-ask) ──────────────────────────

def test_t8_existing_chat_restores(client, env):
    db = env["db"]
    conv_id = _new_conv(client, env)
    client.post("/api/v1/chat/stream", headers=_headers(env["user"]),
                json={"conversation_id": conv_id, "message": "hi"})
    client.post("/api/v1/chat/stream", headers=_headers(env["user"]),
                json={"conversation_id": conv_id, "message": "R.C. Technical Institute"})
    # Simulate reload: conversation GET + further messages, no college question
    res = client.get(f"/api/v1/conversations/{conv_id}", headers=_headers(env["user"]))
    assert res.status_code == 200
    assert res.json()["college_id"] == env["rcti"].id
    client.post("/api/v1/chat/stream", headers=_headers(env["user"]),
                json={"conversation_id": conv_id, "message": "What is the BCA fee?"})
    from backend.app.models.conversation import Message
    prompts = [m for m in db.query(Message).filter(
        Message.conversation_id == conv_id,
        Message.sender == "assistant").all()
        if "Which college information do you want" in m.content]
    assert len(prompts) == 1


# ── T13: future college resolves with NO code change ────────────────────────

def test_t13_future_college_auto_resolves(client, env):
    db = env["db"]
    from backend.app.models.college import College, CollegeAlias
    now = datetime.now(timezone.utc)
    db.add(College(id="fut-x", name="ABC Institute of Technology",
                   code="ABCT", slug="abcit", status="ACTIVE", created_at=now))
    db.commit()
    conv_id = _new_conv(client, env)
    client.post("/api/v1/chat/stream", headers=_headers(env["user"]),
                json={"conversation_id": conv_id, "message": "hi"})
    client.post("/api/v1/chat/stream", headers=_headers(env["user"]),
                json={"conversation_id": conv_id,
                      "message": "ABC Institute of Technology"})
    from backend.app.models.conversation import Conversation
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    db.refresh(conv)
    assert conv.college_id == "fut-x"
    assert "Connected to ABC Institute of Technology" in _last_assistant(db, conv_id).content
    # Inactive colleges are NOT selectable (§24)
    db.add(CollegeAlias(college_id="fut-x", alias="abc", normalized_alias=normalize("abc")))
    off = College(id="off-x", name="Offline University", code="OFFU",
                  slug="offlineu", status="INACTIVE", created_at=now)
    db.add(off)
    db.commit()
    conv_id = _new_conv(client, env)
    client.post("/api/v1/chat/stream", headers=_headers(env["user"]),
                json={"conversation_id": conv_id, "message": "hi"})
    client.post("/api/v1/chat/stream", headers=_headers(env["user"]),
                json={"conversation_id": conv_id, "message": "Offline University"})
    db.refresh(conv := db.query(Conversation).filter(Conversation.id == conv_id).first())
    assert conv.college_id is None, "inactive college must not be selectable"


# ── T14: ambiguous alias never auto-selects ─────────────────────────────────

def test_t14_ambiguous_alias_asks_for_clarification(client, env):
    db = env["db"]
    from backend.app.models.college import College, CollegeAlias
    from backend.app.chat.college_context import college_context_manager
    now = datetime.now(timezone.utc)
    c1 = College(id="amb-1", name="ABC College - Ahmedabad", code="ABCA",
                 slug="abc-a", status="ACTIVE", created_at=now)
    c2 = College(id="amb-2", name="ABC College - Surat", code="ABCS",
                 slug="abc-s", status="ACTIVE", created_at=now)
    db.add_all([c1, c2])
    db.add(CollegeAlias(college_id="amb-1", alias="ABC College",
                        normalized_alias=normalize("ABC College")))
    db.add(CollegeAlias(college_id="amb-2", alias="ABC College",
                        normalized_alias=normalize("ABC College")))
    db.commit()

    res = college_context_manager.resolve(db, "ABC College")
    assert res["status"] == "AMBIGUOUS"
    assert res["college_id"] is None

    conv_id = _new_conv(client, env)
    client.post("/api/v1/chat/stream", headers=_headers(env["user"]),
                json={"conversation_id": conv_id, "message": "hi"})
    client.post("/api/v1/chat/stream", headers=_headers(env["user"]),
                json={"conversation_id": conv_id, "message": "ABC College"})
    from backend.app.models.conversation import Conversation
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    db.refresh(conv)
    assert conv.college_id is None
    reply = _last_assistant(db, conv_id).content
    assert "more than one college" in reply


# ── T15: frontend tampering — backend never trusts client college_id ────────

def test_t15_frontend_cannot_override_tenant(client, env):
    db = env["db"]
    conv_id = _new_conv(client, env)
    client.post("/api/v1/chat/stream", headers=_headers(env["user"]),
                json={"conversation_id": conv_id, "message": "hi"})
    client.post("/api/v1/chat/stream", headers=_headers(env["user"]),
                json={"conversation_id": conv_id, "message": "R.C. Technical Institute"})
    from backend.app.models.conversation import Conversation
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    db.refresh(conv)
    assert conv.college_id == env["rcti"].id
    # The chat API has NO college_id field at all (Pydantic rejects/ignores it),
    # and the authoritative context is re-read from the conversation row.
    res = client.post("/api/v1/chat/stream", headers=_headers(env["user"]),
                      json={"conversation_id": conv_id,
                            "message": "What is the BCA fee?",
                            "college_id": env["ait"].id})
    assert res.status_code == 200
    db.refresh(conv)
    assert conv.college_id == env["rcti"].id, "conversation tenant unchanged"
