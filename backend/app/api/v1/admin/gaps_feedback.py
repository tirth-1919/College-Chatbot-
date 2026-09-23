"""
Knowledge Gap Center + User Feedback Center admin API (§13-§19, §21-§29, §35, §37-§41).

Tenancy rules:
- college_id is ALWAYS derived from the authenticated user (never from the client).
- COLLEGE_ADMIN sees only their own college's gaps/feedback.
- SUPER_ADMIN has a platform-wide view with optional college filter.
- All important actions are audit-logged via the existing log_admin_audit.
"""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.permissions import get_current_admin_user, log_admin_audit
from backend.app.models.knowledge import KnowledgeGap, MessageFeedback
from backend.app.models.college import ChangeRequest, Notification, College
from backend.app.models.conversation import Conversation, Message
from backend.app.models.user import User
from backend.app.knowledge.gaps import compute_priority, VALID_STATUSES

router = APIRouter(prefix="", tags=["Admin Knowledge Gaps & Feedback"])

VALID_CATEGORIES = {
    "Admissions", "Courses", "Fees", "Faculty", "Departments", "Scholarships",
    "Examinations", "Academic Calendar", "Hostel", "Library", "Transport",
    "Placements", "Events", "Facilities", "Rules", "Contact", "Other",
}

RESOLVED_GAP_STATUSES = {"RESOLVED", "DISMISSED", "DUPLICATE"}


def _tenant_filter(query, model, current_user: User, college_filter: Optional[str]):
    """Apply tenancy: SUPER_ADMIN may filter by college; others locked to own."""
    is_super = (current_user.role or "").upper() == "SUPER_ADMIN"
    if is_super:
        if college_filter and college_filter != "ALL":
            query = query.filter(model.college_id == college_filter)
        return query
    if not current_user.college_id:
        return query.filter(model.college_id == "__none__")  # empty result set
    return query.filter(model.college_id == current_user.college_id)

def _gap_dict(db: Session, g: KnowledgeGap, college_name: Optional[str] = None) -> dict:
    neg = 0
    if g.college_id:
        neg = (
            db.query(func.count(MessageFeedback.id))
            .filter(
                MessageFeedback.college_id == g.college_id,
                MessageFeedback.feedback_type.in_(["NEGATIVE", "REPORT"]),
            )
            .scalar() or 0
        )
    return {
        "id": g.id,
        "college_id": g.college_id,
        "college_name": college_name,
        "query": g.user_query,
        "question": g.user_query,
        "detected_intent": g.detected_intent,
        "intent": g.detected_intent,
        "missing_entity": g.missing_entity,
        "status": g.status or ("RESOLVED" if g.resolved else "OPEN"),
        "resolved": bool(g.resolved),
        "occurrence_count": g.occurrence_count or 1,
        "frequency": g.occurrence_count or 1,  # legacy field name
        "first_seen_at": g.first_seen_at.isoformat() if g.first_seen_at else None,
        "last_seen_at": g.last_seen_at.isoformat() if g.last_seen_at else None,
        "occurred_at": g.occurred_at.isoformat() if g.occurred_at else None,
        "created_at": (g.first_seen_at or g.occurred_at).isoformat() if (g.first_seen_at or g.occurred_at) else None,
        "sample_answer": g.sample_answer,
        "ai_response_summary": (g.sample_answer or "")[:150] or None,  # legacy field name
        "reason": g.reason,
        "category": g.category,
        "course": g.course,
        "academic_year": g.academic_year,
        "priority": compute_priority(g, negative_feedback_count=neg),
        "conversation_id": g.conversation_id,
        "message_id": g.message_id,
        "resolved_at": g.resolved_at.isoformat() if g.resolved_at else None,
    }


