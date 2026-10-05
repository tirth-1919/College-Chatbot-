"Endpoint-level Smart Upload regression coverage."""
import io
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.app.core.database import Base, get_db
from backend.app.core.security import create_access_token
from backend.app.main import app
from backend.app.models.college import College, StagedUploadRecord
from backend.app.models.knowledge_categories import KnowledgeRecord
from backend.app.models.user import User
PDF_WITH_SECTIONS = (b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>endobj\n4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n5 0 obj<</Length 520>>stream\nBT\n/F1 12 Tf\n72 720 Td\n(Admission Process: complete the application.) Tj\n0 -30 Td\n(Admission Eligibility: passed 12th standard.) Tj\n0 -30 Td\n(Admission Documents: 12th marksheet; School leaving certificate; Government identity proof; Passport-size photographs; Applicable category certificates.) Tj\n0 -30 Td\n(Admission Fees: BCA fee INR 32000.) Tj\n0 -30 Td\n(Courses and Programs: BCA is a three-year program.) Tj\n0 -30 Td\n(Scholarship: eligible students may apply.) Tj\n0 -30 Td\n(Hostel: accommodation subject to availability.) Tj\n0 -30 Td\n(Contact Information: contact the Admission Office.) Tj\n0 -30 Td\n(Entrance Exam: verify GUJCET requirement.) Tj\nET\nendstream endobj\nxref\n0 6\n0000 65535 f \n0009 00000 n \n0000058 00000 n \n0000115 00000 n \n0000275 00000 n \n0000345 00000 n \ntrailer<</Size 6/Root 1 0 R>>\nstartxref\n825\n%%EOF\n")

@pytest.fixture
def endpoint_context():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    now = datetime.now(timezone.utc)
    college = College(
        id="endpoint-ait", name="AIT", code="AIT", slug="endpoint-ait",
        status="ACTIVE", registration_status="APPROVED", created_at=now, updated_at=now,
    )
    user = User(
        id="endpoint-admin", email="endpoint-admin@test.local", full_name="AIT Admin",
        role="COLLEGE_ADMIN", college_id=college.id, permissions=["knowledge.read"],
        is_active=True, hashed_password="x",
    )
    db.add_all([college, user])
    db.commit()
    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app) as client:
            yield client, db, user, college
    finally:
        app.dependency_overrides.pop(get_db, None)
        db.close()
        engine.dispose()


