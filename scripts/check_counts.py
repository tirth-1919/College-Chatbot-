import asyncio, os
from dotenv import load_dotenv
import asyncpg
load_dotenv()
ADMIN_URL = os.environ.get("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://", 1)
APP_URL = os.environ.get("DATABASE_APP_ROLE_URL", "").replace("postgresql+asyncpg://", "postgresql://", 1)

async def check_data():
    conn = await asyncpg.connect(ADMIN_URL)
    tables = ['colleges', 'users', 'college_memberships', 'website_sources', 'documents', 'chat_sessions', 'knowledge_chunks']
    print("=== Table row counts under superuser (postgres) ===")
    for t in tables:
        c = await conn.fetchval(f"SELECT COUNT(*) FROM {t}")
        print(f"  {t}: {c}")
    
    users = await conn.fetch("SELECT id, email, role FROM users")
    print("\n=== Users in DB ===")
    for u in users:
        print(f"  {u['id']} | {u['email']} | {u['role']}")
        
    mems = await conn.fetch("SELECT college_id, user_id, role_in_college FROM college_memberships")
    print("\n=== Memberships in DB ===")
    for m in mems:
        print(f"  college={m['college_id']} | user={m['user_id']} | role={m['role_in_college']}")
        
    await conn.close()

    # Now test with college_app_user using real user IDs
    print("\n=== Testing users table visibility with college_app_user ===")
    app_conn = await asyncpg.connect(APP_URL)
    ait_admin_id = "22222222-aaaa-aaaa-aaaa-aaaaaaaaaaaa" # let's see real user ids
    # Let's run and print
    await app_conn.close()

asyncio.run(check_data())

