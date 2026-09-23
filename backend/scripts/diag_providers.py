"""Diagnose where the request hangs by testing each layer with a timeout."""
import asyncio
import os
import sys
import time

sys.path.insert(0, ".")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

async def main():
    q = "ai means"
    print("=== 1. Direct Gemini adapter call (with timeout) ===")
    from backend.app.core.config import settings
    print("GEMINI key configured:", bool(settings.GEMINI_API_KEY))
    print("GROQ key configured:", bool(settings.GROQ_API_KEY))
    print("OPENROUTER key configured:", bool(settings.OPENROUTER_API_KEY))

    from backend.app.ai.adapters.gemini_adapter import GeminiProvider
    gem = GeminiProvider()
    start = time.time()
    try:
        resp = await asyncio.wait_for(
            gem.generate_response(model_name="gemini-3.7-flash", prompt=q,
                                  system_instruction="You are a helpful assistant."),
            timeout=60,
        )
        print(f"GEMINI OK in {time.time()-start:.1f}s, content len={len(resp.content)}")
        print("CONTENT PREVIEW:", resp.content[:120])
    except asyncio.TimeoutError:
        print(f"GEMINI TIMED OUT after {time.time()-start:.1f}s  <-- HANG CONFIRMED")
    except Exception as e:
        print(f"GEMINI ERROR after {time.time()-start:.1f}s: {type(e).__name__}: {str(e)[:300]}")

    print("\n=== 2. Groq adapter ===")
    from backend.app.ai.adapters.groq_adapter import GroqProvider
    g = GroqProvider()
    start = time.time()
    try:
        resp = await asyncio.wait_for(
            g.generate_response(model_name="openai/gpt-oss-20b", prompt=q,
                                system_instruction="You are a helpful assistant."),
            timeout=40,
        )
        print(f"GROQ OK in {time.time()-start:.1f}s, content len={len(resp.content)}")
    except asyncio.TimeoutError:
        print(f"GROQ TIMED OUT after {time.time()-start:.1f}s")
    except Exception as e:
        print(f"GROQ ERROR after {time.time()-start:.1f}s: {type(e).__name__}: {str(e)[:300]}")

    print("\n=== 3. OpenRouter adapter ===")
    from backend.app.ai.adapters.openrouter_adapter import OpenRouterProvider
    o = OpenRouterProvider()
    start = time.time()
    try:
        resp = await asyncio.wait_for(
            o.generate_response(model_name="google/gemma-4-31b-it:free", prompt=q,
                                system_instruction="You are a helpful assistant."),
            timeout=50,
        )
        print(f"OPENROUTER OK in {time.time()-start:.1f}s, content len={len(resp.content)}")
    except asyncio.TimeoutError:
        print(f"OPENROUTER TIMED OUT after {time.time()-start:.1f}s")
    except Exception as e:
        print(f"OPENROUTER ERROR after {time.time()-start:.1f}s: {type(e).__name__}: {str(e)[:300]}")

asyncio.run(main())
