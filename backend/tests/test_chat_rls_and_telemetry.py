"""Phase 2.2 — Chat Message RLS Insert & Telemetry Persistence Tests.

Behavioural tests for the chat-message insert path and AI telemetry
persistence. No real database writes occur — every DB, AI, and RLS call is
mocked, matching the style of the existing backend test suite.

Coverage (mapped to the Phase 2.2 task list):

  1. User message insertion            — test_user_message_insertion_sets_tenant_context_first
  2. Assistant message insertion       — test_assistant_message_insertion_re_establishes_tenant_context
  3. NO_RELIABLE_INFORMATION insertion  — test_no_reliable_information_response_is_persisted
  4. Unauthorized session rejection     — test_unauthorized_nonexistent_session_rejected
  5. Cross-user session rejection       — test_cross_user_session_rejected
  6. Request/session tenant context      — test_send_message_reestablishes_session_tenant_context
  7. Missing tenant identifier rejection — test_no_insert_without_authoritative_tenant_context
  8. Transaction rollback & atomicity   — test_assistant_insert_failure_fails_whole_request
                                          + test_get_db_commits_on_success_rolls_back_on_error
  9. Telemetry event persistence        — test_telemetry_event_inserted_and_flushed
                                          + test_telemetry_persistence_failure_is_observable_not_silent
                                          + test_ai_provider_event_orm_maps_canonical_telemetry_table

RLS enforcement background
--------------------------
The currently deployed database policy is college-scoped. The proposed
Phase 3A.4 patch additionally requires the authenticated user to own the chat
session. These mocked tests verify request context and application ownership
checks; they do not prove the live PostgreSQL policy behavior.

``set_rls_context`` uses transaction-local settings. The isolated database
policy validation is still required before deploying the proposed SQL patch.
"""

import contextlib
import hashlib
import logging
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1.chat import send_chat_message
from app.database import session as db_session_module
from app.models.ai import AIProviderEvent
from app.schemas.chat import SendMessageRequest

TEST_VISITOR_TOKEN = "test-anonymous-session-capability"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_chat_session(college_id, user_id=None, title="New Conversation", language="en"):
    """A lightweight stand-in for ChatSession used only to feed the handler."""
    cs = MagicMock()
    cs.college_id = college_id
    cs.user_id = user_id
    cs.visitor_token_hash = (
        hashlib.sha256(TEST_VISITOR_TOKEN.encode("utf-8")).hexdigest()
        if user_id is None else None
    )
    cs.session_title = title
    cs.language = language
    return cs


def make_user(uid, role="STUDENT"):
    u = MagicMock()
    u.id = uid
    u.role = role
    return u


def _rag_result(*, provider="GEMINI", source_type="OFFICIAL_WEBSITE", verified=True):
    return {
        "answer_text": "According to the official college records, ...",
        "is_verified": verified,
        "answer_source_type": source_type,
        "source_citations": [],
        "token_count": 30,
        "model_used": "gemini-1.5-flash",
        "answer_mode": "COLLEGE_KNOWLEDGE",
        "actual_provider": provider,
        "actual_model": "gemini-1.5-flash",
        "fallback_reason": None,
        "attempt_count": 1,
        "request_duration_ms": 450,
    }


_NO_RELIABLE_RAG_RESULT = {
    "answer_text": "I'm temporarily unable to generate a response. All AI providers are unavailable.",
    "is_verified": False,
    "answer_source_type": "NO_RELIABLE_INFORMATION",
    "source_citations": [],
    "token_count": 0,
    "model_used": "none",
    "answer_mode": "UNAVAILABLE",
    "actual_provider": "UNAVAILABLE",
    "actual_model": "none",
    "fallback_reason": "all providers exhausted",
    "attempt_count": 3,
    "request_duration_ms": 900,
}


