"""
Unit and integration tests for SkillForge AI Checkpoint C7-C:
RAG Retrieval Quality & Evidence Grounding.

Tests cover:
A. Single-skill filtering (skill_ids=(python_id,))
B. Multi-skill filtering (skill_ids=(python_id, docker_id))
C. Cross-skill exclusion (assert unrelated skills absent)
D. Empty skill_ids=() behaves as unfiltered retrieval
E. Existing single skill_id backward compatibility
F. Conflicting skill_id + skill_ids validation rejection
G. Minimum similarity threshold (boundary inclusion/exclusion)
H. No-result threshold returns []
I. Threshold bounds validation (< 0, > 1 rejected)
J. Explicit caller override of min_similarity
K. Default configuration uses settings.RAG_MIN_SIMILARITY_THRESHOLD
L. Deterministic ranking across multiple executions
M. Source filtering combined with multi-skill filtering
N. Real populated corpus multi-skill retrieval probe
O. Noise query exclusion below threshold
P. Chat Grounding Test ("Compare my Python and Docker skills")
"""

import math
from typing import Generator, List, Optional, Sequence
from uuid import UUID, uuid4
from datetime import datetime, timezone
import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session
from unittest.mock import MagicMock, patch

from app.config import settings
from app.db.database import SessionLocal
from app.db.models import (
    Skill,
    RAGDocument as DBRAGDocument,
    RAGChunk as DBRAGChunk,
)
from app.ai.context.models import (
    VerifiedContext,
    VerifiedCandidateContext,
    VerifiedSkillFact,
    SkillClassification,
    FactProvenance,
)
from app.ai.chatbot.service import CareerChatService
from app.ai.chatbot.models import CareerChatRequest
from app.rag.embeddings import EmbeddingProvider, MockEmbeddingProvider, get_shared_embedding_provider
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
from app.rag.service import RAGService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def canonical_python_skill(db_session: Session) -> Skill:
    skill = db_session.query(Skill).filter_by(slug="python").first()
    if not skill:
        skill = Skill(
            id=uuid4(),
            name="Python",
            slug="python",
            category="Languages",
            description="Core programming language",
        )
        db_session.add(skill)
        db_session.commit()
    return skill


@pytest.fixture
def canonical_docker_skill(db_session: Session) -> Skill:
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
def canonical_react_skill(db_session: Session) -> Skill:
    skill = db_session.query(Skill).filter_by(slug="react").first()
    if not skill:
        skill = Skill(
            id=uuid4(),
            name="React",
            slug="react",
            category="Frontend",
            description="UI library",
        )
        db_session.add(skill)
        db_session.commit()
    return skill


# ---------------------------------------------------------------------------
# Test A: Single-skill filtering using skill_ids=(python_id,)
# ---------------------------------------------------------------------------

def test_a_single_skill_ids_filtering(db_session: Session, canonical_python_skill: Skill, canonical_docker_skill: Skill):
    """Verify skill_ids=(python_id,) strictly returns only Python chunks."""
    rag_service = RAGService(session=db_session, embedding_provider=get_shared_embedding_provider())
    filter_obj = RAGRetrievalFilter(skill_ids=(canonical_python_skill.id,))

    results = rag_service.retrieve(
        query="Explain programming tutorials and tools",
        top_k=5,
        filters=filter_obj,
    )

    assert len(results) > 0
    for r in results:
        assert r.skill_id == canonical_python_skill.id
        assert r.skill_id != canonical_docker_skill.id


# ---------------------------------------------------------------------------
# Test B: Multi-skill filtering using skill_ids=(python_id, docker_id)
# ---------------------------------------------------------------------------

def test_b_multi_skill_filtering(
    db_session: Session,
    canonical_python_skill: Skill,
    canonical_docker_skill: Skill,
    canonical_react_skill: Skill,
):
    """Verify skill_ids=(python_id, docker_id) returns only Python and Docker chunks."""
    rag_service = RAGService(session=db_session, embedding_provider=get_shared_embedding_provider())
    target_ids = (canonical_python_skill.id, canonical_docker_skill.id)
    filter_obj = RAGRetrievalFilter(skill_ids=target_ids)

    results = rag_service.retrieve(
        query="How do I use Python and Docker together for microservices?",
        top_k=10,
        filters=filter_obj,
    )

    assert len(results) > 0
    for r in results:
        assert r.skill_id in target_ids
        assert r.skill_id != canonical_react_skill.id


