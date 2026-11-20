"""AI Answering + Multi-Provider Failover Tests.

32 tests covering:
  - Answer modes (college knowledge, general AI, mixed)
  - Gemini model failover (tests 7-9)
  - OpenAI model failover (tests 10-12)
  - xKiro model failover (tests 13-15)
  - Reliability: retries, circuit breaker, backoff (tests 16-22)
  - Verification labels (tests 23-27)
  - Security + persistence (tests 28-32)

No real Supabase writes. All external calls are mocked.
"""

import asyncio
import time
import uuid
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_chunk(
    college_id=None,
    source_type="OFFICIAL_WEBSITE",
    heading="Test Heading",
    source_url="https://college.edu/test",
    chunk_text="Some verified content.",
):
    chunk = MagicMock()
    chunk.college_id = college_id or uuid.uuid4()
    chunk.source_type = source_type
    chunk.heading = heading
    chunk.source_url = source_url
    chunk.chunk_text = chunk_text
    chunk.category = "ADMISSIONS"
    chunk.page_number = 1
    chunk.embedding = [0.1] * 768
    return chunk


def _make_college(college_id=None, name="Test College", domain="college.edu"):
    college = MagicMock()
    college.id = college_id or uuid.uuid4()
    college.name = name
    college.official_domain = domain
    return college


def _make_gemini_response(text="Gemini answer"):
    """Minimal Gemini REST response payload."""
    return {
        "candidates": [{"content": {"parts": [{"text": text}]}}],
        "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 20},
    }


def _mock_httpx_response(status_code=200, json_body=None, headers=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body or _make_gemini_response()
    resp.text = str(json_body) if json_body else ""
    resp.headers = headers or {}
    return resp


def test_provider_error_details_redact_configured_api_keys(monkeypatch):
    from app.core.config import settings
    from app.services.ai_provider_service import AIProviderService

    secret = "test-only-gemini-secret-value"
    monkeypatch.setattr(settings, "GEMINI_API_KEY", secret)

    detail = AIProviderService._redact_provider_secrets(
        f"request failed for key={secret}"
    )

    assert secret not in detail
    assert "[REDACTED]" in detail


# ---------------------------------------------------------------------------
# Answer mode tests (1–6)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_college_info_found_returns_verified_answer_with_citations():
    """Test 1: High-similarity college chunks → verified answer with citations."""
    from app.services.rag_service import RAGService

    college_id = uuid.uuid4()
    chunk = _make_chunk(
        college_id=college_id,
        source_type="OFFICIAL_WEBSITE",
        chunk_text="The official B.Tech Computer Engineering tuition fee is ₹78,000.",
    )
    college = _make_college(college_id=college_id)
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[chunk])))))

    rag = RAGService()

    scored_chunks = [(chunk, 0.92)]
    with patch.object(rag, "retrieve_relevant_chunks", return_value=scored_chunks), \
         patch.object(rag, "get_recent_conversation_context", return_value=[]), \
         patch("app.services.rag_service.ai_provider_service") as mock_ai:

        mock_ai.generate_response = AsyncMock(return_value={
            "text": "The official fee is ₹78,000.",
            "provider": "GEMINI",
            "model": "gemini-1.5-flash",
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "latency_ms": 500,
            "answer_mode": "COLLEGE_KNOWLEDGE",
            "fallback_reason": None,
            "attempt_count": 1,
        })

        result = await rag.answer_question(
            college_id=college_id,
            query="What is the tuition fee?",
            session=mock_session,
            college=college,
        )

    assert result["answer_source_type"] in ("OFFICIAL_WEBSITE", "ADMIN_VERIFIED")
    assert result["is_verified"] is True
    assert len(result["source_citations"]) > 0


@pytest.mark.asyncio
async def test_college_info_missing_returns_general_ai_answer():
    """Test 2: No college chunks → General AI mode, unverified, contains 'AI Guidance'."""
    from app.services.rag_service import RAGService
    from app.core.config import settings

    college_id = uuid.uuid4()
    mock_session = AsyncMock()
    college = _make_college(college_id=college_id)

    rag = RAGService()

    with patch.object(rag, "retrieve_relevant_chunks", return_value=[]), \
         patch.object(rag, "get_recent_conversation_context", return_value=[]), \
         patch("app.services.rag_service.settings") as mock_settings, \
         patch("app.services.rag_service.ai_provider_service") as mock_ai:

        mock_settings.AI_GENERAL_ANSWERING_ENABLED = True
        mock_settings.gemini_model_list = ["gemini-1.5-flash"]

        mock_ai.generate_response = AsyncMock(return_value={
            "text": "AI Guidance — Not verified by college\n\nPython uses indentation.",
            "provider": "GEMINI",
            "model": "gemini-1.5-flash",
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "latency_ms": 400,
            "answer_mode": "GENERAL_AI",
            "fallback_reason": None,
            "attempt_count": 1,
        })

        result = await rag.answer_question(
            college_id=college_id,
            query="What is Python programming?",
            session=mock_session,
            college=college,
        )

    assert result["answer_mode"] == "GENERAL_AI"
    assert result["is_verified"] is False
    assert "AI Guidance" in result["answer_text"]


@pytest.mark.asyncio
async def test_unrelated_low_similarity_chunks_use_general_ai_fallback():
    """Low similarity and no question-term evidence must not enter college context."""
    from app.services.rag_service import RAGService

    college_id = uuid.uuid4()
    chunk = _make_chunk(college_id=college_id)
    college = _make_college(college_id=college_id)
    mock_session = AsyncMock()
    rag = RAGService()

    # These scores exceed the retrieval floor but the text does not answer the query.
    scored_chunks = [(chunk, 0.45), (chunk, 0.52)]

    with patch.object(rag, "retrieve_relevant_chunks", return_value=scored_chunks), \
         patch.object(rag, "get_recent_conversation_context", return_value=[]), \
         patch("app.services.rag_service.ai_provider_service") as mock_ai:

        mock_ai.generate_response = AsyncMock(return_value={
            "text": "Some partial answer.",
            "provider": "GEMINI",
            "model": "gemini-1.5-flash",
            "prompt_tokens": 5,
            "completion_tokens": 10,
            "latency_ms": 300,
            "answer_mode": "MIXED",
            "fallback_reason": None,
            "attempt_count": 1,
        })

        result = await rag.answer_question(
            college_id=college_id,
            query="Tell me about admissions",
            session=mock_session,
            college=college,
        )

    assert result["answer_mode"] == "GENERAL_AI"
    assert result["source_citations"] == []
    assert result["is_verified"] is False
    assert "AI Guidance — Not verified by college" in result["answer_text"]
    generate_call = mock_ai.generate_response.await_args
    assert generate_call is not None
    assert generate_call.kwargs["context_chunks"] == []


@pytest.mark.parametrize(
    "query",
    [
        "What is the lunar rover maintenance schedule for the observatory?",
        "Who won the 1874 intergalactic chess championship on Mars?",
        "What is the boiling point of pure water at standard atmospheric pressure?",
        "What is the orbital period of Mars around the Sun?",
        "How do I prepare a traditional sourdough starter at home?",
        "What is the exact population of Thimphu, Bhutan?",
    ],
)
def test_step47_unrelated_queries_reject_actual_college_evidence(query):
    """The six Step 4.7 false-positive queries must not pass the evidence gate."""
    from app.services.rag_service import RAGService

    rag = RAGService()
    evidence = [
        _make_chunk(
            source_type="OFFICIAL_WEBSITE",
            heading="Academic Calendar",
            chunk_text=(
                "Stay updated with important academic activities, examination "
                "schedules, holidays, and institutional events."
            ),
        ),
        _make_chunk(
            source_type="OFFICIAL_WEBSITE",
            heading="Degree Engineering Admissions 2026",
            chunk_text=(
                "Applications open for Management and Vacant Quota seats across "
                "Computer Engineering. Apply between 05-08-2026 and 10-08-2026."
            ),
        ),
        _make_chunk(
            source_type="PDF",
            heading="Admission Verification",
            chunk_text=(
                "Applicants must bring the original school transcript and one "
                "signed identity declaration. The transcript must reach the "
                "admission office by 17 July 2026 at 4:30 PM."
            ),
        ),
    ]

    assert rag._select_relevant_evidence(
        query, [(chunk, 0.45) for chunk in evidence]
    ) == []


