import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, JSON, Integer, Float
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class AutomationJob(Base):
    __tablename__ = "automation_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    job_id = Column(String(100), unique=True, index=True, nullable=False)
    job_type = Column(String(100), index=True, nullable=False)
    # Statuses: QUEUED, RUNNING, SUCCEEDED, FAILED, RETRYING, CANCELLED, DEAD_LETTER
    status = Column(String(50), default="QUEUED", index=True, nullable=False)
    priority = Column(Integer, default=5, nullable=False)  # 1 (highest) to 10 (lowest)
    
    # Timing
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Retry & Fault Handling
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    # Error classification: TRANSIENT, PERMANENT, AUTHENTICATION, RATE_LIMIT, VALIDATION, SECURITY, DEPENDENCY, UNKNOWN
    error_class = Column(String(50), nullable=True)
    error = Column(Text, nullable=True)
    
    # Execution & Idempotency
    idempotency_key = Column(String(255), unique=True, index=True, nullable=True)
    source_hash = Column(String(100), nullable=True)
    worker_id = Column(String(100), nullable=True)
    payload = Column(JSON, default=dict)
    execution_metadata = Column(JSON, default=dict)

    runs = relationship("AutomationJobRun", back_populates="job", cascade="all, delete-orphan", order_by="AutomationJobRun.attempt_number.desc()")

class AutomationJobRun(Base):
    __tablename__ = "automation_job_runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    job_ref_id = Column(String(36), ForeignKey("automation_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_number = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Float, default=0.0)
    worker_id = Column(String(100), nullable=True)
    error_class = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    run_log = Column(Text, nullable=True)

    job = relationship("AutomationJob", back_populates="runs")

class DistributedLock(Base):
    __tablename__ = "distributed_locks"

    lock_key = Column(String(200), primary_key=True)
    owner = Column(String(100), nullable=False)
    acquired_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=False, index=True)

class SystemEvent(Base):
    __tablename__ = "system_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    # e.g., KNOWLEDGE_UPDATED, IMAGE_UPDATED, DOCUMENT_PUBLISHED, WEBSITE_SYNC_COMPLETED,
    # AI_PROVIDER_FAILED, AI_PROVIDER_RECOVERED, QUOTA_CHANGED, KNOWLEDGE_CONFLICT_CREATED,
    # KNOWLEDGE_GAP_CREATED, SECURITY_ALERT_CREATED
    event_type = Column(String(100), index=True, nullable=False)
    source = Column(String(100), nullable=False)
    entity_id = Column(String(100), nullable=True)
    payload = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

class SystemAlert(Base):
    __tablename__ = "system_alerts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    # Severity: INFO, WARNING, ERROR, CRITICAL
    severity = Column(String(20), default="WARNING", index=True, nullable=False)
    source = Column(String(100), nullable=False, index=True)  # AI_PROVIDER, DATABASE, SYNC, REDIS, WORKER, SECURITY
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    # Status: OPEN, ACKNOWLEDGED, RESOLVED
    status = Column(String(30), default="OPEN", index=True, nullable=False)
    acknowledged_by = Column(String(100), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(100), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

class KnowledgeEvaluation(Base):
    __tablename__ = "knowledge_evaluations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    suite_name = Column(String(100), default="AIT_GOLDEN_EVALUATION_SET", nullable=False)
    version_tag = Column(String(50), nullable=False)
    total_queries = Column(Integer, default=0, nullable=False)
    passed_queries = Column(Integer, default=0, nullable=False)
    failed_queries = Column(Integer, default=0, nullable=False)
    accuracy_score = Column(Float, default=0.0, nullable=False)
    regression_detected = Column(Boolean, default=False, nullable=False)
    domain_scores = Column(JSON, default=dict)  # BCA, BBA, MCA, MBA, CSE, IT, Faculty, Fees, Admissions, etc.
    detailed_results = Column(JSON, default=list)
    evaluated_by = Column(String(100), default="AutomatedWorker", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

class MaintenanceState(Base):
    __tablename__ = "maintenance_state"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    # Mode: NORMAL, MAINTENANCE, READ_ONLY, EMERGENCY
    mode = Column(String(30), default="NORMAL", nullable=False)
    user_message = Column(String(500), default="System is operating normally.")
    is_active = Column(Boolean, default=True, nullable=False)
    updated_by = Column(String(100), default="SUPER_ADMIN")
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class SystemMetric(Base):
    __tablename__ = "system_metrics"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    metric_name = Column(String(100), index=True, nullable=False)
    metric_type = Column(String(30), default="GAUGE")  # COUNTER, GAUGE, HISTOGRAM
    value = Column(Float, nullable=False)
    labels = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
