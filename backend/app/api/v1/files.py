import os
import io
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.api.v1.auth import get_optional_user
from backend.app.models.user import User
from backend.app.models.document import Document
from backend.app.security.file_validator import file_validator
from backend.app.knowledge.rag import rag_engine

router = APIRouter(prefix="/files", tags=["Files & Documents"])

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    content = await file.read()
    filename = file.filename or "uploaded_file"

    # 1. Security Validation
    is_valid, reason, meta = file_validator.validate_file(filename, content)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reason)

    clean_filename = meta["clean_filename"]
    ext = meta["extension"]

    # 2. Extract Text Content based on type
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
        elif ext in ["png", "jpg", "jpeg", "webp"]:
            # Image OCR
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

    # 3. Save physical file in upload quarantine directory
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    saved_path = os.path.join(settings.UPLOAD_DIR, f"{meta['content_hash'][:16]}_{clean_filename}")
    with open(saved_path, "wb") as f:
        f.write(content)

    # 4. Index in private RAG store (strictly attached to current_user.id)
    user_id = current_user.id if current_user else None
    doc = rag_engine.index_document(
        db=db,
        title=clean_filename,
        text_content=extracted_text or clean_filename,
        doc_type=ext,
        source_url=saved_path,
        user_id=user_id
    )

    return {
        "file_id": doc.id,
        "filename": clean_filename,
        "extension": ext,
        "size_bytes": meta["size"],
        "content_hash": meta["content_hash"],
        "is_private": user_id is not None,
        "extracted_chars": len(extracted_text),
        "message": "File validated, secured, and privately indexed."
    }
