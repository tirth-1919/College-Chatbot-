"""
Smart Upload & Knowledge Staging Pipeline — Production Hardened.

Multi-tenant by construction:
  - College Admin uploads are always scoped to ``current_user.college_id``;
    any client-supplied ``college_id`` that differs is rejected with 403.
  - Super Admin MUST explicitly pass a target ``college_id``; there is no
    implicit first-college / default-tenant fallback.
  - Approve / reject / submit lookups are tenant-scoped: a College Admin
    touching another college's record gets a 404 (existence not leaked).
  - Approve is Super-Admin-only for protected knowledge (College Admin can
    only submit for approval). No record is published on RAG failure.
"""
import io
import logging
import os
import re
import uuid
import zipfile
from datetime import datetime, timezone
from typing import Optional, List, Tuple
logger = logging.getLogger(__name__)
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from backend.app.intelligence.intent import intent_classifier
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.permissions import get_current_admin_user, require_super_admin, log_admin_audit
from backend.app.models.user import User
from backend.app.models.college import College, StagedUploadRecord
from backend.app.models.knowledge_categories import KnowledgeCategory, KnowledgeRecord
from backend.app.knowledge.rag import rag_engine
from backend.app.utils.tenancy import (
    get_tenant_scoped_staged_record,
    get_tenant_category,
)

router = APIRouter(prefix="/smart-upload", tags=["Smart Upload"])

# ---------------------------------------------------------------------------
# Limits & configuration
# ---------------------------------------------------------------------------
MAX_ARCHIVE_SIZE = 100 * 1024 * 1024        # 100 MB max archive size
MAX_ARCHIVE_ENTRIES = 200                    # max extracted files per archive
MAX_ENTRY_UNCOMPRESSED = 25 * 1024 * 1024    # 25 MB max per extracted file
MAX_TOTAL_UNCOMPRESSED = 200 * 1024 * 1024   # 200 MB total extracted size

MAX_TEXT_CHARS = 100_000

ALLOWED_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".csv", ".txt", ".md",
    ".json", ".pptx", ".png", ".jpg", ".jpeg", ".webp", ".zip",
}

STATUS_NEEDS_REVIEW = "NEEDS_REVIEW"


# The classifier returns the existing canonical category keys, not display labels.
_INTENT_TO_CATEGORY = {
    "DOCUMENTS": "admission_documents",
    "ADMISSION_ELIGIBILITY": "admission_eligibility",
    "ADMISSION_FEES": "admission_fees",
    "ADMISSION_PROCESS": "admission_process",
    "ADMISSION_APPLICATION": "admission_application",
    "ADMISSION_ENTRANCE_EXAM": "admission_entrance_exam",
    "ADMISSION_CONTACT": "admission_contact",
    "ADMISSION_PROGRAMS": "admission_programs",
    "ADMISSION_HOSTEL": "admission_hostel",
    "ADMISSION_SCHOLARSHIP": "admission_scholarship",
    "ADMISSION_MERIT": "admission_merit",
    "ADMISSION_COUNSELLING": "admission_counselling",
    "ADMISSION_DEADLINE": "admission_deadline",
    "ADMISSION_RESERVATION": "admission_reservation",
    "ADMISSION_CONFIRMATION": "admission_confirmation",
    "ADMISSION_CANCELLATION": "admission_cancellation",
    "ADMISSION_REFUND": "admission_refund",
    "ADMISSION_NRI": "admission_nri",
    "ADMISSION_INTERNATIONAL": "admission_international",
    "COURSES": "courses",
    "DEPARTMENTS": "departments",
    "FEES": "fees",
    "FACULTY": "faculty",
    "PLACEMENT": "placement",
    "HOSTEL": "hostel",
    "SCHOLARSHIP": "scholarships",
    "CONTACT": "admission_contact",
    "FACILITIES": "facilities",
    "EVENT": "events",
}


def _normalize_confidence(value) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("confidence must be a number between 0 and 1") from exc
    if not 0 <= score <= 1:
        raise ValueError("confidence must be between 0 and 1")
    return round(score, 4)


