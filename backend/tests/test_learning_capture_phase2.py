"""
Phase 2 Tests: Learning Capture Service
========================================
Tests that every normal student question is captured into LearningCandidate,
that source attribution is preserved as-is, that tenant isolation is respected,
and that a capture failure never blocks the chat response.

All tests operate against the real SQLite test database (SessionLocal) — the
same approach used by the Phase 1 tests.
"""
import uuid
import logging
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from backend.app.core.database import Base, SessionLocal
from backend.app.models.college import College
from backend.app.models.learning import LearningCandidate, LEARNING_STATUS_PENDING_REVIEW
from backend.app.services.learning_service import (
    capture_question,
    normalize_question,
    _derive_verification_status,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_college(db: Session, suffix: str) -> College:
    college = College(
        id=str(uuid.uuid4()),
        name=f"Test College {suffix}",
        code=f"TC{suffix.upper()[:6]}",
        slug=f"tc-{suffix.lower()[:8]}-{uuid.uuid4().hex[:4]}",
        status="ACTIVE",
    )
    db.add(college)
    db.commit()
    db.refresh(college)
    return college


def _count_candidates(db: Session, college_id: str) -> int:
    return db.query(LearningCandidate).filter(
        LearningCandidate.college_id == college_id
    ).count()


def _get_candidate(db: Session, college_id: str) -> LearningCandidate:
    return db.query(LearningCandidate).filter(
        LearningCandidate.college_id == college_id
    ).order_by(LearningCandidate.created_at.desc()).first()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture()
def ait_college(db):
    c = _make_college(db, "AIT")
    yield c
    db.query(LearningCandidate).filter(LearningCandidate.college_id == c.id).delete()
    db.query(College).filter(College.id == c.id).delete()
    db.commit()


@pytest.fixture()
def rcti_college(db):
    c = _make_college(db, "RCTI")
    yield c
    db.query(LearningCandidate).filter(LearningCandidate.college_id == c.id).delete()
    db.query(College).filter(College.id == c.id).delete()
    db.commit()


@pytest.fixture()
def third_college(db):
    c = _make_college(db, "THIRD")
    yield c
    db.query(LearningCandidate).filter(LearningCandidate.college_id == c.id).delete()
    db.query(College).filter(College.id == c.id).delete()
    db.commit()


# ===========================================================================
# 1. NORMALISATION (deterministic, no DB required)
# ===========================================================================

def test_normalize_strips_whitespace():
    assert normalize_question("  hello world  ") == "hello world"


def test_normalize_collapses_internal_whitespace():
    assert normalize_question("What  is   BCA   fee?") == "what is bca fee?"


def test_normalize_lowercases():
    assert normalize_question("What Is The BCA Fee?") == "what is the bca fee?"


def test_normalize_preserves_punctuation():
    result = normalize_question("  What is BCA   fee?  ")
    assert result == "what is bca fee?"
    assert "?" in result


def test_normalize_empty_string():
    assert normalize_question("") == ""


def test_normalize_none_like_empty():
    assert normalize_question("") == ""


# ===========================================================================
# 2. VERIFICATION STATUS HELPER (no DB required)
# ===========================================================================

def test_derive_verification_status_official_website():
    assert _derive_verification_status("OFFICIAL_WEBSITE", "verified") == "verified"


def test_derive_verification_status_admin_verified():
    assert _derive_verification_status("ADMIN_VERIFIED", "verified") == "verified"


def test_derive_verification_status_gemini_unverified():
    assert _derive_verification_status("GEMINI_UNVERIFIED", "general_ai") == "unverified"


def test_derive_verification_status_provider_error():
    assert _derive_verification_status("PROVIDER_ERROR", "unverified") == "provider_error"


def test_derive_verification_status_fallback_to_grounding():
    # unknown source falls back to the grounding_status string
    assert _derive_verification_status("SOME_UNKNOWN", "general_ai") == "general_ai"


# ===========================================================================
# 3. CAPTURE — OFFICIAL_WEBSITE source is preserved
# ===========================================================================

def test_official_website_source_preserved(db, ait_college):
    before = _count_candidates(db, ait_college.id)
    capture_question(
        db,
        college_id=ait_college.id,
        question="What is the BCA fee at AIT?",
        generated_answer="The BCA fee is ₹45,000/year.",
        answer_source="OFFICIAL_WEBSITE",
        grounding_status="verified",
        conversation_id=None,
    )
    assert _count_candidates(db, ait_college.id) == before + 1
    cand = _get_candidate(db, ait_college.id)
    assert cand.answer_source == "OFFICIAL_WEBSITE"
    assert cand.verification_status == "verified"
    assert cand.college_id == ait_college.id


# ===========================================================================
# 4. CAPTURE — ADMIN_VERIFIED source is preserved
# ===========================================================================

def test_admin_verified_source_preserved(db, ait_college):
    before = _count_candidates(db, ait_college.id)
    capture_question(
        db,
        college_id=ait_college.id,
        question="Who teaches DBMS at AIT?",
        generated_answer="Prof. Asha Rao teaches DBMS.",
        answer_source="ADMIN_VERIFIED",
        grounding_status="verified",
    )
    assert _count_candidates(db, ait_college.id) == before + 1
    cand = _get_candidate(db, ait_college.id)
    assert cand.answer_source == "ADMIN_VERIFIED"
    assert cand.verification_status == "verified"


# ===========================================================================
# 5. CAPTURE — GEMINI_UNVERIFIED source is preserved (not upgraded)
# ===========================================================================

def test_gemini_unverified_source_preserved(db, ait_college):
    before = _count_candidates(db, ait_college.id)
    capture_question(
        db,
        college_id=ait_college.id,
        question="What programming concepts should a beginner practice?",
        generated_answer="Beginners should practice variables, loops, functions…",
        answer_source="GEMINI_UNVERIFIED",
        grounding_status="general_ai",
    )
    assert _count_candidates(db, ait_college.id) == before + 1
    cand = _get_candidate(db, ait_college.id)
    # MUST remain GEMINI_UNVERIFIED — never promoted to ADMIN_VERIFIED
    assert cand.answer_source == "GEMINI_UNVERIFIED"
    assert cand.verification_status == "unverified"


def test_gemini_source_not_converted_to_admin_verified(db, ait_college):
    """Explicit regression: GEMINI_UNVERIFIED must never become ADMIN_VERIFIED."""
    capture_question(
        db,
        college_id=ait_college.id,
        question="Explain polymorphism in Python.",
        generated_answer="Polymorphism allows objects of different types…",
        answer_source="GEMINI_UNVERIFIED",
        grounding_status="general_ai",
    )
    cand = _get_candidate(db, ait_college.id)
    assert cand.answer_source != "ADMIN_VERIFIED", (
        "GEMINI_UNVERIFIED answer was wrongly promoted to ADMIN_VERIFIED"
    )


# ===========================================================================
# 6. TENANT ISOLATION — AIT question → AIT LearningCandidate
# ===========================================================================

def test_ait_question_creates_ait_candidate(db, ait_college, rcti_college):
    before_ait = _count_candidates(db, ait_college.id)
    before_rcti = _count_candidates(db, rcti_college.id)

    capture_question(
        db,
        college_id=ait_college.id,
        question="What is the BCA fee at AIT?",
        generated_answer="₹45,000/year.",
        answer_source="OFFICIAL_WEBSITE",
        grounding_status="verified",
    )

    assert _count_candidates(db, ait_college.id) == before_ait + 1
    # RCTI count must not increase
    assert _count_candidates(db, rcti_college.id) == before_rcti
    cand = _get_candidate(db, ait_college.id)
    assert cand.college_id == ait_college.id
    assert cand.college_id != rcti_college.id


# ===========================================================================
# 7. TENANT ISOLATION — RCTI question → RCTI LearningCandidate (never AIT)
# ===========================================================================

def test_rcti_question_creates_rcti_candidate(db, ait_college, rcti_college):
    before_ait = _count_candidates(db, ait_college.id)
    before_rcti = _count_candidates(db, rcti_college.id)

    capture_question(
        db,
        college_id=rcti_college.id,
        question="What is the BCA Semester 5 fee at RCTI?",
        generated_answer="The BCA Semester 5 fee at RCTI is ₹30,000.",
        answer_source="ADMIN_VERIFIED",
        grounding_status="verified",
    )

    assert _count_candidates(db, rcti_college.id) == before_rcti + 1
    # AIT count must not increase
    assert _count_candidates(db, ait_college.id) == before_ait
    cand = _get_candidate(db, rcti_college.id)
    # CRITICAL: college_id must be RCTI, never AIT
    assert cand.college_id == rcti_college.id
    assert cand.college_id != ait_college.id


# ===========================================================================
# 8. TENANT ISOLATION — Third college question → third-college LearningCandidate
# ===========================================================================

def test_third_college_candidate_correct_tenant(db, ait_college, rcti_college, third_college):
    before_ait = _count_candidates(db, ait_college.id)
    before_rcti = _count_candidates(db, rcti_college.id)
    before_third = _count_candidates(db, third_college.id)

    capture_question(
        db,
        college_id=third_college.id,
        question="What courses does the third college offer?",
        generated_answer="The third college offers BCA, BBA, and B.Com.",
        answer_source="ADMIN_VERIFIED",
        grounding_status="verified",
    )

    assert _count_candidates(db, third_college.id) == before_third + 1
    assert _count_candidates(db, ait_college.id) == before_ait
    assert _count_candidates(db, rcti_college.id) == before_rcti
    cand = _get_candidate(db, third_college.id)
    assert cand.college_id == third_college.id


# ===========================================================================
# 9. NO HARD-CODED AIT FALLBACK
# ===========================================================================

def test_no_hardcoded_ait_fallback(db, ait_college, rcti_college):
    """If college_id=rcti, the resulting candidate must be scoped to RCTI, not AIT."""
    capture_question(
        db,
        college_id=rcti_college.id,
        question="What is the hostel fee at RCTI?",
        generated_answer="RCTI hostel costs ₹60,000/year.",
        answer_source="GEMINI_UNVERIFIED",
        grounding_status="unverified",
    )
    cand = _get_candidate(db, rcti_college.id)
    assert cand is not None
    assert cand.college_id == rcti_college.id
    # Verify no stray AIT candidate appeared
    ait_cands = db.query(LearningCandidate).filter(
        LearningCandidate.college_id == ait_college.id,
        LearningCandidate.question == "What is the hostel fee at RCTI?",
    ).all()
    assert ait_cands == [], "Candidate was wrongly created under AIT instead of RCTI"


# ===========================================================================
# 10. MISSING college_id — should log and skip (no exception raised)
# ===========================================================================

def test_missing_college_id_skips_capture(db, caplog):
    with caplog.at_level(logging.WARNING, logger="ait.learning_service"):
        capture_question(
            db,
            college_id=None,
            question="Some question without a college",
            generated_answer="Some answer.",
            answer_source="GEMINI_UNVERIFIED",
            grounding_status="general_ai",
        )
    assert any("without college_id" in r.message for r in caplog.records), (
        "Expected a warning log when college_id is missing"
    )


# ===========================================================================
# 11. CONVERSATION ID is preserved
# ===========================================================================

def test_conversation_id_preserved(db, ait_college):
    conv_id = str(uuid.uuid4())
    capture_question(
        db,
        college_id=ait_college.id,
        question="Tell me about AIT placements.",
        generated_answer="AIT has excellent placements.",
        answer_source="OFFICIAL_WEBSITE",
        grounding_status="verified",
        conversation_id=conv_id,
    )
    cand = _get_candidate(db, ait_college.id)
    assert cand.conversation_id == conv_id


def test_none_conversation_id_stored_as_none(db, ait_college):
    capture_question(
        db,
        college_id=ait_college.id,
        question="Tell me about AIT courses.",
        generated_answer="AIT offers BCA, BBA.",
        answer_source="ADMIN_VERIFIED",
        grounding_status="verified",
        conversation_id=None,
    )
    cand = _get_candidate(db, ait_college.id)
    assert cand.conversation_id is None


# ===========================================================================
# 12. DETECTED INTENT is captured when available
# ===========================================================================

def test_detected_intent_captured(db, ait_college):
    capture_question(
        db,
        college_id=ait_college.id,
        question="What are the fees for BCA?",
        generated_answer="₹45,000/year.",
        answer_source="ADMIN_VERIFIED",
        grounding_status="verified",
        detected_intent="FEES",
    )
    cand = _get_candidate(db, ait_college.id)
    assert cand.detected_intent == "FEES"


def test_detected_intent_none_when_not_provided(db, ait_college):
    capture_question(
        db,
        college_id=ait_college.id,
        question="General question here.",
        generated_answer="General answer.",
        answer_source="GEMINI_UNVERIFIED",
        grounding_status="general_ai",
    )
    cand = _get_candidate(db, ait_college.id)
    assert cand.detected_intent is None


# ===========================================================================
# 13. CATEGORY is captured when available
# ===========================================================================

def test_category_captured(db, ait_college):
    capture_question(
        db,
        college_id=ait_college.id,
        question="Tell me about the library.",
        generated_answer="The library has 10,000 books.",
        answer_source="ADMIN_VERIFIED",
        grounding_status="verified",
        category="Facilities",
    )
    cand = _get_candidate(db, ait_college.id)
    assert cand.category == "Facilities"


# ===========================================================================
# 14. NORMALIZED QUESTION is stored correctly
# ===========================================================================

def test_normalized_question_stored(db, ait_college):
    raw = "  What Is The BCA   Fee?  "
    capture_question(
        db,
        college_id=ait_college.id,
        question=raw,
        generated_answer="₹45,000/year.",
        answer_source="OFFICIAL_WEBSITE",
        grounding_status="verified",
    )
    cand = _get_candidate(db, ait_college.id)
    assert cand.question == raw                        # original preserved
    # normalize_question collapses all runs of whitespace → "what is the bca fee?"
    import re as _re
    expected_normalized = _re.sub(r"\s+", " ", raw.strip()).lower()
    assert cand.normalized_question == expected_normalized



# ===========================================================================
# 15. LEARNING CAPTURE FAILURE does NOT fail the chat response
# ===========================================================================

def test_capture_failure_does_not_raise(db, ait_college):
    """Simulates a DB error during capture — must not propagate to caller."""
    import unittest.mock as mock

    # Force db.add to raise an unexpected error
    original_add = db.add

    def exploding_add(obj):
        if isinstance(obj, LearningCandidate):
            raise RuntimeError("Simulated DB failure during learning capture")
        return original_add(obj)

    with mock.patch.object(db, "add", side_effect=exploding_add):
        # This MUST NOT raise
        capture_question(
            db,
            college_id=ait_college.id,
            question="Will this fail silently?",
            generated_answer="It should.",
            answer_source="GEMINI_UNVERIFIED",
            grounding_status="general_ai",
        )
    # If we reach here, the error was swallowed correctly ✓


# ===========================================================================
# 16. OCCURRENCE COUNT default = 1 (Phase 1 model default, not changed)
# ===========================================================================

def test_occurrence_count_default_is_one(db, ait_college):
    capture_question(
        db,
        college_id=ait_college.id,
        question="How many labs does AIT have?",
        generated_answer="AIT has 10 computer labs.",
        answer_source="OFFICIAL_WEBSITE",
        grounding_status="verified",
    )
    cand = _get_candidate(db, ait_college.id)
    assert cand.occurrence_count == 1


# ===========================================================================
# 17. STATUS defaults to PENDING_REVIEW (Phase 1 model default)
# ===========================================================================

def test_status_defaults_to_pending_review(db, ait_college):
    capture_question(
        db,
        college_id=ait_college.id,
        question="What is AIT's address?",
        generated_answer="AIT is located in Ahmedabad.",
        answer_source="OFFICIAL_WEBSITE",
        grounding_status="verified",
    )
    cand = _get_candidate(db, ait_college.id)
    assert cand.status == LEARNING_STATUS_PENDING_REVIEW


# ===========================================================================
# 18. METADATA is stored and includes capture version
# ===========================================================================

def test_metadata_contains_capture_version(db, ait_college):
    capture_question(
        db,
        college_id=ait_college.id,
        question="What is the admission process?",
        generated_answer="Apply via ACPC.",
        answer_source="ADMIN_VERIFIED",
        grounding_status="verified",
        extra_metadata={"route": "institutional", "source_count": 2},
    )
    cand = _get_candidate(db, ait_college.id)
    assert cand.metadata_json is not None
    # Phase 3 bumped the version to 2; accept any value >= 1 so this test
    # remains compatible with future phase upgrades.
    assert cand.metadata_json.get("learning_capture_version", 0) >= 1
    assert cand.metadata_json.get("effective_college_id") == ait_college.id
    assert cand.metadata_json.get("route") == "institutional"


# ===========================================================================
# 19. CROSS-TENANT CONTAMINATION — two captures for different colleges
# ===========================================================================

def test_no_cross_tenant_contamination(db, ait_college, rcti_college):
    capture_question(
        db, college_id=ait_college.id,
        question="AIT's BCA fee?", generated_answer="₹45,000.",
        answer_source="OFFICIAL_WEBSITE", grounding_status="verified",
    )
    capture_question(
        db, college_id=rcti_college.id,
        question="RCTI's BCA fee?", generated_answer="₹30,000.",
        answer_source="OFFICIAL_WEBSITE", grounding_status="verified",
    )

    ait_cands = db.query(LearningCandidate).filter(LearningCandidate.college_id == ait_college.id).all()
    rcti_cands = db.query(LearningCandidate).filter(LearningCandidate.college_id == rcti_college.id).all()

    # Each college's candidates must only belong to that college
    for c in ait_cands:
        assert c.college_id == ait_college.id
    for c in rcti_cands:
        assert c.college_id == rcti_college.id

    # Questions must not cross tenants
    ait_questions = {c.question for c in ait_cands}
    rcti_questions = {c.question for c in rcti_cands}
    assert "RCTI's BCA fee?" not in ait_questions
    assert "AIT's BCA fee?" not in rcti_questions