@contextlib.contextmanager
def _chat_env(*, chat_session, rag_result, college_header=None,
              get_session_returns="SENTINEL", create_side_effect=None):
    """Patches every DB / AI / RLS dependency of send_chat_message.

    Yields a namespace carrying an ordered call log plus the individual mocks.
    The call log records ("set_rls_context", kwargs) and ("create_message", msg)
    in execution order so tests can assert ordering and authority.
    """
    log = {"calls": []}

    async def _rls(*args, **kwargs):
        log["calls"].append(("set_rls_context", kwargs))

    set_rls_mock = AsyncMock(side_effect=_rls)

    async def _default_persist(message):
        # Real flush() would apply the created_at Python default; emulate it so
        # ChatMessageResponse.model_validate(...) succeeds on the return.
        if getattr(message, "created_at", None) is None:
            message.created_at = datetime.now(timezone.utc)
        return message

    user_create = create_side_effect or _default_persist

    async def create_wrapper(message):
        # Centralised logging: a completed insert is recorded; a raising
    # side_effect propagates without appending, so a failed insert is not
        # counted as persisted.
        result = await user_create(message)
        log["calls"].append(("create_message", message))
        return result

    create_mock = AsyncMock(side_effect=create_wrapper)
    update_mock = AsyncMock(return_value=chat_session)
    gs_returns = chat_session if get_session_returns == "SENTINEL" else get_session_returns
    get_session_mock = AsyncMock(return_value=gs_returns)
    college_mock = MagicMock()
    get_college_mock = AsyncMock(return_value=college_mock)

    rag_mock = MagicMock()
    rag_mock.answer_question = AsyncMock(return_value=rag_result)

    request = MagicMock()
    request.headers.get.return_value = college_header  # str | None
    request.state.college_id = (
        chat_session.college_id if chat_session is not None else None
    )

    session = AsyncMock()

    async def _validate_user_college(_service, _user, college_id):
        return SimpleNamespace(id=college_id)

    async def _validate_college(_service, college_id):
        return SimpleNamespace(id=college_id)

    with patch("app.api.v1.chat.set_rls_context", set_rls_mock), \
            patch("app.services.tenant_service.TenantService.validate_user_access_to_college",
                  new=_validate_user_college), \
            patch("app.services.tenant_service.TenantService.get_active_college",
                  new=_validate_college), \
            patch("app.api.v1.chat.ChatRepository.create_message", create_mock), \
            patch("app.api.v1.chat.ChatRepository.update_session", update_mock), \
            patch("app.api.v1.chat.ChatRepository.get_session", get_session_mock), \
            patch("app.api.v1.chat.CollegeRepository.get_by_id", get_college_mock), \
            patch("app.api.v1.chat.rag_service", rag_mock):
        yield SimpleNamespace(
            log=log, set_rls=set_rls_mock, create=create_mock, update=update_mock,
            get_session=get_session_mock, get_college=get_college_mock, rag=rag_mock,
            college=college_mock, request=request, session=session,
        )


def _create_messages(env):
    return [m for tag, m in env.log["calls"] if tag == "create_message"]


def _rls_kwargs(env):
    return [kw for tag, kw in env.log["calls"] if tag == "set_rls_context"]


def _rls_before(env, n=0):
    """kwargs of the set_rls_context call immediately preceding the n-th
    create_message call, or None if there isn't one."""
    calls = env.log["calls"]
    create_indices = [i for i, (tag, _) in enumerate(calls) if tag == "create_message"]
    if n >= len(create_indices):
        return None
    for j in range(create_indices[n] - 1, -1, -1):
        if calls[j][0] == "set_rls_context":
            return calls[j][1]
    return None


# ---------------------------------------------------------------------------
# 1. User message insertion
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_user_message_insertion_sets_tenant_context_first():
    """The user message is inserted only after an authoritative tenant context
    (from the DB-fetched chat_sessions row) has been set."""
    college_id = uuid.uuid4()
    chat_session = make_chat_session(college_id=college_id, user_id=None)

    with _chat_env(chat_session=chat_session, rag_result=_rag_result()) as env:
        req = SendMessageRequest(message_text="What is the tuition fee?")
        await send_chat_message(
            uuid.uuid4(), req, env.request, None, env.session,
            visitor_token=TEST_VISITOR_TOKEN,
        )

    creates = _create_messages(env)
    assert len(creates) == 2
    user_msg = creates[0]
    assert user_msg.sender_role == "user"
    assert user_msg.message_text == "What is the tuition fee?"
    assert user_msg.answer_source_type == "OFFICIAL_WEBSITE"

    ctx = _rls_before(env, 0)
    assert ctx is not None, "user message inserted without a preceding set_rls_context"
    assert ctx["college_id"] == college_id          # authoritative, DB-fetched
    assert ctx["user_id"] is None                    # anonymous session


