import pytest
from starlette.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.core.security import verify_totp_code, get_password_hash
from backend.app.models.user import User, UserSession
from backend.app.models.document import Document, VISIBILITY_ADMIN_VERIFIED, VISIBILITY_PRIVATE_USER
from backend.app.knowledge.grounding import grounding_validator

client = TestClient(app)

def test_p0_security_mfa_no_bypass():
    """P0-2: Verify that 123456 and 000000 are rejected as MFA bypass codes."""
    dummy_secret = "JBSWY3DPEHPK3PXP"  # Standard base32 secret
    assert verify_totp_code(dummy_secret, "123456") is False
    assert verify_totp_code(dummy_secret, "000000") is False
    assert verify_totp_code(dummy_secret, "invalid") is False

def test_p0_storage_uploads_not_publicly_mounted():
    """P0-4: /storage/uploads must return 404 and not be a static mounted directory."""
    resp = client.get("/storage/uploads/secret.pdf")
    assert resp.status_code == 404

def test_p0_document_visibility_model():
    """P0-3: Document model has visibility column and respects visibility values."""
    db = SessionLocal()
    try:
        doc = Document(
            title="Institutional Syllabus",
            doc_type="pdf",
            content_hash="test_hash_123",
            visibility=VISIBILITY_ADMIN_VERIFIED
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        assert doc.visibility == VISIBILITY_ADMIN_VERIFIED

        # Cleanup
        db.delete(doc)
        db.commit()
    finally:
        db.close()

def test_p1_grounding_validator_unverified_when_no_evidence():
    """P1-3: Grounding validator must return is_grounded=False when evidence is empty."""
    res = grounding_validator.validate_answer(
        query="What is the tuition fee for MBA?",
        route="ait_institutional",
        retrieved_evidence=[],
        candidate_answer="The MBA fee is 50,000 INR."
    )
    assert res["is_grounded"] is False
    assert res["grounding_status"] == "unverified"
    assert res["confidence"] == 0.0

def test_p1_monitoring_sse_requires_admin():
    """P1-14: Anonymous requests to monitoring SSE must be rejected."""
    resp = client.get("/api/v1/admin/monitoring/live-stream")
    assert resp.status_code == 401
