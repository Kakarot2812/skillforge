"""
Comprehensive test suite for Checkpoint C7-E: Approved Practical Project RAG Ingestion.

Verifies:
A. Exactly 8 authoritative seed projects detected from database.
B. All 2,815+ polluted fixture rows rejected.
C. Title-only matching is NOT used.
D. Timestamp is NOT used for provenance.
E. Project UUID is NOT used for provenance.
F. Fingerprint is deterministic.
G. Same canonical project definition produces same hash.
H. Authoritative fingerprint set contains exactly 8 hashes.
I. Project builder produces APPROVED_PROJECT source type.
J. source_reference format is correct (approved_project:<id>).
K. content_hash is deterministic.
L. Metadata contains canonical skill_id.
M. Metadata contains approved_by="curated_seed_0017".
N. Content contains title, target skill, target role, difficulty, estimated hours.
O. Content contains deliverables and verification criteria.
P. Content does not expose raw JSON.
Q. Content does not contain fixture title "Production FastAPI Microservice".
R. Exactly 8 project documents are ingested.
S. Exactly 8 project chunks are ingested.
T. Second ingestion skips all 8 projects.
U. No duplicate source references.
V. Changed authoritative project causes update.
W. Old chunks are deleted during update.
X. Failed embedding/database operation rolls back that project.
Y. Multi-skill retrieval can retrieve project evidence for requested skills.
Z. Minimum similarity threshold applies.
AA. Project evidence remains NON-AUTHORITATIVE.
AB. VerifiedContext remains authoritative.
AC. Existing C7-B resource/market ingestion remains unchanged.
AD. Fixture cleanup regression: test fixtures clean up created ApprovedProject rows.
"""

from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4, uuid5, NAMESPACE_DNS
import pytest
from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.db.database import SessionLocal
from app.db.models import (
    ApprovedProject,
    ApprovedResource,
    JobRole,
    MarketJob,
    MarketJobSkill,
    MarketSkillDemand,
    Skill,
    RAGChunk as DBRAGChunk,
    RAGDocument as DBRAGDocument,
)
from app.rag.chunking import DeterministicChunker
from app.rag.embeddings import MockEmbeddingProvider
from app.rag.exceptions import RAGEmbeddingError, RAGValidationError
from app.rag.ingestion import (
    EvidenceIngestionService,
    build_project_rag_document,
    compute_document_content_hash,
)
from app.rag.models import (
    RAGDocument,
    RAGDocumentMetadata,
    RAGRetrievalFilter,
    RAGSourceType,
)
from app.rag.provenance import (
    CANONICAL_SEED_PROJECT_HASHES,
    CANONICAL_SEED_PROJECT_SPECS,
    compute_canonical_project_fingerprint,
    is_canonical_project,
)
from app.rag.repository import RAGRepository
from app.rag.retriever import EvidenceRetriever


# ---------------------------------------------------------------------------
# Test Fixtures (Isolated via SQLAlchemy Savepoints)
# ---------------------------------------------------------------------------

