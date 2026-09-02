import uuid
from unittest.mock import MagicMock, patch
import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.database import SessionLocal
from app.db.models import GitHubRepository, ProjectEvidence, Skill
from app.services.github_analyzer import github_analyzer, GitHubAnalyzerService

client = TestClient(app)

SAMPLE_REQUIREMENTS = """
# Production API dependencies
fastapi==0.115.0
pydantic>=2.0.0
sqlalchemy>=2.0
redis~=5.0
unknown-internal-lib==1.0.0
"""

SAMPLE_PACKAGE_JSON = """
{
  "name": "my-dashboard",
  "dependencies": {
    "next": "^14.0.0",
    "react": "^18.2.0",
    "tailwindcss": "^3.4.0",
    "arbitrary-unknown-tool": "1.0.0"
  },
  "devDependencies": {
    "typescript": "^5.0.0"
  }
}
"""

SAMPLE_PYPROJECT_TOML = """
[project]
name = "data-pipeline"
dependencies = [
    "pandas>=2.0",
    "numpy>=1.24",
    "fastapi>=0.110.0"
]
"""

SAMPLE_POM_XML = """
<project>
  <dependencies>
    <dependency>
      <groupId>org.postgresql</groupId>
      <artifactId>postgresql</artifactId>
      <version>42.6.0</version>
    </dependency>
    <dependency>
      <groupId>com.example</groupId>
      <artifactId>unknown-mvn-pkg</artifactId>
    </dependency>
  </dependencies>
</project>
"""

SAMPLE_DOCKERFILE = """
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0"]
"""

SAMPLE_CI_WORKFLOW = """
name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pytest
"""


def test_requirements_txt_parser():
    """Verify requirements.txt parsing extracts candidate dependencies."""
    service = GitHubAnalyzerService()
    candidates = service.parse_requirements_txt(SAMPLE_REQUIREMENTS, "requirements.txt")
    names = {c.skill_name_candidate for c in candidates}
    assert "fastapi" in names
    assert "pydantic" in names
    assert "sqlalchemy" in names
    assert "redis" in names
    for c in candidates:
        assert c.evidence_type == "dependency"
        assert 0.0 <= c.confidence_score <= 1.0


def test_package_json_parser():
    """Verify package.json parsing extracts dependencies and devDependencies."""
    service = GitHubAnalyzerService()
    candidates = service.parse_package_json(SAMPLE_PACKAGE_JSON, "package.json")
    names = {c.skill_name_candidate for c in candidates}
    assert "react" in names
    assert "next" in names
    assert "typescript" in names
    assert "tailwindcss" in names


def test_dockerfile_and_ci_parsers():
    """Verify Dockerfile and CI workflow detection."""
    service = GitHubAnalyzerService()
    docker_cands = service.parse_dockerfile(SAMPLE_DOCKERFILE, "Dockerfile")
    assert len(docker_cands) == 1
    assert docker_cands[0].skill_name_candidate == "Docker"
    assert docker_cands[0].evidence_type == "dockerfile"
    assert docker_cands[0].confidence_score == 0.90

    ci_cands = service.parse_ci_workflow(SAMPLE_CI_WORKFLOW, ".github/workflows/ci.yml")
    assert len(ci_cands) == 1
    assert ci_cands[0].evidence_type == "ci_workflow"
    assert ci_cands[0].confidence_score == 0.85


def test_analyze_repository_full_lifecycle():
    """
    Requirements 4-13: Full repository analysis pipeline
    - Tree inspection
    - Manifest parsing
    - Canonical normalization
    - Unknown dependency filtering
    - Idempotent upsert & stale reconciliation
    """
    db = SessionLocal()
    repo_id = uuid.uuid4()
    test_repo = GitHubRepository(
        id=repo_id,
        user_id=None,
        github_repository_id=98765,
        repo_name="demo-service",
        full_name="demo-user/demo-service",
        repo_url="https://github.com/demo-user/demo-service",
        description="Demo microservice",
        default_branch="main",
        visibility="public",
        primary_language="Python",
        is_fork=False,
    )
    db.add(test_repo)
    db.commit()
    db.close()

    mock_tree = [
        {"path": "requirements.txt", "type": "blob"},
        {"path": "Dockerfile", "type": "blob"},
        {"path": ".github/workflows/ci.yml", "type": "blob"},
    ]

    def mock_fetch_content(full_name, path, token=None):
        if path == "requirements.txt":
            return SAMPLE_REQUIREMENTS
        elif path == "Dockerfile":
            return SAMPLE_DOCKERFILE
        elif path == ".github/workflows/ci.yml":
            return SAMPLE_CI_WORKFLOW
        return None

    with patch.object(github_analyzer, "fetch_repo_tree", return_value=mock_tree), \
         patch.object(github_analyzer, "fetch_file_content", side_effect=mock_fetch_content):

        # 1. First analysis via POST /api/v1/github/analyze
        res1 = client.post("/api/v1/github/analyze", json={"repository_id": str(repo_id)})
        assert res1.status_code == 200
        body1 = res1.json()

        assert "data" in body1
        data1 = body1["data"]
        assert data1["repository_id"] == str(repo_id)
        assert data1["analyzed"] is True
        assert data1["evidence_count"] >= 3

        demonstrated = {s["skill_name"]: s for s in data1["demonstrated_skills"]}
        # FastAPI, Docker, and Python (from language/dependencies) must be detected
        assert "FastAPI" in demonstrated
        assert "Docker" in demonstrated
        assert demonstrated["FastAPI"]["confidence_score"] == 0.95
        assert demonstrated["FastAPI"]["evidence_tier"] == "HIGH"
        assert demonstrated["Docker"]["confidence_score"] == 0.90

        # Requirement 9: Unknown dependency 'unknown-internal-lib' was rejected from canonical skills
        all_skill_names = {s["skill_name"] for s in data1["demonstrated_skills"]}
        assert "unknown-internal-lib" not in all_skill_names

        # 2. Requirement 12: Idempotent re-analysis
        res2 = client.post("/api/v1/github/analyze", json={"repository_id": str(repo_id)})
        assert res2.status_code == 200
        body2 = res2.json()
        # Count must remain exactly the same (no duplicate rows created)
        assert body2["data"]["evidence_count"] == data1["evidence_count"]

        # 3. Requirement 13: Stale evidence reconciliation
        # If requirements.txt is updated to remove redis, redis evidence is removed on re-analysis
        updated_requirements = "fastapi==0.115.0\npydantic>=2.0.0\n"

        def mock_fetch_updated(full_name, path, token=None):
            if path == "requirements.txt":
                return updated_requirements
            elif path == "Dockerfile":
                return SAMPLE_DOCKERFILE
            return None

        with patch.object(github_analyzer, "fetch_file_content", side_effect=mock_fetch_updated):
            res3 = client.post("/api/v1/github/analyze", json={"repository_id": str(repo_id)})
            assert res3.status_code == 200
            redis_ev = [s for s in res3.json()["data"]["demonstrated_skills"] if s["skill_name"] == "Redis"]
            assert len(redis_ev) == 0  # Reconciled and removed!

    # Clean up
    db = SessionLocal()
    r = db.query(GitHubRepository).filter(GitHubRepository.id == repo_id).first()
    if r:
        db.delete(r)
        db.commit()
    db.close()


