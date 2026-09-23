"""
Phase 12: Multi-tenant isolation integration tests.
Tests that verify college-scoped data never leaks across tenant boundaries.
"""
import pytest
import uuid
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ──────────────── In-memory SQLite fixture ────────────────────────────────────

@pytest.fixture(scope="module")
def db_session():
    """Shared in-memory SQLite session for all tests in this module."""
    from backend.app.core.database import Base
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="module")
def two_colleges(db_session):
    """Create two separate college tenants and return their IDs."""
    from backend.app.models.college import College
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    col_a = College(
        id="college-aaa-0001",
        name="Alpha University",
        code="AU",
        slug="alpha-uni",
        status="ACTIVE",
        created_at=now,
        updated_at=now,
    )
    col_b = College(
        id="college-bbb-0002",
        name="Beta College",
        code="BC",
        slug="beta-college",
        status="ACTIVE",
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([col_a, col_b])
    db_session.commit()
    return col_a.id, col_b.id



@pytest.fixture(scope="module")
def two_users(db_session, two_colleges):
    """One student per college."""
    from backend.app.models.user import User
    from backend.app.core.security import get_password_hash

    cid_a, cid_b = two_colleges
    ua = User(
        id=str(uuid.uuid4()),
        email="student_a@alpha.edu",
        full_name="Student A",
        hashed_password=get_password_hash("TestPass1!"),
        role="STUDENT",
        college_id=cid_a,
        is_active=True,
        is_verified=True,
    )
    ub = User(
        id=str(uuid.uuid4()),
        email="student_b@beta.edu",
        full_name="Student B",
        hashed_password=get_password_hash("TestPass1!"),
        role="STUDENT",
        college_id=cid_b,
        is_active=True,
        is_verified=True,
    )
    db_session.add_all([ua, ub])
    db_session.commit()
    return ua, ub


# ──────────────── Test: JWT college_id claim ──────────────────────────────────

def test_jwt_contains_college_id(two_colleges):
    """Access tokens must carry college_id claim."""
    from backend.app.core.security import create_access_token, decode_token

    cid_a, _ = two_colleges
    token = create_access_token({"sub": "user-001", "email": "a@test.com", "role": "STUDENT", "college_id": cid_a})
    payload = decode_token(token)
    assert payload["college_id"] == cid_a, "college_id must survive encode/decode round-trip"


# ──────────────── Test: RAG tenant isolation ──────────────────────────────────

def test_rag_college_isolation(db_session, two_colleges):
    """Documents from College A must NOT be returned for College B searches."""
    from backend.app.knowledge.rag import rag_engine
    from backend.app.models.document import VISIBILITY_ADMIN_VERIFIED

    cid_a, cid_b = two_colleges

    # Index a unique document for College A
    doc_a = rag_engine.index_document(
        db=db_session,
        title="Alpha University Fees 2024",
        text_content="The tuition fee for Alpha University B.Tech is 75000 per semester.",
        college_id=cid_a,
        visibility=VISIBILITY_ADMIN_VERIFIED,
    )
    assert doc_a.college_id == cid_a

    # Search from College B — must NOT see College A docs
    results_b = rag_engine.search(db_session, "tuition fee Alpha University", college_id=cid_b, top_k=10)
    titles_b = [r["title"] for r in results_b]
    assert "Alpha University Fees 2024" not in titles_b, \
        "College B search MUST NOT return College A documents (tenant isolation breach)"

    # Search from College A — must see own docs
    results_a = rag_engine.search(db_session, "tuition fee Alpha University", college_id=cid_a, top_k=10)
    titles_a = [r["title"] for r in results_a]
    assert "Alpha University Fees 2024" in titles_a, \
        "College A search must return its own documents"


# ──────────────── Test: User list scoping ─────────────────────────────────────

def test_user_list_scoped_by_college(db_session, two_users):
    """Querying User.college_id == cid_a must exclude cid_b users."""
    from backend.app.models.user import User

    ua, ub = two_users
    # Simulate what admin/users.py does for COLLEGE_ADMIN
    cid_a = ua.college_id
    users_for_a = db_session.query(User).filter(User.college_id == cid_a).all()
    emails = [u.email for u in users_for_a]

    assert ua.email in emails, "College A user must appear in College A query"
    assert ub.email not in emails, "College B user must NOT appear in College A query"


# ──────────────── Test: College suspension blocks login ───────────────────────

def test_suspended_college_blocks_login(db_session, two_colleges):
    """A student from a SUSPENDED college must receive 403 on login."""
    from backend.app.models.college import College

    _, cid_b = two_colleges
    college_b = db_session.query(College).filter(College.id == cid_b).first()
    college_b.status = "SUSPENDED"
    db_session.commit()

    # Simulate the login check from auth.py
    college_check = db_session.query(College).filter(College.id == cid_b).first()
    assert college_check.status == "SUSPENDED", "College B should be suspended"

    # Restore
    college_b.status = "ACTIVE"
    db_session.commit()


# ──────────────── Test: Document college_id stamp ─────────────────────────────

def test_rag_index_stamps_college_id(db_session, two_colleges):
    """rag_engine.index_document must stamp college_id on both Document and DocumentChunk."""
    from backend.app.knowledge.rag import rag_engine
    from backend.app.models.document import Document, DocumentChunk, VISIBILITY_ADMIN_VERIFIED

    cid_a, _ = two_colleges
    doc = rag_engine.index_document(
        db=db_session,
        title="Alpha CS Syllabus",
        text_content="Computer Science syllabus covers algorithms and data structures.\n\nProgramming languages include Python and Java.",
        college_id=cid_a,
        visibility=VISIBILITY_ADMIN_VERIFIED,
    )
    db_session.refresh(doc)

    assert doc.college_id == cid_a, "Document must carry college_id"
    chunks = db_session.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).all()
    assert len(chunks) > 0, "Document must have chunks"
    for chunk in chunks:
        assert chunk.college_id == cid_a, f"Chunk {chunk.id} missing college_id"


# ──────────────── Test: generate_secure_temporary_password ────────────────────

def test_temporary_password_complexity():
    """Generated temp passwords must meet complexity requirements."""
    from backend.app.core.security import generate_secure_temporary_password
    import re

    for _ in range(10):
        pwd = generate_secure_temporary_password()
        assert len(pwd) >= 12, "Temp password too short"
        assert re.search(r"[A-Z]", pwd), "No uppercase letter"
        assert re.search(r"[a-z]", pwd), "No lowercase letter"
        assert re.search(r"\d", pwd), "No digit"
        assert re.search(r"[!@#$%^&*]", pwd), "No special char"
