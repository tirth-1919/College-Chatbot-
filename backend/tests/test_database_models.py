"""Database Schema & SQLAlchemy ORM Model Unit Tests.

Validates that all 20 entities, table names, primary keys, foreign keys,
and column constraints are correctly declared and structurally sound.
"""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.database.base import Base
from app.services.embedding_service import EmbeddingService
from app.services.knowledge_service import KnowledgeService
from app.models import (
    College,
    User,
    CollegeMembership,
    WebsiteSource,
    WebsitePage,
    CrawlJob,
    CrawlEvent,
    Document,
    DocumentPage,
    DocumentParagraph,
    ExtractedFact,
    KnowledgeChunk,
    KnowledgeReview,
    ChatSession,
    ChatMessage,
    AIProviderConfig,
    AIProviderEvent,
    AuditLog,
    Feedback,
    SupportTicket,
)

EXPECTED_20_TABLES = [
    "colleges",
    "users",
    "college_memberships",
    "website_sources",
    "website_pages",
    "crawl_jobs",
    "crawl_events",
    "documents",
    "document_pages",
    "document_paragraphs",
    "extracted_facts",
    "knowledge_chunks",
    "knowledge_reviews",
    "chat_sessions",
    "chat_messages",
    "ai_provider_configs",
    "ai_provider_events",
    "audit_logs",
    "feedback",
    "support_tickets",
]


def test_all_20_tables_registered_in_metadata():
    """Verify that all 20 required entities are registered in SQLAlchemy metadata."""
    registered_tables = list(Base.metadata.tables.keys())
    for expected_table in EXPECTED_20_TABLES:
        assert expected_table in registered_tables, f"Missing table: {expected_table}"
    assert len(EXPECTED_20_TABLES) == 20


def test_college_model_schema():
    """Validate College entity columns, primary key, and unique constraints."""
    table = College.__table__
    assert table.name == "colleges"
    assert "id" in table.c
    assert table.c.id.primary_key
    assert "name" in table.c
    assert "slug" in table.c
    assert table.c.slug.unique
    assert "official_domain" in table.c
    assert "status" in table.c
    assert "is_active" in table.c


def test_user_model_schema():
    """Validate User entity columns and constraints."""
    table = User.__table__
    assert table.name == "users"
    assert table.c.id.primary_key
    assert table.c.email.unique
    assert "role" in table.c
    assert "is_verified" in table.c


def test_tenant_isolation_foreign_keys():
    """Verify that all tenant-owned tables have a foreign key to colleges.id."""
    tenant_tables = [
        WebsiteSource.__table__,
        CrawlJob.__table__,
        WebsitePage.__table__,
        Document.__table__,
        ExtractedFact.__table__,
        KnowledgeChunk.__table__,
        ChatSession.__table__,
        Feedback.__table__,
        SupportTicket.__table__,
    ]

    for table in tenant_tables:
        assert "college_id" in table.c, f"Table {table.name} missing college_id column"
        fks = [fk.target_fullname for fk in table.c.college_id.foreign_keys]
        assert "colleges.id" in fks, f"Table {table.name} college_id does not reference colleges.id"


def test_knowledge_chunk_vector_embedding():
    """Validate that knowledge_chunks contains an embedding column."""
    table = KnowledgeChunk.__table__
    assert "embedding" in table.c
    assert "chunk_text" in table.c
    assert "status" in table.c
    assert "college_id" in table.c


def test_model_instantiation():
    """Verify in-memory model instantiation with sample test attributes."""
    college_id = uuid.uuid4()
    college = College(
        id=college_id,
        name="Test Engineering College",
        slug="test-college",
        official_domain="testcollege.edu",
        contact_email="info@testcollege.edu",
    )
    assert college.name == "Test Engineering College"
    assert college.slug == "test-college"
    assert college.id == college_id

    chunk = KnowledgeChunk(
        college_id=college_id,
        source_type="OFFICIAL_WEBSITE",
        source_id=uuid.uuid4(),
        chunk_text="Hostel fee is 25000 per semester.",
        status="PENDING_REVIEW",
    )
    assert chunk.college_id == college_id
    assert chunk.status == "PENDING_REVIEW"


@pytest.mark.asyncio
async def test_process_website_pages_uses_cleaned_text_payload():
    """Website ingestion must read the canonical cleaned_text column instead of a nonexistent attribute."""
    college_id = uuid.uuid4()
    page = SimpleNamespace(
        id=uuid.uuid4(),
        college_id=college_id,
        title="Admissions",
        url="https://example.edu/admissions",
        crawl_job_id=None,
        cleaned_text="Official admissions information.\nFee details and policies.",
    )

    session = MagicMock()
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [page]
    dedupe_result = MagicMock()
    dedupe_result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(side_effect=[list_result, dedupe_result])
    session.commit = AsyncMock()

    chunk = SimpleNamespace(
        content_hash="abc123",
        chunk_text="Official admissions information.",
        category="ADMISSIONS",
        heading="Admissions",
        source_url=page.url,
        metadata={"source": "website"},
    )

    with patch("app.services.knowledge_service.chunker_service.chunk_content", return_value=[chunk]), \
         patch("app.services.knowledge_service.embedding_service.get_embedding", new=AsyncMock(return_value=[0.0] * 768)):
        result = await KnowledgeService().process_website_pages(
            college_id=college_id,
            session=session,
        )

    assert result["pages_processed"] == 1
    assert result["chunks_created"] == 1
    session.add.assert_called_once()
    assert session.execute.await_count == 2


@pytest.mark.asyncio
async def test_embedding_service_failures_are_not_silently_fallback_persisted():
    """Embedding errors must surface as a hard failure instead of silently storing synthetic vectors."""
    svc = EmbeddingService()
    svc.is_placeholder_key = False
    svc.api_key = "valid-key"
    svc.model_name = "text-embedding-004"

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "server error"

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_response)):
        with pytest.raises(RuntimeError, match="Embedding generation failed"):
            await svc.get_embedding("This should fail loudly.")

