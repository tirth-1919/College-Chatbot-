"""FastAPI Authentication and Role-Based Authorization Dependencies.

Validates JWT bearer tokens and enforces role restrictions on protected endpoints.

After successfully resolving the authenticated ``User``, ``get_current_user``
sets three transaction-local PostgreSQL GUCs via ``set_rls_context()``:

  - ``app.current_user_id``   — the authenticated user's UUID
  - ``app.is_super_admin``    — True only for SUPER_ADMIN role
  - ``app.current_college_id`` — left empty here; set by tenant dependencies
                                 after college membership is verified

This satisfies the RLS functions ``current_app_user_id()`` and
``is_platform_super_admin()`` for every request that passes through auth.
"""

import uuid
from typing import Callable, List, Optional
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db, set_rls_context
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.security.jwt import decode_token

# HTTP Bearer scheme extractor
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    auth_credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    session: AsyncSession = Depends(get_db),
) -> User:
    """Extracts and validates the JWT bearer token, returning the authenticated User.

    After resolving the user, sets transaction-local GUCs:
      - ``app.current_user_id``
      - ``app.is_super_admin``
    College GUC (``app.current_college_id``) is set by tenant dependencies.
    """
    if not auth_credentials or not auth_credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication bearer token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_payload = decode_token(auth_credentials.credentials)
    if not token_payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, malformed, or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if token_payload.get("token_type", "access") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = token_payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token subject missing.",
        )

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token subject is not a valid UUID.",
        )

    # Bind the verified token subject and role before loading the user row.
    # Super-admin profile reads must see the account through RLS.
    token_role = str(token_payload.get("role") or "")
    # If the access token already contains an assigned college_id claim (standard for
    # COLLEGE_ADMIN, STUDENT, etc.), preserve it immediately rather than resetting to None.
    token_college_id_str = token_payload.get("college_id")
    token_college_id = None
    if token_college_id_str:
        try:
            token_college_id = uuid.UUID(str(token_college_id_str))
        except (ValueError, TypeError):
            token_college_id = None

    await set_rls_context(
        session,
        college_id=token_college_id,
        user_id=user_id,
        is_super_admin=(token_role.upper() == "SUPER_ADMIN"),
    )

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    if not user:
        # RLS can hide a valid profile on an existing deployment. Resolve it
        # through the narrow auth lookup, and bind it to every signed identity
        # claim before allowing the request to continue.
        token_email = token_payload.get("email")
        auth_lookup = (
            await user_repo.get_auth_account_by_email(token_email)
            if isinstance(token_email, str) and token_email.strip()
            else None
        )
        if (
            auth_lookup
            and auth_lookup.id == user_id
            and auth_lookup.role == token_role
            and auth_lookup.is_active
        ):
            user = User(
                id=auth_lookup.id,
                email=auth_lookup.email,
                hashed_password=auth_lookup.hashed_password,
                full_name=auth_lookup.full_name,
                role=auth_lookup.role,
                is_verified=auth_lookup.is_verified,
                is_active=auth_lookup.is_active,
            )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The user associated with this token no longer exists.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your user account is suspended or deactivated.",
        )

    # Set transaction-local RLS context for the current user.
    # Preserves token_college_id if already present; tenant dependencies will further
    # verify college membership for college-scoped routes.
    await set_rls_context(
        session,
        college_id=token_college_id,
        user_id=user.id,
        is_super_admin=(user.role == "SUPER_ADMIN"),
    )

    return user


async def get_optional_current_user(
    auth_credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    session: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Extracts User if a valid JWT is present, or returns None for anonymous visitors."""
    if not auth_credentials or not auth_credentials.credentials:
        return None
    token_payload = decode_token(auth_credentials.credentials)
    if not token_payload:
        return None
    if token_payload.get("token_type", "access") != "access":
        return None
    user_id_str = token_payload.get("sub")
    if not user_id_str:
        return None
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        return None

    token_role = str(token_payload.get("role") or "")
    # If the access token already contains an assigned college_id claim (standard for
    # COLLEGE_ADMIN, STUDENT, etc.), preserve it immediately rather than resetting to None.
    token_college_id_str = token_payload.get("college_id")
    token_college_id = None
    if token_college_id_str:
        try:
            token_college_id = uuid.UUID(str(token_college_id_str))
        except (ValueError, TypeError):
            token_college_id = None

    await set_rls_context(
        session,
        college_id=token_college_id,
        user_id=user_id,
        is_super_admin=(token_role.upper() == "SUPER_ADMIN"),
    )
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    if user and user.is_active:
        # Set RLS context even for optional auth so queries stay tenant-safe
        await set_rls_context(
            session,
            college_id=None,
            user_id=user.id,
            is_super_admin=(user.role == "SUPER_ADMIN"),
        )
        return user
    return None


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensures that the current user has verified their email address."""
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email address to access this resource.",
        )
    return current_user


def require_role(*permitted_roles: str) -> Callable:
    """Factory dependency that restricts route access to specific roles."""

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in permitted_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Requires one of the following roles: {', '.join(permitted_roles)}.",
            )
        return current_user

    return role_checker


# Convenient role-specific dependencies
require_college_admin = require_role("COLLEGE_ADMIN", "SUPER_ADMIN")
require_super_admin = require_role("SUPER_ADMIN")