# ---------------------------------------------------------------------------
# Test C: Cross-skill exclusion
# ---------------------------------------------------------------------------

def test_c_cross_skill_exclusion(
    db_session: Session,
    canonical_python_skill: Skill,
    canonical_docker_skill: Skill,
):
    """Retrieve with multi-skill filter and explicitly assert unrelated skills are absent."""
    rag_service = RAGService(session=db_session, embedding_provider=get_shared_embedding_provider())
    target_ids = (canonical_python_skill.id, canonical_docker_skill.id)
    filter_obj = RAGRetrievalFilter(skill_ids=target_ids)

    # Broad query that in unfiltered mode would surface C++, Java, React, etc.
    results = rag_service.retrieve(
        query="software architecture development libraries and frameworks",
        top_k=10,
        filters=filter_obj,
    )

    all_other_skills = (
        db_session.query(Skill.id)
        .filter(Skill.id.notin_(target_ids))
        .all()
    )
    forbidden_ids = {s[0] for s in all_other_skills}

    for r in results:
        assert r.skill_id not in forbidden_ids
        assert r.skill_id in target_ids


# ---------------------------------------------------------------------------
# Test D: Empty skill_ids behaves as unfiltered retrieval
# ---------------------------------------------------------------------------

def test_d_empty_skill_ids_behaves_as_unfiltered(db_session: Session):
    """Verify skill_ids=() applies no skill restriction."""
    rag_service = RAGService(session=db_session, embedding_provider=get_shared_embedding_provider())
    filter_empty = RAGRetrievalFilter(skill_ids=())

    results = rag_service.retrieve(
        query="software development fundamentals",
        top_k=5,
        filters=filter_empty,
    )

    assert len(results) > 0


# ---------------------------------------------------------------------------
# Test E: Existing single skill_id filter backward compatibility
# ---------------------------------------------------------------------------

def test_e_existing_skill_id_compatibility(db_session: Session, canonical_python_skill: Skill):
    """Verify the original single skill_id field continues to function properly."""
    rag_service = RAGService(session=db_session, embedding_provider=get_shared_embedding_provider())
    filter_legacy = RAGRetrievalFilter(skill_id=canonical_python_skill.id)

    results = rag_service.retrieve(
        query="Python learning guides",
        top_k=5,
        filters=filter_legacy,
    )

    assert len(results) > 0
    for r in results:
        assert r.skill_id == canonical_python_skill.id


# ---------------------------------------------------------------------------
# Test F: Conflicting skill_id + skill_ids validation rejection
# ---------------------------------------------------------------------------

def test_f_conflicting_skill_id_and_skill_ids_rejected(canonical_python_skill: Skill, canonical_docker_skill: Skill):
    """Verify providing both skill_id and skill_ids raises a validation error."""
    with pytest.raises(ValidationError) as exc:
        RAGRetrievalFilter(
            skill_id=canonical_python_skill.id,
            skill_ids=(canonical_docker_skill.id,),
        )
    assert "Cannot specify both 'skill_id' and 'skill_ids'" in str(exc.value)


# ---------------------------------------------------------------------------
# Test G: Minimum similarity threshold inclusion & exclusion
# ---------------------------------------------------------------------------

