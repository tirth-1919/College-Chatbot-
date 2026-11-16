"""Celery Document Processing & OCR Background Task Definitions.

Executes asynchronous PDF deconstruction, table parsing, and OCR
with tenant isolation and local background fallback.
"""

import asyncio
import logging
import threading
from typing import Optional
import uuid

from fastapi import BackgroundTasks

from app.services.document_service import document_service
from app.tasks.celery_app import celery_app

logger = logging.getLogger("college_chatbot.tasks.document")


# ---------------------------------------------------------------------------
# Persistent worker event loop
# ---------------------------------------------------------------------------
# The SQLAlchemy async engine (``app.database.connection.async_engine``) binds
# its pooled connections to the event loop that opened them.  Calling
# ``asyncio.run()`` for every Celery task creates and tears down a fresh loop
# each time, leaving the engine's connection pool full of connections bound to
# already-closed loops.  The next task then fails with
# ``RuntimeError: Event loop is closed`` (and, once the pool is further
# corrupted, with ``not enough values to unpack ...``) — and the document is
# left permanently stuck in QUEUED because even the FAILED-status update (which
# also used ``asyncio.run``) hits the same dead connections.
#
# Running one long-lived event loop in a background daemon thread keeps every
# pooled connection valid for the lifetime of the worker process and avoids
# unsafe event-loop nesting inside the synchronous Celery task body.  This
# preserves the existing retry behaviour (any exception raised by the
# coroutine still propagates to the task body) and tenant isolation (the
# services and ``tenant_session`` calls are unchanged).
_worker_loop: "Optional[asyncio.AbstractEventLoop]" = None
_worker_loop_lock = threading.Lock()


def _get_worker_loop() -> "asyncio.AbstractEventLoop":
    """Lazily create and start a single persistent event loop for the worker.

    The loop is reused for every subsequent task in this process, so the async
    engine's pooled connections always remain bound to a live loop.
    """
    global _worker_loop
    if _worker_loop is not None and not _worker_loop.is_closed():
        return _worker_loop
    with _worker_loop_lock:
        if _worker_loop is None or _worker_loop.is_closed():
            loop = asyncio.new_event_loop()
            thread = threading.Thread(
                target=loop.run_forever,
                name="celery-async-worker-loop",
                daemon=True,
            )
            thread.start()
            _worker_loop = loop
    return _worker_loop


def run_async(coro):
    """Run *coro* on the worker's persistent event loop and return its result.

    Safe to call from the synchronous Celery task body — it does not create or
    close an event loop.  Any exception raised by the coroutine propagates to
    the caller, preserving the existing retry / FAILED-status behaviour.
    """
    loop = _get_worker_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result()


def _run_mark_failed_sync(
    document_id: uuid.UUID,
    college_id: uuid.UUID,
    reason: str,
) -> None:
    """Run _mark_document_failed from a synchronous (non-async) context.

    This is only safe to call when there is no running event loop on the current
    thread — i.e. from a Celery synchronous task worker.  It runs the update on
    the worker's single persistent event loop (see ``run_async``) instead of
    creating a throwaway loop with ``asyncio.run()``, so the async engine's
    pooled connections stay bound to a live loop across retries.

    For async callers (FastAPI route handlers) use await _mark_document_failed()
    directly instead of going through this function.
    """
    run_async(_mark_document_failed(document_id, college_id, reason))


