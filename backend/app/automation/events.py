import threading
from typing import Dict, List, Callable, Any
from datetime import datetime, timezone
from backend.app.core.database import SessionLocal
from backend.app.models.automation import SystemEvent

class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, handler: Callable):
        """Subscribe handler to a specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def publish(self, event_type: str, source: str, entity_id: str = None, payload: Dict[str, Any] = None):
        """Publishes an event synchronously to DB and asynchronously to registered listeners."""
        # 1. Persist to DB
        db = SessionLocal()
        try:
            evt = SystemEvent(
                event_type=event_type,
                source=source,
                entity_id=entity_id,
                payload=payload or {},
                created_at=datetime.now(timezone.utc)
            )
            db.add(evt)
            db.commit()
        except Exception as e:
            db.rollback()
        finally:
            db.close()

        # 2. Dispatch to subscribers asynchronously in daemon thread
        handlers = self._subscribers.get(event_type, [])
        if handlers:
            def _dispatch():
                for h in handlers:
                    try:
                        h(event_type, source, entity_id, payload or {})
                    except Exception:
                        pass
            threading.Thread(target=_dispatch, daemon=True).start()

event_bus = EventBus()

# Default Event Handlers
def on_knowledge_updated(evt, source, entity_id, payload):
    # Triggers cache invalidation & evaluation check
    pass

def on_image_updated(evt, source, entity_id, payload):
    # Invalidate image cache
    pass

def on_ai_provider_failed(evt, source, entity_id, payload):
    # Logs failover or issues alert
    pass

event_bus.subscribe("KNOWLEDGE_UPDATED", on_knowledge_updated)
event_bus.subscribe("IMAGE_UPDATED", on_image_updated)
event_bus.subscribe("AI_PROVIDER_FAILED", on_ai_provider_failed)
