from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from pydantic import BaseModel
from backend.app.core.database import get_db
from backend.app.api.v1.admin.auth import get_current_admin
from backend.app.automation.engine import automation_engine
from backend.app.automation.jobs import JOBS_MAP
from backend.app.models.automation import AutomationJob, AutomationJobRun, DistributedLock

router = APIRouter(prefix="/automation", tags=["Admin Automation Engine"])

class JobTriggerRequest(BaseModel):
    job_type: str
    priority: int = 5
    payload: Optional[Dict[str, Any]] = None

JOB_METADATA = {
    "ait_website_sync": "Synchronizes official AIT website announcements & pages into snapshot store",
    "website_change_detection": "Detects content changes across crawled college URLs",
    "image_sync": "Synchronizes local campus images with official AIT repository",
    "image_verification": "Verifies imagery provenance and tags official AIT visual assets",
    "document_ingestion": "Processes pending circulars, brochures, and academic PDFs",
    "ocr_processing": "Isolates and executes OCR text extraction on uploaded scans",
    "rag_indexing": "Incrementally indexes published chunks into vector embeddings",
    "rag_reindexing": "Performs rolling zero-downtime vector reindex with rollback safety",
    "stale_knowledge_detection": "Scans and flags verified knowledge unreviewed for >180 days",
    "knowledge_conflict_detection": "Detects discrepancies between website text and DB entities",
    "knowledge_gap_analysis": "Analyzes unanswered queries and clusters knowledge gaps",
    "question_clustering": "Clusters student inquiries into trending academic topics",
    "ai_provider_health_checks": "Executes ping and capability probes against Gemini, OpenAI & Ollama",
    "quota_updates": "Refreshes provider token limits and daily rate allocations",
    "cache_cleanup": "Invalidates expired semantic query caches",
    "temporary_file_cleanup": "Purges temporary session uploads older than 24 hours",
    "backup_creation": "Creates an encrypted database and metadata backup archive",
    "restore_verification": "Automates isolated restore test to verify database integrity",
    "knowledge_evaluation": "Executes golden evaluation suite across 16 core AIT academic domains",
    "regression_evaluation": "Evaluates accuracy delta against previous version before publication",
    "security_scans": "Analyzes traffic for prompt injections, oversized uploads, and token abuse",
    "alert_processing": "Aggregates and escalates critical unacknowledged system alerts",
    "dead_letter_processing": "Inspects and processes failed tasks in the dead-letter queue",
    "storage_cleanup": "Removes orphaned files and stale image caches safely"
}

@router.get("/jobs")
def list_available_jobs(db: Session = Depends(get_db), current_admin = Depends(get_current_admin)):
    """Lists all 24 registered automated jobs, their descriptions, and recent execution statuses."""
    recent_jobs = db.query(AutomationJob).order_by(AutomationJob.created_at.desc()).limit(50).all()
    recent_by_type = {}
    for j in recent_jobs:
        if j.job_type not in recent_by_type:
            recent_by_type[j.job_type] = {
                "job_id": j.job_id,
                "status": j.status,
                "completed_at": j.completed_at.isoformat() if j.completed_at else None,
                "retry_count": j.retry_count,
                "error": j.error
            }

    result = []
    for job_type, desc in JOB_METADATA.items():
        last_run = recent_by_type.get(job_type)
        result.append({
            "job_type": job_type,
            "description": desc,
            "is_registered": job_type in automation_engine._registry,
            "last_run": last_run
        })
    return {"total_jobs": len(result), "jobs": result}

@router.post("/jobs/trigger")
def trigger_job(req: JobTriggerRequest, db: Session = Depends(get_db), current_admin = Depends(get_current_admin)):
    """Manually triggers any of the 24 automated background jobs."""
    if req.job_type not in JOBS_MAP:
        raise HTTPException(status_code=400, detail=f"Job type '{req.job_type}' is not recognized.")

    job_id = automation_engine.enqueue_job(
        job_type=req.job_type,
        payload=req.payload or {},
        priority=req.priority
    )

    return {
        "success": True,
        "message": f"Job {req.job_type} enqueued successfully.",
        "job_id": job_id,
        "priority": req.priority
    }

@router.get("/dead-letter")
def list_dead_letter_queue(db: Session = Depends(get_db), current_admin = Depends(get_current_admin)):
    """Retrieves all failed jobs resting in the Dead-Letter Queue."""
    dlq_jobs = db.query(AutomationJob).filter(AutomationJob.status == "DEAD_LETTER").order_by(AutomationJob.created_at.desc()).all()
    return {
        "count": len(dlq_jobs),
        "dead_letters": [
            {
                "job_id": j.job_id,
                "job_type": j.job_type,
                "status": j.status,
                "retry_count": j.retry_count,
                "max_retries": j.max_retries,
                "error_class": j.error_class,
                "error": j.error,
                "created_at": j.created_at.isoformat() if j.created_at else None,
                "execution_metadata": j.execution_metadata
            }
            for j in dlq_jobs
        ]
    }

@router.post("/dead-letter/{job_id}/retry")
def retry_dead_letter_job(job_id: str, db: Session = Depends(get_db), current_admin = Depends(get_current_admin)):
    """Retries a failed job from the Dead-Letter Queue."""
    job = db.query(AutomationJob).filter(AutomationJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = "QUEUED"
    job.retry_count = 0
    job.error = None
    job.error_class = None
    db.commit()

    automation_engine._queue.put((job.priority, job.job_id))
    return {"success": True, "message": f"Job {job_id} re-queued for execution."}

@router.delete("/dead-letter/{job_id}")
def cancel_dead_letter_job(job_id: str, db: Session = Depends(get_db), current_admin = Depends(get_current_admin)):
    """Cancels or purges a dead-letter job from the queue."""
    job = db.query(AutomationJob).filter(AutomationJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = "CANCELLED"
    db.commit()
    return {"success": True, "message": f"Job {job_id} marked as CANCELLED."}

@router.get("/worker-status")
def get_worker_status(db: Session = Depends(get_db), current_admin = Depends(get_current_admin)):
    """Returns the worker daemon status, queue depth, and active distributed locks."""
    locks = db.query(DistributedLock).all()
    return {
        "worker_id": automation_engine.worker_id,
        "is_running": automation_engine._running,
        "queue_depth": automation_engine._queue.qsize(),
        "registered_jobs_count": len(automation_engine._registry),
        "active_locks": [
            {
                "lock_key": l.lock_key,
                "owner": l.owner,
                "acquired_at": l.acquired_at.isoformat() if l.acquired_at else None,
                "expires_at": l.expires_at.isoformat() if l.expires_at else None
            }
            for l in locks
        ]
    }