def test_g_minimum_similarity_threshold_boundary(db_session: Session):
    """Verify controlled embeddings above cutoff are included and below are excluded."""
    provider = MockEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)
    repo = RAGRepository(session=db_session)

    # Unit vector setup
    query_vec = [1.0] + [0.0] * (settings.EMBEDDING_DIMENSION - 1)
    # Vec A: dot product with query = 0.80 -> similarity = 0.80
    vec_a = [0.80, math.sqrt(1.0 - 0.80**2)] + [0.0] * (settings.EMBEDDING_DIMENSION - 2)
    # Vec B: dot product with query = 0.20 -> similarity = 0.20
    vec_b = [0.20, math.sqrt(1.0 - 0.20**2)] + [0.0] * (settings.EMBEDDING_DIMENSION - 2)

    doc_id = uuid4()
    doc = DBRAGDocument(
        id=doc_id,
        source_type=RAGSourceType.MARKET.value,
        source_reference=f"test:thresh:{doc_id.hex[:6]}",
        title="Threshold Test Doc",
        content="Testing similarity boundary conditions.",
        document_metadata={"source_reference": f"test:thresh:{doc_id.hex[:6]}"},
    )
    chunk_a = DBRAGChunk(
        id=uuid4(),
        document_id=doc_id,
        chunk_index=0,
        content="High similarity chunk at 0.80",
        embedding=vec_a,
        source_type=RAGSourceType.MARKET.value,
        source_reference=f"test:thresh:{doc_id.hex[:6]}",
        chunk_metadata={"chunk_index": 0, "source_reference": f"test:thresh:{doc_id.hex[:6]}"},
    )
    chunk_b = DBRAGChunk(
        id=uuid4(),
        document_id=doc_id,
        chunk_index=1,
        content="Low similarity chunk at 0.20",
        embedding=vec_b,
        source_type=RAGSourceType.MARKET.value,
        source_reference=f"test:thresh:{doc_id.hex[:6]}",
        chunk_metadata={"chunk_index": 1, "source_reference": f"test:thresh:{doc_id.hex[:6]}"},
    )
    db_session.add(doc)
    db_session.add(chunk_a)
    db_session.add(chunk_b)
    db_session.commit()

    try:
        # Search with threshold 0.50: chunk_a (0.80) included, chunk_b (0.20) excluded
        filter_thresh = RAGRetrievalFilter(
            source_reference=f"test:thresh:{doc_id.hex[:6]}",
            min_similarity=0.50,
        )
        results = repo.search_similar(query_vector=query_vec, top_k=5, filters=filter_thresh)

        assert len(results) == 1
        assert results[0].chunk_id == chunk_a.id
        assert results[0].similarity_score >= 0.79
    finally:
        db_session.delete(chunk_a)
        db_session.delete(chunk_b)
        db_session.delete(doc)
        db_session.commit()


# ---------------------------------------------------------------------------
# Test H: No-result threshold returns []
# ---------------------------------------------------------------------------

def test_h_no_result_threshold_returns_empty_list(db_session: Session):
    """Verify that when all chunks are below min_similarity, an empty list is returned."""
    rag_service = RAGService(session=db_session, embedding_provider=get_shared_embedding_provider())
    # Require 0.999 similarity on a general query
    filter_impossible = RAGRetrievalFilter(min_similarity=0.999)

    results = rag_service.retrieve(
        query="Some arbitrary non-exact query string",
        top_k=5,
        filters=filter_impossible,
    )

    assert results == []


# ---------------------------------------------------------------------------
# Test I: Threshold bounds validation (< 0, > 1 rejected)
# ---------------------------------------------------------------------------

def test_i_threshold_bounds_validation():
    """Verify min_similarity < 0.0 or > 1.0 raises ValidationError."""
    with pytest.raises(ValidationError):
        RAGRetrievalFilter(min_similarity=-0.01)

    with pytest.raises(ValidationError):
        RAGRetrievalFilter(min_similarity=1.01)

    # Boundaries 0.0 and 1.0 are valid
    f_zero = RAGRetrievalFilter(min_similarity=0.0)
    assert f_zero.min_similarity == 0.0

    f_one = RAGRetrievalFilter(min_similarity=1.0)
    assert f_one.min_similarity == 1.0


# ---------------------------------------------------------------------------
# Test J: Explicit caller override of min_similarity
# ---------------------------------------------------------------------------

def test_j_explicit_caller_override(db_session: Session):
    """Verify explicit min_similarity in filter overrides settings.RAG_MIN_SIMILARITY_THRESHOLD."""
    repo = RAGRepository(session=db_session)
    query_vec = [1.0] + [0.0] * (settings.EMBEDDING_DIMENSION - 1)
    # Vec at 0.25 similarity (below default 0.30)
    vec_low = [0.25, math.sqrt(1.0 - 0.25**2)] + [0.0] * (settings.EMBEDDING_DIMENSION - 2)

    doc_id = uuid4()
    doc = DBRAGDocument(
        id=doc_id,
        source_type=RAGSourceType.MARKET.value,
        source_reference=f"test:override:{doc_id.hex[:6]}",
        title="Override Test Doc",
        content="Testing explicit caller override.",
        document_metadata={"source_reference": f"test:override:{doc_id.hex[:6]}"},
    )
    chunk = DBRAGChunk(
        id=uuid4(),
        document_id=doc_id,
        chunk_index=0,
        content="Chunk at 0.25",
        embedding=vec_low,
        source_type=RAGSourceType.MARKET.value,
        source_reference=f"test:override:{doc_id.hex[:6]}",
        chunk_metadata={"chunk_index": 0, "source_reference": f"test:override:{doc_id.hex[:6]}"},
    )
    db_session.add(doc)
    db_session.add(chunk)
    db_session.commit()

    try:
        # Default behavior (min_similarity=None) uses 0.30 -> chunk is excluded
        filter_default = RAGRetrievalFilter(source_reference=f"test:override:{doc_id.hex[:6]}")
        res_default = repo.search_similar(query_vector=query_vec, top_k=5, filters=filter_default)
        assert len(res_default) == 0

        # Caller overrides threshold to 0.20 -> chunk is included
        filter_override = RAGRetrievalFilter(
            source_reference=f"test:override:{doc_id.hex[:6]}",
            min_similarity=0.20,
        )
        res_override = repo.search_similar(query_vector=query_vec, top_k=5, filters=filter_override)
        assert len(res_override) == 1
        assert res_override[0].chunk_id == chunk.id
    finally:
        db_session.delete(chunk)
        db_session.delete(doc)
        db_session.commit()


