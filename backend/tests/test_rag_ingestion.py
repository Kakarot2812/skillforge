"""
Comprehensive test suite for Checkpoint C7-B: Approved Evidence Ingestion.

Covers:
1. Approved resource eligibility
2. Unapproved resource exclusion
3. Market demand eligibility
4. Market job skill eligibility
5. Unmapped market jobs excluded
6. Exact source_reference values
7. Deterministic UUID5 IDs
8. Deterministic content
9. Deterministic metadata
10. Canonical skill_id preservation
11. SHA-256 content hash
12. Second ingestion is idempotent
13. Changed content causes replacement
14. Stale chunks are removed
15. Source-type separation
16. Raw market descriptions are not ingested
17. Raw JSON is not ingested
18. No secrets/private data are ingested
19. Embedding failure rollback
20. Database failure rollback
21. Structured ingestion summary
22. Empty/invalid content handling
23. Corpus count verification
"""

from datetime import datetime, timezone
import hashlib
from typing import List, Optional
from uuid import UUID, uuid4, uuid5, NAMESPACE_URL
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import (
    ApprovedResource,
    MarketJob,
    MarketJobSkill,
    MarketSkillDemand,
    Skill,
    RAGChunk as DBRAGChunk,
    RAGDocument as DBRAGDocument,
)
from app.rag.chunking import DeterministicChunker
from app.rag.embeddings import EmbeddingProvider, MockEmbeddingProvider
from app.rag.exceptions import RAGEmbeddingError, RAGValidationError
from app.rag.ingestion import (
    EvidenceIngestionService,
    build_market_demand_rag_document,
    build_market_job_rag_document,
    build_resource_rag_document,
    compute_document_content_hash,
)
from app.rag.models import RAGDocument, RAGSourceType
from app.rag.repository import RAGRepository


# ---------------------------------------------------------------------------
# Test Fixtures (Isolated via SQLAlchemy Savepoints)
# ---------------------------------------------------------------------------

@pytest.fixture
def db_session():
    """
    Provides a transactional database session using savepoints so that any
    commits inside the service commit to the savepoint and are completely
    undone at test teardown by trans.rollback(). Zero pollution of the database.
    """
    engine = create_engine(settings.DATABASE_URL)
    connection = engine.connect()
    trans = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    yield session

    session.close()
    trans.rollback()
    connection.close()


@pytest.fixture
def mock_embedding_provider():
    """Returns a deterministic 384-dimensional controllable mock provider."""
    return MockEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)


@pytest.fixture
def sample_skill(db_session: Session) -> Skill:
    """Provides a canonical Skill in the isolated session."""
    skill_id = uuid4()
    skill = Skill(
        id=skill_id,
        name=f"Python-Test-{skill_id.hex[:6]}",
        slug=f"python-test-{skill_id.hex[:6]}",
        category="Backend",
        description="Core programming language for backend and ML workflows.",
    )
    db_session.add(skill)
    db_session.flush()
    return skill


@pytest.fixture
def sample_approved_resource(db_session: Session, sample_skill: Skill) -> ApprovedResource:
    """Provides an approved resource."""
    res = ApprovedResource(
        id=uuid4(),
        skill_id=sample_skill.id,
        title="Official Python Tutorial",
        url="https://docs.python.org/3/tutorial/",
        resource_type="OFFICIAL_DOCS",
        provider="Python Software Foundation",
        difficulty="BEGINNER",
        estimated_minutes=240,
        is_approved=True,
        approval_source="CURATED_SEED",
    )
    db_session.add(res)
    db_session.flush()
    return res


@pytest.fixture
def sample_market_demand(db_session: Session, sample_skill: Skill) -> MarketSkillDemand:
    """Provides a canonical market demand record."""
    demand = MarketSkillDemand(
        id=uuid4(),
        skill_id=sample_skill.id,
        source="adzuna",
        job_count=45,
        sample_size=150,
        demand_share=0.30,
        demand_score=0.30,
        computed_at=datetime.now(timezone.utc),
    )
    db_session.add(demand)
    db_session.flush()
    return demand


