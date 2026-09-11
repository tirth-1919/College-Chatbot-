import os
import hashlib
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.core.permissions import get_current_admin_user, require_permission, log_admin_audit, PERM_DOCUMENTS_MANAGE
from backend.app.models.document import Document, DocumentChunk
from backend.app.models.user import User
from backend.app.knowledge.rag import rag_engine

router = APIRouter(prefix="/documents", tags=["Admin Document Management"])

@router.get("")
def list_authoritative_documents(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    docs = (
        db.query(Document)
        .filter(Document.user_id == None)  # Official institutional documents
        .order_by(Document.created_at.desc())
        .all()
    )
    return [
        {
            "id": d.id,
            "title": d.title,
            "doc_type": d.doc_type,
            "source_url": d.source_url or "Administrative Upload",
            "content_hash": d.content_hash,
            "chunk_count": len(d.chunks),
            "created_at": d.created_at.isoformat() if d.created_at else None
        }
        for d in docs
    ]

@router.post("/upload")
async def upload_authoritative_document(
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission(PERM_DOCUMENTS_MANAGE)),
    db: Session = Depends(get_db)
):
    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File exceeds 25MB maximum size")

    ext = file.filename.split(".")[-1].lower() if "." in file.filename else "txt"
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported format: {ext}")

    content_hash = hashlib.sha256(content).hexdigest()
    save_path = os.path.join(settings.UPLOAD_DIR, f"admin_{content_hash[:12]}_{file.filename}")
    with open(save_path, "wb") as f:
        f.write(content)

    # Ingest directly into institutional RAG (user_id=None)
    doc = rag_engine.ingest_document(
        db=db,
        file_path=save_path,
        doc_type=ext,
        title=f"AIT Official: {file.filename}",
        user_id=None,
        source_url=f"internal://storage/{file.filename}"
    )

    log_admin_audit(db, current_user, "UPLOAD_OFFICIAL_DOCUMENT", "DOCUMENT", {
        "id": doc.id,
        "filename": file.filename,
        "chunks": len(doc.chunks)
    })

    return {
        "message": "Institutional document ingested successfully",
        "document_id": doc.id,
        "chunks_indexed": len(doc.chunks)
    }

@router.get("/{document_id}/chunks")
def get_document_chunks(
    document_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == None).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index.asc())
        .all()
    )
    return {
        "document_id": doc.id,
        "title": doc.title,
        "chunks": [
            {
                "id": c.id,
                "chunk_index": c.chunk_index,
                "content": c.content,
                "metadata": c.metadata_,
                "has_embedding": bool(c.embedding_json)
            }
            for c in chunks
        ]
    }

@router.delete("/{document_id}")
def delete_document(
    document_id: str,
    current_user: User = Depends(require_permission(PERM_DOCUMENTS_MANAGE)),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == None).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    db.delete(doc)
    db.commit()
    log_admin_audit(db, current_user, "DELETE_OFFICIAL_DOCUMENT", "DOCUMENT", {"id": document_id})
    return {"message": "Institutional document removed from RAG index"}
