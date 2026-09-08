import uuid
from unittest.mock import MagicMock, patch
import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.db.database import SessionLocal
from app.db.models import GitHubRepository
from app.services.github_service import github_service, GitHubService, validate_github_username

client = TestClient(app)

# Sample mock GitHub API responses
MOCK_USER_RESPONSE = {
    "login": "octocat",
    "id": 583231,
    "name": "The Octocat",
    "public_repos": 8,
}

MOCK_REPOS_PAGE_1 = [
    {
        "id": 101,
        "name": "super-service",
        "full_name": "octocat/super-service",
        "html_url": "https://github.com/octocat/super-service",
        "description": "Production microservice in Python",
        "default_branch": "main",
        "private": False,
        "language": "Python",
        "fork": False,
        "stargazers_count": 42,
        "forks_count": 5,
        "pushed_at": "2026-08-25T12:00:00Z",
    },
    {
        "id": 102,
        "name": "forked-library",
        "full_name": "octocat/forked-library",
        "html_url": "https://github.com/octocat/forked-library",
        "description": "A fork of an open-source library",
        "default_branch": "master",
        "private": False,
        "language": "JavaScript",
        "fork": True,  # Fork that MUST be filtered out
        "stargazers_count": 0,
        "forks_count": 0,
        "pushed_at": "2026-08-01T10:00:00Z",
    },
    {
        "id": 103,
        "name": "frontend-app",
        "full_name": "octocat/frontend-app",
        "html_url": "https://github.com/octocat/frontend-app",
        "description": "React Next.js dashboard",
        "default_branch": "main",
        "private": False,
        "language": "TypeScript",
        "fork": False,
        "stargazers_count": 19,
        "forks_count": 2,
        "pushed_at": "2026-08-28T15:30:00Z",
    },
]


def test_validate_github_username_ssrf_protection():
    """Verify GitHub username regex validation rejects path traversal and SSRF attacks."""
    assert validate_github_username("octocat") == "octocat"
    assert validate_github_username("jane-doe-123") == "jane-doe-123"

    import pytest
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        validate_github_username("user/repo")
    with pytest.raises(HTTPException):
        validate_github_username("../../etc/passwd")
    with pytest.raises(HTTPException):
        validate_github_username("user?query=1")
    with pytest.raises(HTTPException):
        validate_github_username("-invalid-start")


def test_fork_filtering_and_normalization():
    """
    Requirement 7: Fork filtering
    Forked repositories must be excluded; only original repos retained.
    """
    service = GitHubService()
    filtered = service.filter_and_normalize(MOCK_REPOS_PAGE_1)

    assert len(filtered) == 2  # 1 of the 3 was a fork
    names = {r["repo_name"] for r in filtered}
    assert "super-service" in names
    assert "frontend-app" in names
    assert "forked-library" not in names  # fork excluded!

    for r in filtered:
        assert r["is_fork"] is False


