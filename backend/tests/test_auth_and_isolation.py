import pytest
from backend.app.core.database import SessionLocal
from backend.app.core.security import verify_password, get_password_hash, create_access_token, decode_token
from backend.app.models.user import User
from backend.app.models.conversation import Conversation
from backend.app.chat.context import context_manager
from backend.app.knowledge.rag import rag_engine

@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    yield session
    session.close()

def test_password_hashing_and_jwt():
    raw = "AitSecurePassword2026!"
    hashed = get_password_hash(raw)
    assert verify_password(raw, hashed) == True
    assert verify_password("wrongpassword", hashed) == False

    token = create_access_token({"sub": "user-123", "email": "test@aitindia.in", "role": "student"})
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["email"] == "test@aitindia.in"

def test_coreference_resolution():
    recent = [
        {"sender": "user", "content": "Who teaches DBMS?"},
        {"sender": "assistant", "content": "Prof. Anjali Sharma teaches Database Management Systems."}
    ]
    query = "Where is her office?"
    resolved = context_manager.resolve_coreference(query, recent)
    assert "Prof. Anjali Sharma's office" in resolved

def test_user_file_isolation(db):
    # User A uploads a private document
    doc_a = rag_engine.index_document(
        db=db,
        title="user_a_private_notes.txt",
        text_content="User A private secret project details: Alpha Beta Gamma",
        user_id="user-a"
    )

    # Search by User A -> Must find it
    results_a = rag_engine.search(db, "Alpha Beta Gamma", user_id="user-a")
    assert len(results_a) > 0
    assert results_a[0]["title"] == "user_a_private_notes.txt"

    # Search by User B -> Must NOT find User A's private document!
    results_b = rag_engine.search(db, "Alpha Beta Gamma", user_id="user-b")
    assert len(results_b) == 0

    # Search anonymously -> Must NOT find User A's private document!
    results_anon = rag_engine.search(db, "Alpha Beta Gamma", user_id=None)
    assert len(results_anon) == 0
