"""One-off verification: college_switch_prompt block must be streamed (§22/§61)."""
import asyncio
from backend.app.chat.streaming import sse_stream_manager


async def run():
    out = ""
    async for chunk in sse_stream_manager.stream_chat_response(
        "c1", "m1", "hello",
        [{"type": "college_switch_prompt", "content": "q",
          "target_college_id": "abc", "current_college_id": "def"}],
    ):
        out += chunk
    assert "event: college_switch_prompt" in out, out
    assert "target_college_id" in out, out
    print("PASS: college_switch_prompt streamed with target_college_id")


asyncio.run(run())
