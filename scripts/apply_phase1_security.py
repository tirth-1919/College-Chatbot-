"""
Apply Phase 1 security migrations: 018, 019, 020
Run from project root: python scripts/apply_phase1_security.py
"""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
import asyncpg

load_dotenv()

db_url = os.environ.get("DATABASE_URL", "")
if db_url.startswith("postgresql+asyncpg://"):
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://", 1)

MIGRATIONS = [
    "database/migrations/018_create_application_role.sql",
    "database/migrations/019_complete_rls_policies.sql",
    "database/migrations/020_revoke_anon_grants.sql",
]

async def apply_migrations():
    print("Connecting to database...")
    conn = await asyncpg.connect(db_url)
    try:
        for path_str in MIGRATIONS:
            p = Path(path_str)
            print(f"\nApplying {p.name} ...")
            sql = p.read_text(encoding="utf-8")
            await conn.execute(sql)
            print(f"  [OK] {p.name}")

        # Verify college_app_user role was created
        result = await conn.fetchrow(
            "SELECT rolname, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = 'college_app_user'"
        )
        if result:
            print(f"\n[VERIFY] college_app_user role:")
            print(f"  rolname     = {result['rolname']}")
            print(f"  rolsuper    = {result['rolsuper']}   (expected: False)")
            print(f"  rolbypassrls= {result['rolbypassrls']} (expected: False)")
        else:
            print("\n[WARN] college_app_user role not found after migration 018!")

        # Verify no anon grants remain on application tables
        anon_grants = await conn.fetch("""
            SELECT table_name, privilege_type, grantee
            FROM information_schema.role_table_grants
            WHERE grantee IN ('anon', 'authenticated')
              AND table_schema = 'public'
            ORDER BY table_name, grantee
        """)
        if anon_grants:
            print(f"\n[WARN] {len(anon_grants)} anon/authenticated grants still exist:")
            for row in anon_grants:
                print(f"  {row['grantee']} -> {row['privilege_type']} ON {row['table_name']}")
        else:
            print("\n[VERIFY] No anon/authenticated grants remain on application tables. [OK]")

        print("\nPhase 1 security migrations applied successfully!")

    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(apply_migrations())
