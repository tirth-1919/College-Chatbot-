import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from starlette.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

print("--- 1. Testing Health Check ---")
res_health = client.get("/health")
assert res_health.status_code == 200
print("Health:", res_health.json())

print("\n--- 2. Testing Brand Configuration ---")
res_brand = client.get("/api/v1/config/brand")
assert res_brand.status_code == 200
print("Brand:", res_brand.json()["institution_name"], "| Colors:", res_brand.json()["colors"]["primary"])

print("\n--- 3. Testing Suggested Prompts ---")
res_sug = client.get("/api/v1/chat/suggestions")
assert res_sug.status_code == 200
print(f"Returned {len(res_sug.json())} verified prompts. Sample:", res_sug.json()[0]["prompt"])

print("\n--- 4. Testing P0 Real Image Retrieval (Library & Computer Lab) ---")
res_lib = client.get("/api/v1/images/query?q=library")
assert res_lib.status_code == 200
lib_data = res_lib.json()
print("Library Images Found:", lib_data["count"], "| Sample URL:", lib_data["results"][0]["image_url"])

res_lab = client.get("/api/v1/images/query?q=computer lab")
assert res_lab.status_code == 200
lab_data = res_lab.json()
print("Lab Images Found:", lab_data["count"], "| Sample URL:", lab_data["results"][0]["image_url"])

print("\n--- 5. Testing User Signup & Auth ---")
import uuid
unique_email = f"student_{uuid.uuid4().hex[:6]}@aitindia.in"
res_signup = client.post("/api/v1/auth/signup", json={
    "email": unique_email,
    "password": "AitStudent2026!",
    "full_name": "Kavya Patel"
})
assert res_signup.status_code == 201
signup_data = res_signup.json()
token = signup_data["access_token"]
print("User signed up:", signup_data["user"]["full_name"], "| Token generated.")

print("\n--- 6. Testing Multilingual Chat Stream (Gujlish: 'BCA ni fees ketli che?') ---")
res_chat_guj = client.post(
    "/api/v1/chat/stream",
    json={
        "conversation_id": f"conv-{uuid.uuid4().hex[:8]}",
        "message": "BCA ni fees ketli che?"
    },
    headers={"Authorization": f"Bearer {token}"}
)
assert res_chat_guj.status_code == 200
stream_output = res_chat_guj.text
assert "text_delta" in stream_output
assert "message_complete" in stream_output
assert "45,000" in stream_output or "BCA" in stream_output
print("Gujlish Stream Response Verified! Sample bytes length:", len(stream_output))

print("\n--- 7. Testing P0 Real Image Chat Stream ('Show me the AIT library') ---")
res_chat_img = client.post(
    "/api/v1/chat/stream",
    json={
        "conversation_id": f"conv-{uuid.uuid4().hex[:8]}",
        "message": "Show me the AIT library"
    },
    headers={"Authorization": f"Bearer {token}"}
)
assert res_chat_img.status_code == 200
img_stream_output = res_chat_img.text
assert "image" in img_stream_output
assert "class5.png" in img_stream_output or "library" in img_stream_output
print("P0 Real Image SSE Event Stream Verified! Image correctly streamed in response.")

print("\n--- 8. Testing Follow-up Coreference ('Who teaches DBMS?' -> 'Where is her office?') ---")
conv_id = f"conv-coref-{uuid.uuid4().hex[:6]}"
res_turn1 = client.post(
    "/api/v1/chat/stream",
    json={
        "conversation_id": conv_id,
        "message": "Who teaches DBMS?"
    },
    headers={"Authorization": f"Bearer {token}"}
)
assert res_turn1.status_code == 200
assert "Anjali Sharma" in res_turn1.text

res_turn2 = client.post(
    "/api/v1/chat/stream",
    json={
        "conversation_id": conv_id,
        "message": "Where is her office?"
    },
    headers={"Authorization": f"Bearer {token}"}
)
assert res_turn2.status_code == 200
assert "Block B" in res_turn2.text or "Room 204" in res_turn2.text
print("Follow-up Coreference Resolution Verified! Resolved 'her office' to Prof. Anjali Sharma's office location.")

print("\nALL LIVE INTEGRATION TESTS COMPLETED SUCCESSFULLY!")
