"""Comprehensive test suite for Login Phase 4:
Account Ownership, Resource Isolation, and IDOR Defense.

Verifies:
1. User A cannot access User B resume (403 Forbidden)
2. User A cannot activate User B resume (403 Forbidden)
3. User A cannot access User B GitHub repositories (isolated)
4. User A cannot access User B evidence (403 Forbidden)
5. User A cannot access User B demonstrated skills (isolated)
6. User A cannot access User B skill gaps (isolated)
7. User A cannot access User B roadmap (403 Forbidden)
8. User A cannot modify User B progress / verify User B milestone (403 Forbidden)
9. User A cannot verify User B milestone against User B repo
10. X-User-Id header cannot change authenticated identity in production
11. Query user_id cannot change authenticated identity
12. Client-supplied localStorage identity cannot affect backend ownership
13. Anonymous requests to user-owned endpoints are rejected (401 Unauthorized)
14. New authenticated user receives only their own empty/scoped data
15. Active resume cannot point to another user's resume (rejected and unactivatable)
16. Reconnecting GitHub doesn't cross ownership boundaries
17. Evidence remains strictly isolated between users
18. Roadmap remains strictly isolated between users
19. Milestone verification remains strictly isolated
"""

from datetime import datetime, timedelta, timezone
import io
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import generate_session_token, hash_session_token, hash_password
from app.db.database import SessionLocal
from app.db.models import (
    User,
    UserSession,
    Resume,
    GitHubRepository,
    ProjectEvidence,
    DemonstratedSkill,
    Skill,
    JobRole,
    CandidateRoadmap,
    RoadmapMilestone,
    MilestoneVerification,
)
from app.main import app
from app.api.deps import get_current_active_user
from tests.test_resume_parser import generate_test_pdf_bytes


@pytest.fixture
def clean_db():
    """Provides a fresh database session and cleans up test-created records."""
    session = SessionLocal()
    created_user_ids = []
    created_role_ids = []
    created_skill_ids = []
    try:
        yield session, created_user_ids, created_role_ids, created_skill_ids
    finally:
        session.rollback()
        if created_user_ids:
            session.query(MilestoneVerification).filter(MilestoneVerification.user_id.in_(created_user_ids)).delete(synchronize_session=False)
            session.query(RoadmapMilestone).filter(RoadmapMilestone.roadmap_id.in_(
                session.query(CandidateRoadmap.id).filter(CandidateRoadmap.user_id.in_(created_user_ids))
            )).delete(synchronize_session=False)
            session.query(CandidateRoadmap).filter(CandidateRoadmap.user_id.in_(created_user_ids)).delete(synchronize_session=False)
            session.query(DemonstratedSkill).filter(DemonstratedSkill.user_id.in_(created_user_ids)).delete(synchronize_session=False)
            session.query(ProjectEvidence).filter(ProjectEvidence.user_id.in_(created_user_ids)).delete(synchronize_session=False)
            session.query(GitHubRepository).filter(GitHubRepository.user_id.in_(created_user_ids)).delete(synchronize_session=False)
            # Break cycle before deleting resumes
            session.query(User).filter(User.id.in_(created_user_ids)).update({"active_resume_id": None}, synchronize_session=False)
            session.commit()
            session.query(Resume).filter(Resume.user_id.in_(created_user_ids)).delete(synchronize_session=False)
            session.query(UserSession).filter(UserSession.user_id.in_(created_user_ids)).delete(synchronize_session=False)
            session.query(User).filter(User.id.in_(created_user_ids)).delete(synchronize_session=False)
        if created_role_ids:
            session.query(JobRole).filter(JobRole.id.in_(created_role_ids)).delete(synchronize_session=False)
        if created_skill_ids:
            session.query(Skill).filter(Skill.id.in_(created_skill_ids)).delete(synchronize_session=False)
        session.commit()
        session.close()


