'''Focused final-answer source-routing regressions.

These tests exercise ChatOrchestrator.process_chat(), not only the retrieval
helpers, so the selected evidence must be consumed by the final answer path.
'''
import hashlib
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.app.chat.orchestrator import (
    ADMIN_VERIFIED,
    GEMINI_UNVERIFIED,
    NO_VERIFIED_INFORMATION,
    OFFICIAL_WEBSITE,
    ChatOrchestrator,
)
from backend.app.core.database import Base
from backend.app.models.college import College
from backend.app.models.conversation import Conversation, Message
from backend.app.models.knowledge import AitEntity, WebsiteSnapshot
from backend.app.models.knowledge_categories import KnowledgeCategory, KnowledgeRecord
from backend.app.models.image import AitImage
from backend.app.images.retrieval import image_retrieval_engine
from backend.app.chat import college_context
from backend.app.intelligence.entities import EntityExtractor
from backend.app.models.user import User
from backend.app.intelligence.intent import intent_classifier
from backend.app.knowledge.source_router import source_router
from backend.app.ai.router import ai_router
from backend.app.core.database import get_db
from backend.app.core.security import create_access_token
from backend.app.main import app
@pytest.fixture
def routing_env(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, autoflush=False)()
    now = datetime.now(timezone.utc)
    ait = College(
        id="routing-ait", name="Ahmedabad Institute of Technology", code="AIT",
        slug="routing-ait", status="ACTIVE", registration_status="APPROVED",
        official_website="https://ait.routing.test",
    )
    rcti = College(
        id="routing-rcti", name="R.C. Technical Institute", code="RCTI",
        slug="routing-rcti", status="ACTIVE", registration_status="APPROVED",
        official_website="https://rcti.routing.test",
    )
    user = User(
        id="routing-user", email="routing@example.test", full_name="Routing User",
        role="STUDENT", is_active=True, hashed_password="x", college_id=ait.id,
    )
    db.add_all([ait, rcti, user])
    ait_hostel_category = KnowledgeCategory(
        id="routing-ait-hostel-category", college_id=ait.id,
        name="Hostel", key="hostel", status="ACTIVE",
    )
    rcti_hostel_category = KnowledgeCategory(
        id="routing-rcti-hostel-category", college_id=rcti.id,
        name="Hostel", key="hostel", status="ACTIVE",
    )
    db.add_all([ait_hostel_category, rcti_hostel_category])
    db.add_all([
        AitImage(
            id="routing-ait-campus-image", college_id=ait.id,
            title="AIT Campus Building", description="Official AIT campus photograph",
            category="campus", image_url="https://ait.routing.test/images/campus.jpg",
            thumbnail_url="https://ait.routing.test/images/campus-thumb.jpg",
            source_url="https://ait.routing.test/campus", source_type="OFFICIAL_WEBSITE",
            source_domain="ait.routing.test", verified=True,
            verification_status="PUBLISHED", content_hash=hashlib.sha256(b"routing-ait-image").hexdigest(),
        ),
        AitImage(
            id="routing-rcti-campus-image", college_id=rcti.id,
            title="RCTI Campus Building", description="Official RCTI campus photograph",
            category="campus", image_url="https://rcti.routing.test/images/campus.jpg",
            source_url="https://rcti.routing.test/campus", source_type="OFFICIAL_WEBSITE",
            source_domain="rcti.routing.test", verified=True,
            verification_status="PUBLISHED", content_hash=hashlib.sha256(b"routing-rcti-image").hexdigest(),
        ),
        KnowledgeRecord(
            id="routing-ait-hostel-1", college_id=ait.id,
            category_id=ait_hostel_category.id, title="hostel - All Programs",
            value="Hostel: accommodation subject to availability.",
            metadata_json={"summary": "Hostel: accommodation subject to availability."},
            source_type=ADMIN_VERIFIED, verified=True, status="ACTIVE",
        ),
        KnowledgeRecord(
            id="routing-ait-hostel-2", college_id=ait.id,
            category_id=ait_hostel_category.id, title="hostel - All Programs",
            value="Hostel", metadata_json={"summary": "Hostel"},
            source_type=ADMIN_VERIFIED, verified=True, status="ACTIVE",
        ),
        KnowledgeRecord(
            id="routing-rcti-hostel", college_id=rcti.id,
            category_id=rcti_hostel_category.id, title="hostel - All Programs",
            value="RCTI hostel facilities: 999 beds.",
            metadata_json={"summary": "RCTI hostel facilities: 999 beds."},
            source_type=ADMIN_VERIFIED, verified=True, status="ACTIVE",
        ),
        AitEntity(
            id="routing-ait-dbms", college_id=ait.id, category="faculty",
            name="DBMS Faculty", details={"subject": "DBMS", "answer": "Prof. Asha Rao is responsible for DBMS."},
            source_url="https://ait.routing.test/faculty", source_type=ADMIN_VERIFIED,
            authority="Ahmedabad Institute of Technology Verified Database",
            is_verified=True, content_hash=hashlib.sha256(b"dbms").hexdigest(),
        ),
        AitEntity(
            id="routing-ait-data-science", college_id=ait.id, category="fee",
            name="Data Science Program Fee", details={"program": "Data Science", "answer": "The recorded fee is INR 72,000 per year."},
            source_url="https://ait.routing.test/fees", source_type=ADMIN_VERIFIED,
            authority="Ahmedabad Institute of Technology Verified Database",
            is_verified=True, content_hash=hashlib.sha256(b"data-science").hexdigest(),
        ),
        AitEntity(
            id="routing-rcti-bca-fee", college_id=rcti.id, category="fee",
            name="BCA Semester 5 Fee", academic_year="2026-27",
            details={"answer": "The recorded BCA Semester 5 fee is INR 48,000 for AY 2026-27."},
            source_url="https://rcti.routing.test/fees", source_type=ADMIN_VERIFIED,
            authority="R.C. Technical Institute Verified Database",
            is_verified=True, content_hash=hashlib.sha256(b"rcti-fee").hexdigest(),
        ),
        WebsiteSnapshot(
            id="routing-rcti-official", college_id=rcti.id,
            url="https://rcti.routing.test/about", title="About RCTI",
            text_content=("R.C. Technical Institute was established in Ahmedabad and offers "
                          "BCA courses, technical education, student services, and academic programs. " * 3),
            content_hash=hashlib.sha256(b"official-rcti").hexdigest(), status_code=200,
        ),
        WebsiteSnapshot(
            id="routing-ait-home", college_id=ait.id,
            url="https://ait.routing.test/", title="Home",
            text_content=("Welcome to Ahmedabad Institute of Technology. Campus, events, admissions, students, and facilities." * 2),
            content_hash=hashlib.sha256(b"routing-ait-home").hexdigest(), status_code=200,
        ),
        WebsiteSnapshot(
            id="f3d56179-879d-4ce1-a130-cb75058f1e8a", college_id=ait.id,
            url="https://www.aitindia.in/facilities/library", title="Ahmedabad Institute of Technology — Library",
            text_content=("SECTION: Library\\n36,000+ Books\\nBook Bank Service\\n"
                          "Extended Access\\nReading Hall\\nSpacious hall with capacity for 200+ readers\\n"
                          "Newspapers in English, Gujarati and Hindi."),
            content_hash=hashlib.sha256(b"official-ait-library").hexdigest(), status_code=200,
        ),
        WebsiteSnapshot(
            id="routing-rcti-departments", college_id=rcti.id,
            url="https://rcti.routing.test/academics/departments/",
            title="Academic Departments — R.C. Technical Institute",
            text_content=("Academic departments and departmental coordinators: "
                          "Civil Engineering — Departmental Coordinator; "
                          "Computer Engineering — Departmental Coordinator; "
                          "Information Technology — Departmental Coordinator; "
                          "Mechanical Engineering — Departmental Coordinator."),
            content_hash=hashlib.sha256(b"official-rcti-departments").hexdigest(), status_code=200,
        ),
    ])
    db.commit()
    calls = []

    async def fake_provider(**kwargs):
        calls.append(kwargs)
        return ("Beginners should practice variables, conditionals, loops, functions, data structures, "
                "HTML, CSS, JavaScript, DOM events, form validation, debugging, and Git before "
                "building a small web application.")

    monkeypatch.setattr(ai_router, "generate_response", fake_provider)

    def make_conversation(college_id):
        existing = db.query(Conversation).filter_by(id=f"conv-{college_id}").first()
        if existing:
            return existing.id
        conversation = Conversation(
            id=f"conv-{college_id}", user_id=user.id, college_id=college_id,
            conversation_type="NORMAL", title="routing",
        )
        db.add(conversation)
        db.commit()
        return conversation.id
    yield {"db": db, "ait": ait, "rcti": rcti, "conversation": make_conversation,
           "calls": calls}
    db.close()
    Base.metadata.drop_all(engine)
    engine.dispose()

