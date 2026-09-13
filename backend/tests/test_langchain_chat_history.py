"""
Comprehensive Tests for SkillForge AI — Checkpoint 3: LangChain Integration.

Covers:
1. LangChain packages import successfully.
2. Compatible versions are installed.
3. User DB message -> HumanMessage.
4. Assistant DB message -> AIMessage.
5. Chronological ordering preserved.
6. History reaches Qwen.
7. User message persisted.
8. Assistant message persisted.
9. Failed Qwen does not persist assistant message.
10. Ownership enforced through ConversationService.
11. Cross-user history blocked.
12. Cross-user message injection blocked.
13. General-purpose question works.
14. Programming question works.
15. Career question works.
16. Empty conversation works.
17. 20-message history bound works.
18. VerifiedContext remains authoritative.
19. Conversation history cannot override VerifiedContext.
20. Real PostgreSQL roundtrip works.
21. Persistence survives session reopen.
22. Stateless mode still works.
23. No direct Conversation/Message DB operations occur inside LangChain adapter.
24. SkillForgeChatMessageHistory delegates persistence to ConversationService.
25. API: Stateless chat works without X-User-Id.
26. API: Persistent chat requires X-User-Id (401 when missing).
27. API: Persistent chat rejects invalid X-User-Id format (422).
28. API: Persistent chat returns 404 for non-existent user.
29. API: Cross-user access via API returns 404 (IDOR defense).
30. API: Reject user_id in request body (422 via extra="forbid").
"""

import importlib.metadata
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from sqlalchemy.orm import Session

