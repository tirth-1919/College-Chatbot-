"""
Migration: Fix Knowledge Category Uniqueness Constraints

Problem:
- KnowledgeCategory has global UNIQUE constraints on `name` and `key`
- In a multi-college platform, multiple colleges need the same category keys
  (e.g., "fees", "faculty", "courses")
- Global uniqueness prevents tenant-scoped categories

Solution:
- Drop global UNIQUE constraints on `name` and `key`
- Add composite UNIQUE constraints: (college_id, name) and (college_id, key)
- This allows each college to have its own "fees" category while preventing
  duplicates within a single college

Safety:
- Non-destructive: does not delete data
- Idempotent: can run multiple times safely
- Preserves existing categories
"""
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect


def migrate_category_uniqueness(db: Session):
    """
    Migrate KnowledgeCategory uniqueness from global to tenant-scoped.
    Safe for SQLite and PostgreSQL.
    """
    
    inspector = inspect(db.bind)
    engine_dialect = db.bind.dialect.name
    
    print(f"[MIGRATION] Starting category uniqueness fix ({engine_dialect})...")
    
    # Check if table exists
    if "knowledge_categories" not in inspector.get_table_names():
        print("[MIGRATION] knowledge_categories table does not exist yet, skipping migration")
        return
    
    # Check if table has any data
    result = db.execute(text("SELECT COUNT(*) FROM knowledge_categories")).scalar()
    if result == 0:
        print("[MIGRATION] knowledge_categories table is empty, skipping migration (fresh install)")
        return
    
    try:
        if engine_dialect == "sqlite":
            # SQLite requires table recreation to modify constraints
            print("[MIGRATION] SQLite detected: recreating table with new constraints...")
            
            # Check if migration already applied
            existing_indexes = {idx["name"] for idx in inspector.get_indexes("knowledge_categories")}
            if "ix_knowledge_categories_college_id_key" in existing_indexes:
                print("[MIGRATION] Migration already applied (composite indexes exist), skipping")
                return
            
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS knowledge_categories_new (
                    id VARCHAR(36) PRIMARY KEY,
                    name VARCHAR(120) NOT NULL,
                    key VARCHAR(80) NOT NULL,
                    description TEXT,
                    icon VARCHAR(50),
                    display_order INTEGER DEFAULT 0 NOT NULL,
                    status VARCHAR(20) DEFAULT 'ACTIVE' NOT NULL,
                    college_id VARCHAR(36),
                    created_by VARCHAR(36),
                    updated_by VARCHAR(36),
                    created_at DATETIME,
                    updated_at DATETIME,
                    FOREIGN KEY(college_id) REFERENCES colleges(id) ON DELETE CASCADE,
                    FOREIGN KEY(created_by) REFERENCES users(id) ON DELETE SET NULL,
                    FOREIGN KEY(updated_by) REFERENCES users(id) ON DELETE SET NULL,
                    UNIQUE(college_id, name),
                    UNIQUE(college_id, key)
                )
            """))
            
            # Copy data with explicit column mapping to handle schema evolution
            # Get actual columns from old table
            old_columns = {col["name"] for col in inspector.get_columns("knowledge_categories")}
            print(f"[MIGRATION] Old table columns: {sorted(old_columns)}")
            
            # Build column list dynamically based on what exists
            base_cols = ["id", "name", "key"]
            optional_cols = {
                "description": "NULL",
                "icon": "NULL",
                "display_order": "0",
                "status": "'ACTIVE'",
                "college_id": "NULL",
                "created_by": "NULL",
                "updated_by": "NULL",
                "created_at": "NULL",
                "updated_at": "NULL"
            }
            
            select_parts = []
            for col in base_cols:
                select_parts.append(col)
            
            for col, default in optional_cols.items():
                if col in old_columns:
                    select_parts.append(col)
                else:
                    select_parts.append(f"{default} as {col}")
            
            select_clause = ", ".join(select_parts)
            insert_cols = ", ".join(base_cols + list(optional_cols.keys()))
            
            sql_statement = f"""
                INSERT INTO knowledge_categories_new ({insert_cols})
                SELECT {select_clause}
                FROM knowledge_categories
            """
            print(f"[MIGRATION] Full Copy SQL: {sql_statement}")
            
            db.execute(text(sql_statement))
            
            # Drop old table
            db.execute(text("DROP TABLE knowledge_categories"))
            
            # Rename new table
            db.execute(text("ALTER TABLE knowledge_categories_new RENAME TO knowledge_categories"))
            
            # Recreate indexes
            db.execute(text("CREATE INDEX ix_knowledge_categories_college_id ON knowledge_categories(college_id)"))
            db.execute(text("CREATE INDEX ix_knowledge_categories_status ON knowledge_categories(status)"))
            
            db.commit()
            print("[MIGRATION] SQLite migration complete")
            
        elif engine_dialect == "postgresql":
            # PostgreSQL allows direct constraint modification
            print("[MIGRATION] PostgreSQL detected: modifying constraints...")
            
            # Check if old constraints exist
            constraints = {c["name"] for c in inspector.get_unique_constraints("knowledge_categories")}
            indexes = {idx["name"] for idx in inspector.get_indexes("knowledge_categories")}
            
            # Check if migration already applied
            if "uq_knowledge_categories_college_id_key" in constraints or \
               "ix_knowledge_categories_college_id_key" in indexes:
                print("[MIGRATION] Migration already applied (composite constraints exist), skipping")
                return
            
            # Drop old unique constraints if they exist
            if "knowledge_categories_name_key" in constraints or "uq_knowledge_categories_name" in constraints:
                try:
                    db.execute(text("ALTER TABLE knowledge_categories DROP CONSTRAINT IF EXISTS knowledge_categories_name_key"))
                    db.execute(text("ALTER TABLE knowledge_categories DROP CONSTRAINT IF EXISTS uq_knowledge_categories_name"))
                except Exception as e:
                    print(f"[MIGRATION] Note: Could not drop name constraint: {e}")
            
            if "knowledge_categories_key_key" in constraints or "uq_knowledge_categories_key" in constraints:
                try:
                    db.execute(text("ALTER TABLE knowledge_categories DROP CONSTRAINT IF EXISTS knowledge_categories_key_key"))
                    db.execute(text("ALTER TABLE knowledge_categories DROP CONSTRAINT IF EXISTS uq_knowledge_categories_key"))
                except Exception as e:
                    print(f"[MIGRATION] Note: Could not drop key constraint: {e}")
            
            # Drop old indexes if they exist
            if "ix_knowledge_categories_name" in indexes:
                db.execute(text("DROP INDEX IF EXISTS ix_knowledge_categories_name"))
            if "ix_knowledge_categories_key" in indexes:
                db.execute(text("DROP INDEX IF EXISTS ix_knowledge_categories_key"))
            
            # Add new composite unique constraints
            db.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS ix_knowledge_categories_college_id_name 
                ON knowledge_categories(college_id, name)
            """))
            db.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS ix_knowledge_categories_college_id_key 
                ON knowledge_categories(college_id, key)
            """))
            
            db.commit()
            print("[MIGRATION] PostgreSQL migration complete")
        
        else:
            print(f"[MIGRATION] Unsupported database dialect: {engine_dialect}")
            return
        
        print("[MIGRATION] Category uniqueness constraints successfully migrated to tenant-scoped")
        
    except Exception as e:
        print(f"[MIGRATION] Error during category uniqueness migration: {e}")
        db.rollback()
        raise


if __name__ == "__main__":
    from backend.app.core.database import SessionLocal
    db = SessionLocal()
    try:
        migrate_category_uniqueness(db)
    finally:
        db.close()