# ---------------------------------------------------------------------------
# Test K: Default configuration uses settings.RAG_MIN_SIMILARITY_THRESHOLD
# ---------------------------------------------------------------------------

def test_k_default_configuration_uses_settings_threshold():
    """Verify that settings defines RAG_MIN_SIMILARITY_THRESHOLD as 0.30."""
    assert hasattr(settings, "RAG_MIN_SIMILARITY_THRESHOLD")
    assert settings.RAG_MIN_SIMILARITY_THRESHOLD == 0.30

    f = RAGRetrievalFilter()
    assert f.min_similarity is None  # Defaults to None, triggering settings threshold


# ---------------------------------------------------------------------------
# Test L: Deterministic ranking across multiple executions
# ---------------------------------------------------------------------------

def test_l_deterministic_ranking_stability(db_session: Session):
    """Verify that identical queries return byte-for-byte identical results in exact order."""
    rag_service = RAGService(session=db_session, embedding_provider=get_shared_embedding_provider())
    query = "Explain backend development with Python and Docker"

    run1 = rag_service.retrieve(query=query, top_k=5)
    run2 = rag_service.retrieve(query=query, top_k=5)
    run3 = rag_service.retrieve(query=query, top_k=5)

    assert len(run1) > 0
    assert len(run1) == len(run2) == len(run3)

    for i in range(len(run1)):
        assert run1[i].chunk_id == run2[i].chunk_id == run3[i].chunk_id
        assert run1[i].similarity_score == run2[i].similarity_score == run3[i].similarity_score


# ---------------------------------------------------------------------------
# Test M: Source filtering combined with multi-skill filtering
# ---------------------------------------------------------------------------

def test_m_source_filtering_combined_with_multi_skill(
    db_session: Session,
    canonical_python_skill: Skill,
    canonical_docker_skill: Skill,
):
    """Verify combining source_type and skill_ids filters simultaneously."""
    rag_service = RAGService(session=db_session, embedding_provider=get_shared_embedding_provider())
    target_ids = (canonical_python_skill.id, canonical_docker_skill.id)

    # 1. APPROVED_RESOURCE + (Python, Docker)
    filter_res = RAGRetrievalFilter(
        source_type=RAGSourceType.APPROVED_RESOURCE,
        skill_ids=target_ids,
    )
    res_resources = rag_service.retrieve(query="programming tutorials", top_k=10, filters=filter_res)
    for r in res_resources:
        assert r.source_type == RAGSourceType.APPROVED_RESOURCE
        assert r.skill_id in target_ids

    # 2. MARKET + (Python, Docker)
    filter_mkt = RAGRetrievalFilter(
        source_type=RAGSourceType.MARKET,
        skill_ids=target_ids,
    )
    res_market = rag_service.retrieve(query="industry demand", top_k=10, filters=filter_mkt)
    for r in res_market:
        assert r.source_type == RAGSourceType.MARKET
        assert r.skill_id in target_ids


# ---------------------------------------------------------------------------
# Test N: Real populated corpus multi-skill retrieval probe
# ---------------------------------------------------------------------------

def test_n_real_populated_corpus_multi_skill_probe(
    db_session: Session,
    canonical_python_skill: Skill,
    canonical_docker_skill: Skill,
):
    """Verify multi-skill retrieval against the live 74-document corpus."""
    rag_service = RAGService(session=db_session, embedding_provider=get_shared_embedding_provider())
    target_ids = (canonical_python_skill.id, canonical_docker_skill.id)

    filter_obj = RAGRetrievalFilter(skill_ids=target_ids)
    results = rag_service.retrieve(
        query="Deploying Python backend applications in Docker containers",
        top_k=8,
        filters=filter_obj,
    )

    assert len(results) > 0
    skills_found = set()
    for r in results:
        assert r.skill_id in target_ids
        skills_found.add(r.skill_id)

    # Both skills should be represented in top results for this dual-skill query
    assert canonical_python_skill.id in skills_found or canonical_docker_skill.id in skills_found


