import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from backend.app.models.document import (
    Document, DocumentChunk,
    VISIBILITY_ADMIN_VERIFIED, VISIBILITY_PUBLIC_INSTITUTIONAL, VISIBILITY_PRIVATE_USER
)

INSTITUTIONAL_VISIBILITIES = [VISIBILITY_ADMIN_VERIFIED, VISIBILITY_PUBLIC_INSTITUTIONAL]


class RAGEngine:
    @classmethod
    def search(cls, db, query, college_id=None, user_id=None, top_k=5):
        """
        CRITICAL: college_id filter is applied BEFORE any scoring.
        A student from College A will NEVER see College B's documents.
        If college_id is None (legacy path), still restrict to institutional only.
        """
        query_terms = [t.lower() for t in query.split() if len(t) > 2]
        if not query_terms:
            return []

        institutional_filter = Document.visibility.in_(INSTITUTIONAL_VISIBILITIES)

        # Phase 8: MANDATORY tenant pre-filter
        if college_id:
            tenant_filter = Document.college_id == college_id
            if user_id:
                doc_filter = and_(
                    tenant_filter,
                    or_(
                        institutional_filter,
                        and_(Document.user_id == user_id, Document.visibility == VISIBILITY_PRIVATE_USER)
                    )
                )
            else:
                doc_filter = and_(tenant_filter, institutional_filter)
        else:
            # No college context: restrict to institutional, no cross-college
            if user_id:
                doc_filter = or_(
                    institutional_filter,
                    and_(Document.user_id == user_id, Document.visibility == VISIBILITY_PRIVATE_USER)
                )
            else:
                doc_filter = institutional_filter

        chunks = (db.query(DocumentChunk)
            .join(Document, DocumentChunk.document_id == Document.id)
            .filter(doc_filter).all())

        scored_chunks = []
        for ch in chunks:
            score = sum(1 for t in query_terms if t in ch.content.lower())
            if score > 0:
                scored_chunks.append((score, ch))
        scored_chunks.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, ch in scored_chunks[:top_k]:
            doc = ch.document
            results.append({
                "chunk_id": ch.id, "document_id": ch.document_id,
                "college_id": doc.college_id,
                "title": doc.title, "source_url": doc.source_url,
                "visibility": doc.visibility,
                "is_institutional": doc.visibility in INSTITUTIONAL_VISIBILITIES,
                "is_private": doc.visibility == VISIBILITY_PRIVATE_USER,
                "content": ch.content, "score": score,
                "name": doc.title, "details": ch.content,
                "source_type": "institutional_rag" if doc.visibility in INSTITUTIONAL_VISIBILITIES else "user_document",
                "verification_status": doc.visibility,
            })
        return results

    @classmethod
    def index_document(cls, db, title, text_content, doc_type="txt", source_url=None,
                       user_id=None, visibility=VISIBILITY_PRIVATE_USER, college_id=None, chunk_size=400):
        import hashlib
        content_hash = hashlib.sha256(text_content.encode("utf-8")).hexdigest()
        # Duplicate detection scoped per college
        q = db.query(Document).filter(
            Document.content_hash == content_hash, Document.visibility == visibility
        )
        if college_id:
            q = q.filter(Document.college_id == college_id)
        existing = q.first()
        if existing:
            return existing
        doc = Document(
            user_id=user_id,
            college_id=college_id,
            title=title,
            doc_type=doc_type,
            source_url=source_url,
            content_hash=content_hash,
            visibility=visibility
        )
        db.add(doc)
        db.flush()
        nl2 = chr(10) + chr(10)
        paragraphs = text_content.split(nl2)
        current_chunk, current_len, chunks_to_create = [], 0, []
        for para in paragraphs:
            para_clean = para.strip()
            if not para_clean:
                continue
            if current_len + len(para_clean) > chunk_size and current_chunk:
                chunks_to_create.append(" ".join(current_chunk))
                current_chunk, current_len = [para_clean], len(para_clean)
            else:
                current_chunk.append(para_clean)
                current_len += len(para_clean)
        if current_chunk:
            chunks_to_create.append(" ".join(current_chunk))
        for idx, chunk_text in enumerate(chunks_to_create):
            db.add(DocumentChunk(
                document_id=doc.id,
                college_id=college_id,
                chunk_index=idx,
                content=chunk_text,
                metadata_={"source": title, "college_id": college_id}
            ))
        db.commit()
        db.refresh(doc)
        return doc

    @classmethod
    def ingest_document(cls, db, file_path, doc_type, title, user_id=None,
                        source_url=None, visibility=VISIBILITY_ADMIN_VERIFIED, college_id=None):
        import io
        with open(file_path, "rb") as fh:
            raw = fh.read()
        text = ""
        try:
            if doc_type in ["txt", "md", "csv"]:
                text = raw.decode("utf-8", errors="ignore")
            elif doc_type == "pdf":
                from PyPDF2 import PdfReader
                r = PdfReader(io.BytesIO(raw))
                text = (chr(10)+chr(10)).join([p.extract_text() or "" for p in r.pages])
            elif doc_type == "docx":
                import docx as d
                dfile = d.Document(io.BytesIO(raw))
                text = (chr(10)+chr(10)).join([p.text for p in dfile.paragraphs if p.text.strip()])
            elif doc_type == "xlsx":
                import openpyxl
                wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
                ls = []
                for sh in wb.worksheets:
                    ls.append("Sheet: " + sh.title)
                    for row in sh.iter_rows(values_only=True):
                        rt = chr(9).join([str(c) if c is not None else "" for c in row])
                        if rt.strip(): ls.append(rt)
                text = chr(10).join(ls)
            elif doc_type in ["png", "jpg", "jpeg", "webp"]:
                from PIL import Image; import pytesseract
                try: text = pytesseract.image_to_string(Image.open(io.BytesIO(raw))).strip()
                except Exception: text = "Image: " + title
            else:
                text = "Document: " + title
        except Exception as e:
            text = "Error: " + str(e)
        if not text.strip(): text = "Document empty: " + title
        return cls.index_document(
            db=db, title=title, text_content=text,
            doc_type=doc_type, source_url=source_url or file_path,
            user_id=user_id, visibility=visibility, college_id=college_id
        )


rag_engine = RAGEngine()