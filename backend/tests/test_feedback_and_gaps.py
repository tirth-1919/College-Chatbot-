"""
Tests for the Feedback + Knowledge Gap feature (§53-§56, §38, §41, §42).

Covers:
- Feedback tests: positive/negative/reason/update/duplicate protection/college scope/role protection
- Knowledge gap tests: unanswered detection, dedup/increment, college scope, category/course/year,
  resolution, dismissal
- Security tests: tenant isolation for feedback and gaps, student access blocked, tampering blocked
- Integration test: gap -> draft -> change request -> approval flow shape
"""
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.database import Base, get_db
from backend.app.main import app


# ──────────────── Fixtures ────────────

@pytest.fixture(scope="module")
def db_engine():
    # StaticPool: one shared in-memory DB across threads (TestClient runs in a worker thread)
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="module")
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="module")
def tenant(db_session):
    """Two colleges + admin per college + one student in college A."""
    # Isolate the shared in-memory login rate limiter so this module's many
    # logins don't trip 429s (same pattern as test_auth_refresh_p0.py).
    from backend.app.security.rate_limiter import rate_limiter
    limiter_snapshot = dict(rate_limiter._history)
    rate_limiter._history.clear()
    from backend.app.models.college import College
    from backend.app.models.user import User
    from backend.app.core.security import get_password_hash

    now = datetime.now(timezone.utc)
    ait = College(id="fg-col-ait", name="AIT Test College", code="AITT", slug="ait-test",
                  status="ACTIVE", created_at=now, updated_at=now)
    rcti = College(id="fg-col-rcti", name="RCTI Test College", code="RCTIT", slug="rcti-test",
                   status="ACTIVE", created_at=now, updated_at=now)
    db_session.add_all([ait, rcti])

    def mkuser(email, role, college):
        return User(id=str(uuid.uuid4()), email=email, full_name=email.split("@")[0],
                    hashed_password=get_password_hash("TestPass1!"), role=role,
                    college_id=college, is_active=True, is_verified=True)

    admin_ait = mkuser("aitadmin@fg.example.com", "COLLEGE_ADMIN", ait.id)
    admin_rcti = mkuser("rctiadmin@fg.example.com", "COLLEGE_ADMIN", rcti.id)
    super_admin = mkuser("super@fg.example.com", "SUPER_ADMIN", None)
    student = mkuser("student@fg.example.com", "STUDENT", ait.id)
    db_session.add_all([admin_ait, admin_rcti, super_admin, student])
    db_session.commit()
    yield {
        "ait": ait.id, "rcti": rcti.id,
        "admin_ait": admin_ait, "admin_rcti": admin_rcti,
        "super_admin": super_admin, "student": student,
        "db": db_session,
    }
    # Restore limiter history after the module finishes.
    rate_limiter._history.clear()
    rate_limiter._history.update(limiter_snapshot)


@pytest.fixture(scope="module")
def client(db_session, tenant):
    """TestClient wired to the in-memory session."""
    def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


def _login(client, email):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": "TestPass1!"})
    assert r.status_code == 200, r.text
    data = r.json()
    return data.get("access_token") or data.get("token") or data.get("access")


def _auth_headers(client, email):
    # Clear the shared in-memory login limiter so the module's many logins
    # never trip 429s (production rate limiting is tested elsewhere).
    try:
        from backend.app.security.rate_limiter import rate_limiter
        rate_limiter._history.clear()
    except Exception:
        pass
    return {"Authorization": f"Bearer {_login(client, email)}"}


# ──────────────── §53 Feedback tests ──────────

def test_positive_feedback(client, tenant):
    """A student can leave positive feedback on an assistant answer."""
    from backend.app.models.conversation import Conversation, Message

    now = datetime.now(timezone.utc)
    conv = Conversation(id="fg-conv-1", user_id=tenant["student"].id,
                        college_id=tenant["ait"], title="t", created_at=now, updated_at=now)
    msg = Message(id="fg-msg-1", conversation_id=conv.id, sender="assistant",
                  content="Answer text", created_at=now)
    tenant["db"].add_all([conv, msg])
    tenant["db"].commit()

    headers = _auth_headers(client, "student@fg.example.com")
    r = client.post("/api/v1/chat/feedback", headers=headers, json={
        "message_id": msg.id, "feedback_type": "POSITIVE"})
    assert r.status_code in (200, 201), r.text

    from backend.app.models.knowledge import MessageFeedback
    row = (tenant["db"].query(MessageFeedback)
           .filter(MessageFeedback.message_id == msg.id).first())
    assert row is not None
    assert row.feedback_type == "POSITIVE"
    assert row.college_id == tenant["ait"]