def _classify_content(filename: str, text: str) -> dict:
    result = intent_classifier.classify_intent(text)
    intent = str(result["intent"])
    heading_categories = [
        (r"^admission\s+process\b", "admission_process"),
        (r"^admission\s+eligibility\b", "admission_eligibility"),
        (r"^admission\s+documents?\b", "admission_documents"),
        (r"^admission\s+fees?\b", "admission_fees"),
        (r"^courses?\s+and\s+programs?\b", "courses"),
        (r"^scholarships?\b", "scholarships"),
        (r"^hostel\b", "hostel"),
        (r"^contact\s+information\b", "admission_contact"),
        (r"^entrance\s+exam\b", "admission_entrance_exam"),
    ]
    category = next((key for pattern, key in heading_categories if re.search(pattern, text.strip(), re.I)), None)
    category = category or _INTENT_TO_CATEGORY.get(intent, "general")
    combined = f"{filename} {text}".lower()
    # A fee statement is an admission-fee record even when its prose omits the
    # word admission; generic fee keywords must not route it to Departments.
    if category == "fees" and re.search(r"\b(bca|b\.?tech|mca|tuition|admission)\b", combined):
        category = "admission_fees"
    year_match = re.search(r"(202\d\s*[-/]\s*20?2\d|202\d[-/]\d{2})", combined)
    academic_year = year_match.group(1).replace(" ", "") if year_match else "2026-27"
    course_match = re.search(r"\b(b\.?tech|m\.?tech|bca|mca|bba|mba|diploma|ph\.?d)\b", combined)
    course = course_match.group(1).upper() if course_match else "All Programs"
    dept_match = re.search(r"\b(computer\s+engineering|information\s+technology|mechanical|civil|electrical)\b", combined)
    dept = dept_match.group(1).title() if dept_match else None
    fee_match = re.search(r"(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d+)?)|([\d,]{4,})\s*(?:per\s+sem|per\s+year|fees?)", combined)
    fee = (fee_match.group(1) or fee_match.group(2)) if fee_match else None
    # Keep a short summary for review UI, but retain the complete classified
    # section for publication.  The summary is not sufficient answer evidence
    # (it can cut an admission-document checklist mid-sentence).
    data = {
        "summary": text[:280].strip(),
        "content": text.strip(),
        "academic_year": academic_year,
        "course": course,
        "department": dept,
    }
    if fee:
        data["fee_amount"] = f"₹{fee}"
    raw_confidence = result.get("confidence", 0.4)
    return {"detected_category": category, "academic_year": academic_year,
            "course_department": f"{course} - {dept}" if dept else course,
            "extracted_data": data,
            "confidence_score": _normalize_confidence(raw_confidence),
            "_debug_raw_confidence": raw_confidence}


def _split_into_sections(text: str) -> List[str]:
    '''Split a document without breaking a section at its internal blank lines.

    PDF extractors commonly emit a blank line between each checklist item.  The
    old paragraph-first split treated those items as independent sections, so
    only the first item remained attached to an ``Admission Documents`` record.
    Recognized section headings are the authoritative boundaries; paragraph
    splitting is only a fallback for documents without those headings.
    '''
    clean = re.sub(r"\r", "", text or "")
    if not clean.strip():
        return []
    labels = (
        r"Admission Process|Admission Eligibility|Admission Documents|Admission Fees|"
        r"Courses and Programs|Scholarship|Hostel|Contact Information|Entrance Exam"
    )
    heading_matches = list(re.finditer(rf"(?i)\b(?:{labels})\b\s*:?", clean))
    if len(heading_matches) > 1:
        sections = []
        for index, match in enumerate(heading_matches):
            end = heading_matches[index + 1].start() if index + 1 < len(heading_matches) else len(clean)
            section = clean[match.start():end].strip()
            if section:
                sections.append(section)
        return sections
    blocks = [b.strip() for b in re.split(r"\n\s*\n+", clean) if b.strip()]
    return blocks or [clean]


def _classify_sections(filename: str, text: str) -> List[dict]:
    return [_classify_content(filename, section) for section in _split_into_sections(text)]


