"""
Phase: Persistent AI Chat History (Checkpoint 1: Database Foundation).

Tests covering the PostgreSQL database foundation for AI chat history:
1. Conversation creation for an existing user
2. Message creation for a conversation
3. Multiple messages belonging to one conversation (chronological ordering)
4. Message isolation across different conversations
5. Bidirectional Conversation <-> User relationships
6. Bidirectional Message <-> Conversation relationships
7. Required NOT NULL fields and CheckConstraint validations (role check)
8. Foreign key integrity enforcement (nonexistent user_id / conversation_id)
9. Cascade deletion (deleting conversation deletes messages without orphans; deleting user cascades)
10. Migration lifecycle and PostgreSQL schema reflection (tables, columns, types, FKs, indexes)
"""

import os
import uuid
import pytest
from datetime import datetime, timezone
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.db.database import SessionLocal, engine
from app.db.models import User, Conversation, Message


@pytest.fixture
def alembic_cfg():
    """Alembic configuration referencing the backend alembic.ini."""
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ini_path = os.path.join(backend_dir, "alembic.ini")
    cfg = Config(ini_path)
    cfg.set_main_option("script_location", os.path.join(backend_dir, "alembic"))
    return cfg


@pytest.fixture
def db_session():
    """Provides a transactional database session rolled back or cleaned up after tests."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def seed_user(db_session):
    """Creates and returns a test user."""
    user = User(
        email=f"chat_test_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Chat Tester",
        target_role="Software Engineer",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ====================================================================
# Schema & Migration Verification Tests
# ====================================================================

def test_alembic_migration_lifecycle(alembic_cfg):
    """Verify that migration 0019 downgrades and re-upgrades cleanly."""
    # Downgrade to 0018
    command.downgrade(alembic_cfg, "0018_milestone_verifications")
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "conversations" not in tables
    assert "messages" not in tables

    # Upgrade back to head (0019)
    command.upgrade(alembic_cfg, "head")
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "conversations" in tables
    assert "messages" in tables


def test_schema_conversations_columns():
    """Verify conversations table columns, types, and nullability."""
    inspector = inspect(engine)
    columns = {col["name"]: col for col in inspector.get_columns("conversations")}

    assert "id" in columns
    assert "user_id" in columns
    assert "title" in columns
    assert "created_at" in columns
    assert "updated_at" in columns

    # Nullability checks
    assert columns["id"]["nullable"] is False
    assert columns["user_id"]["nullable"] is False
    assert columns["title"]["nullable"] is True
    assert columns["created_at"]["nullable"] is False
    assert columns["updated_at"]["nullable"] is False

    # Primary key
    pk = inspector.get_pk_constraint("conversations")
    assert pk["constrained_columns"] == ["id"]

    # Foreign key to users
    fks = inspector.get_foreign_keys("conversations")
    assert any(
        fk["referred_table"] == "users"
        and fk["constrained_columns"] == ["user_id"]
        and fk.get("options", {}).get("ondelete") == "CASCADE"
        for fk in fks
    )

    # Indexes
    indexes = inspector.get_indexes("conversations")
    index_cols = [idx["column_names"] for idx in indexes]
    assert ["user_id"] in index_cols


def test_schema_messages_columns_and_indexes():
    """Verify messages table columns, types, FK, check constraint, and indexes."""
    inspector = inspect(engine)
    columns = {col["name"]: col for col in inspector.get_columns("messages")}

    assert "id" in columns
    assert "conversation_id" in columns
    assert "role" in columns
    assert "content" in columns
    assert "created_at" in columns

    # Nullability checks
    assert columns["id"]["nullable"] is False
    assert columns["conversation_id"]["nullable"] is False
    assert columns["role"]["nullable"] is False
    assert columns["content"]["nullable"] is False
    assert columns["created_at"]["nullable"] is False

    # Primary key
    pk = inspector.get_pk_constraint("messages")
    assert pk["constrained_columns"] == ["id"]

    # Foreign key to conversations
    fks = inspector.get_foreign_keys("messages")
    assert any(
        fk["referred_table"] == "conversations"
        and fk["constrained_columns"] == ["conversation_id"]
        and fk.get("options", {}).get("ondelete") == "CASCADE"
        for fk in fks
    )

    # Indexes: Compound index (conversation_id, created_at) must exist
    indexes = inspector.get_indexes("messages")
    index_cols = [idx["column_names"] for idx in indexes]
    assert ["conversation_id", "created_at"] in index_cols

    # Verify no standalone messages(conversation_id) or messages(created_at) index
    assert ["conversation_id"] not in index_cols
    assert ["created_at"] not in index_cols


# ====================================================================
# Model & Relational Operations Tests
# ====================================================================

def test_create_conversation_for_user(db_session, seed_user):
    """Verify a conversation can be created for an existing user."""
    conv = Conversation(
        user_id=seed_user.id,
        title="Career Advisory Session 1",
    )
    db_session.add(conv)
    db_session.commit()
    db_session.refresh(conv)

    assert conv.id is not None
    assert conv.user_id == seed_user.id
    assert conv.title == "Career Advisory Session 1"
    assert conv.created_at is not None
    assert conv.updated_at is not None

    # Clean up
    db_session.delete(conv)
    db_session.commit()


def test_create_conversation_with_null_title(db_session, seed_user):
    """Verify title is nullable on conversation creation."""
    conv = Conversation(user_id=seed_user.id, title=None)
    db_session.add(conv)
    db_session.commit()
    db_session.refresh(conv)

    assert conv.id is not None
    assert conv.title is None

    # Clean up
    db_session.delete(conv)
    db_session.commit()


def test_create_message_for_conversation(db_session, seed_user):
    """Verify a message can be created for an existing conversation."""
    conv = Conversation(user_id=seed_user.id, title="Test Chat")
    db_session.add(conv)
    db_session.commit()

    msg = Message(
        conversation_id=conv.id,
        role="user",
        content="What skills should I learn for Backend Engineering?",
    )
    db_session.add(msg)
    db_session.commit()
    db_session.refresh(msg)

    assert msg.id is not None
    assert msg.conversation_id == conv.id
    assert msg.role == "user"
    assert msg.content == "What skills should I learn for Backend Engineering?"
    assert msg.created_at is not None

    # Clean up
    db_session.delete(conv)
    db_session.commit()


def test_multiple_messages_in_conversation(db_session, seed_user):
    """Verify multiple messages belong to one conversation in chronological order."""
    conv = Conversation(user_id=seed_user.id, title="Multi-turn conversation")
    db_session.add(conv)
    db_session.commit()

    msg1 = Message(conversation_id=conv.id, role="user", content="Hello!")
    msg2 = Message(conversation_id=conv.id, role="assistant", content="Hello! How can I assist you with your career today?")
    msg3 = Message(conversation_id=conv.id, role="user", content="I want to learn Docker.")
    msg4 = Message(conversation_id=conv.id, role="assistant", content="Docker is a containerization platform...")

    db_session.add_all([msg1, msg2, msg3, msg4])
    db_session.commit()

    # Re-query conversation and check messages relationship
    db_session.refresh(conv)
    assert len(conv.messages) == 4
    assert [m.role for m in conv.messages] == ["user", "assistant", "user", "assistant"]
    assert [m.content for m in conv.messages] == [
        "Hello!",
        "Hello! How can I assist you with your career today?",
        "I want to learn Docker.",
        "Docker is a containerization platform...",
    ]

    # Verify chronological ordering
    for i in range(len(conv.messages) - 1):
        assert conv.messages[i].created_at <= conv.messages[i + 1].created_at

    # Clean up
    db_session.delete(conv)
    db_session.commit()


def test_message_isolation_between_conversations(db_session, seed_user):
    """Verify messages belong strictly to their designated conversation."""
    conv1 = Conversation(user_id=seed_user.id, title="Conversation 1")
    conv2 = Conversation(user_id=seed_user.id, title="Conversation 2")
    db_session.add_all([conv1, conv2])
    db_session.commit()

    msg1 = Message(conversation_id=conv1.id, role="user", content="Msg in conv 1")
    msg2 = Message(conversation_id=conv2.id, role="user", content="Msg in conv 2")
    db_session.add_all([msg1, msg2])
    db_session.commit()

    db_session.refresh(conv1)
    db_session.refresh(conv2)

    assert len(conv1.messages) == 1
    assert conv1.messages[0].content == "Msg in conv 1"

    assert len(conv2.messages) == 1
    assert conv2.messages[0].content == "Msg in conv 2"

    # Clean up
    db_session.delete(conv1)
    db_session.delete(conv2)
    db_session.commit()


def test_conversation_user_relationship(db_session, seed_user):
    """Verify bidirectional User <-> Conversation relationship."""
    conv = Conversation(user_id=seed_user.id, title="Relationship Check")
    db_session.add(conv)
    db_session.commit()

    db_session.refresh(seed_user)
    db_session.refresh(conv)

    # Conversation -> User
    assert conv.user.id == seed_user.id
    assert conv.user.email == seed_user.email

    # User -> Conversations
    user_conv_ids = [c.id for c in seed_user.conversations]
    assert conv.id in user_conv_ids

    # Clean up
    db_session.delete(conv)
    db_session.commit()


def test_message_conversation_relationship(db_session, seed_user):
    """Verify bidirectional Conversation <-> Message relationship."""
    conv = Conversation(user_id=seed_user.id, title="Message Rel Check")
    db_session.add(conv)
    db_session.commit()

    msg = Message(conversation_id=conv.id, role="user", content="Test prompt")
    db_session.add(msg)
    db_session.commit()

    db_session.refresh(conv)
    db_session.refresh(msg)

    # Message -> Conversation
    assert msg.conversation.id == conv.id
    assert msg.conversation.title == "Message Rel Check"

    # Conversation -> Message
    assert msg in conv.messages

    # Clean up
    db_session.delete(conv)
    db_session.commit()


# ====================================================================
# Constraint & Foreign Key Enforcement Tests
# ====================================================================

def test_role_check_constraint_valid(db_session, seed_user):
    """Verify valid roles ('user' and 'assistant') are accepted."""
    conv = Conversation(user_id=seed_user.id, title="Valid Roles")
    db_session.add(conv)
    db_session.commit()

    msg_user = Message(conversation_id=conv.id, role="user", content="From user")
    msg_assistant = Message(conversation_id=conv.id, role="assistant", content="From assistant")
    db_session.add_all([msg_user, msg_assistant])
    db_session.commit()

    assert msg_user.id is not None
    assert msg_assistant.id is not None

    # Clean up
    db_session.delete(conv)
    db_session.commit()


def test_role_check_constraint_invalid(db_session, seed_user):
    """Verify invalid roles (e.g., 'system', 'admin', 'bot') are rejected by check constraint."""
    conv = Conversation(user_id=seed_user.id, title="Invalid Roles")
    db_session.add(conv)
    db_session.commit()

    invalid_msg = Message(conversation_id=conv.id, role="system", content="System instruction")
    db_session.add(invalid_msg)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()

    assert "chk_messages_role" in str(exc_info.value)
    db_session.rollback()

    # Clean up
    db_session.delete(conv)
    db_session.commit()


def test_required_fields_enforced(db_session, seed_user):
    """Verify NOT NULL constraints on conversations and messages."""
    # Conversation without user_id
    conv_no_user = Conversation(user_id=None, title="Missing User")
    db_session.add(conv_no_user)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Message without conversation_id
    msg_no_conv = Message(conversation_id=None, role="user", content="Missing conv")
    db_session.add(msg_no_conv)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Message without role
    valid_conv = Conversation(user_id=seed_user.id, title="Test Conv")
    db_session.add(valid_conv)
    db_session.commit()

    msg_no_role = Message(conversation_id=valid_conv.id, role=None, content="Missing role")
    db_session.add(msg_no_role)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Message without content
    msg_no_content = Message(conversation_id=valid_conv.id, role="user", content=None)
    db_session.add(msg_no_content)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Clean up
    db_session.delete(valid_conv)
    db_session.commit()


def test_foreign_key_integrity(db_session):
    """Verify FK violations for nonexistent user_id or conversation_id."""
    nonexistent_id = uuid.uuid4()

    # Nonexistent user_id
    conv = Conversation(user_id=nonexistent_id, title="Ghost User Conv")
    db_session.add(conv)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Nonexistent conversation_id
    msg = Message(conversation_id=nonexistent_id, role="user", content="Ghost Conv Msg")
    db_session.add(msg)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_cascade_delete_conversation_removes_messages(db_session, seed_user):
    """Verify deleting a conversation cascades and deletes all associated messages."""
    conv = Conversation(user_id=seed_user.id, title="Cascade Delete Test")
    db_session.add(conv)
    db_session.commit()

    msg1 = Message(conversation_id=conv.id, role="user", content="Message 1")
    msg2 = Message(conversation_id=conv.id, role="assistant", content="Message 2")
    db_session.add_all([msg1, msg2])
    db_session.commit()

    conv_id = conv.id
    msg1_id = msg1.id
    msg2_id = msg2.id

    # Delete conversation
    db_session.delete(conv)
    db_session.commit()

    # Verify conversation is gone
    assert db_session.query(Conversation).filter_by(id=conv_id).first() is None

    # Verify messages are gone (no orphaned messages)
    assert db_session.query(Message).filter_by(id=msg1_id).first() is None
    assert db_session.query(Message).filter_by(id=msg2_id).first() is None


def test_cascade_delete_user_removes_conversations_and_messages(db_session):
    """Verify deleting a user cascades to conversations and their messages."""
    temp_user = User(
        email=f"cascade_user_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Cascade User",
    )
    db_session.add(temp_user)
    db_session.commit()

    conv = Conversation(user_id=temp_user.id, title="User Cascade Conv")
    db_session.add(conv)
    db_session.commit()

    msg = Message(conversation_id=conv.id, role="user", content="User cascade message")
    db_session.add(msg)
    db_session.commit()

    user_id = temp_user.id
    conv_id = conv.id
    msg_id = msg.id

    # Delete the user
    db_session.delete(temp_user)
    db_session.commit()

    # Verify user, conversation, and message are all deleted
    assert db_session.query(User).filter_by(id=user_id).first() is None
    assert db_session.query(Conversation).filter_by(id=conv_id).first() is None
    assert db_session.query(Message).filter_by(id=msg_id).first() is None
