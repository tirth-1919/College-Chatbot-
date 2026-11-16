"""Tenant Validation & Authorization Service.

Enforces strict tenant boundaries, resolving college identity and verifying that
users operate strictly within their permitted institution.
"""

import uuid
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.college import College
from app.models.user import User
from app.repositories.college_repository import CollegeRepository
from app.repositories.membership_repository import MembershipRepository


class TenantService:
    """Service enforcing multi-tenant isolation rules."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.college_repo = CollegeRepository(session)
        self.membership_repo = MembershipRepository(session)

    async def get_active_college(self, college_id: uuid.UUID) -> College:
        """Retrieves college tenant and verifies it is active and approved."""
        college = await self.college_repo.get_by_id(college_id)
        if not college:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="College institution not found.",
            )

        if not college.is_active or college.status != "APPROVED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"College '{college.name}' is currently {college.status.lower()} or inactive.",
            )

        return college

    async def validate_user_access_to_college(
        self, user: User, target_college_id: uuid.UUID
    ) -> College:
        """Validates that a user has authorization to access the target college tenant.

        Rules:
        - SUPER_ADMIN: Can access any college tenant platform-wide.
        - COLLEGE_ADMIN: Can only access their assigned college.
        - STUDENT: Can query public information from active colleges.
        """
        college = await self.get_active_college(target_college_id)

        if user.role == "SUPER_ADMIN":
            return college

        if user.role == "COLLEGE_ADMIN":
            membership = await self.membership_repo.get_membership(
                college_id=target_college_id, user_id=user.id
            )
            if not membership:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cross-tenant access denied: You are not authorized for this college.",
                )
            return college

        # Regular students can access active colleges for public chat/reading
        return college