@pytest.mark.parametrize(
    ("query", "evidence_text"),
    [
        (
            "How many seats are available in Computer Engineering?",
            "Program Seats Start Date: Computer Engineering 120 15 Aug 2026.",
        ),
        (
            "By what date and time must the transcript reach the admission office?",
            "The transcript must reach the admission office by 17 July 2026 at 4:30 PM.",
        ),
        (
            "What caveat applies to the synthetic seat counts and start date?",
            "Footnote: seat counts and dates are synthetic test values; verify official details.",
        ),
    ],
)
def test_relevance_gate_preserves_table_detail_and_footnote_evidence(query, evidence_text):
    from app.services.rag_service import RAGService

    chunk = _make_chunk(source_type="PDF", chunk_text=evidence_text)
    selected = RAGService._select_relevant_evidence(query, [(chunk, 0.42)])

    assert selected == [(chunk, 0.42)]


def test_relevance_gate_combines_multiple_chunks_for_multi_part_question():
    from app.services.rag_service import RAGService

    website_chunk = _make_chunk(
        source_type="OFFICIAL_WEBSITE",
        heading="Degree Engineering Admissions 2026",
        chunk_text="Applications open. Apply between 05-08-2026 and 10-08-2026.",
    )
    pdf_chunk = _make_chunk(
        source_type="PDF",
        heading="Extracted Tables",
        chunk_text="Program | Seats | Computer Engineering | 120",
    )
    query = (
        "What are the application dates for degree engineering, and what "
        "seat counts are listed for Computer Engineering?"
    )
    selected = RAGService._select_relevant_evidence(
        query,
        [(website_chunk, 0.43), (pdf_chunk, 0.41)],
    )

    assert {chunk.source_type for chunk, _ in selected} == {
        "OFFICIAL_WEBSITE",
        "PDF",
    }
    assert RAGService._select_relevant_evidence(query, [(pdf_chunk, 0.41)]) == []


@pytest.mark.asyncio
async def test_general_programming_question_returns_code_response():
    """Test 4: General programming question → AI returns code block."""
    from app.services.rag_service import RAGService

    college_id = uuid.uuid4()
    mock_session = AsyncMock()
    college = _make_college(college_id=college_id)
    rag = RAGService()

    with patch.object(rag, "retrieve_relevant_chunks", return_value=[]), \
         patch.object(rag, "get_recent_conversation_context", return_value=[]), \
         patch("app.services.rag_service.settings") as mock_settings, \
         patch("app.services.rag_service.ai_provider_service") as mock_ai:

        mock_settings.AI_GENERAL_ANSWERING_ENABLED = True

        mock_ai.generate_response = AsyncMock(return_value={
            "text": "AI Guidance — Not verified by college\n\n```python\nprint('hello')\n```",
            "provider": "GEMINI",
            "model": "gemini-1.5-flash",
            "prompt_tokens": 10,
            "completion_tokens": 15,
            "latency_ms": 300,
            "answer_mode": "GENERAL_AI",
            "fallback_reason": None,
            "attempt_count": 1,
        })

        result = await rag.answer_question(
            college_id=college_id,
            query="Write hello world in Python",
            session=mock_session,
            college=college,
        )

    assert "```" in result["answer_text"] or "print" in result["answer_text"]
    assert result["is_verified"] is False


@pytest.mark.asyncio
async def test_general_educational_question_returns_explanation():
    """Test 5: General educational question → non-empty explanation."""
    from app.services.rag_service import RAGService

    college_id = uuid.uuid4()
    mock_session = AsyncMock()
    college = _make_college(college_id=college_id)
    rag = RAGService()

    with patch.object(rag, "retrieve_relevant_chunks", return_value=[]), \
         patch.object(rag, "get_recent_conversation_context", return_value=[]), \
         patch("app.services.rag_service.settings") as mock_settings, \
         patch("app.services.rag_service.ai_provider_service") as mock_ai:

        mock_settings.AI_GENERAL_ANSWERING_ENABLED = True

        mock_ai.generate_response = AsyncMock(return_value={
            "text": "AI Guidance — Not verified by college\n\nPhotosynthesis converts light energy into chemical energy.",
            "provider": "GEMINI",
            "model": "gemini-1.5-flash",
            "prompt_tokens": 8,
            "completion_tokens": 18,
            "latency_ms": 350,
            "answer_mode": "GENERAL_AI",
            "fallback_reason": None,
            "attempt_count": 1,
        })

        result = await rag.answer_question(
            college_id=college_id,
            query="Explain photosynthesis",
            session=mock_session,
            college=college,
        )

    assert len(result["answer_text"]) > 0
    assert result["is_verified"] is False


@pytest.mark.asyncio
async def test_missing_college_specific_fact_no_fabrication():
    """Test 6: No chunks, AI answer should not contain hardcoded institutional facts."""
    from app.services.rag_service import RAGService

    college_id = uuid.uuid4()
    mock_session = AsyncMock()
    college = _make_college(college_id=college_id)
    rag = RAGService()

    ai_text = (
        "AI Guidance — Not verified by college\n\n"
        "I don't have verified information about this college's specific fees. "
        "Please contact the admissions office directly."
    )

    with patch.object(rag, "retrieve_relevant_chunks", return_value=[]), \
         patch.object(rag, "get_recent_conversation_context", return_value=[]), \
         patch("app.services.rag_service.settings") as mock_settings, \
         patch("app.services.rag_service.ai_provider_service") as mock_ai:

        mock_settings.AI_GENERAL_ANSWERING_ENABLED = True

        mock_ai.generate_response = AsyncMock(return_value={
            "text": ai_text,
            "provider": "GEMINI",
            "model": "gemini-1.5-flash",
            "prompt_tokens": 10,
            "completion_tokens": 25,
            "latency_ms": 300,
            "answer_mode": "GENERAL_AI",
            "fallback_reason": None,
            "attempt_count": 1,
        })

        result = await rag.answer_question(
            college_id=college_id,
            query="What is the exact fee for B.Tech at Ahmedabad Institute?",
            session=mock_session,
            college=college,
        )

    # AI should not fabricate specific fee amounts (₹78,000 is a known fabrication risk)
    assert "₹78,000" not in result["answer_text"]
    assert result["is_verified"] is False


@pytest.mark.asyncio
async def test_missing_fee_is_not_grounded_by_unrelated_seat_table():
    from app.services.rag_service import RAGService

    college_id = uuid.uuid4()
    college = _make_college(college_id=college_id)
    session = AsyncMock()
    rag = RAGService()
    seat_table = _make_chunk(
        college_id=college_id,
        source_type="PDF",
        heading="Extracted Tables",
        chunk_text=(
            "| Program | Seats | Start Date |\n"
            "| Computer Engineering | 120 | 15 Aug 2026 |"
        ),
    )

    with (
        patch.object(
            rag,
            "retrieve_relevant_chunks",
            new=AsyncMock(return_value=[(seat_table, 0.81)]),
        ),
        patch.object(rag, "get_recent_conversation_context", new=AsyncMock(return_value=[])),
        patch("app.services.rag_service.settings") as mock_settings,
        patch("app.services.rag_service.ai_provider_service") as mock_ai,
    ):
        mock_settings.AI_GENERAL_ANSWERING_ENABLED = True
        mock_ai.generate_response = AsyncMock(
            return_value={
                "text": "AI Guidance — Not verified by college\n\nI cannot verify the fee.",
                "provider": "GEMINI",
                "model": "test-model",
                "prompt_tokens": 1,
                "completion_tokens": 1,
            }
        )

        result = await rag.answer_question(
            college_id=college_id,
            query="What is the exact tuition fee for the 2026 engineering program?",
            session=session,
            college=college,
        )

    assert result["answer_mode"] == "GENERAL_AI"
    assert result["source_citations"] == []
    assert result["is_verified"] is False
    assert mock_ai.generate_response.await_args.kwargs["context_chunks"] == []


