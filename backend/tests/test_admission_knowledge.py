"Focused admission category, course, tenant, and approval regressions."""
import uuid
from backend.app.intelligence.intent import intent_classifier
from backend.app.knowledge.database import KnowledgeDatabase
from backend.app.models.knowledge import AitEntity
from backend.app.models.knowledge_categories import KnowledgeCategory, KnowledgeRecord
from backend.app.models.college import College

def _college(db, key, code):
    unique_id = f"{key}-{uuid.uuid4().hex[:8]}"
    unique_code = f"{code}-{uuid.uuid4().hex[:8]}"
    c = College(id=unique_id, name=code, code=unique_code, slug=f"{key}-{uuid.uuid4().hex[:8]}", status="ACTIVE", registration_status="APPROVED")
    db.add(c)
    db.flush()
    db.flush()
    return c

def _record(db, college, key, course, title, value, status="ACTIVE", verified=True):
    cat = db.query(KnowledgeCategory).filter_by(college_id=college.id, key=key).first()
    if not cat:
        cat = KnowledgeCategory(id=f"cat-{uuid.uuid4().hex}", college_id=college.id, name=key, key=key, status="ACTIVE")
        db.add(cat)
        db.flush()
    rec = KnowledgeRecord(id=f"rec-{uuid.uuid4().hex}", college_id=college.id, category_id=cat.id,
                          title=title, course=course, value=value, source_type="ADMIN_VERIFIED",
                          verified=verified, status=status)
    db.add(rec)
    db.flush()
    return rec

def test_admission_intents_are_specific():
    assert intent_classifier.classify_intent("What documents are required for BCA admission?")["intent"] == "DOCUMENTS"
    assert intent_classifier.classify_intent("What is the admission fee for BCA?")["intent"] == "ADMISSION_FEES"
    assert intent_classifier.classify_intent("What are the eligibility criteria for admission?")["intent"] == "ADMISSION_ELIGIBILITY"
    assert intent_classifier.classify_intent("Is GUJCET required for admission?")["intent"] == "ADMISSION_ENTRANCE_EXAM"


def test_admission_course_and_tenant_isolation(db):
    ait = _college(db, "admission-ait", "AIT")
    rcti = _college(db, "admission-rcti", "RCTI")
    _record(db, ait, "admission_documents", "BCA", "BCA documents", "AIT BCA checklist")
    _record(db, ait, "admission_documents", "B.Tech CSE", "B.Tech documents", "AIT B.Tech checklist")
    _record(db, rcti, "admission_documents", "BCA", "BCA documents", "RCTI BCA checklist")
    db.commit()

    ait_results = KnowledgeDatabase.query_entities(db, "What documents are required for BCA admission?", college_id=ait.id)
    assert any("AIT BCA" in str(r["details"]) for r in ait_results)
    assert all(r["college_id"] == ait.id for r in ait_results)
    assert all("B.Tech" not in str(r["details"]) for r in ait_results)


def test_pending_admission_record_is_not_retrieved(db):
    ait = _college(db, "admission-pending", "AIT")
    _record(db, ait, "admission_documents", "BCA", "Pending docs", "Should not appear", status="DRAFT", verified=False)
    db.commit()
    assert KnowledgeDatabase.query_entities(db, "BCA admission documents", college_id=ait.id) == []


def test_live_smart_upload_document_record_retrieval_is_scoped_and_filtered(db):
    ait = _college(db, "live-smart-upload", "AIT")
    other = _college(db, "live-smart-upload-other", "OTHER")
    category = KnowledgeCategory(
        id=f"cat-{uuid.uuid4().hex}", college_id=ait.id,
        name="admission_documents", key="admission-documents-4812f8", status="ACTIVE",
    )
    other_category = KnowledgeCategory(
        id=f"cat-{uuid.uuid4().hex}", college_id=other.id,
        name="admission_documents", key="admission_documents", status="ACTIVE",
    )
    fee_category = KnowledgeCategory(
        id=f"cat-{uuid.uuid4().hex}", college_id=ait.id,
        name="fees", key="fees", status="ACTIVE",
    )
    db.add_all([category, other_category, fee_category])
    db.flush()
    approved = KnowledgeRecord(
        id=f"rec-{uuid.uuid4().hex}", college_id=ait.id, category_id=category.id,
        title="admission_documents - AIT_SMART_UPLOAD_NEW_TEST_20261002.pdf",
        course="All Programs", value="Admission Documents: submit the marksheet.",
        metadata_json={"content": "BCA admission required documents: submit the marksheet and ID proof."},
        source_type="ADMIN_VERIFIED", verified=True, status="ACTIVE",
    )
    db.add_all([
        approved,
        KnowledgeRecord(
            id=f"rec-{uuid.uuid4().hex}", college_id=ait.id, category_id=category.id,
            title="pending BCA documents", course="BCA", value="Do not return", source_type="ADMIN_VERIFIED",
            verified=False, status="PENDING_REVIEW",
        ),
        KnowledgeRecord(
            id=f"rec-{uuid.uuid4().hex}", college_id=ait.id, category_id=fee_category.id,
            title="BCA fee", course="BCA", value="Do not return", source_type="ADMIN_VERIFIED",
            verified=True, status="ACTIVE",
        ),
        KnowledgeRecord(
            id=f"rec-{uuid.uuid4().hex}", college_id=other.id, category_id=other_category.id,
            title="other tenant documents", course="All Programs", value="Do not return", source_type="ADMIN_VERIFIED",
            verified=True, status="ACTIVE",
        ),
    ])
    db.flush()
    db.commit()

    results = KnowledgeDatabase.query_entities(
        db, "What documents are required for BCA admission?", college_id=ait.id,
    )

    assert [result["id"] for result in results] == [approved.id]
    assert results[0]["college_id"] == ait.id
    assert results[0]["category"] == "admission-documents-4812f8"
    assert "BCA admission required documents" in results[0]["details"]["content"]


