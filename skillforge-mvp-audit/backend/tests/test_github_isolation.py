import uuid
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.database import SessionLocal
from app.db.models import GitHubRepository, ProjectEvidence, DemonstratedSkill, Skill
from app.services.github_service import github_service
from app.services.demonstrated_skill_service import demonstrated_skill_service

client = TestClient(app)

MOCK_ALICE_REPOS = [
    {
        "id": 1001,
        "name": "alice-api",
        "full_name": "alice/alice-api",
        "html_url": "https://github.com/alice/alice-api",
        "owner": {"login": "alice"},
        "description": "Alice API service",
        "default_branch": "main",
        "private": False,
        "language": "Python",
        "fork": False,
        "stargazers_count": 10,
        "forks_count": 1,
        "pushed_at": "2026-08-30T10:00:00Z",
    },
    {
        "id": 1002,
        "name": "alice-web",
        "full_name": "alice/alice-web",
        "html_url": "https://github.com/alice/alice-web",
        "owner": {"login": "alice"},
        "description": "Alice Web UI",
        "default_branch": "main",
        "private": False,
        "language": "TypeScript",
        "fork": False,
        "stargazers_count": 5,
        "forks_count": 0,
        "pushed_at": "2026-08-29T10:00:00Z",
    },
]

MOCK_BOB_REPOS = [
    {
        "id": 2001,
        "name": "bob-engine",
        "full_name": "bob/bob-engine",
        "html_url": "https://github.com/bob/bob-engine",
        "owner": {"login": "bob"},
        "description": "Bob ML Engine",
        "default_branch": "main",
        "private": False,
        "language": "Python",
        "fork": False,
        "stargazers_count": 25,
        "forks_count": 3,
        "pushed_at": "2026-08-31T10:00:00Z",
    },
    {
        "id": 2002,
        "name": "bob-infra",
        "full_name": "bob/bob-infra",
        "html_url": "https://github.com/bob/bob-infra",
        "owner": {"login": "bob"},
        "description": "Bob Infrastructure",
        "default_branch": "main",
        "private": False,
        "language": "HCL",
        "fork": False,
        "stargazers_count": 8,
        "forks_count": 2,
        "pushed_at": "2026-08-28T10:00:00Z",
    },
]


@pytest.fixture(autouse=True)
def cleanup_test_data():
    """Ensure clean database before and after each test."""
    db = SessionLocal()
    try:
        db.query(ProjectEvidence).delete()
        db.query(DemonstratedSkill).delete()
        db.query(GitHubRepository).delete()
        db.commit()
    finally:
        db.close()
    yield
    db = SessionLocal()
    try:
        db.query(ProjectEvidence).delete()
        db.query(DemonstratedSkill).delete()
        db.query(GitHubRepository).delete()
        db.commit()
    finally:
        db.close()