async def _ask(env, college_id, question):
    return await ChatOrchestrator.process_chat(
        env["db"], env["conversation"](college_id), question,
        user_id="routing-user", college_id=college_id,
    )

@pytest.mark.parametrize("question", [
    "ait image show",
    "show AIT images",
    "show AIT campus photos",
])
def test_ait_image_queries_classify_and_route_as_visual(question, routing_env):
    intent = intent_classifier.classify_intent(question)
    assert intent["intent"] == "IMAGE_REQUEST"
    assert source_router.route_query(
        question, intent, {}, college_id=routing_env["ait"].id,
    ) == "visual"

@pytest.mark.asyncio
@pytest.mark.parametrize("question", [
    "ait image show",
    "show AIT images",
    "show AIT campus photos",
])
async def test_visual_route_returns_tenant_scoped_verified_images_without_gemini(routing_env, question):
    result = await _ask(routing_env, routing_env["ait"].id, question)
    image_blocks = [block for block in result["blocks"] if block["type"] == "image"]

    assert result["answer_status"] == OFFICIAL_WEBSITE
    assert result["source_type"] == OFFICIAL_WEBSITE
    assert result["verified"] is True
    assert result["source_context"]["active_college_id"] == routing_env["ait"].id
    assert image_blocks
    assert image_blocks[0]["url"] == "https://ait.routing.test/images/campus.jpg"
    assert image_blocks[0]["verified"] is True
    assert all("rcti.routing.test" not in block["url"] for block in image_blocks)
    assert routing_env["calls"] == []


def test_image_query_api_keeps_existing_response_shape_and_tenant_scope(routing_env):
    app.dependency_overrides[get_db] = lambda: routing_env["db"]
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/images/query",
                params={"q": "show AIT campus photos"},
                headers={"Authorization": f"Bearer {create_access_token({'sub': 'routing-user'})}"},
            )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "show AIT campus photos"
    assert payload["count"] == 1
    assert payload["results"][0]["image_url"] == "https://ait.routing.test/images/campus.jpg"
    assert payload["results"][0]["verified"] is True
@pytest.mark.asyncio
async def test_ait_admin_verified_faculty_is_consumed_by_final_answer(routing_env):
    result = await _ask(routing_env, routing_env["ait"].id,
                        "Who is the faculty member responsible for DBMS at AIT?")
    assert result["answer_status"] == ADMIN_VERIFIED
    assert result["verified"] is True
    assert "Asha Rao" in result["text_content"]
    assert routing_env["calls"] == []

@pytest.mark.asyncio
async def test_exact_ait_bca_documents_question_rejects_program_fee_record(routing_env, monkeypatch):
    '''The live orchestrator must not let an extracted BCA program satisfy DOCUMENTS.'''
    from backend.app.intelligence.intent import intent_classifier
    db = routing_env["db"]
    db.add(AitEntity(
        id="routing-ait-bca-program", college_id=routing_env["ait"].id, category="program",
        name="BCA Program", code="BCA",
        details={"duration": "3 years / 6 semesters", "fee": "INR 45,000-52,000 per year", "eligibility": "12th pass"},
        source_url="https://ait.routing.test/programs/bca", source_type=ADMIN_VERIFIED,
        authority="Ahmedabad Institute of Technology Verified Database",
        is_verified=True, content_hash=hashlib.sha256(b"bca-program").hexdigest(),
    ))
    db.commit()
    question = "What documents are required for the BCA program at Ahmedabad Institute of Technology?"
    assert intent_classifier.classify_intent(question)["intent"] == "DOCUMENTS"

    async def no_live_page(*args, **kwargs):
        return None
    monkeypatch.setattr(
        "backend.app.knowledge.crawler.AitWebsiteCrawler.fetch_relevant_page",
        no_live_page,
    )
    result = await _ask(routing_env, routing_env["ait"].id, question)

    expected = "The specific admission document requirements could not be verified from the official college website or admin-verified records."
    assert result["text_content"] == expected
    assert result["answer_status"] == NO_VERIFIED_INFORMATION
    assert result["verified"] is False
    assert result["text_content"] != "The recorded fee is INR 72,000 per year."
    assert routing_env["calls"] == []

