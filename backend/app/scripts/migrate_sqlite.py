import sqlite3
import os
from backend.app.core.config import settings

def run_migrations():
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    if not os.path.exists(db_path):
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Inspect users columns
    cursor.execute("PRAGMA table_info(users)")
    user_cols = [c[1] for c in cursor.fetchall()]

    new_user_cols = {
        "mfa_enabled": "BOOLEAN DEFAULT 0",
        "mfa_secret": "VARCHAR(64)",
        "failed_login_attempts": "INTEGER DEFAULT 0",
        "locked_until": "DATETIME",
        "permissions": "JSON DEFAULT '[]'",
        "last_login_at": "DATETIME"
    }

    for col, col_type in new_user_cols.items():
        if col not in user_cols:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")
            print(f"Added column {col} to users table.")

    # Inspect sessions columns
    cursor.execute("PRAGMA table_info(sessions)")
    session_cols = [c[1] for c in cursor.fetchall()]

    new_session_cols = {
        "device_info": "VARCHAR(255)",
        "is_revoked": "BOOLEAN DEFAULT 0",
        "last_activity_at": "DATETIME"
    }

    for col, col_type in new_session_cols.items():
        if col not in session_cols:
            cursor.execute(f"ALTER TABLE sessions ADD COLUMN {col} {col_type}")
            print(f"Added column {col} to sessions table.")

    conn.commit()
    conn.close()
    
    # Ensure all tables registered in models are created
    from backend.app.core.database import Base, engine
    import backend.app.models
    Base.metadata.create_all(bind=engine)
    print("SQLite migration check and table creation completed successfully.")

if __name__ == "__main__":
    run_migrations()

