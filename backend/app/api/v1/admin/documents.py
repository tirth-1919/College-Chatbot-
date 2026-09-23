import os
import hashlib
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.core.permissions import get_current_admin_user, require_permission, log_admin_audit, PERM_DOCUMENTS_MANAGE
from backend.app.models.document import Document, DocumentChunk, VISIBILITY_ADMIN_VERIFIED, VISIBILITY_PUBLIC_INSTITUTIONAL
from backend.app.models.user import User
from backend.app.knowledge.rag import rag_engine
from backend.app.security.file_validator import file_validator

router = APIRouter(prefix="/documents", tags=["Admin Document Management"])

@router.get("")
def list_authoritative_documents(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    q = (db.query(Document)
        .filter(Document.visibility.in_([VISIBILITY_ADMIN_VERIFIED, VISIBILITY_PUBLIC_INSTITUTIONAL]))
    )
    # Phase 9 tenant isolation
    if current_user.role != "SUPER_ADMIN" and current_user.college_id:
        q = q.filter(Document.college_id == current_user.college_id)
    docs = q.order_by(Document.created_at.desc()).all()
    return [
        {
            "id": d.id,
            "title": d.title,
            "doc_type": d.doc_type,
            "source_url": d.source_url or "Administrative Upload",
            "content_hash": d.content_hash,
            "chunk_count": len(d.chunks),
            "visibility": d.visibility,
            "college_id": d.college_id,
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
    filename = file.filename or "uploaded_file"
    is_valid, reason, meta = file_validator.validate_file(filename, content)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reason)

    clean_filename = meta["clean_filename"]
    ext = meta["extension"]

    content_hash = hashlib.sha256(content).hexdigest()
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    save_path = os.path.join(settings.UPLOAD_DIR, f"admin_{uuid.uuid4().hex}_{content_hash[:12]}")
    with open(save_path, "wb") as f:
        f.write(content)

    # P1-5 FIX: ingest_document() now exists in rag_engine and accepts visibility.
    # user_id is set to the uploading admin (not None) for accountability.
    # Visibility ADMIN_VERIFIED means it enters institutional RAG for all users.
    doc = rag_engine.ingest_document(
        db=db,
        file_path=save_path,
        doc_type=ext,
        title=f"Official: {clean_filename}",
        user_id=current_user.id,  # admin accountability
        source_url=f"internal://storage/{file.filename}",
        visibility=VISIBILITY_ADMIN_VERIFIED,
        college_id=current_user.college_id  # Phase 9: tenant stamp
    )

    log_admin_audit(db, current_user, "UPLOAD_OFFICIAL_DOCUMENT", "DOCUMENT", {
        "id": doc.id,
        "filename": clean_filename,
        "chunks": len(doc.chunks)
    })

    return {
        "message": "Institutional document ingested and verified successfully",
        "document_id": doc.id,
        "chunks_indexed": len(doc.chunks),
        "visibility": VISIBILITY_ADMIN_VERIFIED
    }

@router.get("/{document_id}/chunks")
def get_document_chunks(
    document_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    # P0-3 FIX: filter by visibility not user_id == None
    q = db.query(Document).filter(
        Document.id == document_id,
        Document.visibility.in_([VISIBILITY_ADMIN_VERIFIED, VISIBILITY_PUBLIC_INSTITUTIONAL])
    )
    if current_user.role != "SUPER_ADMIN" and current_user.college_id:
        q = q.filter(Document.college_id == current_user.college_id)
    doc = q.first()
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
                "content_preview": c.content[:200] if c.content else "",
                "chunk_size": len(c.content) if c.content else 0,
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
    # P0-3 FIX: filter by visibility not user_id == None
    q = db.query(Document).filter(
        Document.id == document_id,
        Document.visibility.in_([VISIBILITY_ADMIN_VERIFIED, VISIBILITY_PUBLIC_INSTITUTIONAL])
    )
    if current_user.role != "SUPER_ADMIN" and current_user.college_id:
        q = q.filter(Document.college_id == current_user.college_id)
    doc = q.first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    db.delete(doc)
    db.commit()
    log_admin_audit(db, current_user, "DELETE_OFFICIAL_DOCUMENT", "DOCUMENT", {"id": document_id})
    return {"message": "Institutional document removed from RAG index"}