@pytest.mark.asyncio
async def test_smart_upload_admission_documents_answer_uses_complete_approved_section(routing_env, monkeypatch):
    db = routing_env["db"]
    category = KnowledgeCategory(
        id="routing-ait-admission-documents", college_id=routing_env["ait"].id,
        name="admission_documents", key="admission_documents", status="ACTIVE",
    )
    db.add(category)
    other_category = KnowledgeCategory(
        id="routing-rcti-admission-documents", college_id=routing_env["rcti"].id,
        name="admission_documents", key="admission_documents", status="ACTIVE",
    )
    db.add(other_category)
    db.add(KnowledgeRecord(
        id="routing-rcti-smart-upload-docs", college_id=routing_env["rcti"].id,
        category_id=other_category.id, title="admission_documents - RCTI_TEST.pdf",
        course="BCA", value="RCTI tenant checklist", metadata_json={"content": "RCTI tenant checklist"},
        source_type=ADMIN_VERIFIED, source_title="RCTI_TEST.pdf", verified=True, status="ACTIVE",
    ))
    db.add(KnowledgeRecord(
        id="routing-ait-smart-upload-docs", college_id=routing_env["ait"].id,
        category_id=category.id, title="admission_documents - AIT_SMART_UPLOAD_NEW_TEST_20261002.pdf",
        course="BCA", value="Admission Documents: submit the marksheet.",
        description="Auto-extracted from AIT_SMART_UPLOAD_NEW_TEST_20261002.pdf",
        metadata_json={
            "summary": "Admission Documents: submit the marksheet.",
            "content": (
                "Admission Documents: 12th marksheet; School leaving certificate; "
                "Government identity proof; Passport-size photographs; "
                "Applicable category certificates."
            ),
        }, source_type=ADMIN_VERIFIED, source_title="AIT_SMART_UPLOAD_NEW_TEST_20261002.pdf",
        verified=True, status="ACTIVE",
    ))
    db.commit()

    async def no_live_page(*args, **kwargs):
        return None
    monkeypatch.setattr("backend.app.knowledge.crawler.AitWebsiteCrawler.fetch_relevant_page", no_live_page)

    result = await _ask(routing_env, routing_env["ait"].id,
                        "What documents are required for BCA admission?")
    answer = result["text_content"]
    for item in (
        "12th marksheet", "School leaving certificate", "Government identity proof",
        "Passport-size photographs", "Applicable category certificates",
    ):
        assert item in answer
    assert "fee" not in answer.lower()
    assert "Courses and Programs" not in answer
    assert "RCTI tenant checklist" not in answer
    assert result["answer_status"] == ADMIN_VERIFIED
    assert result["verified"] is True
    citation_items = [item for block in result["blocks"] if block["type"] == "citation" for item in block["items"]]
    assert any(c["title"].endswith("AIT_SMART_UPLOAD_NEW_TEST_20261002.pdf") for c in citation_items)
    assert all(c.get("source_type") == ADMIN_VERIFIED for c in citation_items)
    assert result["source_context"]["active_college_id"] == routing_env["ait"].id
    assert "routing-ait-smart-upload-docs" not in answer
    assert "score" not in answer.lower()

@pytest.mark.asyncio
async def test_smart_upload_dynamic_admission_documents_answer_does_not_duplicate(routing_env, monkeypatch):
    '''Verify dynamic category keys (admission-documents-*) do not cause 4x duplicate content.'''
    db = routing_env["db"]
    cat1 = KnowledgeCategory(
        id="routing-ait-cat-dynamic-1", college_id=routing_env["ait"].id,
        name="admission_documents", key="admission-documents-289f39", status="ACTIVE",
    )
    cat2 = KnowledgeCategory(
        id="routing-ait-cat-dynamic-2", college_id=routing_env["ait"].id,
        name="admission_documents", key="admission-documents-4812f8", status="ACTIVE",
    )
    db.add_all([cat1, cat2])

    full_docs_text = (
        "Admission Documents: submit the marksheet, transfer certificate, "
        "migration certificate, passport size photographs, and identity proof during counseling."
    )
    details_payload = {
        "value": full_docs_text,
        "academic_year": "2026-27",
        "course": "All Programs",
        "description": "Auto-extracted from AIT_SMART_UPLOAD_NEW_TEST_20261002.pdf",
        "summary": full_docs_text,
        "content": full_docs_text,
    }
    rec1 = KnowledgeRecord(
        id="routing-ait-dynamic-rec-1", college_id=routing_env["ait"].id,
        category_id=cat1.id, title="admission_documents - AIT_SMART_UPLOAD_NEW_TEST_20261002.pdf",
        course="All Programs", value=full_docs_text,
        description="Auto-extracted from AIT_SMART_UPLOAD_NEW_TEST_20261002.pdf",
        metadata_json=details_payload,
        source_type=ADMIN_VERIFIED, source_title="AIT_SMART_UPLOAD_NEW_TEST_20261002.pdf",
        verified=True, status="ACTIVE",
    )
    rec2 = KnowledgeRecord(
        id="routing-ait-dynamic-rec-2", college_id=routing_env["ait"].id,
        category_id=cat2.id, title="admission_documents - AIT_SMART_UPLOAD_NEW_TEST_20261002.pdf",
        course="All Programs", value=full_docs_text,
        description="Auto-extracted from AIT_SMART_UPLOAD_NEW_TEST_20261002.pdf",
        metadata_json=details_payload,
        source_type=ADMIN_VERIFIED, source_title="AIT_SMART_UPLOAD_NEW_TEST_20261002.pdf",
        verified=True, status="ACTIVE",
    )
    db.add_all([rec1, rec2])
    db.commit()

    async def no_live_page(*args, **kwargs):
        return None
    monkeypatch.setattr("backend.app.knowledge.crawler.AitWebsiteCrawler.fetch_relevant_page", no_live_page)

    result = await _ask(routing_env, routing_env["ait"].id,
                        "What documents are required for BCA admission?")
    answer = result["text_content"]

    # All five items must be present
    for item in ("marksheet", "transfer certificate", "migration certificate", "passport size photographs", "identity proof"):
        assert item in answer

    # Complete text must appear exactly once, no 4x duplication or multi-record repetition
    assert answer.count(full_docs_text) == 1
    assert answer.count("marksheet") == 1
    assert answer.strip() == full_docs_text

    # Metadata fields must not leak into user answer
    assert "Auto-extracted from" not in answer
    assert "All Programs" not in answer
    assert "2026-27" not in answer

    # Institutional grounding and verification flags
    assert result["answer_status"] == ADMIN_VERIFIED
    assert result["verified"] is True
    assert result["source_context"]["active_college_id"] == routing_env["ait"].id

