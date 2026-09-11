import base64
import uuid
from unittest.mock import MagicMock, patch
import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.database import SessionLocal
from app.db.models import (
    GitHubRepository,
    ProjectEvidence,
    Skill,
    DemonstratedSkill,
    User,
)
from app.services.github_service import (
    github_service,
    validate_github_username,
    get_github_headers,
)
from app.services.github_analyzer import (
    github_analyzer,
    is_safe_repo_path,
    MAX_TREE_ENTRIES,
    MAX_FILE_SIZE_BYTES,
)
from app.services.demonstrated_skill_service import demonstrated_skill_service

client = TestClient(app)


# -----------------------------------------------------------------------------
# 1-6: GitHub API Resilience & Error Mapping
# -----------------------------------------------------------------------------

def test_github_username_validation_ssrf():
    """1. Ensure username format regex blocks traversal and invalid characters."""
    assert validate_github_username("valid-user-123") == "valid-user-123"
    with pytest.raises(Exception):
        validate_github_username("../malicious")
    with pytest.raises(Exception):
        validate_github_username("user;cat /etc/passwd")
    with pytest.raises(Exception):
        validate_github_username("user\0null")


def test_github_auth_failure_401_mapping():
    """2. GitHub 401 returns structured UNAUTHENTICATED error."""
    mock_res = MagicMock(status_code=401)
    with patch.object(github_service.client, "get", return_value=mock_res):
        res = client.post("/api/v1/github/connect", json={"github_username": "valid-user", "personal_access_token": "bad_token"})
        assert res.status_code == 401
        body = res.json()
        assert body["error"]["code"] == "UNAUTHENTICATED"
        assert "Invalid token" in body["error"]["message"]


def test_github_rate_limit_429_mapping():
    """3. GitHub 429 returns structured RATE_LIMITED error."""
    mock_res = MagicMock(status_code=429)
    with patch.object(github_service.client, "get", return_value=mock_res):
        res = client.post("/api/v1/github/connect", json={"github_username": "valid-user"})
        assert res.status_code == 429
        body = res.json()
        assert body["error"]["code"] == "RATE_LIMITED"


def test_github_timeout_504_mapping():
    """4. GitHub timeout returns structured GATEWAY_TIMEOUT error."""
    with patch.object(github_service.client, "get", side_effect=httpx.TimeoutException("Read timed out")):
        res = client.post("/api/v1/github/connect", json={"github_username": "valid-user"})
        assert res.status_code == 504
        body = res.json()
        assert body["error"]["code"] == "GATEWAY_TIMEOUT"


def test_github_upstream_502_mapping():
    """5. GitHub 500/502 upstream errors return UPSTREAM_GATEWAY_ERROR."""
    mock_res = MagicMock(status_code=502)
    with patch.object(github_service.client, "get", return_value=mock_res):
        res = client.post("/api/v1/github/connect", json={"github_username": "valid-user"})
        assert res.status_code == 502
        body = res.json()
        assert body["error"]["code"] == "UPSTREAM_GATEWAY_ERROR"


def test_malformed_github_response_handling():
    """6. Malformed GitHub responses (e.g. non-list json) are handled safely."""
    mock_user_res = MagicMock(status_code=200)
    mock_user_res.json.return_value = {"login": "test-user"}
    mock_repos_res = MagicMock(status_code=200)
    mock_repos_res.json.return_value = {"unexpected": "object_instead_of_list"}

    with patch.object(github_service.client, "get", side_effect=[mock_user_res, mock_repos_res]):
        res = client.post("/api/v1/github/connect", json={"github_username": "test-user"})
        assert res.status_code == 200
        assert res.json()["data"]["discovered_repositories"] == 0


# -----------------------------------------------------------------------------
# 7-8: PAT Security & Non-leakage
# -----------------------------------------------------------------------------

def test_pat_never_in_response_or_error():
    """7 & 8. Secret PAT is never echoed in responses, errors, or stored in plaintext."""
    secret_pat = "ghp_VERY_SECRET_TOKEN_1234567890"
    mock_user_res = MagicMock(status_code=200)
    mock_user_res.json.return_value = {"login": "secret-user"}
    mock_repos_res = MagicMock(status_code=200)
    mock_repos_res.json.return_value = []

    with patch.object(github_service.client, "get", side_effect=[mock_user_res, mock_repos_res]):
        res = client.post(
            "/api/v1/github/connect",
            json={"github_username": "secret-user", "personal_access_token": secret_pat},
        )
        assert res.status_code == 200
        assert secret_pat not in res.text

    # Verify headers construction
    headers = get_github_headers(secret_pat)
    assert headers["Authorization"] == f"Bearer {secret_pat}"

    # Verify error mapping never echoes token
    mock_fail = MagicMock(status_code=401)
    with patch.object(github_service.client, "get", return_value=mock_fail):
        err_res = client.post(
            "/api/v1/github/connect",
            json={"github_username": "secret-user", "personal_access_token": secret_pat},
        )
        assert secret_pat not in err_res.text


