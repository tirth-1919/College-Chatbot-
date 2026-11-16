"""Student Feedback Collection API Router.

Accepts answer accuracy ratings and commentary categorized by feedback type.
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.models.user import User
from app.models.chat import ChatMessage, ChatSession
from app.models.feedback_support import Feedback
from app.dependencies.auth import get_optional_current_user, require_role
from app.repositories.membership_repository import MembershipRepository
from app.schemas.support_and_analytics import (
    FeedbackCreateRequest,
    FeedbackItemResponse,
)
from app.schemas.common import APIResponse

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.post(
    "",
    response_model=APIResponse[FeedbackItemResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Submit student feedback on answer accuracy",
)
async def submit_feedback(
    req: FeedbackCreateRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Records student rating and optional commentary categorized by feedback issue type."""
    # Lookup message to verify and extract session/college
    msg_stmt = select(ChatMessage).where(ChatMessage.id == req.message_id)
    msg_res = await session.execute(msg_stmt)
    message = msg_res.scalar_one_or_none()
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Referenced chat message not found.")

    session_stmt = select(ChatSession).where(ChatSession.id == message.session_id)
    session_res = await session.execute(session_stmt)
    chat_session = session_res.scalar_one_or_none()

    resolved_college_id = req.college_id or (chat_session.college_id if chat_session else None)
    if not resolved_college_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not resolve college institution.")

    feedback = Feedback(
        id=uuid.uuid4(),
        college_id=resolved_college_id,
        message_id=req.message_id,
        session_id=message.session_id,
        user_id=current_user.id if current_user else None,
        rating=req.rating,
        category=req.category.upper(),
        comments=req.comments,
    )
    session.add(feedback)
    await session.commit()

    return APIResponse(
        success=True,
        message="Feedback recorded successfully",
        data=FeedbackItemResponse.model_validate(feedback),
    )


@router.get(
    "",
    response_model=APIResponse[List[FeedbackItemResponse]],
    summary="List feedback entries for college or platform",
)
async def list_feedback(
    college_id: Optional[uuid.UUID] = Query(None),
    rating: Optional[int] = Query(None, description="1 (helpful) or -1 (unhelpful)"),
    category: Optional[str] = Query(None),
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(require_role("COLLEGE_ADMIN", "SUPER_ADMIN")),
    session: AsyncSession = Depends(get_db),
):
    """Retrieves feedback items scoped to authorized college tenant or platform."""
    resolved_id = college_id
    if current_user.role == "COLLEGE_ADMIN":
        membership_repo = MembershipRepository(session)
        membership = await membership_repo.get_by_user_id(current_user.id)
        if not membership:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No active college assignment found.")
        resolved_id = membership.college_id

    query = select(Feedback).order_by(desc(Feedback.created_at)).limit(limit).offset(offset)
    if resolved_id:
        query = query.where(Feedback.college_id == resolved_id)
    if rating is not None:
        query = query.where(Feedback.rating == rating)
    if category and category.upper() != "ALL":
        query = query.where(Feedback.category == category.upper())

    result = await session.execute(query)
    feedbacks = list(result.scalars().all())

    return APIResponse(
        success=True,
        message=f"Retrieved {len(feedbacks)} feedback records",
        data=[FeedbackItemResponse.model_validate(f) for f in feedbacks],
    )