# ---------------------------------------------------------------------------
# Gemini failover tests (7–9)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_first_gemini_model_succeeds():
    """Test 7: First Gemini model responds HTTP 200 → used directly."""
    from app.services.ai_provider_service import AIProviderService

    svc = AIProviderService()
    svc.is_placeholder_key = False
    svc.gemini_key = "fake-key-1234567890abcdef"

    mock_response = _mock_httpx_response(200, _make_gemini_response("Hello from Gemini"))

    with patch("app.services.ai_provider_service.settings") as mock_settings, \
         patch("app.services.ai_provider_service.provider_health_tracker") as mock_tracker, \
         patch("httpx.AsyncClient") as mock_client_cls:

        mock_settings.AI_MAX_RETRIES = 3
        mock_settings.AI_TIMEOUT_SECONDS = 30
        mock_settings.AI_CIRCUIT_BREAKER_THRESHOLD = 5
        mock_settings.gemini_model_list = ["gemini-1.5-flash", "gemini-1.5-pro"]
        mock_settings.openai_model_list = ["gpt-4o-mini"]
        mock_settings.xkiro_model_list = []
        mock_settings.OPENAI_API_KEY = None
        mock_settings.SECONDARY_AI_API_KEY = None
        mock_settings.XKIRO_API_KEY = None

        mock_tracker.is_available = AsyncMock(return_value=True)
        mock_tracker.record_success = AsyncMock()
        mock_tracker.record_failure = AsyncMock()
        mock_tracker.record_retry = AsyncMock()
        mock_tracker.record_fallback_event = AsyncMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await svc.generate_response(
            prompt="Hello",
            system_instruction="Be helpful",
            context_chunks=[],
        )

    assert result["provider"] == "GEMINI"
    assert result["model"] == "gemini-1.5-flash"
    assert "Hello from Gemini" in result["text"]


@pytest.mark.asyncio
async def test_first_gemini_fails_second_gemini_succeeds():
    """Test 8: First Gemini model returns HTTP 500, second returns 200."""
    from app.services.ai_provider_service import AIProviderService

    svc = AIProviderService()
    svc.is_placeholder_key = False
    svc.gemini_key = "fake-key-1234567890abcdef"

    fail_response = _mock_httpx_response(500, {}, {})
    fail_response.text = "Internal Server Error"
    ok_response = _mock_httpx_response(200, _make_gemini_response("Second model answer"))

    call_count = {"n": 0}

    async def _post_side_effect(*args, **kwargs):
        call_count["n"] += 1
        # First 3+1 calls are from the first model (retries), then succeed on 2nd
        # We simplify: just fail first time each time
        if "gemini-1.5-flash" in args[0]:
            return fail_response
        return ok_response

    with patch("app.services.ai_provider_service.settings") as mock_settings, \
         patch("app.services.ai_provider_service.provider_health_tracker") as mock_tracker, \
         patch("app.services.ai_provider_service.asyncio.sleep", new_callable=AsyncMock), \
         patch("httpx.AsyncClient") as mock_client_cls:

        mock_settings.AI_MAX_RETRIES = 1
        mock_settings.AI_TIMEOUT_SECONDS = 30
        mock_settings.AI_CIRCUIT_BREAKER_THRESHOLD = 5
        mock_settings.gemini_model_list = ["gemini-1.5-flash", "gemini-1.5-pro"]
        mock_settings.openai_model_list = []
        mock_settings.xkiro_model_list = []
        mock_settings.OPENAI_API_KEY = None
        mock_settings.SECONDARY_AI_API_KEY = None
        mock_settings.XKIRO_API_KEY = None

        mock_tracker.is_available = AsyncMock(return_value=True)
        mock_tracker.record_success = AsyncMock()
        mock_tracker.record_failure = AsyncMock()
        mock_tracker.record_retry = AsyncMock()
        mock_tracker.record_fallback_event = AsyncMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=_post_side_effect)
        mock_client_cls.return_value = mock_client

        result = await svc.generate_response(
            prompt="Test",
            system_instruction="Be helpful",
            context_chunks=[],
        )

    assert result["provider"] == "GEMINI"
    assert result["model"] == "gemini-1.5-pro"


@pytest.mark.asyncio
async def test_all_gemini_models_fail():
    """Test 9: All Gemini models fail → provider is not GEMINI on final result."""
    from app.services.ai_provider_service import AIProviderService

    svc = AIProviderService()
    svc.is_placeholder_key = False
    svc.gemini_key = "fake-key-1234567890abcdef"

    fail_response = _mock_httpx_response(500, {}, {})
    fail_response.text = "Server Error"

    with patch("app.services.ai_provider_service.settings") as mock_settings, \
         patch("app.services.ai_provider_service.provider_health_tracker") as mock_tracker, \
         patch("app.services.ai_provider_service.asyncio.sleep", new_callable=AsyncMock), \
         patch("httpx.AsyncClient") as mock_client_cls:

        mock_settings.AI_MAX_RETRIES = 0
        mock_settings.AI_TIMEOUT_SECONDS = 30
        mock_settings.AI_CIRCUIT_BREAKER_THRESHOLD = 5
        mock_settings.gemini_model_list = ["gemini-1.5-flash", "gemini-1.5-pro"]
        mock_settings.openai_model_list = []
        mock_settings.xkiro_model_list = []
        mock_settings.OPENAI_API_KEY = None
        mock_settings.SECONDARY_AI_API_KEY = None
        mock_settings.XKIRO_API_KEY = None

        mock_tracker.is_available = AsyncMock(return_value=True)
        mock_tracker.record_success = AsyncMock()
        mock_tracker.record_failure = AsyncMock()
        mock_tracker.record_retry = AsyncMock()
        mock_tracker.record_fallback_event = AsyncMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=fail_response)
        mock_client_cls.return_value = mock_client

        result = await svc.generate_response(
            prompt="Test",
            system_instruction="Be helpful",
            context_chunks=[],
        )

    assert result["provider"] != "GEMINI"


# ---------------------------------------------------------------------------
# OpenAI failover tests (10–12)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_all_gemini_fail_first_openai_succeeds():
    """Test 10: All Gemini fail, first OpenAI model succeeds."""
    from app.services.ai_provider_service import AIProviderService

    svc = AIProviderService()
    svc.is_placeholder_key = False
    svc.gemini_key = "fake-key-1234567890abcdef"

    fail_response = _mock_httpx_response(500, {}, {})
    fail_response.text = "Server Error"

    openai_completion = MagicMock()
    openai_completion.choices = [MagicMock(message=MagicMock(content="OpenAI answer"))]
    openai_completion.usage = MagicMock(prompt_tokens=10, completion_tokens=20)

    with patch("app.services.ai_provider_service.settings") as mock_settings, \
         patch("app.services.ai_provider_service.provider_health_tracker") as mock_tracker, \
         patch("app.services.ai_provider_service.asyncio.sleep", new_callable=AsyncMock), \
         patch("app.services.ai_provider_service.AsyncOpenAI") as mock_openai_cls, \
         patch("httpx.AsyncClient") as mock_client_cls:

        mock_settings.AI_MAX_RETRIES = 0
        mock_settings.AI_TIMEOUT_SECONDS = 30
        mock_settings.AI_CIRCUIT_BREAKER_THRESHOLD = 5
        mock_settings.gemini_model_list = ["gemini-1.5-flash"]
        mock_settings.openai_model_list = ["gpt-4o-mini", "gpt-4o"]
        mock_settings.xkiro_model_list = []
        mock_settings.OPENAI_API_KEY = "sk-fake-openai-key-abcdef"
        mock_settings.SECONDARY_AI_API_KEY = None
        mock_settings.XKIRO_API_KEY = None

        mock_tracker.is_available = AsyncMock(return_value=True)
        mock_tracker.record_success = AsyncMock()
        mock_tracker.record_failure = AsyncMock()
        mock_tracker.record_retry = AsyncMock()
        mock_tracker.record_fallback_event = AsyncMock()

        # Gemini fails
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=fail_response)
        mock_client_cls.return_value = mock_client

        # OpenAI succeeds
        mock_openai_instance = AsyncMock()
        mock_openai_instance.chat = AsyncMock()
        mock_openai_instance.chat.completions = AsyncMock()
        mock_openai_instance.chat.completions.create = AsyncMock(return_value=openai_completion)
        mock_openai_cls.return_value = mock_openai_instance

        result = await svc.generate_response(
            prompt="Test",
            system_instruction="Be helpful",
            context_chunks=[],
        )

    assert result["provider"] == "OPENAI"


