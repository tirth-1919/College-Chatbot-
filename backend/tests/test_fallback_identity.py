"Focused regressions for tenant-safe AI fallback identity."""
import asyncio
from backend.app.ai.router import AIRouter
class _FakeDB:
    # No provider registry is needed for these synthesizer tests.  Make the
    # stand-in behave like the absent optional DB session expected by the
    # router, while retaining the methods used by fallback telemetry.
    def __bool__(self):
        return False
    def add(self, _item):
        pass
    def commit(self):
        pass

def _fallback(college_name=None, prompt="What is the hostel policy?"):
    router = AIRouter.__new__(AIRouter)
    router._expand_candidates = lambda _models, _db: []
    return asyncio.run(
        router.generate_response(
            prompt=prompt,
            system_instruction="",
            db=_FakeDB(),
            college_name=college_name,
        )
    )


def test_ait_fallback_identity_is_supported():
    answer = _fallback("Ahmedabad Institute of Technology", "Who are you?")
    assert "Ahmedabad Institute of Technology" in answer

def test_rcti_fallback_identity_never_uses_ait():
    answer = _fallback("R.C. Technical Institute", "Who are you?")
    assert "R.C. Technical Institute" in answer
    assert "Ahmedabad Institute of Technology" not in answer
    assert "AIT" not in answer
    assert "Official AIT Website" not in answer
    assert "aitindia.in" not in answer

def test_generic_college_fallback_identity_is_tenant_safe():
    answer = _fallback("Test College", "Who are you?")
    assert "Test College" in answer
    assert "Ahmedabad Institute of Technology" not in answer
    assert "AIT" not in answer

def test_missing_college_context_is_neutral_and_not_ait():
    answer = _fallback(None, "Who are you?")
    assert "active college context" in answer
    assert "Ahmedabad Institute of Technology" not in answer
    assert "AIT" not in answer
    assert "aitindia.in" not in answer
