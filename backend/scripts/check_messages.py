import sqlite3
con = sqlite3.connect("backend/ait_assistant.db")
print("--- empty assistant messages ---")
for r in con.execute("SELECT sender, substr(content,1,150), grounding_status FROM messages WHERE sender='assistant' AND (content IS NULL OR content='') ORDER BY rowid DESC LIMIT 10"):
    print(r)
print("--- last assistant messages ---")
for r in con.execute("SELECT sender, substr(content,1,150), grounding_status, created_at FROM messages WHERE sender='assistant' ORDER BY rowid DESC LIMIT 10"):
    print(r)

print("--- count empty assistant messages ---")
for r in con.execute("SELECT COUNT(*) FROM messages WHERE sender='assistant' AND (content IS NULL OR content='')"):
    print(r)
print("--- empty msg timestamps vs usage logs ---")
for r in con.execute("SELECT created_at FROM messages WHERE sender='assistant' AND (content IS NULL OR content='') ORDER BY rowid DESC LIMIT 15"):
    print(r)

print("--- gemini model latency stats ---")
for r in con.execute("SELECT model_identifier, avg_latency_ms, requests_success, requests_failed FROM ai_model_registry WHERE provider_id=(SELECT id FROM ai_provider_configs WHERE provider_name='gemini')"):
    print(r)
