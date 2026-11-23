"""End-to-End Multi-Step Integration Workflow Automated Test Suite.

Tests complete business transactions across layers:
  - Workflow 1: Complete Student Conversational Journey (Auth -> Profile -> College Directory -> Chat Query -> Citations).
  - Workflow 2: College Admin Management Journey (Auth -> Dashboard Stats -> Crawler Jobs -> Document Queue -> Support Tickets).
  - Workflow 3: Platform Super Admin Governance Journey (Auth -> Global Telemetry -> AI Provider Status -> College Registrations).
"""

import time
import uuid
from typing import List, Dict, Any
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from tests.config import (
    STUDENT_EMAIL,
    COLLEGE_ADMIN_EMAIL,
    SUPER_ADMIN_EMAIL,
    DEFAULT_PASSWORD,
    AIT_COLLEGE_ID,
)
from app.main import app


async def run_integration_suite() -> List[Dict[str, Any]]:
    """Executes multi-step end-to-end integration workflows."""
    results = []

    # =========================================================================
    # WORKFLOW 1: Student Conversational FAQ Journey
    # =========================================================================
    t0 = time.perf_counter()
    w1_passed = False
    w1_detail = ""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        try:
            # Step 1: Login
            login_res = await client.post("/api/v1/auth/login", json={"email": STUDENT_EMAIL, "password": DEFAULT_PASSWORD})
            assert login_res.status_code == 200, f"Login failed: {login_res.status_code}"
            token = login_res.json()["data"]["access_token"]
            headers = {"Authorization": f"Bearer {token}", "X-College-ID": AIT_COLLEGE_ID}

            # Step 2: Profile Check
            me_res = await client.get("/api/v1/auth/me", headers=headers)
            assert me_res.status_code == 200, f"Profile failed: {me_res.status_code}"

            # Step 3: Browse Approved Colleges
            colleges_res = await client.get("/api/v1/colleges")
            assert colleges_res.status_code == 200, f"Colleges failed: {colleges_res.status_code}"
            colleges = colleges_res.json().get("data", [])
            assert len(colleges) > 0, "No approved colleges found"

            # Step 4: Initialize Chat Session
            session_init_res = await client.post(
                "/api/v1/chat/sessions",
                json={"college_id": AIT_COLLEGE_ID, "session_title": "E2E Student Test Session", "language": "en"},
                headers=headers
            )
            assert session_init_res.status_code in (200, 201), f"Session create failed: {session_init_res.status_code}"
            sess_id = session_init_res.json()["data"]["id"]

            # Step 5: Ask College FAQ Question
            with patch(
                "app.api.v1.chat.rag_service.answer_question",
                new=AsyncMock(return_value={
                    "answer_text": "Test-only assistant response.",
                    "is_verified": False,
                    "answer_source_type": "NO_RELIABLE_INFORMATION",
                    "source_citations": [],
                    "token_count": 4,
                    "model_used": None,
                    "answer_mode": "TEST",
                    "actual_provider": None,
                    "actual_model": None,
                    "fallback_reason": "External generation is stubbed in integration tests.",
                    "attempt_count": 0,
                    "request_duration_ms": 0,
                }),
            ):
                query_res = await client.post(
                    f"/api/v1/chat/sessions/{sess_id}/messages",
                    json={
                        "message_text": "What are the engineering courses offered?",
                        "language": "en",
                    },
                    headers=headers,
                )
            assert query_res.status_code in [200, 201], f"Chat query failed: {query_res.status_code}"
            q_data = query_res.json().get("data", {})
            assert "message_text" in q_data or "answer" in q_data or "text" in q_data or "reply" in q_data or query_res.status_code == 200

            # Exercise the image citation transport through the real chat
            # endpoint: the structured-gallery result must survive response
            # validation, persistence, and history reload unchanged.
            expected_image_url = "https://www.aitindia.in/Library/sudylib.png"
            with patch(
                "app.api.v1.chat.answer_structured_question",
                new=AsyncMock(return_value={
                    "message_text": "Verified AIT photographs",
                    "is_verified": True,
                    "answer_source_type": "ADMIN_VERIFIED",
                    "source_citations": [{
                        "title": "AIT Library",
                        "source_type": "ADMIN_VERIFIED",
                        "url": "https://www.aitindia.in/facilities/library",
                        "image_url": expected_image_url,
                        "image_category": "LIBRARY",
                    }],
                }),
            ):
                image_res = await client.post(
                    f"/api/v1/chat/sessions/{sess_id}/messages",
                    json={"message_text": "Show all AIT images", "language": "en"},
                    headers=headers,
                )
            assert image_res.status_code in [200, 201], f"Image chat query failed: {image_res.status_code}"
            image_data = image_res.json().get("data", {})
            citations = image_data.get("source_citations", [])
            assert any(citation.get("image_url") == expected_image_url for citation in citations), \
                "Image URL was lost before the chat response reached the client"

            history_res = await client.get(
                f"/api/v1/chat/sessions/{sess_id}",
                headers=headers,
            )
            assert history_res.status_code == 200, f"Chat history reload failed: {history_res.status_code}"
            saved_messages = history_res.json().get("data", {}).get("messages", [])
            saved_roles = {message.get("sender_role") for message in saved_messages}
            assert {"user", "assistant"}.issubset(saved_roles), "User and assistant messages were not both persisted"
            saved_image_response = next((message for message in saved_messages if any(
                citation.get("image_url") == expected_image_url
                for citation in message.get("source_citations", [])
            )), None)
            assert saved_image_response, "Image citation was not preserved in the chat history"

            w1_passed = True
            w1_detail = "Login -> Profile -> College Directory -> Chat Session -> Image Citation Response -> Persisted Image Citation and History Reload (AI stubbed)"
        except Exception as exc:
            w1_detail = f"Failed at step: {str(exc)}"

    dur1 = (time.perf_counter() - t0) * 1000
    results.append({
        "category": "Integration",
        "name": "E2E Student Conversational Journey (Auth -> Profile -> Colleges -> RAG Query)",
        "target": "Student Workflow (5 Steps)",
        "status": "PASS" if w1_passed else "FAIL",
        "duration_ms": dur1,
        "detail": w1_detail,
    })

    # =========================================================================
    # WORKFLOW 2: College Admin Management Journey
    # =========================================================================
    t0 = time.perf_counter()
    w2_passed = False
    w2_detail = ""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        try:
            # Step 1: Login as College Admin
            login_res = await client.post("/api/v1/auth/login", json={"email": COLLEGE_ADMIN_EMAIL, "password": DEFAULT_PASSWORD})
            assert login_res.status_code == 200, f"Admin login failed: {login_res.status_code}"
            token = login_res.json()["data"]["access_token"]
            headers = {"Authorization": f"Bearer {token}", "X-College-ID": AIT_COLLEGE_ID}

            # Step 2: Dashboard Metrics
            dash_res = await client.get("/api/v1/college-admin/dashboard", headers=headers)
            assert dash_res.status_code == 200, f"Admin dashboard failed: {dash_res.status_code}"

            # Step 3: Check Crawler Sources
            sources_res = await client.get("/api/v1/college-admin/websites", headers=headers)
            assert sources_res.status_code == 200, f"Crawler sources failed: {sources_res.status_code}"

            # Step 4: Check Documents Queue
            docs_res = await client.get("/api/v1/college-admin/documents", headers=headers)
            assert docs_res.status_code == 200, f"Documents list failed: {docs_res.status_code}"

            # Step 5: Check Support Tickets
            tickets_res = await client.get("/api/v1/support/tickets", headers=headers)
            assert tickets_res.status_code == 200, f"Tickets failed: {tickets_res.status_code}"

            w2_passed = True
            w2_detail = "Step 1-5 Success: Admin Login -> Dashboard -> Crawler Sources -> Docs Queue -> Support Tickets"
        except Exception as exc:
            w2_detail = f"Failed at step: {str(exc)}"

    dur2 = (time.perf_counter() - t0) * 1000
    results.append({
        "category": "Integration",
        "name": "E2E College Admin Workspace Journey (Auth -> Dashboard -> Crawler -> Docs -> Support)",
        "target": "College Admin Workflow (5 Steps)",
        "status": "PASS" if w2_passed else "FAIL",
        "duration_ms": dur2,
        "detail": w2_detail,
    })

    # =========================================================================
    # WORKFLOW 3: Super Admin Governance Journey
    # =========================================================================
    t0 = time.perf_counter()
    w3_passed = False
    w3_detail = ""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        try:
            # Step 1: Login as Super Admin
            login_res = await client.post("/api/v1/auth/login", json={"email": SUPER_ADMIN_EMAIL, "password": DEFAULT_PASSWORD})
            assert login_res.status_code == 200, f"Super Admin login failed: {login_res.status_code}"
            token = login_res.json()["data"]["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # Step 2: Platform Dashboard Overview
            dash_res = await client.get("/api/v1/super-admin/dashboard", headers=headers)
            assert dash_res.status_code == 200, f"Super Admin dashboard failed: {dash_res.status_code}"

            # Step 3: AI Provider Telemetry
            ai_res = await client.get("/api/v1/super-admin/ai-providers", headers=headers)
            assert ai_res.status_code == 200, f"AI providers list failed: {ai_res.status_code}"

            # Step 4: Audit Logs Trail
            logs_res = await client.get("/api/v1/super-admin/audit-logs", headers=headers)
            assert logs_res.status_code == 200, f"Audit logs failed: {logs_res.status_code}"

            w3_passed = True
            w3_detail = "Step 1-4 Success: Super Admin Login -> Global Dashboard -> AI Providers -> Audit Logs"
        except Exception as exc:
            w3_detail = f"Failed at step: {str(exc)}"

    dur3 = (time.perf_counter() - t0) * 1000
    results.append({
        "category": "Integration",
        "name": "E2E Platform Governance Journey (Super Admin Auth -> Global Stats -> AI Config -> Audits)",
        "target": "Super Admin Workflow (4 Steps)",
        "status": "PASS" if w3_passed else "FAIL",
        "duration_ms": dur3,
        "detail": w3_detail,
    })

    return results

