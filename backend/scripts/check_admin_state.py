import sqlite3

con = sqlite3.connect("backend/ait_assistant.db")
tables = [r[0] for r in con.execute(
    "select name from sqlite_master where type='table' and (name like '%provider%' or name like '%failover%' or name like '%model%')"
).fetchall()]
print("tables:", tables)

for t in tables:
    cols = [d[1] for d in con.execute(f"PRAGMA table_info({t})").fetchall()]
    print(f"\n{t} cols:", cols)
    if "model_registry" in t:
        try:
            for r in con.execute(
                f"select m.model_identifier, m.is_enabled, m.priority, m.health_status, "
                f"m.rate_limit_429_count, m.last_success_at "
                f"from {t} m join ai_provider_configs p on m.provider_id = p.id "
                "where p.provider_name='gemini' order by m.priority"
            ):
                print(r)
        except Exception as e:
            print(e)

if "ai_failover_events" in tables:
    print("\nrecent failover events:")
    for r in con.execute("select * from ai_failover_events order by rowid desc limit 5"):
        print(r)
