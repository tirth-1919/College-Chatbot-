"""
Repair migration: fix nullability drift on the physical `colleges` table.

Root cause of the bug this repairs
----------------------------------
The SQLAlchemy model (backend/app/models/college.py) declares
`official_email`, `official_website` and `application_id` as nullable
columns, but the physical SQLite `colleges` table still carries NOT NULL
constraints from an earlier era of the model. `Base.metadata.create_all`
never alters existing tables, so the drift persisted.

Any code that inserts a College without these optional fields fails with
    sqlite3.IntegrityError: NOT NULL constraint failed: colleges.official_website
(e.g. tests/backend college provisioning flow).

This migration rebuilds the `colleges` table with the model's declared
nullability using SQLite's standard copy procedure. It is:
- Non-destructive: every existing row and column value is preserved; the
  backup procedure in migrate_sqlite.py additionally snapshots the DB first.
- Idempotent: if the physical table already matches the model, it is a no-op.
"""
import os
import shutil
from datetime import datetime
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from backend.app.core.config import settings

# Columns the model declares nullable=True but that may still be physically
# NOT NULL. Add entries here if more drift is discovered later.
DRIFTED_NULLABLE_COLUMNS = ("official_email", "official_website", "application_id")

TABLE_DDL = """
CREATE TABLE colleges_new (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50) NOT NULL,
    slug VARCHAR(100) NOT NULL,
    official_email VARCHAR(255),
    official_website VARCHAR(500),
    phone VARCHAR(50),
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100) DEFAULT 'India',
    university_affiliation VARCHAR(255),
    contact_person VARCHAR(255),
    contact_email VARCHAR(255),
    contact_phone VARCHAR(255),
    logo_url VARCHAR(500),
    auth_document_path VARCHAR(500),
    description TEXT,
    additional_info TEXT,
    status VARCHAR(30) NOT NULL,
    registration_status VARCHAR(30) NOT NULL,
    application_id VARCHAR(50),
    rejection_reason TEXT,
    review_notes TEXT,
    timezone VARCHAR(50) DEFAULT 'Asia/Kolkata',
    assistant_name VARCHAR(100) DEFAULT 'AI Assistant',
    welcome_message TEXT,
    primary_color VARCHAR(20) DEFAULT '#0b0a3e',
    secondary_color VARCHAR(20) DEFAULT '#1a2345',
    accent_color VARCHAR(20) DEFAULT '#f08518',
    supported_languages JSON,
    max_users INTEGER,
    max_storage_mb INTEGER,
    max_documents INTEGER,
    max_ai_requests_per_day INTEGER,
    subdomain VARCHAR(100),
    custom_domain VARCHAR(255),
    connection_status VARCHAR(30) DEFAULT 'NOT_CONNECTED',
    website_last_checked_at DATETIME,
    website_last_success_at DATETIME,
    website_last_failure_at DATETIME,
    website_http_status INTEGER,
    website_pages_indexed INTEGER,
    website_error_message TEXT,
    knowledge_last_updated_at DATETIME,
    verified_records_count INTEGER,
    rag_documents_count INTEGER,
    broken_sources_count INTEGER,
    created_at DATETIME,
    updated_at DATETIME,
    created_by VARCHAR(36),
    updated_by VARCHAR(36),
    UNIQUE (code),
    UNIQUE (slug),
    UNIQUE (subdomain),
    UNIQUE (custom_domain),
    UNIQUE (application_id)
)
"""


def repair_colleges_nullability(db: Session) -> bool:
    engine_dialect = db.bind.dialect.name
    if engine_dialect != "sqlite":
        print("[MIGRATION] colleges nullability repair is SQLite-only, skipping")
        return False

    insp = inspect(db.bind)
    if "colleges" not in insp.get_table_names():
        print("[MIGRATION] colleges table does not exist, skipping nullability repair")
        return False

    physical = {col["name"]: bool(col["nullable"]) for col in insp.get_columns("colleges")}
    drifted = [c for c in DRIFTED_NULLABLE_COLUMNS
               if c in physical and not physical[c]]
    if not drifted:
        print("[MIGRATION] colleges table nullability matches model, nothing to repair")
        return False

    print(f"[MIGRATION] colleges table has NOT NULL drift on: {drifted} ({engine_dialect})")

    # Snapshot the database file first (belt-and-braces; migrate_sqlite.py
    # already makes a backup, but never rely on the caller alone).
    db_url = settings.DATABASE_URL
    if db_url.startswith("sqlite:///"):
        db_path = db_url.replace("sqlite:///", "", 1)
        if db_path and os.path.exists(db_path):
            backup_dir = os.path.join(os.path.dirname(db_path) or ".", "backups")
            os.makedirs(backup_dir, exist_ok=True)
            backup_path = os.path.join(
                backup_dir, f"backup_colleges_repair_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            )
            try:
                shutil.copy2(db_path, backup_path)
                print(f"[MIGRATION] Pre-repair backup written to {backup_path}")
            except OSError as e:
                print(f"[MIGRATION] WARNING: could not write backup ({e}); continuing")

    old_cols = [c["name"] for c in insp.get_columns("colleges")]
    db.execute(text("DROP TABLE IF EXISTS colleges_new"))
    db.execute(text(TABLE_DDL))

    col_list = ", ".join(old_cols)
    db.execute(text(
        f"INSERT INTO colleges_new ({col_list}) SELECT {col_list} FROM colleges"
    ))
    db.execute(text("DROP TABLE colleges"))
    db.execute(text("ALTER TABLE colleges_new RENAME TO colleges"))

    # Recreate the indexes that existed on the old table (name-based, safe to
    # re-run via IF NOT EXISTS).
    db.execute(text("CREATE INDEX IF NOT EXISTS ix_colleges_name ON colleges(name)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS ix_colleges_code ON colleges(code)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS ix_colleges_slug ON colleges(slug)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS ix_colleges_status ON colleges(status)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS ix_colleges_application_id ON colleges(application_id)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS ix_colleges_subdomain ON colleges(subdomain)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS ix_colleges_custom_domain ON colleges(custom_domain)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS ix_colleges_connection_status ON colleges(connection_status)"))

    db.commit()
    print(f"[MIGRATION] Rebuilt colleges table matching model nullability ({engine_dialect})")
    return True


if __name__ == "__main__":
    from backend.app.core.database import SessionLocal
    db = SessionLocal()
    try:
        repair_colleges_nullability(db)
    finally:
        db.close()
