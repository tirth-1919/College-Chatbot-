import pytest
from backend.app.core.database import SessionLocal
from backend.app.knowledge.database import knowledge_db
from backend.app.knowledge.source_router import source_router
from backend.app.knowledge.grounding import grounding_validator
from backend.app.images.retrieval import image_retrieval_engine
from backend.app.scripts.seed_ait_data import seed_initial_ait_knowledge

@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    seed_initial_ait_knowledge(session)
    yield session
    session.close()

def test_source_router():
    # Visual query route
    assert source_router.route_query("Show me AIT library", {"intent": "image_request"}, {}) == "ait_visual"

    # Institutional query route
    assert source_router.route_query("What are the BCA fees?", {"intent": "fee_lookup"}, {"programs": ["BCA"]}) == "ait_institutional"

    # General educational route
    assert source_router.route_query("Explain B+ trees in databases", {"intent": "general_educational"}, {}) == "general_educational"

def test_verified_institutional_database_lookup(db):
    # Query BCA program
    bca_results = knowledge_db.query_entities(db, "BCA")
    assert len(bca_results) > 0
    assert "fees" in str(bca_results[0]["details"]).lower()

    # Query DBMS faculty
    faculty_results = knowledge_db.query_entities(db, "Anjali")
    assert len(faculty_results) > 0
    assert "DBMS" in str(faculty_results[0]["details"])

def test_grounding_zero_hallucination():
    # If no evidence is found for an institutional query, grounding validator must not invent
    unverified = grounding_validator.validate_answer(
        query="What is the fee for NASA astronaut course at AIT?",
        route="ait_institutional",
        retrieved_evidence=[],
        candidate_answer=None
    )
    assert unverified["is_grounded"] == False
    assert unverified["grounding_status"] == "unverified"
    assert "couldn't verify" in unverified["answer"].lower()

def test_p0_verified_real_ait_images(db):
    # Test real library image
    lib_images = image_retrieval_engine.match_visual_query(db, "Show me the AIT library")
    assert len(lib_images) > 0
    assert lib_images[0]["verified"] == True
    assert "aitindia.in" in lib_images[0]["image_url"]
    assert lib_images[0]["category"] == "library"

    # Test real computer lab image
    lab_images = image_retrieval_engine.match_visual_query(db, "Show AIT computer lab")
    assert len(lab_images) > 0
    assert lab_images[0]["verified"] == True
    assert "class3.png" in lab_images[0]["image_url"] or "class4.png" in lab_images[0]["image_url"]

    # Test real campus image
    campus_images = image_retrieval_engine.match_visual_query(db, "Show AIT campus photos")
    assert len(campus_images) > 0
    assert campus_images[0]["verified"] == True
