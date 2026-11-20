"""Document Processing Pipeline Service.

Coordinates PDF upload validation, storage persistence, page deconstruction,
OCR execution, database recording, and duplicate detection.

All database sessions in this service use ``tenant_session()`` to ensure the
``app.current_college_id`` GUC is set before every query, activating
PostgreSQL RLS policies for the college tenant scope.
"""

from datetime import datetime, timezone
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import tenant_session
from app.models.document import Document, DocumentPage, DocumentParagraph
from app.services.pdf_processor import pdf_processor
from app.services.pdf_validator import PDFValidationError, validate_pdf_file
from app.services.storage_service import document_storage_service

logger = logging.getLogger("college_chatbot.document_service")


class DocumentProcessingService:
    """End-to-end pipeline service for institutional PDF documents."""

    @staticmethod
    def _split_paragraphs(page_text: str) -> List[str]:
        """Split extracted page text while retaining headings and table blocks."""
        return [
            paragraph.strip()
            for paragraph in re.split(r"\n\s*\n", page_text)
            if paragraph.strip()
        ]

    async def register_and_upload(
        self,
        college_id: uuid.UUID,
        user_id: Optional[uuid.UUID],
        file_bytes: bytes,
        original_filename: str,
        declared_mime_type: Optional[str] = "application/pdf",
        category: str = "GENERAL",
        description: Optional[str] = None,
    ) -> Tuple[Document, bool]:
        """Validates, stores, and registers a PDF document for asynchronous processing.

        Returns:
            Tuple of (Document model, is_duplicate boolean).
        """
        # 1. Strict File Validation & Magic Byte Check
        validation_res = validate_pdf_file(
            file_bytes=file_bytes,
            original_filename=original_filename,
            declared_mime_type=declared_mime_type,
        )

        checksum = validation_res["checksum_sha256"]
        total_pages = validation_res["total_pages"]
        clean_filename = validation_res["sanitized_filename"]
        file_size = validation_res["file_size_bytes"]

        doc_id: Optional[uuid.UUID] = None
        uploaded_path: Optional[str] = None
        try:
            async with tenant_session(college_id=college_id) as session:
                # 2. Check for duplicate upload in this college tenant
                query = select(Document).where(
                    Document.college_id == college_id,
                    Document.checksum_sha256 == checksum,
                )
                res = await session.execute(query)
                existing_doc = res.scalar_one_or_none()

                if existing_doc and existing_doc.processing_status != "DELETED":
                    logger.info(
                        "Duplicate document detected for college %s: checksum=%s",
                        college_id,
                        checksum,
                    )
                    return existing_doc, True

                # 3. Create document record with QUEUED status
                doc_id = uuid.uuid4()
                storage_path = document_storage_service.build_storage_path(college_id, doc_id)

                doc = Document(
                    id=doc_id,
                    college_id=college_id,
                    uploaded_by_user_id=user_id,
                    original_filename=clean_filename,
                    storage_path=storage_path,
                    mime_type="application/pdf",
                    file_size_bytes=file_size,
                    total_pages=total_pages,
                    checksum_sha256=checksum,
                    processing_status="QUEUED",
                    category=category or "GENERAL",
                    description=description,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                # Upload first so failed storage cannot leave document metadata.
                uploaded_path = await document_storage_service.upload_file(
                    college_id=college_id,
                    document_id=doc_id,
                    file_bytes=file_bytes,
                    mime_type="application/pdf",
                )
                session.add(doc)
                await session.flush()

            return doc, False
        except Exception:
            # A successful non-upsert upload created a new object at this
            # tenant-scoped path. The transaction context has rolled back by
            # the time control reaches here, so remove only that object.
            if uploaded_path and doc_id and document_storage_service.is_supabase_configured:
                expected_path = document_storage_service.build_storage_path(college_id, doc_id)
                if uploaded_path == expected_path:
                    try:
                        removed = await document_storage_service.delete_file(college_id, uploaded_path)
                        if not removed:
                            logger.error(
                                "Could not clean up newly uploaded Supabase object in bucket %s at %s",
                                document_storage_service.bucket_name,
                                uploaded_path,
                            )
                    except Exception:
                        logger.exception(
                            "Failed to clean up newly uploaded Supabase object in bucket %s at %s",
                            document_storage_service.bucket_name,
                            uploaded_path,
                        )
            raise

    async def execute_document_processing(
        self,
        document_id: uuid.UUID,
        college_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """Background execution unit: extracts pages, tables, and applies OCR where needed."""
        async with tenant_session(college_id=college_id) as session:
            doc = await session.get(Document, document_id)
            if not doc or doc.college_id != college_id:
                logger.error("Processing aborted: Document %s not found for tenant %s", document_id, college_id)
                return {"success": False, "error": "Document not found."}

            doc.processing_status = "PROCESSING"
            doc.updated_at = datetime.now(timezone.utc)
            await session.commit()

        try:
            # 1. Fetch file bytes from storage
            file_bytes = await document_storage_service.get_file_bytes(college_id, doc.storage_path)

            # 2. Extract text, tables, and OCR
            extraction_res = pdf_processor.process_pdf(
                file_bytes=file_bytes,
                original_filename=doc.original_filename,
                enable_ocr=True,
            )

            title = extraction_res["title"]
            total_pages = extraction_res["total_pages"]
            pages_list = extraction_res["pages"]
            ocr_applied = extraction_res["ocr_applied"]
            if not pages_list or not any(
                len((page.extracted_text or "").strip()) >= 40 for page in pages_list
            ):
                raise ValueError("PDF extraction produced no usable page evidence.")

            # 3. Save page records into database
            async with tenant_session(college_id=college_id) as session:
                # Clear any existing pages if reprocessing
                await session.execute(
                    delete(DocumentPage).where(DocumentPage.document_id == document_id)
                )

                now = datetime.now(timezone.utc)
                for p in pages_list:
                    page_id = uuid.uuid4()
                    page_row = DocumentPage(
                        id=page_id,
                        document_id=document_id,
                        college_id=college_id,
                        page_number=p.page_number,
                        extracted_text=p.extracted_text,
                        is_scanned=p.is_scanned,
                        ocr_applied=p.ocr_applied,
                        ocr_confidence=p.ocr_confidence,
                        extraction_method="PYMUPDF+TESSERACT" if p.ocr_applied else "PYMUPDF",
                        tables_markdown=p.tables_markdown,
                        has_tables=p.has_tables,
                        word_count=p.word_count,
                        char_count=p.char_count,
                        processed_at=now,
                    )
                    session.add(page_row)
                    for paragraph_index, paragraph_text in enumerate(
                        self._split_paragraphs(p.extracted_text)
                    ):
                        session.add(
                            DocumentParagraph(
                                id=uuid.uuid4(),
                                page_id=page_id,
                                document_id=document_id,
                                paragraph_index=paragraph_index,
                                paragraph_text=paragraph_text,
                            )
                        )

                # Update document header
                doc_record = await session.get(Document, document_id)
                if doc_record:
                    doc_record.title = title
                    doc_record.total_pages = total_pages
                    doc_record.ocr_applied = ocr_applied
                    doc_record.extraction_method = "PYMUPDF+TESSERACT" if ocr_applied else "PYMUPDF"
                    doc_record.updated_at = now

                await session.commit()

            # Keep extraction and indexing in one background job. Knowledge chunks
            # are staged for review; publication remains an explicit admin action.
            from app.services.knowledge_service import knowledge_service

            async with tenant_session(college_id=college_id) as session:
                indexing_result = await knowledge_service.process_document_pages(
                    college_id=college_id,
                    document_id=document_id,
                    session=session,
                )
            if not indexing_result["chunks_created"] and not indexing_result["chunks_skipped"]:
                raise ValueError("PDF indexing produced no usable knowledge chunks.")

            async with tenant_session(college_id=college_id) as session:
                doc_record = await session.get(Document, document_id)
                if doc_record:
                    doc_record.processing_status = "PENDING_REVIEW"
                    doc_record.failure_reason = None
                    doc_record.updated_at = datetime.now(timezone.utc)

            logger.info(
                "Document %s successfully processed. Total pages: %s (OCR applied: %s)",
                document_id,
                total_pages,
                ocr_applied,
            )
            return {
                "success": True,
                "document_id": str(document_id),
                "total_pages": total_pages,
                "ocr_applied": ocr_applied,
                "paragraphs_created": sum(
                    len(self._split_paragraphs(page.extracted_text)) for page in pages_list
                ),
                "chunks_created": indexing_result["chunks_created"],
                "chunks_skipped": indexing_result["chunks_skipped"],
                "facts_created": indexing_result.get("facts_created", 0),
            }

        except Exception as exc:
            logger.error("Document processing failed for %s: %s", document_id, str(exc), exc_info=True)
            async with tenant_session(college_id=college_id) as session:
                doc_record = await session.get(Document, document_id)
                if doc_record:
                    doc_record.processing_status = "FAILED"
                    doc_record.failure_reason = str(exc)
                    doc_record.updated_at = datetime.now(timezone.utc)
                    await session.commit()

            return {"success": False, "error": str(exc)}

    async def list_document_pages(
        self,
        college_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> List[DocumentPage]:
        """Retrieves page-by-page extracted text and OCR status with tenant isolation."""
        async with tenant_session(college_id=college_id) as session:
            # Check ownership
            doc = await session.get(Document, document_id)
            if not doc or doc.college_id != college_id:
                return []

            res = await session.execute(
                select(DocumentPage)
                .where(DocumentPage.document_id == document_id)
                .order_by(DocumentPage.page_number.asc())
            )
            return list(res.scalars().all())


# Singleton instance
document_service = DocumentProcessingService()