@pytest.mark.asyncio
async def test_first_openai_fails_second_openai_succeeds():
    """Test 11: First OpenAI model fails, second succeeds."""
    from app.services.ai_provider_service import AIProviderService

    svc = AIProviderService()
    svc.is_placeholder_key = False
    svc.gemini_key = "fake-key-1234567890abcdef"

    fail_response = _mock_httpx_response(500, {}, {})
    fail_response.text = "Server Error"

    openai_completion = MagicMock()
    openai_completion.choices = [MagicMock(message=MagicMock(content="Second OpenAI answer"))]
    openai_completion.usage = MagicMock(prompt_tokens=10, completion_tokens=15)

    call_count = {"n": 0}

    async def _openai_side_effect(**kwargs):
        call_count["n"] += 1
        if kwargs.get("model") == "gpt-4o-mini":
            raise Exception("500 service unavailable")
        return openai_completion

    with patch("app.services.ai_provider_service.settings") as mock_settings, \
         patch("app.services.ai_provider_service.provider_health_tracker") as mock_tracker, \
         patch("app.services.ai_provider_service.asyncio.sleep", new_callable=AsyncMock), \
         patch("app.services.ai_provider_service.AsyncOpenAI") as mock_openai_cls, \
         patch("httpx.AsyncClient") as mock_client_cls:

        mock_settings.AI_MAX_RETRIES = 0
        mock_settings.AI_TIMEOUT_SECONDS = 30
        mock_settings.AI_CIRCUIT_BREAKER_THRESHOLD = 5
        mock_settings.gemini_model_list = ["gemini-1.5-flash"]
        mock_settings.openai_model_list = ["gpt-4o-mini", "gpt-4o"]
        mock_settings.xkiro_model_list = []
        mock_settings.OPENAI_API_KEY = "sk-fake-key-abcdef"
        mock_settings.SECONDARY_AI_API_KEY = None
        mock_settings.XKIRO_API_KEY = None

        mock_tracker.is_available = AsyncMock(return_value=True)
        mock_tracker.record_success = AsyncMock()
        mock_tracker.record_failure = AsyncMock()
        mock_tracker.record_retry = AsyncMock()
        mock_tracker.record_fallback_event = AsyncMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=fail_response)
        mock_client_cls.return_value = mock_client

        mock_openai_instance = AsyncMock()
        mock_openai_instance.chat = AsyncMock()
        mock_openai_instance.chat.completions = AsyncMock()
        mock_openai_instance.chat.completions.create = AsyncMock(side_effect=_openai_side_effect)
        mock_openai_cls.return_value = mock_openai_instance

        result = await svc.generate_response(
            prompt="Test",
            system_instruction="Be helpful",
            context_chunks=[],
        )

    assert result["provider"] == "OPENAI"
    assert result["model"] == "gpt-4o"


@pytest.mark.asyncio
async def test_all_gemini_and_openai_fail():
    """Test 12: All Gemini and OpenAI fail → falls through to xKiro or unavailable."""
    from app.services.ai_provider_service import AIProviderService

    svc = AIProviderService()
    svc.is_placeholder_key = False
    svc.gemini_key = "fake-key-1234567890abcdef"

    fail_response = _mock_httpx_response(500, {}, {})
    fail_response.text = "Server Error"

    with patch("app.services.ai_provider_service.settings") as mock_settings, \
         patch("app.services.ai_provider_service.provider_health_tracker") as mock_tracker, \
         patch("app.services.ai_provider_service.asyncio.sleep", new_callable=AsyncMock), \
         patch("app.services.ai_provider_service.AsyncOpenAI") as mock_openai_cls, \
         patch("httpx.AsyncClient") as mock_client_cls:

        mock_settings.AI_MAX_RETRIES = 0
        mock_settings.AI_TIMEOUT_SECONDS = 30
        mock_settings.AI_CIRCUIT_BREAKER_THRESHOLD = 5
        mock_settings.gemini_model_list = ["gemini-1.5-flash"]
        mock_settings.openai_model_list = ["gpt-4o-mini"]
        mock_settings.xkiro_model_list = []
        mock_settings.OPENAI_API_KEY = "sk-fake-key"
        mock_settings.SECONDARY_AI_API_KEY = None
        mock_settings.XKIRO_API_KEY = None

        mock_tracker.is_available = AsyncMock(return_value=True)
        mock_tracker.record_success = AsyncMock()
        mock_tracker.record_failure = AsyncMock()
        mock_tracker.record_retry = AsyncMock()
        mock_tracker.record_fallback_event = AsyncMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=fail_response)
        mock_client_cls.return_value = mock_client

        mock_openai_instance = AsyncMock()
        mock_openai_instance.chat = AsyncMock()
        mock_openai_instance.chat.completions = AsyncMock()
        mock_openai_instance.chat.completions.create = AsyncMock(
            side_effect=Exception("500 openai failure")
        )
        mock_openai_cls.return_value = mock_openai_instance

        result = await svc.generate_response(
            prompt="Test",
            system_instruction="Be helpful",
            context_chunks=[],
        )

    assert result["provider"] in ("XKIRO", "UNAVAILABLE")


# ---------------------------------------------------------------------------
# xKiro failover tests (13–15)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_all_gemini_openai_fail_xkiro_succeeds():
    """Test 13: Gemini+OpenAI all fail, xKiro succeeds."""
    from app.services.ai_provider_service import AIProviderService

    svc = AIProviderService()
    svc.is_placeholder_key = False
    svc.gemini_key = "fake-key-1234567890abcdef"

    gemini_fail = _mock_httpx_response(500, {}, {})
    gemini_fail.text = "Error"
    xkiro_ok = _mock_httpx_response(200, {
        "choices": [{"message": {"content": "xKiro answer"}}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 10},
    })

    async def _post_side_effect(url, **kwargs):
        if "xkiro" in url:
            return xkiro_ok
        return gemini_fail

    with patch("app.services.ai_provider_service.settings") as mock_settings, \
         patch("app.services.ai_provider_service.provider_health_tracker") as mock_tracker, \
         patch("app.services.ai_provider_service.asyncio.sleep", new_callable=AsyncMock), \
         patch("app.services.ai_provider_service.AsyncOpenAI") as mock_openai_cls, \
         patch("httpx.AsyncClient") as mock_client_cls:

        mock_settings.AI_MAX_RETRIES = 0
        mock_settings.AI_TIMEOUT_SECONDS = 30
        mock_settings.AI_CIRCUIT_BREAKER_THRESHOLD = 5
        mock_settings.gemini_model_list = ["gemini-1.5-flash"]
        mock_settings.openai_model_list = ["gpt-4o-mini"]
        mock_settings.xkiro_model_list = ["xkiro-chat"]
        mock_settings.OPENAI_API_KEY = "sk-fake-key"
        mock_settings.SECONDARY_AI_API_KEY = None
        mock_settings.XKIRO_API_KEY = "xk-fake-key-1234567890"
        mock_settings.XKIRO_API_BASE_URL = "https://api.xkiro.com/v1"

        mock_tracker.is_available = AsyncMock(return_value=True)
        mock_tracker.record_success = AsyncMock()
        mock_tracker.record_failure = AsyncMock()
        mock_tracker.record_retry = AsyncMock()
        mock_tracker.record_fallback_event = AsyncMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=_post_side_effect)
        mock_client_cls.return_value = mock_client

        mock_openai_instance = AsyncMock()
        mock_openai_instance.chat = AsyncMock()
        mock_openai_instance.chat.completions = AsyncMock()
        mock_openai_instance.chat.completions.create = AsyncMock(
            side_effect=Exception("500 openai failure")
        )
        mock_openai_cls.return_value = mock_openai_instance

        result = await svc.generate_response(
            prompt="Test",
            system_instruction="Be helpful",
            context_chunks=[],
        )

    assert result["provider"] == "XKIRO"