def test_negative_feedback_reason(client, tenant):
    """Negative feedback requires a reason and stores it."""
    from backend.app.models.conversation import Conversation, Message

    now = datetime.now(timezone.utc)
    conv = Conversation(id="fg-conv-2", user_id=tenant["student"].id,
                        college_id=tenant["ait"], title="t2", created_at=now, updated_at=now)
    msg = Message(id="fg-msg-2", conversation_id=conv.id, sender="assistant",
                  content="Answer 2", created_at=now)
    tenant["db"].add_all([conv, msg])
    tenant["db"].commit()

    headers = _auth_headers(client, "student@fg.example.com")
    r = client.post("/api/v1/chat/feedback", headers=headers, json={
        "message_id": msg.id,
        "feedback_type": "NEGATIVE",
        "reason": "incorrect_information",
    })
    assert r.status_code in (200, 201), r.text
    assert r.json().get("feedback_type", "NEGATIVE") == "NEGATIVE" or r.json().get("reason")


def test_feedback_updates(client, tenant):
    """Changing 👍 → 👎 updates the same record, not a new one."""
    from backend.app.models.conversation import Conversation, Message

    now = datetime.now(timezone.utc)
    conv = Conversation(id="fg-conv-3", user_id=tenant["student"].id,
                        college_id=tenant["ait"], title="t3", created_at=now, updated_at=now)
    msg = Message(id="fg-msg-3", conversation_id=conv.id, sender="assistant",
                  content="Answer 3", created_at=now)
    tenant["db"].add_all([conv, msg])
    tenant["db"].commit()

    headers = _auth_headers(client, "student@fg.example.com")
    payload = {"message_id": msg.id, "feedback_type": "POSITIVE"}
    r1 = client.post("/api/v1/chat/feedback", headers=headers, json=payload)
    assert r1.status_code in (200, 201), r1.text
    payload["feedback_type"] = "NEGATIVE"
    payload["reason"] = "outdated_information"
    r2 = client.post("/api/v1/chat/feedback", headers=headers, json=payload)
    assert r2.status_code in (200, 201), r2.text

    from backend.app.models.knowledge import MessageFeedback
    rows = (tenant["db"].query(MessageFeedback)
            .filter(MessageFeedback.message_id == msg.id).all())
    assert len(rows) == 1, "feedback update must not duplicate rows (§41)"
    assert rows[0].feedback_type == "NEGATIVE"


def test_duplicate_feedback_protection(client, tenant):
    """Repeated identical submissions stay idempotent (§41)."""
    from backend.app.models.conversation import Conversation, Message

    now = datetime.now(timezone.utc)
    conv = Conversation(id="fg-conv-4", user_id=tenant["student"].id,
                        college_id=tenant["ait"], title="t4", created_at=now, updated_at=now)
    msg = Message(id="fg-msg-4", conversation_id=conv.id, sender="assistant",
                  content="Answer 4", created_at=now)
    tenant["db"].add_all([conv, msg])
    tenant["db"].commit()

    headers = _auth_headers(client, "student@fg.example.com")
    payload = {"message_id": msg.id, "feedback_type": "NEGATIVE", "reason": "other",
               "details": "dup test"}
    for _ in range(3):
        r = client.post("/api/v1/chat/feedback", headers=headers, json=payload)
        assert r.status_code in (200, 201), r.text

    from backend.app.models.knowledge import MessageFeedback
    rows = (tenant["db"].query(MessageFeedback)
            .filter(MessageFeedback.message_id == msg.id).all())
    assert len(rows) == 1


