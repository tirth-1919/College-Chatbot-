"""Support Ticket Management & Threaded Conversation Service.

Enforces strict tenant isolation, role-based ticket ownership,
threaded communication, and admin-only internal note redaction.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.feedback_support import SupportTicket, SupportTicketReply
from app.models.user import User
from app.services.in_app_notification_service import in_app_notification_service

logger = logging.getLogger(__name__)


class SupportService:
    """Manages student inquiry tickets, staff assignment, and conversational resolution."""

    VALID_STATUSES = ["OPEN", "IN_PROGRESS", "WAITING_FOR_USER", "RESOLVED", "CLOSED"]
    VALID_CATEGORIES = ["LOGIN", "CHATBOT", "INCORRECT_ANSWER", "MISSING_INFO", "DOCUMENT", "TECHNICAL", "OTHER"]
    VALID_PRIORITIES = ["LOW", "MEDIUM", "HIGH", "URGENT"]

    async def create_ticket(
        self,
        college_id: uuid.UUID,
        subject: str,
        message: str,
        category: str,
        priority: str,
        student_name: str,
        student_email: str,
        session: AsyncSession,
        user_id: Optional[uuid.UUID] = None,
    ) -> SupportTicket:
        """Creates a new student escalation ticket."""
        norm_category = category.upper() if category.upper() in self.VALID_CATEGORIES else "OTHER"
        norm_priority = priority.upper() if priority.upper() in self.VALID_PRIORITIES else "MEDIUM"

        ticket = SupportTicket(
            id=uuid.uuid4(),
            college_id=college_id,
            user_id=user_id,
            student_name=student_name.strip(),
            student_email=student_email.strip().lower(),
            subject=subject.strip(),
            message=message.strip(),
            category=norm_category,
            priority=norm_priority,
            status="OPEN",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(ticket)
        await session.commit()

        # If user is registered, create an in-app confirmation notification
        if user_id:
            await in_app_notification_service.create_notification(
                user_id=user_id,
                college_id=college_id,
                title="Support Ticket Created",
                message=f"Your ticket '{subject[:40]}' has been opened. Our administration will review it.",
                notification_type="INFO",
                link=f"/support/{ticket.id}",
                session=session,
            )

        return ticket

    async def list_tickets(
        self,
        current_user: User,
        session: AsyncSession,
        college_id: Optional[uuid.UUID] = None,
        status_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[SupportTicket]:
        """Lists tickets with strict multi-tenant boundary checks."""
        query = (
            select(SupportTicket)
            .options(selectinload(SupportTicket.replies))
            .order_by(desc(SupportTicket.updated_at))
            .limit(limit)
            .offset(offset)
        )

        # Enforce Role-Based Scoping
        if current_user.role == "STUDENT":
            query = query.where(SupportTicket.user_id == current_user.id)
        elif current_user.role == "COLLEGE_ADMIN":
            if not college_id:
                raise ValueError("College context required for College Admin support access.")
            query = query.where(SupportTicket.college_id == college_id)
        elif current_user.role == "SUPER_ADMIN":
            if college_id:
                query = query.where(SupportTicket.college_id == college_id)

        if status_filter and status_filter.upper() != "ALL":
            query = query.where(SupportTicket.status == status_filter.upper())
        if category_filter and category_filter.upper() != "ALL":
            query = query.where(SupportTicket.category == category_filter.upper())

        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_ticket_detail(
        self,
        ticket_id: uuid.UUID,
        current_user: User,
        session: AsyncSession,
        authorized_college_id: Optional[uuid.UUID] = None,
    ) -> Optional[Dict[str, Any]]:
        """Fetches full ticket details and filters internal notes if accessed by student."""
        query = (
            select(SupportTicket)
            .where(SupportTicket.id == ticket_id)
            .options(selectinload(SupportTicket.replies))
        )
        res = await session.execute(query)
        ticket = res.scalar_one_or_none()
        if not ticket:
            return None

        # Tenant & Ownership checks
        if current_user.role == "STUDENT" and ticket.user_id != current_user.id:
            return None
        if current_user.role == "COLLEGE_ADMIN" and ticket.college_id != authorized_college_id:
            return None

        # Filter out internal notes for students
        safe_replies = []
        for r in ticket.replies:
            if r.is_internal and current_user.role == "STUDENT":
                continue
            safe_replies.append(r)

        return {
            "ticket": ticket,
            "replies": safe_replies,
        }

    async def add_reply(
        self,
        ticket_id: uuid.UUID,
        current_user: User,
        message_text: str,
        session: AsyncSession,
        is_internal: bool = False,
        authorized_college_id: Optional[uuid.UUID] = None,
    ) -> Optional[SupportTicketReply]:
        """Posts a conversational response turn to a ticket."""
        query = select(SupportTicket).where(SupportTicket.id == ticket_id)
        res = await session.execute(query)
        ticket = res.scalar_one_or_none()
        if not ticket:
            return None

        # Ownership authorization check
        if current_user.role == "STUDENT":
            if ticket.user_id != current_user.id:
                return None
            is_internal = False  # Students cannot post internal notes
            ticket.status = "OPEN"
        elif current_user.role == "COLLEGE_ADMIN":
            if ticket.college_id != authorized_college_id:
                return None
            if not is_internal and ticket.status in ("OPEN", "IN_PROGRESS"):
                ticket.status = "WAITING_FOR_USER"
        elif current_user.role == "SUPER_ADMIN":
            if not is_internal and ticket.status in ("OPEN", "IN_PROGRESS"):
                ticket.status = "WAITING_FOR_USER"

        reply = SupportTicketReply(
            id=uuid.uuid4(),
            ticket_id=ticket.id,
            sender_user_id=current_user.id,
            sender_name=current_user.full_name,
            sender_role=current_user.role,
            message_text=message_text.strip(),
            is_internal=is_internal,
            created_at=datetime.now(timezone.utc),
        )
        session.add(reply)
        ticket.updated_at = datetime.now(timezone.utc)
        await session.commit()

        # Notify student if staff responded (and not an internal note)
        if not is_internal and ticket.user_id and current_user.role in ("COLLEGE_ADMIN", "SUPER_ADMIN"):
            await in_app_notification_service.create_notification(
                user_id=ticket.user_id,
                college_id=ticket.college_id,
                title="Support Ticket Updated",
                message=f"Staff responded to ticket '{ticket.subject[:40]}'.",
                notification_type="INFO",
                link=f"/support/{ticket.id}",
                session=session,
            )

        return reply

    async def update_ticket(
        self,
        ticket_id: uuid.UUID,
        current_user: User,
        session: AsyncSession,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assigned_to_user_id: Optional[uuid.UUID] = None,
        resolution_notes: Optional[str] = None,
        authorized_college_id: Optional[uuid.UUID] = None,
    ) -> Optional[SupportTicket]:
        """Updates ticket lifecycle status, priority, or staff assignment."""
        query = select(SupportTicket).where(SupportTicket.id == ticket_id)
        res = await session.execute(query)
        ticket = res.scalar_one_or_none()
        if not ticket:
            return None

        # Only staff can update status/priority/assignment
        if current_user.role == "STUDENT":
            return None
        if current_user.role == "COLLEGE_ADMIN" and ticket.college_id != authorized_college_id:
            return None

        if status and status.upper() in self.VALID_STATUSES:
            ticket.status = status.upper()
        if priority and priority.upper() in self.VALID_PRIORITIES:
            ticket.priority = priority.upper()
        if assigned_to_user_id is not None:
            ticket.assigned_to_user_id = assigned_to_user_id
        if resolution_notes is not None:
            ticket.resolution_notes = resolution_notes.strip()

        ticket.updated_at = datetime.now(timezone.utc)
        await session.commit()
        return ticket


support_service = SupportService()

