"Focused regressions for provider-error provenance safety."""
from backend.app.chat.orchestrator import (
    ADMIN_VERIFIED,
    GEMINI_UNVERIFIED,
    OFFICIAL_WEBSITE,
    PROVIDER_ERROR,
)
from backend.app.chat.response_builder import response_builder
from backend.app.knowledge.grounding import grounding_validator

def test_provider_error_provenance_is_unverified_and_source_free():
    provenance = {
        "authority": "❌ Unable to generate answer",
        "source_type": PROVIDER_ERROR,
        "answer_status": PROVIDER_ERROR,
        "verified": False,
        "source_context": None,
        "source_domain": None,
        "source_url": None,
    }
    blocks = response_builder.build_blocks(
        "I'm sorry — I couldn't reach any AI provider right now.",
        citations=[],
        provenance=provenance,
    )
    metadata = next(block for block in blocks if block["type"] == "provenance")
    assert metadata["answer_status"] == PROVIDER_ERROR
    assert metadata["source_type"] == PROVIDER_ERROR
    assert metadata["verified"] is False
    assert metadata["source_context"] is None
    assert metadata["source_url"] is None

def test_provider_failure_is_not_gemini_unverified():
    assert PROVIDER_ERROR != GEMINI_UNVERIFIED
    assert PROVIDER_ERROR not in (OFFICIAL_WEBSITE, ADMIN_VERIFIED)

def test_unsupported_generated_claim_is_not_verified():
    result = grounding_validator.validate_answer(
        query="What is the faculty fee?",
        route="ait_institutional",
        retrieved_evidence=[{
            "details": "The faculty department has three professors.",
            "source_type": ADMIN_VERIFIED,
        }],
        candidate_answer="The faculty fee is 100000.",
    )
    assert result["is_grounded"] is False
    assert result["grounding_status"] == "unverified"
    assert "couldn't verify" in result["answer"].lower()

def test_verified_label_requires_claim_support_not_retrieval_presence():
    result = grounding_validator.validate_answer(
        query="Who teaches DBMS?",
        route="ait_institutional",
        retrieved_evidence=[{
            "details": "The library is open from 8 AM to 8 PM.",
            "source_type": OFFICIAL_WEBSITE,
        }],
        candidate_answer="Professor Rao teaches DBMS.",
    )
    assert result["is_grounded"] is False
    assert result["grounding_status"] == "unverified"
