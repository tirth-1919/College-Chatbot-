"Regression tests for intent-aware, tenant-scoped knowledge retrieval."""
import uuid
from backend.app.knowledge.database import KnowledgeDatabase
from backend.app.models.college import College
from backend.app.models.knowledge import AitEntity, WebsiteSnapshot

def _college(db, id_, code, name):
    college = College(id=f"{id_}-{uuid.uuid4().hex}", code=f"{code}-{uuid.uuid4().hex[:8]}", slug=f"{code.lower()}-{uuid.uuid4().hex}", name=name, status="ACTIVE")
    db.add(college)
    db.flush()
    return college

def _entity(db, college, name, category, details, source="https://example.test"):
    entity = AitEntity(
        college_id=college.id, name=name, category=category, details=details,
        source_url=source, content_hash=name,
        is_verified=True,
    )
    db.add(entity)
    db.flush()
    return entity

def test_values_and_clubs_do_not_return_unrelated_records(db):
    ait = _college(db, "retrieval-ait", "RVAIT", "AIT Retrieval")
    _entity(db, ait, "Placement — Company", "placement", {"company": "Example"})
    _entity(db, ait, "Student Grievance Redressal Committee", "committee", {"members": []})
    db.commit()

    assert KnowledgeDatabase.query_entities(db, "core values or educational philosophy", college_id=ait.id) == []
    assert KnowledgeDatabase.query_entities(db, "student clubs or extracurricular activities", college_id=ait.id) == []


def test_general_programming_guidance_does_not_match_placement_snapshot(db):
    ait = _college(db, "retrieval-programming", "RVPROG", "AIT Programming Retrieval")
    db.add(WebsiteSnapshot(
        college_id=ait.id,
        url=f"https://ait-programming.test/placement/{uuid.uuid4().hex}",
        title="Placement — Company / Placement — Drives",
        text_content=("Placement companies and software development recruiters visit the campus. "
                      "Students receive placement training and interview preparation."),
        content_hash="placement-guidance",
        status_code=200,
    ))
    db.commit()

    results = KnowledgeDatabase.query_website_snapshots(
        db,
        "What programming concepts should a beginner practice before building a small web application?",
        college_id=ait.id,
    )
    assert results == []


def test_rto_query_matches_existing_facilities_snapshot(db):
    rcti = _college(db, "retrieval-rcti", "RVRCTI", "R.C. Technical Institute")
    db.add(WebsiteSnapshot(
        college_id=rcti.id, url=f"https://rcti-retrieval.test/about/facilities/{uuid.uuid4().hex}", title="Facilities",
        text_content=("RTO License Facilitation Center assists with learning license and "
                      "driving license applications through local transport authorities."),
        content_hash="rto", status_code=200,
    ))
    db.commit()
    results = KnowledgeDatabase.query_website_snapshots(db, "RTO License Facilitation Center", college_id=rcti.id)
    assert results
    assert "license" in results[0]["content"].lower()


def test_database_fee_query_is_tenant_scoped(db):
    ait = _college(db, "retrieval-fee-ait", "RVFAIT", "AIT Fee Retrieval")
    rcti = _college(db, "retrieval-fee-rcti", "RVFRCTI", "RCTI Fee Retrieval")
    _entity(db, ait, "BCA Fee 2026-27", "fees", {"course": "BCA", "academic_year": "2026-27", "fee": "AIT fee"})
    _entity(db, rcti, "BCA Fee 2026-27", "fees", {"course": "BCA", "academic_year": "2026-27", "fee": "RCTI fee"})
    db.commit()

    ait_results = KnowledgeDatabase.query_entities(db, "BCA fee records academic year course categories stored in database", college_id=ait.id)
    rcti_results = KnowledgeDatabase.query_entities(db, "BCA fee records academic year course categories stored in database", college_id=rcti.id)
    assert any("AIT fee" in str(item["details"]) for item in ait_results)
    assert all("RCTI fee" not in str(item["details"]) for item in ait_results)
    assert any("RCTI fee" in str(item["details"]) for item in rcti_results)
    assert all("AIT fee" not in str(item["details"]) for item in rcti_results)


