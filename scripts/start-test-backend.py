"""Start FastAPI against the isolated test database only.

Usage: python scripts/start-test-backend.py [--port 8010]
"""

import argparse
import asyncio
import os
import secrets
import socket
import sys
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
TEST_ENV_FILE = ROOT_DIR / ".env.test.local"

if not TEST_ENV_FILE.is_file():
    raise SystemExit("FATAL: .env.test.local is required; test backend was not started.")

parser = argparse.ArgumentParser(description="Start the isolated Phase 4.8 test backend.")
parser.add_argument("--port", type=int, default=8010)
args = parser.parse_args()
if not 1 <= args.port <= 65535 or args.port in {8000, 8001, 54322}:
    raise SystemExit("FATAL: use an available application port other than 8000, 8001, or 54322.")

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

_APPLICATION_ENVIRONMENT_KEYS = (
    "ENVIRONMENT",
    "DATABASE_URL",
    "DATABASE_APP_ROLE_URL",
    "DATABASE_URL_SYNC",
    "REDIS_URL",
    "CELERY_BROKER_URL",
    "CELERY_RESULT_BACKEND",
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "JWT_SECRET_KEY",
    "RLS_CONTEXT_SECRET",
    "GEMINI_API_KEY",
    "GEMINI_DEFAULT_MODEL",
    "GEMINI_MODEL_PRIORITY",
    "GEMINI_EMBEDDING_MODEL",
    "SECONDARY_AI_API_KEY",
    "OPENAI_API_KEY",
    "XKIRO_API_KEY",
    "SMTP_PASSWORD",
    "SENTRY_DSN",
    "TEST_BACKEND_URL",
)
for variable in _APPLICATION_ENVIRONMENT_KEYS:
    os.environ.pop(variable, None)

load_dotenv(TEST_ENV_FILE, override=True)

if os.environ.get("ENVIRONMENT", "").strip().lower() != "test":
    raise SystemExit("FATAL: .env.test.local must set ENVIRONMENT=test.")

from tests.config import DATABASE_APP_ROLE_URL, verify_safety_guard

if verify_safety_guard().get("status") != "SAFE":
    raise SystemExit("FATAL: isolated database guard did not confirm SAFE.")

app_database_url = DATABASE_APP_ROLE_URL
parsed_database_url = urlparse(app_database_url)
if (
    parsed_database_url.hostname != "127.0.0.1"
    or parsed_database_url.port != 54322
    or parsed_database_url.path != "/postgres"
    or parsed_database_url.username != "college_app_user"
):
    raise SystemExit("FATAL: app database target is not the required isolated test endpoint.")

os.environ["DATABASE_URL"] = app_database_url
os.environ.pop("DATABASE_URL_SYNC", None)
os.environ["TEST_BACKEND_URL"] = f"http://127.0.0.1:{args.port}"
if not os.environ.get("JWT_SECRET_KEY"):
    os.environ["JWT_SECRET_KEY"] = secrets.token_hex(32)

gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
gemini_configured = bool(gemini_key and gemini_key != "placeholder-gemini-key")
if not gemini_configured:
    raise SystemExit("FATAL: GEMINI_API_KEY is not configured in .env.test.local.")

rls_secret = os.environ.get("RLS_CONTEXT_SECRET", "").strip()
try:
    if len(bytes.fromhex(rls_secret)) != 32:
        raise ValueError
except ValueError:
    raise SystemExit("FATAL: test RLS_CONTEXT_SECRET must be 32 bytes encoded as hexadecimal.")

RLS_TABLES = (
    "colleges",
    "users",
    "college_memberships",
    "knowledge_chunks",
    "extracted_facts",
    "chat_sessions",
    "chat_messages",
)


