"""
Comprehensive Tests for Checkpoint 4 (C4) — User Profile Database Foundation.

Test scenarios:
1. create profile
2. get profile
3. update profile
4. partial update
5. delete profile
6. create duplicate profile fails (service raises UserProfileAlreadyExistsError, API returns 409)
7. unknown user fails (service raises UserNotFoundError, API returns 404)
8. invalid user identity fails (missing X-User-Id -> 401, invalid UUID -> 422)
9. cross-user access fails (User B cannot access/mutate User A's profile)
10. user_id cannot be supplied in request body as authority (extra="forbid" -> 422)
11. optional fields can be NULL
12. semester validation (positive integer only, <= 0 rejected with 422)
13. whitespace handling (stripped, whitespace-only rejected)
14. timestamps exist and updated_at advances on mutation
15. one-to-one uniqueness enforced at database level
16. deleting user cascades to profile
17. deleting profile does NOT delete the user
18. conversations/messages remain independent from profile deletion
19. migration lifecycle: upgrade -> downgrade -> re-upgrade
"""

import os
import time
import uuid
from datetime import datetime, timezone
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.database import SessionLocal, engine
from app.db.models import Conversation, Message, User, UserProfile
from app.main import app
from app.schemas.user_profile import (
    UserProfileCreate,
    UserProfileResponse,
    UserProfileUpdate,
)
from app.services.conversation_service import conversation_service
from app.services.user_profile_service import (
    InvalidUserProfileError,
    UserNotFoundError,
    UserProfileAlreadyExistsError,
    UserProfileNotFoundError,
    user_profile_service,
)


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def alembic_cfg():
    """Alembic configuration referencing the backend alembic.ini."""
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ini_path = os.path.join(backend_dir, "alembic.ini")
    cfg = Config(ini_path)
    cfg.set_main_option("script_location", os.path.join(backend_dir, "alembic"))
    return cfg


