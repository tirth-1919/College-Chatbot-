# Focused continuous-learning admin workflow tests.
import json
import uuid
from datetime import datetime, timezone
from backend.app.api.v1.admin.learning import list_candidates, priority
from backend.app.models.learning import LearningCandidate
class Admin:
    role = "COLLEGE_ADMIN"
    college_id = "college-a"
    id = "admin-a"
    full_name = "College Admin"

def candidate(college, question, status="PENDING_REVIEW", source="OFFICIAL_WEBSITE"):
    now = datetime.now(timezone.utc)
    return LearningCandidate(id=str(uuid.uuid4()), college_id=college, question=question,
        normalized_question=question.lower(), generated_answer="Answer", answer_source=source,
        verification_status="verified", status=status, occurrence_count=6, variations=["variation"],
        first_asked_at=now, last_asked_at=now)

def test_priority_is_explainable():
    result = priority(candidate("college-a", "How are fees published?"))
    assert result["priority"] == "HIGH"
    assert "asked frequently" in result["reason"]

def test_admin_queue_is_tenant_scoped(db):
    db.add_all([candidate("college-a", "A question"), candidate("college-b", "B question")])
    db.commit()
    result = list_candidates(current_user=Admin(), db=db, page=1, per_page=50)
    assert result["total"] >= 1
    assert all(item["college_id"] == "college-a" for item in result["items"])

def test_export_payload_excludes_untrusted_gemini():
    row = candidate("college-a", "Gemini question", status="APPROVED", source="GEMINI_UNVERIFIED")
    assert row.answer_source == "GEMINI_UNVERIFIED"
    assert json.loads(json.dumps({"source": row.answer_source}))["source"] == "GEMINI_UNVERIFIED"