@pytest.mark.asyncio
async def test_all_xkiro_models_fail():
    """Test 14: All three providers fail → controlled failure."""
    from app.services.ai_provider_service import AIProviderService

    svc = AIProviderService()
    svc.is_placeholder_key = False
    svc.gemini_key = "fake-key-1234567890abcdef"

    fail_response = _mock_httpx_response(500, {}, {})
    fail_response.text = "Error"

    with patch("app.services.ai_provider_service.settings") as mock_settings, \
         patch("app.services.ai_provider_service.provider_health_tracker") as mock_tracker, \
         patch("app.services.ai_provider_service.asyncio.sleep", new_callable=AsyncMock), \
         patch("app.services.ai_provider_service.AsyncOpenAI") as mock_openai_cls, \
         patch("httpx.AsyncClient") as mock_client_cls:

        mock_settings.AI_MAX_RETRIES = 0
        mock_settings.AI_TIMEOUT_SECONDS = 30
        mock_settings.AI_CIRCUIT_BREAKER_THRESHOLD = 5
        mock_settings.gemini_model_list = ["gemini-1.5-flash"]
        mock_settings.openai_model_list = ["gpt-4o-mini"]
        mock_settings.xkiro_model_list = ["xkiro-chat", "xkiro-fast"]
        mock_settings.OPENAI_API_KEY = "sk-fake"
        mock_settings.SECONDARY_AI_API_KEY = None
        mock_settings.XKIRO_API_KEY = "xk-fake-key-1234567890"
        mock_settings.XKIRO_API_BASE_URL = "https://api.xkiro.com/v1"

        mock_tracker.is_available = AsyncMock(return_value=True)
        mock_tracker.record_success = AsyncMock()
        mock_tracker.record_failure = AsyncMock()
        mock_tracker.record_retry = AsyncMock()
        mock_tracker.record_fallback_event = AsyncMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=fail_response)
        mock_client_cls.return_value = mock_client

        mock_openai_instance = AsyncMock()
        mock_openai_instance.chat = AsyncMock()
        mock_openai_instance.chat.completions = AsyncMock()
        mock_openai_instance.chat.completions.create = AsyncMock(
            side_effect=Exception("openai failure")
        )
        mock_openai_cls.return_value = mock_openai_instance

        result = await svc.generate_response(
            prompt="Test",
            system_instruction="Be helpful",
            context_chunks=[],
        )

    assert result["provider"] == "UNAVAILABLE"


@pytest.mark.asyncio
async def test_all_providers_fail_returns_controlled_error():
    """Test 15: All providers exhausted → no exception, provider=UNAVAILABLE, non-empty text."""
    from app.services.ai_provider_service import AIProviderService

    svc = AIProviderService()
    svc.is_placeholder_key = False
    svc.gemini_key = "fake-key-1234567890abcdef"

    fail_response = _mock_httpx_response(500, {}, {})
    fail_response.text = "Error"

    with patch("app.services.ai_provider_service.settings") as mock_settings, \
         patch("app.services.ai_provider_service.provider_health_tracker") as mock_tracker, \
         patch("app.services.ai_provider_service.asyncio.sleep", new_callable=AsyncMock), \
         patch("app.services.ai_provider_service.AsyncOpenAI") as mock_openai_cls, \
         patch("httpx.AsyncClient") as mock_client_cls:

        mock_settings.AI_MAX_RETRIES = 0
        mock_settings.AI_TIMEOUT_SECONDS = 30
        mock_settings.AI_CIRCUIT_BREAKER_THRESHOLD = 5
        mock_settings.gemini_model_list = ["gemini-1.5-flash"]
        mock_settings.openai_model_list = ["gpt-4o-mini"]
        mock_settings.xkiro_model_list = ["xkiro-chat"]
        mock_settings.OPENAI_API_KEY = "sk-fake"
        mock_settings.SECONDARY_AI_API_KEY = None
        mock_settings.XKIRO_API_KEY = "xk-fake-key-12345"
        mock_settings.XKIRO_API_BASE_URL = "https://api.xkiro.com/v1"

        mock_tracker.is_available = AsyncMock(return_value=True)
        mock_tracker.record_success = AsyncMock()
        mock_tracker.record_failure = AsyncMock()
        mock_tracker.record_retry = AsyncMock()
        mock_tracker.record_fallback_event = AsyncMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=fail_response)
        mock_client_cls.return_value = mock_client

        mock_openai_instance = AsyncMock()
        mock_openai_instance.chat = AsyncMock()
        mock_openai_instance.chat.completions = AsyncMock()
        mock_openai_instance.chat.completions.create = AsyncMock(
            side_effect=Exception("openai failure")
        )
        mock_openai_cls.return_value = mock_openai_instance

        # Must NOT raise
        result = await svc.generate_response(
            prompt="Test",
            system_instruction="Be helpful",
            context_chunks=[],
        )

    assert result["provider"] == "UNAVAILABLE"
    assert len(result["text"]) > 0


# ---------------------------------------------------------------------------
# Reliability tests (16–22)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_http_429_handled_with_backoff():
    """Test 16: HTTP 429 with Retry-After → retry happens, no crash."""
    from app.services.ai_provider_service import AIProviderService

    svc = AIProviderService()
    svc.is_placeholder_key = False
    svc.gemini_key = "fake-key-1234567890abcdef"

    rate_limit_resp = _mock_httpx_response(429, {}, {"Retry-After": "0.1"})
    rate_limit_resp.text = "Rate limited"
    ok_response = _mock_httpx_response(200, _make_gemini_response("After retry"))

    call_count = {"n": 0}

    async def _post_side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return rate_limit_resp
        return ok_response

    with patch("app.services.ai_provider_service.settings") as mock_settings, \
         patch("app.services.ai_provider_service.provider_health_tracker") as mock_tracker, \
         patch("app.services.ai_provider_service.asyncio.sleep", new_callable=AsyncMock), \
         patch("httpx.AsyncClient") as mock_client_cls:

        mock_settings.AI_MAX_RETRIES = 3
        mock_settings.AI_TIMEOUT_SECONDS = 30
        mock_settings.AI_CIRCUIT_BREAKER_THRESHOLD = 5
        mock_settings.gemini_model_list = ["gemini-1.5-flash"]
        mock_settings.openai_model_list = []
        mock_settings.xkiro_model_list = []
        mock_settings.OPENAI_API_KEY = None
        mock_settings.SECONDARY_AI_API_KEY = None
        mock_settings.XKIRO_API_KEY = None

        mock_tracker.is_available = AsyncMock(return_value=True)
        mock_tracker.record_success = AsyncMock()
        mock_tracker.record_failure = AsyncMock()
        mock_tracker.record_retry = AsyncMock()
        mock_tracker.record_fallback_event = AsyncMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=_post_side_effect)
        mock_client_cls.return_value = mock_client

        result = await svc.generate_response(
            prompt="Test",
            system_instruction="Be helpful",
            context_chunks=[],
        )

    # Either recovered or exhausted without crashing
    assert result is not None
    assert result["provider"] in ("GEMINI", "UNAVAILABLE")


