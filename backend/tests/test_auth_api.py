"""Focused unit and integration test suite for Login Phase 2:
Email/Password Authentication, Password Hashing via scrypt, Server-Side Sessions,
HTTP-only Cookies, and Current-User Dependency.

Verifies:
1. signup success
2. signup creates a new real User
3. password is hashed, not plaintext
4. duplicate email -> 409
5. email normalization
6. password < 8 rejected
7. password > 128 rejected
8. login success
9. wrong password -> generic 401
10. nonexistent email -> same generic 401
11. inactive user rejected
12. session cookie created
13. HttpOnly set
14. SameSite=Lax
15. Secure behavior matches environment
16. /auth/me works with valid cookie
17. /auth/me without cookie -> 401
18. invalid session token -> 401
19. expired session -> 401
20. logout revokes session
21. multiple sessions can coexist
22. remember-me creates longer lifetime
23. raw session token not stored in DB
24. X-User-Id alone cannot authenticate
25. Bearer header cannot authenticate
26. synthetic candidate account is NOT adopted
27. logout clears cookie
28. inactive user session is rejected
"""

from datetime import datetime, timedelta, timezone
import hashlib
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import hash_password, hash_session_token, verify_password
from app.db.database import SessionLocal
from app.db.models import User, UserSession
from app.main import app


@pytest.fixture
def db():
    """Provides a database session with automatic cleanup for test-isolated users."""
    session = SessionLocal()
    created_user_ids = []
    try:
        yield session, created_user_ids
    finally:
        if created_user_ids:
            session.query(UserSession).filter(UserSession.user_id.in_(created_user_ids)).delete(synchronize_session=False)
            session.query(User).filter(User.id.in_(created_user_ids)).delete(synchronize_session=False)
            session.commit()
        session.close()


@pytest.fixture
def client():
    """Provides a standard FastAPI TestClient."""
    return TestClient(app)


