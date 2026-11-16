"""Platform & Institutional Analytics API Router.

Computes real, database-backed telemetry metrics with date filtering,
question frequency distributions, unanswered query tracking, and AI token analytics.
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.models.user import User
from app.dependencies.auth import get_current_user, require_super_admin, require_role
from app.repositories.membership_repository import MembershipRepository
from app.services.analytics_service import analytics_service
from app.schemas.support_and_analytics import (
    PlatformAnalyticsResponse,
    CollegeAnalyticsDetailResponse,
    QuestionFrequencyItem,
    UnansweredQuestionItem,
    AIUsageMetrics,
)
from app.schemas.common import APIResponse

router = APIRouter(prefix="/analytics", tags=["Analytics & Telemetry"])


@router.get(
    "/platform",
    response_model=APIResponse[PlatformAnalyticsResponse],
    summary="Get platform-wide analytics (Super Admin only)",
)
async def get_platform_analytics(
    time_range: str = Query("30D", description="TODAY, 7D, 30D, 90D"),
    current_admin: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
):
    """Aggregates platform-wide colleges, users, questions, knowledge size, and AI token metrics."""
    data = await analytics_service.get_platform_analytics(
        time_range=time_range,
        session=session,
    )
    return APIResponse(
        success=True,
        message="Platform analytics retrieved",
        data=data,
    )


@router.get(
    "/college",
    response_model=APIResponse[CollegeAnalyticsDetailResponse],
    summary="Get college-scoped analytics (College Admin & Super Admin)",
)
async def get_college_analytics(
    college_id: Optional[uuid.UUID] = Query(None, description="Target college ID"),
    time_range: str = Query("30D", description="TODAY, 7D, 30D, 90D"),
    current_user: User = Depends(require_role("COLLEGE_ADMIN", "SUPER_ADMIN")),
    session: AsyncSession = Depends(get_db),
):
    """Retrieves analytics scoped strictly to the authorized college institution."""
    resolved_college_id = college_id
    if current_user.role == "COLLEGE_ADMIN":
        membership_repo = MembershipRepository(session)
        membership = await membership_repo.get_by_user_id(current_user.id)
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access Denied: No active college assignment found.",
            )
        resolved_college_id = membership.college_id

    if not resolved_college_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="college_id parameter is required.",
        )

    data = await analytics_service.get_college_analytics(
        college_id=resolved_college_id,
        time_range=time_range,
        session=session,
    )
    return APIResponse(
        success=True,
        message="College analytics loaded",
        data=data,
    )


@router.get(
    "/questions",
    response_model=APIResponse[List[QuestionFrequencyItem]],
    summary="List frequently asked student questions",
)
async def get_frequently_asked_questions(
    college_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(10, le=50),
    current_user: User = Depends(require_role("COLLEGE_ADMIN", "SUPER_ADMIN")),
    session: AsyncSession = Depends(get_db),
):
    """Aggregates frequently asked questions for knowledge base refinement."""
    resolved_id = college_id
    if current_user.role == "COLLEGE_ADMIN":
        membership_repo = MembershipRepository(session)
        membership = await membership_repo.get_by_user_id(current_user.id)
        if membership:
            resolved_id = membership.college_id

    items = await analytics_service.get_frequently_asked_questions(
        college_id=resolved_id,
        limit=limit,
        session=session,
    )
    return APIResponse(
        success=True,
        message=f"Retrieved {len(items)} popular inquiries",
        data=items,
    )


@router.get(
    "/unanswered-questions",
    response_model=APIResponse[List[UnansweredQuestionItem]],
    summary="List questions where reliable knowledge was missing",
)
async def get_unanswered_questions(
    college_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(10, le=50),
    current_user: User = Depends(require_role("COLLEGE_ADMIN", "SUPER_ADMIN")),
    session: AsyncSession = Depends(get_db),
):
    """Identifies questions that received NO_RELIABLE_INFORMATION or negative feedback."""
    resolved_id = college_id
    if current_user.role == "COLLEGE_ADMIN":
        membership_repo = MembershipRepository(session)
        membership = await membership_repo.get_by_user_id(current_user.id)
        if membership:
            resolved_id = membership.college_id

    items = await analytics_service.get_unanswered_questions(
        college_id=resolved_id,
        limit=limit,
        session=session,
    )
    return APIResponse(
        success=True,
        message=f"Found {len(items)} unanswered student inquiries",
        data=items,
    )


@router.get(
    "/ai-usage",
    response_model=APIResponse[AIUsageMetrics],
    summary="Get AI provider token consumption and latency metrics",
)
async def get_ai_usage_analytics(
    time_range: str = Query("30D"),
    current_user: User = Depends(require_role("COLLEGE_ADMIN", "SUPER_ADMIN")),
    session: AsyncSession = Depends(get_db),
):
    """Tracks token consumption, average response times, and secondary provider failover rates."""
    data = await analytics_service.get_ai_usage_analytics(session=session)
    return APIResponse(
        success=True,
        message="AI usage analytics retrieved",
        data=data,
    )

