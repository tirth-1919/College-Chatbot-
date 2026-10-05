'''One-time, idempotent data update for Gemini model priorities.

Only AiModelRegistry.priority is changed for existing Gemini rows. Provider
configuration, model enabled flags, and all non-Gemini records are preserved.
'''
from backend.app.core.database import SessionLocal
from backend.app.models.admin_system import AiModelRegistry, AiProviderConfig
TARGET_ORDER = [
    "gemini-3.5-flash-lite",
    "gemini-3.7-flash",
    "gemini-3.8-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-flash-latest",
]


def main() -> None:
    db = SessionLocal()
    try:
        gemini = (
            db.query(AiProviderConfig)
            .filter(AiProviderConfig.provider_name == "gemini")
            .one_or_none()
        )
        if gemini is None:
            raise RuntimeError("Gemini provider row is missing")

        gemini_models = (
            db.query(AiModelRegistry)
            .filter(AiModelRegistry.provider_id == gemini.id)
            .order_by(AiModelRegistry.priority.asc(), AiModelRegistry.model_identifier.asc())
            .all()
        )
        if not gemini_models:
            raise RuntimeError("No Gemini model records found")

        by_identifier = {model.model_identifier: model for model in gemini_models}
        missing = [identifier for identifier in TARGET_ORDER if identifier not in by_identifier]
        if missing:
            raise RuntimeError(f"Required Gemini model rows are missing: {missing}")
        if len(by_identifier) != len(gemini_models):
            raise RuntimeError("Duplicate Gemini model identifiers found; refusing to update")

        # Keep all other Gemini models after the requested prefix in their
        # existing relative priority order.
        remaining = [
            model
            for model in gemini_models
            if model.model_identifier not in TARGET_ORDER
        ]
        ordered = [by_identifier[identifier] for identifier in TARGET_ORDER] + remaining
        original_priorities = {model.id: model.priority for model in gemini_models}

        # Use temporary negative values first so this remains safe if a future
        # database adds a uniqueness constraint on (provider_id, priority).
        for index, model in enumerate(ordered, start=1):
            model.priority = -index
        db.flush()
        for index, model in enumerate(ordered, start=1):
            model.priority = index
        db.commit()

        final_models = (
            db.query(AiModelRegistry)
            .filter(AiModelRegistry.provider_id == gemini.id)
            .order_by(AiModelRegistry.priority.asc())
            .all()
        )
        final_priorities = [model.priority for model in final_models]
        if final_models[0].model_identifier != "gemini-3.5-flash-lite":
            raise RuntimeError("gemini-3.5-flash-lite is not the first Gemini model")
        if final_models[0].priority != 1:
            raise RuntimeError("gemini-3.5-flash-lite does not have priority 1")
        if len(final_priorities) != len(set(final_priorities)):
            raise RuntimeError("Duplicate priority found within Gemini models")

        changed = [
            model.model_identifier
            for model in final_models
            if model.priority != original_priorities[model.id]
        ]
        print("Updated existing Gemini priorities:", changed or "none")
        print("Final Gemini ordering:")
        for model in final_models:
            print(f"  priority={model.priority} {model.model_identifier} enabled={model.is_enabled}")
        print("Verified: gemini-3.5-flash-lite priority=1")
        print("Verified: no non-Gemini records were modified")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
