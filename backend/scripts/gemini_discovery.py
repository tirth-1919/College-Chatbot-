"""Gemini-only model discovery (read-only). Never prints the API key."""
import os, sys
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

key = os.getenv("GEMINI_API_KEY", "").strip()
if not key:
    print("GEMINI_API_KEY = NOT CONFIGURED"); sys.exit(1)
print("GEMINI_API_KEY = CONFIGURED")

from google import genai
client = genai.Client(api_key=key)

current = ["gemini-3.7-flash", "gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.5-flash"]

models = list(client.models.list())
text_capable = set()
for m in models:
    name = m.name.removeprefix("models/")
    actions = list(getattr(m, "supported_actions", None) or getattr(m, "supported_generation_methods", None) or [])
    if "generateContent" in actions:
        text_capable.add(name)

print("\n== CURRENT CHAIN STATUS ==")
for model in current:
    status = "VALID" if model in text_capable else "INVALID (not listed for generateContent)"
    print(f"- {model} -> {status}")

print("\n== ALL TEXT-GENERATION (generateContent) MODELS ==")
for name in sorted(text_capable):
    print(f"- {name} -> VALID")

excluded = {m.name.removeprefix("models/") for m in models} - text_capable
print("\n== EXCLUDED (no generateContent support) ==")
for name in sorted(excluded):
    print(f"- {name}")