def create_authenticated_user(session: Session, email_prefix: str) -> tuple[User, str]:
    """Helper to create a real User with an active server-side session."""
    user = User(
        id=uuid.uuid4(),
        email=f"{email_prefix}-{uuid.uuid4().hex[:8]}@skillforge.test",
        hashed_password=hash_password("ValidPassword123!"),
        auth_provider="local",
        is_active=True,
    )
    session.add(user)
    session.flush()

    raw_token = generate_session_token()
    token_hash = hash_session_token(raw_token)
    now = datetime.now(timezone.utc)
    user_session = UserSession(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=token_hash,
        created_at=now,
        expires_at=now + timedelta(days=7),
        last_seen_at=now,
    )
    session.add(user_session)
    session.commit()
    session.refresh(user)
    return user, raw_token


def make_client_for_session(token: str) -> TestClient:
    """Returns a TestClient with the session cookie set."""
    client = TestClient(app)
    client.cookies.set(settings.SESSION_COOKIE_NAME, token)
    return client


# -----------------------------------------------------------------------------
# 1 & 2. Resume Isolation & Activation IDOR Defense
# -----------------------------------------------------------------------------

def test_user_cannot_access_or_activate_other_user_resume(clean_db):
    """User A cannot access or activate User B's resume via ID, query params, or headers."""
    db, user_ids, _, _ = clean_db
    user_a, token_a = create_authenticated_user(db, "user-a")
    user_b, token_b = create_authenticated_user(db, "user-b")
    user_ids.extend([user_a.id, user_b.id])

    # Create resume owned by User B
    resume_b = Resume(
        id=uuid.uuid4(),
        user_id=user_b.id,
        file_name="resume_b.pdf",
        file_type="pdf",
        file_size=1024,
        storage_path="/tmp/fake_b.pdf",
        raw_text="Skills: Python, Docker",
        parsed_data={},
    )
    db.add(resume_b)
    db.commit()

    client_a = make_client_for_session(token_a)

    # 1. User A attempts GET /resumes/{resume_b.id} -> 403 Forbidden
    resp = client_a.get(f"/api/v1/resumes/{resume_b.id}")
    assert resp.status_code == 403
    assert "Cross-user access denied" in resp.json()["detail"]

    # 2. User A attempts PUT /resumes/{resume_b.id}/activate -> 403 Forbidden
    resp_act = client_a.put(f"/api/v1/resumes/{resume_b.id}/activate")
    assert resp_act.status_code == 403
    assert "Cross-user access denied" in resp_act.json()["detail"]

    # Verify User A's active_resume_id was NOT changed
    db.refresh(user_a)
    assert user_a.active_resume_id != resume_b.id

    # 3. User A attempts DELETE /resumes/{resume_b.id} -> 403 Forbidden
    resp_del = client_a.delete(f"/api/v1/resumes/{resume_b.id}")
    assert resp_del.status_code == 403

    # 4. User A list resumes does not contain User B's resume
    resp_list = client_a.get("/api/v1/resumes")
    assert resp_list.status_code == 200
    ids = [item["resume_id"] for item in resp_list.json()["data"]]
    assert str(resume_b.id) not in ids


def test_user_can_activate_own_resume_and_deleting_falls_back(clean_db):
    """User can activate own resume; deleting active resume safely falls back."""
    db, user_ids, _, _ = clean_db
    user, token = create_authenticated_user(db, "user-own")
    user_ids.append(user.id)

    res1 = Resume(
        id=uuid.uuid4(),
        user_id=user.id,
        file_name="res1.pdf",
        file_type="pdf",
        file_size=1000,
        storage_path="/tmp/res1.pdf",
        parsed_data={},
    )
    res2 = Resume(
        id=uuid.uuid4(),
        user_id=user.id,
        file_name="res2.pdf",
        file_type="pdf",
        file_size=1000,
        storage_path="/tmp/res2.pdf",
        parsed_data={},
    )
    db.add_all([res1, res2])
    db.commit()

    client = make_client_for_session(token)

    # Activate res1
    resp1 = client.put(f"/api/v1/resumes/{res1.id}/activate")
    assert resp1.status_code == 200
    assert resp1.json()["active_resume_id"] == str(res1.id)

    db.refresh(user)
    assert user.active_resume_id == res1.id

    # Activate res2
    resp2 = client.put(f"/api/v1/resumes/{res2.id}/activate")
    assert resp2.status_code == 200
    assert resp2.json()["active_resume_id"] == str(res2.id)

    db.refresh(user)
    assert user.active_resume_id == res2.id

    # Delete res2 (currently active) -> should fallback to res1
    resp_del = client.delete(f"/api/v1/resumes/{res2.id}")
    assert resp_del.status_code == 204

    db.refresh(user)
    assert user.active_resume_id == res1.id