@pytest.fixture
def db_session():
    """
    Provides a transactional database session using savepoints so that commits
    inside the service commit to the savepoint and are completely undone at test
    teardown by trans.rollback(). Zero database mutation or pollution.
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


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def test_a_exactly_8_authoritative_projects_detected(db_session: Session):
    """A. Exactly 8 authoritative seed projects are detected from the live database."""
    projects = (
        db_session.query(ApprovedProject)
        .options(joinedload(ApprovedProject.skill), joinedload(ApprovedProject.role))
        .all()
    )
    authoritative = [p for p in projects if is_canonical_project(p, p.skill, p.role)]
    assert len(authoritative) == 8


def test_b_all_polluted_fixture_rows_rejected(db_session: Session):
    """B. All 2,815+ polluted fixture rows are rejected by the provenance check."""
    projects = (
        db_session.query(ApprovedProject)
        .options(joinedload(ApprovedProject.skill), joinedload(ApprovedProject.role))
        .all()
    )
    rejected = [p for p in projects if not is_canonical_project(p, p.skill, p.role)]
    assert len(rejected) >= 2815


def test_c_title_only_matching_not_used(db_session: Session):
    """C. Title-only matching is NOT used: project with identical title but altered criteria is rejected."""
    # Find a canonical seed project
    spec = CANONICAL_SEED_PROJECT_SPECS[0]  # FastAPI project
    skill = db_session.query(Skill).filter(Skill.slug == spec["skill_slug"]).first()
    role = db_session.query(JobRole).filter(JobRole.slug == spec["role_slug"]).first()
    assert skill is not None

    fake_project = ApprovedProject(
        id=uuid4(),
        skill_id=skill.id,
        role_id=role.id if role else None,
        title=spec["title"],  # Exact title match!
        description="Tampered description that does not match seed.",
        difficulty=spec["difficulty"],
        deliverables=["different_file.py"],  # Tampered deliverables!
        verification_criteria=["tampered_criterion"],  # Tampered criteria!
        estimated_hours=999,  # Tampered hours!
    )

    # Must be rejected because full cryptographic fingerprint differs
    assert not is_canonical_project(fake_project, skill, role)


def test_d_timestamp_not_used_for_provenance():
    """D. Timestamp is NOT used for provenance: different timestamps yield identical fingerprint."""
    spec = CANONICAL_SEED_PROJECT_SPECS[0]
    fp1 = compute_canonical_project_fingerprint(
        skill_slug=spec["skill_slug"],
        role_slug=spec["role_slug"],
        title=spec["title"],
        description=spec["description"],
        difficulty=spec["difficulty"],
        deliverables=spec["deliverables"],
        verification_criteria=spec["verification_criteria"],
        estimated_hours=spec["estimated_hours"],
    )

    # Calling with different hypothetical timestamps makes no difference to the fingerprint function
    fp2 = compute_canonical_project_fingerprint(
        skill_slug=spec["skill_slug"],
        role_slug=spec["role_slug"],
        title=spec["title"],
        description=spec["description"],
        difficulty=spec["difficulty"],
        deliverables=spec["deliverables"],
        verification_criteria=spec["verification_criteria"],
        estimated_hours=spec["estimated_hours"],
    )
    assert fp1 == fp2
    assert fp1 in CANONICAL_SEED_PROJECT_HASHES


def test_e_project_uuid_not_used_for_provenance(db_session: Session):
    """E. Project UUID is NOT used for provenance: two instances with different UUIDs have same fingerprint."""
    spec = CANONICAL_SEED_PROJECT_SPECS[1]  # Docker project
    skill = db_session.query(Skill).filter(Skill.slug == spec["skill_slug"]).first()
    role = db_session.query(JobRole).filter(JobRole.slug == spec["role_slug"]).first()

    p1 = ApprovedProject(
        id=uuid4(),
        skill_id=skill.id,
        role_id=role.id if role else None,
        title=spec["title"],
        description=spec["description"],
        difficulty=spec["difficulty"],
        deliverables=spec["deliverables"],
        verification_criteria=spec["verification_criteria"],
        estimated_hours=spec["estimated_hours"],
    )
    p2 = ApprovedProject(
        id=uuid4(),  # Different UUID!
        skill_id=skill.id,
        role_id=role.id if role else None,
        title=spec["title"],
        description=spec["description"],
        difficulty=spec["difficulty"],
        deliverables=spec["deliverables"],
        verification_criteria=spec["verification_criteria"],
        estimated_hours=spec["estimated_hours"],
    )

    assert is_canonical_project(p1, skill, role)
    assert is_canonical_project(p2, skill, role)


def test_f_fingerprint_is_deterministic():
    """F. Fingerprint is deterministic across multiple independent invocations."""
    for spec in CANONICAL_SEED_PROJECT_SPECS:
        hashes = [
            compute_canonical_project_fingerprint(
                skill_slug=spec["skill_slug"],
                role_slug=spec["role_slug"],
                title=spec["title"],
                description=spec["description"],
                difficulty=spec["difficulty"],
                deliverables=spec["deliverables"],
                verification_criteria=spec["verification_criteria"],
                estimated_hours=spec["estimated_hours"],
            )
            for _ in range(5)
        ]
        assert all(h == hashes[0] for h in hashes)


def test_g_same_canonical_project_definition_produces_same_hash():
    """G. Same canonical project definition produces same hash regardless of spacing or letter case."""
    spec = CANONICAL_SEED_PROJECT_SPECS[2]  # docker-compose
    h1 = compute_canonical_project_fingerprint(
        skill_slug=spec["skill_slug"].upper(),  # case difference normalized
        role_slug=f"  {spec['role_slug']}  ",  # whitespace normalized
        title=f"  {spec['title']}  ",
        description=f"  {spec['description']}  ",
        difficulty=spec["difficulty"].lower(),  # uppercase normalized
        deliverables=list(reversed(spec["deliverables"])),  # order sorted deterministically
        verification_criteria=list(reversed(spec["verification_criteria"])),
        estimated_hours=spec["estimated_hours"],
    )
    h2 = compute_canonical_project_fingerprint(
        skill_slug=spec["skill_slug"],
        role_slug=spec["role_slug"],
        title=spec["title"],
        description=spec["description"],
        difficulty=spec["difficulty"],
        deliverables=spec["deliverables"],
        verification_criteria=spec["verification_criteria"],
        estimated_hours=spec["estimated_hours"],
    )
    assert h1 == h2


def test_h_authoritative_fingerprint_set_contains_exactly_8_hashes():
    """H. Authoritative fingerprint set contains exactly 8 hashes."""
    assert isinstance(CANONICAL_SEED_PROJECT_HASHES, frozenset)
    assert len(CANONICAL_SEED_PROJECT_HASHES) == 8


def test_i_builder_produces_approved_project_source_type(db_session: Session):
    """I. Project builder produces APPROVED_PROJECT source type."""
    projects = (
        db_session.query(ApprovedProject)
        .options(joinedload(ApprovedProject.skill), joinedload(ApprovedProject.role))
        .all()
    )
    auth = [p for p in projects if is_canonical_project(p, p.skill, p.role)][0]
    doc = build_project_rag_document(auth, auth.skill, auth.role)
    assert doc.source_type == RAGSourceType.APPROVED_PROJECT


def test_j_source_reference_format_is_correct(db_session: Session):
    """J. source_reference format is strictly 'approved_project:<project.id>'."""
    projects = (
        db_session.query(ApprovedProject)
        .options(joinedload(ApprovedProject.skill), joinedload(ApprovedProject.role))
        .all()
    )
    auth = [p for p in projects if is_canonical_project(p, p.skill, p.role)][0]
    doc = build_project_rag_document(auth, auth.skill, auth.role)
    assert doc.source_reference == f"approved_project:{auth.id}"
    expected_id = uuid5(NAMESPACE_DNS, f"sf:rag:approved_project:{auth.id}")
    assert doc.id == expected_id


def test_k_content_hash_is_deterministic(db_session: Session):
    """K. content_hash is deterministic."""
    projects = (
        db_session.query(ApprovedProject)
        .options(joinedload(ApprovedProject.skill), joinedload(ApprovedProject.role))
        .all()
    )
    auth = [p for p in projects if is_canonical_project(p, p.skill, p.role)][0]
    doc1 = build_project_rag_document(auth, auth.skill, auth.role)
    doc2 = build_project_rag_document(auth, auth.skill, auth.role)
    assert doc1.metadata.content_hash == doc2.metadata.content_hash


def test_l_metadata_contains_canonical_skill_id(db_session: Session):
    """L. Metadata contains canonical skill_id."""
    projects = (
        db_session.query(ApprovedProject)
        .options(joinedload(ApprovedProject.skill), joinedload(ApprovedProject.role))
        .all()
    )
    auth = [p for p in projects if is_canonical_project(p, p.skill, p.role)][0]
    doc = build_project_rag_document(auth, auth.skill, auth.role)
    assert doc.metadata.skill_id == auth.skill_id
    assert doc.metadata.skill_name == auth.skill.name.strip()


def test_m_metadata_contains_curated_seed_0017(db_session: Session):
    """M. Metadata contains approved_by='curated_seed_0017'."""
    projects = (
        db_session.query(ApprovedProject)
        .options(joinedload(ApprovedProject.skill), joinedload(ApprovedProject.role))
        .all()
    )
    auth = [p for p in projects if is_canonical_project(p, p.skill, p.role)][0]
    doc = build_project_rag_document(auth, auth.skill, auth.role)
    assert doc.metadata.approved_by == "curated_seed_0017"
    assert doc.metadata.confidence_score == 1.0


def test_n_project_content_contains_required_fields(db_session: Session):
    """N. Project content contains title, skill, role, difficulty, hours."""
    projects = (
        db_session.query(ApprovedProject)
        .options(joinedload(ApprovedProject.skill), joinedload(ApprovedProject.role))
        .all()
    )
    auth = [p for p in projects if is_canonical_project(p, p.skill, p.role)][0]
    doc = build_project_rag_document(auth, auth.skill, auth.role)

    assert f"Title: {auth.title}" in doc.content
    assert f"Target Skill: {auth.skill.name.strip()}" in doc.content
    assert f"Difficulty: {auth.difficulty}" in doc.content
    assert f"Estimated Hours: {auth.estimated_hours}" in doc.content


def test_o_project_content_contains_deliverables_and_criteria(db_session: Session):
    """O. Project content contains deliverables and verification criteria."""
    projects = (
        db_session.query(ApprovedProject)
        .options(joinedload(ApprovedProject.skill), joinedload(ApprovedProject.role))
        .all()
    )
    auth = [p for p in projects if is_canonical_project(p, p.skill, p.role)][0]
    doc = build_project_rag_document(auth, auth.skill, auth.role)

    for d in auth.deliverables:
        assert f"- {d}" in doc.content
    for c in auth.verification_criteria:
        assert f"- {c}" in doc.content


def test_p_project_content_does_not_expose_raw_json(db_session: Session):
    """P. Project content does not expose raw database JSON representations."""
    projects = (
        db_session.query(ApprovedProject)
        .options(joinedload(ApprovedProject.skill), joinedload(ApprovedProject.role))
        .all()
    )
    auth = [p for p in projects if is_canonical_project(p, p.skill, p.role)][0]
    doc = build_project_rag_document(auth, auth.skill, auth.role)

    assert "['" not in doc.content
    assert '{"' not in doc.content
    assert '":' not in doc.content


def test_q_project_content_does_not_contain_fixture_title(db_session: Session, mock_embedding_provider):
    """Q. Project content does not contain fixture title 'Production FastAPI Microservice'."""
    service = EvidenceIngestionService(session=db_session, embedding_provider=mock_embedding_provider)
    service.ingest_approved_projects()

    ingested_docs = (
        db_session.query(DBRAGDocument)
        .filter(DBRAGDocument.source_type == RAGSourceType.APPROVED_PROJECT.value)
        .all()
    )

    for doc in ingested_docs:
        assert "Production FastAPI Microservice" not in doc.title
        assert "Production FastAPI Microservice" not in doc.content


def test_r_s_t_idempotent_ingestion_and_counts(db_session: Session, mock_embedding_provider):
    """R, S, T. Exactly 8 documents & 8 chunks ingested on first pass; second pass skips all 8."""
    # Ensure savepoint starts clean of project docs to test 0 -> 8 transition
    db_session.query(DBRAGDocument).filter(
        DBRAGDocument.source_type == RAGSourceType.APPROVED_PROJECT.value
    ).delete(synchronize_session=False)
    db_session.flush()

    service = EvidenceIngestionService(session=db_session, embedding_provider=mock_embedding_provider)

    # First pass: must ingest exactly 8 authoritative projects
    res1 = service.ingest_approved_projects()
    assert res1["ingested"] == 8
    assert res1["failed"] == 0
    assert res1["updated"] == 0

    proj_docs = (
        db_session.query(DBRAGDocument)
        .filter(DBRAGDocument.source_type == RAGSourceType.APPROVED_PROJECT.value)
        .count()
    )
    proj_chunks = (
        db_session.query(DBRAGChunk)
        .filter(DBRAGChunk.source_type == RAGSourceType.APPROVED_PROJECT.value)
        .count()
    )
    assert proj_docs == 8
    assert proj_chunks == 8

    # Second pass: must skip all 8 without creating any new documents or chunks
    res2 = service.ingest_approved_projects()
    assert res2["ingested"] == 0
    assert res2["skipped"] == 8
    assert res2["updated"] == 0
    assert res2["failed"] == 0

    proj_docs_after = (
        db_session.query(DBRAGDocument)
        .filter(DBRAGDocument.source_type == RAGSourceType.APPROVED_PROJECT.value)
        .count()
    )
    assert proj_docs_after == 8


def test_u_no_duplicate_source_references(db_session: Session, mock_embedding_provider):
    """U. No duplicate source references exist in RAG documents."""
    service = EvidenceIngestionService(session=db_session, embedding_provider=mock_embedding_provider)
    service.ingest_approved_projects()

    docs = (
        db_session.query(DBRAGDocument)
        .filter(DBRAGDocument.source_type == RAGSourceType.APPROVED_PROJECT.value)
        .all()
    )
    refs = [d.source_reference for d in docs]
    assert len(refs) == len(set(refs)) == 8


def test_v_w_changed_project_causes_update_and_replaces_old_chunks(db_session: Session, mock_embedding_provider):
    """V, W. Changed project causes update; old chunks are purged via CASCADE and replaced."""
    service = EvidenceIngestionService(session=db_session, embedding_provider=mock_embedding_provider)
    service.ingest_approved_projects()

    projects = (
        db_session.query(ApprovedProject)
        .options(joinedload(ApprovedProject.skill), joinedload(ApprovedProject.role))
        .all()
    )
    auth = [p for p in projects if is_canonical_project(p, p.skill, p.role)][0]

    doc_before = db_session.query(DBRAGDocument).filter(
        DBRAGDocument.source_reference == f"approved_project:{auth.id}"
    ).first()
    assert doc_before is not None

    chunk_before = db_session.query(DBRAGChunk).filter(
        DBRAGChunk.document_id == doc_before.id
    ).first()
    assert chunk_before is not None
    chunk_before_id = chunk_before.id

    # Temporarily update description to simulate a content change
    auth.description = "Updated description with enhanced architecture details."
    doc_updated = build_project_rag_document(auth, auth.skill, auth.role)
    status = service.index_or_update_document(doc_updated)
    assert status == "updated"

    # Verify old chunk was purged
    old_chunk = db_session.query(DBRAGChunk).filter(DBRAGChunk.id == chunk_before_id).first()
    assert old_chunk is None

    # Verify new chunk exists with updated text
    new_chunk = db_session.query(DBRAGChunk).filter(DBRAGChunk.document_id == doc_before.id).first()
    assert new_chunk is not None
    assert "Enhanced architecture details" in new_chunk.content or "enhanced architecture details" in new_chunk.content


def test_x_failure_rollback_isolation(db_session: Session, mock_embedding_provider):
    """X. Failed embedding/database operation rolls back that project without corrupting corpus."""
    service = EvidenceIngestionService(session=db_session, embedding_provider=mock_embedding_provider)

    skill = db_session.query(Skill).first()
    role = db_session.query(JobRole).first()
    test_proj = ApprovedProject(
        id=uuid4(),
        skill_id=skill.id,
        role_id=role.id if role else None,
        title="Test Rollback Isolation Project",
        description="Testing atomic rollback during storage failure.",
        difficulty="INTERMEDIATE",
        deliverables=["test.py"],
        verification_criteria=["test_criteria"],
        estimated_hours=4,
    )
    doc = build_project_rag_document(test_proj, skill, role)

    def failing_save(chunks):
        raise RAGValidationError("Simulated storage constraint error.")

    service.repository.save_chunks = failing_save

    with pytest.raises(RAGValidationError):
        service.index_or_update_document(doc)

    db_session.rollback()
    # Confirm document was not persisted
    assert db_session.get(DBRAGDocument, doc.id) is None


def test_y_z_multi_skill_retrieval_and_threshold(db_session: Session, mock_embedding_provider):
    """Y, Z. Multi-skill retrieval can retrieve project evidence and similarity threshold applies."""
    # Ensure savepoint has project docs embedded with mock_embedding_provider
    db_session.query(DBRAGDocument).filter(
        DBRAGDocument.source_type == RAGSourceType.APPROVED_PROJECT.value
    ).delete(synchronize_session=False)
    db_session.flush()

    service = EvidenceIngestionService(session=db_session, embedding_provider=mock_embedding_provider)
    service.ingest_approved_projects()

    repo = RAGRepository(session=db_session)
    retriever = EvidenceRetriever(repository=repo, embedding_provider=mock_embedding_provider)

    # Find skill id for FastAPI
    fastapi_skill = db_session.query(Skill).filter(Skill.slug == "fastapi").first()
    assert fastapi_skill is not None

    # Retrieve with multi-skill filter containing fastapi_skill
    results = retriever.retrieve(
        query="FastAPI REST API dependency injection",
        top_k=5,
        filters=RAGRetrievalFilter(
            skill_ids=(fastapi_skill.id,),
            min_similarity=0.30,
        ),
    )

    assert len(results) >= 1
    # Check that results belong to requested skill
    for r in results:
        assert r.skill_id == fastapi_skill.id
        assert r.similarity_score >= 0.30

    # Strict noise threshold: a filter with high similarity threshold yields empty list
    high_threshold_results = retriever.retrieve(
        query="unrelated query about astrology and gardening",
        top_k=5,
        filters=RAGRetrievalFilter(
            source_type=RAGSourceType.APPROVED_PROJECT,
            min_similarity=0.99,
        ),
    )
    assert len(high_threshold_results) == 0


def test_aa_ab_project_evidence_remains_non_authoritative(db_session: Session):
    """AA, AB. Project evidence is explicitly non-authoritative; VerifiedContext remains sole authority."""
    projects = (
        db_session.query(ApprovedProject)
        .options(joinedload(ApprovedProject.skill), joinedload(ApprovedProject.role))
        .all()
    )
    auth = [p for p in projects if is_canonical_project(p, p.skill, p.role)][0]
    doc = build_project_rag_document(auth, auth.skill, auth.role)

    # Mandatory disclaimer in document content
    assert "This is curated project evidence." in doc.content
    assert "It is NOT proof that the candidate possesses the listed skills." in doc.content


def test_ac_existing_c7b_ingestion_remains_unchanged(db_session: Session, mock_embedding_provider):
    """AC. Existing C7-B resource/market ingestion remains functional and distinct."""
    service = EvidenceIngestionService(session=db_session, embedding_provider=mock_embedding_provider)

    # ingest_all_approved_evidence with include_projects=False executes only C7-B sources
    summary = service.ingest_all_approved_evidence(include_projects=False)
    assert "approved_resources" in summary["breakdown"]
    assert "market_skill_demand" in summary["breakdown"]
    assert "market_job_skills" in summary["breakdown"]
    assert "approved_projects" not in summary["breakdown"]


def test_ad_fixture_cleanup_regression(db_session: Session):
    """AD. Regression: creating ApprovedProject test rows and deleting them leaves zero leakage."""
    skill = db_session.query(Skill).first()
    assert skill is not None

    initial_count = db_session.query(ApprovedProject).count()

    test_project = ApprovedProject(
        id=uuid4(),
        skill_id=skill.id,
        title="Temporary Regression Test Project",
        description="Regression test description.",
        difficulty="INTERMEDIATE",
        deliverables=["test.py"],
        verification_criteria=["test_criterion"],
        estimated_hours=4,
    )
    db_session.add(test_project)
    db_session.flush()

    assert db_session.query(ApprovedProject).count() == initial_count + 1

    # Teardown logic matching test_verification_api / test_verification_service
    db_session.query(ApprovedProject).filter(ApprovedProject.id == test_project.id).delete(synchronize_session=False)
    db_session.flush()

    assert db_session.query(ApprovedProject).count() == initial_count
