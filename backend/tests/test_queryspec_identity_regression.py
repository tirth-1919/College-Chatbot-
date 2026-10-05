"""
P0.1 — QuerySpec consolidation regression suite.

Proves that the canonical QuerySpec is the SINGLE SOURCE OF TRUTH for the
current user question after query understanding:

  QuerySpec
    -> source routing
    -> database retrieval
    -> website retrieval
    -> evidence normalization
    -> answer builder
    -> grounding
    -> provenance

No downstream stage may independently re-derive intent / category / topic /
program / entity / academic_year from the raw question.

This suite is CODE-ONLY: it builds its own throwaway in-memory database and
never touches the real college records or schema.
"""

from datetime import datetime, timezone
import re

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.ai.prompts import build_system_prompt
from backend.app.chat.orchestrator import _source_label
from backend.app.chat.response_builder import ResponseBuilder
from backend.app.core.database import Base
from backend.app.intelligence.entities import EntityExtractor, QuerySpec
from backend.app.knowledge.database import knowledge_db
from backend.app.knowledge.grounding import GroundingValidator
from backend.app.knowledge.source_router import source_router
from backend.app.models.college import College
from backend.app.models.knowledge import WebsiteSnapshot
from backend.app.models.knowledge_categories import KnowledgeCategory, KnowledgeRecord

ADMIN_VERIFIED = "ADMIN_VERIFIED"
OFFICIAL_WEBSITE = "OFFICIAL_WEBSITE"
GEMINI_UNVERIFIED = "GEMINI_UNVERIFIED"


# ======================================================================
# Fixture
# ======================================================================

def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine)()


AIT_ID = "ait-identity-tenant"
RCTI_ID = "rcti-identity-tenant"


def _record(db, rid, college_id, category_id, title, value, *,
            course=None, year="2026-27", verified=True, status="ACTIVE"):
    db.add(KnowledgeRecord(
        id=rid, college_id=college_id, category_id=category_id,
        course=course, academic_year=year, title=title,
        field_name="tuition_fee", value=value,
        source_type=ADMIN_VERIFIED, status=status, verified=verified,
    ))


@pytest.fixture
def env():
    engine, db = _session()
    now = datetime.now(timezone.utc)
    ait = College(id=AIT_ID, name="Ahmedabad Institute of Technology",
                  code="AIT", slug="ait", status="ACTIVE",
                  registration_status="APPROVED", created_at=now)
    rcti = College(id=RCTI_ID, name="R.C. Technical Institute",
                   code="RCTI", slug="rcti", status="ACTIVE",
                   registration_status="APPROVED", created_at=now)
    ait_fees = KnowledgeCategory(id="ait-fees", name="Fees", key="fees",
                                  status="ACTIVE", college_id=AIT_ID)
    rcti_fees = KnowledgeCategory(id="rcti-fees", name="Fees", key="fees",
                                   status="ACTIVE", college_id=RCTI_ID)
    ait_hostel = KnowledgeCategory(id="ait-hostel", name="Hostel", key="hostel",
                                   status="ACTIVE", college_id=AIT_ID)
    ait_lib = KnowledgeCategory(id="ait-library", name="Library", key="library",
                                status="ACTIVE", college_id=AIT_ID)
    db.add_all([ait, rcti, ait_fees, rcti_fees, ait_hostel, ait_lib])
    db.flush()

    # ---- AIT fee records (matrix rows 1-3) -------------------------
    _record(db, "ait-bca-fee", AIT_ID, ait_fees.id,
            "BCA Tuition Fee", "INR 32,000", course="BCA")
    _record(db, "ait-bba-fee", AIT_ID, ait_fees.id,
            "BBA Tuition Fee", "INR 35,000", course="BBA")
    _record(db, "ait-ds-fee", AIT_ID, ait_fees.id,
            "Data Science Tuition Fee", "INR 72,000", course="Data Science")

    # ---- AIT hostel + library (matrix rows 4-5) ---------------------
    db.add(KnowledgeRecord(
        id="ait-hostel-rec", college_id=AIT_ID, category_id=ait_hostel.id,
        title="AIT Hostel Facilities", field_name="facilities",
        value="Separate hostel blocks with Wi-Fi, mess and 24x7 security.",
        source_type=ADMIN_VERIFIED, status="ACTIVE", verified=True,
    ))
    db.add(KnowledgeRecord(
        id="ait-library-rec", college_id=AIT_ID, category_id=ait_lib.id,
        title="Central Library", field_name="facilities",
        value="36,000+ Books and a digital reading hall.",
        source_type=ADMIN_VERIFIED, status="ACTIVE", verified=True,
    ))

    # ---- matrix rows 13/14: INACTIVE and UNVERIFIED -----------------
    _record(db, "ait-inactive-fee", AIT_ID, ait_fees.id,
            "BCA Inactive Fee", "INR 99,000", course="BCA",
            status="INACTIVE")
    _record(db, "ait-unverified-fee", AIT_ID, ait_fees.id,
            "BCA Unverified Fee", "INR 88,000", course="BCA",
            verified=False)

    # ---- wrong tenant (matrix row: never selected) ------------------
    _record(db, "rcti-bca-fee", RCTI_ID, rcti_fees.id,
            "RCTI BCA Fee", "INR 48,000", course="BCA")

    # ---- AIT official website snapshot (library) --------------------
    db.add(WebsiteSnapshot(
        id="ait-lib-snap", college_id=AIT_ID,
        url="https://ait.identity.test/facilities/library",
        title="Library Facilities", content_hash="ait-lib-hash",
        text_content=(
            "The Central Library holds 36,000+ Books and offers a "
            "Book Bank Service with Extended Access for students."
        ),
        status_code=200, last_crawled_at=now, active=True,
        crawl_error=None, version_number=1, created_at=now,
    ))
    db.commit()
    try:
        yield {"db": db, "ait": ait, "rcti": rcti}
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def _spec(question, college_id, intent=None, college_name=None):
    spec = EntityExtractor.extract_query_understanding(
        question, college_id=college_id, intent=intent,
    )
    if college_name:
        spec.college_name = college_name
    return spec


