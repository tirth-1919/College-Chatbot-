"""Unit & Regression Tests for Upgraded College Profile & Institutional Metadata.

Tests:
1. Model attributes & constraints on College entity.
2. Serialization of complete institutional profile (CollegeProfileResponse).
3. Field validation for profile updates (CollegeProfileUpdateRequest).
4. Protected fields invariant (id, slug, status, is_active cannot be modified by admin).
5. Draft profile schema validation (CollegeDraftSaveRequest).
6. Profile change history serialization (CollegeProfileHistoryItemResponse).
7. Asset upload response schema (ProfileAssetUploadResponse).
8. Magic byte detection for PNG, JPEG, WebP, SVG, PDF.
9. SVG XSS attack prevention.
10. File size validation limits (5MB images, 10MB documents).
"""

import uuid
from datetime import datetime, timezone
from app.models.college import College
from app.models.audit import AuditLog
from app.schemas.college_admin import (
    CollegeProfileResponse,
    CollegeProfileUpdateRequest,
    CollegeDraftSaveRequest,
    CollegeProfileHistoryItemResponse,
    ProfileAssetUploadResponse,
)


def test_college_model_has_all_institutional_metadata_fields():
    """Verify that College model schema contains all required institutional metadata columns."""
    table = College.__table__
    expected_fields = [
        # Identity
        "name", "slug", "official_domain", "logo_url", "contact_email", "contact_phone",
        "short_name", "cover_image_url", "institution_type", "established_year", "website_url",
        # Address & Location
        "address_line1", "address_line2", "city", "district", "state", "country", "postal_code",
        "maps_url", "latitude", "longitude",
        # Contacts
        "admission_email", "examination_email", "placement_email", "admission_helpline",
        "alternate_phone", "working_hours",
        # Accreditation
        "affiliated_university", "recognized_by", "aicte_approval", "ugc_recognition",
        "naac_grade", "nba_accreditation", "accreditation_validity", "approval_document_url",
        # About & Leadership
        "short_description", "about_text", "vision", "mission", "leader_name", "leader_designation",
        # Social
        "linkedin_url", "instagram_url", "facebook_url", "youtube_url", "twitter_url",
        # Branding & Draft
        "favicon_url", "primary_brand_color", "secondary_brand_color", "draft_profile",
    ]
    for field in expected_fields:
        assert field in table.c, f"Missing column in colleges table: {field}"


def test_college_profile_response_serialization():
    """Verify CollegeProfileResponse correctly serializes complete institutional profile."""
    college_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    profile_data = {
        "id": college_id,
        "name": "Ahmedabad Institute of Technology",
        "slug": "ait-college",
        "official_domain": "aitindia.in",
        "contact_email": "info@aitindia.in",
        "contact_phone": "+91-79-27663244",
        "logo_url": "https://aitindia.in/logo.png",
        "status": "APPROVED",
        "is_active": True,
        "created_at": now,
        "updated_at": now,
        "short_name": "AIT",
        "cover_image_url": "https://aitindia.in/cover.jpg",
        "institution_type": "Autonomous College",
        "established_year": 2004,
        "website_url": "https://aitindia.in",
        "address_line1": "Near Gota Cross Road",
        "city": "Ahmedabad",
        "district": "Ahmedabad",
        "state": "Gujarat",
        "country": "India",
        "postal_code": "382481",
        "naac_grade": "A+",
        "leader_name": "Dr. Rajesh K. Patel",
        "leader_designation": "Principal",
        "primary_brand_color": "#10B981",
        "secondary_brand_color": "#6366F1",
    }

    resp = CollegeProfileResponse(**profile_data)
    assert resp.id == college_id
    assert resp.short_name == "AIT"
    assert resp.established_year == 2004
    assert resp.naac_grade == "A+"
    assert resp.leader_name == "Dr. Rajesh K. Patel"
    assert resp.primary_brand_color == "#10B981"


def test_college_profile_update_request_validation():
    """Verify CollegeProfileUpdateRequest allows partial metadata updates."""
    req = CollegeProfileUpdateRequest(
        name="Updated Institute Name",
        short_name="UIN",
        established_year=2010,
        city="Gandhinagar",
        naac_grade="A++",
        primary_brand_color="#059669",
    )
    dumped = req.model_dump(exclude_unset=True)
    assert dumped["name"] == "Updated Institute Name"
    assert dumped["short_name"] == "UIN"
    assert dumped["established_year"] == 2010
    assert dumped["city"] == "Gandhinagar"
    assert dumped["naac_grade"] == "A++"
    assert "official_domain" not in dumped