# -----------------------------------------------------------------------------
# 1. Signup Success
# -----------------------------------------------------------------------------
def test_01_signup_success(client: TestClient, db):
    session, created_user_ids = db
    email = f"candidate_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": email,
        "password": "StrongPassword123!",
        "full_name": "Ada Lovelace",
        "target_role": "Backend Engineer",
    }
    res = client.post("/api/v1/auth/signup", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == email.lower()
    assert data["full_name"] == "Ada Lovelace"
    assert data["target_role"] == "Backend Engineer"
    assert data["auth_provider"] == "local"
    assert data["is_active"] is True
    assert "hashed_password" not in data
    assert "password" not in data

    user_id = uuid.UUID(data["id"])
    created_user_ids.append(user_id)

    # Session cookie must be present
    assert settings.SESSION_COOKIE_NAME in res.cookies


# -----------------------------------------------------------------------------
# 2. Signup Creates a New Real User in PostgreSQL
# -----------------------------------------------------------------------------
def test_02_signup_creates_new_real_user(client: TestClient, db):
    session, created_user_ids = db
    email = f"candidate_{uuid.uuid4().hex[:8]}@example.com"
    payload = {"email": email, "password": "SecurePassword999!"}
    res = client.post("/api/v1/auth/signup", json=payload)
    assert res.status_code == 201
    user_id = uuid.UUID(res.json()["id"])
    created_user_ids.append(user_id)

    db_user = session.query(User).filter(User.id == user_id).first()
    assert db_user is not None
    assert db_user.email == email
    assert db_user.auth_provider == "local"
    assert db_user.is_active is True


# -----------------------------------------------------------------------------
# 3. Password is Hashed via scrypt, Not Plaintext
# -----------------------------------------------------------------------------
def test_03_password_is_hashed_scrypt(client: TestClient, db):
    session, created_user_ids = db
    plain_password = "MySecretPassword123!"
    email = f"candidate_{uuid.uuid4().hex[:8]}@example.com"
    res = client.post("/api/v1/auth/signup", json={"email": email, "password": plain_password})
    assert res.status_code == 201
    user_id = uuid.UUID(res.json()["id"])
    created_user_ids.append(user_id)

    db_user = session.query(User).filter(User.id == user_id).first()
    assert db_user.hashed_password is not None
    assert plain_password not in db_user.hashed_password
    assert db_user.hashed_password.startswith("scrypt$16384$8$1$")
    assert verify_password(plain_password, db_user.hashed_password) is True


# -----------------------------------------------------------------------------
# 4. Duplicate Email Returns 409 Conflict
# -----------------------------------------------------------------------------
def test_04_duplicate_email_returns_409(client: TestClient, db):
    session, created_user_ids = db
    email = f"candidate_{uuid.uuid4().hex[:8]}@example.com"
    res1 = client.post("/api/v1/auth/signup", json={"email": email, "password": "Password123!"})
    assert res1.status_code == 201
    created_user_ids.append(uuid.UUID(res1.json()["id"]))

    res2 = client.post("/api/v1/auth/signup", json={"email": email, "password": "AnotherPassword456!"})
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"].lower()


# -----------------------------------------------------------------------------
# 5. Email Normalization
# -----------------------------------------------------------------------------
def test_05_email_normalization(client: TestClient, db):
    session, created_user_ids = db
    raw_email = f"  CANDIDATE_{uuid.uuid4().hex[:6]}@EXAMPLE.COM  "
    expected_email = raw_email.strip().lower()

    res = client.post("/api/v1/auth/signup", json={"email": raw_email, "password": "Password123!"})
    assert res.status_code == 201
    user_id = uuid.UUID(res.json()["id"])
    created_user_ids.append(user_id)

    assert res.json()["email"] == expected_email
    db_user = session.query(User).filter(User.id == user_id).first()
    assert db_user.email == expected_email


# -----------------------------------------------------------------------------
# 6. Password < 8 Characters Rejected
# -----------------------------------------------------------------------------
def test_06_password_under_8_rejected(client: TestClient):
    email = f"candidate_{uuid.uuid4().hex[:8]}@example.com"
    res = client.post("/api/v1/auth/signup", json={"email": email, "password": "short"})
    assert res.status_code == 422


# -----------------------------------------------------------------------------
# 7. Password > 128 Characters Rejected
# -----------------------------------------------------------------------------
def test_07_password_over_128_rejected(client: TestClient):
    email = f"candidate_{uuid.uuid4().hex[:8]}@example.com"
    too_long = "A" * 129
    res = client.post("/api/v1/auth/signup", json={"email": email, "password": too_long})
    assert res.status_code == 422


# -----------------------------------------------------------------------------
# 8. Login Success
# -----------------------------------------------------------------------------
def test_08_login_success(client: TestClient, db):
    session, created_user_ids = db
    email = f"candidate_{uuid.uuid4().hex[:8]}@example.com"
    password = "CorrectPassword123!"

    # Signup
    signup_res = client.post("/api/v1/auth/signup", json={"email": email, "password": password})
    assert signup_res.status_code == 201
    created_user_ids.append(uuid.UUID(signup_res.json()["id"]))

    # Clean cookies to test fresh login
    client.cookies.clear()

    # Login
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login_res.status_code == 200
    assert login_res.json()["email"] == email.lower()
    assert settings.SESSION_COOKIE_NAME in login_res.cookies


# -----------------------------------------------------------------------------
# 9. Wrong Password -> Generic 401
# -----------------------------------------------------------------------------
def test_09_wrong_password_generic_401(client: TestClient, db):
    session, created_user_ids = db
    email = f"candidate_{uuid.uuid4().hex[:8]}@example.com"
    signup_res = client.post("/api/v1/auth/signup", json={"email": email, "password": "CorrectPassword123!"})
    assert signup_res.status_code == 201
    created_user_ids.append(uuid.UUID(signup_res.json()["id"]))

    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "WrongPassword!"})
    assert login_res.status_code == 401
    assert login_res.json()["detail"] == "Invalid email or password"


