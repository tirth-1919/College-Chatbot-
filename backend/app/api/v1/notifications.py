"""In-App Notifications API Router.

Provides user-facing notification feeds, unread counters, and mark-as-read actions.
"""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.models.user import User
from app.dependencies.auth import get_current_user
from app.services.in_app_notification_service import in_app_notification_service
from app.schemas.support_and_analytics import (
    NotificationListResponse,
    InAppNotificationResponse,
)
from app.schemas.common import APIResponse

router = APIRouter(prefix="/notifications", tags=["In-App Notifications"])


@router.get(
    "",
    response_model=APIResponse[NotificationListResponse],
    summary="List in-app notifications for authenticated user",
)
async def list_notifications(
    unread_only: bool = Query(False, description="Filter only unread items"),
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Fetches user notification feed with total unread count."""
    res = await in_app_notification_service.list_notifications(
        user_id=current_user.id,
        session=session,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )
    items = [InAppNotificationResponse.model_validate(n) for n in res["items"]]
    data = NotificationListResponse(
        unread_count=res["unread_count"],
        items=items,
    )
    return APIResponse(
        success=True,
        message=f"Retrieved {len(items)} notifications",
        data=data,
    )


@router.patch(
    "/{notification_id}/read",
    response_model=APIResponse[InAppNotificationResponse],
    summary="Mark specific notification as read",
)
async def mark_notification_as_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Marks an individual notification turn as read."""
    updated = await in_app_notification_service.mark_as_read(
        notification_id=notification_id,
        user_id=current_user.id,
        session=session,
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")

    return APIResponse(
        success=True,
        message="Notification marked as read",
        data=InAppNotificationResponse.model_validate(updated),
    )


@router.post(
    "/read-all",
    response_model=APIResponse[int],
    summary="Mark all user notifications as read",
)
async def mark_all_notifications_as_read(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Marks all pending notifications as read for current user."""
    count = await in_app_notification_service.mark_all_as_read(
        user_id=current_user.id,
        session=session,
    )
    return APIResponse(
        success=True,
        message=f"Marked {count} notifications as read",
        data=count,
    )