def test_values_query_accepts_only_formal_values_content(db):
    ait = _college(db, "retrieval-values", "RVVAL", "AIT Values Retrieval")
    _entity(db, ait, "AIT Home", "home", {"text": "Discover Your Path to Excellence. Learning in Motion."})
    _entity(db, ait, "AIT Vision and Mission", "institutional", {"text": "Our institutional mission is to provide accessible engineering education; our core values are integrity and innovation."})
    db.commit()

    results = KnowledgeDatabase.query_entities(db, "core values educational philosophy", college_id=ait.id)
    assert any("Vision and Mission" in item["name"] for item in results)
    assert all("Home" not in item["name"] for item in results)


def test_navigation_only_values_and_clubs_are_not_evidence(db):
    ait = _college(db, "retrieval-navigation", "RVNAV", "AIT Navigation Retrieval")
    db.add_all([
        WebsiteSnapshot(
            college_id=ait.id, url=f"https://ait-navigation.test/{uuid.uuid4().hex}", title="Governing Council",
            text_content="HOME > ACADEMICS > Academic Calendar > Co-Curricular Activities STUDENT CELL > Grievance Cell",
            content_hash="navigation", status_code=200,
        ),
        WebsiteSnapshot(
            college_id=ait.id, url=f"https://ait-navigation.test/about/mission/{uuid.uuid4().hex}", title="Mission",
            text_content="Our institutional mission and core values guide teaching, research, integrity, and service.",
            content_hash="mission", status_code=200,
        ),
    ])
    db.commit()

    clubs = KnowledgeDatabase.query_website_snapshots(db, "student clubs extracurricular activities", college_id=ait.id)
    values = KnowledgeDatabase.query_website_snapshots(db, "core values educational philosophy", college_id=ait.id)
    assert clubs == []
    assert values == [] or all("Governing Council" not in item["title"] for item in values)


def test_rto_entity_content_matches_without_exact_title(db):
    rcti = _college(db, "retrieval-rto-entity", "RVRTO", "RCTI RTO Retrieval")
    _entity(db, rcti, "Campus Facilities", "facility", {
        "description": "The center assists students and nearby residents with RTO learning license and driving license applications through local transport authorities."
    })
    db.commit()

    results = KnowledgeDatabase.query_entities(db, "What services are provided through the RTO License Facilitation Center?", college_id=rcti.id)
    assert len(results) == 1
    assert results[0]["name"] == "Campus Facilities"
    assert "license" in str(results[0]["details"]).lower()


def test_rto_query_does_not_return_other_tenant_data(db):
    rcti = _college(db, "retrieval-rto-rcti", "RVRTR", "RCTI RTO Tenant")
    ait = _college(db, "retrieval-rto-ait", "RVTAT", "AIT RTO Tenant")
    _entity(db, ait, "Campus Facilities", "facility", {"description": "RTO learning license information for AIT only."})
    _entity(db, rcti, "Campus Facilities", "facility", {"description": "RTO driving license facilitation for RCTI only."})
    db.commit()

    results = KnowledgeDatabase.query_entities(db, "RTO license facilitation center", college_id=rcti.id)
    assert results
    assert all("AIT only" not in str(item["details"]) for item in results)
    assert any("RCTI only" in str(item["details"]) for item in results)


def test_missing_database_topic_has_no_unrelated_fallback(db):
    rcti = _college(db, "retrieval-missing-db", "RVMDB", "RCTI Missing Database")
    _entity(db, rcti, "Placement Company", "placement", {"company": "Unrelated"})
    db.commit()

    results = KnowledgeDatabase.query_entities(db, "BCA fee records stored in the knowledge database", college_id=rcti.id)
    assert results == []


