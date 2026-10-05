# Regression tests for intent-aware, tenant-safe source selection.

from backend.app.intelligence.intent import intent_classifier
from backend.app.knowledge.source_router import source_router
from backend.app.knowledge.database import KnowledgeDatabase

def test_college_name_does_not_turn_career_advice_into_institutional_retrieval():
    result = intent_classifier.classify_intent(
        "What skills should a College A student develop for a software developer career?"
    )
    assert result["intent"] == "GENERAL_CAREER_ADVICE"
    assert source_router.route_query(
        "What skills should a College A student develop for a software developer career?",
        result,
        {},
        college_id="college-a",
    ) == "general_educational"


def test_subject_faculty_question_is_not_general_programming_advice():
    result = intent_classifier.classify_intent("Who teaches DBMS at College A?")
    assert result["intent"] == "FACULTY"
    assert source_router.route_query(
        "Who teaches DBMS at College A?", result, {}, college_id="college-a"
    ) == "institutional"


def test_required_domain_intents_are_distinct_from_generic_educational_questions():
    assert intent_classifier.classify_intent("What programming languages should I learn?")["intent"] == "GENERAL_CAREER_ADVICE"
    assert intent_classifier.classify_intent("What is DBMS?")["intent"] == "GENERAL_EDUCATIONAL"
    assert intent_classifier.classify_intent("What are College B library facilities?")["intent"] == "LIBRARY"
    assert intent_classifier.classify_intent("What is the BCA Semester 5 fee recorded for College C?")["intent"] == "FEES"


def test_category_compatibility_rejects_fee_for_faculty_and_library_committee_for_facilities():
    assert KnowledgeDatabase.compatible_categories("Who teaches DBMS?") == {"faculty"}
    assert "fee" in KnowledgeDatabase.compatible_categories("What is the BCA fee?")
    library_categories = KnowledgeDatabase.compatible_categories("What library facilities are available?")
    assert "fee" not in library_categories
    assert "library" in library_categories or "facility" in library_categories


def test_production_chatbot_routing_has_no_ait_tenant_dependency():
    from pathlib import Path
    production_root = Path(__file__).parents[1] / "app"
    production_files = list((production_root / "chat").rglob("*.py"))
    assert not any("_ait_tenant_id" in path.read_text(encoding="utf-8") for path in production_files)


def test_source_routes_are_tenant_generic():
    assert source_router.route_query(
        "What are the library facilities?",
        {"intent": "LIBRARY"},
        {},
        college_id="ait-id",
    ) == "institutional"
    assert source_router.route_query(
        "Show me the campus photo",
        {"intent": "IMAGE_REQUEST"},
        {},
        college_id="rcti-id",
    ) == "visual"
    assert source_router.route_query(
        "What are the fees?",
        {"intent": "FEES"},
        {},
        college_id=None,
    ) == "institutional"


def test_admission_document_question_has_document_intent_and_institutional_route():
    question = "What documents are required for admission to the BCA program?"
    intent = intent_classifier.classify_intent(question)
    assert intent["intent"] == "DOCUMENTS"
    assert source_router.route_query(question, intent, {"programs": ["BCA"]}, college_id="college-a") == "institutional"
