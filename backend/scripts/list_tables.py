import sqlite3

con = sqlite3.connect("backend/ait_assistant.db")
tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
print([t for t in tables if 'session' in t or 'mfa' in t or 'audit' in t])
