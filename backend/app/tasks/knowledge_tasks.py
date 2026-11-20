"""Celery & Async Knowledge Pipeline Background Task Definitions.

Executes asynchronous chunking, category classification, and pgvector
embedding generation with tenant isolation and local background fallback.

All database sessions in this module use ``tenant_session()`` instead of
raw ``AsyncSessionLocal()`` so that the ``app.current_college_id`` GUC is
set before every query, activating PostgreSQL RLS policies for the task's
tenant scope.
"""

import asyncio
import logging
from typing import List, Optional
import uuid
from fastapi import BackgroundTasks
from app.database.session import tenant_session
from app.services.knowledge_service import knowledge_service
from app.tasks.celery_app import celery_app
from app.tasks.document_tasks import run_async

logger = logging.getLogger("college_chatbot.tasks.knowledge")


@celery_app.task(name="app.tasks.knowledge_tasks.process_website_knowledge_task", bind=True, max_retries=2)
def process_website_knowledge_task(self, college_id_str: str, page_ids_str: Optional[List[str]] = None):
    """Celery background worker task for ingesting crawled website pages into knowledge chunks."""
    logger.info("Starting Celery website knowledge task: college=%s", college_id_str)
    try:
        college_id = uuid.UUID(college_id_str)
        page_ids = [uuid.UUID(p) for p in page_ids_str] if page_ids_str else None

        async def _run():
            async with tenant_session(college_id=college_id) as session:
                return await knowledge_service.process_website_pages(
                    college_id=college_id, session=session, page_ids=page_ids
                )

        return run_async(_run())
    except Exception as exc:
        logger.error("Celery website knowledge task failed: %s", exc)
        raise self.retry(exc=exc, countdown=15)


@celery_app.task(name="app.tasks.knowledge_tasks.process_document_knowledge_task", bind=True, max_retries=2)
def process_document_knowledge_task(self, college_id_str: str, document_id_str: str):
    """Celery background worker task for ingesting document pages into knowledge chunks."""
    logger.info("Starting Celery document knowledge task: college=%s doc=%s", college_id_str, document_id_str)
    try:
        college_id = uuid.UUID(college_id_str)
        document_id = uuid.UUID(document_id_str)

        async def _run():
            async with tenant_session(college_id=college_id) as session:
                return await knowledge_service.process_document_pages(
                    college_id=college_id, document_id=document_id, session=session
                )

        return run_async(_run())
    except Exception as exc:
        logger.error("Celery document knowledge task failed: %s", exc)
        raise self.retry(exc=exc, countdown=15)


async def _run_async_website_knowledge(college_id: uuid.UUID, page_ids: Optional[List[uuid.UUID]] = None):
    """Local asynchronous fallback runner when Celery broker is offline."""
    try:
        async with tenant_session(college_id=college_id) as session:
            await knowledge_service.process_website_pages(
                college_id=college_id, session=session, page_ids=page_ids
            )
    except Exception as exc:
        logger.error("Local async website knowledge processing failed: %s", exc, exc_info=True)


async def _run_async_document_knowledge(college_id: uuid.UUID, document_id: uuid.UUID):
    """Local asynchronous fallback runner when Celery broker is offline."""
    try:
        async with tenant_session(college_id=college_id) as session:
            await knowledge_service.process_document_pages(
                college_id=college_id, document_id=document_id, session=session
            )
    except Exception as exc:
        logger.error("Local async document knowledge processing failed: %s", exc, exc_info=True)


def dispatch_website_knowledge_processing(
    college_id: uuid.UUID,
    page_ids: Optional[List[uuid.UUID]] = None,
    background_tasks: Optional[BackgroundTasks] = None,
) -> str:
    """Dispatches website knowledge processing task via Celery with fallback."""
    try:
        process_website_knowledge_task.delay(
            str(college_id),
            [str(p) for p in page_ids] if page_ids else None,
        )
        return "CELERY"
    except Exception as exc:
        logger.warning("Celery dispatch unavailable (%s). Falling back to local background execution.", exc)
        if background_tasks:
            background_tasks.add_task(_run_async_website_knowledge, college_id, page_ids)
            return "LOCAL_ASYNC"
        asyncio.create_task(_run_async_website_knowledge(college_id, page_ids))
        return "LOCAL_ASYNC"


def dispatch_document_knowledge_processing(
    college_id: uuid.UUID,
    document_id: uuid.UUID,
    background_tasks: Optional[BackgroundTasks] = None,
) -> str:
    """Dispatches document knowledge processing task via Celery with fallback."""
    try:
        process_document_knowledge_task.delay(str(college_id), str(document_id))
        return "CELERY"
    except Exception as exc:
        logger.warning("Celery dispatch unavailable (%s). Falling back to local background execution.", exc)
        if background_tasks:
            background_tasks.add_task(_run_async_document_knowledge, college_id, document_id)
            return "LOCAL_ASYNC"
        asyncio.create_task(_run_async_document_knowledge(college_id, document_id))
        return "LOCAL_ASYNC"

