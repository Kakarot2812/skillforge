"""
Integration tests for Conversation REST API Endpoints.
Phase: Persistent AI Chat History (Checkpoint 6: Conversation API & Chat History UI).

Tests:
1. list conversations
2. create conversation
3. get messages
4. delete conversation
5. missing X-User-Id (401)
6. malformed UUID in X-User-Id (422)
7. unknown user in X-User-Id (404)
8. cross-user conversation access (404)
9. cross-user message access (404)
10. conversation ordering (updated_at DESC, created_at DESC)
11. message chronological ordering (created_at ASC)
12. cascade deletion behavior through existing service
"""

import uuid
from typing import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import Conversation, Message, User
from app.main import app
from app.services.conversation_service import conversation_service


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Yields a database session for test setup and tear down."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def primary_user(db_session: Session) -> Generator[User, None, None]:
    """Creates a primary candidate user in PostgreSQL."""
    user = User(
        id=uuid.uuid4(),
        email=f"c6_user1_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Primary Candidate",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    yield user

    cleanup = SessionLocal()
    try:
        u = cleanup.query(User).filter(User.id == user.id).first()
        if u:
            cleanup.delete(u)
            cleanup.commit()
    finally:
        cleanup.close()


@pytest.fixture
def secondary_user(db_session: Session) -> Generator[User, None, None]:
    """Creates a secondary candidate user for cross-user tests."""
    user = User(
        id=uuid.uuid4(),
        email=f"c6_user2_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Secondary Candidate",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    yield user

    cleanup = SessionLocal()
    try:
        u = cleanup.query(User).filter(User.id == user.id).first()
        if u:
            cleanup.delete(u)
            cleanup.commit()
    finally:
        cleanup.close()


@pytest.fixture
def client() -> TestClient:
    """Provides a TestClient for making HTTP requests."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# Test Cases 1-4: Basic CRUD Endpoints
# ---------------------------------------------------------------------------

def test_1_create_conversation(client: TestClient, primary_user: User):
    """POST /api/v1/conversations creates a new conversation session."""
    payload = {"title": "Roadmap Strategy Discussion"}
    resp = client.post(
        "/api/v1/conversations",
        json=payload,
        headers={"X-User-Id": str(primary_user.id)},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Roadmap Strategy Discussion"
    assert data["user_id"] == str(primary_user.id)
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_2_create_conversation_with_null_or_empty_title(client: TestClient, primary_user: User):
    """POST /api/v1/conversations with null or missing title."""
    resp = client.post(
        "/api/v1/conversations",
        json={},
        headers={"X-User-Id": str(primary_user.id)},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] is None
    assert data["user_id"] == str(primary_user.id)


def test_3_list_conversations(client: TestClient, primary_user: User, db_session: Session):
    """GET /api/v1/conversations lists only the authenticated user's conversations."""
    conv1 = conversation_service.create_conversation(db_session, primary_user.id, title="Conv 1")
    conv2 = conversation_service.create_conversation(db_session, primary_user.id, title="Conv 2")

    resp = client.get(
        "/api/v1/conversations",
        headers={"X-User-Id": str(primary_user.id)},
    )
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 2
    ids = [item["id"] for item in items]
    assert str(conv1.id) in ids
    assert str(conv2.id) in ids


def test_4_get_conversation_messages(client: TestClient, primary_user: User, db_session: Session):
    """GET /api/v1/conversations/{id}/messages retrieves messages for owned conversation."""
    conv = conversation_service.create_conversation(db_session, primary_user.id, title="Chat")
    conversation_service.add_message(db_session, conv.id, primary_user.id, role="user", content="Hello")
    conversation_service.add_message(db_session, conv.id, primary_user.id, role="assistant", content="Hi there")

    resp = client.get(
        f"/api/v1/conversations/{conv.id}/messages",
        headers={"X-User-Id": str(primary_user.id)},
    )
    assert resp.status_code == 200
    messages = resp.json()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hello"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "Hi there"


def test_5_delete_conversation(client: TestClient, primary_user: User, db_session: Session):
    """DELETE /api/v1/conversations/{id} deletes conversation and cascades messages."""
    conv = conversation_service.create_conversation(db_session, primary_user.id, title="To Delete")
    conversation_service.add_message(db_session, conv.id, primary_user.id, role="user", content="Hello")

    resp = client.delete(
        f"/api/v1/conversations/{conv.id}",
        headers={"X-User-Id": str(primary_user.id)},
    )
    assert resp.status_code == 204

    # Verify conversation is deleted from DB
    assert db_session.query(Conversation).filter(Conversation.id == conv.id).first() is None
    # Verify messages were cascaded
    assert db_session.query(Message).filter(Message.conversation_id == conv.id).count() == 0


# ---------------------------------------------------------------------------
# Test Cases 6-8: Authentication & Identity Validation
# ---------------------------------------------------------------------------

def test_6_missing_x_user_id_returns_401(client: TestClient):
    """Request without X-User-Id returns 401 Unauthorized."""
    resp = client.get("/api/v1/conversations")
    assert resp.status_code == 401
    assert "authentication required" in resp.json()["detail"].lower()


def test_7_malformed_uuid_returns_422(client: TestClient):
    """Request with non-UUID in X-User-Id returns 422 Unprocessable Entity."""
    resp = client.get(
        "/api/v1/conversations",
        headers={"X-User-Id": "invalid-not-a-uuid"},
    )
    assert resp.status_code == 422
    assert "invalid user id format" in resp.json()["detail"].lower()


def test_8_unknown_user_returns_404(client: TestClient):
    """Request with valid UUID for non-existent user returns 404 Not Found."""
    random_uuid = str(uuid.uuid4())
    resp = client.get(
        "/api/v1/conversations",
        headers={"X-User-Id": random_uuid},
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Test Cases 9-10: Cross-User Isolation
# ---------------------------------------------------------------------------

def test_9_cross_user_conversation_messages_access_returns_404(
    client: TestClient, primary_user: User, secondary_user: User, db_session: Session
):
    """Secondary user cannot get messages for primary user's conversation (returns 404)."""
    conv = conversation_service.create_conversation(db_session, primary_user.id, title="User 1 Secret")
    conversation_service.add_message(db_session, conv.id, primary_user.id, role="user", content="Secret")

    resp = client.get(
        f"/api/v1/conversations/{conv.id}/messages",
        headers={"X-User-Id": str(secondary_user.id)},
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_10_cross_user_delete_returns_404(
    client: TestClient, primary_user: User, secondary_user: User, db_session: Session
):
    """Secondary user cannot delete primary user's conversation (returns 404)."""
    conv = conversation_service.create_conversation(db_session, primary_user.id, title="User 1 Conv")

    resp = client.delete(
        f"/api/v1/conversations/{conv.id}",
        headers={"X-User-Id": str(secondary_user.id)},
    )
    assert resp.status_code == 404
    # Verify conversation still exists
    assert db_session.query(Conversation).filter(Conversation.id == conv.id).first() is not None


# ---------------------------------------------------------------------------
# Test Cases 11-12: Ordering & Limits
# ---------------------------------------------------------------------------

def test_11_conversation_ordering_updated_at_desc(
    client: TestClient, primary_user: User, db_session: Session
):
    """Conversations are returned ordered by updated_at DESC."""
    conv1 = conversation_service.create_conversation(db_session, primary_user.id, title="Old Conv")
    conv2 = conversation_service.create_conversation(db_session, primary_user.id, title="New Conv")

    # Update conv1 by adding a message
    conversation_service.add_message(db_session, conv1.id, primary_user.id, role="user", content="Activity on Conv 1")

    resp = client.get(
        "/api/v1/conversations",
        headers={"X-User-Id": str(primary_user.id)},
    )
    assert resp.status_code == 200
    items = resp.json()
    # conv1 should be first because its updated_at was updated by add_message
    assert items[0]["id"] == str(conv1.id)


def test_12_messages_chronological_ordering(
    client: TestClient, primary_user: User, db_session: Session
):
    """Messages are strictly returned in created_at ASC chronological order."""
    conv = conversation_service.create_conversation(db_session, primary_user.id, title="Order Check")
    m1 = conversation_service.add_message(db_session, conv.id, primary_user.id, role="user", content="Turn 1")
    m2 = conversation_service.add_message(db_session, conv.id, primary_user.id, role="assistant", content="Turn 2")
    m3 = conversation_service.add_message(db_session, conv.id, primary_user.id, role="user", content="Turn 3")

    resp = client.get(
        f"/api/v1/conversations/{conv.id}/messages",
        headers={"X-User-Id": str(primary_user.id)},
    )
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 3
    assert [item["content"] for item in items] == ["Turn 1", "Turn 2", "Turn 3"]
    assert items[0]["id"] == str(m1.id)
    assert items[1]["id"] == str(m2.id)
    assert items[2]["id"] == str(m3.id)
