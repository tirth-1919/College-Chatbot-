"""Celery background tasks registry."""

from app.tasks.celery_app import celery_app
from app.tasks.crawler_tasks import dispatch_crawl_job, run_website_crawl_job
from app.tasks.document_tasks import dispatch_document_processing, process_pdf_document_task

__all__ = [
    "celery_app",
    "run_website_crawl_job",
    "dispatch_crawl_job",
    "process_pdf_document_task",
    "dispatch_document_processing",
]