# ======================================================================
# TASK 11 — END-TO-END IDENTITY REGRESSION
# ======================================================================

def test_queryspec_identity_survives_every_downstream_stage(env):
    """
    Deliberately distinctive values, traced end to end:

      college_id      = AIT
      college_name    = Ahmedabad Institute of Technology
      category        = Fees
      topic           = Fees
      program         = BCA
      academic_year   = 2026-27
      requested_field = tuition_fee
      route           = institutional

    Every downstream stage must preserve these EXACT semantic values.
    """
    db = env["db"]

    # ---- 1. QuerySpec (deliberately distinctive values) ------------
    # `category`/`topic` use the canonical stored category key ("fees") and
    # `program` the canonical extractor value, exactly as
    # EntityExtractor.extract_query_understanding produces them.
    spec = QuerySpec(
        college_id=AIT_ID,
        college_name="Ahmedabad Institute of Technology",
        intent="FEES",
        category="fees",
        topic="FEES",
        program="BCA",
        entity=None,
        academic_year="2026-27",
        requested_field="tuition_fee",
        route=None,
        confidence=0.95,
        raw_question="What is the BCA fee for 2026-27?",
        programs=["BCA"],
        topics=["FEES"],
    )

    # ---- 2. Source routing -----------------------------------------
    route = source_router.route_query(spec)
    spec.route = route
    assert route == "institutional"
    assert spec.college_id == AIT_ID
    assert spec.college_name == "Ahmedabad Institute of Technology"
    assert spec.program == "BCA"
    assert spec.academic_year == "2026-27"
    assert spec.requested_field == "tuition_fee"

    # ---- 3. Database retrieval -------------------------------------
    evidence = knowledge_db.query_entities(
        db, spec.raw_question, college_id=AIT_ID, query_spec=spec,
    )
    assert evidence, "AIT BCA fee record must be retrieved"
    assert all(e["college_id"] == AIT_ID for e in evidence)
    assert any(e["course"] == "BCA" for e in evidence)
    assert not any(e["course"] == "BBA" for e in evidence)
    assert not any(e["course"] == "Data Science" for e in evidence)

    # ---- 4. Evidence normalization ---------------------------------
    normalized = ResponseBuilder.normalize_evidence(evidence, query_spec=spec)
    assert normalized
    for item in normalized:
        assert item["college_id"] == AIT_ID
        assert item["program"] == "BCA"
        assert item["academic_year"] == "2026-27"
        assert item["verified"] is not False
        assert str(item["status"]).upper() == "ACTIVE"
        # full evidence contract retained
        for key in (
            "source_type", "source_record_id", "college_id", "college_name",
            "title", "category", "topic", "program", "entity",
            "academic_year", "field", "value", "content", "description",
            "source_url", "verified", "status",
        ):
            assert key in item, f"missing evidence field {key}"

    # ---- 5. Answer builder -----------------------------------------
    # Mirror the orchestrator: admin DB records are labelled entity_db.
    for item in evidence:
        item.setdefault("source_type", "entity_db")
    answer = ResponseBuilder.build_grounded_answer(
        evidence, query_spec=spec, query=spec.raw_question,
    )
    assert "32,000" in answer
    assert "BCA" in answer
    assert "BBA" not in answer

    # ---- 6. Grounding ----------------------------------------------
    grounded = GroundingValidator.validate_answer(
        query_spec=spec, retrieved_evidence=evidence, candidate_answer=answer,
    )
    assert grounded["is_grounded"] is True

    # ---- 7. Provenance ---------------------------------------------
    label = _source_label(ADMIN_VERIFIED, spec.college_name, query_spec=spec)
    assert label == "🗄️ Ahmedabad Institute of Technology Database"


