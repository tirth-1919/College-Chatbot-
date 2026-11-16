"""Website Crawler Task async event-loop unit tests.

Verifies that the Celery crawl task reuses the shared persistent event loop
(from ``document_tasks.run_async``) instead of creating a throwaway loop with
``asyncio.run()``, and that crawl failures propagate / trigger retry instead of
being silently swallowed.

All tests use mocks — no live Redis, no live Supabase, no live DB.
"""

import asyncio
import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


JOB_ID = uuid.uuid4()
COLLEGE_ID = uuid.uuid4()
SOURCE_ID = uuid.uuid4()


# ---------------------------------------------------------------------------
# Test 1: the crawl task imports the *shared* run_async, not a duplicate loop
# ---------------------------------------------------------------------------
def test_crawler_tasks_imports_shared_run_async():
    """``run_website_crawl_job`` must reuse ``document_tasks.run_async``.

    The fix deliberately imports the existing persistent-loop runner instead of
    defining a second event-loop manager, so a single loop keeps the async
    engine's pooled connections valid for the whole worker process.
    """
    from app.tasks import crawler_tasks, document_tasks

    # Same function object — no duplicate implementation.
    assert crawler_tasks.run_async is document_tasks.run_async

    # No second event-loop manager exists in the crawler module.
    assert not hasattr(crawler_tasks, "_worker_loop")
    assert not hasattr(crawler_tasks, "_get_worker_loop")


# ---------------------------------------------------------------------------
# Test 2: sequential crawl runs reuse ONE persistent loop (the connection-pool
# fix) and the coroutine actually runs to completion under run_async — status
# updates are not silently dropped.  Also guards against regressing to
# asyncio.run().
# ---------------------------------------------------------------------------
def test_run_website_crawl_job_reuses_persistent_loop_and_runs_coroutine():
    """Two sequential crawl task runs reuse the same persistent event loop.

    Previously every task called ``asyncio.run()`` (a fresh, throwaway loop),
    which stranded the async engine's pooled connections on closed loops and
    left crawl jobs stuck mid-run.  Reusing the shared persistent loop keeps
    those connections bound to a live loop.  The guard on ``asyncio.run`` proves
    the unsafe path is gone, and the recorded status updates prove the
    coroutine is actually awaited to completion (not dropped).
    """
    from app.tasks import crawler_tasks, document_tasks

    status_updates: list[tuple] = []

    async def fake_execute(job_id, college_id, source_id):
        # Simulate the service performing a status transition (RUNNING -> COMPLETED)
        # before returning.  This must actually run under run_async, not be dropped.
        status_updates.append(("COMPLETED", job_id, college_id, source_id))
        return {
            "success": True,
            "status": "COMPLETED",
            "pages_discovered": 1,
            "pages_crawled": 1,
            "pages_failed": 0,
        }

    prev_loop = document_tasks._worker_loop
    document_tasks._worker_loop = None
    try:
        with (
            patch.object(
                crawler_tasks.crawler_service,
                "execute_crawl_job",
                side_effect=fake_execute,
            ),
            # Fail loudly if the task regresses to asyncio.run().
            patch.object(
                asyncio, "run", side_effect=AssertionError("asyncio.run must not be used in crawl task")
            ),
        ):
            result1 = crawler_tasks.run_website_crawl_job.run(
                str(JOB_ID), str(COLLEGE_ID), str(SOURCE_ID)
            )
            loop_after_first = document_tasks._worker_loop
            assert loop_after_first is not None
            assert not loop_after_first.is_closed()

            result2 = crawler_tasks.run_website_crawl_job.run(
                str(JOB_ID), str(COLLEGE_ID), str(SOURCE_ID)
            )
            loop_after_second = document_tasks._worker_loop

        # The same loop is reused for both calls — no fresh loop per task.
        assert loop_after_first is loop_after_second

        assert result1["success"] is True
        assert result2["success"] is True

        # The coroutine ran to completion twice — status updates happened, not
        # silently swallowed.
        assert len(status_updates) == 2
        # Tenant isolation: the college id is passed through unchanged.
        assert status_updates[0][2] == COLLEGE_ID
        assert status_updates[1][2] == COLLEGE_ID
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