def test_live_database_fee_metadata_preserves_tenant_and_category_variants(db):
    rcti = _college(db, "retrieval-live-rcti", "RVRLIVE", "RCTI Live Retrieval")
    entity = _entity(db, rcti, "BCA Semester 5 Fee", "fee", {
        "course": "BCA", "field": "Semester Fee", "academic_year": "2026-27"
    })
    entity.academic_year = "2026-27"
    db.commit()

    results = KnowledgeDatabase.query_entities(
        db,
        "What academic-year information is stored for the BCA fee records in the knowledge database?",
        college_id=rcti.id,
    )
    assert results
    assert results[0]["id"]
    assert results[0]["college_id"] == rcti.id
    assert results[0]["category"] == "fee"
    assert results[0]["is_verified"] is True
    assert results[0]["academic_year"] == "2026-27"


def test_active_verified_knowledge_record_is_retrieved_with_tenant_filter(db):
    from backend.app.models.knowledge_categories import KnowledgeCategory, KnowledgeRecord
    ait = _college(db, "retrieval-modern-ait", "RVMODAIT", "AIT Modern Retrieval")
    rcti = _college(db, "retrieval-modern-rcti", "RVMODRCTI", "RCTI Modern Retrieval")
    ait_category = KnowledgeCategory(
        id=f"category-{uuid.uuid4().hex}", college_id=ait.id,
        name="Fees", key="fees", status="ACTIVE",
    )
    rcti_category = KnowledgeCategory(
        id=f"category-{uuid.uuid4().hex}", college_id=rcti.id,
        name="Fees", key="fees", status="ACTIVE",
    )
    db.add_all([ait_category, rcti_category])
    db.flush()
    db.add_all([
        KnowledgeRecord(
            id=f"record-{uuid.uuid4().hex}", college_id=ait.id,
            category_id=ait_category.id, title="Data Science Program Fee",
            course="Data Science", academic_year="2026-27", value="INR 72,000 per year",
            source_type="ADMIN_VERIFIED", verified=True, status="ACTIVE",
        ),
        KnowledgeRecord(
            id=f"record-{uuid.uuid4().hex}", college_id=rcti.id,
            category_id=rcti_category.id, title="BCA Semester 5 Fee",
            course="BCA", academic_year="2026-27", value="INR 48,000",
            source_type="ADMIN_VERIFIED", verified=True, status="ACTIVE",
        ),
    ])
    db.commit()

    ait_results = KnowledgeDatabase.query_entities(
        db, "Data Science fee for the current academic year", college_id=ait.id,
    )
    rcti_results = KnowledgeDatabase.query_entities(
        db, "BCA Semester 5 fee for AY 2026-27", college_id=rcti.id,
    )
    assert any("72,000" in str(item["details"]) for item in ait_results)
    assert any("48,000" in str(item["details"]) for item in rcti_results)
    assert all(item["college_id"] == ait.id for item in ait_results)
    assert all(item["college_id"] == rcti.id for item in rcti_results)


# Admission-document relevance regressions

def test_bca_document_question_excludes_fee_only_record(db):
    ait = _college(db, "retrieval-doc-fee", "RVDF", "Document Fee Retrieval")
    _entity(db, ait, "BCA Semester Fee", "fees", {"course": "BCA", "field": "Semester Fee", "value": "₹32,000"})
    db.commit()

    results = KnowledgeDatabase.query_entities(
        db, "What documents are required for admission to the BCA program?", college_id=ait.id,
    )
    assert results == []
    assert all("32,000" not in str(item.get("details")) for item in results)


def test_genuine_admission_document_record_is_preferred(db):
    ait = _college(db, "retrieval-doc-match", "RVDM", "Document Match Retrieval")
    _entity(db, ait, "BCA Semester Fee", "fees", {"course": "BCA", "field": "Semester Fee", "value": "₹32,000"})
    _entity(db, ait, "BCA Admission Documents", "admission", {
        "course": "BCA",
        "required_documents": "Admission application documents and certificates required for BCA admission; see the document checklist.",
    })
    db.commit()

    results = KnowledgeDatabase.query_entities(
        db, "What documents are required for admission to the BCA program?", college_id=ait.id,
    )
    assert len(results) == 1
    assert results[0]["name"] == "BCA Admission Documents"
    assert "checklist" in str(results[0]["details"]).lower()


