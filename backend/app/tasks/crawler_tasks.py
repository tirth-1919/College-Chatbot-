"""Celery Website Crawler Task Definitions.

Dispatches asynchronous website crawling jobs to worker processes
with tenant isolation and automatic local background fallback.
"""

import asyncio
import logging
from typing import Optional
import uuid

from fastapi import BackgroundTasks

from app.services.crawler_service import crawler_service
from app.tasks.celery_app import celery_app
from app.tasks.document_tasks import run_async

logger = logging.getLogger("college_chatbot.tasks.crawler")


@celery_app.task(name="app.tasks.crawler_tasks.run_website_crawl_job", bind=True, max_retries=1)
def run_website_crawl_job(self, job_id_str: str, college_id_str: str, source_id_str: str):
    """Celery background worker entry point for website crawling."""
    logger.info("Executing Celery crawl task: job=%s, college=%s", job_id_str, college_id_str)
    try:
        job_id = uuid.UUID(job_id_str)
        college_id = uuid.UUID(college_id_str)
        source_id = uuid.UUID(source_id_str)

        # Run the async crawl coroutine on the worker's single persistent event
        # loop (shared with document_tasks) instead of asyncio.run().  asyncio.run()
        # creates and tears down a fresh loop per task, which strands the async
        # engine's pooled connections on closed loops and leaves crawl jobs stuck
        # mid-run.  Reusing the persistent loop keeps every pooled connection bound
        # to a live loop for the lifetime of the worker process.  Any exception
        # raised by the coroutine still propagates here, preserving the existing
        # retry behaviour and the tenant-scoped status transitions performed inside
        # crawler_service.execute_crawl_job.
        result = run_async(
            crawler_service.execute_crawl_job(
                job_id=job_id,
                college_id=college_id,
                source_id=source_id,
            )
        )
        return result
    except Exception as exc:
        logger.error("Celery crawl task failed for job %s: %s", job_id_str, str(exc), exc_info=True)
        raise self.retry(exc=exc, countdown=30)


async def _run_async_crawler(job_id: uuid.UUID, college_id: uuid.UUID, source_id: uuid.UUID):
    """Local asynchronous fallback runner when Redis/Celery is unavailable."""
    try:
        await crawler_service.execute_crawl_job(job_id, college_id, source_id)
    except Exception as e:
        logger.error("Local background crawl task encountered error: %s", str(e), exc_info=True)


def dispatch_crawl_job(
    job_id: uuid.UUID,
    college_id: uuid.UUID,
    source_id: uuid.UUID,
    background_tasks: Optional[BackgroundTasks] = None,
) -> str:
    """Dispatches crawl job via Celery broker if available, or falls back to FastAPI BackgroundTasks.

    Returns:
        Execution mode string: "CELERY" or "LOCAL_ASYNC"
    """
    job_id_str = str(job_id)
    college_id_str = str(college_id)
    source_id_str = str(source_id)

    try:
        # Attempt to queue into Celery
        run_website_crawl_job.delay(job_id_str, college_id_str, source_id_str)
        logger.info("Dispatched crawl job %s to Celery queue", job_id_str)
        return "CELERY"
    except Exception as err:
        logger.warning(
            "Celery broker unavailable (%s). Falling back to direct async execution for job %s",
            str(err),
            job_id_str,
        )
        if background_tasks:
            background_tasks.add_task(
                _run_async_crawler, job_id, college_id, source_id
            )
        else:
            # Fallback fire-and-forget task
            asyncio.create_task(
                _run_async_crawler(job_id, college_id, source_id)
            )
        return "LOCAL_ASYNC"

