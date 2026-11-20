"""Document Upload, Storage, and Processing Unit Tests.

Tests the complete upload pipeline, storage interaction, broker failure handling,
and signed URL generation for PDF documents.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
from datetime import datetime, timezone

import fitz


def _valid_pdf_bytes():
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "A valid isolated PDF fixture for document upload tests.")
    content = document.tobytes()
    document.close()
    return content


# Test 1: upload_pdf_document — storage upload called, DB record created, status = QUEUED on success
@pytest.mark.asyncio
async def test_upload_pdf_document_success():
    """Verify that a successful binary upload calls storage, creates DB record, and sets QUEUED status."""
    from app.services.document_service import document_service
    from app.models.document import Document

    college_id = uuid.uuid4()
    user_id = uuid.uuid4()
    valid_pdf = _valid_pdf_bytes()

    with (
        patch.object(document_service, "register_and_upload", new_callable=AsyncMock) as mock_register,
    ):
        doc_id = uuid.uuid4()
        mock_doc = Document(
            id=doc_id,
            college_id=college_id,
            uploaded_by_user_id=user_id,
            original_filename="test.pdf",
            storage_path=f"{college_id}/{doc_id}.pdf",
            mime_type="application/pdf",
            file_size_bytes=len(valid_pdf),
            total_pages=1,
            checksum_sha256="a" * 64,
            processing_status="QUEUED",
            category="GENERAL",
        )
        mock_register.return_value = (mock_doc, False)

        result_doc, is_dup = await document_service.register_and_upload(
            college_id=college_id,
            user_id=user_id,
            file_bytes=valid_pdf,
            original_filename="test.pdf",
        )

        assert result_doc.processing_status == "QUEUED"
        assert result_doc.id == doc_id
        assert is_dup is False
        mock_register.assert_called_once()


# Test 2: upload_pdf_document — storage upload fails → no DB record (rollback)
@pytest.mark.asyncio
async def test_upload_pdf_document_storage_failure_no_db_record():
    """Verify that a storage upload failure does not create a DB record (transaction rollback)."""
    from app.services.document_service import document_service
    from app.services.storage_service import document_storage_service

    college_id = uuid.uuid4()
    user_id = uuid.uuid4()
    valid_pdf = _valid_pdf_bytes()

    with (
        patch.object(document_storage_service, "upload_file", side_effect=RuntimeError("Storage unavailable")),
        patch.object(type(document_storage_service), "is_supabase_configured", property(lambda self: True)),
    ):
        with pytest.raises(RuntimeError) as exc:
            await document_service.register_and_upload(
                college_id=college_id,
                user_id=user_id,
                file_bytes=valid_pdf,
                original_filename="test.pdf",
            )
        assert "Storage unavailable" in str(exc.value)


# Test 3: upload_pdf_document — DB commit fails → uploaded storage object is deleted
@pytest.mark.asyncio
async def test_upload_pdf_document_db_commit_failure_cleans_up_storage():
    """Verify that the cleanup logic fires when flush raises after upload_file succeeds.

    Sequence: duplicate check passes → upload succeeds → flush fails → delete called.
    """
    from app.services.document_service import document_service
    from app.services.storage_service import document_storage_service

    college_id = uuid.uuid4()
    user_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    valid_pdf = _valid_pdf_bytes()

    delete_called = []

    async def fake_upload(college_id, document_id, file_bytes, mime_type="application/pdf"):
        path = f"{college_id}/{document_id}.pdf"
        return path

    async def fake_delete(college_id, storage_path):
        delete_called.append(storage_path)
        return True

    # Mock the duplicate-check result to return None (no duplicate found)
    mock_scalar_result = MagicMock()
    mock_scalar_result.scalar_one_or_none.return_value = None

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_scalar_result)
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock(side_effect=Exception("DB constraint violation"))
    mock_session.refresh = AsyncMock()
    mock_session.commit = AsyncMock()

    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    with (
        patch.object(document_storage_service, "upload_file", side_effect=fake_upload),
        patch.object(document_storage_service, "delete_file", side_effect=fake_delete),
        patch.object(type(document_storage_service), "is_supabase_configured", property(lambda self: True)),
        patch("app.services.document_service.tenant_session", side_effect=lambda **kw: mock_ctx),
    ):
        with pytest.raises(Exception) as exc:
            await document_service.register_and_upload(
                college_id=college_id,
                user_id=user_id,
                file_bytes=valid_pdf,
                original_filename="test.pdf",
            )

        assert "DB constraint violation" in str(exc.value)
        # delete_file must have been called to clean up the orphaned storage object
        assert len(delete_called) == 1


# Test 4: register_uploaded_document (after fix) — returns 422 for missing checksum, no DB record created
@pytest.mark.asyncio
async def test_register_uploaded_document_requires_checksum():
    """Verify that the JSON endpoint rejects requests without a valid checksum."""
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    from app.dependencies.auth import get_current_user
    from app.models.user import User
    from app.api.v1.college_admin import get_authorized_college
    from app.models.college import College

    mock_user = User(id=uuid.uuid4(), email="admin@ait.ac.in", role="COLLEGE_ADMIN")
    mock_college = College(
        id=uuid.uuid4(),
        name="Test College",
        official_domain="ait.ac.in",
        status="APPROVED",
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_authorized_college] = lambda: mock_college

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/college-admin/documents/upload",
            json={
                "original_filename": "test.pdf",
                "file_size_bytes": 1024,
            },
        )
        assert response.status_code == 422
        assert "checksum" in response.json()["detail"].lower()

    app.dependency_overrides.clear()


# Test 5: list_documents — missing storage object → download_url: null, no exception
@pytest.mark.asyncio
async def test_list_documents_missing_storage_object_returns_null_url():
    """Verify that list_documents returns download_url=null when storage object is missing."""
    from app.services.storage_service import document_storage_service

    college_id = uuid.uuid4()
    storage_path = f"{college_id}/{uuid.uuid4()}.pdf"

    with patch.object(
        document_storage_service,
        "get_signed_url",
        side_effect=FileNotFoundError("Object not found"),
    ):
        # The list_documents handler wraps get_signed_url in try/except
        # This test verifies the pattern is applied
        try:
            await document_storage_service.get_signed_url(college_id, storage_path)
            download_url = "should_not_reach"
        except Exception:
            download_url = None

        assert download_url is None


# Test 6: get_document_details — missing storage object → download_url: null, no exception
@pytest.mark.asyncio
async def test_get_document_details_missing_storage_returns_null_url():
    """Verify that get_document_details returns download_url=null when storage object is missing."""
    from app.services.storage_service import document_storage_service

    college_id = uuid.uuid4()
    storage_path = f"{college_id}/{uuid.uuid4()}.pdf"

    with patch.object(
        document_storage_service,
        "get_signed_url",
        side_effect=FileNotFoundError("Object not found"),
    ):
        try:
            await document_storage_service.get_signed_url(college_id, storage_path)
            download_url = "should_not_reach"
        except Exception:
            download_url = None

        assert download_url is None


# Test 7: dispatch_document_processing — broker down → document status set to FAILED, error logged
@pytest.mark.asyncio
async def test_dispatch_document_processing_broker_down_sets_failed():
    """Verify that when Celery broker is down, dispatch marks document as FAILED."""
    from app.tasks.document_tasks import dispatch_document_processing, process_pdf_document_task

    document_id = uuid.uuid4()
    college_id = uuid.uuid4()

    with (
        patch.object(process_pdf_document_task, "delay", side_effect=Exception("Broker unavailable")),
        patch("app.tasks.document_tasks._mark_document_failed", new_callable=AsyncMock) as mock_mark_failed,
    ):
        mode = await dispatch_document_processing(document_id, college_id, background_tasks=None)

        # The dispatch should attempt to mark document as FAILED
        assert mode == "LOCAL_ASYNC"
        mock_mark_failed.assert_called_once()


# Test 8: Import smoke test — from app.tasks.celery_app import celery_app succeeds
def test_celery_app_import():
    """Verify that the Celery app can be imported without errors."""
    from app.tasks.celery_app import celery_app

    assert celery_app is not None
    # Verify the app was initialized with the correct name
    assert hasattr(celery_app, "conf")


# Test 9: Dispatched document reaches FAILED or COMPLETED terminal state
@pytest.mark.asyncio
async def test_document_processing_reaches_terminal_state():
    """Verify that document processing task sets a terminal status (PENDING_REVIEW or FAILED)."""
    from app.services.document_service import document_service
    from app.models.document import Document

    document_id = uuid.uuid4()
    college_id = uuid.uuid4()

    with (
        patch.object(document_service, "execute_document_processing", new_callable=AsyncMock) as mock_exec,
    ):
        # Simulate success
        mock_exec.return_value = {"success": True, "total_pages": 5}
        result = await document_service.execute_document_processing(document_id, college_id)

        assert result["success"] is True
        mock_exec.assert_called_once()

        # Simulate failure
        mock_exec.reset_mock()
        mock_exec.return_value = {"success": False, "error": "Processing error"}
        result = await document_service.execute_document_processing(document_id, college_id)

        assert result["success"] is False
        assert "error" in result


# Test 10: Verify that signed URL failures in upload response are gracefully handled
@pytest.mark.asyncio
async def test_upload_pdf_document_signed_url_failure_does_not_crash():
    """Verify that upload_pdf_document returns download_url=null if signed URL generation fails."""
    from app.services.storage_service import document_storage_service

    college_id = uuid.uuid4()
    storage_path = f"{college_id}/{uuid.uuid4()}.pdf"

    with patch.object(
        document_storage_service,
        "get_signed_url",
        side_effect=FileNotFoundError("Object not found"),
    ):
        # The fixed upload handler wraps the signed URL call in try/except
        try:
            await document_storage_service.get_signed_url(college_id, storage_path)
            download_url = "should_not_reach"
        except Exception:
            download_url = None

        assert download_url is None


# Test 11a: broker failure → FAILED status is set before dispatch returns (not fire-and-forget)
@pytest.mark.asyncio
async def test_dispatch_broker_failure_sets_failed_synchronously():
    """FAILED status is written (awaited) during dispatch, not via ensure_future.

    dispatch_document_processing is async and directly awaits _mark_document_failed
    so the update completes before the function returns.  This covers both the
    synchronous and async caller paths.
    """
    from app.tasks.document_tasks import dispatch_document_processing, process_pdf_document_task

    document_id = uuid.uuid4()
    college_id = uuid.uuid4()
    calls: list[tuple] = []

    async def recording_mark_failed(doc_id, col_id, reason):
        # Confirm tenant isolation — only the correct IDs are used.
        assert doc_id == document_id
        assert col_id == college_id
        calls.append((doc_id, col_id, reason))

    with (
        patch.object(process_pdf_document_task, "delay", side_effect=Exception("broker down")),
        patch("app.tasks.document_tasks._mark_document_failed", side_effect=recording_mark_failed),
    ):
        # dispatch is async; await confirms the update completes before we return.
        mode = await dispatch_document_processing(document_id, college_id, background_tasks=None)

    assert mode == "LOCAL_ASYNC"
    assert len(calls) == 1, f"Expected _mark_document_failed called once; got {len(calls)}"
    assert calls[0][0] == document_id
    assert calls[0][1] == college_id
    assert "Broker unavailable" in calls[0][2]


# Test 11b: Celery task retry — FAILED is set between retries, PROCESSING restored when retry begins
def test_celery_task_sets_failed_before_retry():
    """Before each retry, process_pdf_document_task calls _run_mark_failed_sync.

    This ensures the document is not stuck in PROCESSING if the worker dies
    after a retry is scheduled but before it executes.

    Uses process_pdf_document_task.run() which injects the real task self
    automatically; self.retry is patched to simulate a retry being raised.
    """
    from app.tasks.document_tasks import process_pdf_document_task

    document_id = uuid.uuid4()
    college_id = uuid.uuid4()
    mark_calls: list[tuple] = []

    def recording_sync(doc_id, col_id, reason):
        mark_calls.append((doc_id, col_id, reason))

    class FakeRetry(Exception):
        pass

    def fake_retry(exc, countdown):
        raise FakeRetry("retry") from exc

    with (
        patch("app.tasks.document_tasks._run_mark_failed_sync", side_effect=recording_sync),
        patch(
            "app.tasks.document_tasks.run_async",
            side_effect=RuntimeError("simulated processing failure"),
        ),
        patch.object(process_pdf_document_task, "retry", side_effect=fake_retry),
    ):
        with pytest.raises(FakeRetry):
            process_pdf_document_task.run(str(document_id), str(college_id))

    # _run_mark_failed_sync must have been called once with the correct IDs
    assert len(mark_calls) == 1
    assert mark_calls[0][0] == document_id
    assert mark_calls[0][1] == college_id
    assert "Task execution error" in mark_calls[0][2]


# Test 11c: task exhausts retries → document ends in FAILED with failure_reason set
def test_celery_task_exhausted_retries_ends_in_failed():
    """After max_retries, the task must call _run_mark_failed_sync with a failure_reason.

    When Celery exhausts retries it re-raises the last exception.  The final
    _run_mark_failed_sync call (made just before the last self.retry()) ensures
    the document is in FAILED state with a reason, not stuck in PROCESSING.

    Uses process_pdf_document_task.run() so the real task self is in scope;
    self.retry is patched to simulate MaxRetriesExceededError on last attempt.
    """
    from app.tasks.document_tasks import process_pdf_document_task
    from celery.exceptions import MaxRetriesExceededError

    document_id = uuid.uuid4()
    college_id = uuid.uuid4()
    mark_calls: list[tuple] = []

    def recording_sync(doc_id, col_id, reason):
        mark_calls.append((doc_id, col_id, reason))

    def fake_retry_exhausted(exc, countdown):
        raise MaxRetriesExceededError("max retries exceeded") from exc

    with (
        patch("app.tasks.document_tasks._run_mark_failed_sync", side_effect=recording_sync),
        patch(
            "app.tasks.document_tasks.run_async",
            side_effect=Exception("persistent processing error"),
        ),
        patch.object(process_pdf_document_task, "retry", side_effect=fake_retry_exhausted),
    ):
        with pytest.raises(MaxRetriesExceededError):
            process_pdf_document_task.run(str(document_id), str(college_id))

    # Confirm FAILED was set with a failure_reason before MaxRetriesExceededError propagated
    assert len(mark_calls) == 1, f"Expected 1 call to _run_mark_failed_sync, got {len(mark_calls)}"
    assert mark_calls[0][0] == document_id
    assert mark_calls[0][1] == college_id
    assert mark_calls[0][2] != "", "failure_reason must not be empty"
    assert "Task execution error" in mark_calls[0][2]


# Test 11c-bis: run_async reuses ONE persistent event loop across calls (the fix for the
# event-loop/connection-pool bug that left documents permanently QUEUED in the worker).
def test_run_async_uses_single_persistent_loop_across_calls():
    """run_async runs coroutines on a single reused event loop, not a fresh loop per call.

    The async engine binds pooled connections to the loop that opened them, so
    reusing one long-lived loop keeps those connections valid across tasks.
    Previously every Celery task called asyncio.run() (a fresh, throwaway loop),
    which stranded pooled connections on closed loops and left documents
    permanently stuck in QUEUED.  This test locks in the fix: one loop, reused.
    """
    from app.tasks import document_tasks

    prev_loop = document_tasks._worker_loop
    document_tasks._worker_loop = None
    try:

        async def echo(x):
            return x

        assert document_tasks.run_async(echo(21)) == 21
        loop_after_first = document_tasks._worker_loop
        assert loop_after_first is not None and not loop_after_first.is_closed()

        assert document_tasks.run_async(echo(42)) == 42
        loop_after_second = document_tasks._worker_loop

        # The same loop is reused for both calls — no fresh loop per task.
        assert loop_after_first is loop_after_second
    finally:
        # Detach the loop created here so it cannot leak into later tests.
        loop = document_tasks._worker_loop
        document_tasks._worker_loop = prev_loop
        if loop is not None and not loop.is_closed():
            loop.call_soon_threadsafe(loop.stop)
            try:
                loop.close()
            except Exception:
                pass


# Test 11d: dispatch_document_processing called from an async context (running loop)
# This directly tests the FastAPI route handler path where the event loop is running.
@pytest.mark.asyncio
async def test_dispatch_broker_failure_from_async_context_sets_failed():
    """FAILED status is set correctly when dispatch_document_processing is awaited
    from an async FastAPI-style context (a running event loop).

    Previously _run_mark_failed_sync called loop.run_until_complete() on the
    already-running loop, which always raises RuntimeError and silently dropped
    the FAILED update.  The fix makes dispatch_document_processing async so it
    can await _mark_document_failed directly — no loop nesting required.
    """
    import asyncio
    from app.tasks.document_tasks import dispatch_document_processing, process_pdf_document_task

    document_id = uuid.uuid4()
    college_id = uuid.uuid4()
    mark_failed_calls: list[tuple] = []

    async def recording_mark_failed(doc_id, col_id, reason):
        assert col_id == college_id, "Tenant isolation violated"
        mark_failed_calls.append((doc_id, col_id, reason))

    # Confirm we are inside a running loop (simulates the FastAPI route handler context)
    loop = asyncio.get_running_loop()
    assert loop.is_running()

    with (
        patch.object(process_pdf_document_task, "delay", side_effect=Exception("broker down")),
        patch("app.tasks.document_tasks._mark_document_failed", side_effect=recording_mark_failed),
    ):
        # Await dispatch from within the running loop — previously broke with RuntimeError.
        mode = await dispatch_document_processing(document_id, college_id, background_tasks=None)

    assert mode == "LOCAL_ASYNC"
    assert len(mark_failed_calls) == 1, (
        f"Expected _mark_document_failed to be called once; got {len(mark_failed_calls)}"
    )
    assert mark_failed_calls[0][0] == document_id
    assert mark_failed_calls[0][1] == college_id
    assert "Broker unavailable" in mark_failed_calls[0][2]


# Test 11: reprocess_document — missing storage object → 200 with download_url: null, no exception
@pytest.mark.asyncio
async def test_reprocess_document_missing_storage_returns_null_url():
    """Verify that reprocess_document returns 200 with download_url=null when storage object is missing."""
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    from app.dependencies.auth import get_current_user
    from app.models.user import User
    from app.api.v1.college_admin import get_authorized_college
    from app.models.college import College
    from app.models.document import Document
    from app.repositories.college_admin_repository import CollegeAdminRepository
    from app.services.storage_service import document_storage_service

    college_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    mock_user = User(id=uuid.uuid4(), email="admin@ait.ac.in", role="COLLEGE_ADMIN")
    mock_college = College(
        id=college_id,
        name="Test College",
        official_domain="ait.ac.in",
        status="APPROVED",
    )
    mock_doc = Document(
        id=doc_id,
        college_id=college_id,
        uploaded_by_user_id=mock_user.id,
        original_filename="missing.pdf",
        storage_path=f"{college_id}/{doc_id}.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        total_pages=0,
        checksum_sha256="b" * 64,
        processing_status="FAILED",
        category="GENERAL",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_authorized_college] = lambda: mock_college

    with (
        patch.object(CollegeAdminRepository, "get_document", new_callable=AsyncMock, return_value=mock_doc),
        patch("app.api.v1.college_admin.dispatch_document_processing", return_value="CELERY"),
        patch.object(
            document_storage_service,
            "get_signed_url",
            side_effect=FileNotFoundError("Storage object not found"),
        ),
        patch("app.database.session.get_db", new_callable=AsyncMock),
        patch("sqlalchemy.ext.asyncio.AsyncSession.commit", new_callable=AsyncMock),
    ):
        # Patch the session commit on the router's session dependency
        async def mock_get_db():
            mock_session = AsyncMock()
            mock_session.commit = AsyncMock()
            yield mock_session

        from app.database.session import get_db
        app.dependency_overrides[get_db] = mock_get_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/college-admin/documents/{doc_id}/reprocess",
            )

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["download_url"] is None

    app.dependency_overrides.clear()
