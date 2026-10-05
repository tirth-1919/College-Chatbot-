'''Continuous-learning administration APIs (Phases 4-18).

This module is deliberately an orchestration layer over LearningCandidate and the
existing ChangeRequest/KnowledgeRecord workflow. It never verifies a candidate
or writes production knowledge during college-admin review.
'''
import json
import logging
import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import or_, func
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.permissions import get_current_admin_user, log_admin_audit
from backend.app.models.college import ChangeRequest, College
from backend.app.models.learning import (
    LearningCandidate, LEARNING_STATUS_PENDING_REVIEW, LEARNING_STATUS_APPROVED,
    LEARNING_STATUS_REJECTED, LEARNING_STATUS_MERGED, LEARNING_STATUS_DUPLICATE,
    VALID_LEARNING_STATUSES,
)
from backend.app.models.knowledge import MessageFeedback
from backend.app.models.knowledge_categories import KnowledgeCategory, KnowledgeRecord
from backend.app.models.user import User
log = logging.getLogger("ait.learning_admin")
router = APIRouter(prefix="/learning-candidates", tags=["Continuous Learning"])


def _super(user):
    return (user.role or "").upper() == "SUPER_ADMIN"


def _scoped(candidate_id: str, user: User, db: Session):
    c = db.query(LearningCandidate).filter(LearningCandidate.id == candidate_id).first()
    if not c or (not _super(user) and c.college_id != user.college_id):
        raise HTTPException(status_code=404, detail="Learning candidate not found")
    return c

def priority(candidate):
    reasons = []
    if (candidate.occurrence_count or 0) >= 5:
        reasons.append("asked frequently")
    if (candidate.negative_feedback_count or 0) > 0:
        reasons.append("received negative feedback")
    if candidate.last_asked_at:
        age = (datetime.now(timezone.utc) - candidate.last_asked_at.replace(tzinfo=timezone.utc)).days
        if age <= 7:
            reasons.append("asked recently")
    if candidate.status == LEARNING_STATUS_PENDING_REVIEW:
        reasons.append("awaiting review")
    return {"priority": "HIGH" if candidate.negative_feedback_count or candidate.occurrence_count >= 5 else "MEDIUM", "reason": " and ".join(reasons) or "normal review priority"}


def _item(c):
    result = c.to_dict()
    result["priority"] = priority(c)
    result["reviewer_name"] = c.reviewer.full_name if c.reviewer else None
    return result
class ReviewBody(BaseModel):
    reason: Optional[str] = Field(None, max_length=2000)

class DuplicateBody(BaseModel):
    target_candidate_id: str = Field(min_length=1, max_length=36)

class MergeBody(BaseModel):
    target_candidate_id: str = Field(min_length=1, max_length=36)

class FeedbackBody(BaseModel):
    feedback_type: str
    @field_validator("feedback_type")
    @classmethod
    def valid_type(cls, value):
        value = value.upper()
        if value not in {"POSITIVE", "NEGATIVE"}:
            raise ValueError("feedback_type must be POSITIVE or NEGATIVE")
        return value
@router.get("")
def list_candidates(
    search: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    category: Optional[str] = None,
    answer_source: Optional[str] = None,
    verification_status: Optional[str] = None,
    sort: str = Query("newest", pattern="^(newest|oldest|occurrence_count|priority)$"),
    page: int = Query(1, ge=1), per_page: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_admin_user), db: Session = Depends(get_db),
):
    q = db.query(LearningCandidate)
    if not _super(current_user):
        q = q.filter(LearningCandidate.college_id == current_user.college_id)
    if search:
        like = f"%{search}%"
        q = q.filter(or_(LearningCandidate.question.ilike(like), LearningCandidate.generated_answer.ilike(like)))
    status_value = status_filter if isinstance(status_filter, str) else None
    if status_value and status_value.upper() != "ALL":
        if status_value.upper() not in VALID_LEARNING_STATUSES:
            raise HTTPException(422, "Invalid learning candidate status")
        q = q.filter(LearningCandidate.status == status_value.upper())
    if category: q = q.filter(LearningCandidate.category == category)
    if answer_source: q = q.filter(LearningCandidate.answer_source == answer_source)
    if verification_status: q = q.filter(LearningCandidate.verification_status == verification_status)
    sort_value = sort if isinstance(sort, str) else "newest"
    if sort_value == "oldest": order = LearningCandidate.first_asked_at.asc()
    elif sort_value == "occurrence_count": order = LearningCandidate.occurrence_count.desc()
    elif sort_value == "priority": order = (LearningCandidate.negative_feedback_count.desc(), LearningCandidate.occurrence_count.desc())
    else: order = LearningCandidate.last_asked_at.desc()
    total = q.count()
    rows = q.order_by(order).offset((page - 1) * per_page).limit(per_page).all()
    return {"items": [_item(x) for x in rows], "total": total, "page": page, "per_page": per_page}