import asyncio
from backend.app.chat.orchestrator import ChatOrchestrator
from backend.app.models.conversation import Conversation

def test_orchestrator_retrieves_approved_smart_upload_documents_for_bca(db):
    ait = _college(db, "orchestrator-admission-ait", "AIT")
    other = _college(db, "orchestrator-admission-other", "OTHER")
    category = KnowledgeCategory(
        id=f"cat-{uuid.uuid4().hex}", college_id=ait.id,
        name="admission_documents", key="admission-documents-4812f8", status="ACTIVE",
    )
    other_category = KnowledgeCategory(
        id=f"cat-{uuid.uuid4().hex}", college_id=other.id,
        name="admission_documents", key="admission_documents", status="ACTIVE",
    )
    fee_category = KnowledgeCategory(
        id=f"cat-{uuid.uuid4().hex}", college_id=ait.id,
        name="fees", key="fees", status="ACTIVE",
    )
    db.add_all([category, other_category, fee_category])
    db.flush()
    approved = KnowledgeRecord(
        id=f"rec-{uuid.uuid4().hex}", college_id=ait.id,
        category_id=category.id,
        title="admission_documents - AIT_SMART_UPLOAD_NEW_TEST_20261002.pdf",
        course="All Programs", value="Admission Documents: submit the marksheet.",
        metadata_json={"content": "BCA admission required documents: submit the marksheet and ID proof."},
        source_type="ADMIN_VERIFIED", verified=True, status="ACTIVE",
    )
    db.add_all([
        approved,
        KnowledgeRecord(
            id=f"rec-{uuid.uuid4().hex}", college_id=ait.id, category_id=category.id,
            title="pending BCA documents", course="BCA", value="Do not return",
            source_type="ADMIN_VERIFIED", verified=False, status="PENDING_REVIEW",
        ),
        KnowledgeRecord(
            id=f"rec-{uuid.uuid4().hex}", college_id=ait.id, category_id=fee_category.id,
            title="BCA fee", course="BCA", value="Do not return",
            source_type="ADMIN_VERIFIED", verified=True, status="ACTIVE",
        ),
        KnowledgeRecord(
            id=f"rec-{uuid.uuid4().hex}", college_id=other.id, category_id=other_category.id,
            title="other tenant documents", course="All Programs", value="Do not return",
            source_type="ADMIN_VERIFIED", verified=True, status="ACTIVE",
        ),
    ])
    from backend.app.models.user import User
    user = User(id=str(uuid.uuid4()), email=f"orchestrator-{uuid.uuid4().hex}@example.test", full_name="Orchestrator Test")
    db.add(user)
    db.flush()
    conversation = Conversation(
        id=str(uuid.uuid4()), conversation_type="NORMAL", college_id=ait.id,
        user_id=user.id, title="Orchestrator regression",
    )
    db.add(conversation)
    db.commit()

    result = asyncio.run(ChatOrchestrator.process_chat(
        db=db,
        conversation_id=conversation.id,
        user_message_text="What documents are required for BCA admission?",
        college_id=ait.id,
        persist_message=False,
    ))

    assert result["answer_status"] == "ADMIN_VERIFIED"
    assert result["verified"] is True
    assert "BCA admission required documents" in result["text_content"]
    assert result["source_type"] == "ADMIN_VERIFIED"
