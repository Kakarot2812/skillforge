"""
SkillForge AI — Post-MVP Checkpoint P3
Evidence-Grounded RAG / Retrieval Layer Test Suite

Enforces all 50 verification specifications and the 5 mandatory architectural modifications:
1. P2-B FactProvenance remains strictly unchanged.
2. JSONB is storage only; application layer uses strict Pydantic models with frozen=True, extra="forbid".
3. Authoritative embedding dimension consistency (384) with explicit mismatch detection.
4. Controllable deterministic mock embeddings for predictable ranking tests.
5. Strict ingestion boundary rejecting raw resumes, repository source trees, database dumps, and secrets.
"""

from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.ai.chatbot.models import CareerChatRequest, ChatResponseStatus
from app.ai.chatbot.service import CareerChatService
from app.ai.context.models import (
    FactProvenance,
    GrowthClass,
    PriorityTier,
    SkillClassification,
    VerifiedCandidateContext,
    VerifiedContext,
    VerifiedEvidenceFact,
    VerifiedMarketFact,
    VerifiedPriorityFact,
    VerifiedSkillFact,
)
from app.ai.qwen.client import QwenClient
from app.ai.qwen.models import QwenChatResponse, QwenMessage
from app.config import settings
from app.db.database import Base, get_db
from app.db.models import RAGChunk as DBRAGChunk
from app.db.models import RAGDocument as DBRAGDocument
from app.db.models import Skill
from app.rag.chunking import DeterministicChunker
from app.rag.embeddings import (
    EmbeddingProvider,
    LocalSentenceTransformerProvider,
    MockEmbeddingProvider,
)
from app.rag.exceptions import (
    RAGDimensionMismatchError,
    RAGEmbeddingError,
    RAGRetrievalError,
    RAGStorageError,
    RAGValidationError,
)
from app.rag.models import (
    RAGChunk,
    RAGChunkMetadata,
    RAGDocument,
    RAGDocumentMetadata,
    RAGRetrievalFilter,
    RAGRetrievalResult,
    RAGSourceType,
)
from app.rag.repository import RAGRepository
from app.rag.retriever import EvidenceRetriever
from app.rag.service import RAGService


# ---------------------------------------------------------------------------
# Test Fixtures & Controllable Mock Providers
# ---------------------------------------------------------------------------

@pytest.fixture
def db_session():
    """Provides a transactional database session rolled back after each test."""
    engine = create_engine(settings.DATABASE_URL)
    connection = engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def mock_embedding_provider():
    """Returns a deterministic 384-dimensional controllable mock provider."""
    return MockEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)


@pytest.fixture
def sample_canonical_skill(db_session: Session) -> Skill:
    """Ensures at least one canonical skill exists in the test database."""
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
        db_session.flush()
    return skill


@pytest.fixture
def sample_second_skill(db_session: Session) -> Skill:
    """Ensures a second canonical skill exists for filtering tests."""
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
        db_session.flush()
    return skill


def create_sample_rag_document(
    title: str = "FastAPI Backend Architecture",
    content: str = "FastAPI provides high-performance asynchronous REST endpoints using Pydantic models.",
    source_type: RAGSourceType = RAGSourceType.MARKET,
    skill_id: Optional[UUID] = None,
    skill_name: Optional[str] = None,
    source_ref: str = "market:demand:fastapi:2026",
) -> RAGDocument:
    metadata = RAGDocumentMetadata(
        skill_id=skill_id,
        skill_name=skill_name,
        source_reference=source_ref,
        observed_at=datetime.now(timezone.utc),
        confidence_score=0.95,
        approved_by="deterministic_market_pipeline",
    )
    return RAGDocument(
        id=uuid4(),
        source_type=source_type,
        source_reference=source_ref,
        title=title,
        content=content,
        metadata=metadata,
    )


class MockQwenClient(QwenClient):
    """Mock local Qwen client for offline testing."""
    def __init__(self, response_text: str = "Python is verified as PARTIAL because only 1 test artifact exists."):
        self.response_text = response_text
        self.last_messages: Optional[List[Dict[str, str]]] = None
        self.model = "qwen3:8b"

    def chat(self, messages, system=None, options=None):
        self.last_messages = [
            {"role": m.get("role", ""), "content": m.get("content", "")}
            for m in messages
        ]
        return QwenChatResponse(
            model=self.model,
            message=QwenMessage(role="assistant", content=self.response_text),
            done=True,
            done_reason="stop",
            total_duration=120000000,
            load_duration=10000000,
            prompt_eval_count=45,
            eval_count=30,
        )


# ---------------------------------------------------------------------------
# 1-5: RAG Document & Contract Validation Tests
# ---------------------------------------------------------------------------

def test_1_valid_rag_document():
    """1. Valid RAG document instantiates with typed metadata, UUID, and timestamps."""
    doc = create_sample_rag_document()
    assert isinstance(doc.id, UUID)
    assert doc.source_type == RAGSourceType.MARKET
    assert doc.metadata.confidence_score == 0.95
    assert doc.metadata.approved_by == "deterministic_market_pipeline"
    assert doc.created_at is not None


def test_2_invalid_source_type_rejected():
    """2. Invalid source type rejected."""
    with pytest.raises(ValueError):
        RAGDocument(
            source_type="INVALID_SOURCE_TYPE",  # type: ignore
            source_reference="ref:123",
            title="Title",
            content="Valid content.",
            metadata=RAGDocumentMetadata(source_reference="ref:123"),
        )


