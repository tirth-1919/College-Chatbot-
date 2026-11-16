"""College Membership Database Repository.

Provides data access logic for College Administrator tenant memberships.
"""

import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.membership import CollegeMembership


class MembershipRepository:
    """Data access repository for college administrative memberships."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_user_id(self, user_id: uuid.UUID) -> Optional[CollegeMembership]:
        """Fetches the primary college membership for a given user."""
        result = await self.session.execute(
            select(CollegeMembership)
            .where(CollegeMembership.user_id == user_id)
            .order_by(CollegeMembership.is_primary.desc())
        )
        return result.scalars().first()

    async def get_membership(
        self, college_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[CollegeMembership]:
        """Fetches an exact college-user membership pair."""
        result = await self.session.execute(
            select(CollegeMembership).where(
                CollegeMembership.college_id == college_id,
                CollegeMembership.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_college(self, college_id: uuid.UUID) -> List[CollegeMembership]:
        """Lists all administrative memberships for a specific college."""
        result = await self.session.execute(
            select(CollegeMembership).where(CollegeMembership.college_id == college_id)
        )
        return list(result.scalars().all())

    async def create(self, membership: CollegeMembership) -> CollegeMembership:
        """Persists a new college membership record."""
        self.session.add(membership)
        await self.session.flush()
        return membership

