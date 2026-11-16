import asyncio
import os
import glob
from pathlib import Path
from dotenv import load_dotenv
import asyncpg

load_dotenv()

# Convert SQLAlchemy URL format postgresql+asyncpg:// to postgresql:// for asyncpg
db_url = os.environ.get("DATABASE_URL", "")
if db_url.startswith("postgresql+asyncpg://"):
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://", 1)

async def run_migrations_and_seed():
    print(f"Connecting to database...")
    conn = await asyncpg.connect(db_url)
    try:
        # 1. Run migrations 001 - 017
        migration_files = sorted(glob.glob("database/migrations/*.sql"))
        print(f"Found {len(migration_files)} migration files.")
        for f in migration_files:
            file_name = Path(f).name
            print(f"Running migration: {file_name}...")
            with open(f, "r", encoding="utf-8") as sql_file:
                sql_content = sql_file.read()
            # asyncpg can execute full scripts
            await conn.execute(sql_content)
            print(f"  [OK] {file_name}")

        # 2. Run seed script
        seed_path = "database/seed/development_seed.sql"
        if os.path.exists(seed_path):
            print(f"Running seed file: {seed_path}...")
            with open(seed_path, "r", encoding="utf-8") as sf:
                seed_sql = sf.read()
            await conn.execute(seed_sql)
            print(f"  [OK] Seed data inserted successfully.")

        # 3. Verify users in DB
        rows = await conn.fetch("SELECT email, role, is_active FROM users")
        print("\nRegistered Users in Database:")
        for r in rows:
            print(f"  - {r['email']} ({r['role']}) [Active: {r['is_active']}]")

        print("\nDatabase initialization complete!")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run_migrations_and_seed())

