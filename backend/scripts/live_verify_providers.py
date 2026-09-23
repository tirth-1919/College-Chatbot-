"""One-shot minimal live verification for Gemini, Groq, OpenRouter.
Never prints API keys. Single tiny request per provider."""
import asyncio

from dotenv import load_dotenv

load_dotenv()


async def main():
    from backend.app.ai.adapters.gemini_adapter import GeminiProvider
    from backend.app.ai.adapters.groq_adapter import GroqProvider
    from backend.app.ai.adapters.openrouter_adapter import OpenRouterProvider

    cases = [
        ("gemini", GeminiProvider(), "gemini-3.7-flash"),
        ("groq", GroqProvider(), "openai/gpt-oss-20b"),
        ("openrouter", OpenRouterProvider(), "google/gemma-4-31b-it:free"),
    ]
    for name, prov, model in cases:
        try:
            auth = bool(prov.api_key)
            r = await prov.generate_response(model, "Reply with exactly: OK", "You are a test harness.")
            print(f"{name}: auth={auth} model={r.model_name} http=200 success={bool(r.content.strip())} latency_ms={r.latency_ms}")
        except Exception as e:
            code = getattr(e, "status_code", "?")
            print(f"{name}: auth={bool(prov.api_key)} model={model} FAILED http={code} error={type(e).__name__}: {str(e)[:120]}")


asyncio.run(main())