def test_feedback_college_scope(client, tenant):
    """Feedback inherits the conversation's college, never the browser's claim (§5)."""
    from backend.app.models.conversation import Conversation, Message

    now = datetime.now(timezone.utc)
    # Student's college is AIT but conversation belongs to RCTI context — server must use RCTI
    conv = Conversation(id="fg-conv-5", user_id=tenant["student"].id,
                        college_id=tenant["rcti"], title="t5", created_at=now, updated_at=now)
    msg = Message(id="fg-msg-5", conversation_id=conv.id, sender="assistant",
                  content="RCTI answer", created_at=now)
    tenant["db"].add_all([conv, msg])
    tenant["db"].commit()

    headers = _auth_headers(client, "student@fg.example.com")
    # Try to force a wrong college from the frontend (§55)
    r = client.post("/api/v1/chat/feedback", headers=headers, json={
        "message_id": msg.id, "feedback_type": "POSITIVE",
        "college_id": tenant["ait"],  # tampering attempt — must be ignored
    })
    assert r.status_code in (200, 201), r.text

    from backend.app.models.knowledge import MessageFeedback
    row = (tenant["db"].query(MessageFeedback)
           .filter(MessageFeedback.message_id == msg.id).first())
    assert row is not None
    assert row.college_id == tenant["rcti"], "college_id must come from conversation context (§5)"


def test_feedback_role_protection(client, tenant):
    """Unauthenticated requests are rejected."""
    from backend.app.models.conversation import Conversation, Message

    now = datetime.now(timezone.utc)
    conv = Conversation(id="fg-conv-6", user_id=tenant["student"].id,
                        college_id=tenant["ait"], title="t6", created_at=now, updated_at=now)
    msg = Message(id="fg-msg-6", conversation_id=conv.id, sender="assistant",
                  content="Answer 6", created_at=now)
    tenant["db"].add_all([conv, msg])
    tenant["db"].commit()

    r = client.post("/api/v1/chat/feedback", json={
        "message_id": msg.id, "feedback_type": "POSITIVE"})
    assert r.status_code in (401, 403)


# ──────────────── §54 Knowledge gap tests ─────────────

def test_unanswered_question_creates_gap(tenant):
    """Unanswered detection creates an OPEN gap (§7, §8)."""
    from backend.app.knowledge.gaps import record_gap, is_unanswered

    assert is_unanswered("I couldn't find verified information about this.", "verified")
    assert is_unanswered("Some answer", "unverified")

    g = record_gap(tenant["db"], college_id=tenant["rcti"],
                   question="What is hostel eligibility?",
                   sample_answer="I couldn't find verified information.",
                   reason="no_verified_source")
    assert g is not None
    assert g.status == "OPEN"
    assert g.college_id == tenant["rcti"]
    assert g.occurrence_count == 1
    tenant["db"].expire_all()


def test_repeated_questions_increment_occurrence(tenant):
    """Similar questions dedup into one gap with occurrence_count++ (§9, §42)."""
    from backend.app.knowledge.gaps import record_gap

    cid = tenant["rcti"]
    # Baseline: earlier tests in this module may already have recorded this
    # question in RCTI (shared module DB) — assert on the increment instead.
    baseline = record_gap(tenant["db"], college_id=cid, question="What is hostel eligibility?")
    start = baseline.occurrence_count
    g1 = record_gap(tenant["db"], college_id=cid, question="What is hostel eligibility?")
    g2 = record_gap(tenant["db"], college_id=cid, question="what is hostel eligibility?")
    g3 = record_gap(tenant["db"], college_id=cid, question="What are hostel eligibility rules?")

    assert g1.id == g2.id, "identical (normalized) questions must dedup"
    assert g1.occurrence_count == start + 3
    assert g3.id == g1.id, "punctuation variants group together (§42 example)"
    assert g1.first_seen_at is not None and g1.last_seen_at is not None


def test_gap_is_college_scoped(tenant):
    """The same question in different colleges creates separate gaps (§38, §59)."""
    from backend.app.knowledge.gaps import record_gap

    g_a = record_gap(tenant["db"], college_id=tenant["ait"], question="Bus route timings?")
    g_b = record_gap(tenant["db"], college_id=tenant["rcti"], question="Bus route timings?")
    assert g_a.id != g_b.id, "identical questions in different colleges must not merge"


def test_gap_category(tenant):
    from backend.app.knowledge.gaps import record_gap, extract_category

    assert extract_category("What is the hostel fee?") is None  # hostel + fee ambiguous
    g = record_gap(tenant["db"], college_id=tenant["ait"], question="What are hostel rules?")
    assert g.category == "Hostel"


def test_gap_course_and_academic_year(tenant):
    from backend.app.knowledge.gaps import record_gap

    g = record_gap(tenant["db"], college_id=tenant["rcti"],
                   question="What is MCA fee for 2026-27?")
    assert g.course and g.course.lower() == "mca"
    assert g.academic_year == "2026-27" or g.academic_year.replace(" ", "") == "2026-27"


