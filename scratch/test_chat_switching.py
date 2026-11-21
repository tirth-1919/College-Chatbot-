import asyncio
import uuid
from httpx import AsyncClient, ASGITransport
import os
import sys

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.main import app

AIT_ID = "11111111-1111-1111-1111-111111111111"
RCTI_ID = "22222222-2222-2222-2222-222222222222"

async def test_session_switch():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Create session for AIT
        res = await client.post(
            "/api/v1/chat/sessions",
            headers={"X-College-ID": AIT_ID},
            json={"college_id": AIT_ID, "session_title": "Initial AIT Session"}
        )
        print("Create session status:", res.status_code, res.text)
        assert res.status_code in (200, 201), f"Expected 200/201, got {res.status_code}"
        data = res.json()["data"]
        session_id = data["id"]
        visitor_token = data.get("visitor_token")
        assert data["college_id"] == AIT_ID

        headers = {
            "X-College-ID": AIT_ID,
            "X-Chat-Visitor-Token": visitor_token
        }

        # 2. Switch session to RCTI
        switch_res = await client.post(
            f"/api/v1/chat/sessions/{session_id}/switch-college",
            headers=headers,
            json={"new_college_id": RCTI_ID}
        )
        print("Switch session status:", switch_res.status_code, switch_res.text)
        assert switch_res.status_code == 200, f"Expected 200, got {switch_res.status_code}"
        switch_data = switch_res.json()["data"]
        new_session_id = switch_data["id"]
        assert switch_data["college_id"] == RCTI_ID, "College ID was not updated to RCTI"

        # 3. Access new session with RCTI header
        rcti_headers = {
            "X-College-ID": RCTI_ID,
            "X-Chat-Visitor-Token": visitor_token
        }
        get_res = await client.get(
            f"/api/v1/chat/sessions/{new_session_id}",
            headers=rcti_headers
        )
        print("Get session after switch:", get_res.status_code)
        assert get_res.status_code == 200
        assert get_res.json()["data"]["college_id"] == RCTI_ID

        # 4. Accessing new session with old AIT header should fail (assert session college isolation)
        old_headers = {
            "X-College-ID": AIT_ID,
            "X-Chat-Visitor-Token": visitor_token
        }
        fail_res = await client.get(
            f"/api/v1/chat/sessions/{new_session_id}",
            headers=old_headers
        )
        print("Access with old college header (should be 404):", fail_res.status_code)
        assert fail_res.status_code == 404

        print("\nALL SESSION SWITCH TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(test_session_switch())