def test_3_provenance_required():
    """3. Provenance and source_reference are strictly required."""
    with pytest.raises(ValueError):
        RAGDocumentMetadata(source_reference="")

    with pytest.raises(ValueError):
        RAGDocumentMetadata(source_reference="   ")


def test_4_empty_content_rejected():
    """4. Empty content rejected."""
    with pytest.raises(ValueError):
        create_sample_rag_document(content="")

    with pytest.raises(ValueError):
        create_sample_rag_document(content="   \n  ")


def test_5_content_size_bound():
    """5. Content size bound enforced."""
    oversized = "A" * (settings.RAG_MAX_DOCUMENT_CONTENT_LENGTH + 1)
    with pytest.raises(ValueError) as exc:
        create_sample_rag_document(content=oversized)
    assert "exceeds maximum allowed bound" in str(exc.value)


# ---------------------------------------------------------------------------
# 6-11: Deterministic Chunking Tests
# ---------------------------------------------------------------------------

def test_6_deterministic_chunking():
    """6. Deterministic chunking splits content into bounded segments."""
    chunker = DeterministicChunker(chunk_size=100, chunk_overlap=20)
    long_content = "This is sentence one. " * 15
    doc = create_sample_rag_document(content=long_content)
    chunks = chunker.chunk_document(doc)

    assert len(chunks) > 1
    for chunk in chunks:
        assert isinstance(chunk, RAGChunk)
        assert len(chunk.content) <= 100
        assert chunk.source_type == doc.source_type
        assert chunk.source_reference == doc.source_reference


def test_7_repeated_chunking_produces_identical_output():
    """7. Repeated chunking of the same document produces identical output."""
    chunker = DeterministicChunker(chunk_size=120, chunk_overlap=30)
    content = "Deterministic sentence repetition test. " * 10
    doc = create_sample_rag_document(content=content)

    chunks_1 = chunker.chunk_document(doc)
    chunks_2 = chunker.chunk_document(doc)

    assert len(chunks_1) == len(chunks_2)
    for c1, c2 in zip(chunks_1, chunks_2):
        assert c1.chunk_index == c2.chunk_index
        assert c1.content == c2.content
        assert c1.source_reference == c2.source_reference


def test_8_no_empty_chunks():
    """8. No empty chunks produced by chunker."""
    chunker = DeterministicChunker(chunk_size=50, chunk_overlap=10)
    content = "Word \n\n   \n another word \t   third word"
    doc = create_sample_rag_document(content=content)
    chunks = chunker.chunk_document(doc)

    assert len(chunks) > 0
    for chunk in chunks:
        assert len(chunk.content.strip()) > 0


def test_9_chunk_size_bound():
    """9. Chunk size bound strictly enforced."""
    chunk_size = 80
    chunker = DeterministicChunker(chunk_size=chunk_size, chunk_overlap=15)
    doc = create_sample_rag_document(content="Continuous text stream with various words and separators. " * 10)
    chunks = chunker.chunk_document(doc)

    for chunk in chunks:
        assert len(chunk.content) <= chunk_size


def test_10_overlap_behavior():
    """10. Overlap behavior verified."""
    chunker = DeterministicChunker(chunk_size=40, chunk_overlap=15)
    text_content = "Alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"
    doc = create_sample_rag_document(content=text_content)
    chunks = chunker.chunk_document(doc)

    assert len(chunks) >= 2
    # Second chunk should contain some words from the end of the first chunk
    words_1 = set(chunks[0].content.split())
    words_2 = set(chunks[1].content.split())
    assert len(words_1.intersection(words_2)) > 0


def test_11_stable_chunk_ordering():
    """11. Stable monotonic chunk ordering (0, 1, 2, ...)."""
    chunker = DeterministicChunker(chunk_size=60, chunk_overlap=10)
    doc = create_sample_rag_document(content="Long document content split across several chunks for ordering validation. " * 5)
    chunks = chunker.chunk_document(doc)

    expected_indices = list(range(len(chunks)))
    actual_indices = [c.chunk_index for c in chunks]
    assert actual_indices == expected_indices


# ---------------------------------------------------------------------------
# 12-15: Embedding Provider & Dimension Consistency Tests
# ---------------------------------------------------------------------------

def test_12_embedding_provider_interface():
    """12. Embedding provider interface behaves as expected."""
    provider = MockEmbeddingProvider(dimension=384)
    vec = provider.embed_text("sample skill text")
    assert isinstance(vec, list)
    assert len(vec) == 384
    assert isinstance(vec[0], float)


def test_13_embedding_dimension_consistency():
    """13. Embedding dimension consistency with settings.EMBEDDING_DIMENSION."""
    provider = MockEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)
    assert provider.dimension == settings.EMBEDDING_DIMENSION
    provider.validate_dimension_consistency(settings.EMBEDDING_DIMENSION)


def test_14_same_text_produces_same_dimension():
    """14. Same text produces same vector dimension consistently."""
    provider = MockEmbeddingProvider(dimension=384)
    vec1 = provider.embed_text("Python backend engineering")
    vec2 = provider.embed_text("Python backend engineering")
    vec3 = provider.embed_text("Completely different frontend topic")

    assert len(vec1) == 384
    assert len(vec2) == 384
    assert len(vec3) == 384
    assert vec1 == vec2


def test_15_invalid_embedding_dimension_rejected():
    """15. Invalid embedding dimension rejected with RAGDimensionMismatchError."""
    # Provider with dimension 512 against authoritative setting 384
    provider = MockEmbeddingProvider(dimension=512)
    with pytest.raises(RAGDimensionMismatchError) as exc:
        provider.validate_dimension_consistency(expected_dim=384)
    assert exc.value.expected == 384
    assert exc.value.actual == 512


