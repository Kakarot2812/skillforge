"""
Unit and integration tests for SkillForge AI Checkpoint 5:
Personalized Context Assembly & Qwen Integration.

Strict architectural verification:
1. VerifiedContext remains absolute authoritative ground truth for skills, gaps, and evidence.
2. UserProfile provides non-authoritative personalization context (demographics, preferences).
3. Conversation History provides non-authoritative dialogue context.
4. Profile data (target_role, branch, degree) NEVER becomes verified skill evidence.
5. Exact precedence hierarchy: System -> VerifiedContext -> UserProfile -> RAG -> History -> User Query.
6. Current user message is appended exactly once (no duplication).
7. Missing user profile is tolerated gracefully without errors or profile inference.
8. Stateless personalization operates with X-User-Id without persisting conversations.
9. Cross-user isolation is enforced strictly.
"""

from dataclasses import FrozenInstanceError
import uuid
from typing import Generator, List
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
    CareerChatValidationError,
    ChatResponseStatus,
    PersonalizationContext,
    ProfileContext,
    assemble_personalization_context,
    build_career_chat_langchain_messages,
    build_career_chat_messages,
    get_langchain_history,
)
from app.ai.chatbot.prompts import CAREER_CHATBOT_SYSTEM_PROMPT
from app.ai.context.models import (
    FactProvenance,
    SkillClassification,
    VerifiedCandidateContext,
    VerifiedContext,
    VerifiedSkillFact,
)
from app.ai.qwen.client import QwenClient
from app.ai.qwen.models import QwenChatResponse, QwenMessage
from app.db.database import SessionLocal
from app.db.models import Conversation, Message, User, UserProfile
from app.main import app
from app.schemas.user_profile import UserProfileCreate
from app.services.conversation_service import (
    ConversationNotFoundError,
    conversation_service,
)
from app.services.user_profile_service import (
    UserProfileNotFoundError,
    user_profile_service,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Yields a database session for test setup and tear down."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_user(db_session: Session) -> Generator[User, None, None]:
    """Creates a primary candidate user in PostgreSQL."""
    user = User(
        id=uuid.uuid4(),
        email=f"c5_user_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Alice Candidate",
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
def second_user(db_session: Session) -> Generator[User, None, None]:
    """Creates a secondary candidate user for cross-user isolation tests."""
    user = User(
        id=uuid.uuid4(),
        email=f"c5_user2_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Bob Unauthorized",
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
def test_profile(db_session: Session, test_user: User) -> UserProfile:
    """Creates a populated UserProfile for test_user."""
    profile_in = UserProfileCreate(
        name="Alice Candidate",
        education="Undergraduate",
        college="National Institute of Technology",
        degree="B.Tech",
        branch="Computer Science",
        semester=6,
        target_role="AI/ML Engineer",
        experience_level="Intermediate",
    )
    return user_profile_service.create_profile(
        db=db_session, user_id=test_user.id, profile_data=profile_in
    )


@pytest.fixture
def sample_context() -> VerifiedContext:
    """Returns a valid VerifiedContext containing candidate and skill facts."""
    py_id = uuid.uuid4()
    candidate = VerifiedCandidateContext(
        candidate_id=uuid.uuid4(),
        target_role_id=uuid.uuid4(),
        target_role_name="Software Engineer",
        location="India",
        has_resume=True,
        has_github=True,
        provenance=FactProvenance.DETERMINISTIC_ANALYSIS,
    )
    skills = (
        VerifiedSkillFact(
            skill_id=py_id,
            skill_name="Python",
            canonical_slug="python",
            classification=SkillClassification.STRONG,
            demonstrated_score=0.92,
            claimed=True,
            evidence_count=4,
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


@pytest.fixture
def mock_qwen_client() -> QwenClient:
    """Returns a mocked QwenClient providing deterministic responses."""
    client = MagicMock(spec=QwenClient)
    client.model = "qwen3:8b"
    client.chat.return_value = QwenChatResponse(
        model="qwen3:8b",
        message=QwenMessage(
            role="assistant",
            content="Tailored explanation taking into account your background.",
        ),
        done=True,
        total_duration=120000000,
        load_duration=20000000,
        prompt_eval_count=45,
        eval_count=20,
    )
    return client


# ---------------------------------------------------------------------------
# Test Cases 1-4: Profile Context Data & Serialization
# ---------------------------------------------------------------------------

def test_1_profile_context_is_immutable():
    """ProfileContext must be a frozen dataclass preventing runtime mutation."""
    ctx = ProfileContext(name="Alice", target_role="Backend Developer")
    with pytest.raises(FrozenInstanceError):
        ctx.target_role = "Frontend Developer"  # type: ignore


def test_2_profile_context_from_model_and_omits_none_fields():
    """ProfileContext serialization properly formats available fields and omits None values."""
    ctx = ProfileContext(
        name="Alice",
        education="B.Tech",
        college=None,
        degree=None,
        branch="CSE",
        semester=5,
        target_role="AI Engineer",
        experience_level=None,
    )
    assert ctx.is_available() is True
    serialized = ctx.serialize()
    assert "<user_profile>" in serialized
    assert "</user_profile>" in serialized
    assert "Name: Alice" in serialized
    assert "Education: B.Tech" in serialized
    assert "Branch: CSE" in serialized
    assert "Semester: 5" in serialized
    assert "Target role: AI Engineer" in serialized
    assert "College:" not in serialized
    assert "Degree:" not in serialized
    assert "Experience level:" not in serialized
    assert "None" not in serialized


def test_3_profile_context_unavailable_serialization():
    """Empty or None ProfileContext serializes cleanly as unavailable."""
    empty_ctx = ProfileContext()
    assert empty_ctx.is_available() is False
    serialized = empty_ctx.serialize()
    assert "Profile information is unavailable." in serialized

    none_ctx = ProfileContext.from_model(None)
    assert none_ctx.is_available() is False
    assert "Profile information is unavailable." in none_ctx.serialize()


def test_4_personalization_context_is_immutable_and_preserves_verified_context(sample_context: VerifiedContext):
    """PersonalizationContext preserves sovereign typed VerifiedContext and is immutable."""
    pc = ProfileContext(name="Alice")
    history = (HumanMessage(content="Hello"), AIMessage(content="Hi"))

    pctx = PersonalizationContext(
        profile=pc,
        chat_history=history,
        verified_context=sample_context,
    )
    assert pctx.profile.name == "Alice"
    assert len(pctx.chat_history) == 2
    assert pctx.verified_context is sample_context

    with pytest.raises(FrozenInstanceError):
        pctx.profile = ProfileContext()  # type: ignore


# ---------------------------------------------------------------------------
# Test Cases 5-7: Authority Hierarchy & Non-Authoritative Profile/History
# ---------------------------------------------------------------------------

def test_5_context_precedence_hierarchy_enforced(sample_context: VerifiedContext):
    """Requirement 5 & 10: Final LangChain prompt explicitly establishes strict precedence."""
    pc = ProfileContext(name="Alice", target_role="Data Scientist")
    history = [HumanMessage(content="Previous turn")]

    lc_msgs = build_career_chat_langchain_messages(
        context=sample_context,
        user_query="What should I study next?",
        history_messages=history,
        profile_context=pc,
    )

    # 1. SystemMessage at index 0
    assert isinstance(lc_msgs[0], SystemMessage)
    sys_content = lc_msgs[0].content

    # Check ordering of components within SystemMessage
    sys_idx = sys_content.find("You are a general-purpose AI assistant")
    vc_idx = sys_content.find("=== VERIFIED SKILLFORGE GROUND TRUTH CONTEXT ===")
    profile_idx = sys_content.find("=== USER PROFILE (PERSONALIZATION CONTEXT - NON-AUTHORITATIVE) ===")

    assert sys_idx != -1
    assert vc_idx != -1
    assert profile_idx != -1
    assert sys_idx < vc_idx < profile_idx, "System prompt -> VerifiedContext -> UserProfile precedence violated"

    # History follows SystemMessage
    assert isinstance(lc_msgs[1], HumanMessage)
    assert lc_msgs[1].content == "Previous turn"

    # Current user message is last
    assert isinstance(lc_msgs[-1], HumanMessage)
    assert lc_msgs[-1].content == "What should I study next?"


def test_6_test_authority_with_conflict_role_and_history_cannot_override_missing():
    """
    Requirement 17: Explicit deterministic conflict test:
    UserProfile: target_role = 'AI/ML Engineer'
    VerifiedContext: Machine Learning = MISSING
    Conversation history: 'I already know machine learning.'
    VerifiedContext MUST remain authoritative and show MISSING.
    """
    ml_id = uuid.uuid4()
    vc = VerifiedContext(
        skills=(
            VerifiedSkillFact(
                skill_id=ml_id,
                skill_name="Machine Learning",
                canonical_slug="machine-learning",
                classification=SkillClassification.MISSING,
                demonstrated_score=0.0,
                claimed=False,
                evidence_count=0,
                provenance=FactProvenance.DETERMINISTIC_ANALYSIS,
            ),
        )
    )
    pc = ProfileContext(target_role="AI/ML Engineer", branch="CSE", degree="B.Tech")
    history = [
        HumanMessage(content="I already know machine learning."),
        AIMessage(content="Understood."),
    ]

    lc_msgs = build_career_chat_langchain_messages(
        context=vc,
        user_query="What is the status of my Machine Learning skill?",
        history_messages=history,
        profile_context=pc,
    )

    sys_content = lc_msgs[0].content
    # Verified classification MISSING is preserved
    assert "Machine Learning:" in sys_content
    assert "Classification: MISSING" in sys_content

    # Strict operational rules are included
    assert "Treat the supplied VerifiedContext as authoritative ground truth." in sys_content
    assert "Never claim that a user possesses a skill solely because the profile, target role, or conversation history mentions it." in sys_content
    assert "Target role is an aspiration, branch/degree is an academic background, and dialogue statements are conversational claims; NONE of these constitute verified skill evidence." in sys_content
    assert "Precedence of authority: (1) System Instructions, (2) VerifiedContext (authoritative truth), (3) UserProfile (personalization only)" in sys_content


def test_7_no_forced_personalization_rule_present(sample_context: VerifiedContext):
    """Requirement 4: Prompt explicitly instructs Qwen not to force personalization on general questions."""
    pc = ProfileContext(semester=3, target_role="AI/ML Engineer")

    lc_msgs = build_career_chat_langchain_messages(
        context=sample_context,
        user_query="What is photosynthesis?",
        profile_context=pc,
    )
    sys_content = lc_msgs[0].content
    assert "Do not force personalization when irrelevant (e.g. general knowledge, academic, or casual questions such as 'What is photosynthesis?')." in sys_content
    assert "Answer general questions directly and accurately without awkward or forced profile references." in sys_content


# ---------------------------------------------------------------------------
# Test Cases 8-10: Single Current User Message & History Boundary
# ---------------------------------------------------------------------------

def test_8_current_user_message_never_duplicated_persistent(
    db_session: Session, test_user: User, test_profile: UserProfile, sample_context: VerifiedContext, mock_qwen_client: QwenClient
):
    """
    Requirement 6 & 16: For persistent chat, assert:
    current_user_message_count == 1 in final LangChain message sequence.
    """
    conv = conversation_service.create_conversation(
        db_session, user_id=test_user.id, title="Single Message Test"
    )
    # Add an existing previous turn
    conversation_service.add_message(
        db_session, conv.id, test_user.id, role="user", content="Turn 1 question"
    )
    conversation_service.add_message(
        db_session, conv.id, test_user.id, role="assistant", content="Turn 1 answer"
    )

    service = CareerChatService(qwen_client=mock_qwen_client)
    req = CareerChatRequest(
        user_query="How do I get an internship?",
        conversation_id=conv.id,
        verified_context=sample_context,
    )

    response = service.chat(request=req, db=db_session, user_id=test_user.id)
    assert response.status == ChatResponseStatus.EXPLANATORY

    # Inspect the captured final LangChain messages
    last_lc = service._last_langchain_messages
    assert last_lc is not None

    current_user_message_count = sum(
        1 for m in last_lc if isinstance(m, HumanMessage) and m.content == "How do I get an internship?"
    )
    assert current_user_message_count == 1, f"Expected 1, found {current_user_message_count}"

    # Verify history loader only loaded previous messages
    assert len(last_lc) == 4  # SystemMessage, Turn 1 user, Turn 1 asst, Current user
    assert last_lc[1].content == "Turn 1 question"
    assert last_lc[2].content == "Turn 1 answer"
    assert last_lc[3].content == "How do I get an internship?"


def test_9_current_user_message_never_duplicated_stateless(sample_context: VerifiedContext, mock_qwen_client: QwenClient):
    """Stateless chat has exactly one user message in the LangChain message sequence."""
    service = CareerChatService(qwen_client=mock_qwen_client)
    req = CareerChatRequest(
        user_query="Explain quicksort in Python",
        conversation_id=None,
        verified_context=sample_context,
    )

    response = service.chat(request=req, db=None, user_id=None)
    assert response.status == ChatResponseStatus.EXPLANATORY

    last_lc = service._last_langchain_messages
    assert last_lc is not None
    assert len(last_lc) == 2
    assert isinstance(last_lc[0], SystemMessage)
    assert isinstance(last_lc[1], HumanMessage)
    assert last_lc[1].content == "Explain quicksort in Python"

    current_user_message_count = sum(
        1 for m in last_lc if isinstance(m, HumanMessage) and m.content == "Explain quicksort in Python"
    )
    assert current_user_message_count == 1


def test_10_twenty_message_history_bound_with_exclusion(
    db_session: Session, test_user: User
):
    """History boundary is respected when excluding the current message."""
    conv = conversation_service.create_conversation(
        db_session, user_id=test_user.id, title="Bound Test"
    )

    msg_ids: List[uuid.UUID] = []
    for i in range(25):
        m = conversation_service.add_message(
            db_session,
            conv.id,
            test_user.id,
            role="user" if i % 2 == 0 else "assistant",
            content=f"Message {i}",
        )
        msg_ids.append(m.id)

    # Exclude the 25th message (index 24)
    history = get_langchain_history(
        db=db_session,
        conversation_id=conv.id,
        user_id=test_user.id,
        limit=20,
        exclude_message_id=msg_ids[-1],
    )
    assert len(history) == 20
    # Must contain messages 4 to 23
    assert history[0].content == "Message 4"
    assert history[-1].content == "Message 23"
    assert not any(m.content == "Message 24" for m in history)


# ---------------------------------------------------------------------------
# Test Cases 11-13: Profile Loading & Missing Profile Tolerance
# ---------------------------------------------------------------------------

def test_11_profile_loaded_via_service_layer(
    db_session: Session, test_user: User, test_profile: UserProfile, sample_context: VerifiedContext, mock_qwen_client: QwenClient
):
    """Requirement 7: Profile loading goes through UserProfileService, reaching prompt."""
    service = CareerChatService(qwen_client=mock_qwen_client)
    req = CareerChatRequest(
        user_query="What projects should I build?",
        conversation_id=None,
        verified_context=sample_context,
    )

    service.chat(request=req, db=db_session, user_id=test_user.id)

    last_lc = service._last_langchain_messages
    assert last_lc is not None
    sys_content = last_lc[0].content

    assert "<user_profile>" in sys_content
    assert "Name: Alice Candidate" in sys_content
    assert "Target role: AI/ML Engineer" in sys_content
    assert "College: National Institute of Technology" in sys_content
    assert "Semester: 6" in sys_content


def test_12_missing_profile_handled_gracefully(
    db_session: Session, test_user: User, sample_context: VerifiedContext, mock_qwen_client: QwenClient
):
    """
    Requirement 8: If UserProfileNotFoundError occurs:
    - do not return error
    - do not create profile
    - do not infer profile
    - chat proceeds normally with unavailable ProfileContext
    """
    # Ensure test_user has NO profile in DB
    existing = db_session.query(UserProfile).filter(UserProfile.user_id == test_user.id).first()
    if existing:
        db_session.delete(existing)
        db_session.commit()

    service = CareerChatService(qwen_client=mock_qwen_client)
    req = CareerChatRequest(
        user_query="Tell me about algorithms",
        conversation_id=None,
        verified_context=sample_context,
    )

    resp = service.chat(request=req, db=db_session, user_id=test_user.id)
    assert resp.status == ChatResponseStatus.EXPLANATORY

    # Verify no profile was created in DB
    assert db_session.query(UserProfile).filter(UserProfile.user_id == test_user.id).first() is None

    # Verify prompt omitted user_profile block
    last_lc = service._last_langchain_messages
    assert last_lc is not None
    sys_content = last_lc[0].content
    assert "=== USER PROFILE (PERSONALIZATION CONTEXT - NON-AUTHORITATIVE) ===" not in sys_content


def test_13_profile_cannot_bypass_sufficiency_gate(
    db_session: Session, test_user: User, test_profile: UserProfile, sample_context: VerifiedContext, mock_qwen_client: QwenClient
):
    """
    Requirement 3: Profile target_role or branch cannot bypass sufficiency gate
    for candidate skill possession questions.
    """
    service = CareerChatService(qwen_client=mock_qwen_client)
    req = CareerChatRequest(
        # Candidate asks about their status in PyTorch, which is NOT in VerifiedContext
        user_query="Why am I weak at PyTorch?",
        conversation_id=None,
        verified_context=sample_context,  # Only has Python
    )

    resp = service.chat(request=req, db=db_session, user_id=test_user.id)
    assert resp.status == ChatResponseStatus.INSUFFICIENT_EVIDENCE
    assert "insufficient to answer this question" in resp.explanation
    # Qwen client was NOT called
    mock_qwen_client.chat.assert_not_called()


# ---------------------------------------------------------------------------
# Test Cases 14-15: Stateless Personalization & Anonymous Callers
# ---------------------------------------------------------------------------

def test_14_api_stateless_personalization_with_x_user_id(
    db_session: Session, test_user: User, test_profile: UserProfile, sample_context: VerifiedContext
):
    """
    Requirement 9: POST /chat with conversation_id=None and valid X-User-Id:
    - loads profile
    - does not create conversation
    - does not persist messages
    """
    client = TestClient(app)
    payload = {
        "user_query": "Give me a learning roadmap",
        "conversation_id": None,
        "verified_context": sample_context.model_dump(mode="json"),
    }

    with patch.object(CareerChatService, "chat") as mock_chat:
        mock_chat.return_value = CareerChatResponse(
            explanation="Here is a roadmap personalized for NIT 6th semester.",
            model="qwen3:8b",
            status=ChatResponseStatus.EXPLANATORY,
            referenced_skill_ids=(),
            retrieved_evidence=(),
            usage=None,
            conversation_id=None,
            message_id=None,
        )

        resp = client.post(
            "/api/v1/ai/chat",
            json=payload,
            headers={"X-User-Id": str(test_user.id)},
        )
        assert resp.status_code == 200
        assert mock_chat.called
        # user_id must be passed to chat()
        kwargs = mock_chat.call_args.kwargs
        assert kwargs["user_id"] == test_user.id
        assert kwargs["db"] is not None

    # Verify no conversation or message was created in DB
    assert db_session.query(Conversation).filter(Conversation.user_id == test_user.id).count() == 0
    assert db_session.query(Message).count() == 0


def test_15_api_stateless_anonymous_without_x_user_id(sample_context: VerifiedContext):
    """
    Requirement 9: POST /chat with conversation_id=None and no X-User-Id:
    - anonymous call succeeds
    - user_id is None, db is None
    - no authentication error
    """
    client = TestClient(app)
    payload = {
        "user_query": "What is Python?",
        "conversation_id": None,
        "verified_context": sample_context.model_dump(mode="json"),
    }

    with patch.object(CareerChatService, "chat") as mock_chat:
        mock_chat.return_value = CareerChatResponse(
            explanation="Python is a high-level programming language.",
            model="qwen3:8b",
            status=ChatResponseStatus.EXPLANATORY,
            referenced_skill_ids=(),
            retrieved_evidence=(),
            usage=None,
            conversation_id=None,
            message_id=None,
        )

        resp = client.post("/api/v1/ai/chat", json=payload)
        assert resp.status_code == 200
        kwargs = mock_chat.call_args.kwargs
        assert kwargs["user_id"] is None
        assert kwargs["db"] is None


# ---------------------------------------------------------------------------
# Test Cases 16-17: Persistent Chat Ownership & Cross-User Isolation
# ---------------------------------------------------------------------------

def test_16_cross_user_isolation_user_b_cannot_access_user_a_conversation_or_profile(
    db_session: Session, test_user: User, test_profile: UserProfile, second_user: User, sample_context: VerifiedContext, mock_qwen_client: QwenClient
):
    """
    Requirement 10: Integration test proving User A conversation + User B request
    cannot cause User A profile/history to reach Qwen.
    """
    conv_a = conversation_service.create_conversation(
        db_session, user_id=test_user.id, title="User A Secret Chat"
    )
    conversation_service.add_message(
        db_session, conv_a.id, test_user.id, role="user", content="Secret from User A"
    )

    # User B profile
    user_profile_service.create_profile(
        db_session,
        second_user.id,
        UserProfileCreate(name="Bob", target_role="Security Analyst"),
    )

    service = CareerChatService(qwen_client=mock_qwen_client)
    req = CareerChatRequest(
        user_query="Show me the chat",
        conversation_id=conv_a.id,
        verified_context=sample_context,
    )

    # User B attempts to access User A's conversation
    with pytest.raises(ConversationNotFoundError):
        service.chat(request=req, db=db_session, user_id=second_user.id)

    # Qwen was never called
    mock_qwen_client.chat.assert_not_called()
    # Captured messages must be None
    assert service._last_langchain_messages is None


def test_17_api_cross_user_persistent_chat_returns_404(
    db_session: Session, test_user: User, second_user: User, sample_context: VerifiedContext
):
    """API returns 404 when User B requests User A's conversation_id."""
    conv_a = conversation_service.create_conversation(
        db_session, user_id=test_user.id, title="User A Convo"
    )

    client = TestClient(app)
    payload = {
        "user_query": "Tell me secrets",
        "conversation_id": str(conv_a.id),
        "verified_context": sample_context.model_dump(mode="json"),
    }

    resp = client.post(
        "/api/v1/ai/chat",
        json=payload,
        headers={"X-User-Id": str(second_user.id)},
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Test Cases 18-20: Final LangChain Message Sequence & Real Roundtrip
# ---------------------------------------------------------------------------

def test_18_final_langchain_message_sequence_inspection(
    db_session: Session, test_user: User, test_profile: UserProfile, sample_context: VerifiedContext, mock_qwen_client: QwenClient
):
    """
    Requirement 16: Test that constructs the final messages passed toward Qwen and verifies:
    - system instructions exist
    - VerifiedContext exists
    - user_profile block exists when profile exists
    - profile fields are correctly represented
    - history appears in expected location
    - current user message appears exactly once
    - no profile field is invented
    - VerifiedContext remains clearly authoritative
    """
    conv = conversation_service.create_conversation(
        db_session, user_id=test_user.id, title="Inspection Convo"
    )
    conversation_service.add_message(
        db_session, conv.id, test_user.id, role="user", content="Past question 1"
    )
    conversation_service.add_message(
        db_session, conv.id, test_user.id, role="assistant", content="Past answer 1"
    )

    service = CareerChatService(qwen_client=mock_qwen_client)
    req = CareerChatRequest(
        user_query="What should I learn in semester 6?",
        conversation_id=conv.id,
        verified_context=sample_context,
    )

    service.chat(request=req, db=db_session, user_id=test_user.id)

    last_lc = service._last_langchain_messages
    assert last_lc is not None
    assert len(last_lc) == 4

    sys_msg = last_lc[0]
    assert isinstance(sys_msg, SystemMessage)
    # 1. System instructions
    assert "You are a general-purpose AI assistant" in sys_msg.content
    # 2. VerifiedContext exists and is authoritative
    assert "=== VERIFIED SKILLFORGE GROUND TRUTH CONTEXT ===" in sys_msg.content
    # 3. user_profile block exists
    assert "=== USER PROFILE (PERSONALIZATION CONTEXT - NON-AUTHORITATIVE) ===" in sys_msg.content
    # 4. Profile fields correctly represented
    assert "Name: Alice Candidate" in sys_msg.content
    assert "College: National Institute of Technology" in sys_msg.content
    assert "Semester: 6" in sys_msg.content
    assert "Target role: AI/ML Engineer" in sys_msg.content
    # 5. No invented profile fields
    assert "skills:" not in sys_msg.content.lower().split("=== user profile")[1].split("=== end user profile")[0]
    # 6. History appears in expected location
    assert isinstance(last_lc[1], HumanMessage)
    assert last_lc[1].content == "Past question 1"
    assert isinstance(last_lc[2], AIMessage)
    assert last_lc[2].content == "Past answer 1"
    # 7. Current user message appears exactly once
    assert isinstance(last_lc[3], HumanMessage)
    assert last_lc[3].content == "What should I learn in semester 6?"
    user_msg_matches = [m for m in last_lc if isinstance(m, HumanMessage) and m.content == "What should I learn in semester 6?"]
    assert len(user_msg_matches) == 1


def test_19_failed_qwen_does_not_persist_assistant_message(
    db_session: Session, test_user: User, test_profile: UserProfile, sample_context: VerifiedContext
):
    """Requirement 19: Generation failure does NOT persist assistant message in DB."""
    failing_client = MagicMock(spec=QwenClient)
    failing_client.model = "qwen3:8b"
    failing_client.chat.side_effect = Exception("Ollama connection broke")

    conv = conversation_service.create_conversation(
        db_session, user_id=test_user.id, title="Failure Test"
    )

    service = CareerChatService(qwen_client=failing_client)
    req = CareerChatRequest(
        user_query="Hello AI",
        conversation_id=conv.id,
        verified_context=sample_context,
    )

    with pytest.raises(CareerChatGenerationError):
        service.chat(request=req, db=db_session, user_id=test_user.id)

    # In DB: User message was persisted, but NO assistant message was persisted
    db_messages = conversation_service.get_messages(db_session, conv.id, test_user.id)
    assert len(db_messages) == 1
    assert db_messages[0].role == "user"
    assert db_messages[0].content == "Hello AI"


def test_20_real_postgresql_roundtrip_with_profile_and_chat(
    db_session: Session, test_user: User, test_profile: UserProfile, sample_context: VerifiedContext, mock_qwen_client: QwenClient
):
    """
    Requirement 20 & 21: Full PostgreSQL roundtrip:
    - User has UserProfile in DB
    - User creates Conversation in DB
    - Service persists user message
    - Service loads profile and history
    - Service invokes Qwen
    - Service persists assistant response
    - Messages table accurately stores roundtrip
    """
    conv = conversation_service.create_conversation(
        db_session, user_id=test_user.id, title="PostgreSQL Roundtrip"
    )

    service = CareerChatService(qwen_client=mock_qwen_client)
    req = CareerChatRequest(
        user_query="What should I focus on next?",
        conversation_id=conv.id,
        verified_context=sample_context,
    )

    resp = service.chat(request=req, db=db_session, user_id=test_user.id)
    assert resp.status == ChatResponseStatus.EXPLANATORY
    assert resp.message_id is not None

    # Verify messages in DB
    messages = conversation_service.get_messages(db_session, conv.id, test_user.id)
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].content == "What should I focus on next?"
    assert messages[1].role == "assistant"
    assert messages[1].id == resp.message_id
    assert messages[1].content == "Tailored explanation taking into account your background."


def test_21_branch_and_degree_do_not_establish_verified_skill_evidence(sample_context: VerifiedContext):
    """
    Requirement 3: branch='CSE' and degree='B.Tech' MUST NOT establish verified skill evidence.
    Prompt explicitly contains operational rule.
    """
    pc = ProfileContext(degree="B.Tech", branch="CSE", education="Undergraduate")
    lc_msgs = build_career_chat_langchain_messages(
        context=sample_context,
        user_query="Am I qualified as a programmer?",
        profile_context=pc,
    )
    sys_content = lc_msgs[0].content
    assert "Target role is an aspiration, branch/degree is an academic background, and dialogue statements are conversational claims; NONE of these constitute verified skill evidence." in sys_content
    assert "Only VerifiedContext establishes verified candidate skills." in sys_content


def test_22_stateless_personalization_missing_profile_proceeds(
    db_session: Session, test_user: User, sample_context: VerifiedContext, mock_qwen_client: QwenClient
):
    """
    Requirement 8 & 9: Stateless chat with X-User-Id where user has NO profile:
    - UserProfileNotFoundError handled smoothly
    - No profile created
    - No conversation created
    - Response generated normally
    """
    # Ensure test_user has NO profile
    existing = db_session.query(UserProfile).filter(UserProfile.user_id == test_user.id).first()
    if existing:
        db_session.delete(existing)
        db_session.commit()

    service = CareerChatService(qwen_client=mock_qwen_client)
    req = CareerChatRequest(
        user_query="Tell me about algorithms",
        conversation_id=None,
        verified_context=sample_context,
    )

    resp = service.chat(request=req, db=db_session, user_id=test_user.id)
    assert resp.status == ChatResponseStatus.EXPLANATORY
    # Verify no profile was created
    assert db_session.query(UserProfile).filter(UserProfile.user_id == test_user.id).first() is None
    # Verify no conversation or message was created
    assert db_session.query(Conversation).filter(Conversation.user_id == test_user.id).count() == 0
    assert db_session.query(Message).count() == 0
