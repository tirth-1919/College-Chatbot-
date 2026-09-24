"""
Migration: Add connection health fields to colleges table

This migration adds fields to track college connection status and knowledge health:
- connection_status: Overall connection health (CONNECTED_VERIFIED, CONNECTED_PARTIAL, etc.)
- website_last_checked_at, website_last_success_at, website_last_failure_at: Website health tracking
- website_http_status, website_pages_indexed, website_error_message: Website verification details
- knowledge_last_updated_at: Last knowledge update timestamp
- verified_records_count: Count of verified knowledge records
- rag_documents_count: Count of RAG-indexed documents
- broken_sources_count: Count of broken/unreachable sources

This supports the production multi-college requirement that colleges must have
verified knowledge infrastructure before being considered "connected".
"""
from sqlalchemy import text


def upgrade(engine):
    """Add connection health columns to colleges table."""
    with engine.connect() as conn:
        # Check if columns already exist (idempotent migration)
        result = conn.execute(text("PRAGMA table_info(colleges)"))
        existing_columns = {row[1] for row in result.fetchall()}
        
        if "connection_status" not in existing_columns:
            conn.execute(text("""
                ALTER TABLE colleges ADD COLUMN connection_status VARCHAR(30) DEFAULT 'NOT_CONNECTED'
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_colleges_connection_status ON colleges(connection_status)
            """))
        
        if "website_last_checked_at" not in existing_columns:
            conn.execute(text("""
                ALTER TABLE colleges ADD COLUMN website_last_checked_at DATETIME
            """))
        
        if "website_last_success_at" not in existing_columns:
            conn.execute(text("""
                ALTER TABLE colleges ADD COLUMN website_last_success_at DATETIME
            """))
        
        if "website_last_failure_at" not in existing_columns:
            conn.execute(text("""
                ALTER TABLE colleges ADD COLUMN website_last_failure_at DATETIME
            """))
        
        if "website_http_status" not in existing_columns:
            conn.execute(text("""
                ALTER TABLE colleges ADD COLUMN website_http_status INTEGER
            """))
        
        if "website_pages_indexed" not in existing_columns:
            conn.execute(text("""
                ALTER TABLE colleges ADD COLUMN website_pages_indexed INTEGER DEFAULT 0
            """))
        
        if "website_error_message" not in existing_columns:
            conn.execute(text("""
                ALTER TABLE colleges ADD COLUMN website_error_message TEXT
            """))
        
        if "knowledge_last_updated_at" not in existing_columns:
            conn.execute(text("""
                ALTER TABLE colleges ADD COLUMN knowledge_last_updated_at DATETIME
            """))
        
        if "verified_records_count" not in existing_columns:
            conn.execute(text("""
                ALTER TABLE colleges ADD COLUMN verified_records_count INTEGER DEFAULT 0
            """))
        
        if "rag_documents_count" not in existing_columns:
            conn.execute(text("""
                ALTER TABLE colleges ADD COLUMN rag_documents_count INTEGER DEFAULT 0
            """))
        
        if "broken_sources_count" not in existing_columns:
            conn.execute(text("""
                ALTER TABLE colleges ADD COLUMN broken_sources_count INTEGER DEFAULT 0
            """))
        
        conn.commit()
        print("[MIGRATION] Connection health fields added to colleges table")


def downgrade(engine):
    """
    SQLite does not support DROP COLUMN, so downgrade is not implemented.
    In production PostgreSQL, you would drop the columns here.
    """
    print("[MIGRATION] Downgrade not supported for SQLite")


if __name__ == "__main__":
    # Standalone execution for testing
    from backend.app.core.database import engine as db_engine
    upgrade(db_engine)
