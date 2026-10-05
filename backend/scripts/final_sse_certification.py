import asyncio
import json
import logging
import os
import sys
import uuid
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("SECRET_KEY", "local-certification-only-secret-key-2026")
os.environ.setdefault("ENVIRONMENT", "development")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from starlette.testclient import TestClient
from backend.app.main import app
from backend.app.chat.orchestrator import chat_orchestrator
from backend.app.core.database import SessionLocal
from backend.app.core.security import decode_token
from backend.app.models.college import College
from backend.app.models.conversation import Conversation, Message
from backend.app.models.knowledge import AitEntity, WebsiteSnapshot
THIRD_ID = "3f6b7c8d-9012-4abc-def3-456789012345"
THIRD_FACT = "Test Engineering College library timing is 8:00 AM to 6:00 PM."
CASES = [
    ("A", "AIT", "What academic-year information is stored for the AIT BCA fee records in the knowledge database?"),
    ("B", "RCTI", "What services are provided through the RTO License Facilitation Center at R.C. Technical Institute?"),
    ("C", "TEST-ENGINEERING", "What are the library timing hours?"),
]


def ensure_third_fixture(db):
    third = db.query(College).filter(College.id == THIRD_ID).first()
    if not third:
        third = College(id=THIRD_ID, name="Test Engineering College", code="TEST-ENGINEERING",
                        slug="test-engineering-college", status="ACTIVE", registration_status="APPROVED")
        db.add(third)
        db.flush()
    if not db.query(AitEntity).filter(AitEntity.college_id == THIRD_ID).first():
        import hashlib
        db.add(AitEntity(id="3f6b7c8d-9012-4abc-def3-456789012348", college_id=THIRD_ID,
                         category="facility", name="Test Engineering College Library Timing",
                         details={"library_timing": "8:00 AM to 6:00 PM", "fact": THIRD_FACT},
                         source_url="https://test-engineering.example.test/library",
                         source_type="ADMIN_VERIFIED", is_official=False,
                         authority="Test Engineering College Verified Database", is_verified=True,
                         content_hash=hashlib.sha256(THIRD_FACT.encode()).hexdigest()))
        db.commit()
    return third

def assert_and_print_sse(case_id, expected_college_id, response, events, conversation, db):
    assert response.status_code == 200
    assert any(e["event"] == "message_complete" for e in events)
    conv = db.query(Conversation).filter(Conversation.id == conversation.id).one()
    assert conv.college_id == expected_college_id and conv.conversation_type == "NORMAL"
    complete = next(e["data"] for e in events if e["event"] == "message_complete")
    provenance = next((e["data"] for e in events if e["event"] == "provenance_metadata"), {})
    return complete, provenance


def parse_sse(text):
    events = []
    current = None
    data = []
    for line in text.splitlines():
        if line.startswith("event:"):
            if current is not None:
                events.append((current, "\n".join(data)))
            current = line.split(":", 1)[1].strip()
            data = []
        elif line.startswith("data:"):
            data.append(line.split(":", 1)[1].strip())
    if current is not None:
        events.append((current, "\n".join(data)))
    parsed = []
    for event, raw in events:
        try:
            value = json.loads(raw)
        except Exception:
            value = {"raw": raw}
        parsed.append({"event": event, "data": value})
    return parsed

def json_safe(value):
    return value
async def capture_process(original, *args, **kwargs):
    result = await original(*args, **kwargs)
    INTERNAL.append(result)
    return result
INTERNAL = []
TRACE = []
class TraceHandler(logging.Handler):
    def emit(self, record):
        if record.name == "ait.source_resolver":
            TRACE.append(record.__dict__.get("__dict__", {}))
            TRACE.append({key: getattr(record, key, None) for key in ("request_id", "college_id", "college", "intent", "search_query", "route", "database_query", "database_candidate_ids", "database_candidate_college_ids", "website_candidate_titles", "website_candidate_college_ids", "website", "website_evidence", "database", "database_evidence", "gemini", "final_source", "final_answer_status", "final_selected_titles")})
