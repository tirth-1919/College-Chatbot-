import sqlite3
import os
import shutil
from datetime import datetime, timezone
from backend.app.core.config import settings

AIT_TENANT_ID = "ait-default-tenant-0001"

def run_migrations():
    # 1. Ensure all tables registered in models are created first
    from backend.app.core.database import Base, engine
    import backend.app.models
    Base.metadata.create_all(bind=engine)

    if not settings.DATABASE_URL.startswith("sqlite"):
        return

    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    if not os.path.exists(db_path):
        return

    # Backup db before altering
    try:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(os.path.dirname(db_path), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        backup_path = os.path.join(backup_dir, f"backup_{ts}.db")
        shutil.copy2(db_path, backup_path)
    except Exception as e:
        print(f"Notice: backup creation skipped ({e})")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Helper: add column if missing
    def add_col(table_name, col_name, col_def):
        cursor.execute(f"PRAGMA table_info({table_name})")
        cols = [c[1] for c in cursor.fetchall()]
        if col_name not in cols:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def}")
            print(f"Added column {col_name} to {table_name}.")

    # Inspect users columns
    add_col("users", "mfa_enabled", "BOOLEAN DEFAULT 0")
    add_col("users", "mfa_secret", "VARCHAR(64)")
    add_col("users", "failed_login_attempts", "INTEGER DEFAULT 0")
    add_col("users", "locked_until", "DATETIME")
    add_col("users", "permissions", "JSON DEFAULT '[]'")
    add_col("users", "last_login_at", "DATETIME")
    add_col("users", "college_id", "VARCHAR(36)")
    add_col("users", "default_college_id", "VARCHAR(36)")
    add_col("users", "must_change_password", "BOOLEAN DEFAULT 0")

    # Knowledge Gap Center: new columns on knowledge_gaps + new message_feedback table
    add_col("knowledge_gaps", "dedup_key", "VARCHAR(255)")
    add_col("knowledge_gaps", "conversation_id", "VARCHAR(36)")
    add_col("knowledge_gaps", "message_id", "VARCHAR(36)")
    add_col("knowledge_gaps", "status", "VARCHAR(30) DEFAULT 'OPEN'")
    add_col("knowledge_gaps", "occurrence_count", "INTEGER DEFAULT 1")
    add_col("knowledge_gaps", "first_seen_at", "DATETIME")
    add_col("knowledge_gaps", "last_seen_at", "DATETIME")
    add_col("knowledge_gaps", "sample_answer", "TEXT")
    add_col("knowledge_gaps", "reason", "VARCHAR(50)")
    add_col("knowledge_gaps", "category", "VARCHAR(50)")
    add_col("knowledge_gaps", "course", "VARCHAR(100)")
    add_col("knowledge_gaps", "academic_year", "VARCHAR(20)")
    add_col("knowledge_gaps", "priority", "VARCHAR(20) DEFAULT 'Medium'")
    add_col("knowledge_gaps", "resolved_at", "DATETIME")
    add_col("knowledge_gaps", "resolved_by", "VARCHAR(36)")

    # Inspect colleges columns
    add_col("colleges", "rejection_reason", "TEXT")
    add_col("colleges", "review_notes", "TEXT")
    add_col("colleges", "description", "TEXT")

    # Connection health tracking (production multi-college requirements)
    add_col("colleges", "connection_status", "VARCHAR(30) DEFAULT 'NOT_CONNECTED'")
    add_col("colleges", "website_last_checked_at", "DATETIME")
    add_col("colleges", "website_last_success_at", "DATETIME")
    add_col("colleges", "website_last_failure_at", "DATETIME")
    add_col("colleges", "website_http_status", "INTEGER")
    add_col("colleges", "website_pages_indexed", "INTEGER DEFAULT 0")
    add_col("colleges", "website_error_message", "TEXT")
    add_col("colleges", "knowledge_last_updated_at", "DATETIME")
    add_col("colleges", "verified_records_count", "INTEGER DEFAULT 0")
    add_col("colleges", "rag_documents_count", "INTEGER DEFAULT 0")
    add_col("colleges", "broken_sources_count", "INTEGER DEFAULT 0")

    # Inspect sessions columns
    add_col("sessions", "device_info", "VARCHAR(255)")
    add_col("sessions", "is_revoked", "BOOLEAN DEFAULT 0")
    add_col("sessions", "last_activity_at", "DATETIME")

    # Inspect documents columns
    add_col("documents", "visibility", "VARCHAR(32) DEFAULT 'ADMIN_VERIFIED'")
    add_col("documents", "college_id", "VARCHAR(36)")
    add_col("document_chunks", "college_id", "VARCHAR(36)")

    # Inspect change_requests columns (approval workflow)
    add_col("change_requests", "title", "VARCHAR(255)")
    add_col("change_requests", "clarification_response", "TEXT")
    add_col("change_requests", "updated_at", "DATETIME")

    cursor.execute("UPDATE documents SET visibility = 'PRIVATE_USER' WHERE user_id IS NOT NULL AND (visibility IS NULL OR user_id = 'user-a')")
    cursor.execute("UPDATE documents SET visibility = 'ADMIN_VERIFIED' WHERE user_id IS NULL AND visibility IS NULL")

    # Add college_id to other tenant tables
    tenant_tables = [
        "knowledge_categories",
        "knowledge_records",
        "ait_entities",
        "ait_knowledge_versions",
        "website_snapshots",
        "knowledge_gaps",
        "conversations",
        "ait_images",
        "audit_logs",
        "security_events",
        "ai_usage_logs",
        "knowledge_conflicts",
    ]

    for tbl in tenant_tables:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tbl}'")
        if cursor.fetchone():
            add_col(tbl, "college_id", "VARCHAR(36)")

    # Multi-provider transition: free-tier classification column on the model registry.
    cursor.execute("PRAGMA TABLE_INFO(ai_model_registry)")
    registry_cols = {row[1] for row in cursor.fetchall()}
    if "free_tier_status" not in registry_cols:
        cursor.execute("ALTER TABLE ai_model_registry ADD COLUMN free_tier_status VARCHAR(30) DEFAULT 'UNKNOWN' NOT NULL")
        print("Added column free_tier_status to ai_model_registry table.")

    # 2. Seed AIT as the First College / Tenant if not exists
    cursor.execute("SELECT id FROM colleges WHERE id = ? OR code = 'AIT'", (AIT_TENANT_ID,))
    ait_row = cursor.fetchone()
    now_str = datetime.now(timezone.utc).isoformat()

    if not ait_row:
        cursor.execute("""
            INSERT INTO colleges (
                id, name, code, slug, official_email, official_website,
                phone, address, city, state, country, university_affiliation,
                contact_person, contact_email, contact_phone, logo_url,
                status, registration_status, application_id, timezone,
                assistant_name, welcome_message, primary_color, secondary_color, accent_color,
                supported_languages, max_users, max_storage_mb, max_documents, max_ai_requests_per_day,
                created_at, updated_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?
            )
        """, (
            AIT_TENANT_ID,
            "Ahmedabad Institute of Technology",
            "AIT",
            "ait",
            "admin@aitindia.in",
            "https://www.aitindia.in",
            "+91-79-27660214",
            "Near Vasantnagar Township, Gota-Ognaj Road, Ahmedabad, Gujarat 382481",
            "Ahmedabad",
            "Gujarat",
            "India",
            "Gujarat Technological University (GTU)",
            "AIT Administration",
            "admin@aitindia.in",
            "+91-79-27660214",
            "https://www.aitindia.in/images/Ait-logo.webp",
            "ACTIVE",
            "APPROVED",
            "COL-AIT-ORIGIN",
            "Asia/Kolkata",
            "AI-Powered Colleges Chatbot",
            "Hello! Welcome to AI-Powered Colleges Chatbot. How can I assist you today with courses, admissions, fees, faculty, or placements?",
            "#0b0a3e",
            "#1a2345",
            "#f08518",
            '["en", "gu", "hi"]',
            5000,
            10240,
            2000,
            50000,
            now_str,
            now_str
        ))
        print("[MIGRATION] Seeded AIT as the first tenant.")

    # 3. Backfill all existing tenant records with AIT college_id
    backfill_tables = [
        "knowledge_categories",
        "knowledge_records",
        "ait_entities",
        "ait_knowledge_versions",
        "website_snapshots",
        "knowledge_gaps",
        "documents",
        "document_chunks",
        "conversations",
        "ait_images",
        "audit_logs",
        "security_events",
        "ai_usage_logs",
        "knowledge_conflicts"
    ]

    for tbl in backfill_tables:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tbl}'")
        if cursor.fetchone():
            cursor.execute(f"UPDATE {tbl} SET college_id = ? WHERE college_id IS NULL", (AIT_TENANT_ID,))
            updated_count = cursor.rowcount
            if updated_count > 0:
                print(f"[MIGRATION] Backfilled {updated_count} rows in {tbl} with AIT college_id.")

    # 4. Backfill users:
    # Super admin has role SUPER_ADMIN and can access platform level
    cursor.execute("UPDATE users SET role = 'SUPER_ADMIN' WHERE email = 'admin@aitindia.in'")
    cursor.execute("UPDATE users SET role = 'SUPER_ADMIN', college_id = NULL WHERE email = '3@gmail.com'")
    # College admin 2@gmail.com belongs to AIT as COLLEGE_ADMIN
    cursor.execute("UPDATE users SET role = 'COLLEGE_ADMIN', college_id = ? WHERE email = '2@gmail.com'", (AIT_TENANT_ID,))
    # Demo User 1@gmail.com belongs to AIT as STUDENT
    cursor.execute("UPDATE users SET role = 'STUDENT', college_id = ? WHERE email = '1@gmail.com'", (AIT_TENANT_ID,))
    # Any other user with NULL college_id gets linked to AIT unless SUPER_ADMIN
    cursor.execute("UPDATE users SET college_id = ? WHERE college_id IS NULL AND role != 'SUPER_ADMIN'", (AIT_TENANT_ID,))

    conn.commit()
    conn.close()
    print("SQLite migration check and table creation completed successfully.")

if __name__ == "__main__":
    run_migrations()
