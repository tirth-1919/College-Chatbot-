#!/usr/bin/env python3
"""Detailed verification of backfill results"""

import sys
import os
from pathlib import Path
from sqlalchemy import create_engine, text

# Get DATABASE_URL from environment or use SQLite default
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./backend/ait_assistant.db")

if DATABASE_URL.startswith("sqlite"):
    db_path = DATABASE_URL.replace("sqlite:///./", "")
    project_root = Path(__file__).parent.parent.parent.parent
    abs_db_path = project_root / db_path
    DATABASE_URL = f"sqlite:///{abs_db_path}"

engine = create_engine(DATABASE_URL)

print("=" * 80)
print("DETAILED BACKFILL VERIFICATION")
print("=" * 80)
print()

with engine.connect() as conn:
    # 1. Find the mismatched record
    print("1. MISMATCH DETAILS:")
    print("-" * 80)
    result = conn.execute(text("""
        SELECT 
            kr.id as record_id,
            kr.title as record_title,
            kr.college_id as record_college_id,
            kc.id as category_id,
            kc.name as category_name,
            kc.college_id as category_college_id,
            c1.name as record_college_name,
            c2.name as category_college_name
        FROM knowledge_records kr
        JOIN knowledge_categories kc ON kc.id = kr.category_id
        LEFT JOIN colleges c1 ON c1.id = kr.college_id
        LEFT JOIN colleges c2 ON c2.id = kc.college_id
        WHERE kr.college_id != kc.college_id
    """))
    rows = result.fetchall()
    if result.keys():
        for key in result.keys():
            print(f"{key:25s}", end=" | ")
        print()
        print("-" * 80)
    for row in rows:
        for val in row:
            print(f"{str(val)[:24]:25s}", end=" | ")
        print()
    print()
    
    # 2. Count records with NULL college_id
    print("2. NULL COLLEGE_ID CHECK:")
    print("-" * 80)
    result = conn.execute(text("""
        SELECT COUNT(*) as null_count FROM knowledge_records WHERE college_id IS NULL
    """))
    null_count = result.fetchone()[0]
    print(f"Records with NULL college_id: {null_count}")
    print()
    
    # 3. Total records summary
    print("3. TOTAL RECORDS SUMMARY:")
    print("-" * 80)
    result = conn.execute(text("""
        SELECT 
            COUNT(*) as total,
            COUNT(college_id) as with_college_id,
            COUNT(*) - COUNT(college_id) as without_college_id
        FROM knowledge_records
    """))
    row = result.fetchone()
    print(f"Total records:              {row[0]}")
    print(f"With college_id:            {row[1]}")
    print(f"NULL college_id:            {row[2]}")
    print()
    
    # 4. Check if the mismatched record was GIT
    print("4. GIT RECORD INVESTIGATION:")
    print("-" * 80)
    result = conn.execute(text("""
        SELECT 
            kr.id,
            kr.title,
            kr.college_id as kr_college_id,
            kr.category_id,
            kc.name as category_name,
            kc.college_id as kc_college_id,
            c1.code as record_college,
            c2.code as category_college
        FROM knowledge_records kr
        JOIN knowledge_categories kc ON kc.id = kr.category_id
        LEFT JOIN colleges c1 ON c1.id = kr.college_id
        LEFT JOIN colleges c2 ON c2.id = kc.college_id
        WHERE c1.code = 'GIT' OR c2.code = 'GIT'
    """))
    rows = result.fetchall()
    if rows:
        for key in result.keys():
            print(f"{key:20s}", end=" | ")
        print()
        print("-" * 80)
        for row in rows:
            for val in row:
                print(f"{str(val)[:19]:20s}", end=" | ")
            print()
    else:
        print("No GIT records found")
    print()
    
    # 5. Check all record-category relationships
    print("5. ALL RECORD/CATEGORY RELATIONSHIPS:")
    print("-" * 80)
    result = conn.execute(text("""
        SELECT 
            c.code as college,
            COUNT(DISTINCT kc.id) as categories,
            COUNT(kr.id) as records
        FROM colleges c
        LEFT JOIN knowledge_categories kc ON kc.college_id = c.id
        LEFT JOIN knowledge_records kr ON kr.college_id = c.id
        GROUP BY c.id, c.code
        HAVING categories > 0 OR records > 0
        ORDER BY records DESC, categories DESC
    """))
    rows = result.fetchall()
    for key in result.keys():
        print(f"{key:15s}", end=" | ")
    print()
    print("-" * 80)
    for row in rows:
        for val in row:
            print(f"{str(val):15s}", end=" | ")
        print()

print()
print("=" * 80)