def test_evidence_retrieval_and_filtering_api():
    """
    Requirements 12 & 22-24:
    - GET /api/v1/evidence (paginated, filtering by repo, skill, type)
    - GET /api/v1/evidence/{id} (detailed audit item)
    - 404 for missing evidence
    """
    db = SessionLocal()
    repo_id = uuid.uuid4()
    repo = GitHubRepository(
        id=repo_id,
        user_id=None,
        github_repository_id=55555,
        repo_name="evidence-test-repo",
        full_name="demo-user/evidence-test-repo",
        repo_url="https://github.com/demo-user/evidence-test-repo",
        is_fork=False,
    )
    db.add(repo)

    # Get skill IDs
    fastapi_skill = db.query(Skill).filter(Skill.slug == "fastapi").first()
    docker_skill = db.query(Skill).filter(Skill.slug == "docker").first()

    ev1 = ProjectEvidence(
        id=uuid.uuid4(),
        repo_id=repo_id,
        skill_id=fastapi_skill.id,
        evidence_type="dependency",
        file_path="requirements.txt",
        artifact_name="requirements.txt",
        evidence_description="FastAPI declared in requirements.txt",
        matched_content="fastapi>=0.115",
        evidence_metadata={"package": "fastapi"},
        confidence_score=0.95,
    )
    ev2 = ProjectEvidence(
        id=uuid.uuid4(),
        repo_id=repo_id,
        skill_id=docker_skill.id,
        evidence_type="dockerfile",
        file_path="Dockerfile",
        artifact_name="Dockerfile",
        evidence_description="Valid Dockerfile present",
        matched_content="FROM python:3.12",
        evidence_metadata={"instructions": ["FROM"]},
        confidence_score=0.90,
    )
    db.add(ev1)
    db.add(ev2)
    db.commit()
    ev1_id = str(ev1.id)
    ev2_id = str(ev2.id)
    db.close()

    try:
        # 1. GET /api/v1/evidence
        res = client.get(f"/api/v1/evidence?repository_id={repo_id}")
        assert res.status_code == 200
        body = res.json()
        assert "data" in body
        assert "meta" in body
        assert body["meta"]["total"] == 2
        assert len(body["data"]) == 2

        # 2. Filter by evidence_type=dockerfile
        filter_res = client.get(f"/api/v1/evidence?repository_id={repo_id}&evidence_type=dockerfile")
        assert filter_res.status_code == 200
        f_body = filter_res.json()
        assert f_body["meta"]["total"] == 1
        assert f_body["data"][0]["skill_name"] == "Docker"
        assert f_body["data"][0]["artifact_path"] == "Dockerfile"

        # 3. GET /api/v1/evidence/{evidence_id}
        detail_res = client.get(f"/api/v1/evidence/{ev1_id}")
        assert detail_res.status_code == 200
        d_body = detail_res.json()
        assert d_body["data"]["evidence_id"] == ev1_id
        assert d_body["data"]["skill_name"] == "FastAPI"
        assert d_body["data"]["confidence_score"] == 0.95
        assert d_body["data"]["evidence_description"] == "FastAPI declared in requirements.txt"

        # 4. Missing evidence returns 404
        non_existent = str(uuid.uuid4())
        res_404 = client.get(f"/api/v1/evidence/{non_existent}")
        assert res_404.status_code == 404
        assert res_404.json()["error"]["code"] == "NOT_FOUND"
    finally:
        db = SessionLocal()
        r = db.query(GitHubRepository).filter(GitHubRepository.id == repo_id).first()
        if r:
            db.delete(r)
            db.commit()
        db.close()


def test_analyze_missing_repository_returns_404():
    """Verify analysis of non-existent repository returns clean 404."""
    random_id = str(uuid.uuid4())
    res = client.post("/api/v1/github/analyze", json={"repository_id": random_id})
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"


def test_analyze_empty_request_returns_400():
    """Verify request with neither repository_id nor selected_repo_ids returns 400."""
    res = client.post("/api/v1/github/analyze", json={})
    assert res.status_code == 400