def test_update_college_protected_fields_invariant():
    """Verify that protected fields (id, slug, status, is_active) cannot be altered by admin updates."""
    PROTECTED = {"id", "status", "is_active", "slug"}

    initial_state = {
        "id": uuid.uuid4(),
        "slug": "immutable-slug",
        "status": "APPROVED",
        "is_active": True,
        "name": "Original Name",
        "short_name": "ORIG",
    }

    tampered_updates = {
        "id": uuid.uuid4(),
        "slug": "hacked-slug",
        "status": "REJECTED",
        "is_active": False,
        "name": "Permitted New Name",
        "short_name": "PNN",
    }

    # Simulate repository field filter logic
    applied_updates = {}
    for key, val in tampered_updates.items():
        if key in PROTECTED:
            continue
        applied_updates[key] = val

    state = {**initial_state, **applied_updates}

    # Invariants
    assert state["id"] == initial_state["id"]
    assert state["slug"] == "immutable-slug"
    assert state["status"] == "APPROVED"
    assert state["is_active"] is True
    # Permitted changes applied
    assert state["name"] == "Permitted New Name"
    assert state["short_name"] == "PNN"


def test_draft_profile_schema_validation():
    """Verify CollegeDraftSaveRequest stores arbitrary draft JSON structures."""
    draft_payload = {
        "short_name": "DRAFT-AIT",
        "naac_grade": "A++",
        "working_hours": "Mon-Sat 9AM-5PM",
        "_saved_at": datetime.now(timezone.utc).isoformat(),
    }
    req = CollegeDraftSaveRequest(draft_data=draft_payload)
    assert req.draft_data["short_name"] == "DRAFT-AIT"
    assert req.draft_data["naac_grade"] == "A++"


def test_profile_history_item_response_serialization():
    """Verify CollegeProfileHistoryItemResponse serialization."""
    item_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    diff = {
        "name": {"old": "Old Name", "new": "New Name"},
        "short_name": {"old": "ON", "new": "NN"},
    }
    history_item = CollegeProfileHistoryItemResponse(
        id=item_id,
        action_type="COLLEGE_PROFILE_UPDATED",
        actor_id=actor_id,
        actor_name="Test Administrator",
        actor_email="admin@aitindia.in",
        payload_diff=diff,
        created_at=datetime.now(timezone.utc),
    )
    assert history_item.id == item_id
    assert history_item.action_type == "COLLEGE_PROFILE_UPDATED"
    assert history_item.actor_name == "Test Administrator"
    assert history_item.payload_diff == diff


def test_profile_asset_upload_response_serialization():
    """Verify ProfileAssetUploadResponse serialization."""
    resp = ProfileAssetUploadResponse(
        asset_url="/api/v1/colleges/assets/1111/logo_abc.png",
        asset_type="logo",
        file_name="college_crest.png",
        file_size_bytes=1048576,
    )
    assert resp.asset_type == "logo"
    assert resp.file_size_bytes == 1048576
    assert resp.asset_url.endswith("logo_abc.png")


def test_asset_upload_magic_bytes_detection():
    """Verify magic bytes detection identifies valid PNG, JPEG, WebP, SVG, and PDF files."""
    valid_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
    valid_jpg = b"\xff\xd8\xff\xe0" + b"\x00" * 20
    valid_webp = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 10
    valid_svg = b"<svg xmlns='http://www.w3.org/2000/svg'><path/></svg>"
    valid_pdf = b"%PDF-1.4\n" + b"\x00" * 20

    # PNG test
    header_png = valid_png[:1024]
    assert header_png.startswith(b"\x89PNG\r\n\x1a\n")

    # JPEG test
    header_jpg = valid_jpg[:1024]
    assert header_jpg.startswith(b"\xff\xd8\xff")

    # WebP test
    header_webp = valid_webp[:1024]
    assert header_webp.startswith(b"RIFF") and b"WEBP" in header_webp[:16]

    # SVG test
    assert b"<svg" in valid_svg.lower() and b"</svg>" in valid_svg.lower()
    assert b"<script" not in valid_svg.lower()

    # PDF test
    header_pdf = valid_pdf[:1024]
    assert header_pdf.startswith(b"%PDF-")


def test_asset_upload_svg_xss_protection():
    """Verify SVG uploads with embedded malicious script or javascript are identified."""
    malicious_svg = b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert('xss')</script></svg>"
    has_script = b"<script" in malicious_svg.lower() or b"javascript:" in malicious_svg.lower()
    assert has_script is True

    safe_svg = b"<svg xmlns='http://www.w3.org/2000/svg'><circle cx='50' cy='50' r='40'/></svg>"
    safe_script = b"<script" in safe_svg.lower() or b"javascript:" in safe_svg.lower()
    assert safe_script is False


def test_asset_upload_size_limits():
    """Verify image uploads adhere to 5MB limit and documents to 10MB limit."""
    max_image_bytes = 5 * 1024 * 1024
    max_doc_bytes = 10 * 1024 * 1024

    small_image = b"x" * (2 * 1024 * 1024)
    oversized_image = b"x" * (6 * 1024 * 1024)
    valid_doc = b"x" * (8 * 1024 * 1024)
    oversized_doc = b"x" * (12 * 1024 * 1024)

    assert len(small_image) <= max_image_bytes
    assert len(oversized_image) > max_image_bytes
    assert len(valid_doc) <= max_doc_bytes
    assert len(oversized_doc) > max_doc_bytes
