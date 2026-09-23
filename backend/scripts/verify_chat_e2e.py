"""Final end-to-end verification of chat pipeline with the fix applied (in-process)."""
import asyncio
import os
import sys

sys.path.insert(0, ".")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

QUESTIONS = ["sports chairman", "who is the anti-ragging chairman?",
             "who is the library chairman?"]


async def run_one(db, user_id, q):
    from backend.app.chat.orchestrator import chat_orchestrator
    from backend.app.models.conversation import Conversation, Message
    conv_id = f"verify-{abs(hash(q))}"
    conv = Conversation(id=conv_id, user_id=user_id, title=q[:30])
    db.add(conv)
    msg = Message(conversation_id=conv_id, sender="user", content=q,
                  blocks=[{"type": "text", "content": q}])
    db.add(msg)
    db.commit()
    try:
        result = await asyncio.wait_for(
            chat_orchestrator.process_chat(db=db, conversation_id=conv_id,
                                           user_message_text=q, user_id=user_id),
            timeout=240,
        )
        text = result["text_content"]
        return f"OK ({len(text)} chars, grounding={result['grounding_status']}): {text[:90]!r}"
    except asyncio.TimeoutError:
        return "TIMEOUT  <-- still hanging!"
    except Exception as e:
        return f"ERROR {type(e).__name__}: {str(e)[:150]}"


async def main():
    from backend.app.core.database import SessionLocal
    from backend.app.models.user import User
    db = SessionLocal()
    demo = db.query(User).filter(User.email == "1@gmail.com").first()
    user_id = demo.id if demo else None
    for q in QUESTIONS:
        print(f"\nQ: {q}", flush=True)
        print("  ", await run_one(db, user_id, q), flush=True)
    db.close()

asyncio.run(main())