@pytest.mark.asyncio
async def test_ait_bca_eligibility_answer_contains_only_eligibility(routing_env, monkeypatch):
    db = routing_env["db"]
    db.add(AitEntity(
        id="routing-ait-bca-eligibility", college_id=routing_env["ait"].id,
        category="program", name="BCA (Bachelor of Computer Applications)", code="BCA",
        details={
            "eligibility": (
                "10+2 with English and Mathematics / Business Maths / Statistics\n"
                "Sem 1: C Programming, CS Fundamentals\n"
                "Sem 2: DBMS, Data Structures, Web Design\n"
                "Sem 3: OOP with Java, OS\n"
                "Sem 4: Python, Computer Networks\n"
                "Sem 5: Fullstack Web, AI\n"
                "Sem 6: Major Project & Internship"
            ),
            "duration": "3 Years (6 Semesters)",
            "annual_fee": "INR 45,000 to 52,000 per year",
            "semester_fee": "INR 22,500 to 26,000 per semester",
            "seats": "120 seats",
            "curriculum": "Semester-wise curriculum",
            "other_program": "B.Tech / MCA information",
        }, source_url="https://ait.routing.test/programs/bca",
        source_type=ADMIN_VERIFIED,
        authority="Ahmedabad Institute of Technology Verified Database",
        is_verified=True, content_hash=hashlib.sha256(b"bca-eligibility").hexdigest(),
    ))
    db.commit()

    async def no_live_page(*args, **kwargs):
        return None
    monkeypatch.setattr("backend.app.knowledge.crawler.AitWebsiteCrawler.fetch_relevant_page", no_live_page)

    result = await _ask(routing_env, routing_env["ait"].id,
                        "What are the eligibility requirements for BCA admission?")
    answer = result["text_content"]
    assert "10+2 with English and Mathematics / Business Maths / Statistics" in answer
    assert all(term.lower() not in answer.lower() for term in (
        "45,000", "22,500", "3 years", "6 semesters", "120 seats",
        "semester-wise curriculum", "b.tech", "mca",
    ))
    assert result["answer_status"] == ADMIN_VERIFIED
    assert result["verified"] is True
    citation_items = [item for block in result["blocks"] if block["type"] == "citation" for item in block["items"]]
    assert any(item["source_url"] == "https://ait.routing.test/programs/bca" for item in citation_items)
    assert all(item.get("source_type") == ADMIN_VERIFIED for item in citation_items)

@pytest.mark.asyncio
async def test_ait_admin_verified_fee_is_consumed_by_final_answer(routing_env):
    result = await _ask(routing_env, routing_env["ait"].id,
                         "What is the fee recorded in the database for the Data Science program at AIT?")
    assert result["answer_status"] == ADMIN_VERIFIED
    assert result["verified"] is True
    assert "72,000" in result["text_content"]

@pytest.mark.asyncio
async def test_real_chat_ait_library_snapshot_is_official_and_skips_gemini(routing_env):
    question = "What library facilities are available at Ahmedabad Institute of Technology?"
    result = await _ask(routing_env, routing_env["ait"].id, question)
    assert result["answer_status"] == OFFICIAL_WEBSITE
    assert result["source_type"] == OFFICIAL_WEBSITE
    assert result["verified"] is True
    assert "36,000+ Books" in result["text_content"]
    assert "Book Bank Service" in result["text_content"]
    assert "Extended Access" in result["text_content"]
    assert "English, Gujarati and Hindi" in result["text_content"]
    assert result["source_context"]["active_college_id"] == routing_env["ait"].id
    assert result["source_context"]["source_label"] == "🌐 Official Website — Ahmedabad Institute of Technology"
    assert any(item["source_url"] == "https://www.aitindia.in/facilities/library" for block in result["blocks"] if block["type"] == "citation" for item in block["items"])
    assert "RCTI" not in result["text_content"]
    assert routing_env["calls"] == []
    assert all(block.get("source_type") != GEMINI_UNVERIFIED for block in result["blocks"])

@pytest.mark.asyncio
async def test_exact_ait_hostel_question_uses_verified_records_and_skips_gemini(routing_env):
    result = await _ask(
        routing_env, routing_env["ait"].id,
        "What hostel facilities are available at Ahmedabad Institute of Technology?",
    )
    assert result["source_type"] == ADMIN_VERIFIED
    assert result["answer_status"] == ADMIN_VERIFIED
    assert result["verified"] is True
    assert "accommodation subject to availability" in result["text_content"]
    assert "999 beds" not in result["text_content"]
    assert result["source_context"]["source_label"] == "🗄️ Ahmedabad Institute of Technology Database"
    assert routing_env["calls"] == []

@pytest.mark.asyncio
async def test_ait_hostel_retrieval_is_tenant_isolated(routing_env):
    result = await _ask(
        routing_env, routing_env["ait"].id,
        "What hostel facilities are available at Ahmedabad Institute of Technology?",
    )
    assert result["source_type"] == ADMIN_VERIFIED
    assert result["source_context"]["active_college_id"] == routing_env["ait"].id
    assert "999 beds" not in result["text_content"]
    assert all(
        item.get("source_url") != "https://rcti.routing.test/hostel"
        for block in result["blocks"] if block["type"] == "citation"
        for item in block["items"]
    )

@pytest.mark.asyncio
async def test_ait_library_retrieval_is_tenant_isolated(routing_env):
    routing_env["db"].add(WebsiteSnapshot(
        id="routing-rcti-library", college_id=routing_env["rcti"].id,
        url="https://rcti.routing.test/facilities/library", title="RCTI Library",
        text_content="RCTI Library has 999,999 books and a reading hall.",
        content_hash=hashlib.sha256(b"rcti-library").hexdigest(), status_code=200,
    ))
    routing_env["db"].commit()

    result = await _ask(routing_env, routing_env["ait"].id,
                        "What library facilities are available at Ahmedabad Institute of Technology?")
    assert result["source_type"] == OFFICIAL_WEBSITE
    assert "999,999" not in result["text_content"]
    assert all(item["source_url"] != "https://rcti.routing.test/facilities/library" for block in result["blocks"] if block["type"] == "citation" for item in block["items"])
    assert result["source_context"]["active_college_id"] == routing_env["ait"].id