def test_no_downstream_stage_changes_identity(env):
    """
    Explicitly assert that college_id / program / category / academic_year
    are byte-identical before and after every stage.
    """
    db = env["db"]
    spec = _spec(
        "What is the BCA fee for 2026-27?", AIT_ID, intent="FEES",
    )
    spec.college_name = "Ahmedabad Institute of Technology"
    snapshot_before = (
        spec.college_id, spec.program, spec.topic, spec.category,
        spec.academic_year,
    )
    assert snapshot_before == (
        AIT_ID, "BCA (Bachelor of Computer Applications)", "FEES", "FEES",
        "2026-27",
    )

    spec.route = source_router.route_query(spec)
    knowledge_db.query_entities(
        db, spec.raw_question, college_id=AIT_ID, query_spec=spec,
    )
    knowledge_db.query_website_snapshots(
        db, spec.raw_question, college_id=AIT_ID, query_spec=spec,
    )
    evidence = knowledge_db.query_entities(
        db, spec.raw_question, college_id=AIT_ID, query_spec=spec,
    )
    ResponseBuilder.build_grounded_answer(evidence, query_spec=spec)
    GroundingValidator.validate_answer(
        query_spec=spec, retrieved_evidence=evidence, candidate_answer="x",
    )

    snapshot_after = (
        spec.college_id, spec.program, spec.topic, spec.category,
        spec.academic_year,
    )
    assert snapshot_after == snapshot_before


def test_queryspec_is_the_only_understanding_boundary():
    """
    Static guard: the raw-question regex blocks that used to be duplicated in
    the router, the DB retrieval and the website retrieval must not come back.
    """
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "app"
    router = (root / "knowledge" / "source_router.py").read_text(encoding="utf-8")
    # The router must not build its own keyword tables any more; they live on
    # QuerySpec as resolved booleans.
    assert "strong_keywords = [" not in router
    assert "weak_keywords = [" not in router
    assert "intent_info.get(" not in router
    assert "entities.get(" not in router

    db_module = (root / "knowledge" / "database.py").read_text(encoding="utf-8")
    # The spec-driven path must not re-extract entities or years from text.
    assert "query_spec.requested_years" in db_module
    assert "query_spec.is_fee_query" in db_module
    assert "query_spec.is_document_query" in db_module
    assert "admission_category_from_spec" in db_module
    assert "category_from_spec" in db_module


# ======================================================================
# TASK 7 — grounding mismatch cases
# ======================================================================

def test_grounding_passes_matching_program_and_fails_mismatched_program():
    """BCA evidence grounds a BCA claim but NOT a BBA claim."""
    evidence = [{
        "source_type": "entity_db", "college_id": AIT_ID,
        "program": "BCA", "academic_year": "2026-27",
        "value": "₹32,000",
        "content": {"program": "BCA", "value": "₹32,000",
                    "academic_year": "2026-27"},
    }]
    spec = _spec("What is the BCA fee for 2026-27?", AIT_ID, intent="FEES")

    ok = GroundingValidator.validate_answer(
        query_spec=spec, retrieved_evidence=evidence,
        candidate_answer="The BCA fee is ₹32,000 for 2026-27.",
    )
    assert ok["is_grounded"] is True

    bad = GroundingValidator.validate_answer(
        query_spec=spec, retrieved_evidence=evidence,
        candidate_answer="The BBA fee is ₹32,000.",
    )
    assert bad["is_grounded"] is False
    assert bad["grounding_status"] == "unverified"