# -----------------------------------------------------------------------------
# 10. Nonexistent Email -> Same Generic 401
# -----------------------------------------------------------------------------
def test_10_nonexistent_email_same_generic_401(client: TestClient):
    fake_email = f"nonexistent_{uuid.uuid4().hex[:8]}@example.com"
    login_res = client.post("/api/v1/auth/login", json={"email": fake_email, "password": "AnyPassword123!"})
    assert login_res.status_code == 401
    assert login_res.json()["detail"] == "Invalid email or password"


# -----------------------------------------------------------------------------
# 11. Inactive User Login Rejected
# -----------------------------------------------------------------------------
def test_11_inactive_user_rejected(client: TestClient, db):
    session, created_user_ids = db
    email = f"candidate_{uuid.uuid4().hex[:8]}@example.com"
    password = "ValidPassword123!"

    signup_res = client.post("/api/v1/auth/signup", json={"email": email, "password": password})
    assert signup_res.status_code == 201
    user_id = uuid.UUID(signup_res.json()["id"])
    created_user_ids.append(user_id)

    # Deactivate user directly in PostgreSQL
    db_user = session.query(User).filter(User.id == user_id).first()
    db_user.is_active = False
    session.commit()

    client.cookies.clear()
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login_res.status_code == 401


# -----------------------------------------------------------------------------
# 12. Session Cookie Created
# -----------------------------------------------------------------------------
def test_12_session_cookie_created(client: TestClient, db):
    session, created_user_ids = db
    email = f"candidate_{uuid.uuid4().hex[:8]}@example.com"
    res = client.post("/api/v1/auth/signup", json={"email": email, "password": "Password123!"})
    assert res.status_code == 201
    created_user_ids.append(uuid.UUID(res.json()["id"]))
    assert settings.SESSION_COOKIE_NAME in res.cookies


# -----------------------------------------------------------------------------
# 13. HttpOnly Flag Set on Session Cookie
# -----------------------------------------------------------------------------
def test_13_cookie_httponly_set(client: TestClient, db):
    session, created_user_ids = db
    email = f"candidate_{uuid.uuid4().hex[:8]}@example.com"
    res = client.post("/api/v1/auth/signup", json={"email": email, "password": "Password123!"})
    assert res.status_code == 201
    created_user_ids.append(uuid.UUID(res.json()["id"]))
    cookie_header = res.headers.get("set-cookie", "")
    assert "httponly" in cookie_header.lower()


# -----------------------------------------------------------------------------
# 14. SameSite=Lax Set on Session Cookie
# -----------------------------------------------------------------------------
def test_14_cookie_samesite_lax(client: TestClient, db):
    session, created_user_ids = db
    email = f"candidate_{uuid.uuid4().hex[:8]}@example.com"
    res = client.post("/api/v1/auth/signup", json={"email": email, "password": "Password123!"})
    assert res.status_code == 201
    created_user_ids.append(uuid.UUID(res.json()["id"]))
    cookie_header = res.headers.get("set-cookie", "")
    assert "samesite=lax" in cookie_header.lower()


# -----------------------------------------------------------------------------
# 15. Secure Attribute Matches Environment Setting
# -----------------------------------------------------------------------------
def test_15_secure_matches_environment(client: TestClient, db):
    session, created_user_ids = db
    email = f"candidate_{uuid.uuid4().hex[:8]}@example.com"
    res = client.post("/api/v1/auth/signup", json={"email": email, "password": "Password123!"})
    assert res.status_code == 201
    created_user_ids.append(uuid.UUID(res.json()["id"]))
    cookie_header = res.headers.get("set-cookie", "")
    if settings.SESSION_COOKIE_SECURE:
        assert "secure" in cookie_header.lower()
    else:
        # For local HTTP development, secure is not asserted
        pass