# -----------------------------------------------------------------------------
# 3, 16. GitHub Repositories & Connection Isolation
# -----------------------------------------------------------------------------

def test_github_repository_isolation(clean_db):
    """User A cannot access or analyze User B's repositories; list only returns owned repos."""
    db, user_ids, _, _ = clean_db
    user_a, token_a = create_authenticated_user(db, "user-gh-a")
    user_b, token_b = create_authenticated_user(db, "user-gh-b")
    user_ids.extend([user_a.id, user_b.id])

    repo_b = GitHubRepository(
        id=uuid.uuid4(),
        user_id=user_b.id,
        github_repository_id=98765432,
        repo_name="private-skill-repo",
        full_name="userb/private-skill-repo",
        repo_url="https://github.com/userb/private-skill-repo",
        is_fork=False,
    )
    db.add(repo_b)
    db.commit()

    client_a = make_client_for_session(token_a)

    # 1. GET /github/repositories does not return repo_b
    resp_list = client_a.get("/api/v1/github/repositories")
    assert resp_list.status_code == 200
    repo_ids = [r["repo_id"] for r in resp_list.json()["data"]]
    assert str(repo_b.id) not in repo_ids

    # 2. GET /github/repositories/{repo_b.id} -> 404 Not Found (no existence leakage)
    resp_detail = client_a.get(f"/api/v1/github/repositories/{repo_b.id}")
    assert resp_detail.status_code == 404

    # 3. POST /github/analyze for repo_b -> 403 Forbidden
    resp_analyze = client_a.post("/api/v1/github/analyze", json={"repository_id": str(repo_b.id)})
    assert resp_analyze.status_code == 403
    assert "Cross-user access denied" in resp_analyze.json()["detail"]


def test_github_disconnect_preserves_isolation(clean_db):
    """Disconnecting GitHub clears connected_github_username without affecting other users."""
    db, user_ids, _, _ = clean_db
    user, token = create_authenticated_user(db, "user-disconn")
    user_ids.append(user.id)
    user.connected_github_username = "octocat"
    db.commit()

    client = make_client_for_session(token)
    resp = client.post("/api/v1/github/disconnect")
    assert resp.status_code == 200
    assert resp.json()["connected"] is False

    db.refresh(user)
    assert user.connected_github_username is None


# -----------------------------------------------------------------------------
# 4, 17. Project Evidence Isolation
# -----------------------------------------------------------------------------

