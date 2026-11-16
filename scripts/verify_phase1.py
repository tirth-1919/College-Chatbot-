"""Quick verification of RLS policies after Phase 1 migrations."""
import asyncio, os
from dotenv import load_dotenv
import asyncpg

load_dotenv()
db_url = os.environ.get("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://", 1)

async def verify():
    conn = await asyncpg.connect(db_url)
    try:
        # 1. Tables with RLS enabled — policy counts
        rows = await conn.fetch("""
            SELECT
                c.relname AS table_name,
                c.relrowsecurity AS rls_enabled,
                COUNT(p.polname) AS policy_count
            FROM pg_class c
            LEFT JOIN pg_policy p ON p.polrelid = c.oid
            WHERE c.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
              AND c.relkind = 'r'
              AND c.relrowsecurity = TRUE
            GROUP BY c.relname, c.relrowsecurity
            ORDER BY c.relname
        """)
        print("\n=== Tables with RLS enabled and their policy counts ===")
        problems = []
        for r in rows:
            status = "OK" if r["policy_count"] > 0 else "ZERO POLICIES!"
            print(f"  {r['table_name']:<35} policies={r['policy_count']}  [{status}]")
            if r["policy_count"] == 0:
                problems.append(r["table_name"])

        # 2. knowledge_chunks policy detail
        kc_policies = await conn.fetch("""
            SELECT polname, polcmd::text, pg_get_expr(polqual, polrelid) AS using_expr
            FROM pg_policy p
            JOIN pg_class c ON c.oid = p.polrelid
            WHERE c.relname = 'knowledge_chunks' AND c.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname='public')
        """)
        print("\n=== knowledge_chunks policy USING expressions ===")
        for p in kc_policies:
            print(f"  Policy: {p['polname']} (cmd={p['polcmd']})")
            print(f"    USING: {p['using_expr']}")

        # 3. college_app_user privilege summary
        priv_rows = await conn.fetch("""
            SELECT table_name, string_agg(privilege_type, ', ' ORDER BY privilege_type) AS privileges
            FROM information_schema.role_table_grants
            WHERE grantee = 'college_app_user' AND table_schema = 'public'
            GROUP BY table_name
            ORDER BY table_name
        """)
        print(f"\n=== college_app_user has grants on {len(priv_rows)} tables ===")
        for r in priv_rows[:5]:
            print(f"  {r['table_name']}: {r['privileges']}")
        if len(priv_rows) > 5:
            print(f"  ... and {len(priv_rows)-5} more tables")

        if problems:
            print(f"\n[WARN] Tables still have ZERO policies: {problems}")
        else:
            print("\n[PASS] All RLS-enabled tables have at least one policy.")

    finally:
        await conn.close()

asyncio.run(verify())
