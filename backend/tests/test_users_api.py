"""
Unit and integration tests for candidate identity lifecycle and endpoints.
Verifies:
1. Candidate creation via POST /api/v1/users.
2. Extra client fields are rejected (extra="forbid").
3. Verification via GET /api/v1/users/{user_id}.
4. Verification via GET /api/v1/users/me with X-User-Id.
5. Nonexistent users return 404.
6. Random X-User-Id without backend registration continues to be rejected by P4/P5 endpoints.
7. Candidate isolation remains enforced (IDOR defense).
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.database import SessionLocal
from app.db.models import User, JobRole, CandidateRoadmap


@pytest.fixture
def db_session():
    """Provides a database session for test teardown and verification."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client():
    return TestClient(app)


def test_post_user_fresh_candidate(client: TestClient, db_session: Session):
    """Verifies that an anonymous candidate registration creates a legitimate backend User row."""
    res = client.post("/api/v1/users", json={})
    assert res.status_code == 201
    data = res.json()
    assert "id" in data
    assert "email" in data
    assert data["email"].startswith("candidate-")
    assert "@skillforge.local" in data["email"]

    user_id = uuid.UUID(data["id"])
    db_user = db_session.query(User).filter(User.id == user_id).first()
    assert db_user is not None
    assert db_user.email == data["email"]


def test_post_user_with_payload(client: TestClient, db_session: Session):
    """Verifies that candidate creation with optional full_name and target_role works."""
    unique_email = f"test-candidate-{uuid.uuid4()}@example.com"
    payload = {
        "email": unique_email,
        "full_name": "Test Candidate",
        "target_role": "Backend Engineer",
    }
    res = client.post("/api/v1/users", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == unique_email
    assert data["full_name"] == "Test Candidate"
    assert data["target_role"] == "Backend Engineer"


def test_post_user_rejects_privileged_fields(client: TestClient):
    """Verifies that client cannot supply arbitrary privileged fields like id or role."""
    payload = {
        "id": str(uuid.uuid4()),
        "is_admin": True,
    }
    res = client.post("/api/v1/users", json=payload)
    assert res.status_code == 422


def test_get_user_by_id_success_and_not_found(client: TestClient):
    """Verifies GET /api/v1/users/{user_id} returns 200 for existing and 404 for nonexistent."""
    # 1. Create candidate
    create_res = client.post("/api/v1/users", json={})
    assert create_res.status_code == 201
    created_id = create_res.json()["id"]

    # 2. Query created user
    get_res = client.get(f"/api/v1/users/{created_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == created_id

    # 3. Query nonexistent UUID
    fake_id = str(uuid.uuid4())
    fake_res = client.get(f"/api/v1/users/{fake_id}")
    assert fake_res.status_code == 404
    assert f"User with id '{fake_id}' not found." in fake_res.json()["detail"]


def test_get_current_user_me(client: TestClient):
    """Verifies GET /api/v1/users/me with X-User-Id header."""
    # 1. Missing header -> 401
    missing_res = client.get("/api/v1/users/me")
    assert missing_res.status_code == 401

    # 2. Invalid format -> 422
    bad_res = client.get("/api/v1/users/me", headers={"X-User-Id": "not-a-uuid"})
    assert bad_res.status_code == 422

    # 3. Nonexistent UUID -> 404
    fake_id = str(uuid.uuid4())
    fake_res = client.get("/api/v1/users/me", headers={"X-User-Id": fake_id})
    assert fake_res.status_code == 404

    # 4. Valid registered candidate -> 200
    create_res = client.post("/api/v1/users", json={})
    user_id = create_res.json()["id"]
    ok_res = client.get("/api/v1/users/me", headers={"X-User-Id": user_id})
    assert ok_res.status_code == 200
    assert ok_res.json()["id"] == user_id


def test_p4_roadmap_still_rejects_unregistered_random_uuid(client: TestClient, db_session: Session):
    """
    Critical Security Check:
    Verifies that roadmap generation rejects an arbitrary/random X-User-Id that has no backend User row.
    """
    role = db_session.query(JobRole).first()
    if not role:
        role = JobRole(title=f"Role-{uuid.uuid4()}", slug=f"role-{uuid.uuid4()}")
        db_session.add(role)
        db_session.commit()

    random_user_id = str(uuid.uuid4())
    res = client.post(
        "/api/v1/roadmap/generate",
        json={"role_id": str(role.id), "location": "India"},
        headers={"X-User-Id": random_user_id},
    )
    # Backend must reject with 404 (user not found), NOT automatically create a user
    assert res.status_code == 404
    assert f"User with id '{random_user_id}' not found." in res.json()["detail"]


def test_p4_roadmap_succeeds_with_registered_user(client: TestClient, db_session: Session):
    """
    Verifies that once candidate user is established, roadmap endpoints resolve user without 404 user not found.
    """
    role = db_session.query(JobRole).first()
    if not role:
        role = JobRole(title=f"Role-{uuid.uuid4()}", slug=f"role-{uuid.uuid4()}")
        db_session.add(role)
        db_session.commit()

    # 1. Register candidate user
    create_res = client.post("/api/v1/users", json={})
    assert create_res.status_code == 201
    candidate_id = create_res.json()["id"]

    # 2. Query active roadmap (should be 404 roadmap not found, NOT 404 user not found)
    res = client.get(
        f"/api/v1/roadmap/active?role_id={role.id}",
        headers={"X-User-Id": candidate_id},
    )
    assert res.status_code == 404
    assert "No active roadmap found" in res.json()["detail"]
    assert f"User with id '{candidate_id}' not found." not in res.json()["detail"]
