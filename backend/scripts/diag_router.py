"""Verify router-level failover: Gemini hang -> timeout -> Groq success."""
import asyncio
import os
import sys
import time

sys.path.insert(0, ".")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")


async def main():
    from backend.app.core.database import SessionLocal
    from backend.app.ai.router import ai_router

    db = SessionLocal()
    start = time.time()
    result = await asyncio.wait_for(
        ai_router.generate_response(
            prompt="ai means",
            system_instruction="You are a helpful assistant.",
            db=db,
            user_id=None,
            conversation_id=None,
        ),
        timeout=180,
    )
    elapsed = time.time() - start
    print(f"ROUTER RESULT in {elapsed:.1f}s (len={len(result)}):")
    print(result[:300])
    db.close()

asyncio.run(main())