def test_fee_record_remains_retrievable_for_fee_question(db):
    ait = _college(db, "retrieval-doc-fee-question", "RVDFQ", "Fee Question Retrieval")
    _entity(db, ait, "BCA Semester Fee", "fees", {"course": "BCA", "field": "Semester Fee", "value": "₹32,000"})
    db.commit()

    results = KnowledgeDatabase.query_entities(db, "What is the BCA semester fee?", college_id=ait.id)
    assert any("32,000" in str(item["details"]) for item in results)


def test_bba_fee_does_not_return_bca_fee_record(db):
    ait = _college(db, "retrieval-bba-fee", "RVBBF", "BBA Fee Retrieval")
    _entity(db, ait, "BCA Fee 2026-27", "fees", {
        "course": "BCA", "academic_year": "2026-27", "fee": "₹32,000",
    })
    db.commit()

    results = KnowledgeDatabase.query_entities(db, "bba fee", college_id=ait.id)

    assert all("32,000" not in str(item["details"]) for item in results)
    assert all("BCA" not in str(item["details"]) for item in results)


def test_btech_fee_does_not_return_bca_fee_record(db):
    ait = _college(db, "retrieval-btech-fee", "RVBT", "B.Tech Fee Retrieval")
    _entity(db, ait, "BCA Fee 2026-27", "fees", {
        "course": "BCA", "academic_year": "2026-27", "fee": "₹32,000",
    })
    db.commit()

    results = KnowledgeDatabase.query_entities(db, "btech fee", college_id=ait.id)

    assert all("32,000" not in str(item["details"]) for item in results)
    assert all("BCA" not in str(item["details"]) for item in results)


def test_btech_fee_for_academic_year_rejects_generic_and_other_program_records(db):
    ait = _college(db, "retrieval-btech-year-fee", "RVBTY", "B.Tech Year Fee Retrieval")
    _entity(db, ait, "All Programs Admission 2026-27", "fees", {
        "course": "All Programs", "academic_year": "2026-27",
        "content": "Entrance Exam; Contact Information; Hostel; Scholarship; Admission Eligibility; PDF content",
    })
    _entity(db, ait, "BCA Fee 2026-27", "fees", {
        "course": "BCA", "academic_year": "2026-27", "fee": "₹32,000",
    })
    _entity(db, ait, "BBA Fee 2026-27", "fees", {
        "course": "BBA", "academic_year": "2026-27", "fee": "₹28,000",
    })
    _entity(db, ait, "B.Tech Tuition Fee 2026-27", "fees", {
        "course": "B.Tech", "academic_year": "2026-27", "field": "Tuition Fee",
        "fee": "₹85,000", "source": "admin verified database",
    })
    db.commit()

    results = KnowledgeDatabase.query_entities(
        db, "What is the B.Tech fee for 2026-27?", college_id=ait.id,
    )

    assert results
    assert results[0]["name"] == "B.Tech Tuition Fee 2026-27"
    assert "85,000" in str(results[0]["details"])
    names = [item["name"] for item in results]
    assert "All Programs Admission 2026-27" not in names
    assert "BCA Fee 2026-27" not in names
    assert "BBA Fee 2026-27" not in names
    assert results[0]["authority"] == "Official College Website"
    assert results[0]["is_verified"] is True

def test_document_question_has_no_unsupported_document_fallback(db):
    ait = _college(db, "retrieval-doc-none", "RVDN", "No Document Evidence Retrieval")
    _entity(db, ait, "BCA Admission Information", "admission", {"course": "BCA", "value": "Admission process information"})
    db.commit()

    results = KnowledgeDatabase.query_entities(
        db, "Which certificates and documents are needed for admission?", college_id=ait.id,
    )
    assert results == []


def test_admission_document_retrieval_is_tenant_isolated(db):
    ait = _college(db, "retrieval-doc-tenant-a", "RVDTA", "Document Tenant A")
    other = _college(db, "retrieval-doc-tenant-b", "RVDTB", "Document Tenant B")
    _entity(db, ait, "BCA Admission Documents", "admission", {"required_documents": "Tenant A checklist"})
    _entity(db, other, "BCA Admission Documents", "admission", {"required_documents": "Tenant B checklist"})
    db.commit()

    results = KnowledgeDatabase.query_entities(db, "BCA admission document checklist", college_id=ait.id)
    assert results
    assert all(item["college_id"] == ait.id for item in results)
    assert all("Tenant B" not in str(item["details"]) for item in results)