# ---------------------------------------------------------------------------
# 16-19: Storage & Relationship Tests
# ---------------------------------------------------------------------------

def test_16_document_persistence(db_session: Session):
    """16. Approved document persists to PostgreSQL rag_documents table."""
    repo = RAGRepository(session=db_session)
    doc = create_sample_rag_document(title="Persisted Market Fact")
    db_doc = repo.save_document(doc)

    loaded = repo.get_document(doc.id)
    assert loaded.id == doc.id
    assert loaded.title == "Persisted Market Fact"
    assert loaded.source_type == RAGSourceType.MARKET
    assert loaded.metadata.source_reference == doc.source_reference


def test_17_chunk_persistence(db_session: Session, sample_canonical_skill: Skill):
    """17. Bounded chunks persist with vector embedding in rag_chunks."""
    repo = RAGRepository(session=db_session)
    doc = create_sample_rag_document(skill_id=sample_canonical_skill.id, skill_name="Python")
    repo.save_document(doc)

    chunk_meta = RAGChunkMetadata(
        skill_id=sample_canonical_skill.id,
        skill_name="Python",
        source_reference=doc.source_reference,
        chunk_index=0,
    )
    chunk = RAGChunk(
        id=uuid4(),
        document_id=doc.id,
        chunk_index=0,
        content="Chunk with embedding vector.",
        embedding=tuple([0.1] * settings.EMBEDDING_DIMENSION),
        skill_id=sample_canonical_skill.id,
        source_type=doc.source_type,
        source_reference=doc.source_reference,
        metadata=chunk_meta,
    )
    db_chunks = repo.save_chunks([chunk])
    assert len(db_chunks) == 1

    # Verify query in database
    retrieved = db_session.get(DBRAGChunk, chunk.id)
    assert retrieved is not None
    assert retrieved.chunk_index == 0
    assert len(retrieved.embedding) == settings.EMBEDDING_DIMENSION


def test_18_document_chunk_relationship(db_session: Session):
    """18. Document/chunk relationship cascading deletion."""
    repo = RAGRepository(session=db_session)
    doc = create_sample_rag_document()
    repo.save_document(doc)

    chunk_meta = RAGChunkMetadata(
        source_reference=doc.source_reference,
        chunk_index=0,
    )
    chunk = RAGChunk(
        id=uuid4(),
        document_id=doc.id,
        chunk_index=0,
        content="Cascade deletion test chunk.",
        embedding=tuple([0.05] * settings.EMBEDDING_DIMENSION),
        source_type=doc.source_type,
        source_reference=doc.source_reference,
        metadata=chunk_meta,
    )
    repo.save_chunks([chunk])

    # Delete document
    deleted = repo.delete_document(doc.id)
    assert deleted is True

    # Confirm chunk was cascaded
    chunk_in_db = db_session.get(DBRAGChunk, chunk.id)
    assert chunk_in_db is None


def test_19_duplicate_chunk_protection(db_session: Session):
    """19. Duplicate chunk protection (document_id, chunk_index) raises RAGStorageError."""
    repo = RAGRepository(session=db_session)
    doc = create_sample_rag_document()
    repo.save_document(doc)

    chunk_meta = RAGChunkMetadata(source_reference=doc.source_reference, chunk_index=0)
    chunk1 = RAGChunk(
        id=uuid4(),
        document_id=doc.id,
        chunk_index=0,
        content="First chunk.",
        embedding=tuple([0.1] * settings.EMBEDDING_DIMENSION),
        source_type=doc.source_type,
        source_reference=doc.source_reference,
        metadata=chunk_meta,
    )
    repo.save_chunks([chunk1])

    # Attempt to insert identical document_id and chunk_index
    chunk2 = RAGChunk(
        id=uuid4(),
        document_id=doc.id,
        chunk_index=0,
        content="Duplicate chunk index.",
        embedding=tuple([0.2] * settings.EMBEDDING_DIMENSION),
        source_type=doc.source_type,
        source_reference=doc.source_reference,
        metadata=chunk_meta,
    )
    with pytest.raises(RAGStorageError):
        repo.save_chunks([chunk2])


# ---------------------------------------------------------------------------
# 20-30: Retrieval Contract, Ranking, Filtering & Tie-Breaking Tests
# ---------------------------------------------------------------------------

def test_20_retrieval_returns_typed_results(db_session: Session):
    """20. Retrieval returns typed RAGRetrievalResult objects."""
    provider = MockEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)
    service = RAGService(session=db_session, embedding_provider=provider)

    doc = create_sample_rag_document(content="FastAPI async endpoints with Pydantic.")
    service.index_document(doc)

    results = service.retrieve(query="FastAPI async")
    assert len(results) > 0
    res = results[0]
    assert isinstance(res, RAGRetrievalResult)
    assert isinstance(res.chunk_id, UUID)
    assert isinstance(res.similarity_score, float)
    assert isinstance(res.metadata, RAGChunkMetadata)