@pytest.mark.asyncio
async def test_real_chat_ait_departments_require_academic_snapshot_through_sse(routing_env, monkeypatch):
    db = routing_env["db"]
    ait_id = routing_env["ait"].id
    db.add_all([
        WebsiteSnapshot(
            id="routing-ait-placement-company", college_id=ait_id,
            url="https://ait.routing.test/placement/company", title="Placement — Company",
            text_content=("Placement companies and recruiters visit the campus. "
                          "The placement department supports students and AIT engineering branches."),
            content_hash=hashlib.sha256(b"ait-placement-company").hexdigest(), status_code=200,
        ),
        WebsiteSnapshot(
            id="routing-ait-placement-drives", college_id=ait_id,
            url="https://ait.routing.test/placement/drives", title="Placement — Drives",
            text_content=("Placement drives and company recruitment events are available for "
                          "students from every branch at AIT."),
            content_hash=hashlib.sha256(b"ait-placement-drives").hexdigest(), status_code=200,
        ),
        WebsiteSnapshot(
            id="routing-ait-home-departments-test", college_id=ait_id,
            url="https://ait.routing.test/?departments-test", title="Home",
            text_content=("Welcome to Ahmedabad Institute of Technology. Campus, events, "
                          "admissions, students, and facilities."),
            content_hash=hashlib.sha256(b"ait-home").hexdigest(), status_code=200,
        ),
        WebsiteSnapshot(
            id="routing-ait-departments", college_id=ait_id,
            url="https://ait.routing.test/academics/departments", title="Academic Departments",
            text_content=("Academic departments available at AIT include Computer Engineering, "
                          "Information Technology, Civil Engineering, and Mechanical Engineering."),
            content_hash=hashlib.sha256(b"ait-departments").hexdigest(), status_code=200,
        ),
    ])
    db.commit()

    async def no_live_page(*args, **kwargs):
        return None
    monkeypatch.setattr(
        "backend.app.knowledge.crawler.AitWebsiteCrawler.fetch_relevant_page", no_live_page,
    )
    response = _stream_request(
        routing_env, ait_id,
        "What departments are available at Ahmedabad Institute of Technology?",
    )
    assert '"source_type": "OFFICIAL_WEBSITE"' in response
    assert '"verified": true' in response
    assert "Academic Departments" in response
    assert "ait.routing.test/academics/departments" in response
    assert "Placement — Company" not in response
    assert "Placement — Drives" not in response
    assert "Campus, events" not in response
    assert len(routing_env["calls"]) == 0
@pytest.mark.asyncio
async def test_real_chat_ait_departments_without_valid_snapshot_does_not_use_irrelevant_pages(routing_env, monkeypatch):
    db = routing_env["db"]
    ait_id = routing_env["ait"].id
    # Keep this scenario focused on the absence of a valid official department
    # snapshot. Remove all AIT database evidence so unrelated ADMIN_VERIFIED
    # records cannot satisfy this department-list query.
    db.query(AitEntity).filter(AitEntity.college_id == ait_id).delete()
    db.add_all([
        WebsiteSnapshot(
            id="routing-ait-only-placement-company", college_id=ait_id,
            url="https://ait.routing.test/placement/company-only", title="Placement — Company",
            text_content=("Placement companies and recruiters visit the campus. The placement "
                          "department supports students and AIT branches."),
            content_hash=hashlib.sha256(b"ait-only-placement-company").hexdigest(), status_code=200,
        ),
        WebsiteSnapshot(
            id="routing-ait-only-placement-drives", college_id=ait_id,
            url="https://ait.routing.test/placement/drives-only", title="Placement — Drives",
            text_content=("Placement drives and company recruitment events are available for "
                          "students from every branch at AIT."),
            content_hash=hashlib.sha256(b"ait-only-placement-drives").hexdigest(), status_code=200,
        ),
        WebsiteSnapshot(
            id="routing-ait-only-home", college_id=ait_id,
            url="https://ait.routing.test/home-only", title="Home",
            text_content="Welcome to AIT: campus events, admissions, and student facilities.",
            content_hash=hashlib.sha256(b"ait-only-home").hexdigest(), status_code=200,
        ),
    ])
    db.commit()
    async def no_live_page(*args, **kwargs):
        return None
    monkeypatch.setattr(
        "backend.app.knowledge.crawler.AitWebsiteCrawler.fetch_relevant_page", no_live_page,
    )
    response = _stream_request(
        routing_env, ait_id,
        "What departments are available at Ahmedabad Institute of Technology?",
    )
    assert '"source_type": "OFFICIAL_WEBSITE"' not in response
    assert '"verified": true' not in response
    assert 'event: citation' not in response
    assert "Academic Departments" not in response
    assert "placement/company-only" not in response
    assert "Placement — Company" not in response
    assert "placement/drives-only" not in response
    assert "Placement — Drives" not in response
    assert "home-only" not in response
    assert "Home" not in response
    assert '"source_type": "NO_VERIFIED_INFORMATION"' in response
    assert '"answer_status": "NO_VERIFIED_INFORMATION"' in response
    assert '"verified": false' in response
    assert routing_env["calls"] == []

@pytest.mark.asyncio
async def test_ait_dbms_official_snapshot_beats_library_through_sse(routing_env, monkeypatch):
    routing_env["db"].add(WebsiteSnapshot(
        id="routing-ait-dbms-website", college_id=routing_env["ait"].id,
        url="https://ait.routing.test/academics/dbms", title="DBMS Faculty",
        text_content=("Department of Computer Engineering. Database Management Systems (DBMS) "
                      "is taught by the subject coordinator and faculty member Prof. Neha Shah."),
        content_hash=hashlib.sha256(b"official-ait-dbms").hexdigest(), status_code=200,
    ))
    routing_env["db"].commit()
    async def no_live_page(*args, **kwargs):
        return None
    monkeypatch.setattr("backend.app.knowledge.crawler.AitWebsiteCrawler.fetch_relevant_page", no_live_page)

    response = _stream_request(
        routing_env, routing_env["ait"].id,
        "Who is listed as the subject coordinator for DBMS at AIT?",
    )
    assert '"source_type": "OFFICIAL_WEBSITE"' in response
    assert '"verified": true' in response
    assert "Prof. Neha Shah" in response
    assert "SECTION: Library" not in response
    assert routing_env["calls"] == []

@pytest.mark.asyncio
async def test_ait_dbms_query_never_returns_unrelated_library_snapshot(routing_env, monkeypatch):
    async def no_live_page(*args, **kwargs):
        return None
    monkeypatch.setattr("backend.app.knowledge.crawler.AitWebsiteCrawler.fetch_relevant_page", no_live_page)
    monkeypatch.setattr(
        "backend.app.knowledge.database.knowledge_db.query_entities",
        lambda *args, **kwargs: [],
    )

    response = _stream_request(
        routing_env, routing_env["ait"].id,
        "Who is listed as the subject coordinator for DBMS at AIT?",
    )
    assert "SECTION: Library" not in response
    assert (
        '"source_type": "NO_VERIFIED_INFORMATION"' in response
        or '"source_type": "GEMINI_UNVERIFIED"' in response
    )
    assert '"verified": false' in response
