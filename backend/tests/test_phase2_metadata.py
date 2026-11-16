"""Phase 2 — AI Failover Metadata Tests.

9 tests covering:
  1. Old ENUM values still present in ORM PG_ENUM definition
  2. Safe-proxy pre-migration mapping (AI_NEW_ENUM_ENABLED=False)
  3. New ENUM mapping post-migration (_NEW_ENUM_VALUES_AVAILABLE=True)
  4. All six metadata fields persisted on ChatMessage object
  5. request_duration_ms taken from latency_ms in AI provider result
  6. actual_provider/model recorded after failover
  7. Existing chat history loads without AttributeError on new fields
  8. resolve_source_type_hierarchy unaffected by provider — WEBSITE still → OFFICIAL_WEBSITE
  9. set_rls_context called before create_message in send_chat_message

No real database writes. All DB and external calls are mocked.
"""

import uuid
import inspect
from unittest.mock import AsyncMock, MagicMock, patch
import pytest


# ---------------------------------------------------------------------------
# Test 1: Old ENUM values still present in ORM PG_ENUM definition
# ---------------------------------------------------------------------------

def test_old_enum_values_still_valid():
    """The five original ENUM values remain in the ChatMessage PG_ENUM definition."""
    from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
    from app.models.chat import ChatMessage

    # Find the answer_source_type column's type
    col = ChatMessage.__table__.c["answer_source_type"]
    pg_enum = col.type
    enums = pg_enum.enums

    for expected in (
        "OFFICIAL_WEBSITE",
        "ADMIN_VERIFIED",
        "GEMINI_UNVERIFIED",
        "SECONDARY_AI_FALLBACK",
        "NO_RELIABLE_INFORMATION",
    ):
        assert expected in enums, f"Expected ENUM value '{expected}' missing from PG_ENUM"


# ---------------------------------------------------------------------------
# Test 2: Safe-proxy pre-migration (AI_NEW_ENUM_ENABLED=False)
# ---------------------------------------------------------------------------

def test_safe_proxy_pre_migration():
    """When _NEW_ENUM_VALUES_AVAILABLE=False, providers map to legacy safe-proxy values."""
    import app.services.rag_service as rag_module

    rag = rag_module.RAGService()

    with patch.object(rag_module, "_NEW_ENUM_VALUES_AVAILABLE", False):
        assert rag._source_type_for_general_ai("OPENAI") == "SECONDARY_AI_FALLBACK"
        assert rag._source_type_for_general_ai("XKIRO") == "SECONDARY_AI_FALLBACK"
        assert rag._source_type_for_general_ai("GEMINI") == "GEMINI_UNVERIFIED"
        assert rag._source_type_for_general_ai("UNAVAILABLE") == "NO_RELIABLE_INFORMATION"
        assert rag._source_type_for_general_ai("OFFLINE_GROUNDED") == "GEMINI_UNVERIFIED"


# ---------------------------------------------------------------------------
# Test 3: New ENUM mapping post-migration (_NEW_ENUM_VALUES_AVAILABLE=True)
# ---------------------------------------------------------------------------

def test_new_enum_post_migration():
    """When _NEW_ENUM_VALUES_AVAILABLE=True, providers map to new ENUM values."""
    import app.services.rag_service as rag_module

    rag = rag_module.RAGService()

    with patch.object(rag_module, "_NEW_ENUM_VALUES_AVAILABLE", True):
        assert rag._source_type_for_general_ai("OPENAI") == "OPENAI_UNVERIFIED"
        assert rag._source_type_for_general_ai("XKIRO") == "XKIRO_UNVERIFIED"
        assert rag._source_type_for_general_ai("GEMINI") == "AI_GUIDANCE"
        assert rag._source_type_for_general_ai("OFFLINE_GROUNDED") == "AI_GUIDANCE"
        assert rag._source_type_for_general_ai("UNAVAILABLE") == "NO_RELIABLE_INFORMATION"


# ---------------------------------------------------------------------------
# Test 4: All six metadata fields persisted on ChatMessage object
# ---------------------------------------------------------------------------

def test_all_six_metadata_fields_persisted():
    """ChatMessage accepts all 6 new fields and they are readable back as set."""
    from app.models.chat import ChatMessage

    session_id = uuid.uuid4()
    msg = ChatMessage(
        id=uuid.uuid4(),
        session_id=session_id,
        sender_role="assistant",
        message_text="Test answer",
        is_verified=False,
        answer_source_type="SECONDARY_AI_FALLBACK",
        source_citations=[],
        token_count=10,
        model_used="gpt-4o-mini",
        answer_mode="GENERAL_AI",
        actual_provider="OPENAI",
        actual_model="gpt-4o-mini",
        fallback_reason="gemini_timeout",
        attempt_count=3,
        request_duration_ms=750,
    )

    assert msg.answer_mode == "GENERAL_AI"
    assert msg.actual_provider == "OPENAI"
    assert msg.actual_model == "gpt-4o-mini"
    assert msg.fallback_reason == "gemini_timeout"
    assert msg.attempt_count == 3
    assert msg.request_duration_ms == 750