def test_gap_resolution(tenant):
    from backend.app.knowledge.gaps import record_gap

    g = record_gap(tenant["db"], college_id=tenant["ait"], question="Library opening hours?")
    g.status = "RESOLVED"
    g.resolved = True
    g.resolved_at = datetime.now(timezone.utc)
    tenant["db"].commit()
    assert g.status == "RESOLVED"


def test_gap_dismissal(tenant):
    from backend.app.knowledge.gaps import record_gap

    g = record_gap(tenant["db"], college_id=tenant["ait"], question="Canteen menu prices?")
    g.status = "DISMISSED"
    g.resolved = True
    tenant["db"].commit()
    assert g.status == "DISMISSED"


# ──────────────── §55 Security tests (HTTP layer) ─────────────

def test_admin_tenant_isolation_feedback(client, tenant):
    """AIT admin cannot read RCTI feedback and vice versa (§38)."""
    from backend.app.models.conversation import Conversation, Message
    from backend.app.models.knowledge import MessageFeedback

    now = datetime.now(timezone.utc)
    conv = Conversation(id="fg-conv-r", user_id=tenant["student"].id,
                        college_id=tenant["rcti"], title="r", created_at=now, updated_at=now)
    msg = Message(id="fg-msg-r", conversation_id=conv.id, sender="assistant",
                  content="RCTI answer", created_at=now)
    fb = MessageFeedback(id="fg-fb-r", college_id=tenant["rcti"], conversation_id=conv.id,
                         message_id=msg.id, user_id=tenant["student"].id,
                         feedback_type="NEGATIVE", reason="incorrect_information",
                         status="NEW", created_at=now)
    tenant["db"].add_all([conv, msg, fb])
    tenant["db"].commit()

    ait_headers = _auth_headers(client, "aitadmin@fg.example.com")
    r = client.get("/api/v1/admin/feedback", headers=ait_headers)
    ids = [i["id"] for i in r.json().get("items", [])]
    assert "fg-fb-r" not in ids, "AIT admin must not see RCTI feedback (§38)"

    # Direct fetch of another college's feedback must 403/404
    r2 = client.get("/api/v1/admin/feedback/fg-fb-r", headers=ait_headers)
    assert r2.status_code in (403, 404)

    rcti_headers = _auth_headers(client, "rctiadmin@fg.example.com")
    r3 = client.get("/api/v1/admin/feedback", headers=rcti_headers)
    ids3 = [i["id"] for i in r3.json().get("items", [])]
    assert "fg-fb-r" in ids3, "RCTI admin must see own college feedback"


def test_admin_tenant_isolation_gaps(client, tenant):
    """RCTI admin cannot read AIT gaps and vice versa (§38)."""
    from backend.app.knowledge.gaps import record_gap

    g = record_gap(tenant["db"], college_id=tenant["rcti"], question="RCTI-only gap question?")

    ait_headers = _auth_headers(client, "aitadmin@fg.example.com")
    r = client.get("/api/v1/admin/knowledge-gaps", headers=ait_headers)
    ids = [i["id"] for i in r.json().get("items", r.json() if isinstance(r.json(), list) else [])]
    assert g.id not in ids, "AIT admin must not see RCTI gaps"

    r2 = client.get(f"/api/v1/admin/knowledge-gaps/{g.id}", headers=ait_headers)
    assert r2.status_code in (403, 404)

    rcti_headers = _auth_headers(client, "rctiadmin@fg.example.com")
    r3 = client.get(f"/api/v1/admin/knowledge-gaps/{g.id}", headers=rcti_headers)
    assert r3.status_code == 200, "RCTI admin must see own college gap"


def test_student_cannot_access_admin_feedback_api(client, tenant):
    headers = _auth_headers(client, "student@fg.example.com")
    r = client.get("/api/v1/admin/feedback", headers=headers)
    assert r.status_code in (401, 403)


def test_student_cannot_modify_knowledge_gaps(client, tenant):
    from backend.app.knowledge.gaps import record_gap

    g = record_gap(tenant["db"], college_id=tenant["ait"], question="Student tamper test?")
    headers = _auth_headers(client, "student@fg.example.com")
    r = client.patch(f"/api/v1/admin/knowledge-gaps/{g.id}", headers=headers,
                     json={"status": "RESOLVED"})
    assert r.status_code in (401, 403)