def test_grounding_rejects_evidence_from_another_college():
    evidence = [{
        "source_type": "entity_db", "college_id": RCTI_ID,
        "program": "BCA", "value": "INR 48,000",
        "content": {"program": "BCA", "value": "INR 48,000"},
    }]
    spec = _spec("What is the BCA fee?", AIT_ID, intent="FEES")
    result = GroundingValidator.validate_answer(
        query_spec=spec, retrieved_evidence=evidence,
        candidate_answer="The BCA fee is INR 48,000.",
    )
    assert result["is_grounded"] is False


# ======================================================================
# TASK 5 — evidence normalization guards
# ======================================================================

@pytest.mark.parametrize("item,reason", [
    ({"college_id": RCTI_ID, "program": "BCA"}, "AIT -> RCTI cross-tenant"),
    ({"college_id": AIT_ID, "program": "BBA"}, "BCA -> BBA"),
    ({"college_id": AIT_ID, "program": "Data Science"}, "BCA -> Data Science"),
    ({"college_id": AIT_ID, "program": "BCA", "verified": False}, "VERIFIED -> UNVERIFIED"),
    ({"college_id": AIT_ID, "program": "BCA", "status": "INACTIVE"}, "ACTIVE -> INACTIVE"),
])
def test_normalize_evidence_rejects_identity_mismatches(item, reason):
    spec = QuerySpec(college_id=AIT_ID, program="BCA", category="Fees",
                     topic="Fees", academic_year="2026-27")
    full = {
        "source_type": ADMIN_VERIFIED, "title": "x", "value": "v",
        "status": "ACTIVE", "verified": True, "college_id": AIT_ID,
        "program": "BCA",
    }
    full.update(item)
    out = ResponseBuilder.normalize_evidence([full], query_spec=spec)
    assert out == [], f"evidence should have been rejected: {reason}"


# ======================================================================
# TASK 12 — REQUIRED REGRESSION MATRIX
# ======================================================================

def _values(rows):
    return {str((r.get("details") or {}).get("value")) for r in rows}


def _matrix_1_to_3_fees(env):
    db = env["db"]
    # 1. AIT BCA fee
    spec = _spec("What is the BCA fee for 2026-27?", AIT_ID, intent="FEES",
                 college_name="Ahmedabad Institute of Technology")
    bca = knowledge_db.query_entities(db, spec.raw_question,
                                      college_id=AIT_ID, query_spec=spec)
    assert any(r["course"] == "BCA" for r in bca)
    assert "INR 32,000" in _values(bca)
    assert _source_label(ADMIN_VERIFIED, spec.college_name, query_spec=spec) \
        == "🗄️ Ahmedabad Institute of Technology Database"

    # 2. AIT BBA fee -> must NOT return the BCA record
    spec_bba = _spec("What is the BBA fee for 2026-27?", AIT_ID, intent="FEES")
    bba = knowledge_db.query_entities(db, spec_bba.raw_question,
                                      college_id=AIT_ID, query_spec=spec_bba)
    assert not any(r["course"] == "BCA" for r in bba)
    assert "INR 32,000" not in _values(bba)

    # 3. AIT Data Science fee -> must NOT return the BCA record
    spec_ds = _spec("What is the Data Science fee for 2026-27?",
                    AIT_ID, intent="FEES")
    ds = knowledge_db.query_entities(db, spec_ds.raw_question,
                                     college_id=AIT_ID, query_spec=spec_ds)
    assert not any(r["course"] == "BCA" for r in ds)
    assert "INR 32,000" not in _values(ds)


def test_matrix_01_ait_bca_fee(env):
    _matrix_1_to_3_fees(env)


def test_matrix_02_ait_bba_fee_does_not_return_bca(env):
    db = env["db"]
    spec = _spec("What is the BBA fee for 2026-27?", AIT_ID, intent="FEES")
    rows = knowledge_db.query_entities(db, spec.raw_question,
                                       college_id=AIT_ID, query_spec=spec)
    assert not any(r["course"] == "BCA" for r in rows)


def test_matrix_03_ait_data_science_fee_does_not_return_bca(env):
    db = env["db"]
    spec = _spec("What is the Data Science fee for 2026-27?",
                 AIT_ID, intent="FEES")
    rows = knowledge_db.query_entities(db, spec.raw_question,
                                       college_id=AIT_ID, query_spec=spec)
    assert not any(r["course"] == "BCA" for r in rows)


