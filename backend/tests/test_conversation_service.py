"""
Tests for Checkpoint 2: Conversation Service.

Verifies all required service-layer operations:
1. Conversation creation for existing user
2. Conversation creation with title
3. Conversation creation with null/omitted title
4. Conversation ownership verification
5. Retrieve conversation belonging to user
6. User cannot retrieve another user's conversation (IDOR defense)
7. User receives only their own conversations in listing
8. Conversations are deterministically ordered (updated_at desc, created_at desc)
9. Listing conversations does not eager-load messages
10. Add valid user message
11. Add valid assistant message
12. Message attached to correct conversation
13. Adding message explicitly updates conversation.updated_at
14. Invalid role is rejected (InvalidMessageRoleError)
15. Null/invalid content is rejected (InvalidMessageContentError) without mutation
16. Retrieve messages in chronological order (oldest -> newest)
17. Multiple conversations remain isolated
18. User cannot retrieve another user's messages
19. User cannot add message to another user's conversation
20. User cannot delete another user's conversation
21. Delete owned conversation successfully
22. Cascade deletion removes associated messages
23. User cannot delete another user's conversation (ownership enforced)
24. Non-existent conversation raises ConversationNotFoundError
25. Non-existent user raises UserNotFoundError
26. Empty conversation returns empty message list rather than failing
27. Persistence survives session close and reopen
"""

import time
import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import Conversation, Message, User
from app.services.conversation_service import (
    ConversationNotFoundError,
    ConversationOwnershipError,
    ConversationService,
    InvalidMessageContentError,
    InvalidMessageRoleError,
    UserNotFoundError,
    conversation_service,
)


@pytest.fixture
def db_session():
    """Provides a database session cleaned up after tests."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def primary_user(db_session: Session):
    """Creates a primary test user."""
    user = User(
        id=uuid.uuid4(),
        email=f"user_a_{uuid.uuid4().hex[:8]}@example.com",
        full_name="User Alpha",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    yield user
    # Teardown
    cleanup_session = SessionLocal()
    try:
        u = cleanup_session.query(User).filter(User.id == user.id).first()
        if u:
            cleanup_session.delete(u)
            cleanup_session.commit()
    finally:
        cleanup_session.close()


@pytest.fixture
def secondary_user(db_session: Session):
    """Creates a secondary test user for cross-user security tests."""
    user = User(
        id=uuid.uuid4(),
        email=f"user_b_{uuid.uuid4().hex[:8]}@example.com",
        full_name="User Beta",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    yield user
    # Teardown
    cleanup_session = SessionLocal()
    try:
        u = cleanup_session.query(User).filter(User.id == user.id).first()
        if u:
            cleanup_session.delete(u)
            cleanup_session.commit()
    finally:
        cleanup_session.close()


# ====================================================================
# 1-4. Conversation Creation
# ====================================================================

def test_create_conversation_for_existing_user(db_session: Session, primary_user: User):
    """1. Create conversation for existing user."""
    conv = conversation_service.create_conversation(db_session, user_id=primary_user.id)
    assert conv is not None
    assert conv.id is not None
    assert conv.user_id == primary_user.id
    assert conv.title is None
    assert conv.created_at is not None
    assert conv.updated_at is not None


def test_create_conversation_with_title(db_session: Session, primary_user: User):
    """2. Create conversation with explicit title."""
    title = "Backend Architecture Roadmap Discussion"
    conv = conversation_service.create_conversation(db_session, user_id=primary_user.id, title=title)
    assert conv.title == title


def test_create_conversation_with_null_title(db_session: Session, primary_user: User):
    """3. Create conversation with null or whitespace-only title."""
    conv_none = conversation_service.create_conversation(db_session, user_id=primary_user.id, title=None)
    assert conv_none.title is None

    conv_whitespace = conversation_service.create_conversation(db_session, user_id=primary_user.id, title="   ")
    assert conv_whitespace.title is None


def test_create_conversation_verifies_ownership(db_session: Session, primary_user: User):
    """4. Verify created conversation belongs to the user and is queryable."""
    conv = conversation_service.create_conversation(db_session, user_id=primary_user.id, title="Ownership Test")
    fetched = conversation_service.get_conversation(db_session, conversation_id=conv.id, user_id=primary_user.id)
    assert fetched.user_id == primary_user.id
    assert fetched.id == conv.id


# ====================================================================
# 5-6. Conversation Retrieval & IDOR Defense
# ====================================================================

def test_get_conversation_belonging_to_user(db_session: Session, primary_user: User):
    """5. Retrieve conversation belonging to user."""
    conv = conversation_service.create_conversation(db_session, user_id=primary_user.id, title="Retrieve Test")
    retrieved = conversation_service.get_conversation(db_session, conversation_id=conv.id, user_id=primary_user.id)
    assert retrieved.id == conv.id
    assert retrieved.title == "Retrieve Test"


def test_user_cannot_retrieve_another_users_conversation(
    db_session: Session, primary_user: User, secondary_user: User
):
    """6. User cannot retrieve another user's conversation (IDOR prevention)."""
    conv_a = conversation_service.create_conversation(db_session, user_id=primary_user.id, title="Private Conv A")

    # User B attempts to access User A's conversation
    with pytest.raises(ConversationNotFoundError):
        conversation_service.get_conversation(db_session, conversation_id=conv_a.id, user_id=secondary_user.id)