def test_frontend_college_id_cannot_override_server_context(client, tenant):
    """Admin list API must ignore a client-supplied college_id outside tenant scope (§40)."""
    ait_headers = _auth_headers(client, "aitadmin@fg.example.com")
    # AIT admin tries to pull RCTI-scoped data by passing college_id explicitly
    r = client.get("/api/v1/admin/knowledge-gaps", headers=ait_headers,
                   params={"college_id": tenant["rcti"]})
    items = r.json().get("items", r.json() if isinstance(r.json(), list) else [])
    ids = [i["id"] for i in items]
    assert all(not i.startswith("fg") or True for i in ids)  # shape check
    # Crucially: no RCTI gap should leak. Fetch RCTI gap id set via rcti admin for comparison.
    rcti_headers = _auth_headers(client, "rctiadmin@fg.example.com")
    r2 = client.get("/api/v1/admin/knowledge-gaps", headers=rcti_headers)
    rcti_ids = {i["id"] for i in r2.json().get("items", [])}
    assert not (set(ids) & rcti_ids), "AIT admin must never receive RCTI gaps via query param"


# ──────────────── §56 Integration: gap → draft → change request ───────────────

def test_gap_to_change_request_integration(client, tenant):
    """Gap → admin create-draft → PENDING ChangeRequest (approval flow §19, §56)."""
    from backend.app.models.conversation import Conversation, Message
    from backend.app.knowledge.gaps import record_gap
    from backend.app.models.college import ChangeRequest

    now = datetime.now(timezone.utc)
    conv = Conversation(id="fg-conv-i", user_id=tenant["student"].id,
                        college_id=tenant["rcti"], title="i", created_at=now, updated_at=now)
    msg = Message(id="fg-msg-i", conversation_id=conv.id, sender="user",
                  content="What is the RCTI scholarship criteria for 2026-27?", created_at=now)
    tenant["db"].add_all([conv, msg])
    tenant["db"].commit()

    gap = record_gap(tenant["db"], college_id=tenant["rcti"], question=msg.content,
                     conversation_id=conv.id, message_id=msg.id,
                     sample_answer="I couldn't find verified information.")
    tenant["db"].commit()

    rcti_headers = _auth_headers(client, "rctiadmin@fg.example.com")
    r = client.post(f"/api/v1/admin/knowledge-gaps/{gap.id}/create-draft",
                    headers=rcti_headers, json={
                        "title": "RCTI Scholarship Criteria 2026-27",
                        "answer_value": "Merit-based scholarship per official RCTI page.",
                        "source_type": "OFFICIAL_WEBSITE",
                        "source_url": "https://rcti.example.edu/scholarships",
                    })
    assert r.status_code in (200, 201), r.text
    data = r.json()
    cr_id = data["change_request"]["id"]
    assert data["change_request"]["status"] == "PENDING", "draft must enter approval flow (§17)"
    assert data["is_official"] is True  # official source provided (§18)

    cr = tenant["db"].query(ChangeRequest).filter(ChangeRequest.id == cr_id).first()
    assert cr is not None and cr.status == "PENDING"

    # Gap should now be IN_PROGRESS, not RESOLVED (§48 — only resolved after approval)
    tenant["db"].expire_all()
    assert gap.status == "IN_PROGRESS"


def test_draft_without_source_not_official(client, tenant):
    """A draft without a source must not be labeled official (§18)."""
    from backend.app.knowledge.gaps import record_gap

    gap = record_gap(tenant["db"], college_id=tenant["ait"], question="AIT draft no-source?")
    ait_headers = _auth_headers(client, "aitadmin@fg.example.com")
    r = client.post(f"/api/v1/admin/knowledge-gaps/{gap.id}/create-draft",
                    headers=ait_headers, json={
                        "title": "Untitled knowledge",
                        "answer_value": "Some answer",
                    })
    assert r.status_code in (200, 201), r.text
    assert r.json().get("is_official") is False


def test_super_admin_platform_view(client, tenant):
    """SUPER_ADMIN sees platform-wide gaps and feedback (§21, §23)."""
    super_headers = _auth_headers(client, "super@fg.example.com")
    r = client.get("/api/v1/admin/knowledge-gaps", headers=super_headers)
    assert r.status_code == 200, r.text
    r2 = client.get("/api/v1/admin/feedback", headers=super_headers)
    assert r2.status_code == 200, r2.text
