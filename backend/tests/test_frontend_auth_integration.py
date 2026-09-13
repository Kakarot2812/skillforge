"""Integration tests validating the frontend authentication, session, and resource contract.

Post-MVP Login Phase 5 verification:
- CORS preflight and credential handling (http://localhost:3000)
- Cookie-based session lifecycle (/signup, /login, /me, /logout)
- Safe user profile payload (no password hash, no session tokens)
- Active resume activation via session
- GitHub connection and disconnect via session
- Multi-user isolation across concurrent sessions
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import User, UserSession, Resume
from app.main import app


@pytest.fixture
def db():
    """Provides a database session with automatic cleanup for test-isolated records."""
    session = SessionLocal()
    created_user_ids = []
    try:
        yield session, created_user_ids
    finally:
        if created_user_ids:
            session.query(Resume).filter(Resume.user_id.in_(created_user_ids)).delete(synchronize_session=False)
            session.query(UserSession).filter(UserSession.user_id.in_(created_user_ids)).delete(synchronize_session=False)
            session.query(User).filter(User.id.in_(created_user_ids)).delete(synchronize_session=False)
            session.commit()
        session.close()


@pytest.fixture
def client():
    """Provides a standard FastAPI TestClient."""
    return TestClient(app)


def test_cors_and_credentials_headers_on_auth_endpoints(client: TestClient):
    """Verifies that CORS headers allow credentials from the Next.js frontend."""
    headers = {"Origin": "http://localhost:3000"}
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@example.com", "password": "wrongpassword123"},
        headers=headers,
    )
    # Regardless of auth outcome, CORS headers must be present for credentials
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_frontend_signup_login_restore_logout_flow(client: TestClient, db):
    """End-to-end simulation of the Next.js frontend authentication cycle."""
    session, created_user_ids = db
    signup_email = f"frontend_candidate_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecurePassword123!"

    # 1. Signup Flow (matches LoginForm mode === 'signup')
    signup_res = client.post(
        "/api/v1/auth/signup",
        json={
            "email": signup_email,
            "password": password,
            "full_name": "Frontend Tester",
            "target_role": "Full Stack Engineer",
        },
        headers={"Origin": "http://localhost:3000"},
    )
    assert signup_res.status_code == 201
    user_data = signup_res.json()
    created_user_ids.append(uuid.UUID(user_data["id"]))
    assert user_data["email"] == signup_email
    assert user_data["full_name"] == "Frontend Tester"
    assert user_data["target_role"] == "Full Stack Engineer"
    assert "password" not in user_data
    assert "password_hash" not in user_data

    # Verify session cookie was issued
    session_cookie = signup_res.cookies.get("skillforge_session")
    assert session_cookie is not None

    # 2. Session Restoration (matches CandidateContext on mount via GET /auth/me)
    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Origin": "http://localhost:3000"},
        cookies={"skillforge_session": session_cookie},
    )
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["id"] == user_data["id"]
    assert me_data["email"] == signup_email
    assert me_data["active_resume_id"] is None
    assert me_data["connected_github_username"] is None

    # 3. Unauthenticated access without cookie returns 401
    client.cookies.clear()
    unauth_res = client.get("/api/v1/auth/me", headers={"Origin": "http://localhost:3000"})
    assert unauth_res.status_code == 401

    # 4. Logout Flow (matches Navbar logout action)
    client.cookies.set("skillforge_session", session_cookie)
    logout_res = client.post(
        "/api/v1/auth/logout",
        headers={"Origin": "http://localhost:3000"},
    )
    assert logout_res.status_code == 200
    assert logout_res.json()["message"] == "Logged out successfully"

    # 5. Subsequent /auth/me with revoked session returns 401
    client.cookies.set("skillforge_session", session_cookie)
    revoked_res = client.get(
        "/api/v1/auth/me",
        headers={"Origin": "http://localhost:3000"},
    )
    assert revoked_res.status_code == 401

    # 6. Re-Login Flow (matches LoginForm mode === 'login')
    client.cookies.clear()
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": signup_email, "password": password, "remember_me": True},
        headers={"Origin": "http://localhost:3000"},
    )
    assert login_res.status_code == 200
    new_session_cookie = login_res.cookies.get("skillforge_session")
    assert new_session_cookie is not None
    assert new_session_cookie != session_cookie  # New session token issued
    client.cookies.clear()


def test_frontend_active_resume_and_github_lifecycle(client: TestClient, db):
    """Tests the frontend API client endpoints for active resume and GitHub disconnect."""
    session, created_user_ids = db
    email = f"resource_user_{uuid.uuid4().hex[:8]}@example.com"
    password = "StrongPassword456!"

    # Register candidate
    signup_res = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": password, "full_name": "Resource Tester"},
    )
    assert signup_res.status_code == 201
    user_id = uuid.UUID(signup_res.json()["id"])
    created_user_ids.append(user_id)
    cookie = signup_res.cookies.get("skillforge_session")

    # Create dummy resumes in DB owned by this user
    resume1 = Resume(
        id=uuid.uuid4(),
        user_id=user_id,
        file_name="first_resume.pdf",
        file_type="pdf",
        file_size=2048,
        storage_path="/tmp/first_resume.pdf",
        raw_text="Skills: Python, React, TypeScript",
        parsed_data={},
    )
    resume2 = Resume(
        id=uuid.uuid4(),
        user_id=user_id,
        file_name="second_resume.pdf",
        file_type="pdf",
        file_size=4096,
        storage_path="/tmp/second_resume.pdf",
        raw_text="Skills: Go, Kubernetes, AWS",
        parsed_data={},
    )
    session.add(resume1)
    session.add(resume2)
    session.commit()

    # 1. Activate Resume 2 via PUT /api/v1/resumes/{id}/activate
    client.cookies.set("skillforge_session", cookie)
    act_res = client.put(f"/api/v1/resumes/{resume2.id}/activate")
    assert act_res.status_code == 200
    act_data = act_res.json()
    assert act_data["active_resume_id"] == str(resume2.id)
    assert act_data["filename"] == "second_resume.pdf"

    # Verify GET /auth/me reflects active resume
    me_res = client.get("/api/v1/auth/me")
    assert me_res.status_code == 200
    assert me_res.json()["active_resume_id"] == str(resume2.id)

    # 2. Connect GitHub via user session
    user = session.query(User).filter(User.id == user_id).first()
    user.connected_github_username = "candidate_octocat"
    session.commit()

    me_gh_res = client.get("/api/v1/auth/me")
    assert me_gh_res.json()["connected_github_username"] == "candidate_octocat"

    # 3. Disconnect GitHub via POST /api/v1/github/disconnect
    disc_res = client.post("/api/v1/github/disconnect")
    assert disc_res.status_code == 200
    assert disc_res.json()["connected"] is False

    # Verify GET /auth/me reflects disconnected state
    me_after_disc = client.get("/api/v1/auth/me")
    assert me_after_disc.json()["connected_github_username"] is None
    client.cookies.clear()


def test_multi_user_isolation_between_sessions(client: TestClient, db):
    """Verifies that User A's session cannot access or activate User B's resources."""
    session, created_user_ids = db
    user_a_res = client.post(
        "/api/v1/auth/signup",
        json={"email": f"user_a_{uuid.uuid4().hex[:8]}@example.com", "password": "PasswordA123!"},
    )
    cookie_a = user_a_res.cookies.get("skillforge_session")
    user_a_id = uuid.UUID(user_a_res.json()["id"])
    created_user_ids.append(user_a_id)

    user_b_res = client.post(
        "/api/v1/auth/signup",
        json={"email": f"user_b_{uuid.uuid4().hex[:8]}@example.com", "password": "PasswordB123!"},
    )
    cookie_b = user_b_res.cookies.get("skillforge_session")
    user_b_id = uuid.UUID(user_b_res.json()["id"])
    created_user_ids.append(user_b_id)

    # Create resume belonging to User A
    resume_a = Resume(
        id=uuid.uuid4(),
        user_id=user_a_id,
        file_name="secret_resume_a.pdf",
        file_type="pdf",
        file_size=1024,
        storage_path="/tmp/secret_resume_a.pdf",
        raw_text="Candidate A confidential resume",
        parsed_data={},
    )
    session.add(resume_a)
    session.commit()

    # User B attempts to activate User A's resume -> 403 Forbidden
    client.cookies.set("skillforge_session", cookie_b)
    cross_act_res = client.put(f"/api/v1/resumes/{resume_a.id}/activate")
    assert cross_act_res.status_code == 403

    # User B's /auth/me must not reflect User A's resume
    me_b = client.get("/api/v1/auth/me")
    assert me_b.json()["active_resume_id"] is None
    client.cookies.clear()

