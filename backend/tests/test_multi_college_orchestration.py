"Regression tests for explicit multi-college chat fan-out."""
import hashlib
import json
import pytest
pytest_plugins = ["backend.tests.test_final_answer_source_routing"]
from backend.app.chat.college_context import college_context_manager
from backend.app.chat.orchestrator import ADMIN_VERIFIED, OFFICIAL_WEBSITE
from backend.app.models.conversation import Conversation, Message
from backend.app.models.knowledge import AitEntity
from backend.tests.test_final_answer_source_routing import _stream_request

def _ask_multi(env, question):
    response = _stream_request(env, env["ait"].id, question)
    assert "message_complete" in response
    return response

@pytest.mark.asyncio
async def test_explicit_aliases_resolve_independently(routing_env):
    mentions = college_context_manager.detect_mentions(
        routing_env["db"],
        "What courses are available at AIT and R.C. Technical Institute?",
    )
    assert [item["college_id"] for item in mentions] == [
        routing_env["ait"].id, routing_env["rcti"].id,
    ]

@pytest.mark.asyncio
async def test_multi_college_courses_are_separate_and_tenant_scoped(routing_env):
    response = _ask_multi(routing_env, "What courses are available at AIT and R.C. Technical Institute?")
    assert '"college_name": "Ahmedabad Institute of Technology"' in response
    assert '"college_name": "R.C. Technical Institute"' in response
    assert "BCA" in response
    assert "72,000" not in response
    assert '"source_types": [' in response
    assert '"college_ids": ["routing-ait", "routing-rcti"]' in response
    assert response.count('event: college_answer') == 2
    assert 'event: text_delta' not in response
    assert 'event: message_complete' in response
    college_events = [
        json.loads(line.removeprefix('data: '))
        for line in response.splitlines()
        if line.startswith('data: {') and '"type": "college_answer"' in line
    ]
    assert [event['college_name'] for event in college_events] == [
        'Ahmedabad Institute of Technology', 'R.C. Technical Institute'
    ]
    assistant = routing_env['db'].query(Message).filter(
        Message.conversation_id == 'conv-routing-ait', Message.sender == 'assistant',
    ).order_by(Message.created_at.desc()).first()
    final_blocks = [block for block in assistant.blocks if block.get('type') == 'college_answer']
    assert len(final_blocks) == 2
    assert [block['college_id'] for block in final_blocks] == ['routing-ait', 'routing-rcti']
    assert final_blocks[0]['content'] != final_blocks[1]['content']
    assert "Placement — Company" not in response
    assert "SECTION: Library" not in response
@pytest.mark.asyncio
@pytest.mark.parametrize("question", [
    "What is the admission process for AIT and R.C. Technical Institute?",
    "Where can I find contact details for AIT and RCTI?",
    "What facilities are available for students at AIT and RCTI?",
])
async def test_multi_college_domains_have_separate_sections(routing_env, question):
    response = _ask_multi(routing_env, question)
    assert '"college_name": "Ahmedabad Institute of Technology"' in response
    assert '"college_name": "R.C. Technical Institute"' in response
    assert response.count('event: college_answer') == 2
    assert 'event: text_delta' not in response
    assert response.count('"type": "college_answer"') == 2
@pytest.mark.asyncio
async def test_multi_college_bca_answer_keeps_each_college_identity(routing_env):
    response = _ask_multi(routing_env, "Which college offers BCA at AIT and RCTI?")
    assert '"college_name": "Ahmedabad Institute of Technology"' in response
    assert '"college_name": "R.C. Technical Institute"' in response
    assert '"college_id": "routing-ait"' in response
    assert '"college_id": "routing-rcti"' in response
    assert 'event: text_delta' not in response
@pytest.mark.asyncio
async def test_multi_college_source_priority_is_per_college(routing_env):
    routing_env["db"].add(AitEntity(
        id="routing-ait-program", college_id=routing_env["ait"].id,
        category="program", name="AIT Computer Engineering Program",
        details={"answer": "Computer Engineering is offered at AIT."},
        source_url="https://ait.routing.test/programs", source_type=ADMIN_VERIFIED,
        authority="Ahmedabad Institute of Technology Verified Database",
        is_verified=True, content_hash=hashlib.sha256(b"ait-program").hexdigest(),
    ))
    routing_env["db"].commit()
    response = _ask_multi(routing_env, "What courses are available at AIT and R.C. Technical Institute?")
    assert ADMIN_VERIFIED in response
    assert OFFICIAL_WEBSITE in response
    assert len(routing_env["calls"]) == 0
@pytest.mark.asyncio
async def test_multi_college_does_not_trigger_switch_or_change_active_tenant(routing_env):
    response = _ask_multi(routing_env, "What courses are available at AIT and R.C. Technical Institute?")
    conversation = routing_env["db"].query(Conversation).filter(
        Conversation.id == "conv-routing-ait",
    ).first()
    assert conversation.college_id == routing_env["ait"].id
    assert "Would you like to switch" not in response
    assert "college_switch_prompt" not in response
