"""Celery Background Worker Application Configuration.

Configures Celery distributed task queue using Redis broker and result backend.
"""

import importlib
import os
from typing import Any
from app.core.config import settings

# Dynamically import Celery with fallback for local environments without celery installed
try:
    _celery_mod = importlib.import_module("celery")
    Celery = getattr(_celery_mod, "Celery")
except Exception:
    class Celery:  # type: ignore
        """Fallback mock for environments without Celery installed."""
        def __init__(self, *args: Any, **kwargs: Any):
            self.conf = {}
        def task(self, *args: Any, **kwargs: Any):
            def decorator(fn: Any):
                fn.delay = fn
                return fn
            return decorator

# Initialize Celery Application
celery_app = Celery(
    "college_chatbot",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.crawler_tasks", "app.tasks.document_tasks"],
)

# Celery Configuration Settings
if hasattr(celery_app, "conf") and hasattr(celery_app.conf, "update"):
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=3600,        # 1 hour hard limit
        task_soft_time_limit=3000,   # 50 minutes soft limit
        worker_prefetch_multiplier=1,
        worker_concurrency=4,
        task_routes={
            "app.tasks.crawler_tasks.*": {"queue": "crawlers"},
            "app.tasks.document_tasks.*": {"queue": "documents"},
        },
    )

