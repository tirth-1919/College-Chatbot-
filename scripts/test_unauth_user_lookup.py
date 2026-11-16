import asyncio, os
from dotenv import load_dotenv
import asyncpg
load_dotenv()
APP_URL = os.environ.get("DATABASE_APP_ROLE_URL", "").replace("postgresql+asyncpg://", "postgresql://", 1)

async def test_unauth_user_lookup():
    conn = await asyncpg.connect(APP_URL)
    row = await conn.fetchrow("SELECT * FROM users WHERE email = 'student@gmail.com'")
    print(f"Result for student under college_app_user without GUC: {row}")
    row_super = await conn.fetchrow("SELECT * FROM users WHERE email = 'superadmin@platform.com'")
    print(f"Result for superadmin under college_app_user without GUC: {row_super}")
    await conn.close()

asyncio.run(test_unauth_user_lookup())