trace_handler = TraceHandler()
logging.getLogger("ait.source_resolver").addHandler(trace_handler)
logging.getLogger("ait.source_resolver").setLevel(logging.INFO)
original_process = chat_orchestrator.process_chat
chat_orchestrator.process_chat = lambda *args, **kwargs: capture_process(original_process, *args, **kwargs)

with TestClient(app) as client:
    login = client.post("/api/v1/auth/login", json={"email": "1@gmail.com", "password": "1"})
    print(json.dumps({"login_status": login.status_code}, ensure_ascii=False))
    if login.status_code != 200:
        print(login.text[:500])
        raise SystemExit(1)
    token = login.json()["access_token"]
    headers = {"Authorization": "Bearer " + token}
    db = SessionLocal()
    try:
        third = ensure_third_fixture(db)
        for case_id, tenant, question in CASES:
            INTERNAL.clear()
            college = third if tenant == "TEST-ENGINEERING" else db.query(College).filter(College.code == tenant).one()
            if tenant == "TEST-ENGINEERING":
                tenant_user_id = decode_token(token)["sub"]
            else:
                tenant_user_id = decode_token(token)["sub"]
            conversation_id = "cert-" + case_id.lower() + "-" + uuid.uuid4().hex
            conversation = Conversation(id=conversation_id, user_id=tenant_user_id,
                                        college_id=college.id, conversation_type="NORMAL",
                                        title=f"SSE certification {case_id}")
            # The authenticated user id is decoded from the access token by the API;
            # use the persisted owner returned by the login identity when available.
            if conversation.user_id is None:
                from backend.app.core.security import decode_token
                conversation.user_id = decode_token(token)["sub"]
            db.add(conversation)
            db.commit()
            selected = None
            response = client.post("/api/v1/chat/stream", headers=headers, json={"conversation_id": conversation_id, "message": question})
            events = parse_sse(response.text)
            deltas = [e["data"].get("delta", "") for e in events if e["event"] == "text_delta"]
            complete = next((e["data"] for e in events if e["event"] == "message_complete"), {})
            citations = [e["data"] for e in events if e["event"] == "citation"]
            provenance = [e["data"] for e in events if e["event"] == "provenance_metadata"]
            internal = INTERNAL[-1] if INTERNAL else {}
            trace = TRACE[-1] if TRACE else {}
            conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            assistant = db.query(Message).filter(Message.conversation_id == conversation_id, Message.sender == "assistant").order_by(Message.created_at.desc()).first()
            print(json.dumps({
                "case": case_id,
                "tenant_expected": tenant,
                "conversation_id": conversation_id,
                "selection_status": None,
                "http_status": response.status_code,
                "event_types": [e["event"] for e in events],
                "answer": "".join(deltas),
                "final_sse": {"source_type": (provenance[0].get("source_type") if provenance else None), "verified": (provenance[0].get("verified") if provenance else None), "answer_status": (provenance[0].get("answer_status") if provenance else None), "citation": citations, "provenance": provenance, "complete": complete},
                "internal": {"intent": (assistant.intent if assistant else trace.get("intent")), "route": trace.get("route"), "database_query": trace.get("database_query"), "selected_database_candidate": [c.get("title") for c in (assistant.citations or []) if c.get("source_type") == "ADMIN_VERIFIED"] if assistant else [], "selected_website_candidate": [c.get("title") for c in (assistant.citations or []) if c.get("source_type") == "OFFICIAL_WEBSITE"] if assistant else [], "selected_tenant": conv.college_id if conv else trace.get("college_id"), "verification": internal.get("verified") if internal else None, "gemini_used": trace.get("gemini") == "USED" if trace else (internal.get("source_type") == "GEMINI_UNVERIFIED" if internal else None), "source_type": internal.get("source_type") if internal else None, "answer_status": internal.get("answer_status") if internal else None, "citations": assistant.citations if assistant else [], "trace": trace},
            }, ensure_ascii=False, default=str))
    finally:
        db.close()