@pytest.fixture
def db_session():
    """Provides a database session cleaned up after tests."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    """TestClient for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def primary_user(db_session: Session):
    """Creates a primary test user."""
    user = User(
        id=uuid.uuid4(),
        email=f"user_c4_a_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Candidate Alpha",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    yield user

    cleanup = SessionLocal()
    try:
        u = cleanup.query(User).filter(User.id == user.id).first()
        if u:
            cleanup.delete(u)
            cleanup.commit()
    finally:
        cleanup.close()


@pytest.fixture
def secondary_user(db_session: Session):
    """Creates a secondary test user for cross-user security tests."""
    user = User(
        id=uuid.uuid4(),
        email=f"user_c4_b_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Candidate Beta",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    yield user

    cleanup = SessionLocal()
    try:
        u = cleanup.query(User).filter(User.id == user.id).first()
        if u:
            cleanup.delete(u)
            cleanup.commit()
    finally:
        cleanup.close()


# -----------------------------------------------------------------------------
# Service Tests: CRUD & Edge Cases
# -----------------------------------------------------------------------------

def test_1_create_profile(db_session: Session, primary_user: User):
    """Scenario 1: Create profile with valid fields."""
    data = UserProfileCreate(
        name="Alpha Candidate",
        education="B.Tech",
        college="IIT Delhi",
        degree="Bachelor of Technology",
        branch="Computer Science",
        semester=6,
        target_role="Backend Engineer",
        experience_level="Intermediate",
    )
    profile = user_profile_service.create_profile(db_session, user_id=primary_user.id, profile_data=data)
    assert profile is not None
    assert profile.user_id == primary_user.id
    assert profile.name == "Alpha Candidate"
    assert profile.college == "IIT Delhi"
    assert profile.semester == 6
    assert profile.created_at is not None
    assert profile.updated_at is not None


def test_2_get_profile(db_session: Session, primary_user: User):
    """Scenario 2: Retrieve existing profile."""
    data = UserProfileCreate(name="Candidate Alpha", college="NIT Trichy")
    created = user_profile_service.create_profile(db_session, user_id=primary_user.id, profile_data=data)

    retrieved = user_profile_service.get_profile(db_session, user_id=primary_user.id)
    assert retrieved.id == created.id
    assert retrieved.name == "Candidate Alpha"
    assert retrieved.college == "NIT Trichy"


def test_3_update_profile(db_session: Session, primary_user: User):
    """Scenario 3: Update profile with multiple fields."""
    init_data = UserProfileCreate(name="Original", semester=2)
    profile = user_profile_service.create_profile(db_session, user_id=primary_user.id, profile_data=init_data)

    update_data = UserProfileUpdate(name="Updated Name", semester=4, target_role="ML Engineer")
    updated = user_profile_service.update_profile(db_session, user_id=primary_user.id, profile_data=update_data)

    assert updated.id == profile.id
    assert updated.name == "Updated Name"
    assert updated.semester == 4
    assert updated.target_role == "ML Engineer"


def test_4_partial_update(db_session: Session, primary_user: User):
    """Scenario 4: Partial update modifies only specified fields, preserving omitted ones."""
    init_data = UserProfileCreate(
        name="Candidate Alpha",
        education="B.Tech",
        college="IIT Bombay",
        semester=4,
    )
    user_profile_service.create_profile(db_session, user_id=primary_user.id, profile_data=init_data)

    # Only update semester, leave education and college omitted
    patch_data = UserProfileUpdate(semester=5)
    updated = user_profile_service.update_profile(db_session, user_id=primary_user.id, profile_data=patch_data)

    assert updated.semester == 5
    assert updated.name == "Candidate Alpha"
    assert updated.education == "B.Tech"
    assert updated.college == "IIT Bombay"


def test_5_delete_profile(db_session: Session, primary_user: User):
    """Scenario 5: Delete profile removes profile record cleanly."""
    init_data = UserProfileCreate(name="To be deleted")
    user_profile_service.create_profile(db_session, user_id=primary_user.id, profile_data=init_data)

    user_profile_service.delete_profile(db_session, user_id=primary_user.id)

    with pytest.raises(UserProfileNotFoundError):
        user_profile_service.get_profile(db_session, user_id=primary_user.id)


def test_6_create_duplicate_profile_fails(db_session: Session, primary_user: User):
    """Scenario 6: Create duplicate profile fails with UserProfileAlreadyExistsError."""
    data = UserProfileCreate(name="First Profile")
    user_profile_service.create_profile(db_session, user_id=primary_user.id, profile_data=data)

    duplicate_data = UserProfileCreate(name="Second Profile Attempt")
    with pytest.raises(UserProfileAlreadyExistsError):
        user_profile_service.create_profile(db_session, user_id=primary_user.id, profile_data=duplicate_data)


def test_7_unknown_user_fails(db_session: Session):
    """Scenario 7: Operations on nonexistent user raise UserNotFoundError."""
    nonexistent_id = uuid.uuid4()
    data = UserProfileCreate(name="Ghost")

    with pytest.raises(UserNotFoundError):
        user_profile_service.create_profile(db_session, user_id=nonexistent_id, profile_data=data)

    with pytest.raises(UserNotFoundError):
        user_profile_service.get_profile(db_session, user_id=nonexistent_id)

    with pytest.raises(UserNotFoundError):
        user_profile_service.update_profile(db_session, user_id=nonexistent_id, profile_data=UserProfileUpdate(name="Ghost"))

    with pytest.raises(UserNotFoundError):
        user_profile_service.delete_profile(db_session, user_id=nonexistent_id)


# -----------------------------------------------------------------------------
# API Endpoints & Security Tests
# -----------------------------------------------------------------------------

def test_8_invalid_user_identity_fails(client: TestClient):
    """Scenario 8: Missing header returns 401; malformed UUID returns 422."""
    # 1. Missing header
    res_missing = client.get("/api/v1/profile")
    assert res_missing.status_code == 401
    assert "Authentication required: X-User-Id header missing" in res_missing.json()["detail"]

    # 2. Malformed UUID
    res_malformed = client.get("/api/v1/profile", headers={"X-User-Id": "invalid-not-uuid"})
    assert res_malformed.status_code == 422
    assert "Invalid user ID format in X-User-Id header" in res_malformed.json()["detail"]


def test_9_cross_user_access_fails(client: TestClient, primary_user: User, secondary_user: User):
    """Scenario 9: User B cannot access or modify User A's profile."""
    # Create profile for User A
    res_create = client.post(
        "/api/v1/profile",
        headers={"X-User-Id": str(primary_user.id)},
        json={"name": "User Alpha Profile", "college": "IIT Madras"},
    )
    assert res_create.status_code == 201

    # User B requests profile -> returns 404 (User B has no profile yet)
    res_get_b = client.get("/api/v1/profile", headers={"X-User-Id": str(secondary_user.id)})
    assert res_get_b.status_code == 404

    # User B patches profile -> returns 404
    res_patch_b = client.patch(
        "/api/v1/profile",
        headers={"X-User-Id": str(secondary_user.id)},
        json={"name": "Attacker Name"},
    )
    assert res_patch_b.status_code == 404

    # User A's profile remains untouched
    res_get_a = client.get("/api/v1/profile", headers={"X-User-Id": str(primary_user.id)})
    assert res_get_a.status_code == 200
    assert res_get_a.json()["name"] == "User Alpha Profile"


def test_10_user_id_cannot_be_supplied_in_request_body(client: TestClient, primary_user: User):
    """Scenario 10: user_id supplied in request body is rejected with 422 (extra='forbid')."""
    res_post = client.post(
        "/api/v1/profile",
        headers={"X-User-Id": str(primary_user.id)},
        json={
            "name": "Hacker Attempt",
            "user_id": str(uuid.uuid4()),
        },
    )
    assert res_post.status_code == 422
    detail_str = str(res_post.json()["detail"]).lower()
    assert "extra_forbidden" in detail_str or "extra fields not permitted" in detail_str

    res_patch = client.patch(
        "/api/v1/profile",
        headers={"X-User-Id": str(primary_user.id)},
        json={
            "user_id": str(uuid.uuid4()),
        },
    )
    assert res_patch.status_code == 422


def test_11_optional_fields_can_be_null(client: TestClient, primary_user: User):
    """Scenario 11: All fields can be omitted or null."""
    res_create = client.post(
        "/api/v1/profile",
        headers={"X-User-Id": str(primary_user.id)},
        json={},
    )
    assert res_create.status_code == 201
    data = res_create.json()
    assert data["user_id"] == str(primary_user.id)
    assert data["name"] is None
    assert data["education"] is None
    assert data["college"] is None
    assert data["degree"] is None
    assert data["branch"] is None
    assert data["semester"] is None
    assert data["target_role"] is None
    assert data["experience_level"] is None


def test_12_semester_validation(client: TestClient, primary_user: User):
    """Scenario 12: Semester must be a positive integer (> 0). <= 0 is rejected."""
    # Negative semester
    res_neg = client.post(
        "/api/v1/profile",
        headers={"X-User-Id": str(primary_user.id)},
        json={"semester": -1},
    )
    assert res_neg.status_code == 422

    # Zero semester
    res_zero = client.post(
        "/api/v1/profile",
        headers={"X-User-Id": str(primary_user.id)},
        json={"semester": 0},
    )
    assert res_zero.status_code == 422

    # Valid semester
    res_valid = client.post(
        "/api/v1/profile",
        headers={"X-User-Id": str(primary_user.id)},
        json={"semester": 6},
    )
    assert res_valid.status_code == 201
    assert res_valid.json()["semester"] == 6


def test_13_whitespace_handling(client: TestClient, primary_user: User):
    """Scenario 13: Surrounding whitespace is stripped; empty/whitespace-only string is rejected."""
    # Empty string rejected
    res_empty = client.post(
        "/api/v1/profile",
        headers={"X-User-Id": str(primary_user.id)},
        json={"name": "   "},
    )
    assert res_empty.status_code == 422

    # Surrounding whitespace stripped
    res_trimmed = client.post(
        "/api/v1/profile",
        headers={"X-User-Id": str(primary_user.id)},
        json={"name": "   Jane Doe   ", "college": "  IIT Delhi  "},
    )
    assert res_trimmed.status_code == 201
    assert res_trimmed.json()["name"] == "Jane Doe"
    assert res_trimmed.json()["college"] == "IIT Delhi"


def test_14_timestamps_exist_and_updated_at_advances(db_session: Session, primary_user: User):
    """Scenario 14: Timestamps exist, updated_at advances on mutation."""
    data = UserProfileCreate(name="Initial")
    profile = user_profile_service.create_profile(db_session, user_id=primary_user.id, profile_data=data)

    created_at = profile.created_at
    updated_at = profile.updated_at
    assert created_at is not None
    assert updated_at is not None

    time.sleep(0.01)
    updated = user_profile_service.update_profile(
        db_session, user_id=primary_user.id, profile_data=UserProfileUpdate(name="Modified")
    )
    assert updated.updated_at > updated_at


# -----------------------------------------------------------------------------
# Database Level & Cascade Invariants
# -----------------------------------------------------------------------------

def test_15_one_to_one_uniqueness_enforced_at_db_level(db_session: Session, primary_user: User):
    """Scenario 15: Direct DB insert of second profile for same user violates uq_user_profiles_user_id."""
    p1 = UserProfile(id=uuid.uuid4(), user_id=primary_user.id, name="First")
    db_session.add(p1)
    db_session.commit()

    p2 = UserProfile(id=uuid.uuid4(), user_id=primary_user.id, name="Duplicate")
    db_session.add(p2)
    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()
    db_session.rollback()
    assert "uq_user_profiles_user_id" in str(exc_info.value)


def test_16_deleting_user_cascades_to_profile(db_session: Session):
    """Scenario 16: Deleting User cascades to delete their UserProfile."""
    user = User(
        id=uuid.uuid4(),
        email=f"cascade_test_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Cascade User",
    )
    db_session.add(user)
    db_session.commit()

    profile = UserProfile(id=uuid.uuid4(), user_id=user.id, name="Cascade Profile")
    db_session.add(profile)
    db_session.commit()
    profile_id = profile.id

    # Delete the user
    db_session.delete(user)
    db_session.commit()

    # Profile should be gone
    p_check = db_session.query(UserProfile).filter(UserProfile.id == profile_id).first()
    assert p_check is None


def test_17_deleting_profile_does_not_delete_user(db_session: Session, primary_user: User):
    """Scenario 17: Deleting UserProfile does NOT delete the User record."""
    data = UserProfileCreate(name="Preserve User Test")
    user_profile_service.create_profile(db_session, user_id=primary_user.id, profile_data=data)

    user_profile_service.delete_profile(db_session, user_id=primary_user.id)

    # User remains intact
    u_check = db_session.query(User).filter(User.id == primary_user.id).first()
    assert u_check is not None
    assert u_check.id == primary_user.id


def test_18_conversations_and_messages_independent_from_profile(db_session: Session, primary_user: User):
    """Scenario 18: Conversations and messages remain completely independent from profile creation/deletion."""
    # 1. Create a conversation and messages for the user
    conv = conversation_service.create_conversation(db_session, user_id=primary_user.id, title="Independent Chat")
    msg1 = conversation_service.add_message(db_session, conv.id, primary_user.id, role="user", content="Hello")
    msg2 = conversation_service.add_message(db_session, conv.id, primary_user.id, role="assistant", content="Hi")

    # 2. Create user profile
    user_profile_service.create_profile(db_session, user_id=primary_user.id, profile_data=UserProfileCreate(name="Profile"))

    # 3. Delete user profile
    user_profile_service.delete_profile(db_session, user_id=primary_user.id)

    # 4. Verify conversation and messages remain completely untouched
    conv_check = conversation_service.get_conversation(db_session, conv.id, primary_user.id)
    assert conv_check is not None
    messages_check = conversation_service.get_messages(db_session, conv.id, primary_user.id)
    assert len(messages_check) == 2
    assert messages_check[0].content == "Hello"
    assert messages_check[1].content == "Hi"


# -----------------------------------------------------------------------------
# Migration Lifecycle Tests
# -----------------------------------------------------------------------------

def test_19_migration_lifecycle(alembic_cfg):
    """Scenario 19: Verify migration 0020 downgrades and re-upgrades cleanly, ending at head."""
    try:
        # Downgrade to 0019
        command.downgrade(alembic_cfg, "0019_conversations_and_messages")
        inspector = inspect(engine)
        assert "user_profiles" not in inspector.get_table_names()
        # Verify conversations and messages are still present
        assert "conversations" in inspector.get_table_names()
        assert "messages" in inspector.get_table_names()

        # Upgrade back to head (0020)
        command.upgrade(alembic_cfg, "head")
        inspector = inspect(engine)
        assert "user_profiles" in inspector.get_table_names()
    finally:
        # Ensure DB ends at head
        command.upgrade(alembic_cfg, "head")
