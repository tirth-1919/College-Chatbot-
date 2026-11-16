"""Student Inquiries & Administrative Support Tickets API Router.

Enforces strict tenant isolation, role-based ticket ownership,
threaded messaging, and admin internal note redaction.
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.models.user import User
from app.dependencies.auth import get_current_user, get_optional_current_user
from app.services.support_service import support_service
from app.schemas.support_and_analytics import (
    SupportTicketCreate,
    SupportTicketResponse,
    SupportTicketDetailResponse,
    SupportTicketReplyCreate,
    SupportTicketReplyResponse,
    SupportTicketStatusUpdate,
)
from app.schemas.common import APIResponse

router = APIRouter(prefix="/support", tags=["Support & Inquiries"])


@router.post(
    "/tickets",
    response_model=APIResponse[SupportTicketResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new student support escalation ticket",
)
async def create_support_ticket(
    req: SupportTicketCreate,
    current_user: Optional[User] = Depends(get_optional_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Submits a new student inquiry ticket to the institutional administration."""
    student_name = req.student_name or (current_user.full_name if current_user else "Visitor Student")
    student_email = req.student_email or (current_user.email if current_user else "student@college.edu")

    ticket = await support_service.create_ticket(
        college_id=req.college_id,
        subject=req.subject,
        message=req.message,
        category=req.category,
        priority=req.priority,
        student_name=student_name,
        student_email=student_email,
        session=session,
        user_id=current_user.id if current_user else None,
    )

    return APIResponse(
        success=True,
        message="Support ticket created successfully",
        data=SupportTicketResponse.model_validate(ticket),
    )


@router.get(
    "/tickets",
    response_model=APIResponse[List[SupportTicketResponse]],
    summary="List support tickets with role & tenant isolation",
)
async def list_support_tickets(
    college_id: Optional[uuid.UUID] = Query(None, description="Optional filter by college"),
    status_filter: Optional[str] = Query(None, description="Filter: OPEN, IN_PROGRESS, WAITING_FOR_USER, RESOLVED, CLOSED"),
    category_filter: Optional[str] = Query(None, description="Filter: LOGIN, CHATBOT, INCORRECT_ANSWER, etc."),
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Retrieves tickets scoped to student (own tickets), college admin (own college), or super admin."""
    # Resolve college context for college admin if not passed in query
    c_id = college_id
    if current_user.role == "COLLEGE_ADMIN" and not c_id:
        from app.repositories.membership_repository import MembershipRepository
        mem_repo = MembershipRepository(session)
        membership = await mem_repo.get_by_user_id(current_user.id)
        if membership:
            c_id = membership.college_id

    tickets = await support_service.list_tickets(
        current_user=current_user,
        session=session,
        college_id=c_id,
        status_filter=status_filter,
        category_filter=category_filter,
        limit=limit,
        offset=offset,
    )

    return APIResponse(
        success=True,
        message=f"Retrieved {len(tickets)} support tickets",
        data=[SupportTicketResponse.model_validate(t) for t in tickets],
    )


@router.get(
    "/tickets/{ticket_id}",
    response_model=APIResponse[SupportTicketDetailResponse],
    summary="Get support ticket details and threaded conversation",
)
async def get_ticket_detail(
    ticket_id: uuid.UUID,
    college_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Fetches full ticket details with threaded message turns (internal notes hidden from students)."""
    detail = await support_service.get_ticket_detail(
        ticket_id=ticket_id,
        current_user=current_user,
        session=session,
        authorized_college_id=college_id,
    )
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support ticket not found or access denied.")

    ticket = detail["ticket"]
    safe_replies = detail["replies"]

    resp = SupportTicketDetailResponse.model_validate(ticket)
    resp.replies = [SupportTicketReplyResponse.model_validate(r) for r in safe_replies]
    resp.replies_count = len(safe_replies)

    return APIResponse(
        success=True,
        message="Ticket details retrieved",
        data=resp,
    )


@router.post(
    "/tickets/{ticket_id}/replies",
    response_model=APIResponse[SupportTicketReplyResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Post reply turn to a support ticket",
)
async def add_ticket_reply(
    ticket_id: uuid.UUID,
    req: SupportTicketReplyCreate,
    college_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Adds a message turn to the support ticket discussion."""
    reply = await support_service.add_reply(
        ticket_id=ticket_id,
        current_user=current_user,
        message_text=req.message_text,
        session=session,
        is_internal=req.is_internal,
        authorized_college_id=college_id,
    )
    if not reply:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support ticket not found or access denied.")

    return APIResponse(
        success=True,
        message="Reply posted successfully",
        data=SupportTicketReplyResponse.model_validate(reply),
    )


@router.patch(
    "/tickets/{ticket_id}",
    response_model=APIResponse[SupportTicketResponse],
    summary="Update support ticket status, priority, or assignment",
)
async def update_ticket_status(
    ticket_id: uuid.UUID,
    req: SupportTicketStatusUpdate,
    college_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Allows authorized staff to update ticket lifecycle state, priority, and assigned representative."""
    updated = await support_service.update_ticket(
        ticket_id=ticket_id,
        current_user=current_user,
        session=session,
        status=req.status,
        priority=req.priority,
        assigned_to_user_id=req.assigned_to_user_id,
        resolution_notes=req.resolution_notes,
        authorized_college_id=college_id,
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support ticket not found or access denied.")

    return APIResponse(
        success=True,
        message="Support ticket updated successfully",
        data=SupportTicketResponse.model_validate(updated),
    )