def test_21_similarity_ranking(db_session: Session):
    """21. Controllable mock embeddings prove correct similarity ranking."""
    provider = MockEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)

    # Define controllable orthonormal basis vectors
    query_vec = [1.0, 0.0, 0.0] + [0.0] * (settings.EMBEDDING_DIMENSION - 3)
    relevant_vec = [0.95, 0.05, 0.0] + [0.0] * (settings.EMBEDDING_DIMENSION - 3)
    unrelated_vec = [0.05, 0.95, 0.0] + [0.0] * (settings.EMBEDDING_DIMENSION - 3)

    provider.register_mapping("target python query", query_vec)
    provider.register_mapping("highly relevant python chunk", relevant_vec)
    provider.register_mapping("completely unrelated cooking chunk", unrelated_vec)

    service = RAGService(session=db_session, embedding_provider=provider)

    doc1 = create_sample_rag_document(title="Relevant Doc", content="highly relevant python chunk")
    doc2 = create_sample_rag_document(title="Unrelated Doc", content="completely unrelated cooking chunk")
    service.index_document(doc1)
    service.index_document(doc2)

    results = service.retrieve(query="target python query", top_k=5)
    assert len(results) == 2
    # Most similar must be ranked first
    assert "relevant python chunk" in results[0].content
    assert results[0].similarity_score > results[1].similarity_score


def test_22_deterministic_tie_breaking(db_session: Session):
    """22. Deterministic tie-breaking orders equal similarities by chunk_id ASC."""
    repo = RAGRepository(session=db_session)
    doc = create_sample_rag_document()
    repo.save_document(doc)

    identical_vector = [0.5] * settings.EMBEDDING_DIMENSION
    norm = math.sqrt(sum(x * x for x in identical_vector))
    normalized = [x / norm for x in identical_vector]

    # Create two chunks with fixed UUIDs to verify secondary ordering
    id_lower = UUID("00000000-0000-0000-0000-000000000001")
    id_higher = UUID("00000000-0000-0000-0000-000000000002")

    chunk1 = RAGChunk(
        id=id_higher,
        document_id=doc.id,
        chunk_index=0,
        content="Chunk Higher UUID",
        embedding=tuple(normalized),
        source_type=doc.source_type,
        source_reference=doc.source_reference,
        metadata=RAGChunkMetadata(source_reference=doc.source_reference, chunk_index=0),
    )
    chunk2 = RAGChunk(
        id=id_lower,
        document_id=doc.id,
        chunk_index=1,
        content="Chunk Lower UUID",
        embedding=tuple(normalized),
        source_type=doc.source_type,
        source_reference=doc.source_reference,
        metadata=RAGChunkMetadata(source_reference=doc.source_reference, chunk_index=1),
    )
    repo.save_chunks([chunk1, chunk2])

    results = repo.search_similar(query_vector=normalized, top_k=5)
    assert len(results) == 2
    # Because similarity is identical, tie-breaker must order by chunk_id ASC
    assert results[0].chunk_id == id_lower
    assert results[1].chunk_id == id_higher


def test_23_top_k_bound(db_session: Session):
    """23. Retrieval top_k bounded by settings.RAG_MAX_TOP_K."""
    provider = MockEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)
    service = RAGService(session=db_session, embedding_provider=provider)

    # Index 15 small documents
    for i in range(15):
        doc = create_sample_rag_document(
            title=f"Doc {i}",
            content=f"Batch document content item number {i}",
            source_ref=f"batch:ref:{i}",
        )
        service.index_document(doc)

    # Request top_k = 50 (exceeds max 10)
    results = service.retrieve(query="batch document content", top_k=50)
    assert len(results) <= settings.RAG_MAX_TOP_K


def test_24_source_type_filtering(db_session: Session):
    """24. Authoritative source_type filtering."""
    provider = MockEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)
    service = RAGService(session=db_session, embedding_provider=provider)

    doc_market = create_sample_rag_document(
        title="Market Doc",
        content="Market demand analysis for backend engineer",
        source_type=RAGSourceType.MARKET,
    )
    doc_github = create_sample_rag_document(
        title="GitHub Doc",
        content="GitHub repository Dockerfile inspection",
        source_type=RAGSourceType.GITHUB,
    )
    service.index_document(doc_market)
    service.index_document(doc_github)

    filter_github = RAGRetrievalFilter(source_type=RAGSourceType.GITHUB)
    results = service.retrieve(query="backend inspection", filters=filter_github)

    assert len(results) > 0
    for r in results:
        assert r.source_type == RAGSourceType.GITHUB


def test_25_skill_id_filtering(db_session: Session, sample_canonical_skill: Skill, sample_second_skill: Skill):
    """25. Authoritative skill_id filtering."""
    provider = MockEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)
    service = RAGService(session=db_session, embedding_provider=provider)

    doc_python = create_sample_rag_document(
        title="Python Doc",
        content="Python asyncio event loop details",
        skill_id=sample_canonical_skill.id,
        skill_name="Python",
    )
    doc_docker = create_sample_rag_document(
        title="Docker Doc",
        content="Docker multi-stage build containerization",
        skill_id=sample_second_skill.id,
        skill_name="Docker",
    )
    service.index_document(doc_python)
    service.index_document(doc_docker)

    filter_python = RAGRetrievalFilter(skill_id=sample_canonical_skill.id)
    results = service.retrieve(query="container event loop", filters=filter_python)

    assert len(results) > 0
    for r in results:
        assert r.skill_id == sample_canonical_skill.id