def test_connect_github_endpoint_success():
    """
    Requirements 3 & 4:
    - POST /api/v1/github/connect
    - Token never appears in response
    - Discovers repositories, filters forks, and persists
    """
    secret_token = "ghp_secret_token_12345"

    def mock_get_side_effect(url, headers=None, params=None):
        mock_res = MagicMock()
        mock_res.status_code = 200
        if "/users/octocat/repos" in url:
            mock_res.json.return_value = MOCK_REPOS_PAGE_1
        elif "/users/octocat" in url:
            mock_res.json.return_value = MOCK_USER_RESPONSE
        else:
            mock_res.status_code = 404
            mock_res.json.return_value = {}
        return mock_res

    with patch.object(github_service.client, "get", side_effect=mock_get_side_effect):
        payload = {
            "github_username": "octocat",
            "access_token": secret_token,
        }
        response = client.post("/api/v1/github/connect", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert data["data"]["github_username"] == "octocat"
        assert data["data"]["connected"] is True
        assert data["data"]["discovered_repositories"] == 2  # 2 non-forks

        # Requirement 4: Token security - verify secret token is NEVER in response
        raw_response_text = response.text
        assert secret_token not in raw_response_text
        assert "ghp_" not in raw_response_text

        # Verify database persistence
        db = SessionLocal()
        try:
            repos = db.query(GitHubRepository).all()
            assert len(repos) >= 2
            repo_names = {r.repo_name for r in repos}
            assert "super-service" in repo_names
            assert "frontend-app" in repo_names
            assert "forked-library" not in repo_names
        finally:
            db.query(GitHubRepository).delete()
            db.commit()
            db.close()


def test_idempotent_repository_sync():
    """
    Requirement 11: Idempotency
    Repeated sync of the same user repositories updates records in-place
    and preserves stable local repository IDs without duplicating rows.
    """
    def mock_get_initial(url, headers=None, params=None):
        mock_res = MagicMock()
        mock_res.status_code = 200
        if "/users/octocat/repos" in url:
            mock_res.json.return_value = MOCK_REPOS_PAGE_1
        elif "/users/octocat" in url:
            mock_res.json.return_value = MOCK_USER_RESPONSE
        return mock_res

    with patch.object(github_service.client, "get", side_effect=mock_get_initial):
        # 1. First sync
        res1 = client.post("/api/v1/github/connect", json={"github_username": "octocat"})
        assert res1.status_code == 200

    db = SessionLocal()
    first_sync_repos = db.query(GitHubRepository).all()
    first_ids = {r.repo_name: r.id for r in first_sync_repos}
    assert len(first_sync_repos) == 2
    db.close()

    # 2. Second sync with updated stars
    updated_mock_repos = [
        dict(r, stargazers_count=999) if r["name"] == "super-service" else r
        for r in MOCK_REPOS_PAGE_1
    ]
    def mock_get_updated(url, headers=None, params=None):
        mock_res = MagicMock()
        mock_res.status_code = 200
        if "/users/octocat/repos" in url:
            mock_res.json.return_value = updated_mock_repos
        elif "/users/octocat" in url:
            mock_res.json.return_value = MOCK_USER_RESPONSE
        return mock_res

    with patch.object(github_service.client, "get", side_effect=mock_get_updated):
        res2 = client.post("/api/v1/github/connect", json={"github_username": "octocat"})
        assert res2.status_code == 200

    db2 = SessionLocal()
    try:
        second_sync_repos = db2.query(GitHubRepository).all()
        assert len(second_sync_repos) == 2  # No duplicate rows created!

        # Stable local IDs preserved and metadata updated
        for r in second_sync_repos:
            assert r.id == first_ids[r.repo_name]
            if r.repo_name == "super-service":
                assert r.stars_count == 999  # updated in-place!
    finally:
        db2.query(GitHubRepository).delete()
        db2.commit()
        db2.close()


def test_list_and_get_repositories_api():
    """
    Requirements 12 & 13:
    - GET /api/v1/github/repositories (paginated, deterministic ordering)
    - GET /api/v1/github/repositories/{id} (detailed local metadata)
    - 404 for missing repository
    """
    def mock_get_side_effect(url, headers=None, params=None):
        mock_res = MagicMock()
        mock_res.status_code = 200
        if "/users/octocat/repos" in url:
            mock_res.json.return_value = MOCK_REPOS_PAGE_1
        elif "/users/octocat" in url:
            mock_res.json.return_value = MOCK_USER_RESPONSE
        return mock_res

    with patch.object(github_service.client, "get", side_effect=mock_get_side_effect):
        connect_res = client.post("/api/v1/github/connect", json={"github_username": "octocat"})
        assert connect_res.status_code == 200

    try:
        # 1. GET /api/v1/github/repositories
        res = client.get("/api/v1/github/repositories?limit=10&offset=0")
        assert res.status_code == 200
        list_body = res.json()

        assert "data" in list_body
        assert "meta" in list_body
        assert list_body["meta"]["total"] == 2
        assert len(list_body["data"]) == 2

        repo_item = list_body["data"][0]
        repo_id = repo_item["repo_id"]
        assert repo_item["repo_name"] in ("frontend-app", "super-service")
        assert repo_item["is_fork"] is False

        # 2. GET /api/v1/github/repositories/{repo_id}
        detail_res = client.get(f"/api/v1/github/repositories/{repo_id}")
        assert detail_res.status_code == 200
        detail_body = detail_res.json()

        assert "data" in detail_body
        detail_data = detail_body["data"]
        assert detail_data["repo_id"] == repo_id
        assert "repo_metadata" in detail_data
        assert detail_data["is_fork"] is False

        # 3. Missing repository returns 404
        random_id = str(uuid.uuid4())
        res_404 = client.get(f"/api/v1/github/repositories/{random_id}")
        assert res_404.status_code == 404
        assert res_404.json()["error"]["code"] == "NOT_FOUND"
    finally:
        db = SessionLocal()
        db.query(GitHubRepository).delete()
        db.commit()
        db.close()


def test_github_error_mappings():
    """
    Requirements 15 & 16:
    GitHub API error statuses (401, 403/429, 404, network failure) mapped to clean envelopes.
    """
    # 1. User not found (404)
    mock_res_404 = MagicMock()
    mock_res_404.status_code = 404
    with patch.object(github_service.client, "get", return_value=mock_res_404):
        r_404 = client.post("/api/v1/github/connect", json={"github_username": "nonexistent-user-9999"})
        assert r_404.status_code == 404
        assert r_404.json()["error"]["code"] == "NOT_FOUND"

    # 2. Bad credentials (401)
    mock_res_401 = MagicMock()
    mock_res_401.status_code = 401
    with patch.object(github_service.client, "get", return_value=mock_res_401):
        r_401 = client.post("/api/v1/github/connect", json={"github_username": "octocat", "access_token": "bad_token"})
        assert r_401.status_code == 401
        assert r_401.json()["error"]["code"] == "UNAUTHENTICATED"

    # 3. Rate limiting (429 / 403)
    mock_res_429 = MagicMock()
    mock_res_429.status_code = 429
    with patch.object(github_service.client, "get", return_value=mock_res_429):
        r_429 = client.post("/api/v1/github/connect", json={"github_username": "octocat"})
        assert r_429.status_code == 429

    # 4. Network error
    with patch.object(github_service.client, "get", side_effect=httpx.RequestError("DNS resolution failed")):
        r_502 = client.post("/api/v1/github/connect", json={"github_username": "octocat"})
        assert r_502.status_code == 502
        assert "reach github" in r_502.json()["error"]["message"].lower()