def _feedback_dict(f: MessageFeedback, college_name: Optional[str] = None) -> dict:
    return {
        "id": f.id,
        "college_id": f.college_id,
        "college_name": college_name,
        "conversation_id": f.conversation_id,
        "message_id": f.message_id,
        "user_id": f.user_id,
        "feedback_type": f.feedback_type,
        "reason": f.reason,
        "details": f.details,
        "status": f.status,
        "source_type": f.source_type,
        "source_url": f.source_url,
        "grounding_status": f.grounding_status,
        "created_at": f.created_at.isoformat() if f.created_at else None,
    }


def _load_gap(gap_id: str, current_user: User, db: Session) -> KnowledgeGap:
    g = db.query(KnowledgeGap).filter(KnowledgeGap.id == gap_id).first()
    is_super = (current_user.role or "").upper() == "SUPER_ADMIN"
    if not g or (not is_super and g.college_id != current_user.college_id):
        # 404 to avoid leaking other tenants' resources
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge gap not found")
    return g


def _load_feedback(fid: str, current_user: User, db: Session) -> MessageFeedback:
    f = db.query(MessageFeedback).filter(MessageFeedback.id == fid).first()
    is_super = (current_user.role or "").upper() == "SUPER_ADMIN"
    if not f or (not is_super and f.college_id != current_user.college_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")
    return f


# ── Knowledge Gaps ─────────────────────────────────────────

@router.get("/knowledge-gaps")
def list_knowledge_gaps(
    resolved: Optional[bool] = None,
    status_filter: Optional[str] = Query(None, alias="status_filter"),
    category: Optional[str] = None,
    course: Optional[str] = None,
    academic_year: Optional[str] = None,
    search: Optional[str] = None,
    college_id: Optional[str] = Query(None, alias="college_id"),  # SUPER_ADMIN only filter
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=200),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    q = db.query(KnowledgeGap)
    q = _tenant_filter(q, KnowledgeGap, current_user, college_id)

    if resolved is not None:
        # Legacy boolean filter preserved for the old UI
        q = (q.filter(KnowledgeGap.status.in_(RESOLVED_GAP_STATUSES)) if resolved
             else q.filter(~KnowledgeGap.status.in_(RESOLVED_GAP_STATUSES)))
    if status_filter and status_filter.upper() != "ALL":
        q = q.filter(KnowledgeGap.status == status_filter.upper())
    if category:
        q = q.filter(KnowledgeGap.category == category)
    if course:
        q = q.filter(KnowledgeGap.course == course)
    if academic_year:
        q = q.filter(KnowledgeGap.academic_year == academic_year)
    if search:
        q = q.filter(KnowledgeGap.user_query.ilike(f"%{search.lower()}%"))

    total = q.count()
    rows = (q.order_by(KnowledgeGap.occurrence_count.desc(), KnowledgeGap.last_seen_at.desc())
             .offset((page - 1) * per_page).limit(per_page).all())

    college_names = {c.id: c.name for c in db.query(College).all()}

    # Per-status counts for header cards (§13)
    base = db.query(KnowledgeGap.status, func.count(KnowledgeGap.id))
    base = _tenant_filter(base, KnowledgeGap, current_user, college_id)
    status_counts = dict(base.group_by(KnowledgeGap.status).all())

    return {
        "items": [_gap_dict(db, g, college_names.get(g.college_id)) for g in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
        "status_counts": status_counts,
    }


@router.get("/knowledge-gaps/stats")
def gap_stats(
    college_id: Optional[str] = Query(None, alias="college_id"),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Platform or tenant gap analytics (§22) — DB-driven, no hard-coded names."""
    q = db.query(KnowledgeGap)
    q = _tenant_filter(q, KnowledgeGap, current_user, college_id)

    by_status = dict(q.with_entities(KnowledgeGap.status, func.count()).group_by(KnowledgeGap.status).all())
    open_count = sum(v for k, v in by_status.items() if k not in RESOLVED_GAP_STATUSES)

    day_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)  # naive UTC to match SQLite-stored timestamps
    new_today = q.filter(KnowledgeGap.first_seen_at >= day_start).count()

    top = (
        q.filter(~KnowledgeGap.status.in_(RESOLVED_GAP_STATUSES))
        .with_entities(KnowledgeGap.user_query, KnowledgeGap.category, KnowledgeGap.occurrence_count)
        .order_by(KnowledgeGap.occurrence_count.desc())
        .limit(10)
        .all()
    )
    college_rows = (
        db.query(College.name, func.sum(KnowledgeGap.occurrence_count))
        .join(KnowledgeGap, KnowledgeGap.college_id == College.id)
        .filter(~KnowledgeGap.status.in_(RESOLVED_GAP_STATUSES))
        .group_by(College.name)
        .all()
    )
    cat_rows = (
        q.with_entities(KnowledgeGap.category, func.count(KnowledgeGap.id))
        .group_by(KnowledgeGap.category)
        .all()
    )
    return {
        "open_gaps": open_count,
        "new_gaps_today": new_today,
        "by_status": by_status,
        "top_gaps": [{"question": t[0], "category": t[1], "occurrences": t[2]} for t in top],
        "by_college": [{"college": name, "open_gaps": int(cnt or 0)} for name, cnt in college_rows],
        "by_category": [{"category": c or "Uncategorized", "count": cnt} for c, cnt in cat_rows],
    }


@router.get("/knowledge-gaps/{gap_id}")
def get_knowledge_gap(
    gap_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    g = _load_gap(gap_id, current_user, db)
    college = db.query(College).filter(College.id == g.college_id).first() if g.college_id else None
    data = _gap_dict(db, g, college.name if college else None)
    # Representative questions only — no full private chat history (§37)
    reps = []
    if g.conversation_id:
        um = (
            db.query(Message)
            .filter(Message.conversation_id == g.conversation_id, Message.sender == "user")
            .order_by(Message.created_at.desc()).limit(5).all()
        )
        reps = [m.content[:200] for m in um]
    data["representative_questions"] = list({g.user_query, *reps})[:6]
    return data


class GapPatch(BaseModel):
    status: Optional[str] = None
    category: Optional[str] = None
    course: Optional[str] = None
    academic_year: Optional[str] = None
    notes: Optional[str] = None


@router.patch("/knowledge-gaps/{gap_id}")
def update_knowledge_gap(
    gap_id: str,
    req: GapPatch,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    g = _load_gap(gap_id, current_user, db)
    changed = []
    if req.status:
        if req.status.upper() not in VALID_STATUSES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"status must be one of {sorted(VALID_STATUSES)}")
        g.status = req.status.upper()
        if g.status in RESOLVED_GAP_STATUSES:
            g.resolved = True
            g.resolved_at = datetime.now(timezone.utc)
            g.resolved_by = current_user.id
        changed.append("status")
    if req.category:
        if req.category not in VALID_CATEGORIES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"category must be one of {sorted(VALID_CATEGORIES)}")
        g.category = req.category
        changed.append("category")
    if req.course is not None:
        g.course = req.course[:100]
        changed.append("course")
    if req.academic_year is not None:
        g.academic_year = req.academic_year[:20]
        changed.append("academic_year")

    db.commit()
    log_admin_audit(db, current_user, "KNOWLEDGE_GAP_UPDATED", "KNOWLEDGE_GAP",
                    {"gap_id": g.id, "fields": changed}, college_id=g.college_id)
    return _gap_dict(db, g)


@router.post("/knowledge-gaps/{gap_id}/resolve")
def resolve_knowledge_gap(
    gap_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    g = _load_gap(gap_id, current_user, db)
    g.status = "RESOLVED"
    g.resolved = True
    g.resolved_at = datetime.now(timezone.utc)
    g.resolved_by = current_user.id
    db.commit()
    log_admin_audit(db, current_user, "KNOWLEDGE_GAP_RESOLVED", "KNOWLEDGE_GAP",
                    {"gap_id": g.id}, college_id=g.college_id)
    return {"message": "Knowledge gap marked as resolved"}


@router.post("/knowledge-gaps/{gap_id}/dismiss")
def dismiss_knowledge_gap(
    gap_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    g = _load_gap(gap_id, current_user, db)
    g.status = "DISMISSED"
    g.resolved = True
    g.resolved_at = datetime.now(timezone.utc)
    g.resolved_by = current_user.id
    db.commit()
    log_admin_audit(db, current_user, "KNOWLEDGE_GAP_DISMISSED", "KNOWLEDGE_GAP",
                    {"gap_id": g.id}, college_id=g.college_id)
    return {"message": "Knowledge gap dismissed"}


class DraftFromGap(BaseModel):
    title: str
    answer_value: str
    source_url: Optional[str] = None
    source_type: Optional[str] = None  # OFFICIAL_WEBSITE | OFFICIAL_DOCUMENT | COLLEGE_UPLOAD | OTHER
    category: Optional[str] = None
    academic_year: Optional[str] = None
    course: Optional[str] = None
    notes: Optional[str] = None


@router.post("/knowledge-gaps/{gap_id}/create-draft", status_code=status.HTTP_201_CREATED)
def create_draft_from_gap(
    gap_id: str,
    req: DraftFromGap,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Create knowledge draft from a gap (§16/§17/§18/§19).

    Creates a PENDING ChangeRequest — never publishes directly (§20).
    Without an official source the draft is explicitly NOT official (§18).
    """
    g = _load_gap(gap_id, current_user, db)
    is_super = (current_user.role or "").upper() == "SUPER_ADMIN"
    target_college = g.college_id or current_user.college_id
    if not target_college:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Gap has no college context")

    source_type = (req.source_type or "").upper() or None
    if source_type not in (None, "OFFICIAL_WEBSITE", "OFFICIAL_DOCUMENT", "COLLEGE_UPLOAD", "OTHER"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid source_type")

    # A draft without a verified source must never claim officialness (§18)
    is_official = source_type in ("OFFICIAL_WEBSITE", "OFFICIAL_DOCUMENT", "COLLEGE_UPLOAD") and bool(req.source_url)
    authority = ("Official College Website" if source_type == "OFFICIAL_WEBSITE"
                 else "Official Document" if source_type == "OFFICIAL_DOCUMENT"
                 else "Verified College Upload" if source_type == "COLLEGE_UPLOAD"
                 else "Not provided — NOT official")

    new_value = {
        "name": req.title[:255],
        "answer": req.answer_value,
        "source_url": req.source_url,
        "source_type": source_type or "OTHER",
        "is_official": is_official,
        "authority": authority,
        "academic_year": req.academic_year or g.academic_year,
        "course": req.course or g.course,
        "category": req.category or g.category,
        "notes": req.notes,
        "from_gap_id": g.id,
    }
    cr = ChangeRequest(
        college_id=target_college,
        requested_by=current_user.id,
        entity_type="KNOWLEDGE",
        action="CREATE",
        title=req.title[:255],
        new_value=new_value,
        reason=f"Knowledge gap improvement (gap {g.id}): {g.user_query[:200]}",
        status="PENDING",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(cr)
    # Gap moves to IN_PROGRESS while the change request is pending
    g.status = "IN_PROGRESS"
    db.commit()
    db.refresh(cr)

    log_admin_audit(db, current_user, "KNOWLEDGE_DRAFT_CREATED_FROM_GAP", "KNOWLEDGE_GAP",
                    {"gap_id": g.id, "change_request_id": cr.id, "is_official": is_official},
                    college_id=target_college)
    return {"change_request": cr.to_dict(), "gap_status": g.status, "is_official": is_official}


# ── Feedback Center ────────────────────────────────

@router.get("/feedback")
def list_feedback(
    feedback_type: Optional[str] = None,
    reason: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status_filter"),
    search: Optional[str] = None,
    college_id: Optional[str] = Query(None, alias="college_id"),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=200),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    q = db.query(MessageFeedback)
    q = _tenant_filter(q, MessageFeedback, current_user, college_id)
    if feedback_type:
        q = q.filter(MessageFeedback.feedback_type == feedback_type.upper())
    if reason:
        q = q.filter(MessageFeedback.reason == reason.lower())
    if status_filter and status_filter.upper() != "ALL":
        q = q.filter(MessageFeedback.status == status_filter.upper())
    if search:
        like = f"%{search.lower()}%"
        q = q.filter(or_(MessageFeedback.details.ilike(like), MessageFeedback.reason.ilike(like)))

    total = q.count()
    rows = q.order_by(MessageFeedback.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    college_names = {c.id: c.name for c in db.query(College).all()}

    base = db.query(MessageFeedback.feedback_type, func.count(MessageFeedback.id))
    base = _tenant_filter(base, MessageFeedback, current_user, college_id)
    type_counts = dict(base.group_by(MessageFeedback.feedback_type).all())

    return {
        "items": [_feedback_dict(f, college_names.get(f.college_id)) for f in rows],
        "total": total, "page": page, "per_page": per_page,
        "type_counts": type_counts,
    }


@router.get("/feedback/stats")
def feedback_stats(
    college_id: Optional[str] = Query(None, alias="college_id"),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Answer-quality metrics (§28) — counts only, no misleading accuracy %."""
    base = db.query(MessageFeedback)
    base = _tenant_filter(base, MessageFeedback, current_user, college_id)
    counts = dict(base.with_entities(MessageFeedback.feedback_type, func.count())
                  .group_by(MessageFeedback.feedback_type).all())

    gq = db.query(KnowledgeGap)
    gq = _tenant_filter(gq, KnowledgeGap, current_user, college_id)
    unanswered = gq.filter(~KnowledgeGap.status.in_(RESOLVED_GAP_STATUSES)).count()

    return {
        "positive": counts.get("POSITIVE", 0),
        "negative": counts.get("NEGATIVE", 0),
        "reports": counts.get("REPORT", 0),
        "unanswered_gaps": unanswered,
        "resolved_feedback": base.filter(MessageFeedback.status == "RESOLVED").count(),
        "total_feedback": sum(counts.values()),
    }


@router.get("/feedback/{feedback_id}")
def get_feedback_detail(
    feedback_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    f = _load_feedback(feedback_id, current_user, db)
    data = _feedback_dict(f)
    # Question + answer context (privacy-scoped §37: no emails/IPs/personal data)
    user_msg = assistant_msg = None
    if f.message_id:
        assistant_msg = db.query(Message).filter(Message.id == f.message_id).first()
        if assistant_msg:
            user_msg = (
                db.query(Message)
                .filter(Message.conversation_id == assistant_msg.conversation_id,
                        Message.sender == "user",
                        Message.created_at <= assistant_msg.created_at)
                .order_by(Message.created_at.desc()).first()
            )
    data["question"] = user_msg.content[:500] if user_msg else None
    data["answer"] = assistant_msg.content[:500] if assistant_msg else None
    return data


@router.post("/feedback/{feedback_id}/resolve")
def resolve_feedback(
    feedback_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    f = _load_feedback(feedback_id, current_user, db)
    f.status = "RESOLVED"
    db.commit()
    log_admin_audit(db, current_user, "FEEDBACK_REVIEWED", "MESSAGE_FEEDBACK",
                    {"feedback_id": f.id, "action": "RESOLVED"}, college_id=f.college_id)
    return _feedback_dict(f)


@router.post("/feedback/{feedback_id}/dismiss")
def dismiss_feedback(
    feedback_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    f = _load_feedback(feedback_id, current_user, db)
    f.status = "DISMISSED"
    db.commit()
    log_admin_audit(db, current_user, "REPORT_REVIEWED", "MESSAGE_FEEDBACK",
                    {"feedback_id": f.id, "action": "DISMISSED"}, college_id=f.college_id)
    return _feedback_dict(f)
