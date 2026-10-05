import pytest
from backend.app.chat.orchestrator import ChatOrchestrator
from backend.app.chat.response_builder import ResponseBuilder
from backend.app.intelligence.entities import EntityExtractor
from backend.app.intelligence.intent import intent_classifier

def spec(question, college_id="ait"):
    return EntityExtractor.extract_query_understanding(question, college_id=college_id)


def test_structured_value_survives_normalization_and_grounding():
    s = spec("What hostel facilities are available at AIT?")
    item = {"id": "hostel", "college_id": "ait", "category": "hostel",
            "value": "Hostel: accommodation subject to availability.",
            "details": None, "source_type": "ADMIN_VERIFIED", "verified": True,
            "status": "ACTIVE"}
    normalized = ResponseBuilder.normalize_evidence([item], query_spec=s)
    assert normalized[0]["value"] == item["value"]
    assert ResponseBuilder.build_grounded_answer([item], query_spec=s) == item["value"]

@pytest.mark.parametrize(("question", "topic"), [
    ("What library facilities are available?", "LIBRARY"),
    ("What hostel facilities are available?", "HOSTEL"),
    ("What scholarship support is available?", "SCHOLARSHIP"),
    ("What transportation is available?", "TRANSPORT"),
    ("What facilities are available?", "FACILITIES"),
])
def test_specific_topics_do_not_collapse_to_facilities(question, topic):
    assert spec(question).topic == topic
@pytest.mark.parametrize("question", [
    "What documents are required for BCA admission?",
    "What are the eligibility criteria for BCA?",
])
def test_admission_subtopics_keep_admission_parent(question):
    s = spec(question)
    assert s.topic == "ADMISSION"
    assert s.requested_field in {"documents", "eligibility"}

@pytest.mark.parametrize(("question", "program"), [
    ("What facilities are available for BCA students?", "BCA (Bachelor of Computer Applications)"),
    ("What facilities support research in artificial intelligence?", None),
    ("What facilities are available for students studying data science in general?", None),
])
def test_program_extraction_requires_college_program_context(question, program):
    assert spec(question).program == program
@pytest.mark.parametrize(("question", "intent"), [
    ("What library facilities are available?", "LIBRARY"),
    ("What hostel facilities are available?", "HOSTEL"),
    ("What scholarship support is available?", "SCHOLARSHIP"),
    ("What transportation is available?", "TRANSPORT"),
])
def test_intent_topics_are_explicit(question, intent):
    assert intent_classifier.classify_intent(question)["intent"] == intent

def test_live_snapshot_accepts_query_spec():
    assert "query_spec" in ChatOrchestrator._persist_live_snapshot.__code__.co_varnames