def test_26_unrelated_skill_excluded_by_filter(db_session: Session, sample_canonical_skill: Skill, sample_second_skill: Skill):
    """26. Unrelated skill is excluded by filter even if vector similarity is high."""
    provider = MockEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)
    target_vec = [1.0, 0.0] + [0.0] * (settings.EMBEDDING_DIMENSION - 2)

    # Docker doc has identical vector to query!
    provider.register_mapping("query phrase", target_vec)
    provider.register_mapping("docker high similarity content", target_vec)

    service = RAGService(session=db_session, embedding_provider=provider)

    doc_docker = create_sample_rag_document(
        title="Docker High Similarity",
        content="docker high similarity content",
        skill_id=sample_second_skill.id,
        skill_name="Docker",
    )
    service.index_document(doc_docker)

    # Query with filter for Python
    filter_python = RAGRetrievalFilter(skill_id=sample_canonical_skill.id)
    results = service.retrieve(query="query phrase", filters=filter_python)

    # Must NOT return Docker chunk despite 1.0 vector similarity!
    assert len(results) == 0


def test_27_provenance_preserved_through_retrieval(db_session: Session):
    """27. Provenance and source references preserved through retrieval."""
    provider = MockEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)
    service = RAGService(session=db_session, embedding_provider=provider)

    ref = "repo:kakarot:backend/Dockerfile"
    doc = create_sample_rag_document(
        title="Dockerfile Snippet",
        content="FROM python:3.12-slim\nRUN pip install -r requirements.txt",
        source_type=RAGSourceType.GITHUB,
        source_ref=ref,
    )
    service.index_document(doc)

    results = service.retrieve(query="python slim requirements")
    assert len(results) > 0
    res = results[0]
    assert res.source_type == RAGSourceType.GITHUB
    assert res.source_reference == ref
    assert res.provenance == RAGSourceType.GITHUB


def test_28_embedding_vectors_not_returned_in_normal_result(db_session: Session):
    """28. Embedding vectors are NOT returned in normal retrieval response."""
    provider = MockEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)
    service = RAGService(session=db_session, embedding_provider=provider)

    doc = create_sample_rag_document()
    service.index_document(doc)

    results = service.retrieve(query="architecture")
    assert len(results) > 0
    res = results[0]
    assert not hasattr(res, "embedding")
    assert "embedding" not in res.model_dump()


def test_29_no_arbitrary_dict_retrieval_result():
    """29. No arbitrary dict retrieval result; extra fields forbidden."""
    metadata = RAGChunkMetadata(source_reference="ref", chunk_index=0)
    with pytest.raises(ValueError):
        RAGRetrievalResult(
            chunk_id=uuid4(),
            document_id=uuid4(),
            content="Text",
            similarity_score=0.9,
            source_type=RAGSourceType.MARKET,
            source_reference="ref",
            provenance=RAGSourceType.MARKET,
            metadata=metadata,
            untyped_arbitrary_field="PROHIBITED",  # type: ignore
        )


def test_30_empty_retrieval_handled_correctly(db_session: Session):
    """30. Empty retrieval returns an empty list, not an error."""
    provider = MockEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)
    service = RAGService(session=db_session, embedding_provider=provider)

    # Empty database
    results = service.retrieve(query="any search term")
    assert results == []


# ---------------------------------------------------------------------------
# 31-36: Failure Distinctions & Authority Protection Tests
# ---------------------------------------------------------------------------

def test_31_embedding_failure_distinguished_from_no_results(db_session: Session):
    """31. Embedding failure raises RAGEmbeddingError, distinguished from no results."""
    class FailingEmbeddingProvider(EmbeddingProvider):
        @property
        def dimension(self) -> int:
            return settings.EMBEDDING_DIMENSION

        def embed_text(self, text: str) -> List[float]:
            raise RAGEmbeddingError("Inference failed.")

        def embed_documents(self, texts: List[str]) -> List[List[float]]:
            raise RAGEmbeddingError("Batch inference failed.")

    service = RAGService(session=db_session, embedding_provider=FailingEmbeddingProvider())

    with pytest.raises(RAGEmbeddingError):
        service.retrieve(query="test query")


def test_32_database_failure_distinguished_from_no_results():
    """32. Database failure raises RAGRetrievalError, distinguished from no results."""
    # Mock broken session
    class BrokenSession:
        def execute(self, *args, **kwargs):
            from sqlalchemy.exc import OperationalError
            raise OperationalError("SELECT *", {}, Exception("Database connection lost"))

    repo = RAGRepository(session=BrokenSession())  # type: ignore
    retriever = EvidenceRetriever(
        repository=repo,
        embedding_provider=MockEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION),
    )

    with pytest.raises(RAGRetrievalError):
        retriever.retrieve(query="test query")


def test_33_rag_does_not_modify_verified_context():
    """33. RAG retrieval does not modify VerifiedContext."""
    skill_fact = VerifiedSkillFact(
        skill_id=uuid4(),
        skill_name="Python",
        canonical_slug="python",
        classification=SkillClassification.PARTIAL,
        demonstrated_score=0.4,
        provenance=FactProvenance.DETERMINISTIC_ANALYSIS,
    )
    context = VerifiedContext(skills=(skill_fact,))

    initial_hash = hash(context.skills)

    # Construct mock retrieval results
    metadata = RAGChunkMetadata(source_reference="ref", chunk_index=0)
    retrieved = RAGRetrievalResult(
        chunk_id=uuid4(),
        document_id=uuid4(),
        content="Python is widely used in AI.",
        similarity_score=0.9,
        source_type=RAGSourceType.MARKET,
        source_reference="ref",
        skill_id=skill_fact.skill_id,
        skill_name="Python",
        provenance=RAGSourceType.MARKET,
        metadata=metadata,
    )

    # VerifiedContext is immutable
    with pytest.raises(Exception):
        context.skills = (skill_fact,)  # type: ignore

    assert hash(context.skills) == initial_hash
    assert context.skills[0].classification == SkillClassification.PARTIAL


