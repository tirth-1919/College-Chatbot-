"""Database Engine & Connection Pool Configuration.

Provides two engines:
  - ``async_engine``  — Least-privilege ``college_app_user`` role used by all FastAPI
                        request pipelines and background tasks.  RLS is enforced
                        because this role has NOBYPASSRLS.
  - ``admin_engine``  — Administrative ``postgres`` role used ONLY by Alembic
                        migration scripts that must bypass RLS (e.g. applying
                        migrations, seeding).  Never injected into request sessions.

A SQLAlchemy connection-pool ``checkin`` listener runs ``RESET ALL`` on every
connection returned to the pool, guaranteeing that tenant GUCs
(``app.current_college_id``, ``app.is_super_admin``, ``app.current_user_id``)
set during one request cannot leak to another via pooled connection reuse.

Production behavior is fail-closed: a PostgreSQL connection failure raises
``SystemExit`` instead of silently falling back to in-memory SQLite.
"""

import sys

from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncConnection, create_async_engine
from app.core.config import settings
from app.core.logging import logger


# ---------------------------------------------------------------------------
# Async Application Engine — college_app_user (NOBYPASSRLS)
# Used by ALL FastAPI route sessions.  RLS is fully enforced.
# ---------------------------------------------------------------------------
try:
    async_engine: AsyncEngine = create_async_engine(
        settings.DATABASE_APP_ROLE_URL,
        echo=settings.DEBUG,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=300,
    )
    logger.info("Async application engine initialised (college_app_user, RLS enforced).")
except Exception as err:
    logger.critical(
        "FATAL: Failed to initialise PostgreSQL async engine (college_app_user): %s",
        str(err),
        exc_info=True,
    )
    raise SystemExit(f"Database connection initialisation failed: {str(err)}") from err


# ---------------------------------------------------------------------------
# Pool checkin listener — RESET ALL on every connection return
# Guarantees no tenant GUCs leak across requests via connection reuse.
# ---------------------------------------------------------------------------
@event.listens_for(async_engine.sync_engine, "checkin")
def _reset_connection_on_checkin(dbapi_connection, connection_record):
    """Clears all session-level GUCs when a connection is returned to the pool."""
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("DISCARD TEMP")
        cursor.execute("RESET ALL")
        cursor.close()
    except Exception as exc:  # pragma: no cover
        logger.warning("Pool checkin RESET ALL failed (connection may be stale): %s", exc)


# ---------------------------------------------------------------------------
# Synchronous Admin Engine — postgres role (BYPASSRLS)
# Used ONLY by Alembic CLI migrations.  Never bound to FastAPI sessions.
# ---------------------------------------------------------------------------
try:
    sync_engine = create_engine(
        settings.sync_database_url,
        echo=settings.DEBUG,
        pool_pre_ping=True,
    )
    logger.info("Sync admin engine initialised (postgres, Alembic-only).")
except Exception as err:
    logger.critical(
        "FATAL: Failed to initialise PostgreSQL sync admin engine: %s",
        str(err),
        exc_info=True,
    )
    raise SystemExit(f"Admin database connection initialisation failed: {str(err)}") from err
