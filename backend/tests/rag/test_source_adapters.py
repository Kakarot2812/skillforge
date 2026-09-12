"""Source adapter tests against real Postgres — verifies field mapping onto
real SkillForge tables and that adapters skip rows with no usable text."""
import uuid

import pytest

from app.db.database import SessionLocal
from app.db.models import GitHubRepository, ProjectEvidence, Resume, Skill, User
from app.rag.sources.github import GitHubRepositorySourceAdapter, ProjectEvidenceSourceAdapter
from app.rag.sources.manual import ManualSourceAdapter
from app.rag.sources.resume import ResumeSourceAdapter


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def user(db):
    record = User(email=f"adapter-test-{uuid.uuid4()}@example.com")
    db.add(record)
    db.commit()
    db.refresh(record)
    yield record
    db.delete(record)
    db.commit()


def test_github_repository_adapter_maps_real_fields(db, user):
    repo = GitHubRepository(
        user_id=user.id, repo_name="skillforge", full_name="octocat/skillforge",
        repo_url="https://github.com/octocat/skillforge", description="A career intelligence platform.",
        primary_language="Python",
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)
    try:
        adapter = GitHubRepositorySourceAdapter()
        docs = list(adapter.fetch_one(db, str(repo.id)))
        assert len(docs) == 1
        doc = docs[0]
        assert doc.source_type == "github_repository"
        assert doc.source_id == str(repo.id)
        assert doc.title == "octocat/skillforge"
        assert "career intelligence platform" in doc.text
        assert doc.user_id == user.id
        assert doc.source_url == repo.repo_url
    finally:
        db.delete(repo)
        db.commit()


def test_github_repository_adapter_skips_repo_with_no_text(db, user):
    repo = GitHubRepository(
        user_id=user.id, repo_name="empty-repo", repo_url="https://github.com/x/empty-repo",
        description=None, primary_language=None,
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)
    try:
        adapter = GitHubRepositorySourceAdapter()
        assert list(adapter.fetch_one(db, str(repo.id))) == []
    finally:
        db.delete(repo)
        db.commit()


def test_project_evidence_adapter_maps_real_fields(db, user):
    skill = Skill(name=f"TestSkill-{uuid.uuid4()}", slug=f"test-skill-{uuid.uuid4()}")
    repo = GitHubRepository(user_id=user.id, repo_name="repo", repo_url="https://github.com/x/repo")
    db.add_all([skill, repo])
    db.commit()
    db.refresh(skill)
    db.refresh(repo)

    evidence = ProjectEvidence(
        user_id=user.id, repo_id=repo.id, skill_id=skill.id, evidence_type="dependency",
        evidence_description="Found Docker usage.", matched_content="FROM python:3.12",
        confidence_score=0.9,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    try:
        adapter = ProjectEvidenceSourceAdapter()
        docs = list(adapter.fetch_one(db, str(evidence.id)))
        assert len(docs) == 1
        doc = docs[0]
        assert doc.source_type == "project_evidence"
        assert "Docker usage" in doc.text
        assert "FROM python:3.12" in doc.text
        assert doc.metadata["skill_name"] == skill.name
        assert doc.user_id == user.id
    finally:
        db.delete(evidence)
        db.delete(repo)
        db.delete(skill)
        db.commit()


def test_resume_adapter_maps_real_fields_and_skips_blank(db, user):
    resume = Resume(
        user_id=user.id, file_name="resume.pdf", file_type="pdf", file_size=123,
        storage_path="/tmp/resume.pdf", raw_text="Experienced backend engineer with Python and SQL skills.",
    )
    blank_resume = Resume(
        user_id=user.id, file_name="blank.pdf", file_type="pdf", file_size=1,
        storage_path="/tmp/blank.pdf", raw_text="   ",
    )
    db.add_all([resume, blank_resume])
    db.commit()
    db.refresh(resume)
    db.refresh(blank_resume)
    try:
        adapter = ResumeSourceAdapter()
        docs = list(adapter.fetch_one(db, str(resume.id)))
        assert len(docs) == 1
        assert "backend engineer" in docs[0].text
        assert docs[0].user_id == user.id

        assert list(adapter.fetch_one(db, str(blank_resume.id))) == []
    finally:
        db.delete(resume)
        db.delete(blank_resume)
        db.commit()


def test_manual_adapter_normalizes_direct_input():
    doc = ManualSourceAdapter.normalize(
        source_id="learning-resource-docker-101", title="Docker 101", text="Docker basics explained.",
        metadata={"difficulty": "beginner"},
    )
    assert doc.source_type == "manual"
    assert doc.title == "Docker 101"
    assert doc.metadata["difficulty"] == "beginner"
    assert doc.user_id is None


def test_manual_adapter_fetch_yields_nothing():
    adapter = ManualSourceAdapter()
    assert list(adapter.fetch(None)) == []