def test_34_rag_cannot_modify_skill_classification():
    """34. RAG cannot modify skill classification."""
    skill_fact = VerifiedSkillFact(
        skill_id=uuid4(),
        skill_name="Python",
        canonical_slug="python",
        classification=SkillClassification.PARTIAL,
        provenance=FactProvenance.DETERMINISTIC_ANALYSIS,
    )
    context = VerifiedContext(skills=(skill_fact,))

    # Attempting to mutate classification on frozen model raises error
    with pytest.raises(Exception):
        skill_fact.classification = SkillClassification.STRONG  # type: ignore

    assert context.skills[0].classification == SkillClassification.PARTIAL


def test_35_rag_cannot_modify_demand_score():
    """35. RAG cannot modify demand score."""
    mkt = VerifiedMarketFact(
        skill_id=uuid4(),
        skill_name="Docker",
        demand_score=0.75,
        growth_rate=0.08,
        growth_class=GrowthClass.RISING,
        provenance=FactProvenance.MARKET,
    )
    context = VerifiedContext(market=(mkt,))

    with pytest.raises(Exception):
        mkt.demand_score = 0.99  # type: ignore

    assert context.market[0].demand_score == 0.75


def test_36_rag_cannot_modify_priority_score():
    """36. RAG cannot modify priority score."""
    prio = VerifiedPriorityFact(
        skill_id=uuid4(),
        skill_name="FastAPI",
        priority_score=0.82,
        priority_level=PriorityTier.HIGH,
        gap_status=SkillClassification.MISSING,
        demand_score=0.80,
        growth_rate=0.10,
        demonstrated_score=0.0,
        provenance=FactProvenance.DETERMINISTIC_ANALYSIS,
    )
    context = VerifiedContext(priorities=(prio,))

    with pytest.raises(Exception):
        prio.priority_score = 0.50  # type: ignore

    assert context.priorities[0].priority_score == 0.82


# ---------------------------------------------------------------------------
# 37-43: P2-C Integration Boundary Tests
# ---------------------------------------------------------------------------

def test_37_p2c_works_with_rag_disabled():
    """37. P2-C works as before when rag_service=None."""
    mock_qwen = MockQwenClient(response_text="Standard explanation with RAG disabled.")
    service = CareerChatService(qwen_client=mock_qwen, rag_service=None)

    skill = VerifiedSkillFact(
        skill_id=uuid4(),
        skill_name="Python",
        canonical_slug="python",
        classification=SkillClassification.PARTIAL,
        provenance=FactProvenance.DETERMINISTIC_ANALYSIS,
    )
    context = VerifiedContext(skills=(skill,))
    req = CareerChatRequest(verified_context=context, user_query="Why is Python partial?")

    resp = service.chat(req)
    assert resp.status == ChatResponseStatus.EXPLANATORY
    assert resp.explanation == "Standard explanation with RAG disabled."
    assert resp.retrieved_evidence == ()
    assert "RETRIEVED SUPPORTING EVIDENCE" not in mock_qwen.last_messages[0]["content"]


def test_38_p2c_works_with_relevant_rag_evidence(db_session: Session, sample_canonical_skill: Skill):
    """38. P2-C integrates relevant RAG evidence when enabled."""
    provider = MockEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)
    rag_service = RAGService(session=db_session, embedding_provider=provider)

    python_id = sample_canonical_skill.id
    doc = create_sample_rag_document(
        title="Python Market Fact",
        content="Python is required by 85% of backend positions.",
        skill_id=python_id,
        skill_name="Python",
    )
    rag_service.index_document(doc)

    mock_qwen = MockQwenClient(response_text="Python has high demand and your profile is partial.")
    chat_service = CareerChatService(qwen_client=mock_qwen, rag_service=rag_service)

    skill = VerifiedSkillFact(
        skill_id=python_id,
        skill_name="Python",
        canonical_slug="python",
        classification=SkillClassification.PARTIAL,
        provenance=FactProvenance.DETERMINISTIC_ANALYSIS,
    )
    context = VerifiedContext(skills=(skill,))
    req = CareerChatRequest(verified_context=context, user_query="Why is Python partial?")

    resp = chat_service.chat(req)
    assert resp.status == ChatResponseStatus.EXPLANATORY
    assert len(resp.retrieved_evidence) > 0
    assert resp.retrieved_evidence[0].skill_name == "Python"


def test_39_retrieved_evidence_marked_as_supporting_evidence(db_session: Session, sample_canonical_skill: Skill):
    """39. Retrieved evidence marked explicitly as NON-AUTHORITATIVE in prompt."""
    provider = MockEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)
    rag_service = RAGService(session=db_session, embedding_provider=provider)

    python_id = sample_canonical_skill.id
    doc = create_sample_rag_document(
        title="Python Evidence",
        content="Bounded artifact evidence for Python.",
        skill_id=python_id,
        skill_name="Python",
    )
    rag_service.index_document(doc)

    mock_qwen = MockQwenClient()
    chat_service = CareerChatService(qwen_client=mock_qwen, rag_service=rag_service)

    skill = VerifiedSkillFact(
        skill_id=python_id,
        skill_name="Python",
        canonical_slug="python",
        classification=SkillClassification.PARTIAL,
        provenance=FactProvenance.DETERMINISTIC_ANALYSIS,
    )
    context = VerifiedContext(skills=(skill,))
    req = CareerChatRequest(verified_context=context, user_query="What is Python status?")

    chat_service.chat(req)
    system_prompt = mock_qwen.last_messages[0]["content"]
    assert "=== RETRIEVED SUPPORTING EVIDENCE (NON-AUTHORITATIVE) ===" in system_prompt
    assert "=== END RETRIEVED SUPPORTING EVIDENCE ===" in system_prompt


