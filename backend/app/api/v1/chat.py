"""Student AI Chatbot & Conversation History API Router.

Handles chat session lifecycle, messaging turns, citation grounding, and feedback ratings.
"""

import hashlib
import hmac
import secrets
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Security, status, Request
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db, set_chat_visitor_token, set_rls_context
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage
from app.models.feedback_support import Feedback
from app.repositories.chat_repository import ChatRepository
from app.repositories.college_repository import CollegeRepository
from app.services.rag_service import rag_service
from app.schemas.chat import (
    CreateSessionRequest,
    RenameSessionRequest,
    SendMessageRequest,
    ChatMessageResponse,
    ChatSessionResponse,
    FeedbackRequest,
    FeedbackResponse,
)
from app.schemas.common import APIResponse
from app.dependencies.auth import bearer_scheme, get_current_user
from app.services.tenant_service import TenantService


async def get_optional_chat_user(
    request: Request,
    auth_credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    session: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Treat requests without credentials as anonymous, but never downgrade bad credentials."""
    if not request.headers.get("Authorization"):
        return None

    if not auth_credentials or not auth_credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid chat access credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user = await get_current_user(auth_credentials, session)
    except HTTPException as exc:
        if exc.status_code not in {
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        }:
            raise
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or inactive chat access token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or inactive chat access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def _assert_session_ownership(
    chat_session: ChatSession,
    current_user: Optional[User],
    visitor_token: Optional[str] = None,
) -> None:
    """Hides sessions that the requester is not authorized to access.

    Anonymous requests need the per-session visitor capability token.
    SUPER_ADMIN bypasses ownership only after authentication has verified the account role.
    """
    if current_user is None:
        if (
            chat_session.user_id is None
            and visitor_token
            and chat_session.visitor_token_hash
            and hmac.compare_digest(
                hashlib.sha256(visitor_token.encode("utf-8")).hexdigest(),
                chat_session.visitor_token_hash,
            )
        ):
            return
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found.",
        )
    if current_user.role == "SUPER_ADMIN":
        return
    if chat_session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found.",
        )


def _assert_session_college(chat_session: ChatSession, college_id: uuid.UUID) -> None:
    if chat_session.college_id != college_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found.",
        )


def _requested_college_id(request: Request) -> uuid.UUID:
    raw_college_id = request.headers.get("X-College-ID")
    if not raw_college_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Header 'X-College-ID' is required for chat session access.",
        )
    try:
        return uuid.UUID(str(raw_college_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Header 'X-College-ID' must be a valid UUID.",
        ) from exc


async def _set_chat_context(
    session: AsyncSession,
    college_id: uuid.UUID,
    current_user: Optional[User],
    visitor_token: Optional[str] = None,
) -> None:
    tenant_service = TenantService(session)
    if current_user:
        college = await tenant_service.validate_user_access_to_college(
            current_user, college_id
        )
    else:
        college = await tenant_service.get_active_college(college_id)
    await set_rls_context(
        session,
        college_id=college.id,
        user_id=current_user.id if current_user else None,
        is_super_admin=bool(current_user and current_user.role == "SUPER_ADMIN"),
    )
    await set_chat_visitor_token(session, visitor_token)


router = APIRouter(prefix="/chat", tags=["Student AI Chatbot"])


@router.post(
    "/sessions",
    response_model=APIResponse[ChatSessionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new chat conversation session",
)
async def create_chat_session(
    req: CreateSessionRequest,
    request: Request,
    current_user: Optional[User] = Depends(get_optional_chat_user),
    session: AsyncSession = Depends(get_db),
):
    """Initializes a new conversational session linked to a college institution."""
    request_college_id = _requested_college_id(request)
    if request_college_id != req.college_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Header 'X-College-ID' must match the requested college_id.",
        )

    chat_repo = ChatRepository(session)
    tenant_service = TenantService(session)
    if current_user:
        college = await tenant_service.validate_user_access_to_college(
            current_user, req.college_id
        )
    else:
        college = await tenant_service.get_active_college(req.college_id)
    if not college:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active and approved college institution required to initialize chat.",
        )

    visitor_token = secrets.token_urlsafe(32) if current_user is None else None
    await _set_chat_context(session, college.id, current_user, visitor_token)

    chat_session = ChatSession(
        id=uuid.uuid4(),
        college_id=college.id,
        user_id=current_user.id if current_user else None,
        visitor_token_hash=(
            hashlib.sha256(visitor_token.encode("utf-8")).hexdigest()
            if visitor_token else None
        ),
        session_title=req.session_title or "New Conversation",
        language=req.language,
        is_active=True,
    )

    created = await chat_repo.create_session(chat_session)
    response_data = ChatSessionResponse.model_validate(created)
    response_data.visitor_token = visitor_token
    # Commit before returning 201 so deferred commit errors cannot be reported
    # as a successful session creation by the HTTP access logger.
    await session.commit()
    return APIResponse(
        success=True,
        message="Chat session created successfully",
        data=response_data,
    )


@router.get(
    "/sessions",
    response_model=APIResponse[List[ChatSessionResponse]],
    summary="List student conversation history",
)
async def list_chat_sessions(
    request: Request,
    college_id: Optional[uuid.UUID] = Query(None, description="Optional filter by college"),
    current_user: Optional[User] = Depends(get_optional_chat_user),
    session: AsyncSession = Depends(get_db),
):
    """Retrieves active conversational threads belonging to the student (or empty for anonymous)."""
    requested_college_id = _requested_college_id(request)
    if college_id is not None and college_id != requested_college_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query college_id must match the X-College-ID header.",
        )
    await _set_chat_context(session, requested_college_id, current_user)
    if not current_user:
        return APIResponse(
            success=True,
            message="Anonymous visitor sessions managed locally",
            data=[],
        )
    chat_repo = ChatRepository(session)
    sessions = await chat_repo.list_user_sessions(current_user.id, college_id=requested_college_id)
    return APIResponse(
        success=True,
        message=f"Retrieved {len(sessions)} chat sessions",
        data=[ChatSessionResponse.model_validate(s) for s in sessions],
    )


@router.get(
    "/sessions/{session_id}",
    response_model=APIResponse[ChatSessionResponse],
    summary="Retrieve session message history",
)
async def get_session_history(
    session_id: uuid.UUID,
    request: Request,
    current_user: Optional[User] = Depends(get_optional_chat_user),
    session: AsyncSession = Depends(get_db),
    visitor_token: Optional[str] = Header(None, alias="X-Chat-Visitor-Token"),
):
    """Fetches a specific conversation session along with all turn-by-turn messages."""
    requested_college_id = _requested_college_id(request)
    await _set_chat_context(session, requested_college_id, current_user, visitor_token)
    chat_repo = ChatRepository(session)
    chat_session = await chat_repo.get_session(session_id)
    if not chat_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found.")
    _assert_session_college(chat_session, requested_college_id)
    _assert_session_ownership(chat_session, current_user, visitor_token)

    return APIResponse(
        success=True,
        message="Chat session history retrieved",
        data=ChatSessionResponse.model_validate(chat_session),
    )


@router.patch(
    "/sessions/{session_id}",
    response_model=APIResponse[ChatSessionResponse],
    summary="Rename conversation title",
)
async def rename_chat_session(
    session_id: uuid.UUID,
    req: RenameSessionRequest,
    request: Request,
    current_user: Optional[User] = Depends(get_optional_chat_user),
    session: AsyncSession = Depends(get_db),
    visitor_token: Optional[str] = Header(None, alias="X-Chat-Visitor-Token"),
):
    """Allows student to customize the title of a conversation thread."""
    requested_college_id = _requested_college_id(request)
    await _set_chat_context(session, requested_college_id, current_user, visitor_token)
    chat_repo = ChatRepository(session)
    chat_session = await chat_repo.get_session(session_id)
    if not chat_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found.")
    _assert_session_college(chat_session, requested_college_id)
    _assert_session_ownership(chat_session, current_user, visitor_token)

    chat_session.session_title = req.session_title.strip()
    updated = await chat_repo.update_session(chat_session)

    return APIResponse(
        success=True,
        message="Session title updated",
        data=ChatSessionResponse.model_validate(updated),
    )


@router.delete(
    "/sessions/{session_id}",
    response_model=APIResponse[bool],
    summary="Delete conversation session",
)
async def delete_chat_session(
    session_id: uuid.UUID,
    request: Request,
    current_user: Optional[User] = Depends(get_optional_chat_user),
    session: AsyncSession = Depends(get_db),
    visitor_token: Optional[str] = Header(None, alias="X-Chat-Visitor-Token"),
):
    """Soft-deletes a conversation session from student history."""
    requested_college_id = _requested_college_id(request)
    await _set_chat_context(session, requested_college_id, current_user, visitor_token)
    chat_repo = ChatRepository(session)
    chat_session = await chat_repo.get_session(session_id)
    if not chat_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found.")
    _assert_session_college(chat_session, requested_college_id)
    _assert_session_ownership(chat_session, current_user, visitor_token)

    chat_session.is_active = False
    await chat_repo.update_session(chat_session)

    return APIResponse(
        success=True,
        message="Chat session deleted successfully",
        data=True,
    )


@router.post(
    "/sessions/{session_id}/messages",
    response_model=APIResponse[ChatMessageResponse],
    summary="Send message and receive grounded AI answer",
)
async def send_chat_message(
    session_id: uuid.UUID,
    req: SendMessageRequest,
    request: Request,
    # auth is optional — API contract supports anonymous sessions (no breaking change)
    current_user: Optional[User] = Depends(get_optional_chat_user),
    session: AsyncSession = Depends(get_db),
    visitor_token: Optional[str] = Header(None, alias="X-Chat-Visitor-Token"),
):
    """Submits a user prompt, executes RAG retrieval with tenant isolation, and returns verified AI response."""
    chat_repo = ChatRepository(session)
    college_repo = CollegeRepository(session)

    requested_college_id = _requested_college_id(request)
    await _set_chat_context(session, requested_college_id, current_user, visitor_token)

    chat_session = await chat_repo.get_session(session_id)
    if not chat_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found.")
    _assert_session_college(chat_session, requested_college_id)

    # Ownership check: authenticated users may only send to their own sessions
    _assert_session_ownership(chat_session, current_user, visitor_token)

    college = await college_repo.get_by_id(chat_session.college_id)
    await set_rls_context(
        session,
        college_id=chat_session.college_id,
        user_id=current_user.id if current_user else None,
        is_super_admin=bool(current_user and current_user.role == "SUPER_ADMIN"),
    )
    await set_chat_visitor_token(session, visitor_token)

    # 1. Record User Message Turn
    user_msg = ChatMessage(
        id=uuid.uuid4(),
        session_id=session_id,
        sender_role="user",
        message_text=req.message_text.strip(),
        is_verified=False,
        answer_source_type="OFFICIAL_WEBSITE",
        source_citations=[],
        token_count=len(req.message_text.split()),
        model_used=None,
    )
    await chat_repo.create_message(user_msg)

    # 2. Update session title if default
    if chat_session.session_title == "New Conversation":
        chat_session.session_title = req.message_text.strip()[:40] + ("..." if len(req.message_text) > 40 else "")
        await chat_repo.update_session(chat_session)

    # 3. RAG Answer Generation with Context Continuity
    lang = req.language or chat_session.language or "en"
    rag_result = await rag_service.answer_question(
        college_id=chat_session.college_id,
        query=req.message_text.strip(),
        session=session,
        language=lang,
        college=college,
        session_id=session_id,
    )

    # Prefer actual_model from richer result dict, fall back to model_used
    model_used = rag_result.get("actual_model") or rag_result.get("model_used")

    # Only save assistant message if generation succeeded (not complete failure)
    actual_provider = rag_result.get("actual_provider", "")
    if actual_provider == "UNAVAILABLE":
        # Still persist the message so the user sees the controlled error response
        pass

    assistant_msg = ChatMessage(
        id=uuid.uuid4(),
        session_id=session_id,
        sender_role="assistant",
        message_text=rag_result["answer_text"],
        is_verified=rag_result["is_verified"],
        answer_source_type=rag_result["answer_source_type"],
        source_citations=rag_result["source_citations"],
        token_count=rag_result["token_count"],
        model_used=model_used,
        answer_mode=rag_result.get("answer_mode"),
        actual_provider=rag_result.get("actual_provider"),
        actual_model=rag_result.get("actual_model"),
        fallback_reason=rag_result.get("fallback_reason"),
        attempt_count=rag_result.get("attempt_count", 0),
        request_duration_ms=rag_result.get("request_duration_ms"),
    )
    # Ensure tenant RLS context is active for the assistant response turn
    await set_rls_context(
        session,
        college_id=chat_session.college_id,
        user_id=current_user.id if current_user else None,
        is_super_admin=bool(current_user and current_user.role == "SUPER_ADMIN"),
    )
    await set_chat_visitor_token(session, visitor_token)
    saved_assistant_msg = await chat_repo.create_message(assistant_msg)

    return APIResponse(
        success=True,
        message="Assistant response generated with citations",
        data=ChatMessageResponse.model_validate(saved_assistant_msg),
    )


@router.post(
    "/sessions/{session_id}/stream",
    summary="Stream AI answer using Server-Sent Events (SSE)",
)
async def stream_chat_message(
    session_id: uuid.UUID,
    req: SendMessageRequest,
    request: Request,
    # auth is optional — API contract supports anonymous sessions
    current_user: Optional[User] = Depends(get_optional_chat_user),
    session: AsyncSession = Depends(get_db),
    visitor_token: Optional[str] = Header(None, alias="X-Chat-Visitor-Token"),
):
    """Submits user inquiry and streams tokens via Server-Sent Events (SSE)."""
    requested_college_id = _requested_college_id(request)
    await _set_chat_context(session, requested_college_id, current_user, visitor_token)
    chat_repo = ChatRepository(session)
    college_repo = CollegeRepository(session)

    chat_session = await chat_repo.get_session(session_id)
    if not chat_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found.")
    _assert_session_college(chat_session, requested_college_id)

    # Ownership check: authenticated users may only stream to their own sessions
    _assert_session_ownership(chat_session, current_user, visitor_token)

    college = await college_repo.get_by_id(chat_session.college_id)

    # Record User Message Turn
    user_msg = ChatMessage(
        id=uuid.uuid4(),
        session_id=session_id,
        sender_role="user",
        message_text=req.message_text.strip(),
        is_verified=False,
        answer_source_type="OFFICIAL_WEBSITE",
        source_citations=[],
        token_count=len(req.message_text.split()),
        model_used=None,
    )
    await chat_repo.create_message(user_msg)

    lang = req.language or chat_session.language or "en"
    return StreamingResponse(
        rag_service.stream_answer(
            college_id=chat_session.college_id,
            query=req.message_text.strip(),
            session=session,
            language=lang,
            college=college,
            session_id=session_id,
        ),
        media_type="text/event-stream",
    )


@router.post(
    "/messages/{message_id}/feedback",
    response_model=APIResponse[FeedbackResponse],
    summary="Submit student feedback on answer accuracy",
)
async def submit_message_feedback(
    message_id: uuid.UUID,
    req: FeedbackRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Records student rating (thumbs up/down or 1-5 rating) and optional feedback commentary."""
    requested_college_id = _requested_college_id(request)
    await _set_chat_context(session, requested_college_id, current_user)
    chat_repo = ChatRepository(session)
    msg = await chat_repo.get_message(message_id)
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message turn not found.")

    chat_session = await chat_repo.get_session(msg.session_id)
    if not chat_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found.")
    _assert_session_college(chat_session, requested_college_id)
    _assert_session_ownership(chat_session, current_user)

    feedback = Feedback(
        id=uuid.uuid4(),
        college_id=chat_session.college_id,
        message_id=message_id,
        user_id=current_user.id if current_user else None,
        rating=req.rating,
        comments=req.comments,
    )
    saved_feedback = await chat_repo.create_feedback(feedback)

    return APIResponse(
        success=True,
        message="Feedback submitted successfully",
        data=FeedbackResponse.model_validate(saved_feedback),
    )