async def inspect_database(connection):
    from sqlalchemy import text

    identity_result = await connection.execute(
        text(
            """
            SELECT current_database() AS database_name,
                   current_user AS role_name,
                   r.rolsuper AS is_superuser,
                   r.rolbypassrls AS bypasses_rls
            FROM pg_roles AS r
            WHERE r.rolname = current_user
            """
        )
    )
    identity = identity_result.mappings().one()
    if (
        identity["database_name"] != "postgres"
        or identity["role_name"] != "college_app_user"
        or identity["is_superuser"]
        or identity["bypasses_rls"]
    ):
        raise RuntimeError("The live database role does not meet the application-role requirements.")

    tables_result = await connection.execute(
        text(
            """
            SELECT c.relname AS table_name,
                   c.relrowsecurity AS rls_enabled,
                   c.relforcerowsecurity AS rls_forced,
                   owner.rolname AS owner_name,
                   count(p.policyname) AS policy_count
            FROM pg_class AS c
            JOIN pg_namespace AS n ON n.oid = c.relnamespace
            JOIN pg_roles AS owner ON owner.oid = c.relowner
            LEFT JOIN pg_policies AS p
              ON p.schemaname = n.nspname AND p.tablename = c.relname
            WHERE n.nspname = 'public'
              AND c.relkind IN ('r', 'p')
              AND c.relname = ANY(:table_names)
            GROUP BY c.relname, c.relrowsecurity, c.relforcerowsecurity, owner.rolname
            """
        ),
        {"table_names": list(RLS_TABLES)},
    )
    table_rows = {
        row["table_name"]: row for row in tables_result.mappings().all()
    }
    if set(table_rows) != set(RLS_TABLES):
        raise RuntimeError("One or more required tenant tables are missing from the test database.")
    for table_name, row in table_rows.items():
        if not row["rls_enabled"]:
            raise RuntimeError(f"RLS is disabled on required table {table_name}.")
        if row["owner_name"] == identity["role_name"] and not row["rls_forced"]:
            raise RuntimeError(f"The app role owns {table_name} without FORCE ROW LEVEL SECURITY.")
        if table_name in {"chat_sessions", "chat_messages", "knowledge_chunks"} and not row["policy_count"]:
            raise RuntimeError(f"No RLS policy is present on required table {table_name}.")
    return identity, table_rows


async def preflight_database():
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool

    engine = create_async_engine(app_database_url, poolclass=NullPool, echo=False)
    try:
        async with engine.connect() as connection:
            return await inspect_database(connection)
    finally:
        await engine.dispose()


try:
    with socket.socket() as port_probe:
        port_probe.bind(("127.0.0.1", args.port))
except OSError:
    raise SystemExit(f"FATAL: 127.0.0.1:{args.port} is not available; no existing process was stopped.")

try:
    database_identity, database_tables = asyncio.run(preflight_database())
except Exception as exc:
    raise SystemExit(
        f"FATAL: app-role database preflight failed ({type(exc).__name__}); "
        "no superuser fallback was attempted."
    ) from None

print(
    "TEST_DATABASE_PREFLIGHT=PASS "
    f"database={database_identity['database_name']} "
    f"role={database_identity['role_name']} "
    f"superuser={str(database_identity['is_superuser']).lower()} "
    f"bypassrls={str(database_identity['bypasses_rls']).lower()} "
    "endpoint=127.0.0.1:54322"
)
print(f"RLS_ENABLED_TABLES={','.join(sorted(database_tables))}")
print(f"GEMINI_API_KEY_CONFIGURED={str(gemini_configured).lower()}")
print(f"TEST_BACKEND_URL=http://127.0.0.1:{args.port}")

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import uvicorn

from app.core.config import settings
from app.database.session import get_db
from app.main import app

if settings.ENVIRONMENT.strip().lower() != "test":
    raise SystemExit("FATAL: application settings did not load the test environment.")
if settings.DATABASE_APP_ROLE_URL != app_database_url:
    raise SystemExit("FATAL: FastAPI runtime is not configured with DATABASE_APP_ROLE_URL.")
if urlparse(settings.sync_database_url).username != "college_app_user":
    raise SystemExit("FATAL: test runtime contains a non-app database sync URL.")


async def live_database_identity(session: AsyncSession = Depends(get_db)):
    identity_result = await session.execute(
        text(
            """
            SELECT current_database() AS database_name,
                   current_user AS role_name,
                   r.rolsuper AS is_superuser,
                   r.rolbypassrls AS bypasses_rls
            FROM pg_roles AS r
            WHERE r.rolname = current_user
            """
        )
    )
    identity = dict(identity_result.mappings().one())
    _, tables = await inspect_database(session)
    identity["rls_enabled_tables"] = sorted(tables)
    return identity


app.add_api_route(
    "/__test__/database-identity",
    live_database_identity,
    methods=["GET"],
    include_in_schema=False,
)

uvicorn.run(
    app,
    host="127.0.0.1",
    port=args.port,
    log_level="info",
    access_log=False,
)