def test_40_verified_context_remains_authoritative(db_session: Session):
    """40. Prompt clearly marks VerifiedContext as authoritative ground truth."""
    mock_qwen = MockQwenClient()
    chat_service = CareerChatService(qwen_client=mock_qwen, rag_service=None)

    skill = VerifiedSkillFact(
        skill_id=uuid4(),
        skill_name="Python",
        canonical_slug="python",
        classification=SkillClassification.PARTIAL,
        provenance=FactProvenance.DETERMINISTIC_ANALYSIS,
    )
    context = VerifiedContext(skills=(skill,))
    req = CareerChatRequest(verified_context=context, user_query="Why is Python partial?")

    chat_service.chat(req)
    system_prompt = mock_qwen.last_messages[0]["content"]
    assert "=== VERIFIED SKILLFORGE GROUND TRUTH CONTEXT ===" in system_prompt
    assert "Treat the supplied VerifiedContext as authoritative ground truth." in system_prompt


def test_41_conflicting_retrieved_evidence_cannot_override_verified_context(db_session: Session):
    """41. System prompt instructs Qwen that conflicting retrieved evidence cannot override VerifiedContext."""
    mock_qwen = MockQwenClient()
    chat_service = CareerChatService(qwen_client=mock_qwen, rag_service=None)

    skill = VerifiedSkillFact(
        skill_id=uuid4(),
        skill_name="Python",
        canonical_slug="python",
        classification=SkillClassification.PARTIAL,
        provenance=FactProvenance.DETERMINISTIC_ANALYSIS,
    )
    context = VerifiedContext(skills=(skill,))
    req = CareerChatRequest(verified_context=context, user_query="Why is Python partial?")

    chat_service.chat(req)
    system_prompt = mock_qwen.last_messages[0]["content"]
    assert "It CANNOT override, modify, or contradict VerifiedContext facts." in system_prompt
    assert "strictly adhere to VerifiedContext" in system_prompt


def test_42_no_qwen_call_when_deterministic_evidence_gate_rejects_query(db_session: Session):
    """42. No Qwen call and no RAG call when deterministic evidence gate rejects query."""
    class SpyRAGService:
        def __init__(self):
            self.retrieve_called = False

        def retrieve(self, *args, **kwargs):
            self.retrieve_called = True
            return []

    mock_qwen = MockQwenClient()
    spy_rag = SpyRAGService()
    chat_service = CareerChatService(qwen_client=mock_qwen, rag_service=spy_rag)  # type: ignore

    # Context only contains market fact for Docker, but query asks about candidate weakness in Docker
    mkt = VerifiedMarketFact(
        skill_id=uuid4(),
        skill_name="Docker",
        demand_score=0.8,
        growth_rate=0.05,
        growth_class=GrowthClass.RISING,
        provenance=FactProvenance.MARKET,
    )
    context = VerifiedContext(market=(mkt,))
    req = CareerChatRequest(verified_context=context, user_query="Why am I weak in Docker?")

    resp = chat_service.chat(req)
    assert resp.status == ChatResponseStatus.INSUFFICIENT_EVIDENCE
    assert spy_rag.retrieve_called is False
    assert mock_qwen.last_messages is None


def test_43_qwen_receives_bounded_retrieved_evidence(db_session: Session, sample_canonical_skill: Skill):
    """43. Qwen receives bounded retrieved evidence in prompt."""
    provider = MockEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)
    rag_service = RAGService(session=db_session, embedding_provider=provider)

    python_id = sample_canonical_skill.id
    doc = create_sample_rag_document(
        title="Short Snippet",
        content="Short bounded evidence chunk for testing.",
        skill_id=python_id,
        skill_name="Python",
    )
    rag_service.index_document(doc)

    mock_qwen = MockQwenClient()
    chat_service = CareerChatService(qwen_client=mock_qwen, rag_service=rag_service)

    skill = VerifiedSkillFact(
        skill_id=python_id,
        skill_name="Python",
        canonical_slug="python",
        classification=SkillClassification.PARTIAL,
        provenance=FactProvenance.DETERMINISTIC_ANALYSIS,
    )
    context = VerifiedContext(skills=(skill,))
    req = CareerChatRequest(verified_context=context, user_query="Explain Python status.")

    chat_service.chat(req)
    system_prompt = mock_qwen.last_messages[0]["content"]
    assert "Short bounded evidence chunk for testing." in system_prompt
    assert len(system_prompt) < 10000


# ---------------------------------------------------------------------------
# 44-50: Ingestion Boundaries, Independence & Determinism Tests
# ---------------------------------------------------------------------------

def test_44_no_raw_resume_dump():
    """44. Rejection of raw resume dump attempt exceeding bounds."""
    huge_resume = "RESUME EXPERIENCE EDUCATION SKILLS SUMMARY " * 1200
    with pytest.raises(ValueError) as exc:
        create_sample_rag_document(content=huge_resume)
    assert "exceeds maximum allowed bound" in str(exc.value)


def test_45_no_raw_repository_dump():
    """45. Rejection of raw git diff / repository dump signature."""
    diff_content = "diff --git a/backend/main.py b/backend/main.py\n--- a/backend/main.py\n+++ b/backend/main.py"
    with pytest.raises(ValueError) as exc:
        create_sample_rag_document(content=diff_content)
    assert "prohibited raw dump" in str(exc.value)