@pytest.mark.asyncio
async def test_real_chat_rcti_department_snapshot_is_official_and_tenant_scoped(routing_env):
    result = await _ask(routing_env, routing_env["rcti"].id,
                        "What departments are listed on the R.C. Technical Institute website?")
    assert result["answer_status"] == OFFICIAL_WEBSITE
    assert result["verified"] is True
    assert "Computer" in result["text_content"]
    assert "Civil" in result["text_content"]
    assert routing_env["calls"] == []

@pytest.mark.asyncio
async def test_rcti_admin_verified_bca_fee_is_tenant_scoped(routing_env):
    result = await _ask(routing_env, routing_env["rcti"].id,
                        "What is the recorded BCA Semester 5 fee at R.C. Technical Institute for AY 2026-27?")
    assert result["answer_status"] == ADMIN_VERIFIED
    assert result["verified"] is True
    assert "48,000" in result["text_content"]
    assert "72,000" not in result["text_content"]

@pytest.mark.asyncio
async def test_ait_transportation_gemini_guidance_is_separate_from_missing_verified_evidence(routing_env, monkeypatch):
    async def misleading_transport_provider(**kwargs):
        return (
            "Based on verified college records for Ahmedabad Institute of Technology "
            "provided in our current database, there is no specific information available "
            "regarding official campus transportation or bus routes. If you are looking "
            "for general options typically available for college commuting, here is some "
            "general guidance...\n\n"
            "General commuting options may include public buses, auto-rickshaws, shared "
            "transportation, or private vehicles."
        )

    monkeypatch.setattr(ai_router, "generate_response", misleading_transport_provider)
    result = await _ask(
        routing_env,
        routing_env["ait"].id,
        "What official campus transportation or bus routes are available at AIT?",
    )

    answer = result["text_content"]
    assert result["answer_status"] == NO_VERIFIED_INFORMATION
    assert result["source_type"] == NO_VERIFIED_INFORMATION
    assert result["verified"] is False
    assert result["source_context"]["active_college_id"] == routing_env["ait"].id
    assert "could not be verified" in answer
    assert "Gemini" not in answer
    assert routing_env["calls"] == []
@pytest.mark.asyncio
@pytest.mark.parametrize("question", [
    "What career paths can an AIT computer engineering student pursue after graduation?",
    "What skills should an AIT student develop to prepare for a software development internship?",
])
async def test_general_ait_advice_uses_gemini_warning_path(routing_env, question):
    result = await _ask(routing_env, routing_env["ait"].id, question)
    assert result["answer_status"] == GEMINI_UNVERIFIED
    assert result["verified"] is False
    assert result["source_type"] == GEMINI_UNVERIFIED
    assert routing_env["calls"]
    provenance = next(block for block in result["blocks"] if block["type"] == "provenance")
    assert provenance["answer_status"] == GEMINI_UNVERIFIED
    assert "Gemini-generated" in provenance["authority"]

@pytest.mark.asyncio
async def test_exact_general_programming_question_uses_gemini_warning_path(routing_env):
    result = await _ask(
        routing_env,
        routing_env["ait"].id,
        "What programming concepts should a beginner practice before building a small web application?",
    )
    assert result["answer_status"] == GEMINI_UNVERIFIED
    assert result["source_type"] == GEMINI_UNVERIFIED
    assert result["verified"] is False
    assert "Verified College Fact" not in result["text_content"]
    assert result["source_type"] == GEMINI_UNVERIFIED
    assert routing_env["calls"]
    provenance = next(block for block in result["blocks"] if block["type"] == "provenance")
    assert provenance["answer_status"] == GEMINI_UNVERIFIED
    assert provenance["verified"] is False
    assert provenance["source_context"]["provenance"] == "gemini_unverified"

@pytest.mark.asyncio
async def test_real_chat_stream_exact_programming_question_has_only_unverified_gemini_guidance(routing_env, monkeypatch):
    response = _stream_request(
        routing_env,
        routing_env["ait"].id,
        "What programming concepts should a beginner practice before building a small web application?",
    )
    assert '"source_type": "GEMINI_UNVERIFIED"' in response
    assert '"answer_status": "GEMINI_UNVERIFIED"' in response
    assert '"verified": false' in response
    assert '"provenance": "gemini_unverified"' in response
    assert 'event: citation' not in response
    assistant = routing_env["db"].query(Message).filter(
        Message.conversation_id == "conv-routing-ait", Message.sender == "assistant",
    ).order_by(Message.created_at.desc()).first()
    assert assistant.citations == []
    assert assistant.provenance["source_type"] == GEMINI_UNVERIFIED
    assert assistant.provenance["answer_status"] == GEMINI_UNVERIFIED
    assert assistant.provenance["verified"] is False
    assert assistant.provenance["source_context"]["provenance"] == "gemini_unverified"
    assert all(term.lower() not in response.lower() for term in (
        "Placement — Company", "Placement — Drives", "RADIXWEB", "ASPIRE SOFTSERV",
        "AIT Hackathon", "Verified College Fact", "Official College Website",
    ))
    assert len(routing_env["calls"]) == 1
@pytest.mark.asyncio
async def test_rcti_matching_crawled_data_wins_as_official_website(routing_env):
    result = await _ask(routing_env, routing_env["rcti"].id,
                        "What courses does R.C. Technical Institute offer?")
    assert result["answer_status"] == OFFICIAL_WEBSITE
    assert result["verified"] is True
    assert "R.C. Technical Institute" in result["text_content"]
    # Stored official website evidence is now consumed directly; Gemini is not
    # called when the requested crawled page already contains the answer.
    assert routing_env["calls"] == []

def _stream_request(env, college_id, question):
    app.dependency_overrides[get_db] = lambda: env["db"]
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/chat/stream",
                headers={"Authorization": f"Bearer {create_access_token({'sub': 'routing-user'})}"},
                json={"conversation_id": env["conversation"](college_id), "message": question},
            )
            assert response.status_code == 200, response.text
            return response.text
    finally:
        app.dependency_overrides.pop(get_db, None)