# ====================================================================
# 7-9. Conversation Listing
# ====================================================================

def test_list_conversations_returns_only_own_conversations(
    db_session: Session, primary_user: User, secondary_user: User
):
    """7. User receives only their own conversations."""
    conv1 = conversation_service.create_conversation(db_session, user_id=primary_user.id, title="A's 1")
    conv2 = conversation_service.create_conversation(db_session, user_id=primary_user.id, title="A's 2")
    conv_b = conversation_service.create_conversation(db_session, user_id=secondary_user.id, title="B's 1")

    user_a_convs = conversation_service.list_conversations(db_session, user_id=primary_user.id)
    user_a_ids = [c.id for c in user_a_convs]

    assert conv1.id in user_a_ids
    assert conv2.id in user_a_ids
    assert conv_b.id not in user_a_ids

    user_b_convs = conversation_service.list_conversations(db_session, user_id=secondary_user.id)
    user_b_ids = [c.id for c in user_b_convs]

    assert conv_b.id in user_b_ids
    assert conv1.id not in user_b_ids
    assert conv2.id not in user_b_ids


def test_list_conversations_deterministic_ordering(db_session: Session, primary_user: User):
    """8. Conversations are deterministically ordered: most recently updated first."""
    conv1 = conversation_service.create_conversation(db_session, user_id=primary_user.id, title="First")
    conv2 = conversation_service.create_conversation(db_session, user_id=primary_user.id, title="Second")
    conv3 = conversation_service.create_conversation(db_session, user_id=primary_user.id, title="Third")

    # Add a message to conv1 to make it the most recently updated
    time.sleep(0.01)
    conversation_service.add_message(db_session, conversation_id=conv1.id, user_id=primary_user.id, role="user", content="Ping")

    convs = conversation_service.list_conversations(db_session, user_id=primary_user.id)
    # conv1 should now be first because its updated_at was bumped
    assert convs[0].id == conv1.id


def test_list_conversations_does_not_load_messages_unnecessarily(db_session: Session, primary_user: User):
    """9. Listing conversations only retrieves metadata without eager-loading messages."""
    conv = conversation_service.create_conversation(db_session, user_id=primary_user.id, title="Lazy Check")
    conversation_service.add_message(db_session, conversation_id=conv.id, user_id=primary_user.id, role="user", content="Message 1")

    # Clear session to ensure fresh state
    db_session.expire_all()

    convs = conversation_service.list_conversations(db_session, user_id=primary_user.id)
    found_conv = next(c for c in convs if c.id == conv.id)

    # Verify that the 'messages' relationship attribute remains unloaded (lazy)
    conv_state = inspect(found_conv)
    assert "messages" in conv_state.unloaded


