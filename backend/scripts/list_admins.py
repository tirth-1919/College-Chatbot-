import sqlite3

con = sqlite3.connect("backend/ait_assistant.db")
for r in con.execute("SELECT id, email, role, is_active FROM users WHERE role LIKE '%admin%' COLLATE NOCASE OR role LIKE 'SUPER%' COLLATE NOCASE"):
    print(r)
