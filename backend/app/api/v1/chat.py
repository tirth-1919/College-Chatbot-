from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from backend.app.core.database import get_db
from backend.app.api.v1.auth import get_current_user, get_optional_user
from backend.app.models.user import User
from backend.app.models.conversation import Conversation, Message
from backend.app.chat.orchestrator import chat_orchestrator
from backend.app.chat.streaming import sse_stream_manager
from backend.app.security.sanitizer import sanitizer
from backend.app.security.rate_limiter import rate_limiter

router = APIRouter(prefix="/chat", tags=["Chat"])


def _looks_like_college_name(text: str) -> bool:
    """
    §8: deterministic (no AI) heuristic distinguishing a college-name attempt
    from an ordinary question during onboarding. A name attempt contains a
    college-type keyword ("XYZ Unknown College"), whereas plain chit-chat
    ("hello there") does not. Used only to choose between 'ask again' and
    'couldn't find that college' replies — never to select a college.
    """
    low = (text or "").lower()
    keywords = ("college", "institute", "university", "academy", "school",
                "polytechnic", "vidyalaya", "technology", "technological")
    return any(k in low for k in keywords)

class ChatMessageRequest(BaseModel):
    conversation_id: str
    message: str
    attachments: Optional[List[Dict[str, Any]]] = None

class FeedbackRequest(BaseModel):
    message_id: str
    rating: Optional[int] = None  # 1 thumbs up, -1 thumbs down (legacy compat)
    feedback_text: Optional[str] = None
    # Structured feedback (§3/§4):
    feedback_type: Optional[str] = None  # POSITIVE | NEGATIVE | REPORT
    reason: Optional[str] = None
    details: Optional[str] = None

@router.get("/suggestions")
def get_suggested_prompts():
    """
    Returns authentic, verified prompt suggestions (Section 5).
    Generic multi-college phrasing: no hard-coded college name is assumed
    before the user selects one (§1/§14).
    """
    return [
        {"prompt": "What courses are offered?", "category": "academics", "icon": "GraduationCap"},
        {"prompt": "What are the fees?", "category": "fees", "icon": "BadgeDollarSign"},
        {"prompt": "Show me the library.", "category": "facilities", "icon": "BookOpen"},
        {"prompt": "Who teaches DBMS?", "category": "faculty", "icon": "UserCheck"},
        {"prompt": "Tell me about placements.", "category": "placements", "icon": "Briefcase"},
        {"prompt": "Show campus photos.", "category": "campus", "icon": "Image"}
    ]

