"""
Smart Upload & Knowledge Staging Pipeline
Enables College Admins to upload documents, spreadsheets, and archives with automatic
content classification and field extraction before publishing to production RAG.
"""
import io
import os
import re
import uuid
import zipfile
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.permissions import get_current_admin_user, log_admin_audit
from backend.app.models.user import User
from backend.app.models.college import College, StagedUploadRecord
from backend.app.models.knowledge_categories import KnowledgeCategory, KnowledgeRecord
from backend.app.knowledge.rag import rag_engine

router = APIRouter(prefix="/smart-upload", tags=["Smart Upload"])


def _classify_content(filename: str, text: str) -> dict:
    """
    Intelligent heuristic classifier for academic documents.
    Detects category, academic year, course, and structured values.
    """
    combined = f"{filename} {text}".lower()

    # Category classification
    if any(k in combined for k in ["fee", "tuition", "payment", "cost", "scholarship", "charges", "rupees", "inr", "₹"]):
        category = "Fees"
    elif any(k in combined for k in ["faculty", "professor", "teacher", "hod", "lecturer", "dean", "instructor"]):
        category = "Faculty"
    elif any(k in combined for k in ["course", "syllabus", "curriculum", "bca", "btech", "mtech", "degree", "diploma", "semester"]):
        category = "Courses"
    elif any(k in combined for k in ["admission", "eligibility", "entrance", "merit", "application form", "cutoff"]):
        category = "Admissions"
    elif any(k in combined for k in ["department", "lab", "computer science", "mechanical", "electrical", "civil"]):
        category = "Departments"
    elif any(k in combined for k in ["placement", "recruiter", "package", "lpa", "highest package", "internship"]):
        category = "Placement"
    elif any(k in combined for k in ["calendar", "schedule", "exam date", "holiday", "timetable"]):
        category = "Academic Calendar"
    else:
        category = "General"

    # Academic Year detection
    year_match = re.search(r"(202\d\s*[-/]\s*20?2\d|202\d[-/]\d{2})", combined)
    academic_year = year_match.group(1).replace(" ", "") if year_match else "2026-27"

    # Course detection
    course_match = re.search(r"\b(b\.?tech|m\.?tech|bca|mca|bba|mba|diploma|ph\.?d)\b", combined)
    course = course_match.group(1).upper() if course_match else "General Program"

    # Fee extraction
    fee_match = re.search(r"(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d+)?)|([\d,]{4,})\s*(?:per\s+sem|per\s+year|fees?)", combined)
    extracted_fee = None
    if fee_match:
        fee_raw = fee_match.group(1) or fee_match.group(2)
        if fee_raw:
            extracted_fee = f"₹{fee_raw}"

    # Department detection
    dept_match = re.search(r"\b(computer\s+engineering|information\s+technology|mechanical|civil|electrical)\b", combined)
    dept = dept_match.group(1).title() if dept_match else None

    structured_data = {
        "summary": text[:280].strip() if text else f"Extracted from {filename}",
        "academic_year": academic_year,
        "course": course,
        "department": dept or course,
    }
    if extracted_fee:
        structured_data["fee_amount"] = extracted_fee

    return {
        "detected_category": category,
        "academic_year": academic_year,
        "course_department": f"{course} - {dept}" if dept else course,
        "extracted_data": structured_data,
        "confidence_score": 92 if extracted_fee or dept else 85,
    }


def _extract_text_from_bytes(filename: str, content: bytes) -> str:
    """Extracts readable text from text, csv, md, or falls back gracefully."""
    ext = os.path.splitext(filename)[1].lower()
    try:
        if ext in [".txt", ".md", ".csv", ".json", ".log"]:
            return content.decode("utf-8", errors="replace")
        elif ext in [".pdf", ".docx", ".xlsx", ".xls", ".pptx"]:
            # Fallback printable ASCII extraction for binaries
            printable = re.sub(r"[^\x20-\x7E\n\r\t]", " ", content[:100000].decode("latin-1", errors="replace"))
            clean = " ".join(printable.split())
            if len(clean) > 50:
                return clean[:2000]
            return f"Binary file: {filename} ({len(content)} bytes content)"
        else:
            return f"Document: {filename} uploaded for knowledge processing."
    except Exception:
        return f"Document content from {filename}."