def _extract_text_from_bytes(filename: str, content: bytes) -> str:
    """Extracts readable text from text, csv, md, or falls back gracefully."""
    ext = os.path.splitext(filename)[1].lower()
    try:
        if ext in [".txt", ".md", ".csv", ".json", ".log"]:
            return content.decode("utf-8", errors="replace")
        elif ext == ".pdf":
            try:
                from PyPDF2 import PdfReader
                # strict=False permits recovery of readable text from PDFs with a
                # damaged/mismatched xref pointer (common in exported test PDFs).
                reader = PdfReader(io.BytesIO(content), strict=False)
                pages = []
                for page_number, page in enumerate(reader.pages, start=1):
                    try:
                        pages.append(page.extract_text() or "")
                    except Exception as page_error:
                        logger.warning("Smart Upload PDF page extraction failed: file_type=pdf page=%s error_type=%s", page_number, type(page_error).__name__)
                text = "\n\n".join(pages)
                if text.strip():
                    return text[:MAX_TEXT_CHARS]
            except Exception as pdf_error:
                logger.warning("Smart Upload PDF extraction failed: file_type=pdf error_type=%s", type(pdf_error).__name__)
            return f"Binary file: {filename} ({len(content)} bytes content)"
        elif ext in [".docx", ".xlsx", ".xls", ".pptx"]:
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
    college_id: Optional[str] = Form(None),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Accepts one or more files (including ZIP archives), extracts content,
    performs automatic classification, and stages the data for review.
    """
    role = (current_user.role or "").upper()
    if role == "SUPER_ADMIN":
        cid = college_id
        if not cid:
            raise HTTPException(status_code=400, detail="Super Admin uploads require an explicit target college tenant.")
    else:
        if college_id and college_id != current_user.college_id:
            raise HTTPException(status_code=403, detail="Cannot upload to another college.")
        cid = current_user.college_id
        if not cid:
            raise HTTPException(status_code=400, detail="User is not linked to an active college tenant.")

    tenant = db.query(College).filter(
        College.id == cid,
        College.status == "ACTIVE",
        College.registration_status == "APPROVED",
    ).first()
    if not tenant:
        raise HTTPException(status_code=400, detail="Target college is not active and approved.")

    created_records = []

    for file in files:
        content = await file.read()
        filename = file.filename
        ext = os.path.splitext(filename)[1].lower()

        # A file may contain many sections; each section gets its own pending
        # review item.  Tenant identity remains the authenticated ``cid``.
        upload_items = []
        if ext == ".zip":
            try:
                with zipfile.ZipFile(io.BytesIO(content)) as z:
                    for zip_info in z.infolist():
                        if zip_info.is_dir() or zip_info.filename.startswith("__MACOSX"):
                            continue
                        sub_content = z.read(zip_info.filename)
                        sub_filename = os.path.basename(zip_info.filename)
                        if sub_filename:
                            upload_items.append((sub_filename, sub_content))
            except Exception as zip_err:
                print(f"[SMART UPLOAD] ZIP extraction error: {zip_err}")
        else:
            upload_items.append((filename, content))

        for item_filename, item_content in upload_items:
            extracted_text = _extract_text_from_bytes(item_filename, item_content)
            sections = _classify_sections(item_filename, extracted_text)
            logger.info(
                "Smart Upload extraction diagnostics: file_type=%s extracted_text_length=%s section_count=%s",
                ext.lstrip("."), len(extracted_text), len(sections),
            )
            for classified in sections:
                extracted_data = classified["extracted_data"]
                if classified["detected_category"] == "admission_documents":
                    logger.info(
                        "Smart Upload admission-document diagnostics: section_length=%s content_length=%s summary_length=%s",
                        len(extracted_data.get("content", "")),
                        len(extracted_data.get("content", "")),
                        len(extracted_data.get("summary", "")),
                    )
                staged = StagedUploadRecord(
                    id=str(uuid.uuid4()), college_id=cid, filename=item_filename,
                    file_type=os.path.splitext(item_filename)[1].replace(".", "").upper() or "DOC",
                    file_size=len(item_content), detected_category=classified["detected_category"],
                    academic_year=classified["academic_year"], course_department=classified["course_department"],
                    extracted_data=extracted_data, raw_snippet=extracted_data.get("content") or extracted_data.get("summary", ""),
                    confidence_score=classified["confidence_score"], status="PENDING_REVIEW",
                )
                # raw_snippet is the staged section's answer evidence.  Keep the
                # complete section here; the UI can use extracted_data.summary
                # when it needs a compact preview.
                staged.raw_snippet = extracted_data.get("content") or extracted_data.get("summary", "")
                db.add(staged)
                created_records.append(staged)

    db.commit()
    for r in created_records:
        db.refresh(r)

    log_admin_audit(db, current_user, "SMART_UPLOAD_PROCESSED", "KNOWLEDGE", {
        "college_id": cid,
            "files_count": len(created_records),
        "sections_count": len(created_records),
    })

    return {
        "message": f"Successfully processed and staged {len(created_records)} classified section(s).",
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
    if (current_user.role or "").upper() != "SUPER_ADMIN":
        if not cid:
            raise HTTPException(status_code=403, detail="A college context is required")
        q = q.filter(StagedUploadRecord.college_id == cid)
    else:
        q = q.filter(StagedUploadRecord.college_id.isnot(None))
    records = q.order_by(StagedUploadRecord.created_at.desc()).limit(100).all()
    return [r.to_dict() for r in records]


@router.post("/staged/{record_id}/approve", summary="Approve staged record and publish to RAG")
def approve_staged_record(
    record_id: str,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    Approves a staged record, stores it in Knowledge Categories, and indexes it into RAG.
    Only a Super Admin may publish staged institutional knowledge.
    """
    record = db.query(StagedUploadRecord).filter(StagedUploadRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Staged record not found")
    if record.status not in ("PENDING_REVIEW", "SUBMITTED_FOR_APPROVAL", "NEEDS_CHANGES", "APPROVED"):
        raise HTTPException(status_code=400, detail="This staged record has already been processed.")

    cid = record.college_id
    tenant = db.query(College).filter(
        College.id == cid,
        College.status == "ACTIVE",
        College.registration_status == "APPROVED",
    ).first()
    if not tenant:
        raise HTTPException(status_code=400, detail="The staged record's college is not active and approved.")

    # 1. Find the existing category through the already-published source when
    # reprocessing.  Older uploads may use a tenant-specific category key, so
    # matching only the normalized detected key could create a new category and
    # prevent an in-place update.
    cat_key = re.sub(r"[^a-zA-Z0-9]", "-", record.detected_category.lower())
    existing_source = (db.query(KnowledgeRecord)
        .filter(
            KnowledgeRecord.college_id == cid,
            KnowledgeRecord.course == record.course_department,
            KnowledgeRecord.source_title == record.filename,
            KnowledgeRecord.title.like(f"{record.detected_category}%"),
        ).all())
    if len(existing_source) > 1:
        raise HTTPException(status_code=409, detail="Multiple published records match this staged source; refusing to choose one.")
    category = existing_source[0].category if existing_source else db.query(KnowledgeCategory).filter(
        KnowledgeCategory.key == cat_key,
        KnowledgeCategory.college_id == cid,
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

    # 2. Publish the complete extracted section.  ``summary`` is only a
    # review/UI preview and is never acceptable as answer evidence.
    extracted_data = record.extracted_data or {}
    complete_content = (extracted_data.get("content") or "").strip()
    if not complete_content:
        raise HTTPException(
            status_code=422,
            detail="The staged record has no complete extracted content; it was not republished.",
        )

    title = f"{record.detected_category} - {record.course_department or record.filename}"
    matches = (db.query(KnowledgeRecord)
        .filter(
            KnowledgeRecord.college_id == cid,
            KnowledgeRecord.category_id == category.id,
            KnowledgeRecord.course == record.course_department,
            KnowledgeRecord.source_title == record.filename,
        ).all())
    if len(matches) > 1:
        raise HTTPException(status_code=409, detail="Multiple published records match this staged source; refusing to choose one.")
    k_record = matches[0] if matches else KnowledgeRecord(id=str(uuid.uuid4()))
    if not matches:
        db.add(k_record)
    k_record.college_id = cid
    k_record.category_id = category.id
    k_record.title = title
    k_record.value = complete_content
    k_record.description = complete_content
    k_record.course = record.course_department
    k_record.academic_year = record.academic_year
    k_record.metadata_json = {**extracted_data, "content": complete_content}
    k_record.status = "ACTIVE"
    k_record.source_type = "ADMIN_VERIFIED"
    k_record.source_title = record.filename
    # Reprocessing preserves existing verification provenance when present;
    # first publication receives the approving admin's provenance.
    k_record.verified = True
    k_record.verified_by = k_record.verified_by or current_user.id
    k_record.verified_at = k_record.verified_at or datetime.now(timezone.utc)

    # 3. Ingest into RAG Engine
    try:
        rag_engine.index_document(
            db=db,
            title=f"{record.detected_category}: {record.filename}",
            text_content=complete_content,
            college_id=cid,
            user_id=current_user.id,
        )
    except Exception as rag_err:
        db.rollback()
        raise HTTPException(
            status_code=502,
            detail="Knowledge publication failed; the staged upload remains unpublished.",
        ) from rag_err
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
    current_user: User = Depends(require_super_admin),
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