# ====================================================================
# 10-15. Message Creation
# ====================================================================

def test_add_valid_user_message(db_session: Session, primary_user: User):
    """10. Add valid user message."""
    conv = conversation_service.create_conversation(db_session, user_id=primary_user.id)
    msg = conversation_service.add_message(
        db_session,
        conversation_id=conv.id,
        user_id=primary_user.id,
        role="user",
        content="What is Python async?",
    )
    assert msg.id is not None
    assert msg.conversation_id == conv.id
    assert msg.role == "user"
    assert msg.content == "What is Python async?"
    assert msg.created_at is not None


def test_add_valid_assistant_message(db_session: Session, primary_user: User):
    """11. Add valid assistant message."""
    conv = conversation_service.create_conversation(db_session, user_id=primary_user.id)
    msg = conversation_service.add_message(
        db_session,
        conversation_id=conv.id,
        user_id=primary_user.id,
        role="assistant",
        content="Python async uses an event loop to run cooperative tasks.",
    )
    assert msg.role == "assistant"
    assert msg.content == "Python async uses an event loop to run cooperative tasks."


def test_message_attached_to_correct_conversation(db_session: Session, primary_user: User):
    """12. Message is attached to the correct conversation."""
    conv1 = conversation_service.create_conversation(db_session, user_id=primary_user.id)
    conv2 = conversation_service.create_conversation(db_session, user_id=primary_user.id)

    msg = conversation_service.add_message(
        db_session,
        conversation_id=conv1.id,
        user_id=primary_user.id,
        role="user",
        content="Attached to Conv 1",
    )
    assert msg.conversation_id == conv1.id
    assert msg.conversation_id != conv2.id


def test_add_message_updates_conversation_updated_at(db_session: Session, primary_user: User):
    """13. Adding a message updates conversation.updated_at to reflect activity."""
    conv = conversation_service.create_conversation(db_session, user_id=primary_user.id)
    initial_updated_at = conv.updated_at

    time.sleep(0.01)
    msg = conversation_service.add_message(
        db_session,
        conversation_id=conv.id,
        user_id=primary_user.id,
        role="user",
        content="Testing activity bump",
    )

    db_session.refresh(conv)
    assert conv.updated_at > initial_updated_at
    assert conv.updated_at == msg.created_at


def test_invalid_role_rejected(db_session: Session, primary_user: User):
    """14. Invalid roles (e.g. system, bot, admin) are rejected with InvalidMessageRoleError."""
    conv = conversation_service.create_conversation(db_session, user_id=primary_user.id)

    for invalid_role in ["system", "bot", "tool", "admin", "", "unknown"]:
        with pytest.raises(InvalidMessageRoleError):
            conversation_service.add_message(
                db_session,
                conversation_id=conv.id,
                user_id=primary_user.id,
                role=invalid_role,
                content="Some content",
            )


def test_null_content_rejected_and_not_mutated(db_session: Session, primary_user: User):
    """15. Null or non-string content is rejected; valid content is preserved verbatim."""
    conv = conversation_service.create_conversation(db_session, user_id=primary_user.id)

    with pytest.raises(InvalidMessageContentError):
        conversation_service.add_message(
            db_session,
            conversation_id=conv.id,
            user_id=primary_user.id,
            role="user",
            content=None,
        )

    # Content with leading/trailing spaces must NOT be silently stripped
    raw_content = "   untrimmed message text   \n"
    msg = conversation_service.add_message(
        db_session,
        conversation_id=conv.id,
        user_id=primary_user.id,
        role="user",
        content=raw_content,
    )
    assert msg.content == raw_content


