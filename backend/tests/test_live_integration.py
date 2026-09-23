"""
Live integration tests for the college chatbot API.
These tests exercise the full HTTP stack using TestClient.
NOTE: Coreference test (test 8) depends on faculty data in DB.
"""
import sys, os, uuid
import pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from starlette.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


@pytest.fixture(scope="module")
def auth_token():
    """Create a fresh test user and return its access token."""
    unique_email = f"student_{uuid.uuid4().hex[:6]}@aitindia.in"
    res = client.post("/api/v1/auth/signup", json={
        "email": unique_email,
        "password": "AitStudent2026!",
        "full_name": "Kavya Patel"
    })
    assert res.status_code == 201
    return res.json()["access_token"]


def test_health_check():
    print("--- 1. Testing Health Check ---")
    res = client.get("/health")
    assert res.status_code == 200
    print("Health:", res.json())


def test_brand_configuration():
    print("--- 2. Testing Brand Configuration ---")
    res = client.get("/api/v1/config/brand")
    assert res.status_code == 200
    data = res.json()
    print("Brand:", data["institution_name"], "| Colors:", data["colors"]["primary"])


def test_suggested_prompts():
    print("--- 3. Testing Suggested Prompts ---")
    res = client.get("/api/v1/chat/suggestions")
    assert res.status_code == 200
    items = res.json()
    assert len(items) > 0
    print(f"Returned {len(items)} verified prompts. Sample:", items[0]["prompt"])


def test_image_retrieval_library():
    print("--- 4a. Testing Image Retrieval: Library ---")
    res = client.get("/api/v1/images/query?q=library")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] > 0
    print("Library Images Found:", data["count"], "| Sample URL:", data["results"][0]["image_url"])


def test_image_retrieval_computer_lab():
    print("--- 4b. Testing Image Retrieval: Computer Lab ---")
    res = client.get("/api/v1/images/query?q=computer lab")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] > 0
    print("Lab Images Found:", data["count"], "| Sample URL:", data["results"][0]["image_url"])


def test_user_signup_and_auth(auth_token):
    print("--- 5. Testing User Signup & Auth ---")
    assert auth_token  # fixture handles signup assertion
    print("User signed up | Token generated.")


def test_multilingual_chat_gujlish(auth_token):
    print("--- 6. Testing Multilingual Chat Stream (Gujlish) ---")
    # §5/§12: a new chat starts with college_id = NULL — the college must be
    # selected (onboarding) BEFORE institutional questions are answerable.
    conv_id = f"conv-{uuid.uuid4().hex[:8]}"
    sel = client.post(
        "/api/v1/chat/stream",
        json={"conversation_id": conv_id, "message": "Ahmedabad Institute of Technology"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert sel.status_code == 200
    assert "Connected to" in sel.text
    res = client.post(
        "/api/v1/chat/stream",
        json={
            "conversation_id": conv_id,
            "message": "BCA ni fees ketli che?"
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert res.status_code == 200
    output = res.text
    assert "text_delta" in output
    assert "message_complete" in output
    assert "45,000" in output or "BCA" in output
    print("Gujlish Stream Response Verified! Bytes:", len(output))


def test_image_chat_stream(auth_token):
    print("--- 7. Testing Image Chat Stream ---")
    # §5/§12: select the college first — a new chat never assumes AIT.
    conv_id = f"conv-{uuid.uuid4().hex[:8]}"
    sel = client.post(
        "/api/v1/chat/stream",
        json={"conversation_id": conv_id, "message": "Ahmedabad Institute of Technology"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert sel.status_code == 200
    res = client.post(
        "/api/v1/chat/stream",
        json={
            "conversation_id": conv_id,
            "message": "Show me the library"
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert res.status_code == 200
    output = res.text
    assert "image" in output
    assert "class5.png" in output or "library" in output
    print("P0 Real Image SSE Verified!")


@pytest.mark.xfail(
    reason="Coreference test depends on Anjali Sharma faculty record being present in the DB — may fail on fresh DB",
    strict=False
)
def test_followup_coreference(auth_token):
    """Tests conversational follow-up: 'Who teaches DBMS?' -> 'Where is her office?'"""
    print("--- 8. Testing Follow-up Coreference ---")
    conv_id = f"conv-coref-{uuid.uuid4().hex[:6]}"
    res1 = client.post(
        "/api/v1/chat/stream",
        json={"conversation_id": conv_id, "message": "Who teaches DBMS?"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert res1.status_code == 200
    assert "Anjali Sharma" in res1.text

    res2 = client.post(
        "/api/v1/chat/stream",
        json={"conversation_id": conv_id, "message": "Where is her office?"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert res2.status_code == 200
    assert "Block B" in res2.text or "Room 204" in res2.text
    print("Follow-up Coreference Verified!")