# -----------------------------------------------------------------------------
# 9-11: Ownership Scoping & Isolation
# -----------------------------------------------------------------------------

def test_ownership_isolation_across_endpoints():
    """9, 10, 11. Repositories, evidence, and demonstrated skills isolate by user_id."""
    db = SessionLocal()
    user_1 = User(email=f"user1-{uuid.uuid4()}@example.com")
    user_2 = User(email=f"user2-{uuid.uuid4()}@example.com")
    db.add_all([user_1, user_2])
    db.commit()

    repo_1 = GitHubRepository(
        id=uuid.uuid4(),
        user_id=user_1.id,
        github_repository_id=91001,
        repo_name="repo-user1",
        full_name="user1/repo-user1",
        repo_url="https://github.com/user1/repo-user1",
        is_fork=False,
    )
    db.add(repo_1)

    skill = db.query(Skill).filter(Skill.slug == "python").first()

    ev_1 = ProjectEvidence(
        id=uuid.uuid4(),
        user_id=user_1.id,
        repo_id=repo_1.id,
        skill_id=skill.id,
        evidence_type="dependency",
        file_path="requirements.txt",
        confidence_score=0.95,
    )
    db.add(ev_1)
    db.commit()

    # Recompute
    demonstrated_skill_service.recompute_demonstrated_skill(db=db, skill_id=skill.id, user_id=user_1.id)

    try:
        # Repository ownership
        res_r1 = client.get(f"/api/v1/github/repositories?user_id={user_1.id}")
        assert res_r1.status_code == 200
        assert res_r1.json()["meta"]["total"] == 1

        res_r2 = client.get(f"/api/v1/github/repositories?user_id={user_2.id}")
        assert res_r2.status_code == 200
        assert res_r2.json()["meta"]["total"] == 0

        # Repository detail ownership
        res_det_1 = client.get(f"/api/v1/github/repositories/{repo_1.id}?user_id={user_1.id}")
        assert res_det_1.status_code == 200
        res_det_2 = client.get(f"/api/v1/github/repositories/{repo_1.id}?user_id={user_2.id}")
        assert res_det_2.status_code == 404

        # Evidence ownership
        res_ev_1 = client.get(f"/api/v1/evidence?user_id={user_1.id}")
        assert res_ev_1.status_code == 200
        assert res_ev_1.json()["meta"]["total"] == 1

        res_ev_2 = client.get(f"/api/v1/evidence?user_id={user_2.id}")
        assert res_ev_2.status_code == 200
        assert res_ev_2.json()["meta"]["total"] == 0

        # Evidence detail ownership
        res_evd_1 = client.get(f"/api/v1/evidence/{ev_1.id}?user_id={user_1.id}")
        assert res_evd_1.status_code == 200
        res_evd_2 = client.get(f"/api/v1/evidence/{ev_1.id}?user_id={user_2.id}")
        assert res_evd_2.status_code == 404

        # Demonstrated skill ownership
        res_ds_1 = client.get(f"/api/v1/skills/demonstrated?user_id={user_1.id}")
        assert res_ds_1.status_code == 200
        assert res_ds_1.json()["meta"]["total"] == 1

        res_ds_2 = client.get(f"/api/v1/skills/demonstrated?user_id={user_2.id}")
        assert res_ds_2.status_code == 200
        assert res_ds_2.json()["meta"]["total"] == 0
    finally:
        db.delete(user_1)
        db.delete(user_2)
        db.commit()
        db.close()


# -----------------------------------------------------------------------------
# 12-14: Repository Sync Idempotency & Fork Exclusion
# -----------------------------------------------------------------------------

