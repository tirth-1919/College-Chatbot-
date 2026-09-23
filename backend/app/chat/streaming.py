import json
import asyncio
from typing import AsyncGenerator, Dict, Any, List

class SSEStreamManager:
    @classmethod
    def format_sse(cls, event: str, data: Dict[str, Any]) -> str:
        payload = json.dumps(data)
        return f"event: {event}\ndata: {payload}\n\n"

    @classmethod
    async def stream_chat_response(
        cls,
        conversation_id: str,
        message_id: str,
        text_content: str,
        blocks: List[Dict[str, Any]],
        grounding_status: str = "verified",
        tool_status: str = "Completed institutional resolution"
    ) -> AsyncGenerator[str, None]:
        """
        Streams typed Server-Sent Events conforming strictly to the specification.
        """
        # 1. message_start
        yield cls.format_sse("message_start", {
            "conversation_id": conversation_id,
            "message_id": message_id
        })
        await asyncio.sleep(0.02)

        # 2. tool_status
        yield cls.format_sse("tool_status", {
            "status": tool_status
        })
        await asyncio.sleep(0.02)

        # 3. Stream text_delta chunks
        words = text_content.split(" ")
        chunk_size = 4
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i+chunk_size])
            if i + chunk_size < len(words):
                chunk += " "
            yield cls.format_sse("text_delta", {"delta": chunk})
            await asyncio.sleep(0.03)

        # 4. Stream structured blocks (images, tables, citations, provenance)
        for block in blocks:
            b_type = block.get("type")
            if b_type == "image":
                yield cls.format_sse("image", block)
                await asyncio.sleep(0.02)
            elif b_type == "table":
                yield cls.format_sse("table", block)
                await asyncio.sleep(0.02)
            elif b_type == "citation":
                yield cls.format_sse("citation", block)
                await asyncio.sleep(0.02)
            elif b_type == "provenance":
                yield cls.format_sse("provenance_metadata", block)
                await asyncio.sleep(0.02)
            elif b_type in ("college_switch_prompt", "suggested_action"):
                # FIX: interactive blocks were silently dropped, so the [Switch]
                # button never rendered during a live session (§22/§61). Stream
                # them under their own typed event names.
                yield cls.format_sse(b_type, block)
                await asyncio.sleep(0.02)

        # 5. message_complete
        yield cls.format_sse("message_complete", {
            "conversation_id": conversation_id,
            "message_id": message_id,
            "grounding_status": grounding_status
        })

sse_stream_manager = SSEStreamManager()