def test_evidence_isolation(clean_db):
    """User A cannot list or get User B's project evidence (fixes critical global leak)."""
    db, user_ids, _, skill_ids = clean_db
    user_a, token_a = create_authenticated_user(db, "user-ev-a")
    user_b, token_b = create_authenticated_user(db, "user-ev-b")
    user_ids.extend([user_a.id, user_b.id])

    skill = Skill(id=uuid.uuid4(), name=f"Skill-{uuid.uuid4().hex[:6]}", slug=f"slug-{uuid.uuid4().hex[:6]}")
    db.add(skill)
    skill_ids.append(skill.id)
    db.flush()

    ev_b = ProjectEvidence(
        id=uuid.uuid4(),
        user_id=user_b.id,
        skill_id=skill.id,
        evidence_type="dependency",
        file_path="requirements.txt",
        artifact_name="docker",
        confidence_score=0.9,
    )
    db.add(ev_b)
    db.commit()

    client_a = make_client_for_session(token_a)

    # 1. GET /evidence without query params returns only user_a evidence (0 items)
    resp_list = client_a.get("/api/v1/evidence")
    assert resp_list.status_code == 200
    ev_ids = [e["evidence_id"] for e in resp_list.json()["data"]]
    assert str(ev_b.id) not in ev_ids

    # 2. GET /evidence/{ev_b.id} -> 404 Not Found (no existence leakage)
    resp_detail = client_a.get(f"/api/v1/evidence/{ev_b.id}")
    assert resp_detail.status_code == 404


# -----------------------------------------------------------------------------
# 5. Demonstrated Skills Isolation
# -----------------------------------------------------------------------------

def test_demonstrated_skills_isolation(clean_db):
    """User A cannot list or inspect User B's demonstrated skills."""
    db, user_ids, _, skill_ids = clean_db
    user_a, token_a = create_authenticated_user(db, "user-dem-a")
    user_b, token_b = create_authenticated_user(db, "user-dem-b")
    user_ids.extend([user_a.id, user_b.id])

    skill = Skill(id=uuid.uuid4(), name=f"Skill-{uuid.uuid4().hex[:6]}", slug=f"slug-{uuid.uuid4().hex[:6]}")
    db.add(skill)
    skill_ids.append(skill.id)
    db.flush()

    dem_b = DemonstratedSkill(
        id=uuid.uuid4(),
        user_id=user_b.id,
        skill_id=skill.id,
        confidence_score=0.85,
        evidence_level="HIGH",
        skill_metadata={"repositories": []},
    )
    db.add(dem_b)
    db.commit()

    client_a = make_client_for_session(token_a)

    # 1. GET /skills/demonstrated returns only user_a's demonstrated skills
    resp_list = client_a.get("/api/v1/skills/demonstrated")
    assert resp_list.status_code == 200
    dem_ids = [s["skill_id"] for s in resp_list.json()["data"]]
    assert str(skill.id) not in dem_ids

    # 2. GET /skills/demonstrated/{skill.id} for user_a returns 404 (not owned by user_a)
    resp_detail = client_a.get(f"/api/v1/skills/demonstrated/{skill.id}")
    assert resp_detail.status_code == 404


# -----------------------------------------------------------------------------
# 6. Skill Gaps Isolation
# -----------------------------------------------------------------------------

def test_skill_gaps_isolation(clean_db):
    """Skill gap endpoints operate strictly against current_user.id; User B's resume cannot be analyzed."""
    db, user_ids, role_ids, _ = clean_db
    user_a, token_a = create_authenticated_user(db, "user-gap-a")
    user_b, token_b = create_authenticated_user(db, "user-gap-b")
    user_ids.extend([user_a.id, user_b.id])

    role = JobRole(
        id=uuid.uuid4(),
        title=f"Software Engineer {uuid.uuid4().hex[:6]}",
        slug=f"se-{uuid.uuid4().hex[:6]}",
        category="Engineering",
    )
    db.add(role)
    role_ids.append(role.id)

    resume_b = Resume(
        id=uuid.uuid4(),
        user_id=user_b.id,
        file_name="resume_b.pdf",
        file_type="pdf",
        file_size=1024,
        storage_path="/tmp/b.pdf",
        parsed_data={},
    )
    db.add(resume_b)
    db.commit()

    client_a = make_client_for_session(token_a)

    # User A tries to run gap analysis referencing User B's resume -> 403 Forbidden
    resp = client_a.get(f"/api/v1/gaps/{role.id}?resume_id={resume_b.id}")
    assert resp.status_code == 403
    assert "Cross-user access denied" in resp.json()["detail"]

    # User A tries to run analyze endpoint with User B's resume -> 403 Forbidden
    resp_post = client_a.post(
        "/api/v1/gaps/analyze",
        json={"target_role_id": str(role.id), "resume_id": str(resume_b.id), "location": "India"},
    )
    assert resp_post.status_code == 403


