"""User Database Repository.

Provides encapsulated data access logic for the User entity.
"""

import uuid
from dataclasses import dataclass, field
from typing import List, Optional
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User


@dataclass(frozen=True)
class AuthUserLookup:
    """Minimal account fields required by authentication flows."""

    id: uuid.UUID
    email: str
    hashed_password: str = field(repr=False)
    full_name: str
    role: str
    is_verified: bool
    is_active: bool


class UserRepository:
    """Data access repository for users."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Fetches a user record by primary key."""
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_auth_account_by_email(self, email: str) -> Optional[AuthUserLookup]:
        """Loads only authentication fields from the dedicated lookup function."""
        normalized_email = email.lower().strip()
        result = await self.session.execute(
            text(
                "SELECT id, email, hashed_password, full_name, role, is_verified, is_active "
                "FROM public.lookup_user_by_email_for_auth(:email)"
            ),
            {"email": normalized_email},
        )
        row = result.mappings().one_or_none()
        return AuthUserLookup(**row) if row else None

    async def list_users(self, limit: int = 50, offset: int = 0) -> List[User]:
        """Lists platform users with pagination."""
        result = await self.session.execute(
            select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def create(self, user: User) -> User:
        """Persists a new user record."""
        self.session.add(user)
        await self.session.flush()
        return user

    async def update(self, user: User) -> User:
        """Flushes user updates to the active transaction."""
        await self.session.flush()
        return user

