from backend.app.core.database import Base
from backend.app.models.college import College, ChangeRequest, Notification, WebsiteSyncHistory
from backend.app.models.user import User, UserSession
from backend.app.models.conversation import Conversation, Message, MessageAttachment
from backend.app.models.knowledge import AitEntity, AitKnowledgeVersion, WebsiteSnapshot, KnowledgeGap
from backend.app.models.knowledge_categories import KnowledgeCategory, KnowledgeRecord
from backend.app.models.document import Document, DocumentChunk
from backend.app.models.image import AitImage, ImageProvenance
from backend.app.models.audit import AuditLog, SecurityEvent
from backend.app.models.admin_system import (
    AiProviderConfig,
    AiModelRegistry,
    AiQuota,
    AiUsageLog,
    KnowledgeConflict,
    SystemPrompt,
    PromptVersion,
    FeatureFlag,
    SystemBackup,
)

from backend.app.models.automation import (
    AutomationJob,
    AutomationJobRun,
    DistributedLock,
    SystemEvent,
    SystemAlert,
    KnowledgeEvaluation,
    MaintenanceState,
    SystemMetric,
)

__all__ = [
    "Base",
    "College",
    "ChangeRequest",
    "Notification",
    "WebsiteSyncHistory",
    "User",
    "UserSession",
    "Conversation",
    "Message",
    "MessageAttachment",
    "AitEntity",
    "AitKnowledgeVersion",
    "WebsiteSnapshot",
    "KnowledgeGap",
    "KnowledgeCategory",
    "KnowledgeRecord",
    "Document",
    "DocumentChunk",
    "AitImage",
    "ImageProvenance",
    "AuditLog",
    "SecurityEvent",
    "AiProviderConfig",
    "AiModelRegistry",
    "AiQuota",
    "AiUsageLog",
    "KnowledgeConflict",
    "SystemPrompt",
    "PromptVersion",
    "FeatureFlag",
    "SystemBackup",
    "AutomationJob",
    "AutomationJobRun",
    "DistributedLock",
    "SystemEvent",
    "SystemAlert",
    "KnowledgeEvaluation",
    "MaintenanceState",
    "SystemMetric",
]