@pytest.mark.parametrize("question", [
    "ait image show",
    "show AIT images",
    "show AIT campus photos",
])
def test_real_chat_stream_routes_ait_image_queries_to_verified_images_without_gemini(
    routing_env, monkeypatch, question,
):
    retrieval_calls = []
    original_match = image_retrieval_engine.match_visual_query
    def trace_match(db, query, college_id=None):
        retrieval_calls.append({"query": query, "college_id": college_id})
        return original_match(db, query, college_id=college_id)

    monkeypatch.setattr(image_retrieval_engine, "match_visual_query", trace_match)
    original_detect_mentions = college_context.college_context_manager.detect_mentions
    monkeypatch.setattr(
        college_context.college_context_manager,
        "detect_mentions",
        lambda db, message: original_detect_mentions(db, message) + [
            {"college_id": routing_env["ait"].id, "college": routing_env["ait"]},
            {"college_id": routing_env["rcti"].id, "college": routing_env["rcti"]},
        ],
    )
    response = _stream_request(routing_env, routing_env["ait"].id, question)

    image_events = [
        line.removeprefix("data: ")
        for line in response.splitlines()
        if line.startswith("data: ") and '"type": "image"' in line
    ]
    assert len(retrieval_calls) == 1
    assert retrieval_calls[0]["query"] == question
    assert retrieval_calls[0]["college_id"] == routing_env["ait"].id
    intent = routing_env["db"].query(Message).filter_by(
        conversation_id=routing_env["conversation"](routing_env["ait"].id),
        sender="assistant",
    ).order_by(Message.created_at.desc()).first().intent
    query_spec = EntityExtractor.extract_query_understanding(
        question, college_id=routing_env["ait"].id, intent=intent,
    )
    from backend.app.knowledge.source_router import source_router as runtime_source_router
    assert intent == "IMAGE_REQUEST"
    assert runtime_source_router.route_query(query_spec) == "visual"
    assert image_events
    image_block = __import__("json").loads(image_events[0])
    assert image_block["type"] == "image"
    assert image_block["url"] == "https://ait.routing.test/images/campus.jpg"
    assert image_block["thumbnail_url"] == "https://ait.routing.test/images/campus-thumb.jpg"
    assert image_block["alt"] == "AIT Campus Building"
    assert image_block["title"] == "AIT Campus Building"
    assert image_block["category"] == "campus"
    assert image_block["source_url"] == "https://ait.routing.test/campus"
    assert image_block["verified"] is True
    assert "Gemini" not in response
    assert '"source_type": "OFFICIAL_WEBSITE"' in response
    assert routing_env["calls"] == []

    assistant = routing_env["db"].query(Message).filter_by(
        conversation_id=routing_env["conversation"](routing_env["ait"].id),
        sender="assistant",
    ).order_by(Message.created_at.desc()).first()
    assert assistant.intent == "IMAGE_REQUEST"
    assert assistant.provenance["source_type"] == OFFICIAL_WEBSITE
@pytest.mark.asyncio
async def test_real_chat_stream_general_ait_python_question_calls_gemini_unverified(routing_env, monkeypatch):
    response = _stream_request(
        routing_env, routing_env["ait"].id,
        "What should an AIT student learn before starting a beginner-level Python project?",
    )
    assert '"source_type": "GEMINI_UNVERIFIED"' in response
    assert '"answer_status": "GEMINI_UNVERIFIED"' in response
    assert '"verified": false' in response
    assert '"source_type": "GEMINI_UNVERIFIED"' in response
    assert '"answer_status": "GEMINI_UNVERIFIED"' in response
    assert '"verified": false' in response
    assert "Verified College Fact" not in response
    assert "ait.routing.test" not in response
    assert len(routing_env["calls"]) == 1
@pytest.mark.asyncio
async def test_real_chat_stream_returns_official_website_for_rcti_departments(routing_env, monkeypatch):
    async def no_live_page(*args, **kwargs):
        return None
    monkeypatch.setattr(
        "backend.app.knowledge.crawler.AitWebsiteCrawler.fetch_relevant_page",
        no_live_page,
    )
    response = _stream_request(
        routing_env, routing_env["rcti"].id,
        "What departments are listed on the R.C. Technical Institute website?",
    )
    assert '"source_type": "OFFICIAL_WEBSITE"' in response
    assert '"verified": true' in response
    assert "Computer" in response
    assert len(routing_env["calls"]) == 0
@pytest.mark.asyncio
async def test_real_chat_stream_consumes_verified_knowledge_and_skips_gemini(routing_env, monkeypatch):
    async def no_live_page(*args, **kwargs):
        return None
    monkeypatch.setattr(
        "backend.app.knowledge.crawler.AitWebsiteCrawler.fetch_relevant_page",
        no_live_page,
    )
    response = _stream_request(
        routing_env, routing_env["ait"].id,
        "Which faculty member is listed for DBMS at AIT?",
    )
    assert "Asha Rao" in response
    assert '"source_type": "ADMIN_VERIFIED"' in response
    assert '"verified": true' in response
    assert len(routing_env["calls"]) == 0
@pytest.mark.asyncio
async def test_real_chat_stream_preserves_rcti_tenant_after_switch(routing_env, monkeypatch):
    async def no_live_page(*args, **kwargs):
        return None
    monkeypatch.setattr(
        "backend.app.knowledge.crawler.AitWebsiteCrawler.fetch_relevant_page",
        no_live_page,
    )
    response = _stream_request(
        routing_env, routing_env["rcti"].id,
        "What is the recorded BCA Semester 5 fee at R.C. Technical Institute for AY 2026-27?",
    )
    assert "48,000" in response
    assert '"source_type": "ADMIN_VERIFIED"' in response
    assert '"verified": true' in response
    assert "72,000" not in response
    assert len(routing_env["calls"]) == 0
@pytest.mark.asyncio
async def test_real_chat_stream_routes_placement_contact_to_placement_cell(routing_env, monkeypatch):
    db = routing_env["db"]
    db.add(WebsiteSnapshot(
        id="routing-ait-placement-cell-contact", college_id=routing_env["ait"].id,
        url="https://ait.routing.test/placement/cell", title="Placement — Cell",
        text_content=(
            "SECTION: Placement — Cell\n"
            "Students can contact the placement cell at placement@aitindia.in or 9825024679.\n"
            "SECTION: Placement — Company\nPlacement company lists.\n"
            "SECTION: Placement — Drives\nPlacement drives and unrelated events."
        ),
        content_hash=hashlib.sha256(b"ait-placement-cell-contact").hexdigest(), status_code=200,
    ))
    db.commit()

    async def no_live_page(*args, **kwargs):
        return None
    monkeypatch.setattr(
        "backend.app.knowledge.crawler.AitWebsiteCrawler.fetch_relevant_page",
        no_live_page,
    )
    response = _stream_request(
        routing_env, routing_env["ait"].id,
        "How can students contact the placement cell?",
    )
    assert '"source_type": "OFFICIAL_WEBSITE"' in response
    assert '"verified": true' in response
    assert "placement@aitindia.in" in response
    assert "9825024679" in response
    assert "Placement — Company" not in response
    assert "Placement — Drives" not in response
    assert len(routing_env["calls"]) == 0
@pytest.mark.asyncio
async def test_rcti_courses_use_about_snapshot_without_gemini(routing_env):
    result = await _ask(
        routing_env,
        routing_env["rcti"].id,
        "What courses are offered by R.C. Technical Institute?",
    )
    assert result["answer_status"] == OFFICIAL_WEBSITE
    assert result["verified"] is True
    assert "BCA" in result["text_content"]
    assert routing_env["calls"] == []
    assert "placement" not in result["text_content"].lower()
    assert "grievance" not in result["text_content"].lower()
    assert "library" not in result["text_content"].lower()

