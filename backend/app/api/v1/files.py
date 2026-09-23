import os
import io
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.api.v1.auth import get_current_user
from backend.app.models.user import User
from backend.app.models.document import Document, VISIBILITY_PRIVATE_USER
from backend.app.security.file_validator import file_validator
from backend.app.knowledge.rag import rag_engine
from backend.app.security.rate_limiter import rate_limiter

router = APIRouter(prefix="/files", tags=["Files & Documents"])


@router.post("/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),  # P0-3: auth required, no anonymous uploads
    db: Session = Depends(get_db)
):
    """
    Upload a private document. Authentication required.
    Uploaded file is PRIVATE_USER visibility — it never enters institutional RAG.
    """
    # P1-9: rate limiting per authenticated user
    rate_limiter.enforce("file_upload", request, user_id=current_user.id)

    content = await file.read()
    filename = file.filename or "uploaded_file"

    # 1. Security Validation
    is_valid, reason, meta = file_validator.validate_file(filename, content)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reason)

    clean_filename = meta["clean_filename"]
    ext = meta["extension"]

    # 2. Extract Text Content
    extracted_text = ""
    try:
        if ext in ["txt", "md", "csv"]:
            extracted_text = content.decode("utf-8", errors="ignore")
        elif ext == "pdf":
            from PyPDF2 import PdfReader
            reader = PdfReader(io.BytesIO(content))
            pages = [page.extract_text() or "" for page in reader.pages]
            extracted_text = "\n\n".join(pages)
        elif ext == "docx":
            import docx
            doc_file = docx.Document(io.BytesIO(content))
            extracted_text = "\n\n".join([p.text for p in doc_file.paragraphs if p.text.strip()])
        elif ext == "xlsx":
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
            lines = []
            for sheet in wb.worksheets:
                lines.append(f"Sheet: {sheet.title}")
                for row in sheet.iter_rows(values_only=True):
                    row_text = "\t".join([str(c) if c is not None else "" for c in row])
                    if row_text.strip():
                        lines.append(row_text)
            extracted_text = "\n".join(lines)
        elif ext in ["png", "jpg", "jpeg", "webp"]:
            from PIL import Image
            import pytesseract
            img = Image.open(io.BytesIO(content))
            try:
                extracted_text = pytesseract.image_to_string(img).strip()
            except Exception:
                extracted_text = f"Image attachment: {clean_filename}"
        else:
            extracted_text = f"Attached document: {clean_filename}"
    except Exception as e:
        extracted_text = f"Error extracting content from {clean_filename}: {str(e)}"

    # 3. Save to upload directory with opaque identifier (P0-4: no guessable paths)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    opaque_id = str(uuid.uuid4()).replace("-", "")
    saved_path = os.path.join(settings.UPLOAD_DIR, f"{opaque_id}_{meta['content_hash'][:8]}")
    with open(saved_path, "wb") as f:
        f.write(content)

    # 4. Index as PRIVATE_USER — never enters institutional RAG
    doc = rag_engine.index_document(
        db=db,
        title=clean_filename,
        text_content=extracted_text or clean_filename,
        doc_type=ext,
        source_url=saved_path,
        user_id=current_user.id,  # always bound to authenticated user
        visibility=VISIBILITY_PRIVATE_USER  # explicit private — NOT public
    )

    return {
        "file_id": doc.id,
        "filename": clean_filename,
        "extension": ext,
        "size_bytes": meta["size"],
        "content_hash": meta["content_hash"],
        "visibility": VISIBILITY_PRIVATE_USER,
        "extracted_chars": len(extracted_text),
        "message": "File validated and privately indexed. Only you can access this document."
    }


@router.get("/{file_id}/download")
def download_file(
    file_id: str,
    current_user: User = Depends(get_current_user),  # P0-4: auth required
    db: Session = Depends(get_db)
):
    """
    Download a private file. Authentication required.
    Only the owning user can download their own files.
    Admins can download ADMIN_VERIFIED documents.
    """
    doc = db.query(Document).filter(Document.id == file_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    # P0-4: Ownership enforcement
    is_owner = (doc.user_id == current_user.id)
    is_admin = current_user.role in ["ADMIN", "SUPER_ADMIN"]

    if not is_owner and not is_admin:
        # Return 404 to avoid leaking existence of file to unauthorized users
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    file_path = doc.source_url
    if not file_path or not os.path.isfile(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File data not found on server")

    return FileResponse(
        path=file_path,
        filename=doc.title,
        media_type="application/octet-stream"
    )

