"""FastAPI Tenant Validation Dependencies.

Extracts college context from headers/routes and enforces tenant boundaries.

``require_college_tenant_access`` is the primary dependency for all college-
scoped routes.  After verifying that the authenticated user has a valid
membership for the requested college, it sets the transaction-local GUC
``app.current_college_id`` so that every subsequent database query in the
same session is automatically scoped by PostgreSQL RLS policies.

This dependency MUST be used (not bypassed) for any route that accesses
college-scoped tables.  It supersedes the previously dead-code version that
was never wired to any route; all college-admin routes should depend on it.
"""

import uuid
from typing import Optional
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db, set_rls_context
from app.models.college import College
from app.models.user import User
from app.dependencies.auth import get_current_user
from app.services.tenant_service import TenantService


async def get_requested_college_id(
    x_college_id: Optional[str] = Header(None, alias="X-College-ID"),
) -> uuid.UUID:
    """Extracts college ID from the required X-College-ID HTTP header."""
    if not x_college_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Header 'X-College-ID' is required for this college-scoped operation.",
        )
    try:
        return uuid.UUID(x_college_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Header 'X-College-ID' must be a valid UUID.",
        )


async def require_college_tenant_access(
    college_id: uuid.UUID = Depends(get_requested_college_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> College:
    """Enforces that the authenticated user has verified access to the requested college.

    After membership is confirmed, sets the transaction-local GUC
    ``app.current_college_id`` so PostgreSQL RLS policies are activated for
    all subsequent queries in this session.

    For SUPER_ADMIN users the college GUC is set to the requested college (allowing
    full visibility) while ``app.is_super_admin`` remains True (already set by
    ``get_current_user``).
    """
    tenant_service = TenantService(session)
    college = await tenant_service.validate_user_access_to_college(current_user, college_id)

    # Set the transaction-local college GUC AFTER membership verification.
    # We update only college_id; user_id and is_super_admin were already set
    # by get_current_user earlier in this same session.
    await session.execute(
        text("SELECT set_config('app.current_college_id', :college_id, true)"),
        {"college_id": str(college_id)},
    )

    return college