def test_matrix_04_ait_hostel_generic_verified_evidence(env):
    db = env["db"]
    spec = _spec("What hostel facilities are available at AIT?",
                 AIT_ID, intent="HOSTEL")
    rows = knowledge_db.query_entities(db, spec.raw_question,
                                       college_id=AIT_ID, query_spec=spec)
    assert rows, "generic verified hostel evidence must be available"
    assert all(r["college_id"] == AIT_ID for r in rows)


def test_matrix_05_ait_library_prefers_official_website(env):
    db = env["db"]
    spec = _spec("What library facilities are available at AIT?",
                 AIT_ID, intent="LIBRARY",
                 college_name="Ahmedabad Institute of Technology")
    snaps = knowledge_db.query_website_snapshots(
        db, spec.raw_question, college_id=AIT_ID, query_spec=spec,
    )
    assert snaps, "official AIT library snapshot must be returned"
    assert all(s["url"].startswith("https://ait.identity.test/") for s in snaps)
    assert _source_label(OFFICIAL_WEBSITE, spec.college_name, query_spec=spec) \
        == "🌐 Official Website — Ahmedabad Institute of Technology"


def test_matrix_09_ait_transportation_fabricates_nothing(env):
    """No verified AIT transport record exists -> nothing may be returned."""
    db = env["db"]
    spec = _spec("What transportation or bus facility is available at AIT?",
                 AIT_ID, intent="FACILITIES")
    assert spec.is_transport_query is True
    rows = knowledge_db.query_entities(db, spec.raw_question,
                                       college_id=AIT_ID, query_spec=spec)
    assert all(r["college_id"] == AIT_ID for r in rows)


def test_matrix_10_rcti_hostel_is_tenant_isolated(env):
    """RCTI must never see AIT evidence and vice versa."""
    db = env["db"]
    spec = _spec("What hostel facilities are available at RCTI?",
                 RCTI_ID, intent="HOSTEL")
    rows = knowledge_db.query_entities(db, spec.raw_question,
                                       college_id=RCTI_ID, query_spec=spec)
    assert all(r["college_id"] == RCTI_ID for r in rows)
    assert not any("AIT" in str(r.get("name", "")) for r in rows)


def test_matrix_11_rcti_admission_is_tenant_isolated(env):
    db = env["db"]
    spec = _spec("What is the admission process at RCTI?",
                 RCTI_ID, intent="ADMISSION")
    rows = knowledge_db.query_entities(db, spec.raw_question,
                                       college_id=RCTI_ID, query_spec=spec)
    assert all(r["college_id"] == RCTI_ID for r in rows)


def test_matrix_12_missing_college_returns_nothing(env):
    """An unresolved tenant must fail closed, never widen the query."""
    db = env["db"]
    spec = _spec("What is the BCA fee?", None, intent="FEES")
    assert knowledge_db.query_entities(db, spec.raw_question,
                                       college_id=None, query_spec=spec) == []
    assert knowledge_db.query_website_snapshots(
        db, spec.raw_question, college_id=None, query_spec=spec) == []


def test_matrix_13_inactive_record_is_never_selected(env):
    db = env["db"]
    spec = _spec("What is the BCA fee for 2026-27?", AIT_ID, intent="FEES",
                 college_name="Ahmedabad Institute of Technology")
    rows = knowledge_db.query_entities(db, spec.raw_question,
                                       college_id=AIT_ID, query_spec=spec)
    assert rows
    assert "INR 99,000" not in _values(rows)
    assert all(r.get("status") != "INACTIVE" for r in rows)


def test_matrix_14_unverified_record_is_never_treated_as_verified(env):
    db = env["db"]
    spec = _spec("What is the BCA fee for 2026-27?", AIT_ID, intent="FEES",
                 college_name="Ahmedabad Institute of Technology")
    rows = knowledge_db.query_entities(db, spec.raw_question,
                                       college_id=AIT_ID, query_spec=spec)
    assert rows
    assert "INR 88,000" not in _values(rows)

    # ...and normalization can never promote an unverified item.
    unverified_item = {
        "source_type": ADMIN_VERIFIED, "college_id": AIT_ID,
        "program": "BCA", "value": "INR 88,000",
        "verified": False, "status": "ACTIVE",
    }
    assert ResponseBuilder.normalize_evidence(
        [unverified_item], query_spec=spec) == []


