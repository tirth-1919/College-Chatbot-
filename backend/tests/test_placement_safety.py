import uuid

import pytest

from backend.app.chat.orchestrator import ChatOrchestrator
from backend.app.core.database import SessionLocal
from backend.app.knowledge.crawler import AitWebsiteCrawler
from backend.app.knowledge.database import knowledge_db
from backend.app.knowledge.grounding import grounding_validator
from backend.app.models.knowledge import AitEntity, WebsiteSnapshot
from backend.app.scripts.seed_ait_data import seed_initial_ait_knowledge


@pytest.fixture
def db():
    session = SessionLocal()
    seed_initial_ait_knowledge(session)
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_legacy_placement_statistics_are_not_verified_data(db):
    rows = db.query(AitEntity).filter(AitEntity.category == "placement").all()
    assert not any("12.5" in str(row.details) or "85%" in str(row.details) for row in rows)


def test_placement_without_evidence_cannot_be_grounded():
    result = grounding_validator.validate_answer(
        query="What is the highest package at AIT?",
        route="ait_institutional",
        retrieved_evidence=[],
        candidate_answer=None,
    )
    assert result["grounding_status"] == "unverified"
    assert "couldn't verify" in result["answer"].lower()


def test_program_specific_snapshot_matching_does_not_cross_match(db):
    test_id = uuid.uuid4().hex
    bca = WebsiteSnapshot(
        url=f"https://www.aitindia.in/placement/bca-{test_id}",
        title="BCA Placement",
        content_hash="bca-placement",
        text_content="SECTION: BCA Placement\nBCA-specific placement information.",
    )
    mca = WebsiteSnapshot(
        url=f"https://www.aitindia.in/placement/mca-{test_id}",
        title="MCA Placement",
        content_hash="mca-placement",
        text_content="SECTION: MCA Placement\nMCA-specific placement information.",
    )
    db.add_all([bca, mca])
    db.commit()

    bca_results = knowledge_db.query_website_snapshots(db, "BCA placement")
    mca_results = knowledge_db.query_website_snapshots(db, "MCA placement")
    assert all("bca" in result["url"].lower() for result in bca_results)
    assert all("mca" in result["url"].lower() for result in mca_results)

    db.delete(bca)
    db.delete(mca)
    db.commit()


def test_insufficient_spa_extraction_is_not_successful():
    crawler = AitWebsiteCrawler()
    result = crawler._extract_generic_spa_page("/placement", "path:\"/placement\",element:x.jsx(Y)")
    assert result["extraction_status"] in {"EMPTY", "INSUFFICIENT"}