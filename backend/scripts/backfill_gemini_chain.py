"""One-time backfill: insert the verified Gemini-only failover chain into the
existing ai_model_registry (idempotent). Does not touch other providers.
"""
from backend.app.core.database import SessionLocal
from backend.app.models.admin_system import AiProviderConfig, AiModelRegistry

CHAIN = [
    ("gemini-3.7-flash", "Gemini 3.7 Flash (Primary Verified)", 1),
    ("gemini-3.8-flash", "Gemini 3.8 Flash (Fallback 1)", 2),
    ("gemini-3.6-flash", "Gemini 3.6 Flash (Fallback 2)", 3),
    ("gemini-3.5-flash", "Gemini 3.5 Flash (Fallback 3)", 4),
    ("gemini-flash-latest", "Gemini Flash Latest (Rolling Alias, Fallback 4)", 5),
    ("gemini-3.5-flash-lite", "Gemini 3.5 Flash Lite (Fallback 5)", 6),
    ("gemini-3.1-flash-lite", "Gemini 3.1 Flash Lite (Fallback 6)", 7),
    ("gemini-flash-lite-latest", "Gemini Flash Lite Latest (Rolling Alias, Fallback 7)", 8),
    ("gemini-2.5-flash", "Gemini 2.5 Flash (Fallback 8)", 9),
    ("gemini-2.5-flash-lite", "Gemini 2.5 Flash Lite (Fallback 9)", 10),
]

db = SessionLocal()
gemini = db.query(AiProviderConfig).filter(AiProviderConfig.provider_name == "gemini").first()
assert gemini, "gemini provider row missing"

added = []
for identifier, display, prio in CHAIN:
    exists = (
        db.query(AiModelRegistry)
        .filter(
            AiModelRegistry.provider_id == gemini.id,
            AiModelRegistry.model_identifier == identifier,
        )
        .first()
    )
    if exists:
        if exists.priority != prio:
            exists.priority = prio
            added.append(f"{identifier} (priority updated)")
        continue
    db.add(AiModelRegistry(
        provider_id=gemini.id,
        model_identifier=identifier,
        display_name=display,
        priority=prio,
        supports_text=True,
        supports_vision=False,
        supports_documents=True,
        supports_streaming=True,
        context_limit=1000000,
    ))
    added.append(identifier)

db.commit()
print("Added/updated:", added or "nothing — chain already present")
for m in (
    db.query(AiModelRegistry)
    .filter(AiModelRegistry.provider_id == gemini.id)
    .order_by(AiModelRegistry.priority.asc())
):
    print(f"  prio={m.priority} {m.model_identifier} enabled={m.is_enabled} health={m.health_status}")
db.close()
