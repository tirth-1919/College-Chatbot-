"""AI-Powered Colleges Chatbot — complete DATA RESET (schema preserved).

Cleans the ACTIVE database backend/ait_assistant.db (SQLite).

PRESERVED (system-required):
  - users: the SUPER_ADMIN account (admin@aitindia.in) only
  - system_prompts / prompt_versions (app expects the master prompt to exist)
  - feature_flags (app startup flags)
  - ai_provider_configs, ai_model_registry (AI routing config, seeded system data)
  - maintenance_state (single row, required for normal operations)
  - system_backups rows referencing the backup file we just created

EVERYTHING ELSE is deleted (institutional data, chats, sessions, RAG,
snapshots, users other than SUPER_ADMIN, logs, etc.).
"""
import sqlite3

DB = "backend/ait_assistant.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

tables = [r[0] for r in cur.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()]

# Rows to preserve
admin_row = cur.execute(
    "SELECT id FROM users WHERE role='SUPER_ADMIN'").fetchone()
admin_id = admin_row[0] if admin_row else None

before = {t: cur.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tables}

cur.execute("PRAGMA foreign_keys=OFF")

for t in sorted(tables):
    if t == "users":
        cur.execute("DELETE FROM users WHERE id != ?", (admin_id,))
    elif t in ("system_prompts", "prompt_versions", "feature_flags",
               "ai_provider_configs", "ai_model_registry", "maintenance_state"):
        continue  # system-required, preserved
    elif t == "system_backups":
        # keep only the row for the full reset backup
        cur.execute("DELETE FROM system_backups WHERE filename NOT LIKE 'full_reset_backup_%'")
    else:
        cur.execute(f'DELETE FROM "{t}"')

conn.commit()
cur.execute("VACUUM")
conn.commit()

after = {t: cur.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tables}

print(f"{'TABLE':38s} {'BEFORE':>7s} {'AFTER':>7s}")
print("-" * 54)
for t in sorted(tables):
    flag = "  <-- preserved" if t in ("system_prompts", "prompt_versions", "feature_flags",
                                       "ai_provider_configs", "ai_model_registry",
                                       "maintenance_state") else ""
    print(f"{t:38s} {before[t]:>7d} {after[t]:>7d}{flag}")
print("-" * 54)
print(f"{'TOTAL':38s} {sum(before.values()):>7d} {sum(after.values()):>7d}")
print(f"\nSUPER_ADMIN preserved: {admin_id}")
conn.close()