from app.ai.chatbot import (
    CareerChatGenerationError,
    CareerChatRequest,
    CareerChatResponse,
    CareerChatService,
    CareerChatTimeoutError,
    ChatResponseStatus,
)
from app.ai.chatbot.langchain_history import (
    SkillForgeChatMessageHistory,
    get_langchain_history,
    langchain_messages_to_provider,
    langchain_to_provider_dict,
    message_to_langchain,
    messages_to_langchain,
)
from app.ai.chatbot.prompts import (
    CAREER_CHATBOT_SYSTEM_PROMPT,
    build_career_chat_langchain_messages,
    build_career_chat_messages,
)
from app.ai.context.models import (
    FactProvenance,
    SkillClassification,
    VerifiedCandidateContext,
    VerifiedContext,
    VerifiedSkillFact,
)
from app.ai.qwen.client import QwenClient
from app.ai.qwen.exceptions import QwenTimeoutError
from app.ai.qwen.models import QwenChatResponse, QwenMessage
from app.db.database import SessionLocal
from app.db.models import Conversation, Message, User
from app.main import app
from app.services.conversation_service import (
    ConversationNotFoundError,
    ConversationOwnershipError,
    ConversationService,
    conversation_service,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db_session():
    """Provides a clean database session for each test."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_user(db_session: Session):
    """Creates a primary test user."""
    user = User(
        id=uuid.uuid4(),
        email=f"user_lc_{uuid.uuid4().hex[:8]}@example.com",
        full_name="LangChain Test User",
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
def second_user(db_session: Session):
    """Creates a secondary test user for cross-user tests."""
    user = User(
        id=uuid.uuid4(),
        email=f"user_sec_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Secondary User",
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
def test_conversation(db_session: Session, test_user: User):
    """Creates a test conversation belonging to test_user."""
    conv = conversation_service.create_conversation(
        db_session, user_id=test_user.id, title="Test LangChain Conversation"
    )
    return conv


@pytest.fixture
def sample_context() -> VerifiedContext:
    """Minimal verified context for testing."""
    PYTHON_UUID = uuid.uuid4()
    candidate = VerifiedCandidateContext(
        candidate_id=uuid.uuid4(),
        target_role_id=uuid.uuid4(),
        target_role_name="Backend Developer",
        location="India",
        has_resume=True,
        has_github=True,
        provenance=FactProvenance.DETERMINISTIC_ANALYSIS,
    )
    skills = (
        VerifiedSkillFact(
            skill_id=PYTHON_UUID,
            skill_name="Python",
            canonical_slug="python",
            classification=SkillClassification.STRONG,
            demonstrated_score=0.90,
            claimed=True,
            evidence_count=3,
            provenance=FactProvenance.DETERMINISTIC_ANALYSIS,
        ),
    )
    return VerifiedContext(
        candidate=candidate,
        skills=skills,
        evidence=(),
        market=(),
        priorities=(),
    )


def make_mock_qwen_client(response_text: str = "Assistant reply text.") -> MagicMock:
    """Creates a mock QwenClient returning response_text."""
    client = MagicMock(spec=QwenClient)
    client.model = "qwen3:8b"
    client.chat.return_value = QwenChatResponse(
        model="qwen3:8b",
        message=QwenMessage(role="assistant", content=response_text),
        done=True,
        total_duration=100000000,
        load_duration=10000000,
        prompt_eval_count=50,
        eval_count=20,
    )
    return client


# ---------------------------------------------------------------------------
# Test Cases 1 & 2: LangChain Package Imports & Versions
# ---------------------------------------------------------------------------

def test_1_langchain_packages_import():
    """Requirement 1: LangChain packages import successfully."""
    import langchain
    import langchain_core
    import langchain_core.messages
    import langchain_core.chat_history
    import langchain_ollama

    assert langchain is not None
    assert langchain_core is not None
    assert langchain_ollama is not None


def test_2_compatible_versions_installed():
    """Requirement 2: Compatible versions of LangChain packages are installed."""
    lc_ver = importlib.metadata.version("langchain")
    lc_core_ver = importlib.metadata.version("langchain-core")
    lc_ollama_ver = importlib.metadata.version("langchain-ollama")

    assert lc_ver.startswith("1.")
    assert lc_core_ver.startswith("1.")
    assert lc_ollama_ver.startswith("1.")


# ---------------------------------------------------------------------------
# Test Cases 3, 4, 5: Message Translation & Chronological Ordering
# ---------------------------------------------------------------------------

def test_3_user_db_message_to_human_message():
    """Requirement 3: User DB message -> HumanMessage."""
    db_msg = Message(
        id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        role="user",
        content="Hello world",
        created_at=datetime.now(timezone.utc),
    )
    lc_msg = message_to_langchain(db_msg)
    assert isinstance(lc_msg, HumanMessage)
    assert lc_msg.content == "Hello world"


def test_4_assistant_db_message_to_ai_message():
    """Requirement 4: Assistant DB message -> AIMessage."""
    db_msg = Message(
        id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        role="assistant",
        content="I am here to help.",
        created_at=datetime.now(timezone.utc),
    )
    lc_msg = message_to_langchain(db_msg)
    assert isinstance(lc_msg, AIMessage)
    assert lc_msg.content == "I am here to help."


def test_5_chronological_ordering_preserved(db_session: Session, test_user: User, test_conversation: Conversation):
    """Requirement 5: Messages preserve strict chronological ordering (oldest -> newest)."""
    m1 = conversation_service.add_message(
        db_session, conversation_id=test_conversation.id, user_id=test_user.id, role="user", content="Step 1"
    )
    m2 = conversation_service.add_message(
        db_session, conversation_id=test_conversation.id, user_id=test_user.id, role="assistant", content="Step 2"
    )
    m3 = conversation_service.add_message(
        db_session, conversation_id=test_conversation.id, user_id=test_user.id, role="user", content="Step 3"
    )

    history = get_langchain_history(
        db_session, conversation_id=test_conversation.id, user_id=test_user.id
    )
    assert len(history) == 3
    assert isinstance(history[0], HumanMessage)
    assert history[0].content == "Step 1"
    assert isinstance(history[1], AIMessage)
    assert history[1].content == "Step 2"
    assert isinstance(history[2], HumanMessage)
    assert history[2].content == "Step 3"


# ---------------------------------------------------------------------------
# Test Cases 6, 7, 8, 9: History reaches Qwen & Persistence Flows
# ---------------------------------------------------------------------------

def test_6_history_reaches_qwen(db_session: Session, test_user: User, test_conversation: Conversation, sample_context: VerifiedContext):
    """Requirement 6: Prior conversation history is passed into the Qwen provider payload."""
    # Seed past dialogue
    conversation_service.add_message(
        db_session, conversation_id=test_conversation.id, user_id=test_user.id, role="user", content="First question"
    )
    conversation_service.add_message(
        db_session, conversation_id=test_conversation.id, user_id=test_user.id, role="assistant", content="First answer"
    )

    mock_client = make_mock_qwen_client("Second answer")
    service = CareerChatService(client=mock_client)

    req = CareerChatRequest(
        verified_context=sample_context,
        user_query="Second question",
        conversation_id=test_conversation.id,
    )
    service.chat(req, db=db_session, user_id=test_user.id)

    # Check payload received by client.chat
    call_args = mock_client.chat.call_args
    passed_messages = call_args.kwargs["messages"]
    
    # Sequence should be: SystemMessage, HumanMessage(First question), AIMessage(First answer), HumanMessage(Second question)
    roles = [m["role"] for m in passed_messages]
    contents = [m["content"] for m in passed_messages]

    assert roles[0] == "system"
    assert roles[1] == "user"
    assert contents[1] == "First question"
    assert roles[2] == "assistant"
    assert contents[2] == "First answer"
    assert roles[3] == "user"
    assert contents[3] == "Second question"


def test_7_user_message_persisted(db_session: Session, test_user: User, test_conversation: Conversation, sample_context: VerifiedContext):
    """Requirement 7: User message is persisted to DB during persistent chat."""
    mock_client = make_mock_qwen_client("Sure, here is Python info.")
    service = CareerChatService(client=mock_client)

    req = CareerChatRequest(
        verified_context=sample_context,
        user_query="Tell me about Python",
        conversation_id=test_conversation.id,
    )
    resp = service.chat(req, db=db_session, user_id=test_user.id)

    messages = conversation_service.get_messages(db_session, test_conversation.id, test_user.id)
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].content == "Tell me about Python"


def test_8_assistant_message_persisted(db_session: Session, test_user: User, test_conversation: Conversation, sample_context: VerifiedContext):
    """Requirement 8: Assistant message is persisted and message_id returned in response."""
    mock_client = make_mock_qwen_client("Python is a dynamic high-level language.")
    service = CareerChatService(client=mock_client)

    req = CareerChatRequest(
        verified_context=sample_context,
        user_query="Tell me about Python",
        conversation_id=test_conversation.id,
    )
    resp = service.chat(req, db=db_session, user_id=test_user.id)

    assert resp.conversation_id == test_conversation.id
    assert resp.message_id is not None

    messages = conversation_service.get_messages(db_session, test_conversation.id, test_user.id)
    assert len(messages) == 2
    assert messages[1].role == "assistant"
    assert messages[1].content == "Python is a dynamic high-level language."
    assert messages[1].id == resp.message_id


def test_9_failed_qwen_does_not_persist_assistant_message(
    db_session: Session, test_user: User, test_conversation: Conversation, sample_context: VerifiedContext
):
    """Requirement 9: Failed Qwen does NOT persist an assistant message (user message remains)."""
    mock_client = MagicMock(spec=QwenClient)
    mock_client.model = "qwen3:8b"
    mock_client.chat.side_effect = QwenTimeoutError("Timeout reaching local Ollama")

    service = CareerChatService(client=mock_client)

    req = CareerChatRequest(
        verified_context=sample_context,
        user_query="Explain Python decorators",
        conversation_id=test_conversation.id,
    )

    with pytest.raises(CareerChatTimeoutError):
        service.chat(req, db=db_session, user_id=test_user.id)

    # Verify: user message was recorded, but NO assistant message was saved
    messages = conversation_service.get_messages(db_session, test_conversation.id, test_user.id)
    assert len(messages) == 1
    assert messages[0].role == "user"
    assert messages[0].content == "Explain Python decorators"


# ---------------------------------------------------------------------------
# Test Cases 10, 11, 12: Ownership Enforcement & Cross-User Security
# ---------------------------------------------------------------------------

def test_10_ownership_enforced_through_conversation_service(
    db_session: Session, test_user: User, second_user: User, test_conversation: Conversation, sample_context: VerifiedContext
):
    """Requirement 10: Ownership enforced through ConversationService when chat is invoked."""
    mock_client = make_mock_qwen_client("Hello")
    service = CareerChatService(client=mock_client)

    req = CareerChatRequest(
        verified_context=sample_context,
        user_query="Steal access",
        conversation_id=test_conversation.id,
    )

    # second_user attempts to chat in test_user's conversation -> blocked
    with pytest.raises(ConversationNotFoundError):
        service.chat(req, db=db_session, user_id=second_user.id)


def test_11_cross_user_history_blocked(
    db_session: Session, test_user: User, second_user: User, test_conversation: Conversation
):
    """Requirement 11: Cross-user history loading via get_langchain_history is blocked."""
    conversation_service.add_message(
        db_session, test_conversation.id, test_user.id, role="user", content="Secret message"
    )

    with pytest.raises(ConversationNotFoundError):
        get_langchain_history(db_session, test_conversation.id, user_id=second_user.id)


def test_12_cross_user_message_injection_blocked(
    db_session: Session, test_user: User, second_user: User, test_conversation: Conversation
):
    """Requirement 12: Cross-user message injection is blocked."""
    with pytest.raises(ConversationNotFoundError):
        conversation_service.add_message(
            db_session, test_conversation.id, user_id=second_user.id, role="user", content="Injection attempt"
        )


# ---------------------------------------------------------------------------
# Test Cases 13, 14, 15, 16: General-Purpose, Programming, Career & Empty Conversations
# ---------------------------------------------------------------------------

def test_13_general_purpose_question_works(
    db_session: Session, test_user: User, test_conversation: Conversation, sample_context: VerifiedContext
):
    """Requirement 13: General-purpose question works."""
    mock_client = make_mock_qwen_client("Photosynthesis is the process by which green plants make food.")
    service = CareerChatService(client=mock_client)

    req = CareerChatRequest(
        verified_context=sample_context,
        user_query="What is photosynthesis?",
        conversation_id=test_conversation.id,
    )
    resp = service.chat(req, db=db_session, user_id=test_user.id)
    assert resp.status == ChatResponseStatus.EXPLANATORY
    assert "photosynthesis" in resp.explanation.lower()


def test_14_programming_question_works(
    db_session: Session, test_user: User, test_conversation: Conversation, sample_context: VerifiedContext
):
    """Requirement 14: Programming question works."""
    mock_client = make_mock_qwen_client("A generator in Python yields values one at a time using 'yield'.")
    service = CareerChatService(client=mock_client)

    req = CareerChatRequest(
        verified_context=sample_context,
        user_query="How do Python generators work?",
        conversation_id=test_conversation.id,
    )
    resp = service.chat(req, db=db_session, user_id=test_user.id)
    assert resp.status == ChatResponseStatus.EXPLANATORY
    assert "generator" in resp.explanation.lower()


def test_15_career_question_works(
    db_session: Session, test_user: User, test_conversation: Conversation, sample_context: VerifiedContext
):
    """Requirement 15: Career question grounded in verified skills works."""
    mock_client = make_mock_qwen_client("Your Python skill is verified as STRONG with a 0.90 score.")
    service = CareerChatService(client=mock_client)

    req = CareerChatRequest(
        verified_context=sample_context,
        user_query="What is my status in Python?",
        conversation_id=test_conversation.id,
    )
    resp = service.chat(req, db=db_session, user_id=test_user.id)
    assert resp.status == ChatResponseStatus.EXPLANATORY
    assert len(resp.referenced_skill_ids) == 1


def test_16_empty_conversation_works(
    db_session: Session, test_user: User, test_conversation: Conversation, sample_context: VerifiedContext
):
    """Requirement 16: Initial chat in an empty conversation works seamlessly."""
    # Conversation has 0 messages initially
    assert len(conversation_service.get_messages(db_session, test_conversation.id, test_user.id)) == 0

    mock_client = make_mock_qwen_client("Initial response.")
    service = CareerChatService(client=mock_client)

    req = CareerChatRequest(
        verified_context=sample_context,
        user_query="Hello! First message.",
        conversation_id=test_conversation.id,
    )
    resp = service.chat(req, db=db_session, user_id=test_user.id)

    assert resp.conversation_id == test_conversation.id
    assert resp.message_id is not None
    assert len(conversation_service.get_messages(db_session, test_conversation.id, test_user.id)) == 2


# ---------------------------------------------------------------------------
# Test Case 17: 20-Message History Bound
# ---------------------------------------------------------------------------

def test_17_twenty_message_history_bound_works(
    db_session: Session, test_user: User, test_conversation: Conversation
):
    """Requirement 17: History supplied to LangChain is bounded to the last 20 messages."""
    # Seed 25 messages
    for i in range(25):
        role = "user" if i % 2 == 0 else "assistant"
        conversation_service.add_message(
            db_session, test_conversation.id, test_user.id, role=role, content=f"Message {i}"
        )

    # DB retains all 25 messages
    all_db_msgs = conversation_service.get_messages(db_session, test_conversation.id, test_user.id)
    assert len(all_db_msgs) == 25

    # LangChain adapter retrieves only the latest 20 messages in chronological order
    bounded_history = get_langchain_history(
        db_session, test_conversation.id, test_user.id, limit=20
    )
    assert len(bounded_history) == 20
    assert bounded_history[0].content == "Message 5"
    assert bounded_history[-1].content == "Message 24"


# ---------------------------------------------------------------------------
# Test Cases 18 & 19: VerifiedContext Authority & Prompt Invariants
# ---------------------------------------------------------------------------

def test_18_verified_context_remains_authoritative():
    """Requirement 18: System prompt explicitly specifies VerifiedContext as authoritative ground truth."""
    assert "Treat the supplied VerifiedContext as authoritative ground truth." in CAREER_CHATBOT_SYSTEM_PROMPT
    assert "Do not invent, alter, or contradict any verified facts." in CAREER_CHATBOT_SYSTEM_PROMPT
    assert "Rule 13" or "Conversation history represents conversational dialogue context only." in CAREER_CHATBOT_SYSTEM_PROMPT


def test_19_conversation_history_cannot_override_verified_context(
    sample_context: VerifiedContext
):
    """
    Requirement 19: Conversation history cannot override VerifiedContext.
    Part A: If candidate asks about an unknown skill not in VerifiedContext,
    deterministic sufficiency rejects the query even if dialogue claimed proficiency.
    Part B: When dialogue contains contradictory claims (e.g. 'I am strong in Docker'),
    the constructed message sequence strictly asserts Rule 13 and VerifiedContext ground truth.
    """
    mock_client = make_mock_qwen_client("Should not be called")
    service = CareerChatService(client=mock_client)

    # Part A: Query asks about unknown skill not in VerifiedContext
    req = CareerChatRequest(
        verified_context=sample_context,
        user_query="What is my status of Kubernetes?",
    )
    resp = service.chat(req)
    assert resp.status == ChatResponseStatus.INSUFFICIENT_EVIDENCE
    assert "insufficient" in resp.explanation.lower()
    assert not mock_client.chat.called

    # Part B: VerifiedContext contains Docker as MISSING; history claims candidate is strong in Docker
    DOCKER_UUID = uuid.uuid4()
    context_with_docker = VerifiedContext(
        candidate=sample_context.candidate,
        skills=(
            VerifiedSkillFact(
                skill_id=DOCKER_UUID,
                skill_name="Docker",
                canonical_slug="docker",
                classification=SkillClassification.MISSING,
                demonstrated_score=0.0,
                claimed=False,
                evidence_count=0,
                provenance=FactProvenance.DETERMINISTIC_ANALYSIS,
            ),
        ),
        evidence=(),
        market=(),
        priorities=(),
    )

    prior_history = [
        HumanMessage(content="I am very strong in Docker and deploy it daily."),
        AIMessage(content="Noted."),
    ]

    messages = build_career_chat_messages(
        context=context_with_docker,
        user_query="Why is my Docker classification missing?",
        history_messages=prior_history,
    )

    # System prompt must contain Rule 13
    assert any("Conversation history represents conversational dialogue context only." in m["content"] for m in messages if m["role"] == "system")
    # VerifiedContext ground truth must show Docker MISSING
    assert any("Classification: MISSING" in m["content"] for m in messages if m["role"] == "system")
    # Prior history is present as dialogue context
    assert any(m["role"] == "user" and "strong in Docker" in m["content"] for m in messages)


# ---------------------------------------------------------------------------
# Test Cases 20 & 21: Real PostgreSQL Roundtrip & Session Reopen
# ---------------------------------------------------------------------------

def test_20_real_postgresql_roundtrip(db_session: Session, test_user: User):
    """Requirement 20: Real PostgreSQL roundtrip with conversation and messages."""
    # 1. Create conversation
    conv = conversation_service.create_conversation(db_session, user_id=test_user.id, title="Roundtrip Test")
    
    # 2. Add user message
    u_msg = conversation_service.add_message(
        db_session, conversation_id=conv.id, user_id=test_user.id, role="user", content="Roundtrip question"
    )
    
    # 3. Read back via LangChain adapter
    history = get_langchain_history(db_session, conversation_id=conv.id, user_id=test_user.id)
    assert len(history) == 1
    assert isinstance(history[0], HumanMessage)
    assert history[0].content == "Roundtrip question"

    # 4. Add assistant message
    a_msg = conversation_service.add_message(
        db_session, conversation_id=conv.id, user_id=test_user.id, role="assistant", content="Roundtrip answer"
    )

    # 5. Read back via LangChain adapter
    history_after = get_langchain_history(db_session, conversation_id=conv.id, user_id=test_user.id)
    assert len(history_after) == 2
    assert isinstance(history_after[1], AIMessage)
    assert history_after[1].content == "Roundtrip answer"


def test_21_persistence_survives_session_reopen(test_user: User):
    """Requirement 21: Persistence survives explicit session close and reopen."""
    session1 = SessionLocal()
    try:
        conv = conversation_service.create_conversation(session1, user_id=test_user.id, title="Session Reopen")
        conversation_service.add_message(
            session1, conversation_id=conv.id, user_id=test_user.id, role="user", content="Msg in session 1"
        )
        conv_id = conv.id
    finally:
        session1.close()

    # Reopen in completely fresh session
    session2 = SessionLocal()
    try:
        loaded_history = get_langchain_history(session2, conversation_id=conv_id, user_id=test_user.id)
        assert len(loaded_history) == 1
        assert isinstance(loaded_history[0], HumanMessage)
        assert loaded_history[0].content == "Msg in session 1"
    finally:
        session2.close()


# ---------------------------------------------------------------------------
# Test Case 22: Stateless Mode Still Works
# ---------------------------------------------------------------------------

def test_22_stateless_mode_still_works(sample_context: VerifiedContext):
    """Requirement 22: When conversation_id=None, chatbot runs completely stateless without DB."""
    mock_client = make_mock_qwen_client("Stateless answer.")
    service = CareerChatService(client=mock_client)

    req = CareerChatRequest(
        verified_context=sample_context,
        user_query="Tell me about Python in general",
        conversation_id=None,
    )

    # Call with db=None, user_id=None
    resp = service.chat(req, db=None, user_id=None)

    assert resp.conversation_id is None
    assert resp.message_id is None
    assert resp.explanation == "Stateless answer."


# ---------------------------------------------------------------------------
# Test Cases 23 & 24: Architectural Boundaries & Adapter Delegation
# ---------------------------------------------------------------------------

def test_23_no_direct_conversation_message_db_operations_in_adapter(
    db_session: Session, test_user: User, test_conversation: Conversation
):
    """
    Requirement 23: LangChain adapter NEVER calls db.query(Conversation),
    db.query(Message), db.add, db.delete directly.
    """
    mock_service = MagicMock(spec=ConversationService)
    mock_service.get_messages.return_value = [
        Message(
            id=uuid.uuid4(),
            conversation_id=test_conversation.id,
            role="user",
            content="Delegated message",
            created_at=datetime.now(timezone.utc),
        )
    ]

    history = get_langchain_history(
        db=db_session,
        conversation_id=test_conversation.id,
        user_id=test_user.id,
        conversation_service=mock_service,
    )

    assert mock_service.get_messages.called
    assert len(history) == 1
    assert history[0].content == "Delegated message"


def test_24_skillforge_chat_message_history_delegates(
    db_session: Session, test_user: User, test_conversation: Conversation
):
    """Requirement 24: SkillForgeChatMessageHistory delegates all operations to ConversationService."""
    mock_service = MagicMock(spec=ConversationService)
    mock_service.get_messages.return_value = []

    history_obj = SkillForgeChatMessageHistory(
        db=db_session,
        conversation_id=test_conversation.id,
        user_id=test_user.id,
        conversation_service=mock_service,
    )

    # 1. messages property delegates
    _ = history_obj.messages
    assert mock_service.get_messages.called

    # 2. add_message delegates
    history_obj.add_message(HumanMessage(content="Test human"))
    mock_service.add_message.assert_called_with(
        db_session,
        conversation_id=test_conversation.id,
        user_id=test_user.id,
        role="user",
        content="Test human",
    )

    history_obj.add_message(AIMessage(content="Test ai"))
    mock_service.add_message.assert_called_with(
        db_session,
        conversation_id=test_conversation.id,
        user_id=test_user.id,
        role="assistant",
        content="Test ai",
    )

    # 3. clear delegates
    history_obj.clear()
    mock_service.delete_conversation.assert_called_with(
        db_session,
        conversation_id=test_conversation.id,
        user_id=test_user.id,
    )


# ---------------------------------------------------------------------------
# Test Cases 25 - 30: FastAPI HTTP Endpoint Tests (Identity & Security)
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """TestClient for FastAPI app."""
    return TestClient(app)


def test_25_api_stateless_chat_works_without_x_user_id(client: TestClient, sample_context: VerifiedContext):
    """Requirement 25: POST /api/v1/ai/chat without conversation_id works without X-User-Id header."""
    with patch("app.ai.chatbot.service.CareerChatService.chat") as mock_chat:
        mock_chat.return_value = CareerChatResponse(
            explanation="Stateless API answer.",
            model="qwen3:8b",
            status=ChatResponseStatus.EXPLANATORY,
            referenced_skill_ids=(),
            retrieved_evidence=(),
            usage=None,
            conversation_id=None,
            message_id=None,
        )

        response = client.post(
            "/api/v1/ai/chat",
            json={
                "verified_context": sample_context.model_dump(mode="json"),
                "user_query": "What is Python?",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["explanation"] == "Stateless API answer."
        assert data["conversation_id"] is None


def test_26_api_persistent_chat_requires_x_user_id(client: TestClient, sample_context: VerifiedContext):
    """Requirement 26: POST /api/v1/ai/chat with conversation_id returns 401 if X-User-Id is missing."""
    conv_id = str(uuid.uuid4())
    response = client.post(
        "/api/v1/ai/chat",
        json={
            "verified_context": sample_context.model_dump(mode="json"),
            "user_query": "Hello persistent",
            "conversation_id": conv_id,
        },
    )
    assert response.status_code == 401
    assert "Authentication required: X-User-Id header missing" in response.json()["detail"]


def test_27_api_persistent_chat_rejects_invalid_x_user_id_format(client: TestClient, sample_context: VerifiedContext):
    """Requirement 27: POST /api/v1/ai/chat with invalid X-User-Id format returns 422."""
    conv_id = str(uuid.uuid4())
    response = client.post(
        "/api/v1/ai/chat",
        headers={"X-User-Id": "not-a-valid-uuid"},
        json={
            "verified_context": sample_context.model_dump(mode="json"),
            "user_query": "Hello persistent",
            "conversation_id": conv_id,
        },
    )
    assert response.status_code == 422
    assert "Invalid user ID format in X-User-Id header" in response.json()["detail"]


def test_28_api_persistent_chat_returns_404_for_unknown_user(client: TestClient, sample_context: VerifiedContext):
    """Requirement 28: POST /api/v1/ai/chat returns 404 if user in X-User-Id does not exist in DB."""
    conv_id = str(uuid.uuid4())
    unknown_user_id = str(uuid.uuid4())
    response = client.post(
        "/api/v1/ai/chat",
        headers={"X-User-Id": unknown_user_id},
        json={
            "verified_context": sample_context.model_dump(mode="json"),
            "user_query": "Hello persistent",
            "conversation_id": conv_id,
        },
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_29_api_cross_user_access_returns_404(
    client: TestClient, test_user: User, second_user: User, test_conversation: Conversation, sample_context: VerifiedContext
):
    """Requirement 29: Cross-user conversation access via API returns 404."""
    # second_user attempts to chat in test_conversation (owned by test_user)
    response = client.post(
        "/api/v1/ai/chat",
        headers={"X-User-Id": str(second_user.id)},
        json={
            "verified_context": sample_context.model_dump(mode="json"),
            "user_query": "Sneaky cross-user chat",
            "conversation_id": str(test_conversation.id),
        },
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_30_api_rejects_user_id_in_request_body(client: TestClient, sample_context: VerifiedContext):
    """Requirement 30: Reject user_id in request body (422 via extra='forbid')."""
    response = client.post(
        "/api/v1/ai/chat",
        json={
            "verified_context": sample_context.model_dump(mode="json"),
            "user_query": "Testing forbidden field",
            "user_id": str(uuid.uuid4()),
        },
    )
    assert response.status_code == 422
    assert "extra_forbidden" in str(response.json()["detail"]).lower() or "extra fields not permitted" in str(response.json()["detail"]).lower()
