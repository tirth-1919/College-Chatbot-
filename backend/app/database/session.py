"""Database Session Factory and FastAPI Dependency Provider.

Manages transaction contexts, commits, rollbacks, and connection closing.

``set_rls_context()`` must be called at the start of every request session
(and every background worker session) to bind the PostgreSQL GUCs that
drive Row-Level Security policies:

  - ``app.current_college_id``  → read by ``current_app_tenant()``
  - ``app.is_super_admin``      → read by ``is_platform_super_admin()``
  - ``app.current_user_id``     → read by ``current_app_user_id()``

All three values are set with ``is_local = TRUE``, meaning they are scoped
to the current *transaction* and are automatically discarded on
COMMIT / ROLLBACK.  Combined with the pool checkin ``RESET ALL`` in
``connection.py``, this provides two independent layers of GUC cleanup.
"""

import base64
import hashlib
import hmac
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)
from app.database.connection import async_engine
from app.core.config import settings

# ---------------------------------------------------------------------------
# Session Factory
# ---------------------------------------------------------------------------

# Session factory for producing async database sessions
AsyncSessionFactory = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# Alias for backward compatibility across background tasks and workers
AsyncSessionLocal = AsyncSessionFactory


# ---------------------------------------------------------------------------
# RLS Context Setter
# ---------------------------------------------------------------------------

async def set_rls_context(
    session: AsyncSession,
    *,
    college_id: Optional[uuid.UUID],
    user_id: Optional[uuid.UUID],
    is_super_admin: bool,
    allow_email_verification: bool = False,
) -> None:
    """Sets signed, transaction-local context for PostgreSQL RLS policies.

    Identity and authorization GUCs are not trusted by themselves. PostgreSQL
    verifies their short-lived HMAC using a key provisioned in a private schema.
    Transaction-local settings are also discarded at commit or rollback.

    Call this once per session immediately after acquiring the session, before
    executing any application queries.

    Args:
        session:        The active AsyncSession for the current request or task.
        college_id:     UUID of the current college tenant, or None for super-admin
                        or unauthenticated requests.
        user_id:        UUID of the authenticated user, or None for anonymous calls.
        is_super_admin: True only for verified SUPER_ADMIN role users.
        allow_email_verification: True only after validating a user's
                        verification token.
    """
    secret = settings.RLS_CONTEXT_SECRET
    if secret is None or not secret.get_secret_value():
        raise RuntimeError("RLS_CONTEXT_SECRET must be configured before opening a database context.")
    try:
        signing_key = bytes.fromhex(secret.get_secret_value())
    except ValueError as exc:
        raise RuntimeError("RLS_CONTEXT_SECRET must be 64 hexadecimal characters.") from exc
    if len(signing_key) != 32:
        raise RuntimeError("RLS_CONTEXT_SECRET must encode exactly 32 random bytes.")

    college_id_str = str(college_id) if college_id else ""
    user_id_str = str(user_id) if user_id else ""
    is_super_str = "1" if is_super_admin else "0"
    email_verification_str = "1" if allow_email_verification else "0"
    expires_at = int(datetime.now(timezone.utc).timestamp()) + 300
    payload = (
        f"v1|{user_id_str}|{college_id_str}|{is_super_str}|"
        f"{email_verification_str}|{expires_at}"
    )
    signature = base64.urlsafe_b64encode(
        hmac.new(
            signing_key,
            payload.encode("utf-8"),
            hashlib.sha256,
        ).digest()
    ).decode("ascii").rstrip("=")
    visitor_token = ""

    await session.execute(
        text(
            "SELECT "
            "  set_config('app.current_college_id', :college_id, true), "
            "  set_config('app.is_super_admin',     :is_super,   true), "
            "  set_config('app.current_user_id',    :user_id,    true), "
            "  set_config('app.email_verification_authorized', :email_verification, true), "
            "  set_config('app.request_context_expires_at', :expires_at, true), "
            "  set_config('app.request_context_signature', :signature, true), "
            "  set_config('app.chat_visitor_token', :visitor_token, true)"
        ),
        {
            "college_id": college_id_str,
            "is_super": is_super_str,
            "user_id": user_id_str,
            "email_verification": email_verification_str,
            "expires_at": str(expires_at),
            "signature": signature,
            "visitor_token": visitor_token,
        },
    )


async def set_chat_visitor_token(session: AsyncSession, token: Optional[str]) -> None:
    """Sets the anonymous-chat bearer capability for the current transaction."""
    await session.execute(
        text("SELECT set_config('app.chat_visitor_token', :visitor_token, true)"),
        {"visitor_token": token or ""},
    )


# ---------------------------------------------------------------------------
# FastAPI Dependency
# ---------------------------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an isolated async database session per request.

    Note: This dependency does NOT set RLS context because it cannot know the
    authenticated user or college without coupling to auth dependencies.
    RLS context is set by ``get_current_user`` (auth.py) and
    ``require_college_tenant_access`` / ``get_authorized_college`` (tenant.py)
    which receive both the session and the validated identity.

    Guarantees automatic session close and rollback on unhandled exceptions.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Tenant-Scoped Session Context Manager (for background workers)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def tenant_session(
    college_id: Optional[uuid.UUID],
    user_id: Optional[uuid.UUID] = None,
    is_super_admin: bool = False,
) -> AsyncGenerator[AsyncSession, None]:
    """Async context manager that opens a session and immediately sets RLS GUCs.

    Use this in background workers, Celery tasks, and service methods that
    create their own sessions (i.e. NOT via the FastAPI ``get_db`` dependency).

    Example::

        async with tenant_session(college_id=college_id) as session:
            # All queries automatically RLS-scoped to college_id
            await session.execute(...)

    Args:
        college_id:     UUID of the tenant to scope the session to.
        user_id:        UUID of the acting user (optional for background jobs).
        is_super_admin: Set True only for super-admin background tasks.
    """
    async with AsyncSessionFactory() as session:
        try:
            await set_rls_context(
                session,
                college_id=college_id,
                user_id=user_id,
                is_super_admin=is_super_admin,
            )
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