# ====================================================================
# 16-18. History Retrieval
# ====================================================================

def test_get_messages_chronological_order(db_session: Session, primary_user: User):
    """16. Retrieve messages in chronological order (oldest -> newest)."""
    conv = conversation_service.create_conversation(db_session, user_id=primary_user.id)

    m1 = conversation_service.add_message(db_session, conv.id, primary_user.id, "user", "Message 1")
    time.sleep(0.01)
    m2 = conversation_service.add_message(db_session, conv.id, primary_user.id, "assistant", "Message 2")
    time.sleep(0.01)
    m3 = conversation_service.add_message(db_session, conv.id, primary_user.id, "user", "Message 3")

    history = conversation_service.get_messages(db_session, conversation_id=conv.id, user_id=primary_user.id)

    assert len(history) == 3
    assert [m.id for m in history] == [m1.id, m2.id, m3.id]
    assert history[0].created_at <= history[1].created_at <= history[2].created_at

    # Alias check
    alias_history = conversation_service.get_history(db_session, conversation_id=conv.id, user_id=primary_user.id)
    assert [m.id for m in alias_history] == [m1.id, m2.id, m3.id]


def test_multiple_conversations_messages_isolated(db_session: Session, primary_user: User):
    """17. Multiple conversations remain isolated."""
    conv1 = conversation_service.create_conversation(db_session, user_id=primary_user.id)
    conv2 = conversation_service.create_conversation(db_session, user_id=primary_user.id)

    conversation_service.add_message(db_session, conv1.id, primary_user.id, "user", "Conv1 Msg")
    conversation_service.add_message(db_session, conv2.id, primary_user.id, "user", "Conv2 Msg")

    msgs1 = conversation_service.get_messages(db_session, conv1.id, primary_user.id)
    msgs2 = conversation_service.get_messages(db_session, conv2.id, primary_user.id)

    assert len(msgs1) == 1
    assert msgs1[0].content == "Conv1 Msg"
    assert len(msgs2) == 1
    assert msgs2[0].content == "Conv2 Msg"


def test_user_cannot_retrieve_another_users_messages(
    db_session: Session, primary_user: User, secondary_user: User
):
    """18. User cannot retrieve another user's messages."""
    conv_a = conversation_service.create_conversation(db_session, user_id=primary_user.id)
    conversation_service.add_message(db_session, conv_a.id, primary_user.id, "user", "Secret")

    with pytest.raises(ConversationNotFoundError):
        conversation_service.get_messages(db_session, conversation_id=conv_a.id, user_id=secondary_user.id)


# ====================================================================
# 19-20. Message Ownership / Security
# ====================================================================

def test_user_cannot_add_message_to_another_users_conversation(
    db_session: Session, primary_user: User, secondary_user: User
):
    """19. User cannot add a message to another user's conversation."""
    conv_a = conversation_service.create_conversation(db_session, user_id=primary_user.id)

    with pytest.raises(ConversationNotFoundError):
        conversation_service.add_message(
            db_session,
            conversation_id=conv_a.id,
            user_id=secondary_user.id,
            role="user",
            content="Injected message",
        )


def test_user_cannot_delete_another_users_conversation(
    db_session: Session, primary_user: User, secondary_user: User
):
    """20 & 23. User cannot delete another user's conversation."""
    conv_a = conversation_service.create_conversation(db_session, user_id=primary_user.id)

    with pytest.raises(ConversationNotFoundError):
        conversation_service.delete_conversation(
            db_session,
            conversation_id=conv_a.id,
            user_id=secondary_user.id,
        )

    # Verify conversation still exists under User A
    assert conversation_service.get_conversation(db_session, conv_a.id, primary_user.id) is not None


# ====================================================================
# 21-23. Deletion & Cascade
# ====================================================================