# ---------------------------------------------------------------------------
# 2. Assistant message insertion
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_assistant_message_insertion_re_establishes_tenant_context():
    """Tenant context is re-established immediately before the assistant
    insert, so the WITH CHECK on p_chat_messages_tenant passes even though the
    long-running RAG call sat between the two inserts."""
    college_id = uuid.uuid4()
    user_id = uuid.uuid4()
    chat_session = make_chat_session(college_id=college_id, user_id=user_id)

    with _chat_env(chat_session=chat_session, rag_result=_rag_result()) as env:
        req = SendMessageRequest(message_text="Admission process?")
        await send_chat_message(uuid.uuid4(), req, env.request,
                                 make_user(user_id, "STUDENT"), env.session)

    creates = _create_messages(env)
    assistant_msg = creates[1]
    assert assistant_msg.sender_role == "assistant"
    assert assistant_msg.actual_provider == "GEMINI"
    assert assistant_msg.answer_source_type == "OFFICIAL_WEBSITE"

    ctx = _rls_before(env, 1)
    assert ctx is not None, "assistant message inserted without a preceding set_rls_context"
    assert ctx["college_id"] == college_id
    assert ctx["user_id"] == user_id


# ---------------------------------------------------------------------------
# 3. NO_RELIABLE_INFORMATION insertion
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_reliable_information_response_is_persisted():
    """When every provider is unavailable the controlled NO_RELIABLE_INFORMATION
    assistant message is still persisted (not dropped), carrying the failover
    metadata so the UI can render the 'no verified information' badge."""
    college_id = uuid.uuid4()
    chat_session = make_chat_session(college_id=college_id, user_id=None)

    with _chat_env(chat_session=chat_session, rag_result=_NO_RELIABLE_RAG_RESULT) as env:
        req = SendMessageRequest(message_text="anything")
        await send_chat_message(
            uuid.uuid4(), req, env.request, None, env.session,
            visitor_token=TEST_VISITOR_TOKEN,
        )

    creates = _create_messages(env)
    assert len(creates) == 2  # user + assistant both persisted
    assistant_msg = creates[1]
    assert assistant_msg.sender_role == "assistant"
    assert assistant_msg.answer_source_type == "NO_RELIABLE_INFORMATION"
    assert assistant_msg.is_verified is False
    assert assistant_msg.actual_provider == "UNAVAILABLE"
    assert assistant_msg.answer_mode == "UNAVAILABLE"
    assert assistant_msg.attempt_count == 3


# ---------------------------------------------------------------------------
# 4. Unauthorized session rejection
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unauthorized_nonexistent_session_rejected():
    """A session id that does not exist is rejected with 404 before any insert."""
    with _chat_env(chat_session=None, rag_result=_rag_result(),
                    get_session_returns=None,
                    college_header=str(uuid.uuid4())) as env:
        req = SendMessageRequest(message_text="hi")
        with pytest.raises(HTTPException) as exc:
            await send_chat_message(
                uuid.uuid4(), req, env.request, None, env.session,
                visitor_token=TEST_VISITOR_TOKEN,
            )

    assert exc.value.status_code == 404
    assert _create_messages(env) == []  # nothing persisted


# ---------------------------------------------------------------------------
# 5. Cross-user session rejection
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cross_user_session_rejected():
    """An authenticated user cannot send to a session owned by another user."""
    college_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    other_id = uuid.uuid4()
    chat_session = make_chat_session(college_id=college_id, user_id=owner_id)

    with _chat_env(chat_session=chat_session, rag_result=_rag_result()) as env:
        req = SendMessageRequest(message_text="hi")
        with pytest.raises(HTTPException) as exc:
            await send_chat_message(uuid.uuid4(), req, env.request,
                                     make_user(other_id, "STUDENT"), env.session)

    assert exc.value.status_code == 403
    # Ownership is checked before any insert, so nothing is persisted.
    assert _create_messages(env) == []