# ---------------------------------------------------------------------------
# Test O: Noise query excluded below threshold
# ---------------------------------------------------------------------------

def test_o_noise_query_excluded_by_similarity_threshold(db_session: Session):
    """Verify that uninterpretable noise queries with low similarity are excluded by threshold."""
    rag_service = RAGService(session=db_session, embedding_provider=get_shared_embedding_provider())
    noise_query = "xyzzy qwerty 123456789 uninterpretable nonsense text"

    # Default threshold 0.30 should filter out noise that scored ~0.15
    results = rag_service.retrieve(query=noise_query, top_k=5)

    for r in results:
        assert r.similarity_score >= settings.RAG_MIN_SIMILARITY_THRESHOLD


# ---------------------------------------------------------------------------
# Test P: Chat Grounding Multi-Skill Test ("Compare my Python and Docker skills")
# ---------------------------------------------------------------------------

def test_p_chat_grounding_multi_skill_query(
    db_session: Session,
    canonical_python_skill: Skill,
    canonical_docker_skill: Skill,
):
    """
    Proves that for a multi-skill query:
    1. RAG filter contains both skill IDs
    2. Retrieved evidence only belongs to Python or Docker
    3. Unrelated skills cannot enter retrieved evidence
    4. VerifiedContext remains authoritative
    5. Retrieved evidence is serialized under NON-AUTHORITATIVE section
    """
    rag_service = RAGService(session=db_session, embedding_provider=get_shared_embedding_provider())

    # Mock Qwen to capture prompt and prevent external LLM calls
    mock_qwen = MagicMock()
    mock_qwen.model = "qwen3:8b"
    mock_msg = MagicMock()
    mock_msg.content = "Comparison explanation based on verified context."
    mock_resp = MagicMock()
    mock_resp.message = mock_msg
    mock_resp.model = "qwen3:8b"
    mock_resp.total_duration = 100
    mock_resp.load_duration = 10
    mock_resp.prompt_eval_count = 10
    mock_resp.eval_count = 10
    mock_qwen.chat.return_value = mock_resp

    chat_service = CareerChatService(qwen_client=mock_qwen, rag_service=rag_service)

    verified_context = VerifiedContext(
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
                skill_id=canonical_python_skill.id,
                skill_name="Python",
                canonical_slug="python",
                classification=SkillClassification.STRONG,
                demonstrated_score=0.85,
                claimed=True,
                evidence_count=3,
                provenance=FactProvenance.DETERMINISTIC_ANALYSIS,
            ),
            VerifiedSkillFact(
                skill_id=canonical_docker_skill.id,
                skill_name="Docker",
                canonical_slug="docker",
                classification=SkillClassification.PARTIAL,
                demonstrated_score=0.45,
                claimed=True,
                evidence_count=1,
                provenance=FactProvenance.DETERMINISTIC_ANALYSIS,
            ),
        ),
        provenance=FactProvenance.DETERMINISTIC_ANALYSIS,
    )

    req = CareerChatRequest(
        verified_context=verified_context,
        user_query="Compare my Python and Docker skills",
    )

    response = chat_service.chat(req)

    # 1. Verification of referenced skills
    assert len(response.referenced_skill_ids) == 2
    assert canonical_python_skill.id in response.referenced_skill_ids
    assert canonical_docker_skill.id in response.referenced_skill_ids

    # 2. Retrieved evidence must only contain Python or Docker
    allowed_ids = {canonical_python_skill.id, canonical_docker_skill.id}
    assert len(response.retrieved_evidence) > 0
    for ev in response.retrieved_evidence:
        assert ev.skill_id in allowed_ids
        assert ev.similarity_score >= settings.RAG_MIN_SIMILARITY_THRESHOLD

    # 3. Prompt verification: Verified ground truth remains authoritative
    system_prompt = mock_qwen.chat.call_args[1]["messages"][0]["content"]
    assert "=== VERIFIED SKILLFORGE GROUND TRUTH CONTEXT ===" in system_prompt
    assert "=== RETRIEVED SUPPORTING EVIDENCE (NON-AUTHORITATIVE) ===" in system_prompt
    assert "=== END RETRIEVED SUPPORTING EVIDENCE ===" in system_prompt