# -----------------------------------------------------------------------------
# 16. /auth/me Works With Valid Cookie
# -----------------------------------------------------------------------------
def test_16_auth_me_with_valid_cookie(client: TestClient, db):
    session, created_user_ids = db
    email = f"candidate_{uuid.uuid4().hex[:8]}@example.com"
    signup_res = client.post("/api/v1/auth/signup", json={"email": email, "password": "Password123!", "full_name": "Test Me"})
    assert signup_res.status_code == 201
    user_id = signup_res.json()["id"]
    created_user_ids.append(uuid.UUID(user_id))

    me_res = client.get("/api/v1/auth/me")
    assert me_res.status_code == 200
    assert me_res.json()["id"] == user_id
    assert me_res.json()["email"] == email.lower()
    assert me_res.json()["full_name"] == "Test Me"


# -----------------------------------------------------------------------------
# 17. /auth/me Without Cookie Returns 401
# -----------------------------------------------------------------------------
def test_17_auth_me_without_cookie_returns_401(client: TestClient):
    client.cookies.clear()
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401
    assert "session cookie missing" in res.json()["detail"].lower()


# -----------------------------------------------------------------------------
# 18. Invalid Session Token Returns 401
# -----------------------------------------------------------------------------
def test_18_invalid_session_token_returns_401(client: TestClient):
    client.cookies.set(settings.SESSION_COOKIE_NAME, "completely_invalid_session_token_value")
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401
    assert "invalid or revoked" in res.json()["detail"].lower()


# -----------------------------------------------------------------------------
# 19. Expired Session Returns 401
# -----------------------------------------------------------------------------
def test_19_expired_session_returns_401(client: TestClient, db):
    session, created_user_ids = db
    email = f"candidate_{uuid.uuid4().hex[:8]}@example.com"
    signup_res = client.post("/api/v1/auth/signup", json={"email": email, "password": "Password123!"})
    assert signup_res.status_code == 201
    user_id = uuid.UUID(signup_res.json()["id"])
    created_user_ids.append(user_id)

    raw_token = signup_res.cookies.get(settings.SESSION_COOKIE_NAME)
    token_hash = hash_session_token(raw_token)

    # Mutate expiry date to past in PostgreSQL
    user_session = session.query(UserSession).filter(UserSession.token_hash == token_hash).first()
    assert user_session is not None
    user_session.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    session.commit()

    me_res = client.get("/api/v1/auth/me")
    assert me_res.status_code == 401
    assert "session expired" in me_res.json()["detail"].lower()


# -----------------------------------------------------------------------------
# 20. Logout Revokes Session in PostgreSQL
# -----------------------------------------------------------------------------
def test_20_logout_revokes_session(client: TestClient, db):
    session, created_user_ids = db
    email = f"candidate_{uuid.uuid4().hex[:8]}@example.com"
    signup_res = client.post("/api/v1/auth/signup", json={"email": email, "password": "Password123!"})
    assert signup_res.status_code == 201
    user_id = uuid.UUID(signup_res.json()["id"])
    created_user_ids.append(user_id)

    raw_token = signup_res.cookies.get(settings.SESSION_COOKIE_NAME)
    token_hash = hash_session_token(raw_token)

    # Confirm session exists
    assert session.query(UserSession).filter(UserSession.token_hash == token_hash).first() is not None

    # Logout
    logout_res = client.post("/api/v1/auth/logout")
    assert logout_res.status_code == 200

    # Session record must be deleted from PostgreSQL
    session.expire_all()
    assert session.query(UserSession).filter(UserSession.token_hash == token_hash).first() is None

    # Subsequent /auth/me must fail
    me_res = client.get("/api/v1/auth/me")
    assert me_res.status_code == 401


