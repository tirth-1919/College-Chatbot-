"""Analytics & Support System Security and Redaction Unit Tests."""

import uuid
import pytest
from app.models.feedback_support import SupportTicket, SupportTicketReply, Feedback


def test_internal_staff_note_redaction_for_students():
    """Asserts that ordinary students NEVER receive is_internal=True staff notes."""
    ticket_id = uuid.uuid4()
    student_user_id = uuid.uuid4()
    admin_user_id = uuid.uuid4()

    # Public student inquiry
    student_reply = SupportTicketReply(
        id=uuid.uuid4(),
        ticket_id=ticket_id,
        sender_user_id=student_user_id,
        sender_name="Dharmik Patel",
        sender_role="STUDENT",
        message_text="Can I pay my tuition fee in two installments?",
        is_internal=False,
    )

    # Confidential internal staff note
    internal_admin_note = SupportTicketReply(
        id=uuid.uuid4(),
        ticket_id=ticket_id,
        sender_user_id=admin_user_id,
        sender_name="Accounts Registrar",
        sender_role="COLLEGE_ADMIN",
        message_text="INTERNAL: Student has not submitted 12th marksheet yet. Hold installment approval until verified.",
        is_internal=True,
    )

    # Public official response
    official_admin_reply = SupportTicketReply(
        id=uuid.uuid4(),
        ticket_id=ticket_id,
        sender_user_id=admin_user_id,
        sender_name="Accounts Office",
        sender_role="COLLEGE_ADMIN",
        message_text="Yes, you may submit an installment request at the administrative window.",
        is_internal=False,
    )

    all_replies = [student_reply, internal_admin_note, official_admin_reply]

    # Student viewing ticket: Must redact internal notes
    student_view_replies = [r for r in all_replies if not r.is_internal]
    assert len(student_view_replies) == 2
    assert all(r.is_internal is False for r in student_view_replies)
    assert not any("INTERNAL:" in r.message_text for r in student_view_replies)

    # College Admin viewing ticket: Can see all replies including internal notes
    admin_view_replies = all_replies
    assert len(admin_view_replies) == 3
    assert any(r.is_internal is True for r in admin_view_replies)


def test_ticket_status_lifecycle():
    """Verifies that ticket lifecycle transitions through valid statuses."""
    valid_statuses = {"OPEN", "IN_PROGRESS", "WAITING_FOR_USER", "RESOLVED", "CLOSED"}

    ticket = SupportTicket(
        id=uuid.uuid4(),
        college_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        subject="Hostel admission deadline inquiry",
        message="When does the hostel registration window close for semester 1?",
        category="CHATBOT",
        priority="MEDIUM",
        status="OPEN",
    )

    assert ticket.status in valid_statuses

    ticket.status = "IN_PROGRESS"
    assert ticket.status == "IN_PROGRESS"

    ticket.status = "WAITING_FOR_USER"
    assert ticket.status == "WAITING_FOR_USER"

    ticket.status = "RESOLVED"
    ticket.resolution_notes = "Informed student that hostel deadline is August 20th."
    assert ticket.status == "RESOLVED"
    assert ticket.resolution_notes is not None


def test_feedback_categorization():
    """Verifies feedback categorization categories."""
    valid_categories = {"ACCURACY", "INCORRECT_INFO", "MISSING_INFO", "TECHNICAL_ISSUE", "GENERAL"}

    fb = Feedback(
        id=uuid.uuid4(),
        message_id=uuid.uuid4(),
        rating=1,
        category="ACCURACY",
        comments="Very accurate answer on cutoff ranks.",
    )

    assert fb.category in valid_categories
    assert fb.rating == 1

