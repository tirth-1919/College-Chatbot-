import asyncio, os
from dotenv import load_dotenv
import asyncpg
import bcrypt
load_dotenv()
ADMIN_URL = os.environ.get("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://", 1)

async def check_hashes():
    conn = await asyncpg.connect(ADMIN_URL)
    users = await conn.fetch("SELECT email, hashed_password, role, is_active FROM users")
    for u in users:
        hp = u['hashed_password']
        # check against Admin@12345
        try:
            match = bcrypt.checkpw("Admin@12345".encode('utf-8'), hp.encode('utf-8'))
        except Exception as e:
            match = f"ERR: {e}"
        print(f"User: {u['email']} | Hash: {hp[:25]}... | Match Admin@12345: {match}")
    await conn.close()

asyncio.run(check_hashes())
