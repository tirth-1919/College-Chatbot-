"""Unit coverage for fee-question normalization used by structured lookup."""
import pytest
import json
from pathlib import Path
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4
import asyncio
import hashlib
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
import httpx

from app.services.academic_service import _requested_semester, _course_match, answer_structured_question


@pytest.mark.parametrize(("question", "semester"), [
    ("What is BCA semester 1 fee?", 1),
    ("BCA sem 1 fees", 1),
    ("first semester BCA tuition", 1),
    ("What is BCA semester 2 fee?", 2),
    ("second semester fee", 2),
    ("sem 8 charges", 8),
])
def test_semester_phrasing(question, semester):
    assert _requested_semester(question) == semester


def test_course_lookup_accepts_abbreviation_and_full_name():
    class Course:
        course_name = "Bachelor of Computer Applications"
        course_code = ""
        course_abbreviation = "BCA"
        branch_name = None

    course = Course()
    assert _course_match("What is BCA fee", [course]) is course
    assert _course_match("Bachelor of Computer Applications semester 1", [course]) is course


@pytest.mark.parametrize("question", ["Show all AIT images", "Show AIT photos", "AIT image show"])
def test_plural_ait_image_requests_return_gallery_images(question):
    image = SimpleNamespace(
        image_title="AIT Library",
        image_description="Official AIT library photo",
        image_category="LIBRARY",
        facility_name="Library",
        event_name=None,
        event_date=None,
        image_url="https://www.aitindia.in/Library/sudylib.png",
        source_url="https://www.aitindia.in/facilities/library",
    )

    class Result:
        def __init__(self, rows): self.rows = rows
        def scalars(self): return self
        def all(self): return self.rows

    class Session:
        async def execute(self, statement):
            # Course catalogue lookup precedes the gallery query. The test
            # fixture contains no courses, and one approved gallery image.
            sql = str(statement).lower()
            return Result([image] if "college_gallery_images" in sql else [])
        async def get(self, _model, _id):
            # AIT's short_name is empty in the live college record; this must
            # not crash the gallery lookup when it checks college aliases.
            return SimpleNamespace(name="Ahmedabad Institute of Technology", short_name=None)

    result = asyncio.run(answer_structured_question(Session(), uuid4(), question))
    assert result is not None
    assert "1 matching photograph" in result["message_text"]
    assert result["source_citations"][0]["image_url"] == image.image_url


@pytest.mark.asyncio
async def test_chat_api_preserves_gallery_image_citation_end_to_end():
    from app.main import app
    from app.api.v1 import chat as chat_api

    college_id = uuid4()
    session_id = uuid4()
    visitor_token = "test-gallery-visitor-token"
    chat_session = SimpleNamespace(
        id=session_id,
        college_id=college_id,
        user_id=None,
        visitor_token_hash=hashlib.sha256(visitor_token.encode()).hexdigest(),
        session_title="AIT image request",
        language="en",
    )

    class FakeChatRepository:
        async def get_session(self, _session_id): return chat_session
        async def update_session(self, _session): return _session
        async def create_message(self, message):
            if getattr(message, "id", None) is None: message.id = uuid4()
            if getattr(message, "created_at", None) is None: message.created_at = datetime.now(timezone.utc)
            return message

    class FakeCollegeRepository:
        async def get_by_id(self, _college_id): return SimpleNamespace(name="Ahmedabad Institute of Technology")

    async def fake_db():
        yield object()

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[chat_api.get_db] = fake_db
    app.dependency_overrides[chat_api.get_optional_chat_user] = lambda: None
    citation = {
        "title": "AIT Library",
        "source_type": "ADMIN_VERIFIED",
        "url": "https://www.aitindia.in/facilities/library",
        "image_url": "https://www.aitindia.in/Library/sudylib.png",
        "image_category": "LIBRARY",
    }
    try:
        with patch.object(chat_api, "_set_chat_context", new=AsyncMock()), \
             patch.object(chat_api, "set_rls_context", new=AsyncMock()), \
             patch.object(chat_api, "set_chat_visitor_token", new=AsyncMock()), \
             patch.object(chat_api, "ChatRepository", return_value=FakeChatRepository()), \
             patch.object(chat_api, "CollegeRepository", return_value=FakeCollegeRepository()), \
             patch.object(chat_api, "answer_structured_question", new=AsyncMock(return_value={
                 "message_text": "Verified AIT photographs",
                 "is_verified": True,
                 "answer_source_type": "ADMIN_VERIFIED",
                 "source_citations": [citation],
             })):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    f"/api/v1/chat/sessions/{session_id}/messages",
                    headers={"X-College-ID": str(college_id), "X-Chat-Visitor-Token": visitor_token},
                    json={"message_text": "Show all AIT images", "language": "en"},
                )
        assert response.status_code == 200
        payload = response.json()["data"]
        assert payload["message_text"] == "Verified AIT photographs"
        assert payload["source_citations"][0]["image_url"] == citation["image_url"]
    finally:
        app.dependency_overrides = previous_overrides


@pytest.mark.parametrize(("semester", "expected"), [(1, "₹16,000"), (2, "₹32,000")])
def test_supplied_ait_fee_fixture(semester, expected):
    fixture = json.loads((Path(__file__).parent / "fixtures" / "academic_fee_test_data.json").read_text(encoding="utf-8"))
    course = SimpleNamespace(id=uuid4(), course_name="BCA", course_code=None, course_abbreviation=None,
                             branch_name=None, duration=None, eligibility=None, syllabus_information=None)
    fee_data = next(f for f in fixture["fees"] if f["semester"] == semester)
    fee = SimpleNamespace(id=uuid4(), course_id=course.id, semester_number=semester,
                          fee_amount=Decimal(fee_data["amount"]), currency="INR", fee_type="SEMESTER",
                          academic_year="Test fixture", effective_from=None, source_document=None,
                          source_page=None, verification_status="APPROVED")
    class Result:
        def __init__(self, value): self.value = value
        def scalars(self): return self
        def all(self): return [course]
        def first(self): return fee
    class Session:
        calls = 0
        async def execute(self, _query):
            self.calls += 1
            return Result(course if self.calls == 1 else fee)
        async def get(self, _model, _id): return SimpleNamespace(name=fixture["college"])
    result = asyncio.run(answer_structured_question(Session(), uuid4(), f"What is BCA semester {semester} fee?"))
    assert expected in result["message_text"]
    assert "Test fixture" in result["message_text"]