def test_admission_document_record_preserves_provenance(db):
    ait = _college(db, "retrieval-doc-provenance", "RVDP", "Document Provenance Retrieval")
    entity = _entity(
        db, ait, "BCA Admission Documents", "admission",
        {"required_documents": "Official admin document checklist"},
        source="https://example.test/admissions/documents",
    )
    entity.source_type = "ADMIN_VERIFIED"
    entity.authority = "College Admin"
    db.commit()

    results = KnowledgeDatabase.query_entities(db, "BCA admission document checklist", college_id=ait.id)
    assert results[0]["source_url"] == "https://example.test/admissions/documents"
    assert results[0]["authority"] == "College Admin"
    assert results[0]["is_verified"] is True


def test_query_understanding_captures_hierarchy_and_aliases():
    from backend.app.intelligence.entities import entity_extractor
    parsed = entity_extractor.extract_query_understanding(
        "What is the b tech cse tuition for 2026-27?", college_id="ait", intent="FEES"
    )
    assert parsed.college_id == "ait"
    assert parsed.intent == "FEES"
    assert parsed.topic == "FEES"
    assert parsed.program == "B.Tech Computer Science & Engineering"
    assert parsed.subtopic == "TUITION_FEE"
    assert parsed.academic_year == "2026-27"


def test_query_understanding_identifies_required_admission_documents():
    from backend.app.intelligence.entities import entity_extractor
    parsed = entity_extractor.extract_query_understanding(
        "Which papers are needed for admission?", college_id="test-college", intent="DOCUMENTS"
    )
    assert parsed.college_id == "test-college"
    assert parsed.topic == "ADMISSION"
    assert parsed.subtopic == "REQUIRED_DOCUMENTS"



def test_transport_topic_guard_rejects_generic_records_but_preserves_topic_and_broad_retrieval(db):
    ait = _college(db, "retrieval-transport-entities", "RVTRE", "AIT Transport Entity Retrieval")
    _entity(db, ait, "AIT Contact", "institutional", {
        "address": "Ahmedabad", "phone": "1234567890", "duration": "2 Years",
    })
    _entity(db, ait, "BCA Fee", "fees", {"course": "BCA", "fee": "₹32,000"})
    _entity(db, ait, "B.Tech Fee", "fees", {"course": "B.Tech", "fee": "₹78,000"})
    _entity(db, ait, "BBA Fee", "fees", {"course": "BBA", "fee": "₹45,000"})
    _entity(db, ait, "Placement — Company", "placement", {"company": "Example recruiter"})
    _entity(db, ait, "Campus Bus Transport", "facility", {
        "description": "College bus transportation has routes, pickup and drop-off points for commuting students.",
    })
    db.commit()

    transport = KnowledgeDatabase.query_entities(
        db, "What transportation or bus facility information is available?", college_id=ait.id,
    )
    names = [item["name"] for item in transport]
    assert names == ["Campus Bus Transport"]
    assert "Placement — Company" not in names
    assert all(term not in str(item["details"]) for item in transport for term in ["BCA", "B.Tech", "BBA"])

    broad = KnowledgeDatabase.query_entities(db, "Tell me about AIT", college_id=ait.id)
    assert any(item["name"] == "AIT Contact" for item in broad)


