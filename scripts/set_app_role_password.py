"""
Set college_app_user password in Supabase and update .env automatically.
Run from project root: python scripts/set_app_role_password.py
"""
import asyncio, os, secrets, re
from pathlib import Path
from dotenv import load_dotenv
import asyncpg

load_dotenv()

# Generate a strong random password
password = secrets.token_urlsafe(32)

db_url = os.environ.get("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://", 1)

async def set_password():
    print("Connecting to Supabase as admin (postgres role)...")
    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute(f"ALTER ROLE college_app_user PASSWORD '{password}'")
        print("[OK] Password set for college_app_user in PostgreSQL.")
    finally:
        await conn.close()

asyncio.run(set_password())

# Update .env file
env_path = Path(".env")
env_text = env_path.read_text(encoding="utf-8")

# Build the new app role URL using same host/db as DATABASE_URL
host_part = db_url.split("@", 1)[1] if "@" in db_url else "db.supabase.co:5432/postgres"
new_url = f"postgresql+asyncpg://college_app_user:{password}@{host_part}"
env_text = re.sub(
    r'DATABASE_APP_ROLE_URL="[^"]*"',
    f'DATABASE_APP_ROLE_URL="{new_url}"',
    env_text,
)
env_path.write_text(env_text, encoding="utf-8")
print(f"[OK] DATABASE_APP_ROLE_URL updated in .env")
print("\nPhase 2 setup complete. Restart the backend to activate RLS enforcement.")