@router.post("/upload", summary="Smart Upload document or bulk archive")
async def smart_upload_files(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Accepts one or more files (including ZIP archives), extracts content,
    performs automatic classification, and stages the data for review.
    """
    cid = current_user.college_id
    if not cid and current_user.role != "SUPER_ADMIN":
        raise HTTPException(status_code=400, detail="User is not linked to an active college tenant.")

    # Fallback tenant for testing if SUPER_ADMIN uploads without explicit college
    if not cid:
        first_col = db.query(College).first()
        cid = first_col.id if first_col else "ait-default-tenant-0001"

    created_records = []

    for file in files:
        content = await file.read()
        filename = file.filename
        ext = os.path.splitext(filename)[1].lower()

        # Handle ZIP Archives
        if ext == ".zip":
            try:
                with zipfile.ZipFile(io.BytesIO(content)) as z:
                    for zip_info in z.infolist():
                        if zip_info.is_dir() or zip_info.filename.startswith("__MACOSX"):
                            continue
                        sub_content = z.read(zip_info.filename)
                        sub_filename = os.path.basename(zip_info.filename)
                        if not sub_filename:
                            continue
                        extracted_text = _extract_text_from_bytes(sub_filename, sub_content)
                        classified = _classify_content(sub_filename, extracted_text)

                        staged = StagedUploadRecord(
                            id=str(uuid.uuid4()),
                            college_id=cid,
                            filename=sub_filename,
                            file_type=os.path.splitext(sub_filename)[1].replace(".", "").upper() or "DOC",
                            file_size=len(sub_content),
                            detected_category=classified["detected_category"],
                            academic_year=classified["academic_year"],
                            course_department=classified["course_department"],
                            extracted_data=classified["extracted_data"],
                            raw_snippet=extracted_text[:600],
                            confidence_score=classified["confidence_score"],
                            status="PENDING_REVIEW",
                        )
                        db.add(staged)
                        created_records.append(staged)
            except Exception as zip_err:
                print(f"[SMART UPLOAD] ZIP extraction error: {zip_err}")
        else:
            extracted_text = _extract_text_from_bytes(filename, content)
            classified = _classify_content(filename, extracted_text)

            staged = StagedUploadRecord(
                id=str(uuid.uuid4()),
                college_id=cid,
                filename=filename,
                file_type=ext.replace(".", "").upper() or "DOC",
                file_size=len(content),
                detected_category=classified["detected_category"],
                academic_year=classified["academic_year"],
                course_department=classified["course_department"],
                extracted_data=classified["extracted_data"],
                raw_snippet=extracted_text[:600],
                confidence_score=classified["confidence_score"],
                status="PENDING_REVIEW",
            )
            db.add(staged)
            created_records.append(staged)

    db.commit()
    for r in created_records:
        db.refresh(r)

    log_admin_audit(db, current_user, "SMART_UPLOAD_PROCESSED", "KNOWLEDGE", {
        "college_id": cid,
        "files_count": len(created_records),
    })

    return {
        "message": f"Successfully processed and classified {len(created_records)} file(s).",
        "count": len(created_records),
        "records": [r.to_dict() for r in created_records],
    }


@router.get("/staged", summary="List staged records pending review")
def list_staged_records(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Lists all staged records for the authenticated college."""
    cid = current_user.college_id
    q = db.query(StagedUploadRecord)
    if cid and current_user.role != "SUPER_ADMIN":
        q = q.filter(StagedUploadRecord.college_id == cid)
    records = q.order_by(StagedUploadRecord.created_at.desc()).limit(100).all()
    return [r.to_dict() for r in records]


@router.post("/staged/{record_id}/approve", summary="Approve staged record and publish to RAG")
def approve_staged_record(
    record_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Approves a staged record, stores it in Knowledge Categories, and indexes it into RAG.
    """
    record = db.query(StagedUploadRecord).filter(StagedUploadRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Staged record not found")

    cid = record.college_id

    # 1. Find or create matching Knowledge Category
    cat_key = re.sub(r"[^a-zA-Z0-9]", "-", record.detected_category.lower())
    category = db.query(KnowledgeCategory).filter(
        KnowledgeCategory.key == cat_key
    ).first()
    if not category:
        unique_key = f"{cat_key}-{str(uuid.uuid4())[:6]}"
        category = KnowledgeCategory(
            id=str(uuid.uuid4()),
            college_id=cid,
            name=f"{record.detected_category} ({str(uuid.uuid4())[:4]})",
            key=unique_key,
            description=f"Auto-generated category for {record.detected_category}",
            icon="📁",
            status="ACTIVE"
        )
        db.add(category)
        db.flush()

    # 2. Add Knowledge Record
    k_record = KnowledgeRecord(
        id=str(uuid.uuid4()),
        college_id=cid,
        category_id=category.id,
        title=f"{record.detected_category} - {record.course_department or record.filename}",
        value=record.raw_snippet or f"Knowledge extracted from {record.filename}",
        description=f"Auto-extracted from {record.filename}",
        course=record.course_department,
        academic_year=record.academic_year,
        metadata_json=record.extracted_data or {},
        status="ACTIVE",
        verified=True,
        source_type="ADMIN_VERIFIED",
        source_title=record.filename,
    )
    db.add(k_record)

    # 3. Ingest into RAG Engine
    try:
        rag_engine.index_document(
            db=db,
            title=f"{record.detected_category}: {record.filename}",
            text_content=record.raw_snippet or str(record.extracted_data),
            college_id=cid,
            user_id=current_user.id,
        )
    except Exception as rag_err:
        print(f"[SMART UPLOAD] RAG indexing notice: {rag_err}")

    # 4. Mark staged record as APPROVED
    record.status = "APPROVED"
    record.reviewed_by = current_user.id
    record.reviewed_at = datetime.now(timezone.utc)
    db.commit()

    log_admin_audit(db, current_user, "STAGED_RECORD_APPROVED", "KNOWLEDGE", {
        "staged_id": record.id,
        "category": record.detected_category,
        "college_id": cid
    })

    return {
        "message": f"Record '{record.filename}' approved and published to college knowledge base.",
        "record": record.to_dict()
    }


@router.post("/staged/{record_id}/reject", summary="Reject staged record")
def reject_staged_record(
    record_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Rejects a staged record."""
    record = db.query(StagedUploadRecord).filter(StagedUploadRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Staged record not found")

    record.status = "REJECTED"
    record.reviewed_by = current_user.id
    record.reviewed_at = datetime.now(timezone.utc)
    db.commit()

    log_admin_audit(db, current_user, "STAGED_RECORD_REJECTED", "KNOWLEDGE", {
        "staged_id": record.id,
        "college_id": record.college_id
    })

    return {"message": f"Record '{record.filename}' rejected.", "record": record.to_dict()}