@pytest.fixture
def sample_market_job_with_skill(
    db_session: Session, sample_skill: Skill
) -> tuple[MarketJob, MarketJobSkill]:
    """Provides a MarketJob with an extracted MarketJobSkill."""
    job = MarketJob(
        id=uuid4(),
        source="adzuna",
        external_job_id=f"job-{uuid4().hex[:8]}",
        title="Senior Python Backend Engineer",
        description="We are seeking a senior Python developer. Great benefits and medical insurance.",
        company_name="TechCorp India",
        location="Bengaluru, Karnataka",
        category="IT Jobs",
        redirect_url="https://example.com/job/123",
        raw_data={"benefits": "401k, health", "internal_id": 99999},
    )
    db_session.add(job)
    db_session.flush()

    job_skill = MarketJobSkill(
        id=uuid4(),
        market_job_id=job.id,
        skill_id=sample_skill.id,
        matched_alias="Python",
        source_field="title",
        evidence_text="Senior Python Backend Engineer with async experience",
        confidence_score=1.0,
    )
    db_session.add(job_skill)
    db_session.flush()
    return job, job_skill


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def test_1_approved_resource_eligibility(sample_approved_resource: ApprovedResource, sample_skill: Skill):
    """1. Approved resource with is_approved=True builds into a valid RAGDocument."""
    doc = build_resource_rag_document(sample_approved_resource, sample_skill)
    assert isinstance(doc, RAGDocument)
    assert doc.source_type == RAGSourceType.APPROVED_RESOURCE
    assert doc.metadata.skill_id == sample_skill.id
    assert doc.metadata.approved_by == "curated_learning_resource"
    assert "Official Python Tutorial" in doc.title


def test_2_unapproved_resource_exclusion(sample_approved_resource: ApprovedResource, sample_skill: Skill, db_session: Session, mock_embedding_provider):
    """2. Resource with is_approved=False raises RAGValidationError and is skipped by ingestion."""
    sample_approved_resource.is_approved = False
    db_session.flush()

    # Builder rejects unapproved resource
    with pytest.raises(RAGValidationError) as excinfo:
        build_resource_rag_document(sample_approved_resource, sample_skill)
    assert "is not approved" in str(excinfo.value)

    # Ingestion service query filters out unapproved resources
    service = EvidenceIngestionService(session=db_session, embedding_provider=mock_embedding_provider)
    summary = service.ingest_approved_resources()
    assert summary["failed"] == 0

    # The unapproved resource must NOT exist in RAG
    unapproved_ref = f"approved_resource:{sample_approved_resource.id}"
    assert service.repository.find_document_by_reference(RAGSourceType.APPROVED_RESOURCE, unapproved_ref) is None


def test_3_market_demand_eligibility(sample_market_demand: MarketSkillDemand, sample_skill: Skill):
    """3. MarketSkillDemand with valid metrics builds into a valid RAGDocument."""
    doc = build_market_demand_rag_document(sample_market_demand, sample_skill)
    assert doc.source_type == RAGSourceType.MARKET
    assert doc.metadata.skill_id == sample_skill.id
    assert "Market Demand Intelligence" in doc.title
    assert "0.3" in doc.content

    # Null demand_score raises RAGValidationError
    sample_market_demand.demand_score = None
    with pytest.raises(RAGValidationError):
        build_market_demand_rag_document(sample_market_demand, sample_skill)


def test_4_market_job_skill_eligibility(sample_market_job_with_skill, sample_skill: Skill):
    """4. Valid MarketJob and MarketJobSkill build into a valid RAGDocument."""
    job, job_skill = sample_market_job_with_skill
    doc = build_market_job_rag_document(job, job_skill, sample_skill)
    assert doc.source_type == RAGSourceType.MARKET
    assert doc.metadata.skill_id == sample_skill.id
    assert "Market Requirement" in doc.title
    assert "TechCorp India" in doc.content


def test_5_unmapped_market_jobs_excluded(db_session: Session, mock_embedding_provider):
    """5. Market jobs without any MarketJobSkill are excluded from ingestion."""
    unmapped_job = MarketJob(
        id=uuid4(),
        source="adzuna",
        external_job_id=f"job-{uuid4().hex[:8]}",
        title="General Operations Specialist",
        description="Manage office logistics and vendor relationships.",
        raw_data={},
    )
    db_session.add(unmapped_job)
    db_session.flush()

    service = EvidenceIngestionService(session=db_session, embedding_provider=mock_embedding_provider)
    summary = service.ingest_market_job_skills()
    assert summary["failed"] == 0

    # The unmapped job must NOT exist in RAG
    found = db_session.query(DBRAGDocument).filter(DBRAGDocument.source_reference.like(f"market_job:{unmapped_job.id}%")).first()
    assert found is None