# -----------------------------------------------------------------------------
# 21. Multiple Sessions Can Coexist
# -----------------------------------------------------------------------------
def test_21_multiple_sessions_coexist(client: TestClient, db):
    session, created_user_ids = db
    email = f"candidate_{uuid.uuid4().hex[:8]}@example.com"
    password = "MultiDevicePassword123!"

    # Device 1: Signup
    res1 = client.post("/api/v1/auth/signup", json={"email": email, "password": password})
    assert res1.status_code == 201
    user_id = uuid.UUID(res1.json()["id"])
    created_user_ids.append(user_id)
    token_1 = res1.cookies.get(settings.SESSION_COOKIE_NAME)

    # Device 2: Login
    client2 = TestClient(app)
    res2 = client2.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res2.status_code == 200
    token_2 = res2.cookies.get(settings.SESSION_COOKIE_NAME)

    assert token_1 != token_2

    # Both tokens are valid
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_1)
    assert client.get("/api/v1/auth/me").status_code == 200

    client2.cookies.set(settings.SESSION_COOKIE_NAME, token_2)
    assert client2.get("/api/v1/auth/me").status_code == 200


# -----------------------------------------------------------------------------
# 22. Remember-Me Creates Longer Lifetime
# -----------------------------------------------------------------------------
def test_22_remember_me_creates_longer_lifetime(client: TestClient, db):
    session, created_user_ids = db
    email = f"candidate_{uuid.uuid4().hex[:8]}@example.com"
    password = "LongSessionPassword123!"

    # Normal login (7 days)
    res_normal = client.post("/api/v1/auth/signup", json={"email": email, "password": password})
    created_user_ids.append(uuid.UUID(res_normal.json()["id"]))
    token_normal = res_normal.cookies.get(settings.SESSION_COOKIE_NAME)
    hash_normal = hash_session_token(token_normal)

    sess_normal = session.query(UserSession).filter(UserSession.token_hash == hash_normal).first()
    normal_duration = (sess_normal.expires_at - sess_normal.created_at).total_seconds()
    assert abs(normal_duration - (7 * 24 * 3600)) < 60

    # Remember-me login (30 days)
    res_remember = client.post("/api/v1/auth/login", json={"email": email, "password": password, "remember_me": True})
    token_remember = res_remember.cookies.get(settings.SESSION_COOKIE_NAME)
    hash_remember = hash_session_token(token_remember)

    sess_remember = session.query(UserSession).filter(UserSession.token_hash == hash_remember).first()
    remember_duration = (sess_remember.expires_at - sess_remember.created_at).total_seconds()
    assert abs(remember_duration - (30 * 24 * 3600)) < 60


# -----------------------------------------------------------------------------
# 23. Raw Session Token is Never Stored in Database
# -----------------------------------------------------------------------------
def test_23_raw_token_not_in_db(client: TestClient, db):
    session, created_user_ids = db
    email = f"candidate_{uuid.uuid4().hex[:8]}@example.com"
    res = client.post("/api/v1/auth/signup", json={"email": email, "password": "Password123!"})
    created_user_ids.append(uuid.UUID(res.json()["id"]))
    raw_token = res.cookies.get(settings.SESSION_COOKIE_NAME)

    # Search PostgreSQL user_sessions for raw token string
    raw_in_db = session.query(UserSession).filter(UserSession.token_hash == raw_token).first()
    assert raw_in_db is None

    # Expected SHA-256 hash must match
    expected_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    hashed_in_db = session.query(UserSession).filter(UserSession.token_hash == expected_hash).first()
    assert hashed_in_db is not None


# -----------------------------------------------------------------------------
# 24. X-User-Id Alone Cannot Authenticate
# -----------------------------------------------------------------------------
def test_24_x_user_id_alone_cannot_authenticate(client: TestClient, db):
    session, created_user_ids = db
    email = f"candidate_{uuid.uuid4().hex[:8]}@example.com"
    res = client.post("/api/v1/auth/signup", json={"email": email, "password": "Password123!"})
    user_id = res.json()["id"]
    created_user_ids.append(uuid.UUID(user_id))

    client.cookies.clear()
    # Supplying spoofed X-User-Id without cookie must be rejected with 401
    me_res = client.get("/api/v1/auth/me", headers={"X-User-Id": user_id})
    assert me_res.status_code == 401