# ---------------------------------------------------------------------------
# Test 3: a coroutine failure propagates to the task body and triggers retry —
# it is never silently swallowed.
# ---------------------------------------------------------------------------
def test_run_website_crawl_job_failure_propagates_and_retries():
    """An exception from the crawl coroutine must propagate and call self.retry.

    The existing retry behaviour (``max_retries=1``, ``countdown=30``) must be
    preserved: the task body catches the exception, logs it, and re-queues via
    ``self.retry`` rather than returning a silent success.
    """
    from app.tasks import crawler_tasks

    class FakeRetry(Exception):
        pass

    retry_calls: list[tuple] = []

    def fake_retry(exc, countdown):
        retry_calls.append((exc, countdown))
        raise FakeRetry("retry scheduled") from exc

    with (
        patch("app.tasks.crawler_tasks.run_async", side_effect=RuntimeError("crawl execution blew up")),
        # Replace the async method with a *sync* MagicMock so calling it does not
        # create an un-awaited coroutine (the mocked run_async raises before any
        # await would happen).
        patch.object(crawler_tasks.crawler_service, "execute_crawl_job", new=MagicMock()),
        patch.object(crawler_tasks.run_website_crawl_job, "retry", side_effect=fake_retry),
    ):
        with pytest.raises(FakeRetry):
            crawler_tasks.run_website_crawl_job.run(
                str(JOB_ID), str(COLLEGE_ID), str(SOURCE_ID)
            )

    # self.retry was invoked with the original exception and the existing 30s backoff.
    assert len(retry_calls) == 1
    assert isinstance(retry_calls[0][0], RuntimeError)
    assert "crawl execution blew up" in str(retry_calls[0][0])
    assert retry_calls[0][1] == 30


# ---------------------------------------------------------------------------
# Test 4: a service-level failure ({"success": False}) is surfaced as-is and is
# NOT retried — it is a terminal failure the service already persisted (e.g. via
# _fail_job), so the task must not swallow it nor re-queue it.
# ---------------------------------------------------------------------------
def test_run_website_crawl_job_surfaces_service_failure_without_retry():
    """A ``{"success": False}`` return is returned as-is, never retried or swallowed.

    The crawler service performs its own status transitions internally (e.g.
    ``_fail_job`` sets FAILED for tenant / source validation errors) and returns a
    failure dict.  The task must surface that result unchanged — retrying would
    duplicate work and swallowing it would hide the failure.
    """
    from app.tasks import crawler_tasks

    failure_result = {"success": False, "error": "College tenant not found"}

    def must_not_retry(exc, countdown):
        raise AssertionError("service-level failure must not be retried") from exc

    with (
        patch("app.tasks.crawler_tasks.run_async", return_value=failure_result),
        # Sync MagicMock so no un-awaited coroutine is created.
        patch.object(crawler_tasks.crawler_service, "execute_crawl_job", new=MagicMock()),
        patch.object(crawler_tasks.run_website_crawl_job, "retry", side_effect=must_not_retry),
    ):
        result = crawler_tasks.run_website_crawl_job.run(
            str(JOB_ID), str(COLLEGE_ID), str(SOURCE_ID)
        )

    # The failure dict is surfaced unchanged — not swallowed into a success,
    # not turned into an exception, not retried.
    assert result == failure_result
    assert result["success"] is False
    assert result["error"] == "College tenant not found"


@pytest.mark.asyncio
async def test_save_or_deduplicate_page_marks_new_or_changed_content():
    """Changed content is marked as changed, preserving the original bool contract used by the crawler flow."""
    from app.services.crawler_service import WebsiteCrawlerService

    service = WebsiteCrawlerService()
    session = MagicMock()
    session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
    session.flush = AsyncMock()

    parsed = MagicMock(
        url="https://example.edu/admissions",
        title="Admissions",
        meta_description="Admissions overview",
        content_hash="abc123",
        cleaned_text="Updated admissions content",
        content_length=28,
    )

    changed = await service._save_or_deduplicate_page(
        session=session,
        college_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        parsed=parsed,
        http_status=200,
    )

    assert changed is True
    session.add.assert_called_once()
