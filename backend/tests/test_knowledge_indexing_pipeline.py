"""Focused tests for shared website/PDF knowledge indexing behavior."""

import uuid
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import fitz
import pytest

from app.models.document import Document, DocumentPage, DocumentParagraph
from app.models.knowledge import ExtractedFact, KnowledgeChunk
from app.services.document_service import DocumentProcessingService
from app.services.html_extractor import parse_and_clean_html
from app.services.knowledge_service import KnowledgeService
from app.services.pdf_processor import PDFProcessor, format_table_cells_to_markdown
from app.services.rag_service import RAGService


def _result_with_scalar(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _result_with_rows(rows):
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    result.all.return_value = rows
    return result


def test_html_extractor_preserves_heading_structure_in_stored_text():
    page = parse_and_clean_html(
        "<html><head><title>AIT Admissions</title></head><body>"
        "<main><h1>Admissions</h1><p>Applicants submit forms through the portal.</p>"
        "<h2>Required documents</h2><p>Submit transcripts and identity records.</p></main>"
        "</body></html>",
        "https://ait.example/admissions",
    )

    assert page.title == "AIT Admissions"
    assert "# Admissions" in page.cleaned_text
    assert "## Required documents" in page.cleaned_text
    assert "Applicants submit forms through the portal." in page.cleaned_text
    legacy_text = KnowledgeService._mark_plain_website_headings(
        "Admission Requirements for AIT\n\nApplicants submit forms through the portal."
    )
    assert "## Admission Requirements for AIT" in legacy_text


@pytest.mark.asyncio
async def test_document_indexing_uses_extracted_page_fields_and_stages_fact_and_chunk():
    college_id = uuid.uuid4()
    document_id = uuid.uuid4()
    document = SimpleNamespace(
        id=document_id,
        college_id=college_id,
        original_filename="AIT Prospectus.pdf",
        title="AIT Prospectus",
    )
    page = SimpleNamespace(
        id=uuid.uuid4(),
        college_id=college_id,
        page_number=3,
        extracted_text=(
            "## Admission Requirements\n\n"
            "Applicants must submit the completed form with the required academic records."
        ),
        ocr_applied=False,
    )
    processed_chunk = SimpleNamespace(
        chunk_text="Applicants must submit the completed form with the required academic records.",
        content_hash="content-hash",
        category="ADMISSIONS",
        heading="Admission Requirements",
        metadata={
            "original_filename": document.original_filename,
            "document_title": document.title,
        },
    )
    session = MagicMock()
    session.execute = AsyncMock(
        side_effect=[
            _result_with_scalar(document),
            _result_with_rows([page]),
            _result_with_rows([]),
            _result_with_scalar(None),
        ]
    )
    session.commit = AsyncMock()

    with (
        patch(
            "app.services.knowledge_service.chunker_service.chunk_content",
            return_value=[processed_chunk],
        ),
        patch(
            "app.services.knowledge_service.embedding_service.get_embedding",
            new=AsyncMock(return_value=[0.25] * 768),
        ),
    ):
        result = await KnowledgeService().process_document_pages(
            college_id=college_id,
            document_id=document_id,
            session=session,
        )

    assert result == {
        "pages_processed": 1,
        "chunks_created": 1,
        "chunks_skipped": 0,
        "facts_created": 1,
    }
    staged = [call.args[0] for call in session.add.call_args_list]
    chunk = next(item for item in staged if isinstance(item, KnowledgeChunk))
    fact = next(item for item in staged if isinstance(item, ExtractedFact))
    assert chunk.college_id == college_id
    assert chunk.source_id == document_id
    assert chunk.source_type == "PDF"
    assert chunk.page_number == 3
    assert chunk.embedding is not None and len(chunk.embedding) == 768
    assert chunk.status == "PENDING_REVIEW"
    assert chunk.is_active is False
    assert chunk.chunk_metadata["original_filename"] == document.original_filename
    assert fact.college_id == college_id
    assert fact.source_id == document_id
    assert fact.verification_status == "PENDING"
    session.commit.assert_awaited_once()


def test_pdf_processor_extracts_real_page_text_headings_and_table_cells():
    source = fitz.open()
    page = source.new_page()
    page.insert_text((72, 72), "Admission Requirements", fontsize=20)
    page.insert_text((72, 110), "Applicants must submit the completed form.")
    page.insert_text((72, 130), "Required documents include transcripts and identification.")
    pdf_bytes = source.tobytes()
    source.close()

    extracted = PDFProcessor().process_pdf(
        file_bytes=pdf_bytes,
        original_filename="ait-prospectus.pdf",
        enable_ocr=False,
    )

    assert extracted["total_pages"] == 1
    assert extracted["pages"][0].page_number == 1
    assert "## Admission Requirements" in extracted["pages"][0].extracted_text
    assert "Required documents include transcripts" in extracted["pages"][0].extracted_text
    assert format_table_cells_to_markdown([["Program", "Seats"], ["Engineering", "60"]]).count("|") > 0


@pytest.mark.asyncio
async def test_document_processing_saves_ordered_paragraphs_and_indexes_before_review():
    college_id = uuid.uuid4()
    document_id = uuid.uuid4()
    document = SimpleNamespace(
        id=document_id,
        college_id=college_id,
        storage_path="isolated/test.pdf",
        original_filename="AIT Prospectus.pdf",
        processing_status="QUEUED",
    )
    extracted_page = SimpleNamespace(
        page_number=2,
        extracted_text=(
            "## Admissions\n\nApplicants must complete the admission application online.\n\n"
            "The original transcripts must be submitted during verification."
        ),
        is_scanned=False,
        ocr_applied=False,
        ocr_confidence=None,
        tables_markdown=[],
        has_tables=False,
        word_count=15,
        char_count=140,
    )
    initial_session = MagicMock()
    initial_session.get = AsyncMock(return_value=document)
    initial_session.commit = AsyncMock()
    page_session = MagicMock()
    page_session.execute = AsyncMock()
    page_session.get = AsyncMock(return_value=document)
    page_session.commit = AsyncMock()
    indexing_session = MagicMock()
    final_session = MagicMock()
    final_session.get = AsyncMock(return_value=document)
    final_session.commit = AsyncMock()
    sessions = [initial_session, page_session, indexing_session, final_session]

    @asynccontextmanager
    async def isolated_tenant_session(**_kwargs):
        yield sessions.pop(0)

    with (
        patch("app.services.document_service.tenant_session", isolated_tenant_session),
        patch(
            "app.services.document_service.document_storage_service.get_file_bytes",
            new=AsyncMock(return_value=b"%PDF-isolated-bytes"),
        ),
        patch(
            "app.services.document_service.pdf_processor.process_pdf",
            return_value={
                "title": "AIT Prospectus",
                "total_pages": 1,
                "pages": [extracted_page],
                "ocr_applied": False,
            },
        ),
        patch(
            "app.services.knowledge_service.knowledge_service.process_document_pages",
            new=AsyncMock(
                return_value={
                    "chunks_created": 2,
                    "chunks_skipped": 0,
                    "facts_created": 2,
                }
            ),
        ) as index_document,
    ):
        result = await DocumentProcessingService().execute_document_processing(
            document_id=document_id,
            college_id=college_id,
        )

    assert result["success"] is True
    assert result["paragraphs_created"] == 3
    assert result["chunks_created"] == 2
    assert document.processing_status == "PENDING_REVIEW"
    saved_records = [call.args[0] for call in page_session.add.call_args_list]
    saved_page = next(record for record in saved_records if isinstance(record, DocumentPage))
    paragraphs = [record for record in saved_records if isinstance(record, DocumentParagraph)]
    assert saved_page.college_id == college_id
    assert [paragraph.paragraph_index for paragraph in paragraphs] == [0, 1, 2]
    assert "## Admissions" in paragraphs[0].paragraph_text
    index_document.assert_awaited_once()
    assert index_document.await_args.kwargs["college_id"] == college_id
    assert index_document.await_args.kwargs["document_id"] == document_id


@pytest.mark.asyncio
async def test_empty_pdf_extraction_marks_document_failed_not_reviewable():
    college_id = uuid.uuid4()
    document_id = uuid.uuid4()
    document = SimpleNamespace(
        id=document_id,
        college_id=college_id,
        storage_path="isolated/empty.pdf",
        original_filename="empty.pdf",
        processing_status="QUEUED",
    )
    initial_session = MagicMock()
    initial_session.get = AsyncMock(return_value=document)
    initial_session.commit = AsyncMock()
    failed_session = MagicMock()
    failed_session.get = AsyncMock(return_value=document)
    failed_session.commit = AsyncMock()
    sessions = [initial_session, failed_session]

    @asynccontextmanager
    async def isolated_tenant_session(**_kwargs):
        yield sessions.pop(0)

    with (
        patch("app.services.document_service.tenant_session", isolated_tenant_session),
        patch(
            "app.services.document_service.document_storage_service.get_file_bytes",
            new=AsyncMock(return_value=b"%PDF-isolated-bytes"),
        ),
        patch(
            "app.services.document_service.pdf_processor.process_pdf",
            return_value={
                "title": "Empty",
                "total_pages": 1,
                "pages": [SimpleNamespace(extracted_text="")],
                "ocr_applied": False,
            },
        ),
    ):
        result = await DocumentProcessingService().execute_document_processing(
            document_id=document_id,
            college_id=college_id,
        )

    assert result["success"] is False
    assert "no usable page evidence" in result["error"]
    assert document.processing_status == "FAILED"


@pytest.mark.asyncio
async def test_retrieval_keeps_published_chunks_isolated_by_college():
    ait_id = uuid.uuid4()
    rcti_id = uuid.uuid4()
    embedding = [1.0] + [0.0] * 767
    chunks = [
        KnowledgeChunk(
            college_id=ait_id,
            source_type="OFFICIAL_WEBSITE",
            source_id=uuid.uuid4(),
            chunk_text="AIT offers computer engineering programs.",
            embedding=embedding,
            status="PUBLISHED",
            is_active=True,
        ),
        KnowledgeChunk(
            college_id=rcti_id,
            source_type="OFFICIAL_WEBSITE",
            source_id=uuid.uuid4(),
            chunk_text="RCTI offers mechanical engineering programs.",
            embedding=embedding,
            status="PUBLISHED",
            is_active=True,
        ),
    ]

    async def execute_for_tenant(statement):
        compiled = statement.compile()
        bound_values = compiled.params.values()
        assert ["PUBLISHED"] in bound_values
        assert "is_active" in str(compiled)
        assert "<=>" in str(compiled)
        tenant = next(value for value in bound_values if value in (ait_id, rcti_id))
        return _result_with_rows(
            [
                (chunk, 1.0)
                for chunk in chunks
                if chunk.college_id == tenant
            ]
        )

    session = MagicMock()
    session.execute = AsyncMock(side_effect=execute_for_tenant)
    rag = RAGService()
    with patch(
        "app.services.rag_service.embedding_service.get_embedding",
        new=AsyncMock(return_value=embedding),
    ):
        ait_results = await rag.retrieve_relevant_chunks(ait_id, "engineering programs", session)
        rcti_results = await rag.retrieve_relevant_chunks(rcti_id, "engineering programs", session)

    assert len(ait_results) == len(rcti_results) == 1
    assert ait_results[0][0].college_id == ait_id
    assert "RCTI" not in ait_results[0][0].chunk_text
    assert rcti_results[0][0].college_id == rcti_id
    assert "AIT" not in rcti_results[0][0].chunk_text


@pytest.mark.asyncio
async def test_indexed_chunks_require_explicit_approval_and_publication():
    college_id = uuid.uuid4()
    chunk = KnowledgeChunk(
        college_id=college_id,
        source_type="PDF",
        source_id=uuid.uuid4(),
        chunk_text="A staged PDF chunk with enough content for administrator review.",
        status="PENDING_REVIEW",
        is_active=False,
    )
    session = MagicMock()
    session.execute = AsyncMock(return_value=_result_with_scalar(chunk))
    session.add = MagicMock()
    session.commit = AsyncMock()
    service = KnowledgeService()

    approved = await service.approve_chunk(college_id, chunk.id, None, None, session)
    assert approved is chunk
    assert chunk.status == "APPROVED"
    assert chunk.is_active is False

    published = await service.publish_chunk(college_id, chunk.id, None, session)
    assert published is chunk
    assert chunk.status == "PUBLISHED"
    assert chunk.is_active is True
    assert [item.review_action for item in (call.args[0] for call in session.add.call_args_list)] == [
        "APPROVE",
        "PUBLISH",
    ]


@pytest.mark.asyncio
async def test_answer_context_combines_cited_sources_and_uses_fallback_without_evidence():
    ait_id = uuid.uuid4()
    website = KnowledgeChunk(
        college_id=ait_id,
        source_type="OFFICIAL_WEBSITE",
        source_id=uuid.uuid4(),
        source_url="https://ait.example/admissions",
        heading="Admissions",
        chunk_text="AIT admission forms are submitted online.",
        chunk_metadata={"source_title": "Admissions"},
    )
    pdf = KnowledgeChunk(
        college_id=ait_id,
        source_type="PDF",
        source_id=uuid.uuid4(),
        page_number=4,
        heading="Admission Documents",
        chunk_text="The prospectus lists transcripts and identity documents.",
        chunk_metadata={"original_filename": "AIT Prospectus.pdf"},
    )
    rag = RAGService()
    ai_response = {
        "text": "The website describes online forms and the prospectus lists required documents.",
        "provider": "GEMINI",
        "model": "test-model",
        "prompt_tokens": 1,
        "completion_tokens": 1,
    }
    captured_context = []

    async def capture_ai_response(**kwargs):
        captured_context.extend(kwargs["context_chunks"])
        return ai_response

    with (
        patch.object(rag, "get_recent_conversation_context", new=AsyncMock(return_value=[])),
        patch("app.services.rag_service.ai_provider_service.generate_response", new=capture_ai_response),
        patch.object(rag, "retrieve_relevant_chunks", new=AsyncMock(return_value=[(website, 0.9), (pdf, 0.85)])),
    ):
        combined = await rag.answer_question(
            college_id=ait_id,
            query=(
                "How do I apply online using the admission form, and which "
                "original transcripts and identity documents are required?"
            ),
            session=MagicMock(),
        )

    assert combined["answer_mode"] == "COLLEGE_KNOWLEDGE"
    assert [citation["source_name"] for citation in combined["source_citations"]] == [
        "Admissions",
        "AIT Prospectus.pdf",
    ]
    assert combined["source_citations"][0]["url"] == website.source_url
    assert combined["source_citations"][1]["page_number"] == 4
    assert "AIT Prospectus.pdf" in captured_context[1]["source_title"]

    for source_chunk, expected_source in ((website, "Admissions"), (pdf, "AIT Prospectus.pdf")):
        captured_context.clear()
        with (
            patch.object(rag, "get_recent_conversation_context", new=AsyncMock(return_value=[])),
            patch("app.services.rag_service.ai_provider_service.generate_response", new=capture_ai_response),
            patch.object(
                rag,
                "retrieve_relevant_chunks",
                new=AsyncMock(return_value=[(source_chunk, 0.9)]),
            ),
        ):
            source_answer = await rag.answer_question(
                college_id=ait_id,
                query="Give me the admissions information.",
                session=MagicMock(),
            )
        assert source_answer["answer_mode"] == "COLLEGE_KNOWLEDGE"
        assert source_answer["source_citations"][0]["source_name"] == expected_source

    captured_context.clear()
    with (
        patch.object(rag, "get_recent_conversation_context", new=AsyncMock(return_value=[])),
        patch("app.services.rag_service.settings.AI_GENERAL_ANSWERING_ENABLED", True),
        patch("app.services.rag_service.ai_provider_service.generate_response", new=capture_ai_response),
        patch.object(rag, "retrieve_relevant_chunks", new=AsyncMock(return_value=[])),
    ):
        fallback = await rag.answer_question(
            college_id=ait_id,
            query="What is the capital of France?",
            session=MagicMock(),
        )

    assert fallback["answer_mode"] == "GENERAL_AI"
    assert fallback["is_verified"] is False
    assert fallback["source_citations"] == []