def test_6_exact_source_reference_values(sample_approved_resource, sample_market_demand, sample_market_job_with_skill, sample_skill):
    """6. Verifies exact deterministic source_reference strings."""
    res_doc = build_resource_rag_document(sample_approved_resource, sample_skill)
    assert res_doc.source_reference == f"approved_resource:{sample_approved_resource.id}"

    demand_doc = build_market_demand_rag_document(sample_market_demand, sample_skill)
    assert demand_doc.source_reference == f"market_demand:adzuna:{sample_skill.slug}"

    job, job_skill = sample_market_job_with_skill
    job_doc = build_market_job_rag_document(job, job_skill, sample_skill)
    assert job_doc.source_reference == f"market_job:{job.id}:{sample_skill.id}"


def test_7_deterministic_uuid5_ids(sample_approved_resource, sample_skill):
    """7. Deterministic UUID5 produces identical ID across multiple builder executions."""
    doc1 = build_resource_rag_document(sample_approved_resource, sample_skill)
    doc2 = build_resource_rag_document(sample_approved_resource, sample_skill)
    assert doc1.id == doc2.id
    expected_uuid = uuid5(NAMESPACE_URL, f"sf:rag:approved_resource:{sample_approved_resource.id}")
    assert doc1.id == expected_uuid


def test_8_deterministic_content(sample_approved_resource, sample_skill):
    """8. Verifies structured, deterministic content construction."""
    doc = build_resource_rag_document(sample_approved_resource, sample_skill)
    lines = doc.content.split("\n")
    assert lines[0] == "Learning Resource: Official Python Tutorial"
    assert lines[1] == "Provider: Python Software Foundation"
    assert lines[2] == "Type: OFFICIAL_DOCS"
    assert lines[3] == "Difficulty: BEGINNER"
    assert lines[4] == "Duration: 240 minutes"
    assert "Official URL: https://docs.python.org/3/tutorial/" in lines[6]


def test_9_deterministic_metadata(sample_approved_resource, sample_skill):
    """9. Metadata fields are strongly typed, immutable, and deterministic."""
    doc = build_resource_rag_document(sample_approved_resource, sample_skill)
    assert doc.metadata.skill_id == sample_skill.id
    assert doc.metadata.skill_name == sample_skill.name
    assert doc.metadata.confidence_score == 1.0
    assert doc.metadata.approved_by == "curated_learning_resource"
    assert doc.metadata.content_hash is not None
    assert len(doc.metadata.content_hash) == 64


def test_10_canonical_skill_id_preservation(sample_market_demand, sample_skill, db_session, mock_embedding_provider):
    """10. Canonical skill_id is preserved on both document and generated chunks."""
    doc = build_market_demand_rag_document(sample_market_demand, sample_skill)
    service = EvidenceIngestionService(session=db_session, embedding_provider=mock_embedding_provider)
    status = service.index_or_update_document(doc)
    assert status == "ingested"

    db_doc = db_session.get(DBRAGDocument, doc.id)
    assert db_doc is not None
    assert db_doc.document_metadata["skill_id"] == str(sample_skill.id)

    db_chunks = db_session.query(DBRAGChunk).filter_by(document_id=doc.id).all()
    assert len(db_chunks) >= 1
    for chunk in db_chunks:
        assert chunk.skill_id == sample_skill.id


def test_11_sha256_content_hash():
    """11. Content hash matches SHA-256 over normalized elements."""
    st = "APPROVED_RESOURCE"
    sr = "approved_resource:123"
    title = "Test Resource"
    content = "Resource Details"
    sk_id = uuid4()

    computed = compute_document_content_hash(st, sr, title, content, sk_id)
    expected = hashlib.sha256(f"{st}|{sr}|{str(sk_id)}|{title}|{content}".encode("utf-8")).hexdigest()
    assert computed == expected


def test_12_second_ingestion_is_idempotent(sample_approved_resource, sample_skill, db_session, mock_embedding_provider):
    """12. Second ingestion run skips unchanged documents; 0 duplicates created."""
    service = EvidenceIngestionService(session=db_session, embedding_provider=mock_embedding_provider)

    doc = build_resource_rag_document(sample_approved_resource, sample_skill)
    status1 = service.index_or_update_document(doc)
    assert status1 == "ingested"

    doc_count_1 = db_session.query(DBRAGDocument).count()
    chunk_count_1 = db_session.query(DBRAGChunk).count()

    # Second run
    status2 = service.index_or_update_document(doc)
    assert status2 == "skipped"

    doc_count_2 = db_session.query(DBRAGDocument).count()
    chunk_count_2 = db_session.query(DBRAGChunk).count()

    assert doc_count_1 == doc_count_2
    assert chunk_count_1 == chunk_count_2


