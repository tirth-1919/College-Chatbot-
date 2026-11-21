"""SQLAlchemy ORM Models Registry.

Exports all 20 required entities for clean importing and Alembic metadata reflection.
"""

from app.database.base import Base
from app.models.college import College
from app.models.user import User
from app.models.membership import CollegeMembership
from app.models.website import WebsiteSource, WebsitePage, CrawlJob, CrawlEvent
from app.models.document import Document, DocumentPage, DocumentParagraph
from app.models.knowledge import ExtractedFact, KnowledgeChunk, KnowledgeReview
from app.models.chat import ChatSession, ChatMessage
from app.models.ai import AIProviderConfig, AIProviderEvent
from app.models.audit import AuditLog
from app.models.feedback_support import Feedback, SupportTicket, SupportTicketReply
from app.models.notification import InAppNotification
from app.models.academic import AcademicCourse, AcademicFee, CollegeGalleryImage, AcademicChangeHistory
from app.models.registration import (
    CollegeRegistration,
    RegistrationReview,
    CollegeAdminInvitation,
    CollegeOnboardingProgress,
    NotificationLog,
)

# Aliases to match alternative naming in specification
CrawlJobEvent = CrawlEvent
ProviderEvent = AIProviderEvent

__all__ = [
    "Base",
    # 1. Tenant & Core Identity
    "College",
    "User",
    "CollegeMembership",
    # 2. Website Crawler Subsystem
    "WebsiteSource",
    "WebsitePage",
    "CrawlJob",
    "CrawlEvent",
    "CrawlJobEvent",
    # 3. Document Processing & OCR
    "Document",
    "DocumentPage",
    "DocumentParagraph",
    # 4. Knowledge Base & Human Review
    "ExtractedFact",
    "KnowledgeChunk",
    "KnowledgeReview",
    # 5. Chat & Student Inquiries
    "ChatSession",
    "ChatMessage",
    "Feedback",
    "SupportTicket",
    "SupportTicketReply",
    "InAppNotification",
    "AcademicCourse",
    "AcademicFee",
    "CollegeGalleryImage",
    "AcademicChangeHistory",
    # 6. AI Management & Telemetry
    "AIProviderConfig",
    "AIProviderEvent",
    "ProviderEvent",
    "AuditLog",
    # 7. Phase 6: College Registration & Onboarding
    "CollegeRegistration",
    "RegistrationReview",
    "CollegeAdminInvitation",
    "CollegeOnboardingProgress",
    "NotificationLog",
]