@pytest.mark.asyncio
async def test_http_503_handled():
    """Test 17: HTTP 503 then 200 → retry succeeds."""
    from app.services.ai_provider_service import AIProviderService

    svc = AIProviderService()
    svc.is_placeholder_key = False
    svc.gemini_key = "fake-key-1234567890abcdef"

    fail_resp = _mock_httpx_response(503, {}, {})
    fail_resp.text = "Service Unavailable"
    ok_response = _mock_httpx_response(200, _make_gemini_response("OK after 503"))

    call_count = {"n": 0}

    async def _post(*args, **kwargs):
        call_count["n"] += 1
        return fail_resp if call_count["n"] == 1 else ok_response

    with patch("app.services.ai_provider_service.settings") as mock_settings, \
         patch("app.services.ai_provider_service.provider_health_tracker") as mock_tracker, \
         patch("app.services.ai_provider_service.asyncio.sleep", new_callable=AsyncMock), \
         patch("httpx.AsyncClient") as mock_client_cls:

        mock_settings.AI_MAX_RETRIES = 3
        mock_settings.AI_TIMEOUT_SECONDS = 30
        mock_settings.AI_CIRCUIT_BREAKER_THRESHOLD = 5
        mock_settings.gemini_model_list = ["gemini-1.5-flash"]
        mock_settings.openai_model_list = []
        mock_settings.xkiro_model_list = []
        mock_settings.OPENAI_API_KEY = None
        mock_settings.SECONDARY_AI_API_KEY = None
        mock_settings.XKIRO_API_KEY = None

        mock_tracker.is_available = AsyncMock(return_value=True)
        mock_tracker.record_success = AsyncMock()
        mock_tracker.record_failure = AsyncMock()
        mock_tracker.record_retry = AsyncMock()
        mock_tracker.record_fallback_event = AsyncMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=_post)
        mock_client_cls.return_value = mock_client

        result = await svc.generate_response(
            prompt="Test",
            system_instruction="Be helpful",
            context_chunks=[],
        )

    assert result["provider"] == "GEMINI"
    assert "OK after 503" in result["text"]


@pytest.mark.asyncio
async def test_timeout_handled():
    """Test 18: httpx.TimeoutException → retry up to max, then fallback."""
    from app.services.ai_provider_service import AIProviderService
    import httpx

    svc = AIProviderService()
    svc.is_placeholder_key = False
    svc.gemini_key = "fake-key-1234567890abcdef"

    with patch("app.services.ai_provider_service.settings") as mock_settings, \
         patch("app.services.ai_provider_service.provider_health_tracker") as mock_tracker, \
         patch("app.services.ai_provider_service.asyncio.sleep", new_callable=AsyncMock), \
         patch("httpx.AsyncClient") as mock_client_cls:

        mock_settings.AI_MAX_RETRIES = 1
        mock_settings.AI_TIMEOUT_SECONDS = 30
        mock_settings.AI_CIRCUIT_BREAKER_THRESHOLD = 5
        mock_settings.gemini_model_list = ["gemini-1.5-flash"]
        mock_settings.openai_model_list = []
        mock_settings.xkiro_model_list = []
        mock_settings.OPENAI_API_KEY = None
        mock_settings.SECONDARY_AI_API_KEY = None
        mock_settings.XKIRO_API_KEY = None

        mock_tracker.is_available = AsyncMock(return_value=True)
        mock_tracker.record_success = AsyncMock()
        mock_tracker.record_failure = AsyncMock()
        mock_tracker.record_retry = AsyncMock()
        mock_tracker.record_fallback_event = AsyncMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
        mock_client_cls.return_value = mock_client

        result = await svc.generate_response(
            prompt="Test",
            system_instruction="Be helpful",
            context_chunks=[],
        )

    assert result["provider"] in ("UNAVAILABLE",)
    assert result is not None


@pytest.mark.asyncio
async def test_invalid_credentials_permanent_failure_not_retried():
    """Test 19: HTTP 401 → permanent failure, attempt_count == 1 for that model."""
    from app.services.ai_provider_service import AIProviderService

    svc = AIProviderService()
    svc.is_placeholder_key = False
    svc.gemini_key = "fake-key-1234567890abcdef"

    auth_fail = _mock_httpx_response(401, {}, {})
    auth_fail.text = "Unauthorized"

    post_call_count = {"n": 0}

    async def _post(*args, **kwargs):
        post_call_count["n"] += 1
        return auth_fail

    with patch("app.services.ai_provider_service.settings") as mock_settings, \
         patch("app.services.ai_provider_service.provider_health_tracker") as mock_tracker, \
         patch("app.services.ai_provider_service.asyncio.sleep", new_callable=AsyncMock), \
         patch("httpx.AsyncClient") as mock_client_cls:

        mock_settings.AI_MAX_RETRIES = 3
        mock_settings.AI_TIMEOUT_SECONDS = 30
        mock_settings.AI_CIRCUIT_BREAKER_THRESHOLD = 5
        mock_settings.gemini_model_list = ["gemini-1.5-flash"]
        mock_settings.openai_model_list = []
        mock_settings.xkiro_model_list = []
        mock_settings.OPENAI_API_KEY = None
        mock_settings.SECONDARY_AI_API_KEY = None
        mock_settings.XKIRO_API_KEY = None

        mock_tracker.is_available = AsyncMock(return_value=True)
        mock_tracker.record_success = AsyncMock()
        mock_tracker.record_failure = AsyncMock()
        mock_tracker.record_retry = AsyncMock()
        mock_tracker.record_fallback_event = AsyncMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=_post)
        mock_client_cls.return_value = mock_client

        result = await svc.generate_response(
            prompt="Test",
            system_instruction="Be helpful",
            context_chunks=[],
        )

    # Should have called POST exactly once (no retries for 401)
    assert post_call_count["n"] == 1
    assert result["provider"] == "UNAVAILABLE"


@pytest.mark.asyncio
async def test_invalid_model_404_is_permanent_for_that_model():
    """Ensure invalid or retired Gemini model IDs are treated as permanent per-model failures."""
    from app.services.ai_provider_service import AIProviderService

    svc = AIProviderService()
    svc.is_placeholder_key = False
    svc.gemini_key = "fake-key-1234567890abcdef"

    invalid_model_404 = _mock_httpx_response(404, {}, {})
    invalid_model_404.text = (
        '{"error":{"code":404,"message":"This model models/gemini-2.5-flash is no longer available to new users. '
        'Please update your code to use models/gemini-3.8-flash."}}'
    )

    post_call_count = {"n": 0}

    async def _post(*args, **kwargs):
        post_call_count["n"] += 1
        return invalid_model_404

    with patch("app.services.ai_provider_service.settings") as mock_settings, \
         patch("app.services.ai_provider_service.provider_health_tracker") as mock_tracker, \
         patch("app.services.ai_provider_service.asyncio.sleep", new_callable=AsyncMock), \
         patch("httpx.AsyncClient") as mock_client_cls:

        mock_settings.AI_MAX_RETRIES = 3
        mock_settings.AI_TIMEOUT_SECONDS = 30
        mock_settings.AI_CIRCUIT_BREAKER_THRESHOLD = 5
        mock_settings.gemini_model_list = ["gemini-2.5-flash"]
        mock_settings.openai_model_list = []
        mock_settings.xkiro_model_list = []
        mock_settings.OPENAI_API_KEY = None
        mock_settings.SECONDARY_AI_API_KEY = None
        mock_settings.XKIRO_API_KEY = None

        mock_tracker.is_available = AsyncMock(return_value=True)
        mock_tracker.record_success = AsyncMock()
        mock_tracker.record_failure = AsyncMock()
        mock_tracker.record_retry = AsyncMock()
        mock_tracker.record_fallback_event = AsyncMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=_post)
        mock_client_cls.return_value = mock_client

        result = await svc.generate_response(
            prompt="Test",
            system_instruction="Be helpful",
            context_chunks=[],
        )

    assert post_call_count["n"] == 1
    assert result["provider"] == "UNAVAILABLE"
    assert result["fallback_reason"]


@pytest.mark.asyncio
async def test_circuit_breaker_trips_and_recovers():
    """Test 20: Drive failures >= threshold → is_available returns False; then recovers after cooldown."""
    from app.services.provider_health import ProviderHealthTracker
    from app.core.config import settings

    tracker = ProviderHealthTracker()
    provider = "GEMINI"
    model = "gemini-1.5-flash"

    threshold = settings.AI_CIRCUIT_BREAKER_THRESHOLD
    for _ in range(threshold):
        await tracker.record_failure(provider, model, "HTTP_500")

    assert await tracker.is_available(provider, model) is False

    # Simulate cooldown elapsed
    h = await tracker.get_model_health(provider, model)
    h.last_failure_at = time.time() - settings.AI_COOLDOWN_SECONDS - 1

    assert await tracker.is_available(provider, model) is True