# ---------------------------------------------------------------------------
# 6. AIT-to-RCTI tenant isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_message_reestablishes_session_tenant_context():
    """The message insert context is reset to the fetched session's tenant."""
    ait_id = uuid.uuid4()
    rcti_id = uuid.uuid4()
    chat_session = make_chat_session(college_id=rcti_id, user_id=None)

    with _chat_env(chat_session=chat_session, rag_result=_rag_result(),
                    college_header=str(ait_id)) as env:
        req = SendMessageRequest(message_text="hi")
        await send_chat_message(
            uuid.uuid4(), req, env.request, None, env.session,
            visitor_token=TEST_VISITOR_TOKEN,
        )

    all_rls = _rls_kwargs(env)
    # The request tenant is used to scope the session lookup.
    assert any(kw["college_id"] == ait_id for kw in all_rls)
    # The insert context is re-established from the fetched session.
    for n in range(len(_create_messages(env))):
        ctx = _rls_before(env, n)
        assert ctx is not None
        assert ctx["college_id"] == rcti_id


# ---------------------------------------------------------------------------
# 7. Missing tenant context rejection (application-layer guarantee)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_insert_without_authoritative_tenant_context():
    """A chat operation without a tenant identifier is rejected before access."""
    college_id = uuid.uuid4()
    chat_session = make_chat_session(college_id=college_id, user_id=None)

    with _chat_env(chat_session=chat_session, rag_result=_rag_result()) as env:
        env.request.state.college_id = None
        req = SendMessageRequest(message_text="hi")
        with pytest.raises(HTTPException) as exc:
            await send_chat_message(
                uuid.uuid4(), req, env.request, None, env.session,
                visitor_token=TEST_VISITOR_TOKEN,
            )

    assert exc.value.status_code == 400
    assert _create_messages(env) == []


# ---------------------------------------------------------------------------
# 8. Transaction rollback and atomicity
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_assistant_insert_failure_fails_whole_request():
    """If the assistant insert fails (e.g. an RLS WITH CHECK violation), the
    exception propagates out of the handler. get_db then rolls back the single
    transaction, so the already-flushed user message is NOT committed in
    isolation — the turn is atomic (both messages persist, or neither does)."""
    college_id = uuid.uuid4()
    chat_session = make_chat_session(college_id=college_id, user_id=None)

    async def boom_on_assistant(message):
        if message.sender_role == "assistant":
            raise RuntimeError("new row violates row-level security policy for table \"chat_messages\"")
        if getattr(message, "created_at", None) is None:
            message.created_at = datetime.now(timezone.utc)
        return message

    with _chat_env(chat_session=chat_session, rag_result=_rag_result(),
                    create_side_effect=boom_on_assistant) as env:
        req = SendMessageRequest(message_text="hi")
        with pytest.raises(RuntimeError):
            await send_chat_message(
                uuid.uuid4(), req, env.request, None, env.session,
                visitor_token=TEST_VISITOR_TOKEN,
            )

    # The user message was flushed, then the assistant insert raised; the whole
    # request fails, so get_db rolls back rather than committing the user row.
    env.create.assert_awaited()
    assert _rls_before(env, 0)["college_id"] == college_id  # context was set before user insert


def _fake_session_factory(mock_session):
    """AsyncSessionFactory() -> async context manager yielding mock_session."""
    ctx = AsyncMock()
    ctx.__aenter__.return_value = mock_session
    ctx.__aexit__.return_value = False
    return MagicMock(return_value=ctx)