def test_transport_query_rejects_unrelated_placement_snapshot(db):
    ait = _college(db, "retrieval-transport", "RVTRANS", "AIT Transport Retrieval")
    db.add_all([
        WebsiteSnapshot(
            college_id=ait.id,
            url=f"https://ait-transport.test/placement/company/{uuid.uuid4().hex}",
            title="Placement — Company",
            text_content=(
                "Ahmedabad Institute of Technology Engineering College organised a walkathon "
                "and hackathon. Companies and placement opportunities are listed here."
            ),
            content_hash="transport-placement",
            status_code=200,
        ),
        WebsiteSnapshot(
            college_id=ait.id,
            url=f"https://ait-transport.test/campus/transport/{uuid.uuid4().hex}",
            title="Campus Transport",
            text_content=(
                "The college provides bus transport facilities with routes and pickup points "
                "for students commuting to campus."
            ),
            content_hash="transport-bus",
            status_code=200,
        ),
    ])
    db.commit()

    results = KnowledgeDatabase.query_website_snapshots(
        db,
        "What transportation or bus facility information is available?",
        college_id=ait.id,
    )

    assert results
    assert all("placement/company" not in result["url"] for result in results)
    assert any("transport" in result["url"] for result in results)


def test_placement_query_still_accepts_placement_snapshot(db):
    ait = _college(db, "retrieval-placement", "RVPLACE", "AIT Placement Retrieval")
    db.add(WebsiteSnapshot(
        college_id=ait.id,
        url=f"https://ait-placement.test/placement/company/{uuid.uuid4().hex}",
        title="Placement — Company",
        text_content=(
            "Placement companies and recruiters visit the campus for hiring drives. "
            "Students receive placement support, interview preparation, and campus recruitment guidance."
        ),
        content_hash="placement-company",
        status_code=200,
    ))
    db.commit()

    results = KnowledgeDatabase.query_website_snapshots(
        db, "Which placement companies recruit students?", college_id=ait.id,
    )

    assert results
    assert "/placement/company/" in results[0]["url"]


def test_website_and_entity_retrieval_use_actual_college_id_not_ait_like_text(db):
    canonical_ait = _college(db, "canonical-ait-boundary", "AIT", "Ahmedabad Institute of Technology")
    synthetic = _college(db, "synthetic-ait-boundary", "RETRIEVAL_AIT-001", "Synthetic Retrieval Tenant")
    rcti = _college(db, "canonical-rcti-boundary", "RCTI", "R.C. Technical Institute")
    _entity(db, canonical_ait, "BCA Fee", "fees", {"fee": "canonical AIT fee"})
    _entity(db, synthetic, "BCA Fee", "fees", {"fee": "synthetic AIT-like fee"})
    _entity(db, rcti, "BCA Fee", "fees", {"fee": "canonical RCTI fee"})
    db.add_all([
        WebsiteSnapshot(
            college_id=canonical_ait.id, url="https://synthetic-ait.example/fee",
            title="BCA Fees", text_content="BCA fee ₹32,000", content_hash="canonical-website", status_code=200,
        ),
        WebsiteSnapshot(
            college_id=synthetic.id, url="https://canonical-ait.example/fee",
            title="BCA Fees", text_content="BCA fee ₹999", content_hash="synthetic-website", status_code=200,
        ),
        WebsiteSnapshot(
            college_id=rcti.id, url="https://rcti.example/fee",
            title="BCA Fees", text_content="BCA fee RCTI", content_hash="rcti-website", status_code=200,
        ),
    ])
    db.commit()

    ait_entities = KnowledgeDatabase.query_entities(db, "BCA fee", college_id=canonical_ait.id)
    ait_pages = KnowledgeDatabase.query_website_snapshots(db, "BCA fee", college_id=canonical_ait.id)
    rcti_entities = KnowledgeDatabase.query_entities(db, "BCA fee", college_id=rcti.id)
    rcti_pages = KnowledgeDatabase.query_website_snapshots(db, "BCA fee", college_id=rcti.id)

    assert all(row["college_id"] == canonical_ait.id for row in ait_entities)
    assert all(row["college_id"] == canonical_ait.id for row in ait_pages)
    assert all("synthetic" not in str(row["details"]).lower() for row in ait_entities)
    assert all("999" not in str(row["content"]) for row in ait_pages)
    assert all(row["college_id"] == rcti.id for row in rcti_entities)
    assert all(row["college_id"] == rcti.id for row in rcti_pages)
    assert all("AIT" not in str(row["details"]) for row in rcti_entities)