# -----------------------------------------------------------------------------
# 25. Bearer Header Cannot Authenticate
# -----------------------------------------------------------------------------
def test_25_bearer_header_cannot_authenticate(client: TestClient, db):
    session, created_user_ids = db
    email = f"candidate_{uuid.uuid4().hex[:8]}@example.com"
    res = client.post("/api/v1/auth/signup", json={"email": email, "password": "Password123!"})
    user_id = res.json()["id"]
    created_user_ids.append(uuid.UUID(user_id))

    client.cookies.clear()
    # Supplying Authorization: Bearer without cookie must be rejected with 401
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer some_token"})
    assert me_res.status_code == 401


# -----------------------------------------------------------------------------
# 26. Synthetic Candidate Account is NOT Adopted
# -----------------------------------------------------------------------------
def test_26_synthetic_candidate_not_adopted(client: TestClient, db):
    session, created_user_ids = db

    # Create synthetic candidate user via legacy endpoint
    legacy_res = client.post("/api/v1/users", json={})
    assert legacy_res.status_code == 201
    synthetic_id = uuid.UUID(legacy_res.json()["id"])
    synthetic_email = legacy_res.json()["email"]
    created_user_ids.append(synthetic_id)

    assert "@skillforge.local" in synthetic_email

    # Signup with real email
    real_email = f"real_candidate_{uuid.uuid4().hex[:8]}@example.com"
    signup_res = client.post("/api/v1/auth/signup", json={"email": real_email, "password": "RealPassword123!"})
    assert signup_res.status_code == 201
    real_id = uuid.UUID(signup_res.json()["id"])
    created_user_ids.append(real_id)

    # IDs must be completely distinct; synthetic user is unaffected
    assert real_id != synthetic_id
    db_synthetic = session.query(User).filter(User.id == synthetic_id).first()
    assert db_synthetic.email == synthetic_email
    assert db_synthetic.hashed_password is None


# -----------------------------------------------------------------------------
# 27. Logout Clears Cookie
# -----------------------------------------------------------------------------
def test_27_logout_clears_cookie(client: TestClient, db):
    session, created_user_ids = db
    email = f"candidate_{uuid.uuid4().hex[:8]}@example.com"
    signup_res = client.post("/api/v1/auth/signup", json={"email": email, "password": "Password123!"})
    created_user_ids.append(uuid.UUID(signup_res.json()["id"]))

    logout_res = client.post("/api/v1/auth/logout")
    assert logout_res.status_code == 200

    set_cookie = logout_res.headers.get("set-cookie", "")
    assert settings.SESSION_COOKIE_NAME in set_cookie
    # Cookie should be expired or empty
    assert 'max-age=0' in set_cookie.lower() or 'expires=' in set_cookie.lower() or '""' in set_cookie


# -----------------------------------------------------------------------------
# 28. Inactive User Session is Rejected
# -----------------------------------------------------------------------------
def test_28_inactive_user_session_rejected(client: TestClient, db):
    session, created_user_ids = db
    email = f"candidate_{uuid.uuid4().hex[:8]}@example.com"
    signup_res = client.post("/api/v1/auth/signup", json={"email": email, "password": "Password123!"})
    user_id = uuid.UUID(signup_res.json()["id"])
    created_user_ids.append(user_id)

    # Verify session works
    assert client.get("/api/v1/auth/me").status_code == 200

    # Deactivate user in PostgreSQL
    db_user = session.query(User).filter(User.id == user_id).first()
    db_user.is_active = False
    session.commit()

    # Session must now be rejected
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401
    assert "inactive" in res.json()["detail"].lower()
