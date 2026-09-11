from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from backend.app.core.database import get_db
from backend.app.api.v1.auth import get_current_user
from backend.app.models.user import User
from backend.app.models.conversation import Conversation, Message

router = APIRouter(prefix="/conversations", tags=["Conversations"])

class ConversationCreateRequest(BaseModel):
    title: Optional[str] = "New Conversation"

class ConversationUpdateRequest(BaseModel):
    title: Optional[str] = None
    is_pinned: Optional[bool] = None
    is_archived: Optional[bool] = None

@router.get("")
def list_conversations(
    archived: bool = False,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List user conversations, strictly isolated to the authenticated user.
    """
    q = db.query(Conversation).filter(
        Conversation.user_id == current_user.id,
        Conversation.is_archived == archived
    )

    if search:
        q = q.filter(Conversation.title.ilike(f"%{search}%"))

    conversations = q.order_by(Conversation.is_pinned.desc(), Conversation.updated_at.desc()).all()

    return [
        {
            "id": c.id,
            "title": c.title,
            "is_pinned": c.is_pinned,
            "is_archived": c.is_archived,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            "message_count": len(c.messages)
        }
        for c in conversations
    ]

@router.post("", status_code=status.HTTP_201_CREATED)
def create_conversation(
    req: ConversationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conv = Conversation(
        user_id=current_user.id,
        title=req.title or "New Conversation"
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)

    return {
        "id": conv.id,
        "title": conv.title,
        "is_pinned": conv.is_pinned,
        "is_archived": conv.is_archived,
        "created_at": conv.created_at.isoformat()
    }

@router.get("/{conversation_id}")
def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()

    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    messages = [
        {
            "id": m.id,
            "sender": m.sender,
            "content": m.content,
            "blocks": m.blocks or [],
            "language": m.language,
            "intent": m.intent,
            "grounding_status": m.grounding_status,
            "citations": m.citations or [],
            "provenance": m.provenance or {},
            "created_at": m.created_at.isoformat() if m.created_at else None
        }
        for m in conv.messages
    ]

    return {
        "id": conv.id,
        "title": conv.title,
        "is_pinned": conv.is_pinned,
        "is_archived": conv.is_archived,
        "created_at": conv.created_at.isoformat(),
        "messages": messages
    }

@router.patch("/{conversation_id}")
def update_conversation(
    conversation_id: str,
    req: ConversationUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()

    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    if req.title is not None:
        conv.title = req.title.strip()
    if req.is_pinned is not None:
        conv.is_pinned = req.is_pinned
    if req.is_archived is not None:
        conv.is_archived = req.is_archived

    db.commit()
    return {"message": "Conversation updated successfully", "id": conv.id, "title": conv.title}

@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()

    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    db.delete(conv)
    db.commit()
    return {"message": "Conversation deleted successfully", "id": conversation_id}