@pytest.mark.asyncio
async def test_ait_courses_answer_uses_only_course_sections_from_official_snapshot(routing_env):
    db = routing_env["db"]
    db.add(WebsiteSnapshot(
        id="routing-ait-courses-and-home", college_id=routing_env["ait"].id,
        url="https://ait.routing.test/academics/programs", title="Academic Programs",
        text_content=(
            "SECTION: Courses\n"
            "Ahmedabad Institute of Technology offers the following courses: Computer Engineering, Information Technology, and Mechanical Engineering.\n"

            "SECTION: Placement — Cell\nPlacement training, recruiters, and campus placement drives.\n"
            "SECTION: Home\nWelcome to our vibrant campus with modern facilities, events, and student life."
        ),
        content_hash=hashlib.sha256(b"ait-courses-and-home").hexdigest(), status_code=200,
    ))
    db.commit()

    result = await _ask(
        routing_env, routing_env["ait"].id,
        "What courses are offered by Ahmedabad Institute of Technology?",
    )

    assert result["source_type"] == OFFICIAL_WEBSITE
    assert result["verified"] is True
    assert "Computer Engineering" in result["text_content"]
    assert "Information Technology" in result["text_content"]
    assert "SECTION: Placement — Cell" not in result["text_content"]
    assert "vibrant campus" not in result["text_content"]
    assert routing_env["calls"] == []

@pytest.mark.asyncio
async def test_ait_admission_answer_uses_only_admission_sections_from_official_snapshot(routing_env):
    db = routing_env["db"]
    db.add(WebsiteSnapshot(
        id="routing-ait-admission-and-home", college_id=routing_env["ait"].id,
        url="https://ait.routing.test/admissions/process", title="Admission Process",
        text_content=(
            "SECTION: Admission Process\n"
            "Applicants should register through ACPC, complete the online application, and submit "
            "the required documents before the counselling deadline.\n"
            "SECTION: Home\nAhmedabad Institute of Technology has a beautiful campus, annual events, "
            "modern laboratories, and a welcoming student community.\n"
            "SECTION: Placement — Cell\nRecruiters and placement training support students."
        ),
        content_hash=hashlib.sha256(b"ait-admission-and-home").hexdigest(), status_code=200,
    ))
    db.commit()

    result = await _ask(
        routing_env, routing_env["ait"].id,
        "What is the admission process for Ahmedabad Institute of Technology?",
    )

    assert result["source_type"] == OFFICIAL_WEBSITE
    assert result["verified"] is True
    assert "ACPC" in result["text_content"]
    assert "online application" in result["text_content"]
    assert "beautiful campus" not in result["text_content"]
    assert "SECTION: Placement — Cell" not in result["text_content"]
    assert routing_env["calls"] == []


@pytest.mark.asyncio
async def test_official_snapshots_are_synthesized_into_a_focused_grounded_answer(routing_env, monkeypatch):
    db = routing_env["db"]
    ait_id = routing_env["ait"].id
    db.add_all([
        WebsiteSnapshot(
            id="routing-ait-technical-events", college_id=ait_id,
            url="https://ait.routing.test/events/technical", title="Technical Activities",
            text_content=("AIT has organized an Internal Hackathon and Technical Day. "
                          "Students participate in technical activities and project work."),
            content_hash=hashlib.sha256(b"official-ait-technical-events").hexdigest(), status_code=200,
        ),
        WebsiteSnapshot(
            id="routing-ait-unrelated-sports", college_id=ait_id,
            url="https://ait.routing.test/sports", title="Sports",
            text_content="Sports facilities, teams, and events are available to students.",
            content_hash=hashlib.sha256(b"official-ait-unrelated-sports").hexdigest(), status_code=200,
        ),
    ])
    db.commit()

    async def no_live_page(*args, **kwargs):
        return None
    monkeypatch.setattr(
        "backend.app.knowledge.crawler.AitWebsiteCrawler.fetch_relevant_page", no_live_page,
    )
    result = await _ask(
        routing_env, ait_id,
        "Does Ahmedabad Institute of Technology provide any facilities for students to work on technical projects?",
    )

    assert result["answer_status"] == OFFICIAL_WEBSITE
    assert result["source_type"] == OFFICIAL_WEBSITE
    assert "Internal Hackathon" in result["text_content"]
    assert "Technical Day" in result["text_content"]
    # The generic grounded-answer contract returns normalized evidence text;
    # it does not synthesize the historical negative/qualification wording.
    assert result["text_content"] == (
        "AIT has organized an Internal Hackathon and Technical Day. "
        "Students participate in technical activities and project work."
    )
    assert "Sports facilities" not in result["text_content"]
    assert "placement" not in result["text_content"].lower()
    assert routing_env["calls"] == []


@pytest.mark.asyncio
async def test_ait_bca_fee_year_and_short_query_use_admin_verified_record(routing_env):
    db = routing_env["db"]
    category = KnowledgeCategory(
        id="routing-ait-fees-modern", college_id=routing_env["ait"].id,
        name="Fees", key="fees", status="ACTIVE",
    )
    db.add(category)
    db.add(KnowledgeRecord(
        id="routing-ait-bca-fee-modern", college_id=routing_env["ait"].id,
        category_id=category.id, course="BCA", academic_year="2026-27",
        title="BCA Semester 1 Fee", field_name="Semester Fee", value="₹32,000",
        source_type=ADMIN_VERIFIED, verified=True, status="ACTIVE",
    ))
    db.commit()

    result = await _ask(
        routing_env, routing_env["ait"].id,
        "What is the BCA fee at Ahmedabad Institute of Technology for the 2026-27 academic year?",
    )
    assert result["answer_status"] == ADMIN_VERIFIED
    assert result["verified"] is True
    assert "32,000" in result["text_content"]
    assert routing_env["calls"] == []

    short_result = await _ask(routing_env, routing_env["ait"].id, "bca fee")
    assert short_result["answer_status"] == ADMIN_VERIFIED
    assert short_result["verified"] is True
    assert "32,000" in short_result["text_content"]

@pytest.mark.asyncio
async def test_ait_bba_fee_does_not_fall_back_to_bca_record(routing_env):
    result = await _ask(routing_env, routing_env["ait"].id, "bba fee")
    assert result["answer_status"] != ADMIN_VERIFIED
    assert result["verified"] is False
    assert "48,000" not in result["text_content"]
    assert "72,000" not in result["text_content"]
