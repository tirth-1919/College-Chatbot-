import pytest
from backend.app.knowledge.confidence import verify_claims
from backend.app.knowledge.grounding import grounding_validator
from backend.app.chat.streaming import sse_stream_manager

def test_claim_gate_rejects_unrelated_sentence():
    result = verify_claims(
        "The BCA fee is ₹32,000. Hostel transport is included.",
        [{"details": "BCA fee = ₹32,000 for 2026-27"}],
    )
    assert result["verified"] is False
    assert "Hostel transport is included" in result["unsupported_claims"]


def test_grounding_rejects_claim_not_supported_by_same_evidence():
    result = grounding_validator.validate_answer(
        "What is the BCA fee?", "institutional",
        [{"details": "MCA fee = ₹40,000", "college_id": "college-a"}],
        "The BCA fee is ₹32,000.",
    )
    assert result["is_grounded"] is False
    assert result["grounding_status"] == "unverified"

@pytest.mark.asyncio
async def test_sse_contract_has_single_completion():
    events = []
    async for event in sse_stream_manager.stream_chat_response(
        "conversation", "message", "hello world", [], "verified"
    ):
        events.append(event)
    stream = "".join(events)
    assert "event: message_start" in stream
    assert "event: message_complete" in stream
    assert stream.count("event: message_complete") == 1