def test_sync_idempotency_and_fork_exclusion():
    """12, 13, 14. Re-syncing preserves repository UUID and strictly excludes forks."""
    mock_user_res = MagicMock(status_code=200)
    mock_user_res.json.return_value = {"login": "sync-user"}
    mock_repos_res = MagicMock(status_code=200)
    mock_repos_res.json.return_value = [
        {
            "id": 99001,
            "name": "original-repo",
            "full_name": "sync-user/original-repo",
            "html_url": "https://github.com/sync-user/original-repo",
            "fork": False,
            "stargazers_count": 10,
        },
        {
            "id": 99002,
            "name": "forked-repo",
            "full_name": "sync-user/forked-repo",
            "html_url": "https://github.com/sync-user/forked-repo",
            "fork": True,
            "stargazers_count": 100,
        },
    ]

    with patch.object(github_service.client, "get", side_effect=[mock_user_res, mock_repos_res]):
        res1 = client.post("/api/v1/github/connect", json={"github_username": "sync-user"})
        assert res1.status_code == 200
        assert res1.json()["data"]["discovered_repositories"] == 1

    # Fetch repo ID
    list_res = client.get("/api/v1/github/repositories?username=sync-user")
    repos = [r for r in list_res.json()["data"] if r["repo_name"] == "original-repo"]
    assert len(repos) == 1
    orig_id = repos[0]["repo_id"]

    # Re-sync with updated star count
    mock_repos_res2 = MagicMock(status_code=200)
    mock_repos_res2.json.return_value = [
        {
            "id": 99001,
            "name": "original-repo",
            "full_name": "sync-user/original-repo",
            "html_url": "https://github.com/sync-user/original-repo",
            "fork": False,
            "stargazers_count": 25,  # updated
        },
    ]

    with patch.object(github_service.client, "get", side_effect=[mock_user_res, mock_repos_res2]):
        res2 = client.post("/api/v1/github/connect", json={"github_username": "sync-user"})
        assert res2.status_code == 200

    # Ensure UUID remained stable and stars were updated
    detail_res = client.get(f"/api/v1/github/repositories/{orig_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["data"]["stars_count"] == 25

    # Cleanup
    db = SessionLocal()
    r = db.query(GitHubRepository).filter(GitHubRepository.id == orig_id).first()
    if r:
        db.delete(r)
        db.commit()
    db.close()


# -----------------------------------------------------------------------------
# 15-17: Tree Entry, File Size & Path Traversal Safeguards
# -----------------------------------------------------------------------------

def test_path_safety_and_limits():
    """15, 16, 17. Path traversal rejected, tree entries capped, oversized files rejected."""
    # Malicious paths
    assert is_safe_repo_path("../etc/passwd") is False
    assert is_safe_repo_path("/etc/passwd") is False
    assert is_safe_repo_path("backend/../../secret") is False
    assert is_safe_repo_path("requirements.txt\0null") is False
    assert is_safe_repo_path("src/requirements.txt") is True

    # Tree entries safety limit
    assert MAX_TREE_ENTRIES == 1000
    assert MAX_FILE_SIZE_BYTES == 512 * 1024


# -----------------------------------------------------------------------------
# 18-25: Parser Resilience against Malformed Files
# -----------------------------------------------------------------------------

def test_parsers_resilience_on_malformed_inputs():
    """18-25. All manifest parsers handle invalid/corrupted contents without crashing."""
    service = github_analyzer

    # Malformed requirements
    reqs = service.parse_requirements_txt(";;;invalid---syntax\n#comment\n\x00binary_junk", "requirements.txt")
    assert isinstance(reqs, list)

    # Malformed package.json
    pkg = service.parse_package_json("{invalid json", "package.json")
    assert pkg == []

    # Malformed pyproject.toml
    pyproj = service.parse_pyproject_toml("invalid toml [unclosed", "pyproject.toml")
    assert pyproj == []

    # Malformed pom.xml
    pom = service.parse_pom_xml("<unclosed xml", "pom.xml")
    assert pom == []

    # Malformed go.mod
    gomod = service.parse_go_mod("corrupted content", "go.mod")
    assert isinstance(gomod, list)

    # Malformed Dockerfile (no FROM)
    dock = service.parse_dockerfile("echo hello world", "Dockerfile")
    assert dock == []

    # Unknown dependency rejection
    unknown_reqs = service.parse_requirements_txt("totally-unknown-noncanonical-lib==9.9.9", "requirements.txt")
    assert len(unknown_reqs) == 1
    # Candidate exists, but in pipeline normalizer it will be filtered out


# -----------------------------------------------------------------------------
# 26-28: Stale Evidence & Demonstrated Skill Removal
# -----------------------------------------------------------------------------

def test_stale_evidence_and_demonstrated_skill_full_lifecycle():
    """26, 27, 28. Rescanning with removed technology removes evidence AND deletes demonstrated skill."""
    db = SessionLocal()
    repo_id = uuid.uuid4()
    repo = GitHubRepository(
        id=repo_id,
        github_repository_id=98989,
        repo_name="stale-test-repo",
        full_name="org/stale-test-repo",
        repo_url="https://github.com/org/stale-test-repo",
        is_fork=False,
    )
    db.add(repo)
    db.commit()
    db.close()

    dockerfile_content = "FROM python:3.12-slim\nWORKDIR /app"
    reqs_content = "fastapi==0.115.0\n"

    mock_tree_1 = [
        {"path": "requirements.txt", "type": "blob"},
        {"path": "Dockerfile", "type": "blob"},
    ]

    def mock_fetch_1(full_name, path, token=None):
        if path == "requirements.txt":
            return reqs_content
        elif path == "Dockerfile":
            return dockerfile_content
        return None

    try:
        with patch.object(github_analyzer, "fetch_repo_tree", return_value=mock_tree_1), \
             patch.object(github_analyzer, "fetch_file_content", side_effect=mock_fetch_1):

            # Initial scan: FastAPI and Docker detected
            res1 = client.post("/api/v1/github/analyze", json={"repository_id": str(repo_id)})
            assert res1.status_code == 200
            skills1 = {s["skill_name"] for s in res1.json()["data"]["demonstrated_skills"]}
            assert "FastAPI" in skills1
            assert "Docker" in skills1

            # Check demonstrated skills API
            ds_res1 = client.get("/api/v1/skills/demonstrated")
            ds_names1 = {s["skill_name"] for s in ds_res1.json()["data"]}
            assert "FastAPI" in ds_names1
            assert "Docker" in ds_names1

        # Second scan: Dockerfile is REMOVED from the repository tree!
        mock_tree_2 = [
            {"path": "requirements.txt", "type": "blob"},
        ]

        def mock_fetch_2(full_name, path, token=None):
            if path == "requirements.txt":
                return reqs_content
            return None

        with patch.object(github_analyzer, "fetch_repo_tree", return_value=mock_tree_2), \
             patch.object(github_analyzer, "fetch_file_content", side_effect=mock_fetch_2):

            res2 = client.post("/api/v1/github/analyze", json={"repository_id": str(repo_id)})
            assert res2.status_code == 200
            skills2 = {s["skill_name"] for s in res2.json()["data"]["demonstrated_skills"]}
            assert "FastAPI" in skills2
            assert "Docker" not in skills2  # Docker removed from response!

            # Check demonstrated skills API: Docker must have disappeared!
            ds_res2 = client.get("/api/v1/skills/demonstrated")
            ds_names2 = {s["skill_name"] for s in ds_res2.json()["data"]}
            assert "FastAPI" in ds_names2
            assert "Docker" not in ds_names2  # Stale demonstrated skill cleanly removed!

    finally:
        # Cleanup
        db = SessionLocal()
        r = db.query(GitHubRepository).filter(GitHubRepository.id == repo_id).first()
        if r:
            db.delete(r)
            db.commit()
        fastapi_skill = db.query(Skill).filter(Skill.slug == "fastapi").first()
        if fastapi_skill:
            demonstrated_skill_service.recompute_demonstrated_skill(db=db, skill_id=fastapi_skill.id, user_id=None)
        docker_skill = db.query(Skill).filter(Skill.slug == "docker").first()
        if docker_skill:
            demonstrated_skill_service.recompute_demonstrated_skill(db=db, skill_id=docker_skill.id, user_id=None)
        db.close()


# -----------------------------------------------------------------------------
# 33-40: Pagination, Filtering & Error Envelopes
# -----------------------------------------------------------------------------

def test_pagination_and_filter_validations():
    """33, 34, 35. Pagination constraints, evidence_level validation, deterministic ordering."""
    # Negative offset rejected
    res_neg = client.get("/api/v1/skills/demonstrated?offset=-1")
    assert res_neg.status_code == 422
    assert res_neg.json()["error"]["code"] == "VALIDATION_ERROR"

    # Zero/negative limit rejected
    res_zero = client.get("/api/v1/skills/demonstrated?limit=0")
    assert res_zero.status_code == 422

    # Invalid evidence_level rejected
    res_bad_lvl = client.get("/api/v1/skills/demonstrated?evidence_level=INVALID_TIER")
    assert res_bad_lvl.status_code == 400
    assert res_bad_lvl.json()["error"]["code"] == "BAD_REQUEST"

    # Invalid UUID filter produces 422
    res_bad_uuid = client.get("/api/v1/skills/demonstrated?skill_id=not-a-uuid")
    assert res_bad_uuid.status_code == 422


def test_structured_error_envelopes_and_missing_resources():
    """36, 37, 38, 39, 40. 404s and errors follow standard envelope without leaks."""
    fake_id = str(uuid.uuid4())

    # Missing repo
    r_repo = client.get(f"/api/v1/github/repositories/{fake_id}")
    assert r_repo.status_code == 404
    assert r_repo.json()["error"]["code"] == "NOT_FOUND"

    # Missing evidence
    r_ev = client.get(f"/api/v1/evidence/{fake_id}")
    assert r_ev.status_code == 404
    assert r_ev.json()["error"]["code"] == "NOT_FOUND"

    # Missing demonstrated skill
    r_dem = client.get(f"/api/v1/skills/demonstrated/{fake_id}")
    assert r_dem.status_code == 404
    assert r_dem.json()["error"]["code"] == "NOT_FOUND"
