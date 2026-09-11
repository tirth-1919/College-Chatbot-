import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from backend.app.models.document import Document, DocumentChunk

class RAGEngine:
    """
    RAG system supporting:
    1. Institutional AIT Documents (user_id is None, accessible to all)
    2. Private User Documents (user_id == current_user.id, isolated by tenant permissions)
    """

    @classmethod
    def search(
        cls,
        db: Session,
        query: str,
        user_id: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        query_terms = [t.lower() for t in query.split() if len(t) > 2]
        if not query_terms:
            return []

        # Enforce strict permission boundaries:
        # Include public docs (user_id IS NULL) + user's private docs (user_id == user_id)
        # NEVER include another user's documents!
        doc_filter = Document.user_id == None
        if user_id:
            doc_filter = or_(Document.user_id == None, Document.user_id == user_id)

        # Retrieve relevant chunks
        chunks = (
            db.query(DocumentChunk)
            .join(Document, DocumentChunk.document_id == Document.id)
            .filter(doc_filter)
            .all()
        )

        # Keyword relevance ranking
        scored_chunks = []
        for ch in chunks:
            content_lower = ch.content.lower()
            score = sum(1 for term in query_terms if term in content_lower)
            if score > 0:
                scored_chunks.append((score, ch))

        scored_chunks.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, ch in scored_chunks[:top_k]:
            results.append({
                "chunk_id": ch.id,
                "document_id": ch.document_id,
                "title": ch.document.title,
                "source_url": ch.document.source_url,
                "is_private": ch.document.user_id is not None,
                "content": ch.content,
                "score": score
            })

        return results

    @classmethod
    def index_document(
        cls,
        db: Session,
        title: str,
        text_content: str,
        doc_type: str = "txt",
        source_url: Optional[str] = None,
        user_id: Optional[str] = None,
        chunk_size: int = 400
    ) -> Document:
        import hashlib
        content_hash = hashlib.sha256(text_content.encode('utf-8')).hexdigest()

        doc = Document(
            user_id=user_id,
            title=title,
            doc_type=doc_type,
            source_url=source_url,
            content_hash=content_hash
        )
        db.add(doc)
        db.flush()

        # Simple semantic chunking by paragraph and size
        paragraphs = text_content.split("\n\n")
        current_chunk = []
        current_len = 0
        chunks_to_create = []

        for para in paragraphs:
            para_clean = para.strip()
            if not para_clean:
                continue
            if current_len + len(para_clean) > chunk_size and current_chunk:
                chunks_to_create.append(" ".join(current_chunk))
                current_chunk = [para_clean]
                current_len = len(para_clean)
            else:
                current_chunk.append(para_clean)
                current_len += len(para_clean)

        if current_chunk:
            chunks_to_create.append(" ".join(current_chunk))

        for idx, chunk_text in enumerate(chunks_to_create):
            chunk = DocumentChunk(
                document_id=doc.id,
                chunk_index=idx,
                content=chunk_text,
                metadata_={"source": title}
            )
            db.add(chunk)

        db.commit()
        db.refresh(doc)
        return doc

rag_engine = RAGEngine()
