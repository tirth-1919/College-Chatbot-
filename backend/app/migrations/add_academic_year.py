"""
Migration: Add academic_year column to ait_entities table

This migration adds an optional academic_year field to support year-specific
fee and program data while maintaining backward compatibility with existing records.
"""

import sqlite3
import os

def migrate_add_academic_year():
    """Add academic_year column to ait_entities table."""
    print("=" * 60)
    print("MIGRATION: Add academic_year column")
    print("=" * 60)
    
    # Database path
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "backend", "ait_assistant.db")
    print(f"Database path: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(ait_entities)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'academic_year' in columns:
            print("[OK] academic_year column already exists")
            conn.close()
            return
        
        # Add the column
        cursor.execute("ALTER TABLE ait_entities ADD COLUMN academic_year VARCHAR(20)")
        
        # Create index on academic_year for efficient querying
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ait_entities_academic_year ON ait_entities(academic_year)")
        
        conn.commit()
        conn.close()
        
        print("[OK] academic_year column added successfully")
        print("[OK] Index created on academic_year")
        
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        raise

if __name__ == "__main__":
    migrate_add_academic_year()
    print("\nMigration complete")
