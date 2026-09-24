#!/usr/bin/env python3
"""
Production Backfill Runner - Tenant Isolation Security Fix
Executes backfill_record_college_ids.sql and verifies results
"""

import sys
import os
from pathlib import Path
from sqlalchemy import create_engine, text

# Get DATABASE_URL from environment or use SQLite default (matching config.py)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./backend/ait_assistant.db")

# Adjust path for SQLite to be relative to project root
if DATABASE_URL.startswith("sqlite"):
    db_path = DATABASE_URL.replace("sqlite:///./", "")
    project_root = Path(__file__).parent.parent.parent.parent
    abs_db_path = project_root / db_path
    DATABASE_URL = f"sqlite:///{abs_db_path}"

def main():
    print("=" * 80)
    print("PRODUCTION BACKFILL: knowledge_records.college_id")
    print("=" * 80)
    print()
    
    # Read SQL file
    sql_file = Path(__file__).parent / "backfill_record_college_ids.sql"
    with open(sql_file, 'r') as f:
        sql_script = f.read()
    
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    print(f"✓ Connected to database")
    print(f"✓ SQL file: {sql_file}")
    print()
    
    # Execute SQL script
    print("Executing backfill SQL...")
    print("-" * 80)
    
    try:
        with engine.begin() as conn:
            # Read and parse SQL file
            sql_content = sql_script
            
            # Remove block comments /* ... */
            import re
            sql_content = re.sub(r'/\*.*?\*/', '', sql_content, flags=re.DOTALL)
            
            # Split statements and filter
            statements = []
            for stmt in sql_content.split(';'):
                stmt = stmt.strip()
                # Skip empty, comments, and transaction control (handled by engine.begin())
                if stmt and not stmt.startswith('--') and stmt.upper() not in ('BEGIN', 'COMMIT'):
                    statements.append(stmt)
            
            for stmt in statements:
                result = conn.execute(text(stmt))
                
                # If this is a SELECT, print results
                if stmt.strip().upper().startswith('SELECT'):
                    rows = result.fetchall()
                    if rows:
                        # Print column headers
                        if result.keys():
                            print(" | ".join(str(k) for k in result.keys()))
                            print("-" * 80)
                        # Print rows
                        for row in rows:
                            print(" | ".join(str(v) for v in row))
                        print()
        
        print("-" * 80)
        print("✓ Backfill completed successfully")
        print()
        
    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Additional verification queries
    print("=" * 80)
    print("ADDITIONAL VERIFICATION")
    print("=" * 80)
    print()
    
    with engine.connect() as conn:
        # Distribution by college
        print("Distribution by college:")
        print("-" * 80)
        result = conn.execute(text("""
            SELECT 
                c.name as college_name,
                c.code as college_code,
                COUNT(kr.id) as record_count
            FROM colleges c
            LEFT JOIN knowledge_records kr ON kr.college_id = c.id
            GROUP BY c.id, c.name, c.code
            ORDER BY record_count DESC
        """))
        rows = result.fetchall()
        if result.keys():
            print(" | ".join(str(k) for k in result.keys()))
            print("-" * 80)
        for row in rows:
            print(" | ".join(str(v) for v in row))
        print()
        
        # Category distribution
        print("Categories by college:")
        print("-" * 80)
        result = conn.execute(text("""
            SELECT 
                c.name as college_name,
                COUNT(kc.id) as category_count
            FROM colleges c
            LEFT JOIN knowledge_categories kc ON kc.college_id = c.id
            GROUP BY c.id, c.name
            ORDER BY category_count DESC
        """))
        rows = result.fetchall()
        if result.keys():
            print(" | ".join(str(k) for k in result.keys()))
            print("-" * 80)
        for row in rows:
            print(" | ".join(str(v) for v in row))
        print()
        
        # Consistency check: record.college_id != category.college_id
        print("Record/Category mismatches (should be 0):")
        print("-" * 80)
        result = conn.execute(text("""
            SELECT COUNT(*) as mismatch_count
            FROM knowledge_records kr
            JOIN knowledge_categories kc ON kc.id = kr.category_id
            WHERE kr.college_id != kc.college_id
        """))
        row = result.fetchone()
        print(f"Mismatches: {row[0]}")
        print()
        
        # Orphan college_id check
        print("Orphan college_id (records pointing to non-existent college):")
        print("-" * 80)
        result = conn.execute(text("""
            SELECT COUNT(*) as orphan_count
            FROM knowledge_records kr
            WHERE kr.college_id IS NOT NULL
              AND kr.college_id NOT IN (SELECT id FROM colleges)
        """))
        row = result.fetchone()
        print(f"Orphans: {row[0]}")
        print()
    
    print("=" * 80)
    print("✓ BACKFILL VERIFICATION COMPLETE")
    print("=" * 80)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
