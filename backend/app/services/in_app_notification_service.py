"""In-App Notification Management Service.

Handles real-time status alerts for tickets, crawl operations, document OCR,
and administrative knowledge verification events.
"""

import logging
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import select, and_, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notification import InAppNotification

logger = logging.getLogger(__name__)


class InAppNotificationService:
    """Manages creation, retrieval, and status changes of in-app notifications."""

    async def create_notification(
        self,
        user_id: uuid.UUID,
        title: str,
        message: str,
        session: AsyncSession,
        notification_type: str = "INFO",
        college_id: Optional[uuid.UUID] = None,
        link: Optional[str] = None,
    ) -> InAppNotification:
        """Stores a new in-app alert for a specific user."""
        notification = InAppNotification(
            id=uuid.uuid4(),
            user_id=user_id,
            college_id=college_id,
            title=title.strip(),
            message=message.strip(),
            notification_type=notification_type.upper(),
            link=link,
            is_read=False,
        )
        session.add(notification)
        await session.commit()
        return notification

    async def list_notifications(
        self,
        user_id: uuid.UUID,
        session: AsyncSession,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Lists notifications with unread count."""
        # Unread count
        count_stmt = select(func.count(InAppNotification.id)).where(
            and_(
                InAppNotification.user_id == user_id,
                InAppNotification.is_read == False,
            )
        )
        unread_res = await session.execute(count_stmt)
        unread_count = unread_res.scalar() or 0

        # Query items
        query = (
            select(InAppNotification)
            .where(InAppNotification.user_id == user_id)
            .order_by(InAppNotification.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if unread_only:
            query = query.where(InAppNotification.is_read == False)

        result = await session.execute(query)
        items = list(result.scalars().all())

        return {
            "unread_count": unread_count,
            "items": items,
        }

    async def mark_as_read(
        self,
        notification_id: uuid.UUID,
        user_id: uuid.UUID,
        session: AsyncSession,
    ) -> Optional[InAppNotification]:
        """Marks an individual notification as read."""
        stmt = select(InAppNotification).where(
            and_(
                InAppNotification.id == notification_id,
                InAppNotification.user_id == user_id,
            )
        )
        res = await session.execute(stmt)
        item = res.scalar_one_or_none()
        if not item:
            return None

        item.is_read = True
        await session.commit()
        return item

    async def mark_all_as_read(
        self,
        user_id: uuid.UUID,
        session: AsyncSession,
    ) -> int:
        """Marks all pending notifications as read for this user."""
        stmt = (
            update(InAppNotification)
            .where(
                and_(
                    InAppNotification.user_id == user_id,
                    InAppNotification.is_read == False,
                )
            )
            .values(is_read=True)
        )
        res = await session.execute(stmt)
        await session.commit()
        return res.rowcount or 0


in_app_notification_service = InAppNotificationService()

