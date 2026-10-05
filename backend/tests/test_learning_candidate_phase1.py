"""
Phase 1 Tests: LearningCandidate database model + migration + multi-college constraints.
"""
import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from backend.app.models.college import College
from backend.app.models.learning import (
    LearningCandidate,
    LEARNING_STATUS_PENDING_REVIEW,
    LEARNING_STATUS_APPROVED,
    LEARNING_STATUS_REJECTED,
    LEARNING_STATUS_MERGED,
    LEARNING_STATUS_DUPLICATE,
    VALID_LEARNING_STATUSES,
)

def test_learning_candidate_model_fields_and_defaults(db: Session):
    # Setup test college
    college = College(
        id=str(uuid.uuid4()),
        name="Phase 1 Test College",
        code="P1TC",
        slug="p1-test-college",
        status="ACTIVE"
    )
    db.add(college)
    db.commit()

    candidate = LearningCandidate(
        college_id=college.id,
        question="What is the fee for BCA?",
        normalized_question="what is the fee for bca",
        detected_intent="FEES",
        category="Fees",
        generated_answer="The BCA fee is 45,000 INR per year.",
        answer_source="GEMINI_UNVERIFIED",
        verification_status="UNVERIFIED",
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)

    assert candidate.id is not None
    assert candidate.college_id == college.id
    assert candidate.question == "What is the fee for BCA?"
    assert candidate.normalized_question == "what is the fee for bca"
    assert candidate.status == LEARNING_STATUS_PENDING_REVIEW
    assert candidate.occurrence_count == 1
    assert candidate.first_asked_at is not None
    assert candidate.last_asked_at is not None
    assert candidate.positive_feedback_count == 0
    assert candidate.negative_feedback_count == 0
    assert candidate.reviewed_by is None
    assert candidate.reviewed_at is None
    assert candidate.rejection_reason is None

    # Test to_dict()
    as_dict = candidate.to_dict()
    assert as_dict["id"] == candidate.id
    assert as_dict["college_id"] == college.id
    assert as_dict["status"] == "PENDING_REVIEW"
    assert as_dict["occurrence_count"] == 1
    assert as_dict["question"] == "What is the fee for BCA?"
    assert as_dict["answer_source"] == "GEMINI_UNVERIFIED"

    # Clean up
    db.delete(candidate)
    db.delete(college)
    db.commit()

def test_learning_candidate_multi_tenant_isolation(db: Session):
    ait_college = College(id=str(uuid.uuid4()), name="AIT Test", code="AIT_TEST", slug="ait-test", status="ACTIVE")
    rcti_college = College(id=str(uuid.uuid4()), name="RCTI Test", code="RCTI_TEST", slug="rcti-test", status="ACTIVE")
    db.add_all([ait_college, rcti_college])
    db.commit()

    cand_ait = LearningCandidate(
        college_id=ait_college.id,
        question="AIT Question 1",
        normalized_question="ait question 1",
        answer_source="GEMINI_UNVERIFIED",
    )
    cand_rcti = LearningCandidate(
        college_id=rcti_college.id,
        question="RCTI Question 1",
        normalized_question="rcti question 1",
        answer_source="GEMINI_UNVERIFIED",
    )
    db.add_all([cand_ait, cand_rcti])
    db.commit()

    # Query filtered by college
    ait_candidates = db.query(LearningCandidate).filter(LearningCandidate.college_id == ait_college.id).all()
    rcti_candidates = db.query(LearningCandidate).filter(LearningCandidate.college_id == rcti_college.id).all()

    assert len(ait_candidates) == 1
    assert ait_candidates[0].question == "AIT Question 1"
    assert len(rcti_candidates) == 1
    assert rcti_candidates[0].question == "RCTI Question 1"

    # Verify relationships
    db.refresh(ait_college)
    assert len(ait_college.learning_candidates) == 1
    assert ait_college.learning_candidates[0].id == cand_ait.id

    # Clean up
    db.delete(cand_ait)
    db.delete(cand_rcti)
    db.delete(ait_college)
    db.delete(rcti_college)
    db.commit()

def test_valid_statuses():
    assert LEARNING_STATUS_PENDING_REVIEW in VALID_LEARNING_STATUSES
    assert LEARNING_STATUS_APPROVED in VALID_LEARNING_STATUSES
    assert LEARNING_STATUS_REJECTED in VALID_LEARNING_STATUSES
    assert LEARNING_STATUS_MERGED in VALID_LEARNING_STATUSES
    assert LEARNING_STATUS_DUPLICATE in VALID_LEARNING_STATUSES
    assert len(VALID_LEARNING_STATUSES) == 5
