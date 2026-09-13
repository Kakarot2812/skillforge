"""
Integration tests for C7-A: Live RAG Pipeline Activation in /api/v1/ai/chat.

Verifies:
1. Lazy embedding provider behavior (dimension=384 without eagerly loading model).
2. Shared singleton provider behavior (get_shared_embedding_provider).
3. RAGService injection into live CareerChatService in /api/v1/ai/chat.
4. /api/v1/ai/chat with RAG active and zero matching chunks returns retrieved_evidence=[].
5. Indexed test/fixture chunks retrieved through live chat path.
6. Strict skill filtering excludes unrelated skill chunks.
7. Sufficiency gate prevents RAG retrieval and Qwen calls on rejected query.
8. Anonymous and persistent chat paths both work with RAG enabled.
9. Retrieved evidence is marked strictly non-authoritative in prompt.
"""

from datetime import datetime, timezone
from typing import Generator
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.ai.chatbot import (
    CareerChatRequest,
    CareerChatResponse,
    CareerChatService,
    ChatResponseStatus,
)
from app.ai.chatbot.models import ChatUsageStats
from app.ai.chatbot.prompts import build_career_chat_langchain_messages
from app.ai.context.models import (
    FactProvenance,
    SkillClassification,
    VerifiedCandidateContext,
    VerifiedContext,
    VerifiedSkillFact,
)
from app.config import settings
from app.db.database import SessionLocal, get_db
from app.db.models import Conversation, Message, RAGChunk as DBRAGChunk, RAGDocument as DBRAGDocument, Skill, User
from app.main import app
from app.rag import (
    EmbeddingProvider,
    LazySentenceTransformerProvider,
    MockEmbeddingProvider,
    RAGDocument,
    RAGDocumentMetadata,
    RAGRetrievalFilter,
    RAGRetrievalResult,
    RAGService,
    RAGSourceType,
    get_shared_embedding_provider,
)


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Yields a clean database session for test execution."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_client(db_session: Session) -> Generator[TestClient, None, None]:
    """TestClient that overrides get_db dependency with test db_session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def sample_skill(db_session: Session) -> Skill:
    """Provides a canonical Skill entity (Python) in the database."""
    skill = db_session.query(Skill).filter_by(slug="python").first()
    if not skill:
        skill = Skill(
            id=uuid4(),
            name="Python",
            slug="python",
            category="Backend",
            description="Core programming language",
        )
        db_session.add(skill)
        db_session.commit()
    return skill


@pytest.fixture
def second_skill(db_session: Session) -> Skill:
    """Provides a second canonical Skill entity (Docker) in the database."""
    skill = db_session.query(Skill).filter_by(slug="docker").first()
    if not skill:
        skill = Skill(
            id=uuid4(),
            name="Docker",
            slug="docker",
            category="DevOps",
            description="Container platform",
        )
        db_session.add(skill)
        db_session.commit()
    return skill


@pytest.fixture
def test_user(db_session: Session) -> Generator[User, None, None]:
    """Provides an isolated User for persistent chat testing."""
    user = User(
        id=uuid4(),
        email=f"c7_user_{uuid4().hex[:8]}@example.com",
    )
    db_session.add(user)
    db_session.commit()
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
def verified_context_with_skill(sample_skill: Skill) -> VerifiedContext:
    """VerifiedContext containing the sample skill as PARTIAL."""
    return VerifiedContext(
        candidate=VerifiedCandidateContext(
            candidate_id=uuid4(),
            target_role_name="Backend Engineer",
            location="Remote",
            has_resume=True,
            has_github=True,
            provenance=FactProvenance.DETERMINISTIC_ANALYSIS,
        ),
        skills=(
            VerifiedSkillFact(
                skill_id=sample_skill.id,
                skill_name=sample_skill.name,
                canonical_slug=sample_skill.slug,
                classification=SkillClassification.PARTIAL,
                demonstrated_score=0.45,
                claimed=True,
                evidence_count=1,
                provenance=FactProvenance.DETERMINISTIC_ANALYSIS,
            ),
        ),
        provenance=FactProvenance.DETERMINISTIC_ANALYSIS,
    )


# ---------------------------------------------------------------------------
# 1. Lazy Embedding Provider & Singleton Behavior
# ---------------------------------------------------------------------------

def test_1_lazy_embedding_provider_does_not_load_model_eagerly():
    """Verify LazySentenceTransformerProvider exposes dimension=384 without loading weights."""
    provider = LazySentenceTransformerProvider()
    assert provider.dimension == 384
    assert provider.is_loaded is False
    # Validate dimension consistency without loading
    provider.validate_dimension_consistency(384)
    assert provider.is_loaded is False


def test_2_get_shared_embedding_provider_returns_singleton():
    """Verify get_shared_embedding_provider returns the same instance across calls."""
    p1 = get_shared_embedding_provider()
    p2 = get_shared_embedding_provider()
    assert p1 is p2
    assert isinstance(p1, EmbeddingProvider)
    assert p1.dimension == 384


# ---------------------------------------------------------------------------
# 2. Live Endpoint Injection & Zero Matches
# ---------------------------------------------------------------------------

def test_3_rag_service_injected_into_career_chat_service(
    test_client: TestClient,
    verified_context_with_skill: VerifiedContext,
):
    """Verify RAGService is injected into CareerChatService in /api/v1/ai/chat."""
    payload = {
        "user_query": "Explain my Python status",
        "conversation_id": None,
        "verified_context": verified_context_with_skill.model_dump(mode="json"),
    }

    captured_services = []
    original_init = CareerChatService.__init__

    def spy_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        captured_services.append(self)

    with patch.object(CareerChatService, "__init__", spy_init):
        with patch.object(CareerChatService, "chat") as mock_chat:
            mock_chat.return_value = CareerChatResponse(
                explanation="Mock explanation",
                model="qwen3:8b",
                status=ChatResponseStatus.EXPLANATORY,
                referenced_skill_ids=(),
                retrieved_evidence=(),
                usage=None,
                conversation_id=None,
                message_id=None,
            )
            resp = test_client.post("/api/v1/ai/chat", json=payload)
            assert resp.status_code == 200

    assert len(captured_services) == 1
    injected_service = captured_services[0]
    assert injected_service.rag_service is not None
    assert isinstance(injected_service.rag_service, RAGService)
    assert injected_service.rag_service.embedding_provider.dimension == 384


def test_4_live_chat_with_rag_active_and_zero_matching_chunks(
    test_client: TestClient,
    verified_context_with_skill: VerifiedContext,
):
    """Verify /api/v1/ai/chat with RAG active and 0 matching chunks returns retrieved_evidence=[]."""
    payload = {
        "user_query": "Explain my Python status",
        "conversation_id": None,
        "verified_context": verified_context_with_skill.model_dump(mode="json"),
    }

    with patch("app.ai.chatbot.service.QwenClient") as MockQwen:
        mock_instance = MockQwen.return_value
        mock_instance.model = "qwen3:8b"
        mock_msg = MagicMock()
        mock_msg.content = "Python is partial in your verified profile."
        mock_resp = MagicMock()
        mock_resp.message = mock_msg
        mock_resp.model = "qwen3:8b"
        mock_resp.total_duration = 1000
        mock_resp.load_duration = 100
        mock_resp.prompt_eval_count = 50
        mock_resp.eval_count = 25
        mock_instance.chat.return_value = mock_resp

        resp = test_client.post("/api/v1/ai/chat", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "EXPLANATORY"
        assert data["retrieved_evidence"] == []


# ---------------------------------------------------------------------------
# 3. Retrieval with Controlled Test Evidence
# ---------------------------------------------------------------------------

def test_5_live_chat_retrieves_indexed_test_fixture_chunk(
    test_client: TestClient,
    db_session: Session,
    sample_skill: Skill,
    verified_context_with_skill: VerifiedContext,
):
    """
    Verify indexed test chunk is retrieved through the live /api/v1/ai/chat path
    and returned in the response contract.
    """
    # Create isolated test RAG document and chunk
    doc_id = uuid4()
    chunk_id = uuid4()
    mock_vector = [0.1] * 384
    norm = sum(x * x for x in mock_vector) ** 0.5
    mock_vector = [x / norm for x in mock_vector]

    db_doc = DBRAGDocument(
        id=doc_id,
        source_type=RAGSourceType.APPROVED_RESOURCE.value,
        source_reference="official:python:tutorial",
        title="Python Official Tutorial",
        content="Python is an interpreted, high-level, general-purpose programming language.",
        document_metadata={"skill_id": str(sample_skill.id), "approved_by": "test"},
    )
    db_chunk = DBRAGChunk(
        id=chunk_id,
        document_id=doc_id,
        chunk_index=0,
        content="Python is an interpreted, high-level, general-purpose programming language.",
        embedding=mock_vector,
        skill_id=sample_skill.id,
        source_type=RAGSourceType.APPROVED_RESOURCE.value,
        source_reference="official:python:tutorial",
        chunk_metadata={"chunk_index": 0, "source_reference": "official:python:tutorial"},
    )
    db_session.add(db_doc)
    db_session.add(db_chunk)
    db_session.commit()

    try:
        payload = {
            "user_query": "Explain my Python status",
            "conversation_id": None,
            "verified_context": verified_context_with_skill.model_dump(mode="json"),
        }

        # Mock query embedding generation so test does not depend on model download
        with patch.object(
            get_shared_embedding_provider(),
            "embed_text",
            return_value=mock_vector,
        ):
            with patch("app.ai.chatbot.service.QwenClient") as MockQwen:
                mock_instance = MockQwen.return_value
                mock_instance.model = "qwen3:8b"
                mock_msg = MagicMock()
                mock_msg.content = "Python is partial and high demand."
                mock_resp = MagicMock()
                mock_resp.message = mock_msg
                mock_resp.model = "qwen3:8b"
                mock_resp.total_duration = 1000
                mock_resp.load_duration = 100
                mock_resp.prompt_eval_count = 50
                mock_resp.eval_count = 25
                mock_instance.chat.return_value = mock_resp

                resp = test_client.post("/api/v1/ai/chat", json=payload)
                assert resp.status_code == 200
                data = resp.json()
                assert len(data["retrieved_evidence"]) == 1
                ev = data["retrieved_evidence"][0]
                assert ev["chunk_id"] == str(chunk_id)
                assert "Python" in ev["content"]
                assert ev["source_type"] == "APPROVED_RESOURCE"
                assert ev["similarity_score"] > 0.99
    finally:
        db_session.delete(db_chunk)
        db_session.delete(db_doc)
        db_session.commit()



def test_6_strict_skill_filtering_excludes_unrelated_skill_chunks(
    test_client: TestClient,
    db_session: Session,
    sample_skill: Skill,
    second_skill: Skill,
    verified_context_with_skill: VerifiedContext,
):
    """Verify that retrieval strictly filters by the referenced skill ID."""
    doc_id = uuid4()
    chunk_skill_a = uuid4()
    chunk_skill_b = uuid4()

    vec = [0.1] * 384
    norm = sum(x * x for x in vec) ** 0.5
    vec = [x / norm for x in vec]

    db_doc = DBRAGDocument(
        id=doc_id,
        source_type=RAGSourceType.APPROVED_RESOURCE.value,
        source_reference="test:doc",
        title="Test Doc",
        content="Test content",
        document_metadata={},
    )
    # Chunk A: Python
    c_a = DBRAGChunk(
        id=chunk_skill_a,
        document_id=doc_id,
        chunk_index=0,
        content="Python language fundamentals and standard library.",
        embedding=vec,
        skill_id=sample_skill.id,
        source_type=RAGSourceType.APPROVED_RESOURCE.value,
        source_reference="test:python",
        chunk_metadata={"chunk_index": 0, "source_reference": "test:python"},
    )
    # Chunk B: Docker (different skill)
    c_b = DBRAGChunk(
        id=chunk_skill_b,
        document_id=doc_id,
        chunk_index=1,
        content="Docker containerization and compose setups.",
        embedding=vec,
        skill_id=second_skill.id,
        source_type=RAGSourceType.APPROVED_RESOURCE.value,
        source_reference="test:docker",
        chunk_metadata={"chunk_index": 1, "source_reference": "test:docker"},
    )
    db_session.add(db_doc)
    db_session.add(c_a)
    db_session.add(c_b)
    db_session.commit()

    try:
        # Query only targets Python
        payload = {
            "user_query": "Tell me about my Python gaps",
            "conversation_id": None,
            "verified_context": verified_context_with_skill.model_dump(mode="json"),
        }

        with patch.object(get_shared_embedding_provider(), "embed_text", return_value=vec):
            with patch("app.ai.chatbot.service.QwenClient") as MockQwen:
                mock_instance = MockQwen.return_value
                mock_instance.model = "qwen3:8b"
                mock_msg = MagicMock()
                mock_msg.content = "Python explanation."
                mock_resp = MagicMock()
                mock_resp.message = mock_msg
                mock_resp.model = "qwen3:8b"
                mock_resp.total_duration = 1000
                mock_resp.load_duration = 100
                mock_resp.prompt_eval_count = 50
                mock_resp.eval_count = 25
                mock_instance.chat.return_value = mock_resp

                resp = test_client.post("/api/v1/ai/chat", json=payload)
                assert resp.status_code == 200
                data = resp.json()
                # Must only contain Chunk A (Python), never Chunk B (Docker)
                retrieved_ids = [e["chunk_id"] for e in data["retrieved_evidence"]]
                assert str(chunk_skill_a) in retrieved_ids
                assert str(chunk_skill_b) not in retrieved_ids
    finally:
        db_session.delete(c_a)
        db_session.delete(c_b)
        db_session.delete(db_doc)
        db_session.commit()


# ---------------------------------------------------------------------------
# 4. Authority & Sufficiency Protection
# ---------------------------------------------------------------------------

def test_7_sufficiency_gate_prevents_rag_and_qwen_on_rejected_query(
    test_client: TestClient,
    verified_context_with_skill: VerifiedContext,
):
    """Verify sufficiency gate halts query before RAG retrieval or Qwen execution."""
    payload = {
        "user_query": "Why am I weak at Kubernetes?",  # Unknown skill not in VerifiedContext
        "conversation_id": None,
        "verified_context": verified_context_with_skill.model_dump(mode="json"),
    }

    with patch.object(RAGService, "retrieve") as mock_retrieve:
        with patch("app.ai.chatbot.service.QwenClient") as MockQwen:
            mock_instance = MockQwen.return_value
            mock_instance.model = "qwen3:8b"
            resp = test_client.post("/api/v1/ai/chat", json=payload)
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "INSUFFICIENT_EVIDENCE"
            assert "Kubernetes" in data["explanation"]
            assert data["retrieved_evidence"] == []
            # Neither RAG retrieval nor Qwen may be called
            assert not mock_retrieve.called
            assert not mock_instance.chat.called


def test_8_retrieved_evidence_marked_non_authoritative_in_langchain_prompt(
    sample_skill: Skill,
    verified_context_with_skill: VerifiedContext,
):
    """Verify retrieved evidence is serialized under the NON-AUTHORITATIVE section in prompt."""
    result = RAGRetrievalResult(
        chunk_id=uuid4(),
        document_id=uuid4(),
        content="Official Python async tutorial excerpt.",
        similarity_score=0.92,
        source_type=RAGSourceType.APPROVED_RESOURCE,
        source_reference="python:docs",
        skill_id=sample_skill.id,
        skill_name="Python",
        provenance=RAGSourceType.APPROVED_RESOURCE,
        source_timestamp=datetime.now(timezone.utc),
        metadata={
            "chunk_index": 0,
            "source_reference": "python:docs",
            "skill_id": str(sample_skill.id),
            "skill_name": "Python",
            "confidence_score": 1.0,
        },
    )

    messages = build_career_chat_langchain_messages(
        context=verified_context_with_skill,
        user_query="What is Python?",
        retrieved_evidence=[result],
    )

    system_content = messages[0].content
    assert "=== RETRIEVED SUPPORTING EVIDENCE (NON-AUTHORITATIVE) ===" in system_content
    assert "Official Python async tutorial excerpt." in system_content
    assert "=== END RETRIEVED SUPPORTING EVIDENCE ===" in system_content
    # Verified ground truth header must also be intact
    assert "=== VERIFIED SKILLFORGE GROUND TRUTH CONTEXT ===" in system_content


# ---------------------------------------------------------------------------
# 5. Anonymous and Persistent Chat Both Support RAG
# ---------------------------------------------------------------------------

def test_9_anonymous_and_persistent_chat_both_support_rag(
    test_client: TestClient,
    db_session: Session,
    test_user: User,
    verified_context_with_skill: VerifiedContext,
):
    """Verify both anonymous and persistent chat modes execute RAG retrieval seamlessly."""
    # (A) Anonymous mode
    payload_anon = {
        "user_query": "Explain my Python status",
        "conversation_id": None,
        "verified_context": verified_context_with_skill.model_dump(mode="json"),
    }
    with patch.object(RAGService, "retrieve", return_value=[]):
        with patch("app.ai.chatbot.service.QwenClient") as MockQwen:
            mock_inst = MockQwen.return_value
            mock_inst.model = "qwen3:8b"
            mock_msg = MagicMock()
            mock_msg.content = "Python is partial."
            mock_resp = MagicMock()
            mock_resp.message = mock_msg
            mock_resp.model = "qwen3:8b"
            mock_resp.total_duration = 1000
            mock_resp.load_duration = 100
            mock_resp.prompt_eval_count = 50
            mock_resp.eval_count = 25
            mock_inst.chat.return_value = mock_resp

            resp_anon = test_client.post("/api/v1/ai/chat", json=payload_anon)
            assert resp_anon.status_code == 200
            assert resp_anon.json()["status"] == "EXPLANATORY"

    # (B) Persistent mode
    conv = Conversation(
        id=uuid4(),
        user_id=test_user.id,
        title="Python Conversation",
    )
    db_session.add(conv)
    db_session.commit()

    payload_persist = {
        "user_query": "Explain my Python status",
        "conversation_id": str(conv.id),
        "verified_context": verified_context_with_skill.model_dump(mode="json"),
    }
    with patch.object(RAGService, "retrieve", return_value=[]):
        with patch("app.ai.chatbot.service.QwenClient") as MockQwen:
            mock_inst = MockQwen.return_value
            mock_inst.model = "qwen3:8b"
            mock_msg = MagicMock()
            mock_msg.content = "Python is partial (persistent)."
            mock_resp = MagicMock()
            mock_resp.message = mock_msg
            mock_resp.model = "qwen3:8b"
            mock_resp.total_duration = 1000
            mock_resp.load_duration = 100
            mock_resp.prompt_eval_count = 50
            mock_resp.eval_count = 25
            mock_inst.chat.return_value = mock_resp

            resp_persist = test_client.post(
                "/api/v1/ai/chat",
                json=payload_persist,
                headers={"X-User-Id": str(test_user.id)},
            )
            assert resp_persist.status_code == 200
            data = resp_persist.json()
            assert data["status"] == "EXPLANATORY"
            assert data["conversation_id"] == str(conv.id)
            assert data["message_id"] is not None

            # Verify message persisted in database
            msg_count = db_session.query(Message).filter(Message.conversation_id == conv.id).count()
            assert msg_count == 2  # 1 user + 1 assistant

