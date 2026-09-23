import time
import uuid
import threading
import queue
import traceback
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Callable
from sqlalchemy.orm import Session
from backend.app.core.database import SessionLocal
from backend.app.models.automation import AutomationJob, AutomationJobRun, DistributedLock, SystemAlert

# Error classes
class ErrorClass:
    TRANSIENT = "TRANSIENT"
    PERMANENT = "PERMANENT"
    AUTHENTICATION = "AUTHENTICATION"
    RATE_LIMIT = "RATE_LIMIT"
    VALIDATION = "VALIDATION"
    SECURITY = "SECURITY"
    DEPENDENCY = "DEPENDENCY"
    UNKNOWN = "UNKNOWN"

RETRYABLE_CLASSES = {ErrorClass.TRANSIENT, ErrorClass.RATE_LIMIT, ErrorClass.DEPENDENCY}

class AutomationEngine:
    def __init__(self):
        self.worker_id = f"worker-{uuid.uuid4().hex[:8]}"
        self._registry: Dict[str, Callable] = {}
        self._queue = queue.PriorityQueue()
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None

    def register_job(self, job_type: str, handler: Callable):
        """Registers an automated job handler."""
        self._registry[job_type] = handler

    def start_worker(self):
        """Starts background worker daemon."""
        if not self._running:
            self._running = True
            self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self._worker_thread.start()

    def stop_worker(self):
        """Stops background worker gracefully."""
        self._running = False

    def acquire_lock(self, db: Session, lock_key: str, ttl_seconds: int = 300) -> bool:
        """Acquires a distributed lock with automatic expiry."""
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=ttl_seconds)

        existing = db.query(DistributedLock).filter(DistributedLock.lock_key == lock_key).first()
        if existing:
            # Check if expired (normalize naive/aware datetimes from SQLite)
            existing_expiry = existing.expires_at
            if existing_expiry.tzinfo is None:
                existing_expiry = existing_expiry.replace(tzinfo=timezone.utc)
            if existing_expiry < now:
                existing.owner = self.worker_id
                existing.acquired_at = now
                existing.expires_at = expires_at
                db.commit()
                return True
            return False
        else:
            lock = DistributedLock(
                lock_key=lock_key,
                owner=self.worker_id,
                acquired_at=now,
                expires_at=expires_at
            )
            db.add(lock)
            try:
                db.commit()
                return True
            except Exception:
                db.rollback()
                return False

    def release_lock(self, db: Session, lock_key: str):
        """Safely releases distributed lock if held by this worker."""
        lock = db.query(DistributedLock).filter(
            DistributedLock.lock_key == lock_key,
            DistributedLock.owner == self.worker_id
        ).first()
        if lock:
            db.delete(lock)
            db.commit()

    def enqueue_job(
        self,
        job_type: str,
        payload: Optional[Dict[str, Any]] = None,
        priority: int = 5,
        idempotency_key: Optional[str] = None,
        source_hash: Optional[str] = None,
        max_retries: int = 3
    ) -> str:
        """Submits a job idempotently to the execution engine."""
        db: Session = SessionLocal()
        try:
            # Idempotency check
            if idempotency_key:
                existing = db.query(AutomationJob).filter(AutomationJob.idempotency_key == idempotency_key).first()
                if existing and existing.status in ["QUEUED", "RUNNING", "SUCCEEDED"]:
                    return existing.job_id

            job_id = f"job-{uuid.uuid4().hex[:12]}"
            job = AutomationJob(
                job_id=job_id,
                job_type=job_type,
                status="QUEUED",
                priority=priority,
                retry_count=0,
                max_retries=max_retries,
                idempotency_key=idempotency_key,
                source_hash=source_hash,
                payload=payload or {},
                execution_metadata={"enqueued_at": datetime.now(timezone.utc).isoformat()}
            )
            db.add(job)
            db.commit()

            # Push to queue (priority: 1=highest, 10=lowest)
            self._queue.put((priority, job_id))
            return job_id
        finally:
            db.close()

    def _worker_loop(self):
        """Worker loop processing enqueued tasks."""
        while self._running:
            try:
                try:
                    priority, job_id = self._queue.get(timeout=2.0)
                except queue.Empty:
                    continue

                self._process_job(job_id)
                self._queue.task_done()
            except Exception:
                time.sleep(1)

    def _classify_error(self, err: Exception) -> str:
        """Classifies exception to decide retry eligibility."""
        msg = str(err).lower()
        if "rate limit" in msg or "429" in msg or "quota" in msg:
            return ErrorClass.RATE_LIMIT
        if "auth" in msg or "401" in msg or "403" in msg or "forbidden" in msg:
            return ErrorClass.AUTHENTICATION
        if "timeout" in msg or "connection reset" in msg or "temporary" in msg:
            return ErrorClass.TRANSIENT
        if "not found" in msg or "validation" in msg or "schema" in msg:
            return ErrorClass.VALIDATION
        if "security" in msg or "malicious" in msg or "injection" in msg:
            return ErrorClass.SECURITY
        if "database" in msg or "redis" in msg or "service unavailable" in msg:
            return ErrorClass.DEPENDENCY
        return ErrorClass.UNKNOWN

    def _process_job(self, job_id: str):
        """Executes a single job with locking, audit run tracking, retry backoff, and dead-lettering."""
        db: Session = SessionLocal()
        try:
            job = db.query(AutomationJob).filter(AutomationJob.job_id == job_id).first()
            if not job or job.status in ["CANCELLED", "SUCCEEDED"]:
                return

            handler = self._registry.get(job.job_type)
            if not handler:
                job.status = "DEAD_LETTER"
                job.error_class = ErrorClass.PERMANENT
                job.error = f"No handler registered for job type: {job.job_type}"
                db.commit()
                return

            job.status = "RUNNING"
            job.started_at = datetime.now(timezone.utc)
            job.worker_id = self.worker_id
            db.commit()

            start_t = time.time()
            attempt = job.retry_count + 1

            try:
                # Execute registered job handler
                result = handler(job.payload or {})
                duration_ms = (time.time() - start_t) * 1000

                job.status = "SUCCEEDED"
                job.completed_at = datetime.now(timezone.utc)
                job.execution_metadata = {
                    **(job.execution_metadata or {}),
                    "result": result,
                    "duration_ms": duration_ms
                }
                job.error = None

                # Log run record
                run = AutomationJobRun(
                    job_ref_id=job.id,
                    attempt_number=attempt,
                    status="SUCCEEDED",
                    completed_at=datetime.now(timezone.utc),
                    duration_ms=duration_ms,
                    worker_id=self.worker_id,
                    run_log="Execution completed successfully."
                )
                db.add(run)
                db.commit()

            except Exception as err:
                duration_ms = (time.time() - start_t) * 1000
                err_cls = self._classify_error(err)
                err_msg = str(err)
                trace_str = traceback.format_exc()

                job.retry_count += 1
                job.error_class = err_cls
                job.error = err_msg

                # Run record
                run = AutomationJobRun(
                    job_ref_id=job.id,
                    attempt_number=attempt,
                    status="FAILED",
                    completed_at=datetime.now(timezone.utc),
                    duration_ms=duration_ms,
                    worker_id=self.worker_id,
                    error_class=err_cls,
                    error_message=err_msg,
                    run_log=trace_str
                )
                db.add(run)

                # Retry evaluation
                if err_cls in RETRYABLE_CLASSES and job.retry_count < job.max_retries:
                    job.status = "RETRYING"
                    db.commit()
                    # Exponential backoff: 2^retry seconds
                    backoff = 2 ** job.retry_count
                    time.sleep(backoff)
                    self._queue.put((job.priority, job.job_id))
                else:
                    # Move to Dead Letter Queue
                    job.status = "DEAD_LETTER"
                    db.commit()

                    # Trigger system alert for dead letter job
                    alert = SystemAlert(
                        severity="ERROR",
                        source="WORKER",
                        title=f"Job {job.job_type} moved to Dead-Letter Queue",
                        message=f"Job {job.job_id} failed after {job.retry_count} attempts. Error [{err_cls}]: {err_msg}",
                        metadata_json={"job_id": job.job_id, "job_type": job.job_type, "error_class": err_cls}
                    )
                    db.add(alert)
                    db.commit()

        finally:
            db.close()

# Global singleton
automation_engine = AutomationEngine()
automation_engine.start_worker()