def test_delete_owned_conversation_successfully(db_session: Session, primary_user: User):
    """21. Delete owned conversation successfully."""
    conv = conversation_service.create_conversation(db_session, user_id=primary_user.id, title="To Delete")
    result = conversation_service.delete_conversation(db_session, conversation_id=conv.id, user_id=primary_user.id)

    assert result is True
    with pytest.raises(ConversationNotFoundError):
        conversation_service.get_conversation(db_session, conversation_id=conv.id, user_id=primary_user.id)


def test_delete_conversation_cascades_and_removes_messages(db_session: Session, primary_user: User):
    """22. Associated messages are removed through cascade upon conversation deletion."""
    conv = conversation_service.create_conversation(db_session, user_id=primary_user.id)
    msg1 = conversation_service.add_message(db_session, conv.id, primary_user.id, "user", "Message 1")
    msg2 = conversation_service.add_message(db_session, conv.id, primary_user.id, "assistant", "Message 2")

    msg1_id = msg1.id
    msg2_id = msg2.id

    conversation_service.delete_conversation(db_session, conversation_id=conv.id, user_id=primary_user.id)

    # Messages must no longer exist in the database
    assert db_session.query(Message).filter(Message.id == msg1_id).first() is None
    assert db_session.query(Message).filter(Message.id == msg2_id).first() is None


# ====================================================================
# 24-27. Edge Cases & Persistence Durability
# ====================================================================

def test_nonexistent_conversation_raises_not_found(db_session: Session, primary_user: User):
    """24. Non-existent conversation follows the service's not-found convention."""
    fake_conv_id = uuid.uuid4()
    with pytest.raises(ConversationNotFoundError):
        conversation_service.get_conversation(db_session, conversation_id=fake_conv_id, user_id=primary_user.id)

    with pytest.raises(ConversationNotFoundError):
        conversation_service.get_messages(db_session, conversation_id=fake_conv_id, user_id=primary_user.id)

    with pytest.raises(ConversationNotFoundError):
        conversation_service.delete_conversation(db_session, conversation_id=fake_conv_id, user_id=primary_user.id)


def test_nonexistent_user_raises_not_found(db_session: Session):
    """25. Non-existent user raises UserNotFoundError."""
    fake_user_id = uuid.uuid4()
    with pytest.raises(UserNotFoundError):
        conversation_service.create_conversation(db_session, user_id=fake_user_id)

    with pytest.raises(UserNotFoundError):
        conversation_service.list_conversations(db_session, user_id=fake_user_id)


def test_empty_conversation_returns_empty_message_list(db_session: Session, primary_user: User):
    """26. Empty conversation returns an empty message list rather than failing."""
    conv = conversation_service.create_conversation(db_session, user_id=primary_user.id)
    messages = conversation_service.get_messages(db_session, conversation_id=conv.id, user_id=primary_user.id)
    assert messages == []


def test_persistence_survives_session_reopen(primary_user: User):
    """27. Conversation and messages survive session close and reopen."""
    # Session 1: Create conversation and messages
    s1 = SessionLocal()
    try:
        conv = conversation_service.create_conversation(s1, user_id=primary_user.id, title="Persisted Topic")
        msg = conversation_service.add_message(s1, conv.id, primary_user.id, "user", "Durable message")
        conv_id = conv.id
        msg_id = msg.id
    finally:
        s1.close()

    # Session 2: Fresh session retrieves the persisted data
    s2 = SessionLocal()
    try:
        reopened_conv = conversation_service.get_conversation(s2, conversation_id=conv_id, user_id=primary_user.id)
        assert reopened_conv.title == "Persisted Topic"

        reopened_msgs = conversation_service.get_messages(s2, conversation_id=conv_id, user_id=primary_user.id)
        assert len(reopened_msgs) == 1
        assert reopened_msgs[0].id == msg_id
        assert reopened_msgs[0].content == "Durable message"
    finally:
        s2.close()
