"Production database preflight checks. Never mutates schema or data."
from __future__ import annotations
import os
from sqlalchemy import create_engine, inspect, text
REQUIRED_TABLES = {"colleges", "users", "conversations", "messages", "documents", "document_chunks", "ait_entities", "website_snapshots"}

def main() -> int:
    url = os.getenv("DATABASE_URL", "")
    if not url.startswith(("postgresql://", "postgresql+psycopg://", "postgresql+psycopg2://")):
        print("BLOCKED DATABASE_URL is not PostgreSQL")
        return 2
    engine = create_engine(url, pool_pre_ping=True)
    with engine.connect() as conn:
        inspector = inspect(conn)
        tables = set(inspector.get_table_names())
        missing = sorted(REQUIRED_TABLES - tables)
        vector = conn.execute(text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname='vector')")).scalar()
        revision = conn.execute(text("SELECT version_num FROM alembic_version")).scalar() if "alembic_version" in tables else None
    if missing:
        print(f"FAIL missing_tables={','.join(missing)}")
        return 1
    if not vector:
        print("FAIL pgvector_extension_missing")
        return 1
    print(f"PASS postgres_tables={len(tables)} pgvector=available alembic_revision={revision or 'unknown'}")
    return 0
if __name__ == "__main__": raise SystemExit(main())
