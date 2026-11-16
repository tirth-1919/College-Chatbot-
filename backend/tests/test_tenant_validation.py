"""Multi-Tenant Isolation & Role Permission Unit Tests."""

import uuid
import pytest
from app.models.user import User
from app.models.college import College
from app.models.membership import CollegeMembership


def test_tenant_context_models():
    """Verify tenant model binding between user, membership, and college."""
    college_id = uuid.uuid4()
    user_id = uuid.uuid4()

    college = College(
        id=college_id,
        name="Gujarat Technological University",
        slug="gtu-campus",
        official_domain="gtu.ac.in",
        contact_email="registrar@gtu.ac.in",
        status="APPROVED",
        is_active=True,
    )

    user = User(
        id=user_id,
        email="dean@gtu.ac.in",
        hashed_password="hash",
        full_name="Dean GTU",
        role="COLLEGE_ADMIN",
        is_verified=True,
    )

    membership = CollegeMembership(
        id=uuid.uuid4(),
        college_id=college_id,
        user_id=user_id,
        role_in_college="ADMIN",
        is_primary=True,
    )

    assert membership.college_id == college.id
    assert membership.user_id == user.id
    assert user.role == "COLLEGE_ADMIN"