def test_13_changed_content_causes_replacement(sample_approved_resource, sample_skill, db_session, mock_embedding_provider):
    """13. Modifying resource fields causes clean re-indexing and returns 'updated'."""
    service = EvidenceIngestionService(session=db_session, embedding_provider=mock_embedding_provider)

    doc1 = build_resource_rag_document(sample_approved_resource, sample_skill)
    service.index_or_update_document(doc1)

    # Modify resource title and estimated minutes
    sample_approved_resource.title = "Updated Advanced Python Tutorial"
    sample_approved_resource.estimated_minutes = 360
    db_session.flush()

    doc2 = build_resource_rag_document(sample_approved_resource, sample_skill)
    assert doc1.metadata.content_hash != doc2.metadata.content_hash

    status2 = service.index_or_update_document(doc2)
    assert status2 == "updated"

    # Verify updated content in database
    db_doc = db_session.get(DBRAGDocument, doc1.id)
    assert "Updated Advanced Python Tutorial" in db_doc.title
    assert "360 minutes" in db_doc.content


def test_14_stale_chunks_are_removed(sample_approved_resource, sample_skill, db_session, mock_embedding_provider):
    """14. When document length shrinks, old chunks are purged via CASCADE without orphans."""
    service = EvidenceIngestionService(session=db_session, embedding_provider=mock_embedding_provider)

    # Initial long content to generate multiple chunks (> 500 chars chunk_size)
    sample_approved_resource.title = "Long Python Guide with Extended Description " * 5  # 225 chars <= 255
    sample_approved_resource.url = "https://example.com/docs/" + "python/" * 60  # 445 chars <= 1024
    db_session.flush()
    doc_long = build_resource_rag_document(sample_approved_resource, sample_skill)
    service.index_or_update_document(doc_long)

    initial_chunks = db_session.query(DBRAGChunk).filter_by(document_id=doc_long.id).all()
    assert len(initial_chunks) > 1

    # Shorten document to fit in exactly 1 chunk
    sample_approved_resource.title = "Short Guide"
    sample_approved_resource.url = "https://example.com/docs"
    db_session.flush()
    doc_short = build_resource_rag_document(sample_approved_resource, sample_skill)
    status = service.index_or_update_document(doc_short)
    assert status == "updated"

    new_chunks = db_session.query(DBRAGChunk).filter_by(document_id=doc_short.id).all()
    assert len(new_chunks) == 1
    assert "Short Guide" in new_chunks[0].content


def test_15_source_type_separation(sample_approved_resource, sample_market_demand, sample_skill, db_session, mock_embedding_provider):
    """15. APPROVED_RESOURCE and MARKET sources maintain strict separation."""
    service = EvidenceIngestionService(session=db_session, embedding_provider=mock_embedding_provider)

    res_doc = build_resource_rag_document(sample_approved_resource, sample_skill)
    demand_doc = build_market_demand_rag_document(sample_market_demand, sample_skill)

    service.index_or_update_document(res_doc)
    service.index_or_update_document(demand_doc)

    res_in_db = service.repository.find_document_by_reference(RAGSourceType.APPROVED_RESOURCE, res_doc.source_reference)
    demand_in_db = service.repository.find_document_by_reference(RAGSourceType.MARKET, demand_doc.source_reference)

    assert res_in_db is not None
    assert demand_in_db is not None
    assert res_in_db.source_type == "APPROVED_RESOURCE"
    assert demand_in_db.source_type == "MARKET"

    # Cross query by wrong source_type returns None
    assert service.repository.find_document_by_reference(RAGSourceType.MARKET, res_doc.source_reference) is None


def test_16_raw_market_descriptions_are_not_ingested(sample_market_job_with_skill, sample_skill):
    """16. Raw boilerplate from MarketJob.description is not included in RAG content."""
    job, job_skill = sample_market_job_with_skill
    job.description = "RAW RECRUITER BOILERPLATE: Equal Opportunity Employer, comprehensive 401(k), dental insurance."
    job_skill.evidence_text = "Clean required Python backend skill excerpt."

    doc = build_market_job_rag_document(job, job_skill, sample_skill)
    assert "Clean required Python backend skill excerpt." in doc.content
    assert "Equal Opportunity Employer" not in doc.content
    assert "dental insurance" not in doc.content


def test_17_raw_json_is_not_ingested(sample_market_job_with_skill, sample_skill):
    """17. Raw JSON payloads from MarketJob.raw_data are not dumped into document text."""
    job, job_skill = sample_market_job_with_skill
    job.raw_data = {"internal_tracking": "xyz-123", "secret_payload": "do_not_embed"}

    doc = build_market_job_rag_document(job, job_skill, sample_skill)
    assert "secret_payload" not in doc.content
    assert "xyz-123" not in doc.content