@pytest.mark.asyncio
async def test_get_db_commits_on_success_rolls_back_on_error():
    """get_db commits exactly once on a clean request and rolls back (no commit)
    when the handler raises — the transaction boundary the RLS GUCs live in."""
    # success path
    mock_session = AsyncMock()
    with patch.object(db_session_module, "AsyncSessionFactory", _fake_session_factory(mock_session)):
        gen = db_session_module.get_db()
        assert (await gen.__anext__()) is mock_session
        with pytest.raises(StopAsyncIteration):
            await gen.__anext__()  # resumes past yield -> commit + close
        mock_session.commit.assert_awaited_once()
        mock_session.rollback.assert_not_called()
        mock_session.close.assert_awaited_once()

    # error path
    mock_session2 = AsyncMock()
    with patch.object(db_session_module, "AsyncSessionFactory", _fake_session_factory(mock_session2)):
        gen2 = db_session_module.get_db()
        await gen2.__anext__()
        with pytest.raises(ValueError):
            await gen2.athrow(ValueError, ValueError("assistant insert failed"), None)
        mock_session2.rollback.assert_awaited_once()
        mock_session2.commit.assert_not_called()
        mock_session2.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# 9. Telemetry event persistence
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_telemetry_event_inserted_and_flushed():
    """A successful telemetry write adds a fully-populated AIProviderEvent and
    flushes it, returning True."""
    from app.services.ai_provider_service import AIProviderService

    svc = AIProviderService()
    mock_session = MagicMock()
    mock_session.flush = AsyncMock()

    ok = await svc._log_telemetry(
        session=mock_session, event_type="GENERATION_SUCCESS",
        latency_ms=120, prompt_tokens=10, completion_tokens=20, error_message=None,
    )

    assert ok is True
    mock_session.add.assert_called_once()
    event = mock_session.add.call_args[0][0]
    assert isinstance(event, AIProviderEvent)
    assert event.event_type == "GENERATION_SUCCESS"
    assert event.latency_ms == 120
    assert event.prompt_tokens == 10
    assert event.completion_tokens == 20
    assert event.error_message is None
    assert event.config_id is None  # FK is optional; no provider config bound
    mock_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_telemetry_persistence_failure_is_observable_not_silent():
    """A telemetry persistence failure must NOT crash the caller (telemetry is a
    side-channel) but MUST be observable — an ERROR log with detail is emitted
    and the method returns False so the failure is detectable, never silently
    swallowed as a warning."""
    from app.services.ai_provider_service import AIProviderService

    svc_logger = logging.getLogger("app.services.ai_provider_service")
    captured = []

    class _CaptureHandler(logging.Handler):
        def emit(self, record):
            captured.append(record)

    handler = _CaptureHandler(level=logging.ERROR)
    svc_logger.addHandler(handler)
    prev_level = svc_logger.level
    svc_logger.setLevel(logging.ERROR)
    try:
        svc = AIProviderService()
        mock_session = MagicMock()
        mock_session.flush = AsyncMock(side_effect=RuntimeError("connection lost"))

        ok = await svc._log_telemetry(
            session=mock_session, event_type="GENERATION_SUCCESS",
            latency_ms=99, prompt_tokens=4, completion_tokens=6,
        )
    finally:
        svc_logger.removeHandler(handler)
        svc_logger.setLevel(prev_level)

    # Failure is detectable (not silently swallowed)...
    assert ok is False
    mock_session.flush.assert_awaited_once()
    # ...and observable as an ERROR log carrying the event detail.
    assert captured, "telemetry persistence failure must raise an ERROR log, not be silently swallowed"
    assert all(r.levelno == logging.ERROR for r in captured)
    assert any("GENERATION_SUCCESS" in r.getMessage() for r in captured)


def test_ai_provider_event_orm_maps_canonical_telemetry_table():
    """Locks the ORM mapping to the canonical table created by the project's
    migration runner (scripts/migrate_and_seed.py -> database/migrations/008 ->
    'ai_provider_events').

    The consolidated backend/migrations/001_initial_schema.sql creates a
    differently named 'provider_events' table that the runner never applies;
    every analytics / super-admin reader targets ai_provider_events via this
    ORM, so the mapping must NOT be flipped to 'provider_events' (doing so would
    break analytics_service, super_admin_repository, super_admin and the
    existing test_database_models tablename assertion).
    """
    assert AIProviderEvent.__tablename__ == "ai_provider_events"

    cols = {c.name for c in AIProviderEvent.__table__.columns}
    assert cols == {
        "id", "config_id", "event_type", "latency_ms",
        "prompt_tokens", "completion_tokens", "error_message", "created_at",
    }
    # FK to ai_provider_configs, matching the canonical SQL definition.
    fk = list(AIProviderEvent.__table__.c["config_id"].foreign_keys)[0]
    assert fk.column.table.name == "ai_provider_configs"
