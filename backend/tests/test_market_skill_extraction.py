"""
Unit and integration tests for Deterministic Skill Extraction + Canonical Normalization (P1-D).

Verifies all 30 required specifications across:
1. Taxonomy matching (canonical name, aliases, case-insensitivity, multi-word, punctuation variants)
2. Boundary safety (C/R/Go no false positives, token boundaries, overlap resolution, longest phrase)
3. Deduplication (repeated mentions, title vs description precedence)
4. Evidence contracts (verbatim text, matched alias, source field, deterministic metadata)
5. Idempotent PostgreSQL persistence & reconciliation (market_job_skills table, upserts, deletes stale skills)
6. Security (zero credentials, no authorization headers)
7. Edge cases (empty text, no matches, malformed data, isolation from MVP tables)
"""

from datetime import datetime, timezone
import uuid
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import IndustrySkillDemand, MarketJob, MarketJobSkill, Skill, SkillAlias
from app.services.market.extraction.matcher import (
    DeterministicSkillMatcher,
    extract_evidence_snippet,
)
from app.services.market.extraction.service import MarketSkillExtractionService
from app.services.market.models import MarketJobSkillEvidence, MarketSkillExtractionMetrics
from app.services.market.repository import MarketJobRepository, MarketJobSkillRepository


@pytest.fixture
def db():
    """Provides a transactional database session and cleans up test records."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        # Clean up any test market_jobs (cascades to test market_job_skills)
        session.query(MarketJob).filter(MarketJob.source.like("test_%")).delete(synchronize_session=False)
        session.commit()
        session.close()


def _create_test_job(db: Session, title: str, description: str, ext_id: str = "ext-p1d-001") -> MarketJob:
    """Helper to create and persist a test market job."""
    job = MarketJob(
        id=uuid.uuid4(),
        source="test_p1d",
        external_job_id=ext_id,
        title=title,
        description=description,
        company_name="Test Corp",
        location="Remote",
        created_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


# ===========================================================================
# 1. TAXONOMY MATCHING
# ===========================================================================

def test_existing_canonical_skill_matched(db: Session):
    """1. Existing canonical skill name is matched."""
    matcher = DeterministicSkillMatcher(db=db)
    matches = matcher.match_text_spans("We are building backend services using Python and Docker.", source_field="description")

    names = {m.canonical_skill_name for m in matches}
    assert "Python" in names
    assert "Docker" in names


def test_existing_alias_maps_to_canonical_skill(db: Session):
    """2. Existing alias maps to canonical skill."""
    matcher = DeterministicSkillMatcher(db=db)
    # 'postgres' -> PostgreSQL, 'k8s' -> Kubernetes, 'csharp' -> C#
    text = "Experience with postgres, k8s, and csharp required."
    matches = matcher.match_text_spans(text, source_field="description")

    matches_by_canonical = {m.canonical_skill_name: m for m in matches}
    assert "PostgreSQL" in matches_by_canonical
    assert matches_by_canonical["PostgreSQL"].matched_alias.lower() == "postgres"

    assert "Kubernetes" in matches_by_canonical
    assert matches_by_canonical["Kubernetes"].matched_alias.lower() == "k8s"

    assert "C#" in matches_by_canonical
    assert matches_by_canonical["C#"].matched_alias.lower() == "csharp"


def test_matching_is_case_insensitive(db: Session):
    """3. Matching is case-insensitive for general taxonomy terms."""
    matcher = DeterministicSkillMatcher(db=db)
    text = "We use PYTHON, pOsTgReS, and fAsTaPi."
    matches = matcher.match_text_spans(text, source_field="description")

    names = {m.canonical_skill_name for m in matches}
    assert "Python" in names
    assert "PostgreSQL" in names
    assert "FastAPI" in names


def test_valid_multi_word_skill_matches(db: Session):
    """4. Valid multi-word skill matches as a cohesive phrase."""
    matcher = DeterministicSkillMatcher(db=db)
    text = "We build applications using Spring Boot, Docker Compose, and GitHub Actions."
    matches = matcher.match_text_spans(text, source_field="description")

    names = {m.canonical_skill_name for m in matches}
    assert "Spring Boot" in names
    assert "Docker Compose" in names
    assert "GitHub Actions" in names


def test_punctuation_variants_supported_by_existing_aliases(db: Session):
    """5. Punctuation variants supported by existing aliases normalize to canonical skill."""
    matcher = DeterministicSkillMatcher(db=db)
    # React variants: 'React.js', 'ReactJS', 'React JS', 'react'
    text1 = "Seeking React.js developer."
    text2 = "Seeking ReactJS developer."
    text3 = "Seeking React JS developer."

    m1 = matcher.match_text_spans(text1, source_field="description")
    m2 = matcher.match_text_spans(text2, source_field="description")
    m3 = matcher.match_text_spans(text3, source_field="description")

    assert len(m1) == 1 and m1[0].canonical_skill_name == "React"
    assert len(m2) == 1 and m2[0].canonical_skill_name == "React"
    assert len(m3) == 1 and m3[0].canonical_skill_name == "React"


def test_invalid_unrecognized_skill_is_not_created(db: Session):
    """6. Invalid/unrecognized skills are not created or matched."""
    matcher = DeterministicSkillMatcher(db=db)
    text = "We need someone with excellent Communication, Quantum Leadership, and Excel skills."
    matches = matcher.match_text_spans(text, source_field="description")

    assert len(matches) == 0


def test_no_second_taxonomy_introduced(db: Session):
    """7. Matcher binds strictly to canonical Skill IDs from PostgreSQL."""
    matcher = DeterministicSkillMatcher(db=db)
    matches = matcher.match_text_spans("Python, Java, TypeScript", source_field="description")

    canonical_skills = {s.id: s.name for s in db.query(Skill).all()}
    for m in matches:
        assert m.skill_id in canonical_skills
        assert canonical_skills[m.skill_id] == m.canonical_skill_name


# ===========================================================================
# 2. BOUNDARY SAFETY
# ===========================================================================

def test_short_skills_no_substring_false_positives(db: Session):
    """8. Short skills (C, R, Go) do not create substring false positives."""
    # Test with custom matcher including 1-char skills C and R
    skill_c = Skill(id=uuid.uuid4(), name="C", slug="c")
    skill_r = Skill(id=uuid.uuid4(), name="R", slug="r")
    skill_go = db.query(Skill).filter(Skill.slug == "go").first()

    custom_matcher = DeterministicSkillMatcher(skills=[skill_c, skill_r, skill_go], aliases=skill_go.aliases)

    # Substrings in words must NOT match
    negative_text = "A good developer knows how to configure cloud environments and regular algorithms."
    matches = custom_matcher.match_text_spans(negative_text, source_field="description")
    assert len(matches) == 0, f"Expected 0 matches in negative text, got: {matches}"

    # Lowercase English verb 'go' must NOT match Go
    go_verb_text = "You will go to client sites and manage operations."
    go_matches = custom_matcher.match_text_spans(go_verb_text, source_field="description")
    assert len(go_matches) == 0

    # Genuine standalone mentions MUST match
    positive_text = "Proficiency in C, R, and Go programming (or Golang)."
    pos_matches = custom_matcher.match_text_spans(positive_text, source_field="description")
    pos_names = {m.canonical_skill_name for m in pos_matches}
    assert "C" in pos_names
    assert "R" in pos_names
    assert "Go" in pos_names


def test_word_boundaries_work_correctly(db: Session):
    """9. Word boundaries work correctly around various punctuation marks."""
    matcher = DeterministicSkillMatcher(db=db)
    text = "Skills: [Python], 'FastAPI', (Docker) / PostgreSQL; Git & Redis."
    matches = matcher.match_text_spans(text, source_field="description")

    names = {m.canonical_skill_name for m in matches}
    assert {"Python", "FastAPI", "Docker", "PostgreSQL", "Git", "Redis"}.issubset(names)


def test_overlapping_aliases_are_deterministic(db: Session):
    """10. Overlapping aliases resolve deterministically without duplication."""
    # Test with Docker vs Docker Compose
    matcher = DeterministicSkillMatcher(db=db)
    text = "Must know Docker Compose well."
    matches = matcher.match_text_spans(text, source_field="description")

    # Should match 'Docker Compose', NOT separate 'Docker' and 'Docker Compose' at the same span
    assert len(matches) == 1
    assert matches[0].canonical_skill_name == "Docker Compose"


def test_longest_valid_phrase_behavior(db: Session):
    """11. Longest valid phrase takes precedence over shorter nested sub-terms."""
    skill_react = Skill(id=uuid.uuid4(), name="React", slug="react")
    skill_react_native = Skill(id=uuid.uuid4(), name="React Native", slug="react-native")

    alias_react = SkillAlias(id=uuid.uuid4(), skill_id=skill_react.id, alias="reactjs", normalized_alias="reactjs")
    alias_rn = SkillAlias(id=uuid.uuid4(), skill_id=skill_react_native.id, alias="react-native", normalized_alias="reactnative")

    matcher = DeterministicSkillMatcher(
        skills=[skill_react, skill_react_native],
        aliases=[alias_react, alias_rn],
    )

    text = "We are hiring a Senior React Native Developer."
    matches = matcher.match_text_spans(text, source_field="title")

    assert len(matches) == 1
    assert matches[0].canonical_skill_name == "React Native"
    assert matches[0].matched_alias == "React Native"


# ===========================================================================
# 3. DEDUPLICATION
# ===========================================================================

def test_repeated_skill_mentions_produce_one_canonical_relationship(db: Session):
    """12. Repeated skill mentions produce one canonical relationship per job."""
    matcher = DeterministicSkillMatcher(db=db)
    job_id = uuid.uuid4()
    text = "Python engineer. Python 3 required. 5+ years writing Python code in production."

    skills = matcher.extract_skills_for_job(
        title="Python Engineer",
        description=text,
        market_job_id=job_id,
    )

    python_matches = [s for s in skills if s.canonical_skill_name == "Python"]
    assert len(python_matches) == 1


def test_same_skill_in_title_and_description_does_not_duplicate(db: Session):
    """13. Same skill in title and description preserves title precedence and does not duplicate."""
    matcher = DeterministicSkillMatcher(db=db)
    job_id = uuid.uuid4()

    skills = matcher.extract_skills_for_job(
        title="FastAPI Backend Engineer",
        description="We build microservices using FastAPI and PostgreSQL.",
        market_job_id=job_id,
    )

    fastapi_match = next((s for s in skills if s.canonical_skill_name == "FastAPI"), None)
    assert fastapi_match is not None
    assert fastapi_match.source_field == "title"

    postgres_match = next((s for s in skills if s.canonical_skill_name == "PostgreSQL"), None)
    assert postgres_match is not None
    assert postgres_match.source_field == "description"


# ===========================================================================
# 4. EVIDENCE CONTRACT
# ===========================================================================

def test_evidence_comes_from_original_job_text(db: Session):
    """14. Evidence snippet comes directly from original job text without modification."""
    matcher = DeterministicSkillMatcher(db=db)
    description = "Extensive experience using Kubernetes in large-scale production clusters."

    matches = matcher.match_text_spans(description, source_field="description")
    assert len(matches) == 1
    k8s = matches[0]

    assert k8s.canonical_skill_name == "Kubernetes"
    assert k8s.evidence_text in description
    assert "Kubernetes" in k8s.evidence_text


def test_matched_alias_is_retained(db: Session):
    """15. Matched alias is retained alongside canonical skill name."""
    matcher = DeterministicSkillMatcher(db=db)
    matches = matcher.match_text_spans("Proficient in psql and k8s.", source_field="description")

    by_alias = {m.matched_alias: m.canonical_skill_name for m in matches}
    assert by_alias.get("psql") == "PostgreSQL"
    assert by_alias.get("k8s") == "Kubernetes"


def test_source_field_is_correct(db: Session):
    """16. Source field accurately records 'title' vs 'description'."""
    matcher = DeterministicSkillMatcher(db=db)
    skills = matcher.extract_skills_for_job(
        title="Go Developer",
        description="Must know PostgreSQL and Redis.",
    )

    by_name = {s.canonical_skill_name: s.source_field for s in skills}
    assert by_name["Go"] == "title"
    assert by_name["PostgreSQL"] == "description"
    assert by_name["Redis"] == "description"


def test_extraction_method_is_deterministic(db: Session):
    """17. Extraction method is explicitly 'deterministic_taxonomy_match' and deterministic."""
    matcher = DeterministicSkillMatcher(db=db)
    text = "Python and Docker"

    run1 = matcher.match_text_spans(text, source_field="title")
    run2 = matcher.match_text_spans(text, source_field="title")

    assert [m.canonical_skill_name for m in run1] == [m.canonical_skill_name for m in run2]
    assert all(m.extraction_method == "deterministic_taxonomy_match" for m in run1)
    assert all(m.confidence_score == 1.0 for m in run1)


# ===========================================================================
# 5. PERSISTENCE & RECONCILIATION
# ===========================================================================

def test_new_market_job_skills_insert(db: Session):
    """18. New market-job skills insert into PostgreSQL market_job_skills table."""
    job = _create_test_job(db, "Backend Lead", "Python, FastAPI, and Docker required.")
    service = MarketSkillExtractionService()

    extracted = service.extract_and_persist_for_job(job, db, commit=True)
    assert len(extracted) == 3

    repo = MarketJobSkillRepository()
    persisted = repo.get_skills_for_job(job.id, db)
    assert len(persisted) == 3

    persisted_skills = {p.skill.name for p in persisted}
    assert persisted_skills == {"Python", "FastAPI", "Docker"}


def test_duplicate_processing_is_idempotent(db: Session):
    """19. Repeated extraction runs on unchanged jobs produce 0 new inserts."""
    job = _create_test_job(db, "Cloud Architect", "AWS, Kubernetes, and Terraform.")
    repo = MarketJobSkillRepository()
    matcher = DeterministicSkillMatcher(db=db)

    skills = matcher.extract_skills_for_job(job.title, job.description, market_job_id=job.id)

    # First run: inserts
    ins1, upd1, unc1, del1 = repo.persist_job_skills(job.id, skills, db, reconcile=True)
    db.commit()
    assert ins1 == len(skills)
    assert unc1 == 0

    # Second run: unchanged
    ins2, upd2, unc2, del2 = repo.persist_job_skills(job.id, skills, db, reconcile=True)
    db.commit()
    assert ins2 == 0
    assert upd2 == 0
    assert unc2 == len(skills)
    assert del2 == 0


def test_duplicate_job_skill_prevented_by_unique_constraint(db: Session):
    """20. Uniqueness constraint uq_market_job_skills_job_skill prevents duplicate rows."""
    job = _create_test_job(db, "Python Dev", "Python programming")
    skill_python = db.query(Skill).filter(Skill.slug == "python").first()

    row1 = MarketJobSkill(
        id=uuid.uuid4(),
        market_job_id=job.id,
        skill_id=skill_python.id,
        matched_alias="python",
        source_field="title",
        evidence_text="Python Dev",
    )
    db.add(row1)
    db.commit()

    row2 = MarketJobSkill(
        id=uuid.uuid4(),
        market_job_id=job.id,
        skill_id=skill_python.id,
        matched_alias="python",
        source_field="description",
        evidence_text="Python programming",
    )
    db.add(row2)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_changed_extracted_skills_reconcile_correctly(db: Session):
    """21. Changed job text reconciles relationships (stale deleted, new inserted, common unchanged)."""
    job = _create_test_job(db, "Engineer", "Initial tech stack: Python and Redis.")
    service = MarketSkillExtractionService()

    # Initial extraction
    service.extract_and_persist_for_job(job, db, reconcile=True, commit=True)
    repo = MarketJobSkillRepository()
    initial_skills = {s.skill.name for s in repo.get_skills_for_job(job.id, db)}
    assert initial_skills == {"Python", "Redis"}

    # Update job text: replace Redis with PostgreSQL
    job.description = "Updated tech stack: Python and PostgreSQL."
    db.commit()

    # Re-run extraction
    service.extract_and_persist_for_job(job, db, reconcile=True, commit=True)
    reconciled_skills = {s.skill.name for s in repo.get_skills_for_job(job.id, db)}
    assert reconciled_skills == {"Python", "PostgreSQL"}
    assert "Redis" not in reconciled_skills


def test_unrelated_market_jobs_remain_isolated(db: Session):
    """22. Skills extracted for Job A do not affect skills for Job B."""
    job_a = _create_test_job(db, "Job A", "Python developer", ext_id="ext-iso-001")
    job_b = _create_test_job(db, "Job B", "Java developer", ext_id="ext-iso-002")

    service = MarketSkillExtractionService()
    service.extract_and_persist_for_job(job_a, db, commit=True)
    service.extract_and_persist_for_job(job_b, db, commit=True)

    repo = MarketJobSkillRepository()
    skills_a = [s.skill.name for s in repo.get_skills_for_job(job_a.id, db)]
    skills_b = [s.skill.name for s in repo.get_skills_for_job(job_b.id, db)]

    assert skills_a == ["Python"]
    assert skills_b == ["Java"]


def test_canonical_skills_remain_isolated(db: Session):
    """23. Persisting market job skills does not alter canonical skills or MVP skill_demand."""
    skills_before_count = db.query(Skill).count()
    demand_before = db.query(IndustrySkillDemand).all()
    demand_before_tuples = [(d.skill_id, d.role_id, d.demand_score) for d in demand_before]

    job = _create_test_job(db, "Full Stack Lead", "TypeScript, React, Node.js, and PostgreSQL.")
    service = MarketSkillExtractionService()
    service.extract_and_persist_for_job(job, db, commit=True)

    # Verify canonical skills unchanged
    assert db.query(Skill).count() == skills_before_count

    # Verify MVP skill_demand unchanged
    demand_after = db.query(IndustrySkillDemand).all()
    demand_after_tuples = [(d.skill_id, d.role_id, d.demand_score) for d in demand_after]
    assert demand_before_tuples == demand_after_tuples


# ===========================================================================
# 6. SECURITY
# ===========================================================================

def test_credentials_never_enter_skill_evidence(db: Session):
    """24. Credentials, secret tokens, and API keys are never stored in skill evidence."""
    job = _create_test_job(
        db,
        title="Python Developer",
        description="Requires Python and Docker for building scalable APIs.",
    )
    service = MarketSkillExtractionService()
    extracted = service.extract_and_persist_for_job(job, db, commit=True)

    repo = MarketJobSkillRepository()
    saved = repo.get_skills_for_job(job.id, db)
    assert len(saved) == 2

    for s in saved:
        serialized = f"{s.matched_alias} {s.evidence_text} {s.extraction_method}"
        assert "ADZUNA_APP_ID" not in serialized
        assert "ADZUNA_APP_KEY" not in serialized
        assert "Authorization" not in serialized
        assert "Bearer" not in serialized


def test_authorization_headers_never_persisted(db: Session):
    """25. Headers and authorization parameters are not part of market_job_skills schema."""
    columns = {c.name for c in MarketJobSkill.__table__.columns}
    assert "headers" not in columns
    assert "auth" not in columns
    assert "token" not in columns
    assert "api_key" not in columns


# ===========================================================================
# 7. EDGE CASES
# ===========================================================================

def test_empty_title_and_description(db: Session):
    """26. Empty or None title and description returns empty extraction safely."""
    matcher = DeterministicSkillMatcher(db=db)
    assert matcher.extract_skills_for_job("", "") == []
    assert matcher.extract_skills_for_job(None, None) == []
    assert matcher.extract_skills_for_job("   ", "\n\t  ") == []


def test_no_matching_skills_handled_cleanly(db: Session):
    """27. Job with no matching skills produces clean zero-skill metrics."""
    job = _create_test_job(db, "Executive Chef", "Prepare culinary dishes and lead kitchen staff.")
    service = MarketSkillExtractionService()
    extracted = service.extract_and_persist_for_job(job, db, commit=True)

    assert len(extracted) == 0
    repo = MarketJobSkillRepository()
    assert len(repo.get_skills_for_job(job.id, db)) == 0


def test_missing_or_deleted_market_job_fails_foreign_key(db: Session):
    """28. Attempting to persist skills for a non-existent market_job_id violates foreign key."""
    non_existent_id = uuid.uuid4()
    skill_python = db.query(Skill).filter(Skill.slug == "python").first()

    row = MarketJobSkill(
        id=uuid.uuid4(),
        market_job_id=non_existent_id,
        skill_id=skill_python.id,
        matched_alias="python",
        source_field="title",
    )
    db.add(row)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_missing_canonical_skill_reference_fails_foreign_key(db: Session):
    """29. Attempting to link to a non-existent skill_id violates foreign key."""
    job = _create_test_job(db, "Dev", "Coding")
    non_existent_skill_id = uuid.uuid4()

    row = MarketJobSkill(
        id=uuid.uuid4(),
        market_job_id=job.id,
        skill_id=non_existent_skill_id,
        matched_alias="fake",
        source_field="title",
    )
    db.add(row)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_malformed_market_job_skipped_by_batch_service(db: Session):
    """30. Malformed jobs with empty titles are skipped and tracked in metrics."""
    job_bad = MarketJob(
        id=uuid.uuid4(),
        source="test_p1d",
        external_job_id="bad-job-001",
        title="   ",  # whitespace only
        description="Has Python",
    )
    db.add(job_bad)
    db.commit()

    service = MarketSkillExtractionService()
    metrics = service.process_persisted_jobs(db, batch_size=10, source="test_p1d", commit=True)

    assert metrics.invalid_jobs_skipped >= 1


# ===========================================================================
# 8. BATCH PROCESSING METRICS AUDIT
# ===========================================================================

def test_batch_processing_metrics_accuracy(db: Session):
    """Verifies that MarketSkillExtractionService returns complete and accurate audit metrics."""
    job1 = _create_test_job(db, "Python Dev", "Python & Redis", ext_id="batch-001")
    job2 = _create_test_job(db, "Java Dev", "Java & Spring Boot", ext_id="batch-002")
    job3 = _create_test_job(db, "Receptionist", "Manage front desk", ext_id="batch-003")

    service = MarketSkillExtractionService()
    metrics = service.process_persisted_jobs(db, batch_size=10, source="test_p1d", commit=True)

    assert metrics.jobs_processed == 3
    assert metrics.jobs_with_skills == 2
    assert metrics.jobs_without_skills == 1
    assert metrics.skills_matched == 4  # Python, Redis, Java, Spring Boot
    assert metrics.unique_skill_relationships == 4
    assert metrics.persistence_inserts == 4

    summary = metrics.to_summary_dict()
    assert summary["jobs_processed"] == 3
    assert summary["persistence"]["inserts"] == 4
    assert len(summary["top_skills"]) == 4
