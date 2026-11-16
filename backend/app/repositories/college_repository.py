"""College Tenant Database Repository.

Provides encapsulated data access logic for College tenants.
"""

import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.college import College


class CollegeRepository:
    """Data access repository for college tenants."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, college_id: uuid.UUID) -> Optional[College]:
        """Fetches a college by unique UUID identifier."""
        result = await self.session.execute(select(College).where(College.id == college_id))
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Optional[College]:
        """Fetches a college by URL-safe slug."""
        result = await self.session.execute(select(College).where(College.slug == slug.lower().strip()))
        return result.scalar_one_or_none()

    async def get_by_domain(self, domain: str) -> Optional[College]:
        """Fetches a college by official domain name."""
        result = await self.session.execute(
            select(College).where(College.official_domain == domain.lower().strip())
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[College]:
        """Fetches a college by official contact email."""
        result = await self.session.execute(
            select(College).where(College.contact_email == email.lower().strip())
        )
        return result.scalar_one_or_none()

    async def find_by_query(self, query_str: str) -> Optional[College]:
        """Finds a college matching query by slug, domain, email, or UUID string."""
        q = query_str.lower().strip()
        try:
            cid = uuid.UUID(q)
            by_id = await self.get_by_id(cid)
            if by_id:
                return by_id
        except ValueError:
            pass

        by_slug = await self.get_by_slug(q)
        if by_slug:
            return by_slug

        by_domain = await self.get_by_domain(q)
        if by_domain:
            return by_domain

        by_email = await self.get_by_email(q)
        if by_email:
            return by_email

        return None

    async def list_colleges(
        self,
        only_approved: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> List[College]:
        """Lists colleges with optional approval filtering."""
        query = select(College).order_by(College.name.asc()).limit(limit).offset(offset)
        if only_approved:
            query = query.where(College.status == "APPROVED", College.is_active.is_(True))
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, college: College) -> College:
        """Persists a new college tenant."""
        self.session.add(college)
        await self.session.flush()
        return college

    async def update(self, college: College) -> College:
        """Flushes updates on an existing college tenant."""
        await self.session.flush()
        return college

