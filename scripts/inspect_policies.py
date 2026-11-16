import asyncio, os
from dotenv import load_dotenv
import asyncpg
load_dotenv()
ADMIN_URL = os.environ.get("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://", 1)

async def inspect_user_policies():
    conn = await asyncpg.connect(ADMIN_URL)
    policies = await conn.fetch("""
        SELECT polname, polcmd::text, pg_get_expr(polqual, polrelid) AS using_expr
        FROM pg_policy p
        JOIN pg_class c ON c.oid = p.polrelid
        WHERE c.relname = 'users' AND c.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname='public')
    """)
    print("=== Policies on 'users' ===")
    for p in policies:
        print(f"Policy: {p['polname']} (cmd={p['polcmd']})")
        print(f"  USING: {p['using_expr']}")
    
    # Also check what current_app_user_id() function returns when app.current_user_id is set
    res = await conn.fetchval("""
        SELECT public.current_app_user_id()
    """)
    print(f"\ncurrent_app_user_id() without setting: {res}")
    
    await conn.execute("SELECT set_config('app.current_user_id', 'cccccccc-cccc-cccc-cccc-cccccccccccc', false)")
    res = await conn.fetchval("""
        SELECT public.current_app_user_id()
    """)
    print(f"current_app_user_id() with setting: {res}")
    
    await conn.close()

asyncio.run(inspect_user_policies())