def test_account_repository_isolation():
    """
    Requirements A, B & C:
    When Account A and Account B are both connected:
    - Querying Account A returns ONLY Account A repositories.
    - Querying Account B returns ONLY Account B repositories.
    - Account A repositories never leak to Account B.
    - Account B repositories never leak to Account A.
    """
    def mock_get(url, headers=None, params=None):
        mock_res = MagicMock()
        mock_res.status_code = 200
        if "/users/alice/repos" in url:
            mock_res.json.return_value = MOCK_ALICE_REPOS
        elif "/users/alice" in url:
            mock_res.json.return_value = {"login": "alice", "id": 1, "name": "Alice"}
        elif "/users/bob/repos" in url:
            mock_res.json.return_value = MOCK_BOB_REPOS
        elif "/users/bob" in url:
            mock_res.json.return_value = {"login": "bob", "id": 2, "name": "Bob"}
        return mock_res

    with patch.object(github_service.client, "get", side_effect=mock_get):
        res_a = client.post("/api/v1/github/connect", json={"github_username": "alice"})
        assert res_a.status_code == 200
        assert res_a.json()["data"]["discovered_repositories"] == 2
        # Verify connect response carries only Alice's repos
        connect_repos_a = res_a.json()["data"]["repositories"]
        assert len(connect_repos_a) == 2
        for r in connect_repos_a:
            assert r["full_name"].startswith("alice/")

        res_b = client.post("/api/v1/github/connect", json={"github_username": "bob"})
        assert res_b.status_code == 200
        assert res_b.json()["data"]["discovered_repositories"] == 2
        connect_repos_b = res_b.json()["data"]["repositories"]
        assert len(connect_repos_b) == 2
        for r in connect_repos_b:
            assert r["full_name"].startswith("bob/")

    # 1. Query for Alice
    res_list_a = client.get("/api/v1/github/repositories?username=alice")
    assert res_list_a.status_code == 200
    data_a = res_list_a.json()["data"]
    assert len(data_a) == 2
    for r in data_a:
        assert r["full_name"].startswith("alice/")
        assert not r["full_name"].startswith("bob/")

    # 2. Query for Bob
    res_list_b = client.get("/api/v1/github/repositories?username=bob")
    assert res_list_b.status_code == 200
    data_b = res_list_b.json()["data"]
    assert len(data_b) == 2
    for r in data_b:
        assert r["full_name"].startswith("bob/")
        assert not r["full_name"].startswith("alice/")


def test_repository_owner_and_fork_filtering():
    """
    Requirements C & E:
    Owner verification strictly excludes repos where owner != requested username.
    Fork exclusion strictly excludes forked repos.
    """
    mixed_repos = [
        {
            "id": 3001,
            "name": "carol-app",
            "full_name": "carol/carol-app",
            "html_url": "https://github.com/carol/carol-app",
            "owner": {"login": "carol"},
            "description": "Carol's legitimate app",
            "language": "Python",
            "fork": False,
        },
        {
            "id": 3002,
            "name": "other-repo",
            "full_name": "someone-else/other-repo",
            "html_url": "https://github.com/someone-else/other-repo",
            "owner": {"login": "someone-else"},
            "description": "Third party repo returned by API",
            "language": "Python",
            "fork": False,
        },
        {
            "id": 3003,
            "name": "carol-fork",
            "full_name": "carol/carol-fork",
            "html_url": "https://github.com/carol/carol-fork",
            "owner": {"login": "carol"},
            "description": "A fork",
            "language": "Python",
            "fork": True,
        },
    ]

    clean = github_service.filter_and_normalize(mixed_repos, expected_username="carol")
    assert len(clean) == 1
    assert clean[0]["repo_name"] == "carol-app"
    assert clean[0]["full_name"] == "carol/carol-app"
    assert clean[0]["is_fork"] is False


def test_reconnecting_same_account_idempotent():
    """
    Requirement D:
    Connecting the same account multiple times does not duplicate records in DB.
    """
    def mock_get(url, headers=None, params=None):
        mock_res = MagicMock()
        mock_res.status_code = 200
        if "/users/alice/repos" in url:
            mock_res.json.return_value = MOCK_ALICE_REPOS
        elif "/users/alice" in url:
            mock_res.json.return_value = {"login": "alice", "id": 1, "name": "Alice"}
        return mock_res

    with patch.object(github_service.client, "get", side_effect=mock_get):
        res1 = client.post("/api/v1/github/connect", json={"github_username": "alice"})
        assert res1.status_code == 200
        res2 = client.post("/api/v1/github/connect", json={"github_username": "alice"})
        assert res2.status_code == 200

    list_res = client.get("/api/v1/github/repositories?username=alice")
    assert list_res.status_code == 200
    assert list_res.json()["meta"]["total"] == 2
    assert len(list_res.json()["data"]) == 2