@router.post("/stream")
async def stream_chat(
    req: ChatMessageRequest,
    request: Request,
    current_user: User = Depends(get_current_user),  # P0-5: auth required for persistent chat
    db: Session = Depends(get_db)
):
    """
    Typed SSE streaming endpoint for user chat interaction.
    Authentication required. Conversation ownership enforced.
    """
    # P1-9: Rate limiting per authenticated user
    rate_limiter.enforce("chat", request, user_id=current_user.id)

    # 1. Sanitize and inspect
    cleaned_text = sanitizer.sanitize_text(req.message)
    if not cleaned_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message cannot be empty")

    is_suspicious, reason = sanitizer.inspect_prompt_injection(cleaned_text)

    # 2. P0-5 FIX: Verify or create conversation WITH ownership enforcement
    conv = db.query(Conversation).filter(Conversation.id == req.conversation_id).first()
    if not conv:
        # Create new conversation — owned by current user.
        # §5/§12/§67: every NEW conversation starts WITHOUT a college (NULL) and
        # the assistant asks the in-chat onboarding question. No legacy tenant
        # linkage, default preference or frontend value seeds the college — the
        # user's typed selection is resolved server-side from the database.
        conv = Conversation(
            id=req.conversation_id,
            user_id=current_user.id,
            college_id=None,
            title=cleaned_text[:35] + ("..." if len(cleaned_text) > 35 else "")
        )
        db.add(conv)
        db.commit()
    else:
        # P0-5: Ownership check — cannot access another user's conversation
        if conv.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"  # 404 to avoid leaking existence
            )
        # Auto-update title if still default
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

    # 3.5 College-context onboarding / resolution (Part A: resolved BEFORE retrieval).
    # A conversation with NO college context is asked the onboarding question
    # ONCE; a typed college name is resolved from the DATABASE (never from the
    # frontend) and persisted as THIS conversation's context only (§4/§5).
    # Re-asking is avoided because conv.college_id is set after resolution.
    from backend.app.chat.college_context import (
        college_context_manager, ONBOARDING_QUESTION, AMBIGUOUS_THRESHOLD
    )
    has_college_context = conv.college_id is not None

    if not has_college_context:
        res = college_context_manager.resolve_and_persist(
            db, current_user, conv, cleaned_text, set_default=False
        )
        # §8: a message that is clearly a normal question (not a college-name
        # attempt) re-asks the onboarding question; only a plausible college
        # name attempt gets the not-found retry message. Never guess (§38).
        if res["status"] == "NOT_FOUND" and not _looks_like_college_name(cleaned_text):
            reply = ONBOARDING_QUESTION
            res = {"status": "PENDING", "college": None}
        elif res["status"] == "RESOLVED":
            reply = (
                f"🤖 Connected to {res['college'].name}. "
                "What would you like to know?\n\n"
                "You can ask about courses, fees, admissions, facilities and more."
            )
        elif res["status"] == "AMBIGUOUS":
            top = res["candidates"][0] if res["candidates"] else None
            reply = (
                "🤖 I found more than one college matching that name. "
                "Please enter the full college name."
                + (f"\n\nPossible match: {top['name']}" if top else "")
            )
        else:
            reply = (
                "🤖 I couldn’t find that college. Please enter the full college "
                "name or a registered college alias."
            )

        db.refresh(conv)
        message_id = str(__import__("uuid").uuid4())
        assistant_msg = Message(
            id=message_id,
            conversation_id=conv.id,
            sender="assistant",
            content=reply,
            blocks=[{"type": "text", "content": reply}],
            grounding_status="conversational",
            provenance={"college_context": res["status"]},
        )
        db.add(assistant_msg)
        db.commit()
        blocks = assistant_msg.blocks or []
        return StreamingResponse(
            sse_stream_manager.stream_chat_response(
                conversation_id=conv.id,
                message_id=message_id,
                text_content=reply,
                blocks=blocks,
                grounding_status="conversational"
            ),
            media_type="text/event-stream"
        )

    # 3.6 Explicit other-college mention → safe-switch flow (§22, §23, §61, §68).
    # A college name typed inside a normal question is detected here; the
    # conversation's college is NEVER changed silently and the user's default
    # is never touched. Prompt-injection text cannot switch context because
    # switching happens only through the /college-context/switch API.
    if conv.college_id:
        mention = college_context_manager.detect_mention(
            db, cleaned_text, exclude_college_id=conv.college_id
        )
        if mention and mention["status"] == "RESOLVED" and mention["college"]:
            m_college = mention["college"]
            current_college = college_context_manager.get_conversation_college(db, conv)
            reply = (
                f"🤖 You are currently using {current_college.name}, "
                f"but your question mentions {m_college.name}.\n\n"
                f"Would you like to switch this conversation to {m_college.name}?"
            )
            message_id = str(__import__("uuid").uuid4())
            assistant_msg = Message(
                id=message_id,
                conversation_id=conv.id,
                sender="assistant",
                content=reply,
                blocks=[{
                    "type": "text", "content": reply
                }, {
                    "type": "college_switch_prompt",
                    "content": f"Switch to {m_college.name}?",
                    "target_college_id": m_college.id,
                    "target_college_name": m_college.name,
                    "current_college_id": conv.college_id,
                    "current_college_name": current_college.name if current_college else None,
                }],
                grounding_status="conversational",
                provenance={
                    "college_context": "SWITCH_PROMPT",
                    "mentioned_college_id": m_college.id,
                    "current_college_id": conv.college_id,
                },
            )
            db.add(assistant_msg)
            db.commit()
            blocks = assistant_msg.blocks or []
            return StreamingResponse(
                sse_stream_manager.stream_chat_response(
                    conversation_id=conv.id,
                    message_id=message_id,
                    text_content=reply,
                    blocks=blocks,
                    grounding_status="conversational"
                ),
                media_type="text/event-stream"
            )

    # 4. Orchestrate response — authoritative college context resolved
    # server-side (§15/§67) and passed down for tenant-filtered retrieval.
    effective_college_id = college_context_manager.get_effective_college_id(db, current_user, conv)
    result = await chat_orchestrator.process_chat(
        db=db,
        conversation_id=conv.id,
        user_message_text=cleaned_text,
        user_id=current_user.id,
        college_id=effective_college_id,
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
def submit_feedback(
    req: FeedbackRequest,
    current_user: User = Depends(get_current_user),  # P1-7: auth required
    db: Session = Depends(get_db)
):
    """
    Submit feedback on an AI response (§1-§6, §26, §27, §34, §41).

    - POSITIVE (thumbs up), NEGATIVE (thumbs down with reason) or REPORT.
    - One record per (message_id, user_id): repeated clicks UPDATE, not duplicate.
    - college_id is ALWAYS derived from the conversation — never from the client (§5/§40).
    - Feedback NEVER changes conversation/default college context (§6).
    - 'could_not_answer' reasons create/update a Knowledge Gap (§26).
    - 'wrong_college' reports are stored as a high-priority context issue (§27)
      but never switch the college automatically.
    """
    from backend.app.models.knowledge import MessageFeedback
    from backend.app.knowledge.gaps import record_gap
    import uuid as _uuid

    msg = db.query(Message).filter(Message.id == req.message_id, Message.sender == "assistant").first()
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    # Ownership check — only the conversation owner can leave feedback
    conv = db.query(Conversation).filter(
        Conversation.id == msg.conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    # ── Server-derived type: rating maps to POSITIVE/NEGATIVE (§2/§3) ──
    if req.feedback_type:
        ftype = req.feedback_type.upper()
        if ftype not in ("POSITIVE", "NEGATIVE", "REPORT"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="feedback_type must be POSITIVE, NEGATIVE or REPORT")
    elif req.rating == 1:
        ftype = "POSITIVE"
    elif req.rating == -1:
        ftype = "NEGATIVE"
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rating must be 1 (positive) or -1 (negative)")

    # ── Duplicate protection + update-in-place (§41): idempotent per (message,user) ──
    feedback = (
        db.query(MessageFeedback)
        .filter(MessageFeedback.message_id == msg.id, MessageFeedback.user_id == current_user.id)
        .first()
    )
    if feedback is None:
        feedback = MessageFeedback(id=str(_uuid.uuid4()))
        created = True
    else:
        created = False  # update path — user may change 👍 → 👎

    # ── College context: derived ONLY from the conversation (§5) — feedback
    # must not become an instruction that changes the current college (§6). ──
    feedback.college_id = conv.college_id
    feedback.conversation_id = conv.id
    feedback.message_id = msg.id
    feedback.user_id = current_user.id
    feedback.feedback_type = ftype
    feedback.reason = (req.reason or "").lower()[:50] or None
    feedback.details = (req.details or "")[:2000] or None
    # Retain source metadata from the message for troubleshooting (§34)
    provenance = msg.provenance if isinstance(msg.provenance, dict) else {}
    feedback.source_type = provenance.get("source_type")
    feedback.source_url = provenance.get("source_url")
    feedback.grounding_status = msg.grounding_status
    if created:
        db.add(feedback)
    db.commit()

    # ── Knowledge Gap linkage (§26) ──
    gap_created = False
    user_question = None
    prev_user_msg = (
        db.query(Message)
        .filter(Message.conversation_id == conv.id, Message.sender == "user", Message.created_at <= msg.created_at)
        .order_by(Message.created_at.desc())
        .first()
    )
    user_question = prev_user_msg.content if prev_user_msg else None

    if ftype in ("NEGATIVE", "REPORT"):
        if feedback.reason == "could_not_answer" and user_question:
            record_gap(
                db,
                college_id=conv.college_id,
                question=user_question,
                sample_answer=msg.content,
                reason="user_reported_unanswered",
                conversation_id=conv.id,
                message_id=msg.id,
            )
            gap_created = True
        elif feedback.reason == "wrong_college" and user_question:
            # High-priority context issue (§27): routed for review. NEVER switches
            # the conversation or default college automatically.
            record_gap(
                db,
                college_id=conv.college_id,
                question=user_question,
                sample_answer=msg.content,
                reason="wrong_college_report",
                conversation_id=conv.id,
                message_id=msg.id,
            )
            gap_created = True

    return {
        "status": "success",
        "message": "Feedback recorded successfully",
        "feedback_id": feedback.id,
        "feedback_type": ftype,
        "created": created,
        "knowledge_gap_created": gap_created,
        "rating": 1 if ftype == "POSITIVE" else -1,
    }

class SupportRequest(BaseModel):
    conversation_id: str
    message_id: Optional[str] = None
    question: Optional[str] = None


@router.post("/support-request")
def ask_college_support(
    req: SupportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    'Ask College Support' for unanswered questions (§32/§33).

    Reuses the existing Notification system — no duplicate ticket system.
    college_id is derived from the conversation (never the client).
    """
    from backend.app.models.college import Notification

    conv = db.query(Conversation).filter(
        Conversation.id == req.conversation_id, Conversation.user_id == current_user.id
    ).first()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    question = (req.question or "")[:500]
    if not question and req.message_id:
        m = db.query(Message).filter(
            Message.id == req.message_id, Message.conversation_id == conv.id
        ).first()
        question = (m.content or "")[:500] if m else ""
    if not question:
        question = "(no question text captured)"

    # Notify college admins of this college (tenant-scoped)
    admins = db.query(User).filter(
        User.college_id == conv.college_id,
        User.role.in_(["COLLEGE_ADMIN", "ADMIN"]),
        User.is_active == True,
    ).all()
    for a in admins:
        db.add(Notification(
            college_id=conv.college_id,
            user_id=a.id,
            title="Student support request",
            message=f"Question the assistant could not answer: \"{question}\"",
            type="WARNING",
        ))
    db.commit()
    return {"status": "success", "message": "Your question was sent to college support."}
