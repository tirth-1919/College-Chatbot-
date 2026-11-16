"""Knowledge Base Ingestion, Processing, Verification, and Publishing Service.

Orchestrates the lifecycle of academic institutional knowledge from raw
crawled websites and processed PDFs into categorized, deduplicated,
vector-indexed chunks, enforcing strict human-in-the-loop governance.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.knowledge import KnowledgeChunk, KnowledgeReview, ExtractedFact
from app.models.website import WebsitePage
from app.models.document import Document, DocumentPage
from app.services.text_normalizer import text_normalizer
from app.services.chunking_service import chunker_service
from app.services.embedding_service import embedding_service
from app.services.classifier_service import classifier_service

logger = logging.getLogger(__name__)


class KnowledgeService:
    """Enterprise knowledge processing, review lifecycle, and vector indexing manager."""

    # ==========================================================================
    # 1. Ingestion & Processing Pipeline
    # ==========================================================================

    async def process_website_pages(
        self,
        college_id: uuid.UUID,
        session: AsyncSession,
        page_ids: Optional[List[uuid.UUID]] = None,
    ) -> Dict[str, int]:
        """Ingests crawled website pages into staged knowledge chunks.

        Normalizes HTML content, chunks text by headings, classifies,
        computes SHA256 hashes for deduplication, generates 768-dim embeddings,
        and saves chunks in 'PENDING_REVIEW' state.
        """
        query = select(WebsitePage).where(WebsitePage.college_id == college_id)
        if page_ids:
            query = query.where(WebsitePage.id.in_(page_ids))

        result = await session.execute(query)
        pages = list(result.scalars().all())

        chunks_created = 0
        chunks_skipped = 0

        for page in pages:
            # WebsitePage stores the normalized content in cleaned_text. Older
            # code paths may still populate cleaned_content, so keep a safe
            # fallback while preserving the canonical schema.
            raw_text = getattr(page, "cleaned_text", None) or getattr(page, "cleaned_content", None) or ""
            if not raw_text.strip():
                continue

            processed_chunks = chunker_service.chunk_content(
                content=raw_text,
                source_url=page.url,
                default_heading=page.title or "Official College Website",
                extra_metadata={"crawl_job_id": str(page.crawl_job_id) if page.crawl_job_id else None},
            )

            for p_chunk in processed_chunks:
                # Deduplication check by college_id + content_hash
                existing_stmt = select(KnowledgeChunk.id).where(
                    and_(
                        KnowledgeChunk.college_id == college_id,
                        KnowledgeChunk.content_hash == p_chunk.content_hash,
                    )
                )
                existing = await session.execute(existing_stmt)
                if existing.scalar_one_or_none():
                    chunks_skipped += 1
                    continue

                # Generate vector embedding (768-dim). Fail loudly so the task can be
                # marked failed instead of silently storing a non-semantic fallback vector.
                try:
                    embedding_vector = await embedding_service.get_embedding(p_chunk.chunk_text)
                except Exception as exc:
                    logger.error("Website knowledge indexing failed for college %s page %s: %s", college_id, page.id, exc)
                    raise RuntimeError(f"Embedding generation failed for website chunk: {exc}") from exc

                new_chunk = KnowledgeChunk(
                    id=uuid.uuid4(),
                    college_id=college_id,
                    source_type="OFFICIAL_WEBSITE",
                    source_id=page.id,
                    source_url=p_chunk.source_url,
                    category=p_chunk.category,
                    heading=p_chunk.heading,
                    content_hash=p_chunk.content_hash,
                    chunk_text=p_chunk.chunk_text,
                    chunk_metadata=p_chunk.metadata,
                    embedding=embedding_vector,
                    status="PENDING_REVIEW",  # Never auto-publish
                    is_active=False,
                )
                session.add(new_chunk)
                chunks_created += 1

        await session.commit()
        return {
            "pages_processed": len(pages),
            "chunks_created": chunks_created,
            "chunks_skipped": chunks_skipped,
        }

    async def process_document_pages(
        self,
        college_id: uuid.UUID,
        document_id: uuid.UUID,
        session: AsyncSession,
    ) -> Dict[str, int]:
        """Ingests OCR and PDF pages into staged knowledge chunks."""
        doc_stmt = select(Document).where(
            and_(Document.college_id == college_id, Document.id == document_id)
        )
        doc_res = await session.execute(doc_stmt)
        doc = doc_res.scalar_one_or_none()
        if not doc:
            raise ValueError(f"Document {document_id} not found for this college tenant.")

        page_stmt = (
            select(DocumentPage)
            .where(DocumentPage.document_id == document_id)
            .order_by(DocumentPage.page_number)
        )
        page_res = await session.execute(page_stmt)
        pages = list(page_res.scalars().all())

        chunks_created = 0
        chunks_skipped = 0

        for page in pages:
            text_content = page.page_text or ""
            if not text_content.strip():
                continue

            processed_chunks = chunker_service.chunk_content(
                content=text_content,
                page_number=page.page_number,
                default_heading=f"{doc.original_filename} - Page {page.page_number}",
                extra_metadata={"document_id": str(document_id), "ocr_applied": page.has_ocr_content},
            )

            for p_chunk in processed_chunks:
                # Deduplication check
                existing_stmt = select(KnowledgeChunk.id).where(
                    and_(
                        KnowledgeChunk.college_id == college_id,
                        KnowledgeChunk.content_hash == p_chunk.content_hash,
                    )
                )
                existing = await session.execute(existing_stmt)
                if existing.scalar_one_or_none():
                    chunks_skipped += 1
                    continue

                try:
                    embedding_vector = await embedding_service.get_embedding(p_chunk.chunk_text)
                except Exception as exc:
                    logger.error("Document knowledge indexing failed for college %s document %s page %s: %s", college_id, document_id, page.id, exc)
                    raise RuntimeError(f"Embedding generation failed for document chunk: {exc}") from exc

                new_chunk = KnowledgeChunk(
                    id=uuid.uuid4(),
                    college_id=college_id,
                    source_type="PDF",
                    source_id=doc.id,
                    page_number=page.page_number,
                    category=p_chunk.category,
                    heading=p_chunk.heading,
                    content_hash=p_chunk.content_hash,
                    chunk_text=p_chunk.chunk_text,
                    chunk_metadata=p_chunk.metadata,
                    embedding=embedding_vector,
                    status="PENDING_REVIEW",  # Never auto-publish
                    is_active=False,
                )
                session.add(new_chunk)
                chunks_created += 1

        await session.commit()
        return {
            "pages_processed": len(pages),
            "chunks_created": chunks_created,
            "chunks_skipped": chunks_skipped,
        }

    # ==========================================================================
    # 2. Human-in-the-Loop Review & Publishing Lifecycle
    # ==========================================================================

    async def approve_chunk(
        self,
        college_id: uuid.UUID,
        chunk_id: uuid.UUID,
        reviewer_id: Optional[uuid.UUID],
        comments: Optional[str],
        session: AsyncSession,
    ) -> Optional[KnowledgeChunk]:
        """Approves a chunk. Retains status as APPROVED (not yet published)."""
        stmt = select(KnowledgeChunk).where(
            and_(KnowledgeChunk.college_id == college_id, KnowledgeChunk.id == chunk_id)
        )
        res = await session.execute(stmt)
        chunk = res.scalar_one_or_none()
        if not chunk:
            return None

        chunk.status = "APPROVED"
        chunk.is_active = False  # Approved, but separate publishing action required

        review = KnowledgeReview(
            id=uuid.uuid4(),
            chunk_id=chunk.id,
            reviewed_by_user_id=reviewer_id,
            review_action="APPROVE",
            notes=comments,
        )
        session.add(review)
        await session.commit()
        return chunk

    async def reject_chunk(
        self,
        college_id: uuid.UUID,
        chunk_id: uuid.UUID,
        reviewer_id: Optional[uuid.UUID],
        comments: Optional[str],
        session: AsyncSession,
    ) -> Optional[KnowledgeChunk]:
        """Rejects a chunk and marks it inactive."""
        stmt = select(KnowledgeChunk).where(
            and_(KnowledgeChunk.college_id == college_id, KnowledgeChunk.id == chunk_id)
        )
        res = await session.execute(stmt)
        chunk = res.scalar_one_or_none()
        if not chunk:
            return None

        chunk.status = "REJECTED"
        chunk.is_active = False

        review = KnowledgeReview(
            id=uuid.uuid4(),
            chunk_id=chunk.id,
            reviewed_by_user_id=reviewer_id,
            review_action="REJECT",
            notes=comments,
        )
        session.add(review)
        await session.commit()
        return chunk

    async def publish_chunk(
        self,
        college_id: uuid.UUID,
        chunk_id: uuid.UUID,
        reviewer_id: Optional[uuid.UUID],
        session: AsyncSession,
    ) -> Optional[KnowledgeChunk]:
        """Promotes an APPROVED chunk to PUBLISHED, enabling live student vector retrieval."""
        stmt = select(KnowledgeChunk).where(
            and_(KnowledgeChunk.college_id == college_id, KnowledgeChunk.id == chunk_id)
        )
        res = await session.execute(stmt)
        chunk = res.scalar_one_or_none()
        if not chunk:
            return None

        chunk.status = "PUBLISHED"
        chunk.is_active = True

        review = KnowledgeReview(
            id=uuid.uuid4(),
            chunk_id=chunk.id,
            reviewed_by_user_id=reviewer_id,
            review_action="PUBLISH",
            notes="Published to live student RAG retrieval",
        )
        session.add(review)
        await session.commit()
        return chunk

    async def unpublish_chunk(
        self,
        college_id: uuid.UUID,
        chunk_id: uuid.UUID,
        reviewer_id: Optional[uuid.UUID],
        session: AsyncSession,
    ) -> Optional[KnowledgeChunk]:
        """Reverts a PUBLISHED chunk back to APPROVED and disables live retrieval."""
        stmt = select(KnowledgeChunk).where(
            and_(KnowledgeChunk.college_id == college_id, KnowledgeChunk.id == chunk_id)
        )
        res = await session.execute(stmt)
        chunk = res.scalar_one_or_none()
        if not chunk:
            return None

        chunk.status = "APPROVED"
        chunk.is_active = False

        review = KnowledgeReview(
            id=uuid.uuid4(),
            chunk_id=chunk.id,
            reviewed_by_user_id=reviewer_id,
            review_action="UNPUBLISH",
            notes="Unpublished from live student RAG retrieval",
        )
        session.add(review)
        await session.commit()
        return chunk

    async def update_chunk_text(
        self,
        college_id: uuid.UUID,
        chunk_id: uuid.UUID,
        new_text: str,
        reviewer_id: Optional[uuid.UUID],
        session: AsyncSession,
    ) -> Optional[KnowledgeChunk]:
        """Edits chunk text and recalculates hash and embedding."""
        stmt = select(KnowledgeChunk).where(
            and_(KnowledgeChunk.college_id == college_id, KnowledgeChunk.id == chunk_id)
        )
        res = await session.execute(stmt)
        chunk = res.scalar_one_or_none()
        if not chunk:
            return None

        normalized = text_normalizer.normalize_text(new_text)
        chunk.chunk_text = normalized
        chunk.content_hash = text_normalizer.compute_sha256(normalized)
        chunk.embedding = await embedding_service.get_embedding(normalized)

        review = KnowledgeReview(
            id=uuid.uuid4(),
            chunk_id=chunk.id,
            reviewed_by_user_id=reviewer_id,
            review_action="EDIT",
            edited_chunk_text=normalized,
            notes="Administrator corrected chunk text",
        )
        session.add(review)
        await session.commit()
        return chunk


knowledge_service = KnowledgeService()

