"""Redis heartbeat used for worker readiness on Redis-compatible brokers."""

import logging
import os
import threading
from typing import Any

import redis

from app.core.config import settings

logger = logging.getLogger("college_chatbot.worker_health")
WORKER_SET_KEY = "college_chatbot:workers:active"
HEARTBEAT_PREFIX = "college_chatbot:workers:heartbeat:"
HEARTBEAT_TTL_SECONDS = 12
HEARTBEAT_INTERVAL_SECONDS = 4

_lock = threading.Lock()
_stoppers: dict[str, threading.Event] = {}
_threads: dict[str, threading.Thread] = {}


def _worker_id(sender: Any) -> str:
    hostname = sender if isinstance(sender, str) else getattr(sender, "hostname", None)
    hostname = hostname or "worker"
    return f"{hostname}:{os.getpid()}"


def _write_heartbeat(worker_id: str) -> None:
    key = f"{HEARTBEAT_PREFIX}{worker_id}"
    try:
        client = redis.Redis.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=2)
        try:
            with client.pipeline() as pipe:
                pipe.setex(key, HEARTBEAT_TTL_SECONDS, str(os.getpid()))
                pipe.sadd(WORKER_SET_KEY, worker_id)
                pipe.execute()
        finally:
            client.close()
    except Exception:
        logger.exception("Could not update Celery worker heartbeat")


def on_worker_ready(sender: Any = None, **_: Any) -> None:
    worker_id = _worker_id(sender)
    stop = threading.Event()

    def heartbeat_loop() -> None:
        while not stop.is_set():
            _write_heartbeat(worker_id)
            stop.wait(HEARTBEAT_INTERVAL_SECONDS)

    with _lock:
        prior = _stoppers.pop(worker_id, None)
        if prior:
            prior.set()
        _stoppers[worker_id] = stop
        thread = threading.Thread(
            target=heartbeat_loop,
            name="celery-readiness-heartbeat",
            daemon=True,
        )
        _threads[worker_id] = thread
        thread.start()


def on_worker_shutdown(sender: Any = None, **_: Any) -> None:
    worker_id = _worker_id(sender)
    with _lock:
        stop = _stoppers.pop(worker_id, None)
        thread = _threads.pop(worker_id, None)
    if stop:
        stop.set()
    if thread and thread.is_alive():
        thread.join(timeout=2)

    try:
        client = redis.Redis.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=2)
        try:
            # worker_shutting_down sends the hostname as sender, while worker_ready
            # sends the consumer object; remove matching PID-qualified heartbeats.
            members = client.smembers(WORKER_SET_KEY)
            hostname = sender if isinstance(sender, str) else getattr(sender, "hostname", None)
            matching = [
                member.decode() if isinstance(member, bytes) else str(member)
                for member in members
                if str(member.decode() if isinstance(member, bytes) else member).startswith(f"{hostname}:")
            ] if hostname else [worker_id]
            if not matching:
                matching = [worker_id]
            with client.pipeline() as pipe:
                for member in matching:
                    pipe.delete(f"{HEARTBEAT_PREFIX}{member}")
                    pipe.srem(WORKER_SET_KEY, member)
                pipe.execute()
        finally:
            client.close()
    except Exception:
        logger.exception("Could not clear Celery worker heartbeat")