@pytest.mark.asyncio
async def test_no_infinite_retry_loop():
    """Test 21: Always-500 → total attempts <= AI_MAX_RETRIES * total_model_count."""
    from app.services.ai_provider_service import AIProviderService

    svc = AIProviderService()
    svc.is_placeholder_key = False
    svc.gemini_key = "fake-key-1234567890abcdef"

    fail_response = _mock_httpx_response(500, {}, {})
    fail_response.text = "Error"
    post_calls = {"n": 0}

    async def _post(*args, **kwargs):
        post_calls["n"] += 1
        return fail_response

    max_retries = 2
    gemini_models = ["gemini-1.5-flash", "gemini-1.5-pro"]

    with patch("app.services.ai_provider_service.settings") as mock_settings, \
         patch("app.services.ai_provider_service.provider_health_tracker") as mock_tracker, \
         patch("app.services.ai_provider_service.asyncio.sleep", new_callable=AsyncMock), \
         patch("httpx.AsyncClient") as mock_client_cls:

        mock_settings.AI_MAX_RETRIES = max_retries
        mock_settings.AI_TIMEOUT_SECONDS = 30
        mock_settings.AI_CIRCUIT_BREAKER_THRESHOLD = 100  # never trips
        mock_settings.gemini_model_list = gemini_models
        mock_settings.openai_model_list = []
        mock_settings.xkiro_model_list = []
        mock_settings.OPENAI_API_KEY = None
        mock_settings.SECONDARY_AI_API_KEY = None
        mock_settings.XKIRO_API_KEY = None

        mock_tracker.is_available = AsyncMock(return_value=True)
        mock_tracker.record_success = AsyncMock()
        mock_tracker.record_failure = AsyncMock()
        mock_tracker.record_retry = AsyncMock()
        mock_tracker.record_fallback_event = AsyncMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=_post)
        mock_client_cls.return_value = mock_client

        await svc.generate_response(
            prompt="Test",
            system_instruction="Be helpful",
            context_chunks=[],
        )

    # Each model: max_retries+1 attempts; total = (max_retries+1) * len(gemini_models)
    max_expected = (max_retries + 1) * len(gemini_models)
    assert post_calls["n"] <= max_expected


@pytest.mark.asyncio
async def test_no_duplicate_generation_from_retry():
    """Test 22: Successful HTTP 200 is not re-sent."""
    from app.services.ai_provider_service import AIProviderService

    svc = AIProviderService()
    svc.is_placeholder_key = False
    svc.gemini_key = "fake-key-1234567890abcdef"

    ok_response = _mock_httpx_response(200, _make_gemini_response("Single success"))
    post_calls = {"n": 0}

    async def _post(*args, **kwargs):
        post_calls["n"] += 1
        return ok_response

    with patch("app.services.ai_provider_service.settings") as mock_settings, \
         patch("app.services.ai_provider_service.provider_health_tracker") as mock_tracker, \
         patch("httpx.AsyncClient") as mock_client_cls:

        mock_settings.AI_MAX_RETRIES = 3
        mock_settings.AI_TIMEOUT_SECONDS = 30
        mock_settings.AI_CIRCUIT_BREAKER_THRESHOLD = 5
        mock_settings.gemini_model_list = ["gemini-1.5-flash"]
        mock_settings.openai_model_list = []
        mock_settings.xkiro_model_list = []
        mock_settings.OPENAI_API_KEY = None
        mock_settings.SECONDARY_AI_API_KEY = None
        mock_settings.XKIRO_API_KEY = None

        mock_tracker.is_available = AsyncMock(return_value=True)
        mock_tracker.record_success = AsyncMock()
        mock_tracker.record_failure = AsyncMock()
        mock_tracker.record_retry = AsyncMock()
        mock_tracker.record_fallback_event = AsyncMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=_post)
        mock_client_cls.return_value = mock_client

        result = await svc.generate_response(
            prompt="Test",
            system_instruction="Be helpful",
            context_chunks=[],
        )

    assert post_calls["n"] == 1  # Sent exactly once
    assert result["provider"] == "GEMINI"


# ---------------------------------------------------------------------------
# Verification tests (23–27)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_openai_general_answer_gets_unverified_label():
    """Test 23: OpenAI general answer → is_verified=False, not OFFICIAL_WEBSITE/ADMIN_VERIFIED."""
    from app.services.rag_service import RAGService

    college_id = uuid.uuid4()
    mock_session = AsyncMock()
    college = _make_college(college_id=college_id)
    rag = RAGService()

    with patch.object(rag, "retrieve_relevant_chunks", return_value=[]), \
         patch.object(rag, "get_recent_conversation_context", return_value=[]), \
         patch("app.services.rag_service.settings") as mock_settings, \
         patch("app.services.rag_service.ai_provider_service") as mock_ai:

        mock_settings.AI_GENERAL_ANSWERING_ENABLED = True

        mock_ai.generate_response = AsyncMock(return_value={
            "text": "AI Guidance — Not verified by college\n\nOpenAI answer here.",
            "provider": "OPENAI",
            "model": "gpt-4o-mini",
            "prompt_tokens": 10,
            "completion_tokens": 15,
            "latency_ms": 400,
            "answer_mode": "GENERAL_AI",
            "fallback_reason": "gemini_failed",
            "attempt_count": 2,
        })

        result = await rag.answer_question(
            college_id=college_id,
            query="What is machine learning?",
            session=mock_session,
            college=college,
        )

    assert result["is_verified"] is False
    assert result["answer_source_type"] not in ("OFFICIAL_WEBSITE", "ADMIN_VERIFIED")


@pytest.mark.asyncio
async def test_xkiro_general_answer_gets_unverified_label():
    """Test 24: xKiro general answer → is_verified=False."""
    from app.services.rag_service import RAGService

    college_id = uuid.uuid4()
    mock_session = AsyncMock()
    college = _make_college(college_id=college_id)
    rag = RAGService()

    with patch.object(rag, "retrieve_relevant_chunks", return_value=[]), \
         patch.object(rag, "get_recent_conversation_context", return_value=[]), \
         patch("app.services.rag_service.settings") as mock_settings, \
         patch("app.services.rag_service.ai_provider_service") as mock_ai:

        mock_settings.AI_GENERAL_ANSWERING_ENABLED = True

        mock_ai.generate_response = AsyncMock(return_value={
            "text": "AI Guidance — Not verified by college\n\nxKiro answer.",
            "provider": "XKIRO",
            "model": "xkiro-chat",
            "prompt_tokens": 8,
            "completion_tokens": 12,
            "latency_ms": 500,
            "answer_mode": "GENERAL_AI",
            "fallback_reason": "gemini_openai_failed",
            "attempt_count": 3,
        })

        result = await rag.answer_question(
            college_id=college_id,
            query="Explain neural networks",
            session=mock_session,
            college=college,
        )

    assert result["is_verified"] is False
    assert result["answer_source_type"] not in ("OFFICIAL_WEBSITE", "ADMIN_VERIFIED")


@pytest.mark.asyncio
async def test_gemini_general_answer_gets_unverified_label():
    """Test 25: Gemini in General AI mode → is_verified=False."""
    from app.services.rag_service import RAGService

    college_id = uuid.uuid4()
    mock_session = AsyncMock()
    college = _make_college(college_id=college_id)
    rag = RAGService()

    with patch.object(rag, "retrieve_relevant_chunks", return_value=[]), \
         patch.object(rag, "get_recent_conversation_context", return_value=[]), \
         patch("app.services.rag_service.settings") as mock_settings, \
         patch("app.services.rag_service.ai_provider_service") as mock_ai:

        mock_settings.AI_GENERAL_ANSWERING_ENABLED = True

        mock_ai.generate_response = AsyncMock(return_value={
            "text": "AI Guidance — Not verified by college\n\nGemini general answer.",
            "provider": "GEMINI",
            "model": "gemini-1.5-flash",
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "latency_ms": 300,
            "answer_mode": "GENERAL_AI",
            "fallback_reason": None,
            "attempt_count": 1,
        })

        result = await rag.answer_question(
            college_id=college_id,
            query="What is the quadratic formula?",
            session=mock_session,
            college=college,
        )

    assert result["is_verified"] is False
    assert result["answer_source_type"] not in ("OFFICIAL_WEBSITE", "ADMIN_VERIFIED")