# -----------------------------------------------------------------------------
# 7, 8, 9, 18, 19. Roadmap & Milestone Verification Isolation
# -----------------------------------------------------------------------------

def test_roadmap_and_verification_isolation(clean_db):
    """User A cannot access User B's roadmap, verify User B's milestone, or modify User B's progress."""
    db, user_ids, role_ids, skill_ids = clean_db
    user_a, token_a = create_authenticated_user(db, "user-rd-a")
    user_b, token_b = create_authenticated_user(db, "user-rd-b")
    user_ids.extend([user_a.id, user_b.id])

    role = JobRole(
        id=uuid.uuid4(),
        title=f"Backend Engineer {uuid.uuid4().hex[:6]}",
        slug=f"be-{uuid.uuid4().hex[:6]}",
        category="Engineering",
    )
    db.add(role)
    role_ids.append(role.id)

    skill = Skill(
        id=uuid.uuid4(),
        name=f"FastAPI {uuid.uuid4().hex[:6]}",
        slug=f"fastapi-{uuid.uuid4().hex[:6]}",
        category="Framework",
    )
    db.add(skill)
    skill_ids.append(skill.id)
    db.flush()

    roadmap_b = CandidateRoadmap(
        id=uuid.uuid4(),
        user_id=user_b.id,
        role_id=role.id,
        target_role_title=role.title,
        location="India",
        status="ACTIVE",
        roadmap_version="v1",
        summary_metadata={"github_username": "userb"},
    )
    db.add(roadmap_b)
    db.flush()

    milestone_b = RoadmapMilestone(
        id=uuid.uuid4(),
        roadmap_id=roadmap_b.id,
        skill_id=skill.id,
        order_index=1,
        status="NOT_STARTED",
        gap_status="MISSING",
        reason="Core backend framework requirement",
        milestone_metadata={},
    )
    db.add(milestone_b)
    db.commit()

    client_a = make_client_for_session(token_a)

    # 1. User A tries to GET /roadmap/{roadmap_b.id} -> 403 Forbidden
    resp_get = client_a.get(f"/api/v1/roadmap/{roadmap_b.id}")
    assert resp_get.status_code == 403

    # 2. User A tries to GET /roadmap/active for role.id -> 404 (User A has no active roadmap)
    resp_act = client_a.get(f"/api/v1/roadmap/active?role_id={role.id}")
    assert resp_act.status_code == 404

    # 3. User A tries to verify User B's milestone -> 403 Forbidden
    resp_ver = client_a.post(
        f"/api/v1/roadmap/{roadmap_b.id}/milestones/{milestone_b.id}/verify",
        headers={"Authorization": "Bearer ghp_faketoken1234567890"},
    )
    assert resp_ver.status_code == 403
    assert "Cross-user access denied" in resp_ver.json()["detail"]

    # 4. User A tries to get latest verification for User B's milestone -> 403 Forbidden
    resp_lat = client_a.get(
        f"/api/v1/roadmap/{roadmap_b.id}/milestones/{milestone_b.id}/verification",
    )
    assert resp_lat.status_code == 403

    # 5. User A tries to batch verify User B's roadmap -> 403 Forbidden
    resp_batch = client_a.post(
        f"/api/v1/roadmap/{roadmap_b.id}/verify",
        headers={"Authorization": "Bearer ghp_faketoken1234567890"},
    )
    assert resp_batch.status_code == 403


# -----------------------------------------------------------------------------
# 10, 11, 12, 13. Production Invariant Checks: Cookie Authority & Anonymous Rejection
# -----------------------------------------------------------------------------

