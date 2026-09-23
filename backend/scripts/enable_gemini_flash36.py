import sqlite3

con = sqlite3.connect("backend/ait_assistant.db")
con.execute(
    "UPDATE ai_model_registry SET is_enabled=1 "
    "WHERE model_identifier='gemini-3.6-flash' AND provider_id="
    "(SELECT id FROM ai_provider_configs WHERE provider_name='gemini')"
)
con.commit()
for r in con.execute(
    "SELECT m.model_identifier, m.is_enabled, m.priority FROM ai_model_registry m "
    "JOIN ai_provider_configs p ON m.provider_id = p.id "
    "WHERE p.provider_name='gemini' ORDER BY m.priority"
):
    print(r)