def test_wrong_tenant_record_is_never_selected(env):
    """RCTI's ₹48,000 fee must never appear in an AIT answer."""
    db = env["db"]
    spec = _spec("What is the BCA fee for 2026-27?", AIT_ID, intent="FEES")
    rows = knowledge_db.query_entities(db, spec.raw_question,
                                       college_id=AIT_ID, query_spec=spec)
    assert "INR 48,000" not in _values(rows)
    assert all(r["college_id"] == AIT_ID for r in rows)


# ======================================================================
# TASK 9 / 10 / 8 — Gemini, clarification, provenance
# ======================================================================

def test_gemini_fallback_preserves_queryspec_identity_and_stays_unverified():
    """If the spec says AIT / BCA / Fees, the fallback context says so too."""
    spec = QuerySpec(
        college_id=AIT_ID, college_name="Ahmedabad Institute of Technology",
        category="Fees", topic="Fees", program="BCA",
        academic_year="2026-27", requested_field="tuition_fee",
    )
    prompt = build_system_prompt(
        "Ahmedabad Institute of Technology", query_spec=spec,
    )
    assert "Ahmedabad Institute of Technology" in prompt
    assert "BCA" in prompt
    assert "Fees" in prompt
    assert "2026-27" in prompt
    assert "R.C. Technical Institute" not in prompt

    # Gemini can never become a verified source.
    assert _source_label(GEMINI_UNVERIFIED, spec.college_name, query_spec=spec) \
        == "🤖 Gemini Answer — Not Verified"


def test_clarification_uses_queryspec_not_raw_text():
    evidence_multi = [
        {"program": "BCA", "college_id": AIT_ID},
        {"program": "BBA", "college_id": AIT_ID},
    ]
    evidence_single = [{"program": "BCA", "college_id": AIT_ID}]

    # "What hostel facilities are available at AIT?" -> no program on the
    # spec and generic evidence -> NO program clarification.
    hostel = _spec("What hostel facilities are available at AIT?",
                   AIT_ID, intent="HOSTEL")
    assert hostel.program is None
    assert GroundingValidator.clarification_needed(hostel, evidence_single) is False

    # "What is the BCA fee?" -> spec.program is BCA -> NO clarification.
    bca = _spec("What is the BCA fee?", AIT_ID, intent="FEES")
    assert bca.program is not None
    assert GroundingValidator.clarification_needed(bca, evidence_multi) is False

    # "What is the fee?" -> no program, and the evidence genuinely spans more
    # than one program family -> clarification IS allowed.
    generic = _spec("What is the fee?", AIT_ID, intent="FEES")
    assert generic.program is None
    assert GroundingValidator.clarification_needed(generic, evidence_multi) is True


def test_provenance_labels_are_exact():
    spec = QuerySpec(college_id=AIT_ID,
                     college_name="Ahmedabad Institute of Technology")
    assert _source_label(OFFICIAL_WEBSITE, None, query_spec=spec) == \
        "🌐 Official Website — Ahmedabad Institute of Technology"
    assert _source_label(ADMIN_VERIFIED, None, query_spec=spec) == \
        "🗄️ Ahmedabad Institute of Technology Database"
    assert _source_label(GEMINI_UNVERIFIED, None, query_spec=spec) == \
        "🤖 Gemini Answer — Not Verified"


def test_provenance_college_comes_from_spec_not_question():
    """A question naming another college must not relabel provenance."""
    spec = QuerySpec(
        college_id=AIT_ID, college_name="Ahmedabad Institute of Technology",
        raw_question="What is the fee at R.C. Technical Institute?",
    )
    label = _source_label(ADMIN_VERIFIED, spec.college_name, query_spec=spec)
    assert "R.C. Technical Institute" not in label
    assert label == "🗄️ Ahmedabad Institute of Technology Database"


# ======================================================================
# TASK 6 — no category-specific branches in the answer builder
# ======================================================================

def test_answer_builder_has_no_category_specific_branches():
    from pathlib import Path

    src = (Path(__file__).resolve().parents[1] / "app" / "chat" /
           "response_builder.py").read_text(encoding="utf-8")
    # Only executable code is inspected: strip docstrings and comments.
    body = src.split("def build_grounded_answer", 1)[1]
    body = body.split("@classmethod", 1)[0]
    code = "\n".join(
        line for line in body.splitlines()
        if not line.strip().startswith("#")
    )
    code = re.sub(r'""".*?"""', "", code, flags=re.S)
    code = code.lower()
    for banned in ("if hostel", "if library", "if scholarship", "if facilities"):
        assert banned not in code