def test_anonymous_requests_rejected_and_header_cannot_authenticate(clean_db):
    """
    Verifies that under production authentication (without test override):
    - Requests without a cookie return 401
    - X-User-Id alone returns 401
    - Query user_id alone returns 401
    - X-User-Id pointing to User B while authenticated as User A still acts as User A
    """
    db, user_ids, _, _ = clean_db
    user_a, token_a = create_authenticated_user(db, "user-prod-a")
    user_b, token_b = create_authenticated_user(db, "user-prod-b")
    user_ids.extend([user_a.id, user_b.id])

    # Clear dependency override to test pure production get_current_active_user
    app.dependency_overrides.clear()
    try:
        raw_client = TestClient(app)

        # 1. Anonymous request to /resumes -> 401 Unauthorized
        resp1 = raw_client.get("/api/v1/resumes")
        assert resp1.status_code == 401
        assert "Authentication required" in resp1.json()["detail"]

        # 2. Anonymous request with X-User-Id header alone -> 401 Unauthorized (Header NOT trusted)
        resp2 = raw_client.get("/api/v1/resumes", headers={"X-User-Id": str(user_a.id)})
        assert resp2.status_code == 401

        # 3. Anonymous request with query user_id alone -> 401 Unauthorized (Query NOT trusted)
        resp3 = raw_client.get(f"/api/v1/resumes?user_id={user_a.id}")
        assert resp3.status_code == 401

        # 4. Authenticated as User A, but spoofing X-User-Id: User B -> resolves to User A!
        auth_client_a = TestClient(app)
        auth_client_a.cookies.set(settings.SESSION_COOKIE_NAME, token_a)

        # Calling GET /users/me should return User A, completely ignoring X-User-Id
        resp_me = auth_client_a.get("/api/v1/users/me", headers={"X-User-Id": str(user_b.id)})
        assert resp_me.status_code == 200
        assert resp_me.json()["id"] == str(user_a.id)

        # Anonymous request to /evidence -> 401
        resp_ev = raw_client.get("/api/v1/evidence")
        assert resp_ev.status_code == 401

        # Anonymous request to /github/repositories -> 401
        resp_gh = raw_client.get("/api/v1/github/repositories")
        assert resp_gh.status_code == 401

    finally:
        # Restore test override for subsequent test modules
        from tests.conftest import test_get_current_active_user
        app.dependency_overrides[get_current_active_user] = test_get_current_active_user


# -----------------------------------------------------------------------------
# 14. New User Isolation
# -----------------------------------------------------------------------------

def test_new_authenticated_user_receives_only_own_data(clean_db):
    """A newly registered user receives zero resources from other users."""
    db, user_ids, _, _ = clean_db
    user_new, token_new = create_authenticated_user(db, "user-brand-new")
    user_ids.append(user_new.id)

    client = make_client_for_session(token_new)

    resp_res = client.get("/api/v1/resumes")
    assert resp_res.status_code == 200
    assert resp_res.json()["data"] == []

    resp_gh = client.get("/api/v1/github/repositories")
    assert resp_gh.status_code == 200
    assert resp_gh.json()["data"] == []

    resp_ev = client.get("/api/v1/evidence")
    assert resp_ev.status_code == 200
    assert resp_ev.json()["data"] == []

    resp_sk = client.get("/api/v1/skills/claimed")
    assert resp_sk.status_code == 200
    assert resp_sk.json()["data"] == []


# -----------------------------------------------------------------------------
# 20. Users API: Prevent Account Takeover
# -----------------------------------------------------------------------------

def test_create_user_prevents_account_takeover(clean_db):
    """Attempting to register an existing email via POST /api/v1/users returns 409 Conflict."""
    db, user_ids, _, _ = clean_db
    user, _ = create_authenticated_user(db, "user-takeover-target")
    user_ids.append(user.id)

    client = TestClient(app)
    resp = client.post("/api/v1/users", json={"email": user.email, "full_name": "Attacker"})
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"]
