"""Probe: routing + retrieval for RCTI location questions on the dev DB."""
from backend.app.core.database import SessionLocal
from backend.app.knowledge.database import knowledge_db
from backend.app.knowledge.source_router import source_router
from backend.app.intelligence.intent import intent_classifier
from backend.app.intelligence.entities import entity_extractor

db = SessionLocal()
from backend.app.models.college import College
rcti = db.query(College).filter(College.code == "RCTI").first()
print("rcti id:", rcti.id if rcti else None)

queries = [
    "Where R.C. Technical Institute?",
    "Where is R.C. Technical Institute?",
    "What is the address of RCTI?",
    "Where is the college located?",
    "Where is the institute located?",
]
for q in queries:
    intent_info = intent_classifier.classify_intent(q)
    entities = entity_extractor.extract_entities(q)
    route = source_router.route_query(q, intent_info, entities, college_id=rcti.id if rcti else None)
    print("\nQ:", q)
    print("  intent:", intent_info["intent"], "route:", route, "topics:", entities["topics"])
    ents = knowledge_db.query_entities(db, q, college_id=rcti.id if rcti else None)
    print("  entities:", [(e["name"], e["code"]) for e in ents][:4])
    snaps = knowledge_db.query_website_snapshots(db, q, college_id=rcti.id if rcti else None)
    print("  website snaps:", [s.get("url") for s in snaps][:3])