@router.get("/dashboard/summary")
def learning_summary(current_user: User = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    q = db.query(LearningCandidate)
    if not _super(current_user): q = q.filter(LearningCandidate.college_id == current_user.college_id)
    rows = q.all()
    record_q = db.query(KnowledgeRecord).filter(KnowledgeRecord.verified == True, KnowledgeRecord.source_type == "ADMIN_VERIFIED")
    if not _super(current_user): record_q = record_q.filter(KnowledgeRecord.college_id == current_user.college_id)
    return {"total": len(rows), "pending": sum(x.status == LEARNING_STATUS_PENDING_REVIEW for x in rows),
            "approved": sum(x.status == LEARNING_STATUS_APPROVED for x in rows), "rejected": sum(x.status == LEARNING_STATUS_REJECTED for x in rows),
            "duplicates": sum(x.status in {LEARNING_STATUS_DUPLICATE, LEARNING_STATUS_MERGED} for x in rows),
            "occurrences": sum(x.occurrence_count or 0 for x in rows), "negative_feedback": sum(x.negative_feedback_count or 0 for x in rows),
            "verified_knowledge_created": record_q.count()}

@router.get("/clusters")
def clusters(threshold: float = Query(.88, ge=0, le=1), current_user: User = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    q = db.query(LearningCandidate).filter(LearningCandidate.embedding_json.is_not(None))
    if not _super(current_user): q = q.filter(LearningCandidate.college_id == current_user.college_id)
    rows = q.all(); groups = []
    from backend.app.services.learning_service import calculate_cosine_similarity
    for c in rows:
        vec = json.loads(c.embedding_json); group = next((g for g in groups if g["college_id"] == c.college_id and calculate_cosine_similarity(vec, g["_vector"]) >= threshold), None)
        if group: group["candidate_ids"].append(c.id)
        else: groups.append({"_vector": vec, "candidate_ids": [c.id], "college_id": c.college_id})
    return [{k:v for k,v in g.items() if k != "_vector"} for g in groups]

@router.get("/export/jsonl")
def export_dataset(current_user: User = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    q = db.query(LearningCandidate).filter(LearningCandidate.status == LEARNING_STATUS_APPROVED, LearningCandidate.verification_status == "verified", LearningCandidate.answer_source != "GEMINI_UNVERIFIED")
    if not _super(current_user): q = q.filter(LearningCandidate.college_id == current_user.college_id)
    lines = [json.dumps({"question": c.question, "answer": c.generated_answer, "college_id": c.college_id, "category": c.category,
                         "source": c.answer_source, "verification_status": c.verification_status, "occurrence_count": c.occurrence_count,
                         "variations": c.variations or []}, ensure_ascii=False) for c in q.order_by(LearningCandidate.created_at.asc()).all()]
    data = ("\\n".join(lines) + ("\\n" if lines else "")).encode()
    log.info("learning operation=dataset_export status=success college_id=%s", getattr(current_user, "college_id", None))
    return StreamingResponse(BytesIO(data), media_type="application/x-ndjson", headers={"Content-Disposition": "attachment; filename=learning-dataset.jsonl"})

@router.post("/training/prepare")
def prepare_training(current_user: User = Depends(get_current_admin_user)):
    return {"status": "PREPARED", "dataset_endpoint": "/api/v1/admin/learning-candidates/export/jsonl", "deployment": "CONTROLLED_MANUAL", "message": "Training job infrastructure is prepared; no model was deployed."}

@router.get("/{candidate_id}")
def candidate_detail(candidate_id: str, current_user: User = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    return _item(_scoped(candidate_id, current_user, db))

def _review(candidate, user, db, new_status, reason=None):
    if candidate.status in {LEARNING_STATUS_REJECTED, LEARNING_STATUS_DUPLICATE, LEARNING_STATUS_MERGED}:
        raise HTTPException(409, "Terminal candidate cannot be silently resurrected")
    candidate.status = new_status
    candidate.reviewed_by = user.id
    candidate.reviewed_at = datetime.now(timezone.utc)
    if new_status == LEARNING_STATUS_REJECTED:
        if not reason or not reason.strip(): raise HTTPException(422, "Rejection reason is required")
        candidate.rejection_reason = reason.strip()
    db.add(candidate)
    log_admin_audit(db, user, f"LEARNING_CANDIDATE_{new_status}", "LEARNING_CANDIDATE", {"candidate_id": candidate.id}, college_id=candidate.college_id)

@router.post("/{candidate_id}/approve")
def approve_candidate(candidate_id: str, body: ReviewBody = ReviewBody(), current_user: User = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    c = _scoped(candidate_id, current_user, db)
    if _super(current_user): raise HTTPException(403, "College Admin review is required before ChangeRequest creation")
    _review(c, current_user, db, LEARNING_STATUS_APPROVED, body.reason)
    category = db.query(KnowledgeCategory).filter(KnowledgeCategory.college_id == c.college_id, KnowledgeCategory.key == "learning").first()
    if not category:
        category = KnowledgeCategory(college_id=c.college_id, name="Learning", key="learning", status="ACTIVE", created_by=current_user.id, updated_by=current_user.id)
        db.add(category); db.flush()
    payload = {"category_id": category.id, "title": c.question[:255], "value": c.generated_answer or "", "description": c.question,
               "metadata_json": {"learning_candidate_id": c.id, "variations": c.variations or [], "occurrence_count": c.occurrence_count,
                                 "answer_source": c.answer_source, "verification_status": c.verification_status},
               "source_title": "Learning candidate", "source_url": None, "learning_candidate_id": c.id}
    cr = ChangeRequest(college_id=c.college_id, requested_by=current_user.id, entity_type="KNOWLEDGE", action="CREATE",
                       title=f"Learning candidate: {c.question[:220]}", reason="LEARNING_CANDIDATE", new_value=payload,
                       status="PENDING", proposal_origin="LEARNING_CANDIDATE", learning_candidate_id=c.id,
                       provenance_json={"candidate_id": c.id, "occurrence_count": c.occurrence_count, "variations": c.variations or [],
                                        "answer_source": c.answer_source, "verification_status": c.verification_status})
    db.add(cr); db.flush(); c.change_request_id = cr.id; db.commit(); db.refresh(cr)
    log.info("learning operation=change_request_creation status=success college_id=%s candidate_id=%s", c.college_id, c.id)
    return {"candidate": _item(c), "change_request": cr.to_dict()}

@router.post("/{candidate_id}/reject")
def reject_candidate(candidate_id: str, body: ReviewBody, current_user: User = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    c = _scoped(candidate_id, current_user, db); _review(c, current_user, db, LEARNING_STATUS_REJECTED, body.reason); db.commit(); return _item(c)

@router.post("/{candidate_id}/duplicate")
def duplicate_candidate(candidate_id: str, body: DuplicateBody, current_user: User = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    c = _scoped(candidate_id, current_user, db); target = _scoped(body.target_candidate_id, current_user, db)
    if c.id == target.id: raise HTTPException(422, "Duplicate target must differ from candidate")
    if c.college_id != target.college_id: raise HTTPException(403, "Candidates must belong to the same college")
    _review(c, current_user, db, LEARNING_STATUS_DUPLICATE); c.similar_candidate_id = target.id
    target.occurrence_count = (target.occurrence_count or 0) + (c.occurrence_count or 0)
    target.positive_feedback_count = (target.positive_feedback_count or 0) + (c.positive_feedback_count or 0)
    target.negative_feedback_count = (target.negative_feedback_count or 0) + (c.negative_feedback_count or 0)
    target.variations = list(dict.fromkeys((target.variations or []) + [c.question] + (c.variations or [])))[:20]
    db.commit(); return _item(c)

@router.post("/{candidate_id}/merge")
def merge_candidate(candidate_id: str, body: MergeBody, current_user: User = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    c = _scoped(candidate_id, current_user, db); target = _scoped(body.target_candidate_id, current_user, db)
    if c.id == target.id or c.college_id != target.college_id: raise HTTPException(422, "Merge target must be another candidate in the same college")
    if c.status in {LEARNING_STATUS_REJECTED, LEARNING_STATUS_DUPLICATE, LEARNING_STATUS_MERGED}: raise HTTPException(409, "Candidate is terminal")
    c.status = LEARNING_STATUS_MERGED; c.similar_candidate_id = target.id; c.reviewed_by = current_user.id; c.reviewed_at = datetime.now(timezone.utc)
    target.occurrence_count = (target.occurrence_count or 0) + (c.occurrence_count or 0)
    target.positive_feedback_count = (target.positive_feedback_count or 0) + (c.positive_feedback_count or 0)
    target.negative_feedback_count = (target.negative_feedback_count or 0) + (c.negative_feedback_count or 0)
    target.variations = list(dict.fromkeys((target.variations or []) + [c.question] + (c.variations or [])))[:20]
    db.commit(); return _item(target)

@router.post("/{candidate_id}/feedback")
def candidate_feedback(candidate_id: str, body: FeedbackBody, current_user: User = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    c = _scoped(candidate_id, current_user, db)
    if body.feedback_type == "POSITIVE": c.positive_feedback_count = (c.positive_feedback_count or 0) + 1
    else: c.negative_feedback_count = (c.negative_feedback_count or 0) + 1
    log.info("learning operation=feedback status=success college_id=%s candidate_id=%s", c.college_id, c.id)
    db.commit(); return _item(c)

