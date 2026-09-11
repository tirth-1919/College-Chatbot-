from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.permissions import get_current_admin_user, require_permission, log_admin_audit, PERM_KNOWLEDGE_UPDATE
from backend.app.models.knowledge import KnowledgeGap
from backend.app.models.conversation import Message
from backend.app.models.user import User

router = APIRouter(prefix="", tags=["Admin Knowledge Gaps & Feedback"])

@router.get("/knowledge-gaps")
def list_knowledge_gaps(
    resolved: Optional[bool] = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    query = db.query(KnowledgeGap)
    if resolved is not None:
        query = query.filter(KnowledgeGap.resolved == resolved)

    gaps = query.order_by(KnowledgeGap.occurred_at.desc()).limit(100).all()
    return [
        {
            "id": g.id,
            "query": g.user_query,
            "intent": g.detected_intent,
            "missing_entity": g.missing_entity,
            "resolved": g.resolved,
            "occurred_at": g.occurred_at.isoformat() if g.occurred_at else None
        }
        for g in gaps
    ]

@router.post("/knowledge-gaps/{gap_id}/resolve")
def resolve_knowledge_gap(
    gap_id: str,
    current_user: User = Depends(require_permission(PERM_KNOWLEDGE_UPDATE)),
    db: Session = Depends(get_db)
):
    gap = db.query(KnowledgeGap).filter(KnowledgeGap.id == gap_id).first()
    if not gap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge gap not found")

    gap.resolved = True
    db.commit()

    log_admin_audit(db, current_user, "RESOLVE_KNOWLEDGE_GAP", "KNOWLEDGE_GAP", {"id": gap_id})
    return {"message": "Knowledge gap marked as resolved"}

@router.get("/feedback")
def list_feedback(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    # Retrieve messages with user feedback rating or report blocks
    messages = (
        db.query(Message)
        .filter(Message.sender == "assistant")
        .order_by(Message.created_at.desc())
        .limit(50)
        .all()
    )

    feedback_items = []
    for m in messages:
        feedback_items.append({
            "message_id": m.id,
            "conversation_id": m.conversation_id,
            "content_preview": m.content[:150] + "..." if len(m.content) > 150 else m.content,
            "grounding_status": m.grounding_status,
            "rating": "positive" if m.grounding_status == "verified" else "neutral",
            "created_at": m.created_at.isoformat() if m.created_at else None
        })

    return feedback_items