def test_18_no_secrets_or_private_data_are_ingested(sample_approved_resource, sample_skill):
    """18. Secrets matching PROHIBITED_PATTERNS trigger validation failure."""
    sample_approved_resource.title = "api_key = 'abcdef0123456789abcdef0123456789'"
    with pytest.raises(ValueError) as excinfo:
        build_resource_rag_document(sample_approved_resource, sample_skill)
    assert "prohibited" in str(excinfo.value)


def test_19_embedding_failure_rollback(sample_approved_resource, sample_skill, db_session):
    """19. Embedding failure rolls back transaction; no document or chunks saved."""
    class FailingEmbeddingProvider(EmbeddingProvider):
        @property
        def dimension(self) -> int:
            return settings.EMBEDDING_DIMENSION

        def embed_text(self, text: str) -> List[float]:
            raise RAGEmbeddingError("Inference engine failure.")

        def embed_documents(self, texts: List[str]) -> List[List[float]]:
            raise RAGEmbeddingError("Batch inference engine failure.")

    service = EvidenceIngestionService(session=db_session, embedding_provider=FailingEmbeddingProvider())
    doc = build_resource_rag_document(sample_approved_resource, sample_skill)

    with pytest.raises(RAGEmbeddingError):
        service.index_or_update_document(doc)

    db_doc = db_session.get(DBRAGDocument, doc.id)
    assert db_doc is None


def test_20_database_failure_rollback(sample_approved_resource, sample_skill, db_session, mock_embedding_provider):
    """20. Database error during chunk save triggers clean rollback."""
    service = EvidenceIngestionService(session=db_session, embedding_provider=mock_embedding_provider)
    doc = build_resource_rag_document(sample_approved_resource, sample_skill)

    # Force database failure by closing session during save
    original_save = service.repository.save_chunks

    def failing_save(chunks):
        raise RAGValidationError("Simulated storage constraint violation.")

    service.repository.save_chunks = failing_save

    with pytest.raises(RAGValidationError):
        service.index_or_update_document(doc)

    db_session.rollback()
    assert db_session.get(DBRAGDocument, doc.id) is None


def test_21_structured_ingestion_summary(sample_approved_resource, sample_market_demand, sample_market_job_with_skill, db_session, mock_embedding_provider):
    """21. Ingestion returns full structured summary with accurate breakdown."""
    service = EvidenceIngestionService(session=db_session, embedding_provider=mock_embedding_provider)
    summary = service.ingest_all_approved_evidence()

    assert "ingested" in summary
    assert "skipped" in summary
    assert "updated" in summary
    assert "failed" in summary
    assert "errors" in summary
    assert "breakdown" in summary

    assert summary["ingested"] >= 3
    assert summary["failed"] == 0
    assert summary["breakdown"]["approved_resources"]["ingested"] >= 1
    assert summary["breakdown"]["market_skill_demand"]["ingested"] >= 1
    assert summary["breakdown"]["market_job_skills"]["ingested"] >= 1
    assert summary["ingested"] == (
        summary["breakdown"]["approved_resources"]["ingested"]
        + summary["breakdown"]["market_skill_demand"]["ingested"]
        + summary["breakdown"]["market_job_skills"]["ingested"]
    )


def test_22_empty_invalid_content_handling(sample_approved_resource, sample_skill):
    """22. Empty or whitespace-only titles/urls are rejected with RAGValidationError."""
    sample_approved_resource.title = "   "
    with pytest.raises(RAGValidationError):
        build_resource_rag_document(sample_approved_resource, sample_skill)

    sample_approved_resource.title = "Valid Title"
    sample_approved_resource.url = "   "
    with pytest.raises(RAGValidationError):
        build_resource_rag_document(sample_approved_resource, sample_skill)


def test_23_corpus_count_verification(sample_approved_resource, sample_market_demand, sample_market_job_with_skill, db_session, mock_embedding_provider):
    """23. Database row counts match exactly the reported ingestion count."""
    service = EvidenceIngestionService(session=db_session, embedding_provider=mock_embedding_provider)
    summary = service.ingest_all_approved_evidence()

    db_docs = db_session.query(DBRAGDocument).count()
    db_chunks = db_session.query(DBRAGChunk).count()

    assert db_docs == (summary["ingested"] + summary["skipped"] + summary["updated"])
    assert db_chunks >= db_docs
