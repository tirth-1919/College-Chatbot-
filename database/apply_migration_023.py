"""
One-shot script: Apply migration 023_upgrade_college_profile_metadata.sql
to the Supabase PostgreSQL instance using the admin (postgres) credentials.

Usage:
    python database/apply_migration_023.py

Safe to re-run — every statement uses IF NOT EXISTS.
"""

import asyncio
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Resolve migration SQL path
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
MIGRATION_FILE = SCRIPT_DIR / "migrations" / "023_upgrade_college_profile_metadata.sql"

if not MIGRATION_FILE.exists():
    print(f"[ERROR] Migration file not found: {MIGRATION_FILE}")
    sys.exit(1)

MIGRATION_SQL = MIGRATION_FILE.read_text(encoding="utf-8")

# ---------------------------------------------------------------------------
# Load DATABASE_URL from .env (admin / postgres role — has DDL privileges)
# ---------------------------------------------------------------------------
env_file = SCRIPT_DIR.parent / ".env"
db_url: str = ""

if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("DATABASE_URL="):
            db_url = line.split("=", 1)[1].strip().strip('"').strip("'")
            break

if not db_url:
    db_url = os.environ.get("DATABASE_URL", "")

if not db_url:
    print("[ERROR] DATABASE_URL not found in .env or environment.")
    sys.exit(1)

# asyncpg requires a plain postgresql:// URL (no +asyncpg dialect prefix)
asyncpg_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
print(f"[INFO] Connecting to: {asyncpg_url[:60]}...")

# ---------------------------------------------------------------------------
# Apply migration
# ---------------------------------------------------------------------------
async def run():
    try:
        import asyncpg  # type: ignore
    except ImportError:
        print("[ERROR] asyncpg is not installed. Run: pip install asyncpg")
        sys.exit(1)

    conn = await asyncpg.connect(asyncpg_url)
    try:
        print("[INFO] Applying migration 023...")
        await conn.execute(MIGRATION_SQL)
        print("[OK]  Migration 023 applied successfully.")

        # Verify a sample column landed
        row = await conn.fetchrow(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'colleges' AND column_name = 'short_name'
            """
        )
        if row:
            print(f"[OK]  Column verified: short_name ({row['data_type']})")
        else:
            print("[WARN] short_name column NOT found after migration — check for errors above.")

        # Print a full column count for the colleges table
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'colleges'"
        )
        print(f"[INFO] colleges table now has {count} columns.")

    except Exception as exc:
        print(f"[ERROR] Migration failed: {exc}")
        sys.exit(1)
    finally:
        await conn.close()

asyncio.run(run())
