"""Ownership and archive/rename regression tests for student conversations."""
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.api.v1.conversations import router
from backend.app.core.database import Base, get_db
from backend.app.core.security import create_access_token
from backend.app.models.conversation import Conversation, Message
from backend.app.models.user import User


@pytest.fixture
def conversation_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False)
    db = factory()
    owner = User(id=str(uuid.uuid4()), email="conversation-owner@example.test", full_name="Owner", role="STUDENT")
    other = User(id=str(uuid.uuid4()), email="conversation-other@example.test", full_name="Other", role="STUDENT")
    db.add_all([owner, other])
    db.commit()

    app = FastAPI()
    app.include_router(router)

    def override_db():
        request_db = factory()
        try:
            yield request_db
        finally:
            request_db.close()

    app.dependency_overrides[get_db] = override_db

    def create(owner_id=owner.id, title="Original title"):
        conversation = Conversation(id=str(uuid.uuid4()), user_id=owner_id, title=title)
        db.add(conversation)
        db.add(Message(conversation_id=conversation.id, sender="user", content="persisted message"))
        db.commit()
        return conversation.id

    def headers(user):
        return {"Authorization": f"Bearer {create_access_token({'sub': user.id})}"}

    try:
        yield TestClient(app), db, create, headers(owner), headers(other)
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_student_can_rename_own_conversation_and_refresh_persists(conversation_client):
    client, db, create, owner_headers, _ = conversation_client
    conversation_id = create()
    response = client.patch(f"/conversations/{conversation_id}", headers=owner_headers, json={"title": "Renamed chat"})
    assert response.status_code == 200
    assert response.json()["title"] == "Renamed chat"
    db.expire_all()
    assert db.get(Conversation, conversation_id).title == "Renamed chat"
    assert client.get("/conversations", headers=owner_headers).json()[0]["title"] == "Renamed chat"


def test_archive_unarchive_preserves_messages_and_moves_between_views(conversation_client):
    client, db, create, owner_headers, _ = conversation_client
    conversation_id = create()
    assert client.patch(f"/conversations/{conversation_id}", headers=owner_headers,
                        json={"is_archived": True}).status_code == 200
    assert client.get("/conversations", headers=owner_headers).json() == []
    archived = client.get("/conversations?archived=true", headers=owner_headers).json()
    assert [item["id"] for item in archived] == [conversation_id]
    assert client.get(f"/conversations/{conversation_id}", headers=owner_headers).json()["messages"][0]["content"] == "persisted message"
    assert client.patch(f"/conversations/{conversation_id}", headers=owner_headers,
                        json={"is_archived": False}).status_code == 200
    assert [item["id"] for item in client.get("/conversations", headers=owner_headers).json()] == [conversation_id]


def test_student_cannot_change_another_students_conversation(conversation_client):
    client, _, create, _, other_headers = conversation_client
    conversation_id = create()
    assert client.patch(f"/conversations/{conversation_id}", headers=other_headers,
                        json={"title": "stolen"}).status_code == 404
    assert client.patch(f"/conversations/{conversation_id}", headers=other_headers,
                        json={"is_archived": True}).status_code == 404


def test_blank_conversation_title_is_rejected(conversation_client):
    client, _, create, owner_headers, _ = conversation_client
    response = client.patch(f"/conversations/{create()}", headers=owner_headers, json={"title": "   "})
    assert response.status_code == 422
