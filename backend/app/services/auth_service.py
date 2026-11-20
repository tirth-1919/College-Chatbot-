"""Authentication Service.

Implements core authentication business logic: registration, credential validation,
email verification, and JWT issuance with role and tenant claims.
"""

import uuid
from datetime import timedelta
from typing import Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.membership import CollegeMembership
from app.repositories.user_repository import UserRepository
from app.repositories.college_repository import CollegeRepository
from app.repositories.membership_repository import MembershipRepository
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.security.password import hash_password, verify_password
from app.security.jwt import create_access_token, decode_token
from app.core.config import settings
from app.database.session import set_rls_context


class AuthService:
    """Service handling user authentication and registration workflows."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.college_repo = CollegeRepository(session)
        self.membership_repo = MembershipRepository(session)

    async def register(self, req: RegisterRequest) -> Tuple[User, Optional[CollegeMembership]]:
        """Registers a new user and optionally establishes their college membership."""
        normalized_role = req.role.upper()
        if normalized_role not in ("STUDENT", "REGULAR_USER"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Privileged accounts must be created through the approved college onboarding or invitation workflow.",
            )
        normalized_role = "STUDENT"

        # 1. Check for existing email address
        existing_user = await self.user_repo.get_auth_account_by_email(req.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email address already exists.",
            )

        # 2. Create user entity. The transaction context permits only self
        # registration as a non-privileged student.
        user = User(
            id=uuid.uuid4(),
            email=req.email.lower().strip(),
            hashed_password=hash_password(req.password),
            full_name=req.full_name.strip(),
            role=normalized_role,
            is_verified=False,
            is_active=True,
            verification_token=str(uuid.uuid4())[:8],  # 8-char verification code
        )
        await set_rls_context(
            self.session,
            college_id=None,
            user_id=user.id,
            is_super_admin=False,
        )
        await self.user_repo.create(user)

        return user, None

    async def authenticate(self, req: LoginRequest) -> TokenResponse:
        """Authenticates user credentials and issues a signed JWT access token."""
        user = await self.user_repo.get_auth_account_by_email(req.email)
        if not user or not verify_password(req.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password credentials.",
            )

        await set_rls_context(
            self.session,
            college_id=None,
            user_id=user.id,
            is_super_admin=(user.role == "SUPER_ADMIN"),
        )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This user account has been suspended or deactivated.",
            )

        # Resolve and verify associated college membership for College Admins
        college_id: Optional[uuid.UUID] = None
        if user.role == "COLLEGE_ADMIN":
            membership = await self.membership_repo.get_by_user_id(user.id)
            college_id = membership.college_id if membership else None
            if not college_id:
                # The security-definer membership check can resolve the assignment
                # when the ORM query is filtered by the deployed RLS policy.
                colleges = await self.college_repo.list_colleges(
                    only_approved=True,
                    limit=1000,
                )
                for candidate in colleges:
                    if await self.membership_repo.user_belongs_to_college(
                        user.id, candidate.id
                    ):
                        college_id = candidate.id
                        break

            if not college_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No institutional membership associated with this college administrator account.",
                )
            college = await self.college_repo.get_by_id(college_id)
            if not college:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Associated college institution not found.",
                )

            # Institutional Onboarding Gate
            if college.status == "PENDING":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Institutional Onboarding Pending: Your college registration application is currently under review by platform administrators.",
                )
            elif college.status == "REJECTED":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Institutional Onboarding Rejected: Your college application was not approved. Please contact platform support.",
                )
            elif college.status == "SUSPENDED" or not college.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Institutional Workspace Suspended: Your college tenant has been temporarily deactivated.",
                )

        # Generate JWT Access Token & Refresh Token
        access_token = create_access_token(
            subject=str(user.id),
            role=user.role,
            college_id=str(college_id) if college_id else None,
            additional_claims={
                "email": user.email,
                "full_name": user.full_name,
            },
        )
        refresh_token = create_access_token(
            subject=str(user.id),
            role=user.role,
            college_id=str(college_id) if college_id else None,
            expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            additional_claims={"token_type": "refresh"},
        )

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            college_id=college_id,
            is_verified=user.is_verified,
            refresh_token=refresh_token,
        )

    async def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """Validates a refresh token and generates a new access token."""
        payload = decode_token(refresh_token)
        if not payload or payload.get("token_type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid, malformed, or expired refresh token.",
            )

        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject.")

        try:
            user_id = uuid.UUID(user_id_str)
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token subject.",
            ) from exc
        await set_rls_context(
            self.session,
            college_id=None,
            user_id=user_id,
            is_super_admin=False,
        )
        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is deactivated.")

        try:
            college_id = uuid.UUID(payload["college_id"]) if payload.get("college_id") else None
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token tenant claim.",
            ) from exc

        new_access_token = create_access_token(
            subject=str(user.id),
            role=user.role,
            college_id=str(college_id) if college_id else None,
            additional_claims={"email": user.email, "full_name": user.full_name},
        )

        return TokenResponse(
            access_token=new_access_token,
            token_type="bearer",
            expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            college_id=college_id,
            is_verified=user.is_verified,
            refresh_token=refresh_token,
        )

    async def request_password_reset(self, email: str) -> Optional[str]:
        """Generates a secure password reset token."""
        user = await self._load_user_for_email_flow(email)
        if not user:
            # Return None silently to prevent user enumeration
            return None

        reset_token = str(uuid.uuid4())[:8]
        user.verification_token = reset_token
        await self.user_repo.update(user)
        return reset_token

    async def reset_password(self, email: str, token: str, new_password: str) -> bool:
        """Validates password reset token and saves new bcrypt hash."""
        user = await self._load_user_for_email_flow(email)
        if not user or not user.verification_token or user.verification_token != token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired password reset token.",
            )

        user.hashed_password = hash_password(new_password)
        user.verification_token = None
        await self.user_repo.update(user)
        return True

    async def verify_email(self, email: str, token: str) -> bool:
        """Validates email verification token and marks account as verified."""
        user = await self._load_user_for_email_flow(email)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        if user.verification_token != token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification code.")

        await set_rls_context(
            self.session,
            college_id=None,
            user_id=user.id,
            is_super_admin=False,
            allow_email_verification=True,
        )
        user.is_verified = True
        user.verification_token = None
        await self.user_repo.update(user)
        return True

    async def _load_user_for_email_flow(self, email: str) -> Optional[User]:
        """Loads an account row only after binding signed context to its ID."""
        auth_account = await self.user_repo.get_auth_account_by_email(email)
        if not auth_account:
            return None

        await set_rls_context(
            self.session,
            college_id=None,
            user_id=auth_account.id,
            is_super_admin=False,
        )
        return await self.user_repo.get_by_id(auth_account.id)