@celery_app.task(name="app.tasks.document_tasks.process_pdf_document_task", bind=True, max_retries=2)
def process_pdf_document_task(self, document_id_str: str, college_id_str: str):
    """Celery background worker task for PDF text extraction and OCR."""
    logger.info("Starting Celery document processing task: doc=%s, college=%s", document_id_str, college_id_str)
    document_id = uuid.UUID(document_id_str)
    college_id = uuid.UUID(college_id_str)
    try:
        result = run_async(
            document_service.execute_document_processing(
                document_id=document_id,
                college_id=college_id,
            )
        )
        # execute_document_processing returns {"success": False, ...} on internal failure;
        # treat that as a terminal FAILED state without retry.
        if isinstance(result, dict) and not result.get("success", True):
            logger.error(
                "Document processing returned failure for %s: %s",
                document_id_str,
                result.get("error"),
            )
        return result
    except Exception as exc:
        logger.error("Celery document task failed for %s: %s", document_id_str, str(exc), exc_info=True)
        # Mark document FAILED synchronously before retrying so the status is
        # always up-to-date even if the worker dies between retries.
        try:
            _run_mark_failed_sync(document_id, college_id, f"Task execution error: {exc}")
        except Exception:
            logger.exception("Could not update document status to FAILED for %s", document_id_str)
        raise self.retry(exc=exc, countdown=15)


async def _mark_document_failed(
    document_id: uuid.UUID,
    college_id: uuid.UUID,
    reason: str,
) -> None:
    """Sets a document's processing_status to FAILED with the given reason."""
    from datetime import datetime, timezone
    from app.database.session import tenant_session
    from app.models.document import Document

    try:
        async with tenant_session(college_id=college_id) as session:
            doc = await session.get(Document, document_id)
            if doc:
                doc.processing_status = "FAILED"
                doc.failure_reason = reason
                doc.updated_at = datetime.now(timezone.utc)
                await session.commit()
    except Exception:
        logger.exception(
            "Failed to mark document %s as FAILED in database",
            document_id,
        )


async def _run_async_document_processing(document_id: uuid.UUID, college_id: uuid.UUID):
    """Local asynchronous fallback runner when Celery broker is offline."""
    try:
        await document_service.execute_document_processing(document_id, college_id)
    except Exception as e:
        logger.error(
            "Local background document processing failed for %s: %s",
            document_id,
            str(e),
            exc_info=True,
        )
        # Ensure document status is set to FAILED so it does not stay QUEUED.
        await _mark_document_failed(document_id, college_id, f"Local async processing error: {e}")


async def dispatch_document_processing(
    document_id: uuid.UUID,
    college_id: uuid.UUID,
    background_tasks: Optional[BackgroundTasks] = None,
) -> str:
    """Dispatches document processing task via Celery with fallback to FastAPI BackgroundTasks.

    This is an async function so that the FAILED status update can be awaited
    directly when called from an async FastAPI route handler.  Calling
    loop.run_until_complete() or asyncio.run() from inside a running event loop
    raises RuntimeError; awaiting _mark_document_failed avoids that entirely.

    Returns:
        Execution mode: 'CELERY' or 'LOCAL_ASYNC'
    """
    doc_id_str = str(document_id)
    college_id_str = str(college_id)

    try:
        process_pdf_document_task.delay(doc_id_str, college_id_str)
        logger.info("Queued document %s into Celery distributed queue", doc_id_str)
        return "CELERY"
    except Exception as err:
        logger.error(
            "Broker unavailable — could not queue document %s: %s",
            doc_id_str,
            str(err),
        )

        # Update document status to FAILED directly (awaited) so it is never silently stuck in QUEUED.
        # asyncio.ensure_future() is intentionally avoided: fire-and-forget coroutines can be
        # dropped during event loop shutdown and would leave the document in QUEUED permanently.
        try:
            await _mark_document_failed(
                document_id,
                college_id,
                "Broker unavailable: task could not be queued",
            )
        except Exception:
            logger.exception(
                "Could not update document %s status to FAILED after broker failure",
                doc_id_str,
            )

        # Keep LOCAL_ASYNC fallback but log prominently and ensure it also sets FAILED on its own error.
        if background_tasks:
            logger.warning(
                "Broker unavailable — falling back to LOCAL_ASYNC for document %s",
                doc_id_str,
            )
            background_tasks.add_task(
                _run_async_document_processing, document_id, college_id
            )
            return "LOCAL_ASYNC"

        logger.error(
            "Broker unavailable and no BackgroundTasks context — document %s will not be processed",
            doc_id_str,
        )
        return "LOCAL_ASYNC"
