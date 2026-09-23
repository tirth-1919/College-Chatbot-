"""Live end-to-end diagnostic: login as demo user, send 'ai means', read full SSE stream."""
import json
import sys
import httpx

BASE = "http://localhost:8000"

# 1. Login
r = httpx.post(f"{BASE}/api/v1/auth/login", json={"email": "1@gmail.com", "password": "1"}, timeout=15)
print("LOGIN:", r.status_code)
if r.status_code != 200:
    print(r.text[:300]); sys.exit(1)
token = r.json().get("access_token")
headers = {"Authorization": f"Bearer {token}"}

# 2. Send chat message, print every SSE event
questions = ["ai means", "What is artificial intelligence?", "explain Python"]
for q in questions:
    print(f"\n=== QUESTION: {q} ===")
    with httpx.stream("POST", f"{BASE}/api/v1/chat/stream",
                      json={"conversation_id": f"diag-{abs(hash(q))}", "message": q},
                      headers=headers, timeout=120) as resp:
        print("HTTP:", resp.status_code, resp.headers.get("content-type"))
        events = []
        text_len = 0
        done = False
        for line in resp.iter_lines():
            if line.startswith("event:"):
                events.append(line.split(":", 1)[1].strip())
            elif line.startswith("data:"):
                try:
                    d = json.loads(line.split(":", 1)[1].strip())
                    if "delta" in d:
                        text_len += len(d["delta"])
                except Exception:
                    pass
        print("EVENTS:", events)
        print("TEXT LEN:", text_len)
        print("TERMINAL EVENT PRESENT:", "message_complete" in events)