def test_real_upload_endpoint_extracts_sections_and_stages_tenant_records(endpoint_context):
    client, db, user, college = endpoint_context
    token = create_access_token({"sub": user.id})
    response = client.post(
        "/api/v1/admin/smart-upload/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"files": ("AIT_SMART_UPLOAD_NEW_TEST_20261002.pdf", io.BytesIO(PDF_WITH_SECTIONS), "application/pdf")},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["count"] >= 2
    categories = {record["detected_category"] for record in payload["records"]}
    assert {"admission_process", "admission_eligibility", "admission_documents", "admission_fees"} <= categories
    assert all(0 < record["confidence_score"] <= 1 for record in payload["records"])
    assert all(record["status"] == "PENDING_REVIEW" for record in payload["records"])
    assert all(record["college_id"] == college.id for record in payload["records"])

    staged = db.query(StagedUploadRecord).filter_by(filename="AIT_SMART_UPLOAD_NEW_TEST_20261002.pdf").all()
    assert len(staged) == payload["count"]
    assert all(record.college_id == college.id for record in staged)
    assert all(record.confidence_score <= 1 for record in staged)


def test_smart_upload_complete_content_survives_super_admin_approval(endpoint_context, monkeypatch):
    client, db, user, college = endpoint_context
    token = create_access_token({"sub": user.id})
    response = client.post(
        "/api/v1/admin/smart-upload/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"files": ("AIT_ADMISSION_DOCS_2026.pdf", io.BytesIO(PDF_WITH_SECTIONS), "application/pdf")},
    )
    assert response.status_code == 200, response.text
    staged = db.query(StagedUploadRecord).filter_by(
        filename="AIT_ADMISSION_DOCS_2026.pdf", detected_category="admission_documents"
    ).one()
    complete = staged.extracted_data["content"]
    expected_items = (
        "12th marksheet", "School leaving certificate", "Government identity proof",
        "Passport-size photographs", "Applicable category certificates",
    )
    assert staged.status == "PENDING_REVIEW"
    assert staged.raw_snippet == complete
    assert all(item in complete for item in expected_items)
    assert complete != "Admission Documents: submit the marksheet."

    user.role = "SUPER_ADMIN"
    db.commit()
    monkeypatch.setattr(
        "backend.app.api.v1.admin.smart_upload.rag_engine.index_document",
        lambda **kwargs: None,
    )
    approval = client.post(
        f"/api/v1/admin/smart-upload/staged/{staged.id}/approve",
        headers={"Authorization": f"Bearer {create_access_token({'sub': user.id})}"},
    )
    assert approval.status_code == 200, approval.text
    approved = db.query(KnowledgeRecord).filter_by(source_title="AIT_ADMISSION_DOCS_2026.pdf").one()
    assert approved.college_id == college.id
    assert approved.status == "ACTIVE"
    assert approved.verified is True
    assert approved.source_type == "ADMIN_VERIFIED"
    assert approved.source_title == "AIT_ADMISSION_DOCS_2026.pdf"
    assert approved.value == complete
    assert approved.metadata_json["content"] == complete
    assert all(item in approved.value for item in expected_items)
    assert approved.value != "Admission Documents: submit the marksheet."


def test_reprocessing_approved_staged_record_updates_existing_record(endpoint_context, monkeypatch):
    client, db, user, college = endpoint_context
    from backend.app.models.knowledge_categories import KnowledgeCategory
    category = KnowledgeCategory(
        id="endpoint-admission-documents", college_id=college.id,
        name="admission_documents", key="admission-documents-4812", status="ACTIVE",
    )
    staged_content = (
        "Admission Documents: 12th marksheet; School leaving certificate; "
        "Government identity proof; Passport-size photographs; "
        "Applicable category certificates."
    )
    staged = StagedUploadRecord(
        id="endpoint-approved-staged", college_id=college.id,
        filename="AIT_SMART_UPLOAD_NEW_TEST_20261002.pdf", file_type="PDF",
        detected_category="admission_documents", course_department="All Programs",
        academic_year="2026-27", extracted_data={"summary": "old preview", "content": staged_content},
        raw_snippet="old preview", status="APPROVED", reviewed_by="original-reviewer",
        reviewed_at=datetime.now(timezone.utc),
    )
    existing = KnowledgeRecord(
        id="endpoint-existing-knowledge", college_id=college.id, category_id=category.id,
        title="admission_documents - All Programs", course="All Programs",
        value="Admission Documents: submit the marksheet.",
        description="Auto-extracted from AIT_SMART_UPLOAD_NEW_TEST_20261002.pdf",
        metadata_json={"summary": "old preview"}, status="ACTIVE", verified=True,
        verified_by="original-reviewer", verified_at=datetime.now(timezone.utc),
        source_type="ADMIN_VERIFIED", source_title=staged.filename,
    )
    db.add_all([category, staged, existing])
    user.role = "SUPER_ADMIN"
    db.commit()
    monkeypatch.setattr("backend.app.api.v1.admin.smart_upload.rag_engine.index_document", lambda **kwargs: None)

    response = client.post(
        f"/api/v1/admin/smart-upload/staged/{staged.id}/approve",
        headers={"Authorization": f"Bearer {create_access_token({'sub': user.id})}"},
    )
    assert response.status_code == 200, response.text
    db.expire_all()
    published = db.query(KnowledgeRecord).filter_by(
        college_id=college.id, source_title=staged.filename,
        category_id=category.id, course="All Programs", status="ACTIVE",
    ).all()
    assert len(published) == 1
    assert published[0].id == existing.id
    assert published[0].value == staged_content
    assert published[0].description == staged_content
    assert published[0].metadata_json["content"] == staged_content
    assert published[0].source_type == "ADMIN_VERIFIED"
    assert published[0].verified is True
    assert published[0].verified_by == "original-reviewer"
    assert published[0].college_id == college.id
    assert published[0].source_title == staged.filename