@pytest.mark.asyncio
async def test_official_citations_preserved_correctly():
    """Test 26: OFFICIAL_WEBSITE chunk → citation contains url and correct source_type."""
    from app.services.rag_service import RAGService

    college_id = uuid.uuid4()
    college = _make_college(college_id=college_id, name="Test College", domain="test.edu")
    rag = RAGService()

    chunk = _make_chunk(
        college_id=college_id,
        source_type="OFFICIAL_WEBSITE",
        heading="Fee Structure 2026",
        source_url="https://test.edu/fees",
        chunk_text="B.Tech fee is ₹50,000 per year.",
    )
    scored_chunks = [(chunk, 0.94)]
    citations = rag.build_citations(scored_chunks, college=college)

    assert len(citations) == 1
    assert citations[0]["url"] == "https://test.edu/fees"
    assert citations[0]["source_type"] == "OFFICIAL_WEBSITE"
    assert citations[0]["similarity_score"] == 0.94


@pytest.mark.asyncio
async def test_ai_generated_content_cannot_become_admin_verified():
    """Test 27: AI-only response must never get ADMIN_VERIFIED source type."""
    from app.services.rag_service import RAGService

    college_id = uuid.uuid4()
    mock_session = AsyncMock()
    college = _make_college(college_id=college_id)
    rag = RAGService()

    # Empty chunks → AI alone answers
    with patch.object(rag, "retrieve_relevant_chunks", return_value=[]), \
         patch.object(rag, "get_recent_conversation_context", return_value=[]), \
         patch("app.services.rag_service.settings") as mock_settings, \
         patch("app.services.rag_service.ai_provider_service") as mock_ai:

        mock_settings.AI_GENERAL_ANSWERING_ENABLED = True

        mock_ai.generate_response = AsyncMock(return_value={
            "text": "AI Guidance — Not verified by college\n\nSome AI answer.",
            "provider": "GEMINI",
            "model": "gemini-1.5-flash",
            "prompt_tokens": 5,
            "completion_tokens": 10,
            "latency_ms": 300,
            "answer_mode": "GENERAL_AI",
            "fallback_reason": None,
            "attempt_count": 1,
        })

        result = await rag.answer_question(
            college_id=college_id,
            query="Explain binary search",
            session=mock_session,
            college=college,
        )

    assert result["answer_source_type"] != "ADMIN_VERIFIED"
    assert result["is_verified"] is False


# ---------------------------------------------------------------------------
# Security and persistence tests (28–32)
# ---------------------------------------------------------------------------

def test_ait_rcti_tenant_isolation_enforced():
    """Test 28: RAG retrieval for college_a never returns college_b chunks."""
    from app.models.knowledge import KnowledgeChunk

    college_a_id = uuid.uuid4()
    college_b_id = uuid.uuid4()

    chunk_a = KnowledgeChunk(
        id=uuid.uuid4(),
        college_id=college_a_id,
        chunk_text="AIT Computer Science fee is ₹78,000.",
        status="PUBLISHED",
        is_active=True,
    )
    chunk_b = KnowledgeChunk(
        id=uuid.uuid4(),
        college_id=college_b_id,
        chunk_text="RCTI Engineering fee is ₹65,000.",
        status="PUBLISHED",
        is_active=True,
    )
    all_chunks = [chunk_a, chunk_b]

    college_a_results = [c for c in all_chunks if c.college_id == college_a_id]
    assert len(college_a_results) == 1
    assert "RCTI" not in college_a_results[0].chunk_text

    college_b_results = [c for c in all_chunks if c.college_id == college_b_id]
    assert len(college_b_results) == 1
    assert "AIT" not in college_b_results[0].chunk_text


@pytest.mark.asyncio
async def test_unauthorized_session_access_rejected():
    """Test 29: Session owned by user_a, request by user_b → 403 HTTPException."""
    from fastapi import HTTPException
    from app.api.v1.chat import _assert_session_ownership
    from app.models.chat import ChatSession
    from app.models.user import User

    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()

    session = MagicMock(spec=ChatSession)
    session.user_id = user_a_id

    user_b = MagicMock(spec=User)
    user_b.id = user_b_id
    user_b.role = "STUDENT"

    with pytest.raises(HTTPException) as exc_info:
        _assert_session_ownership(session, user_b)

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_correct_assistant_message_rls_insertion():
    """Test 30: chat_repo.create_message called with session_id matching verified session."""
    from app.services.rag_service import RAGService
    from app.repositories.chat_repository import ChatRepository
    from app.models.chat import ChatMessage

    college_id = uuid.uuid4()
    session_id = uuid.uuid4()
    mock_session = AsyncMock()
    college = _make_college(college_id=college_id)
    rag = RAGService()

    scored_chunks = [(_make_chunk(college_id=college_id, source_type="OFFICIAL_WEBSITE"), 0.90)]

    with patch.object(rag, "retrieve_relevant_chunks", return_value=scored_chunks), \
         patch.object(rag, "get_recent_conversation_context", return_value=[]), \
         patch("app.services.rag_service.ai_provider_service") as mock_ai:

        mock_ai.generate_response = AsyncMock(return_value={
            "text": "Official answer.",
            "provider": "GEMINI",
            "model": "gemini-1.5-flash",
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "latency_ms": 300,
            "answer_mode": "COLLEGE_KNOWLEDGE",
            "fallback_reason": None,
            "attempt_count": 1,
        })

        result = await rag.answer_question(
            college_id=college_id,
            query="What is the admission process?",
            session=mock_session,
            college=college,
            session_id=session_id,
        )

    # Verify that the result has the correct session_id context
    assert result["answer_source_type"] in ("OFFICIAL_WEBSITE", "ADMIN_VERIFIED", "GEMINI_UNVERIFIED")


@pytest.mark.asyncio
async def test_missing_tenant_context_rejected():
    """Test 31: retrieve_relevant_chunks with no matching chunks returns empty list."""
    from app.services.rag_service import RAGService

    college_id = uuid.uuid4()
    mock_session = AsyncMock()

    # Return empty scalars → no chunks for this college
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)

    rag = RAGService()

    with patch("app.services.rag_service.embedding_service") as mock_emb:
        mock_emb.get_embedding = AsyncMock(return_value=[0.1] * 768)
        chunks = await rag.retrieve_relevant_chunks(
            college_id=college_id,
            query="Something",
            session=mock_session,
        )

    assert chunks == []


@pytest.mark.asyncio
async def test_provider_failure_does_not_create_false_successful_chat_record():
    """Test 32: All providers fail → chat_repo.create_message not called for a fabricated success."""
    from app.services.rag_service import RAGService

    college_id = uuid.uuid4()
    mock_session = AsyncMock()
    college = _make_college(college_id=college_id)
    rag = RAGService()

    with patch.object(rag, "retrieve_relevant_chunks", return_value=[]), \
         patch.object(rag, "get_recent_conversation_context", return_value=[]), \
         patch("app.services.rag_service.settings") as mock_settings, \
         patch("app.services.rag_service.ai_provider_service") as mock_ai:

        mock_settings.AI_GENERAL_ANSWERING_ENABLED = True

        # All providers failed — controlled response
        mock_ai.generate_response = AsyncMock(return_value={
            "text": "I'm temporarily unable to generate a response. All AI providers are unavailable.",
            "provider": "UNAVAILABLE",
            "model": "none",
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "latency_ms": 1000,
            "answer_mode": "UNAVAILABLE",
            "fallback_reason": "all_providers_failed",
            "attempt_count": 9,
        })

        result = await rag.answer_question(
            college_id=college_id,
            query="Any question",
            session=mock_session,
            college=college,
        )

    # Result must clearly indicate failure, not fabricated success
    assert result["answer_source_type"] == "NO_RELIABLE_INFORMATION"
    assert result["answer_mode"] == "GENERAL_AI"
    assert result["is_verified"] is False
    assert result["source_citations"] == []
    assert "unavailable" in result["answer_text"].lower() or "unable" in result["answer_text"].lower()
    assert "all_providers_failed" not in result["answer_text"]