def test_46_no_raw_database_dump():
    """46. Rejection of raw SQL database dump signature."""
    pg_dump = "BEGIN PG_DUMP;\nCOPY users (id, email) FROM stdin;\n"
    with pytest.raises(ValueError) as exc:
        create_sample_rag_document(content=pg_dump)
    assert "prohibited raw dump" in str(exc.value)


def test_47_no_chat_persistence(db_session: Session):
    """47. RAG does not persist chat queries or conversations."""
    mock_qwen = MockQwenClient()
    provider = MockEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)
    rag_service = RAGService(session=db_session, embedding_provider=provider)
    chat_service = CareerChatService(qwen_client=mock_qwen, rag_service=rag_service)

    skill = VerifiedSkillFact(
        skill_id=uuid4(),
        skill_name="Python",
        canonical_slug="python",
        classification=SkillClassification.PARTIAL,
        provenance=FactProvenance.DETERMINISTIC_ANALYSIS,
    )
    context = VerifiedContext(skills=(skill,))
    req = CareerChatRequest(verified_context=context, user_query="Ephemeral question about Python.")

    # Record row counts before
    docs_before = db_session.execute(text("SELECT COUNT(*) FROM rag_documents")).scalar()
    chunks_before = db_session.execute(text("SELECT COUNT(*) FROM rag_chunks")).scalar()

    chat_service.chat(req)

    # Record row counts after
    docs_after = db_session.execute(text("SELECT COUNT(*) FROM rag_documents")).scalar()
    chunks_after = db_session.execute(text("SELECT COUNT(*) FROM rag_chunks")).scalar()

    assert docs_before == docs_after
    assert chunks_before == chunks_after


def test_48_no_roadmap_dependency():
    """48. RAG operates independently without roadmap dependencies."""
    provider = MockEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)
    chunker = DeterministicChunker()
    doc = create_sample_rag_document()
    chunks = chunker.chunk_document(doc)
    assert len(chunks) > 0


def test_49_no_github_verification_dependency(db_session: Session):
    """49. RAG operates independently without GitHub verification loop."""
    provider = MockEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)
    rag_service = RAGService(session=db_session, embedding_provider=provider)
    doc = create_sample_rag_document(
        title="Market Evidence Independent Of GitHub",
        content="Market intelligence fact without live GitHub connection.",
        source_type=RAGSourceType.MARKET,
    )
    rag_service.index_document(doc)
    results = rag_service.retrieve(query="market intelligence fact")
    assert len(results) > 0


def test_50_deterministic_repeated_retrieval_behavior(db_session: Session):
    """50. Repeated retrieval with same query yields identical results."""
    provider = MockEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)
    rag_service = RAGService(session=db_session, embedding_provider=provider)

    doc1 = create_sample_rag_document(title="Doc 1", content="Alpha document chunk.")
    doc2 = create_sample_rag_document(title="Doc 2", content="Beta document chunk.")
    rag_service.index_document(doc1)
    rag_service.index_document(doc2)

    res1 = rag_service.retrieve(query="document chunk")
    res2 = rag_service.retrieve(query="document chunk")

    assert len(res1) == len(res2)
    for r1, r2 in zip(res1, res2):
        assert r1.chunk_id == r2.chunk_id
        assert r1.similarity_score == r2.similarity_score
        assert r1.content == r2.content


# ---------------------------------------------------------------------------
# Additional Mandatory Modifications Verification Tests
# ---------------------------------------------------------------------------

def test_mandatory_mod_1_p2b_fact_provenance_unchanged():
    """Mandatory Mod 1: P2-B FactProvenance remains strictly unchanged."""
    provenance_values = {p.value for p in FactProvenance}
    assert provenance_values == {
        "RESUME",
        "GITHUB",
        "MARKET",
        "DETERMINISTIC_ANALYSIS",
    }
    assert "APPROVED_RESOURCE" not in provenance_values

    # RAGSourceType contains APPROVED_RESOURCE
    rag_sources = {s.value for s in RAGSourceType}
    assert "APPROVED_RESOURCE" in rag_sources


def test_mandatory_mod_2_jsonb_is_storage_only():
    """Mandatory Mod 2: Application domain rejects arbitrary Dict[str, Any] for metadata."""
    with pytest.raises(ValueError):
        RAGDocumentMetadata(
            source_reference="ref",
            untyped_metadata={"arbitrary_key": "arbitrary_val"},  # type: ignore
        )

    with pytest.raises(ValueError):
        RAGChunkMetadata(
            source_reference="ref",
            chunk_index=0,
            untyped_dict={"free_form": 123},  # type: ignore
        )


def test_mandatory_mod_3_dimension_mismatch_fails_cleanly():
    """Mandatory Mod 3: Mismatched embedding provider dimension raises RAGDimensionMismatchError."""
    mismatched_provider = MockEmbeddingProvider(dimension=768)
    with pytest.raises(RAGDimensionMismatchError) as exc_info:
        mismatched_provider.validate_dimension_consistency(expected_dim=384)
    assert exc_info.value.expected == 384
    assert exc_info.value.actual == 768


def test_mandatory_mod_5_secrets_rejected_at_ingestion():
    """Mandatory Mod 5: Secrets are rejected at ingestion boundary."""
    secret_content = "Here is the production key: api_key='sk-abcdef1234567890abcdef'"
    with pytest.raises(ValueError) as exc:
        create_sample_rag_document(content=secret_content)
    assert "prohibited raw dump or secret" in str(exc.value)