# ---------------------------------------------------------------------------
# Test 5: request_duration_ms populated from latency_ms
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_request_duration_ms_from_latency():
    """rag_service.answer_question returns request_duration_ms == ai_result['latency_ms']."""
    import app.services.rag_service as rag_module
    from app.services.rag_service import RAGService

    college_id = uuid.uuid4()
    mock_session = AsyncMock()
    college = MagicMock()
    college.id = college_id
    college.name = "Test College"
    college.official_domain = "college.edu"

    rag = RAGService()

    with patch.object(rag, "retrieve_relevant_chunks", return_value=[]), \
         patch.object(rag, "get_recent_conversation_context", return_value=[]), \
         patch("app.services.rag_service.settings") as mock_settings, \
         patch("app.services.rag_service.ai_provider_service") as mock_ai:

        mock_settings.AI_GENERAL_ANSWERING_ENABLED = True

        mock_ai.generate_response = AsyncMock(return_value={
            "text": "Some answer text",
            "provider": "GEMINI",
            "model": "gemini-1.5-flash",
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "latency_ms": 450,
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

    assert result.get("request_duration_ms") == 450


# ---------------------------------------------------------------------------
# Test 6: actual_provider and actual_model recorded after failover
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_actual_provider_model_recorded_after_failover():
    """actual_provider and actual_model in rag_result match what ai_provider_service returned."""
    from app.services.rag_service import RAGService

    college_id = uuid.uuid4()
    mock_session = AsyncMock()
    college = MagicMock()
    college.id = college_id
    college.name = "Test College"
    college.official_domain = "college.edu"

    rag = RAGService()

    with patch.object(rag, "retrieve_relevant_chunks", return_value=[]), \
         patch.object(rag, "get_recent_conversation_context", return_value=[]), \
         patch("app.services.rag_service.settings") as mock_settings, \
         patch("app.services.rag_service.ai_provider_service") as mock_ai:

        mock_settings.AI_GENERAL_ANSWERING_ENABLED = True

        mock_ai.generate_response = AsyncMock(return_value={
            "text": "OpenAI answer text",
            "provider": "OPENAI",
            "model": "gpt-4o-mini",
            "prompt_tokens": 15,
            "completion_tokens": 25,
            "latency_ms": 320,
            "answer_mode": "GENERAL_AI",
            "fallback_reason": "gemini::gemini-1.5-flash circuit-open",
            "attempt_count": 2,
        })

        result = await rag.answer_question(
            college_id=college_id,
            query="What is machine learning?",
            session=mock_session,
            college=college,
        )

    assert result["actual_provider"] == "OPENAI"
    assert result["actual_model"] == "gpt-4o-mini"


# ---------------------------------------------------------------------------
# Test 7: Existing chat history loads without AttributeError
# ---------------------------------------------------------------------------

def test_existing_chat_history_loads():
    """ChatMessage with all new fields as None/0 raises no AttributeError on access."""
    from app.models.chat import ChatMessage

    session_id = uuid.uuid4()
    msg = ChatMessage(
        id=uuid.uuid4(),
        session_id=session_id,
        sender_role="assistant",
        message_text="Old message from before migration",
        is_verified=True,
        answer_source_type="OFFICIAL_WEBSITE",
        source_citations=[],
        token_count=5,
        model_used=None,
    )

    # Simulate loading a pre-migration row: new fields are None/default
    # (SQLAlchemy sets them to None if not passed to constructor)
    _ = msg.answer_mode
    _ = msg.actual_provider
    _ = msg.actual_model
    _ = msg.fallback_reason
    _ = msg.attempt_count
    _ = msg.request_duration_ms
    # No AttributeError means the fields exist on the model


# ---------------------------------------------------------------------------
# Test 8: resolve_source_type_hierarchy unaffected — WEBSITE chunks → OFFICIAL_WEBSITE
# ---------------------------------------------------------------------------

def test_tenant_isolation_unaffected():
    """resolve_source_type_hierarchy returns OFFICIAL_WEBSITE for WEBSITE chunks
    regardless of which provider was used."""
    from app.services.rag_service import RAGService

    rag = RAGService()

    website_chunk = MagicMock()
    website_chunk.source_type = "WEBSITE"

    scored = [(website_chunk, 0.85)]

    for provider in ("GEMINI", "OPENAI", "XKIRO", "SECONDARY_AI_FALLBACK"):
        result = rag.resolve_source_type_hierarchy(scored, provider)
        assert result == "OFFICIAL_WEBSITE", (
            f"Expected OFFICIAL_WEBSITE for provider={provider}, got {result}"
        )


# ---------------------------------------------------------------------------
# Test 9: set_rls_context called before create_message in send_chat_message
# ---------------------------------------------------------------------------

def test_rls_insert_preserved():
    """send_chat_message calls set_rls_context before create_message in its source code."""
    import app.api.v1.chat as chat_module
    source = inspect.getsource(chat_module.send_chat_message)

    # Verify that set_rls_context appears before create_message in function body
    rls_pos = source.find("set_rls_context")
    create_pos = source.rfind("create_message")

    assert rls_pos != -1, "set_rls_context not found in send_chat_message"
    assert create_pos != -1, "create_message not found in send_chat_message"
    assert rls_pos < create_pos, (
        "set_rls_context must appear before create_message in send_chat_message"
    )