def test_pagination_with_username_filter():
    """
    Requirement F:
    Pagination (limit and offset) behaves deterministically with username scoping.
    """
    def mock_get(url, headers=None, params=None):
        mock_res = MagicMock()
        mock_res.status_code = 200
        if "/users/alice/repos" in url:
            mock_res.json.return_value = MOCK_ALICE_REPOS
        elif "/users/alice" in url:
            mock_res.json.return_value = {"login": "alice", "id": 1, "name": "Alice"}
        return mock_res

    with patch.object(github_service.client, "get", side_effect=mock_get):
        client.post("/api/v1/github/connect", json={"github_username": "alice"})

    page1 = client.get("/api/v1/github/repositories?username=alice&limit=1&offset=0").json()
    assert page1["meta"]["total"] == 2
    assert len(page1["data"]) == 1

    page2 = client.get("/api/v1/github/repositories?username=alice&limit=1&offset=1").json()
    assert page2["meta"]["total"] == 2
    assert len(page2["data"]) == 1
    assert page1["data"][0]["repo_id"] != page2["data"][0]["repo_id"]


def test_demonstrated_skills_isolated_between_accounts():
    """
    Requirement G:
    Demonstrated skills and supporting evidence do not leak between accounts.
    """
    db = SessionLocal()
    try:
        # Create canonical skills
        skill_python = db.query(Skill).filter(Skill.name == "Python").first()
        skill_ts = db.query(Skill).filter(Skill.name == "TypeScript").first()

        if not skill_python:
            skill_python = Skill(id=uuid.uuid4(), name="Python", slug="python", category="languages")
            db.add(skill_python)
        if not skill_ts:
            skill_ts = Skill(id=uuid.uuid4(), name="TypeScript", slug="typescript", category="languages")
            db.add(skill_ts)
        db.commit()

        # Create Alice repo and Bob repo
        repo_alice = GitHubRepository(
            id=uuid.uuid4(),
            user_id=None,
            repo_name="alice-api",
            full_name="alice/alice-api",
            repo_url="https://github.com/alice/alice-api",
            is_fork=False,
            stars_count=10,
        )
        repo_bob = GitHubRepository(
            id=uuid.uuid4(),
            user_id=None,
            repo_name="bob-web",
            full_name="bob/bob-web",
            repo_url="https://github.com/bob/bob-web",
            is_fork=False,
            stars_count=5,
        )
        db.add_all([repo_alice, repo_bob])
        db.commit()

        # Alice demonstrated Python
        ev_alice = ProjectEvidence(
            id=uuid.uuid4(),
            user_id=None,
            repo_id=repo_alice.id,
            skill_id=skill_python.id,
            evidence_type="dependency",
            file_path="requirements.txt",
            confidence_score=0.95,
        )
        # Bob demonstrated TypeScript
        ev_bob = ProjectEvidence(
            id=uuid.uuid4(),
            user_id=None,
            repo_id=repo_bob.id,
            skill_id=skill_ts.id,
            evidence_type="dependency",
            file_path="package.json",
            confidence_score=0.95,
        )
        db.add_all([ev_alice, ev_bob])
        db.commit()

        # Recompute demonstrated skills
        demonstrated_skill_service.recompute_demonstrated_skill(db, skill_id=skill_python.id, user_id=None)
        demonstrated_skill_service.recompute_demonstrated_skill(db, skill_id=skill_ts.id, user_id=None)

        # Query demonstrated skills for Alice
        res_alice = client.get("/api/v1/skills/demonstrated?username=alice")
        assert res_alice.status_code == 200
        alice_skills = [s["skill_name"] for s in res_alice.json()["data"]]
        assert "Python" in alice_skills
        assert "TypeScript" not in alice_skills

        # Query demonstrated skills for Bob
        res_bob = client.get("/api/v1/skills/demonstrated?username=bob")
        assert res_bob.status_code == 200
        bob_skills = [s["skill_name"] for s in res_bob.json()["data"]]
        assert "TypeScript" in bob_skills
        assert "Python" not in bob_skills
    finally:
        db.close()
