from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from backend.app.core.database import get_db
from backend.app.api.v1.auth import get_optional_user
from backend.app.models.user import User
from backend.app.models.conversation import Conversation, Message
from backend.app.chat.orchestrator import chat_orchestrator
from backend.app.chat.streaming import sse_stream_manager
from backend.app.security.sanitizer import sanitizer

router = APIRouter(prefix="/chat", tags=["Chat"])

class ChatMessageRequest(BaseModel):
    conversation_id: str
    message: str
    attachments: Optional[List[Dict[str, Any]]] = None

class FeedbackRequest(BaseModel):
    message_id: str
    rating: int  # 1 for thumbs up, -1 for thumbs down
    feedback_text: Optional[str] = None

@router.get("/suggestions")
def get_suggested_prompts():
    """
    Returns authentic, verified prompt suggestions (Section 5).
    """
    return [
        {"prompt": "What courses does AIT offer?", "category": "academics", "icon": "GraduationCap"},
        {"prompt": "What are the BCA fees?", "category": "fees", "icon": "BadgeDollarSign"},
        {"prompt": "Show me the AIT library.", "category": "facilities", "icon": "BookOpen"},
        {"prompt": "Who teaches DBMS?", "category": "faculty", "icon": "UserCheck"},
        {"prompt": "Tell me about AIT placements.", "category": "placements", "icon": "Briefcase"},
        {"prompt": "Show AIT campus photos.", "category": "campus", "icon": "Image"}
    ]

@router.post("/stream")
async def stream_chat(
    req: ChatMessageRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Typed SSE streaming endpoint for user chat interaction.
    """
    # 1. Sanitize text and inspect prompt injection
    cleaned_text = sanitizer.sanitize_text(req.message)
    if not cleaned_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message cannot be empty")

    is_suspicious, reason = sanitizer.inspect_prompt_injection(cleaned_text)

    # 2. Verify or create conversation
    conv = db.query(Conversation).filter(Conversation.id == req.conversation_id).first()
    if not conv:
        # Create a conversation automatically if not exists
        user_id = current_user.id if current_user else "anonymous-session"
        conv = Conversation(
            id=req.conversation_id,
            user_id=user_id,
            title=cleaned_text[:35] + ("..." if len(cleaned_text) > 35 else "")
        )
        db.add(conv)
        db.commit()
    else:
        # Auto-update conversation title if it's currently default
        if conv.title in ["New Conversation", "New Chat"]:
            conv.title = cleaned_text[:35] + ("..." if len(cleaned_text) > 35 else "")
            db.commit()

    # 3. Store user message
    user_msg = Message(
        conversation_id=conv.id,
        sender="user",
        content=cleaned_text,
        blocks=[{"type": "text", "content": cleaned_text}]
    )
    db.add(user_msg)
    db.commit()

    # 4. Orchestrate response
    user_id = current_user.id if current_user else None
    result = await chat_orchestrator.process_chat(
        db=db,
        conversation_id=conv.id,
        user_message_text=cleaned_text,
        user_id=user_id,
        attachments=req.attachments
    )

    # 5. Return SSE Stream
    return StreamingResponse(
        sse_stream_manager.stream_chat_response(
            conversation_id=result["conversation_id"],
            message_id=result["message_id"],
            text_content=result["text_content"],
            blocks=result["blocks"],
            grounding_status=result["grounding_status"]
        ),
        media_type="text/event-stream"
    )

@router.post("/feedback")
def submit_feedback(req: FeedbackRequest, db: Session = Depends(get_db)):
    msg = db.query(Message).filter(Message.id == req.message_id).first()
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    return {"status": "success", "message": "Feedback recorded successfully"}
