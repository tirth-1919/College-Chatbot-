"""Post-reset scan: search every table for AIT institutional remnants."""
import sqlite3

c = sqlite3.connect("backend/ait_assistant.db")
tables = [r[0] for r in c.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
keywords = ["ahmedabad institute", "aitindia", "anti-ragging", "anjali sharma",
            "rajesh patel", "b.tech", "bca", "mca", "bba", "semester",
            "placement", "hostel", "ait "]

found = 0
for t in tables:
    try:
        rows = c.execute(f'SELECT * FROM "{t}"').fetchall()
    except Exception:
        continue
    for row in rows:
        s = str(row).lower()
        if any(k in s for k in keywords):
            found += 1
            print(f"[HIT] {t}: {row[:2]}")
print(f"\nTotal rows containing AIT-related keywords: {found}")
print("Intentionally-kept system rows (system prompt mentions AIT by design):"
      " system_prompts/prompt_versions define the assistant persona.")
