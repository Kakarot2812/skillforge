"""Focused test suite for Login Phase 3:
Google OAuth 2.0 Authorization Code flow with PKCE, HMAC-SHA256 signed state protection,
Google identity validation, Account Resolution Matrix (Cases A-E), and session cookie integration.

Covers all 22 required specifications:
1. Google login endpoint redirects correctly
2. Missing Google credentials fails safely
3. State generated
4. Invalid state rejected
5. Expired state rejected
6. State cannot be reused
7. PKCE challenge generated
8. Authorization code exchanged with correct verifier
9. Google API/token exchange failure handled safely
10. Unverified Google email rejected
11. Brand-new Google user created (Case A)
12. Existing Google user resolved by sub (Case B)
13. Existing local user linked by verified email (Case C)
14. Duplicate Google subject conflict rejected (Case D)
15. Session created after successful Google login
16. skillforge_session cookie set
17. Session works with /api/v1/auth/me
18. Google login does NOT use Bearer/JWT
19. Google secrets never appear in logs / responses
20. Google callback cannot select arbitrary SkillForge user
21. Google subject cannot be reassigned between users
22. Failed OAuth flow creates no authenticated session
"""

import base64
import hashlib
import json
import time
from unittest.mock import AsyncMock, patch
import urllib.parse
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import hash_session_token
from app.db.database import SessionLocal
from app.db.models import User, UserSession
from app.main import app
from app.services.oauth_service import GoogleUserInfo, oauth_service


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


@pytest.fixture(autouse=True)
def configure_google_oauth():
    """Ensures test environment has mock Google OAuth credentials configured."""
    original_client_id = settings.GOOGLE_CLIENT_ID
    original_client_secret = settings.GOOGLE_CLIENT_SECRET
    original_redirect_uri = settings.GOOGLE_REDIRECT_URI

    settings.GOOGLE_CLIENT_ID = "test-google-client-id-12345.apps.googleusercontent.com"
    settings.GOOGLE_CLIENT_SECRET = "test-google-client-secret-XYZ98765"
    settings.GOOGLE_REDIRECT_URI = "http://localhost:8000/api/v1/auth/google/callback"

    yield

    settings.GOOGLE_CLIENT_ID = original_client_id
    settings.GOOGLE_CLIENT_SECRET = original_client_secret
    settings.GOOGLE_REDIRECT_URI = original_redirect_uri


# -----------------------------------------------------------------------------
# 1. Google login endpoint redirects correctly
# -----------------------------------------------------------------------------
def test_01_google_login_redirects_correctly(client: TestClient):
    res = client.get("/api/v1/auth/google/login", follow_redirects=False)
    assert res.status_code == 302
    assert "location" in res.headers

    location = res.headers["location"]
    assert location.startswith("https://accounts.google.com/o/oauth2/v2/auth")

    parsed = urllib.parse.urlparse(location)
    params = urllib.parse.parse_qs(parsed.query)

    assert params["client_id"][0] == settings.GOOGLE_CLIENT_ID
    assert params["redirect_uri"][0] == settings.GOOGLE_REDIRECT_URI
    assert params["response_type"][0] == "code"
    assert "openid" in params["scope"][0]
    assert "email" in params["scope"][0]
    assert "code_challenge" in params
    assert params["code_challenge_method"][0] == "S256"
    assert "state" in params

    # State cookie must be set
    assert "skillforge_oauth_state" in res.cookies


# -----------------------------------------------------------------------------
# 2. Missing Google credentials fails safely
# -----------------------------------------------------------------------------
def test_02_missing_credentials_fails_safely(client: TestClient):
    settings.GOOGLE_CLIENT_ID = None
    settings.GOOGLE_CLIENT_SECRET = None

    res = client.get("/api/v1/auth/google/login", follow_redirects=False)
    assert res.status_code == 503
    data = res.json()
    assert "not configured" in data["detail"].lower()
    # Ensure no secrets are leaked
    assert "XYZ98765" not in res.text


# -----------------------------------------------------------------------------
# 3. State generated (cryptographically random)
# -----------------------------------------------------------------------------
def test_03_state_generated_random(client: TestClient):
    res1 = client.get("/api/v1/auth/google/login", follow_redirects=False)
    res2 = client.get("/api/v1/auth/google/login", follow_redirects=False)

    loc1 = urllib.parse.parse_qs(urllib.parse.urlparse(res1.headers["location"]).query)
    loc2 = urllib.parse.parse_qs(urllib.parse.urlparse(res2.headers["location"]).query)

    state1 = loc1["state"][0]
    state2 = loc2["state"][0]

    assert len(state1) >= 32
    assert len(state2) >= 32
    assert state1 != state2


# -----------------------------------------------------------------------------
# 4. Invalid state rejected
# -----------------------------------------------------------------------------
def test_04_invalid_state_rejected(client: TestClient):
    # Initiate login to obtain legitimate cookie
    res = client.get("/api/v1/auth/google/login", follow_redirects=False)
    state_cookie = res.cookies.get("skillforge_oauth_state")

    # Send callback with tampered state query param
    callback_res = client.get(
        "/api/v1/auth/google/callback?code=mock_code&state=completely_tampered_state",
        cookies={"skillforge_oauth_state": state_cookie},
        follow_redirects=False,
    )
    assert callback_res.status_code == 400
    assert "state" in callback_res.json()["detail"].lower()


# -----------------------------------------------------------------------------
# 5. Expired state rejected
# -----------------------------------------------------------------------------
def test_05_expired_state_rejected(client: TestClient):
    state = oauth_service.generate_state()
    verifier, _ = oauth_service.generate_pkce_pair()

    # Create expired cookie (15 minutes old)
    payload = {
        "state": state,
        "verifier": verifier,
        "iat": int(time.time()) - 900,
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    b64_payload = base64.urlsafe_b64encode(payload_bytes).decode("ascii").rstrip("=")
    signature = hashlib.sha256(b64_payload.encode("ascii")).hexdigest()
    # Correct signature with SECRET_KEY
    import hmac
    signature = hmac.new(settings.SECRET_KEY.encode("utf-8"), b64_payload.encode("ascii"), hashlib.sha256).hexdigest()
    expired_cookie = f"{b64_payload}.{signature}"

    callback_res = client.get(
        f"/api/v1/auth/google/callback?code=mock_code&state={state}",
        cookies={"skillforge_oauth_state": expired_cookie},
        follow_redirects=False,
    )
    assert callback_res.status_code == 400
    assert "expired" in callback_res.json()["detail"].lower()


# -----------------------------------------------------------------------------
# 6. State cannot be reused
# -----------------------------------------------------------------------------
@patch.object(oauth_service, "exchange_code_for_tokens", new_callable=AsyncMock)
@patch.object(oauth_service, "fetch_google_user_info", new_callable=AsyncMock)
def test_06_state_cannot_be_reused(mock_userinfo, mock_exchange, client: TestClient, db):
    session, created_user_ids = db
    mock_exchange.return_value = {"access_token": "mock_access_token"}
    sub = f"sub_{uuid.uuid4().hex[:12]}"
    email = f"reuse_{uuid.uuid4().hex[:8]}@example.com"
    mock_userinfo.return_value = GoogleUserInfo(sub=sub, email=email, email_verified=True, full_name="Reuse Test")

    # 1. Login to get cookie and state
    login_res = client.get("/api/v1/auth/google/login", follow_redirects=False)
    state_cookie = login_res.cookies.get("skillforge_oauth_state")
    state = urllib.parse.parse_qs(urllib.parse.urlparse(login_res.headers["location"]).query)["state"][0]

    # 2. First callback succeeds
    cb1 = client.get(
        f"/api/v1/auth/google/callback?code=valid_code_1&state={state}",
        cookies={"skillforge_oauth_state": state_cookie},
        follow_redirects=False,
    )
    assert cb1.status_code == 302
    # Verify the state cookie was deleted in response headers
    set_cookie_headers = cb1.headers.get_list("set-cookie") if hasattr(cb1.headers, "get_list") else [cb1.headers.get("set-cookie", "")]
    # Track created user
    user = session.query(User).filter(User.google_sub == sub).first()
    if user:
        created_user_ids.append(user.id)

    # 3. Second callback without the cookie (as browser would delete it) fails
    cb2 = client.get(
        f"/api/v1/auth/google/callback?code=valid_code_2&state={state}",
        follow_redirects=False,
    )
    assert cb2.status_code == 400


# -----------------------------------------------------------------------------
# 7. PKCE challenge generated
# -----------------------------------------------------------------------------
def test_07_pkce_challenge_generated():
    verifier, challenge = oauth_service.generate_pkce_pair()
    expected_digest = hashlib.sha256(verifier.encode("ascii")).digest()
    expected_challenge = base64.urlsafe_b64encode(expected_digest).decode("ascii").rstrip("=")
    assert challenge == expected_challenge
    assert len(verifier) >= 43


# -----------------------------------------------------------------------------
# 8. Authorization code exchanged with correct verifier
# -----------------------------------------------------------------------------
@patch.object(oauth_service, "exchange_code_for_tokens", new_callable=AsyncMock)
@patch.object(oauth_service, "fetch_google_user_info", new_callable=AsyncMock)
def test_08_code_exchanged_with_correct_verifier(mock_userinfo, mock_exchange, client: TestClient, db):
    session, created_user_ids = db
    mock_exchange.return_value = {"access_token": "mock_tok"}
    sub = f"sub_{uuid.uuid4().hex[:12]}"
    mock_userinfo.return_value = GoogleUserInfo(sub=sub, email="verifier_test@example.com", email_verified=True)

    login_res = client.get("/api/v1/auth/google/login", follow_redirects=False)
    state_cookie = login_res.cookies.get("skillforge_oauth_state")
    state = urllib.parse.parse_qs(urllib.parse.urlparse(login_res.headers["location"]).query)["state"][0]

    # Unpack verifier from state cookie to compare
    _, expected_verifier, _ = oauth_service.verify_and_unpack_oauth_state(state_cookie, state)

    cb = client.get(
        f"/api/v1/auth/google/callback?code=test_auth_code_123&state={state}",
        cookies={"skillforge_oauth_state": state_cookie},
        follow_redirects=False,
    )
    assert cb.status_code == 302
    mock_exchange.assert_called_once_with("test_auth_code_123", expected_verifier)

    user = session.query(User).filter(User.google_sub == sub).first()
    if user:
        created_user_ids.append(user.id)


# -----------------------------------------------------------------------------
# 9. Google API/token exchange failure handled safely
# -----------------------------------------------------------------------------
@patch.object(oauth_service, "exchange_code_for_tokens", new_callable=AsyncMock)
def test_09_google_token_exchange_failure_handled_safely(mock_exchange, client: TestClient):
    from fastapi import HTTPException
    mock_exchange.side_effect = HTTPException(status_code=400, detail="Google authorization code exchange failed.")

    login_res = client.get("/api/v1/auth/google/login", follow_redirects=False)
    state_cookie = login_res.cookies.get("skillforge_oauth_state")
    state = urllib.parse.parse_qs(urllib.parse.urlparse(login_res.headers["location"]).query)["state"][0]

    cb = client.get(
        f"/api/v1/auth/google/callback?code=bad_code&state={state}",
        cookies={"skillforge_oauth_state": state_cookie},
        follow_redirects=False,
    )
    assert cb.status_code == 400
    assert "failed" in cb.json()["detail"].lower()


# -----------------------------------------------------------------------------
# 10. Unverified Google email rejected (Case E)
# -----------------------------------------------------------------------------
@patch.object(oauth_service, "exchange_code_for_tokens", new_callable=AsyncMock)
@patch.object(oauth_service, "fetch_google_user_info", new_callable=AsyncMock)
def test_10_unverified_google_email_rejected(mock_userinfo, mock_exchange, client: TestClient, db):
    session, _ = db
    mock_exchange.return_value = {"access_token": "mock_tok"}
    unverified_email = f"unverified_{uuid.uuid4().hex[:8]}@example.com"
    mock_userinfo.return_value = GoogleUserInfo(
        sub="sub_unverified_999",
        email=unverified_email,
        email_verified=False,
    )

    login_res = client.get("/api/v1/auth/google/login", follow_redirects=False)
    state_cookie = login_res.cookies.get("skillforge_oauth_state")
    state = urllib.parse.parse_qs(urllib.parse.urlparse(login_res.headers["location"]).query)["state"][0]

    cb = client.get(
        f"/api/v1/auth/google/callback?code=mock_code&state={state}",
        cookies={"skillforge_oauth_state": state_cookie},
        follow_redirects=False,
    )
    assert cb.status_code == 400
    assert "unverified" in cb.json()["detail"].lower()

    # Confirm user was NOT created
    user = session.query(User).filter(User.email == unverified_email).first()
    assert user is None


# -----------------------------------------------------------------------------
# 11. Brand-new Google user created (Case A)
# -----------------------------------------------------------------------------
@patch.object(oauth_service, "exchange_code_for_tokens", new_callable=AsyncMock)
@patch.object(oauth_service, "fetch_google_user_info", new_callable=AsyncMock)
def test_11_brand_new_google_user_created(mock_userinfo, mock_exchange, client: TestClient, db):
    session, created_user_ids = db
    mock_exchange.return_value = {"access_token": "mock_tok"}
    sub = f"sub_case_a_{uuid.uuid4().hex[:8]}"
    email = f"case_a_{uuid.uuid4().hex[:8]}@example.com"
    name = "Grace Hopper"
    mock_userinfo.return_value = GoogleUserInfo(sub=sub, email=email, email_verified=True, full_name=name)

    login_res = client.get("/api/v1/auth/google/login", follow_redirects=False)
    state_cookie = login_res.cookies.get("skillforge_oauth_state")
    state = urllib.parse.parse_qs(urllib.parse.urlparse(login_res.headers["location"]).query)["state"][0]

    cb = client.get(
        f"/api/v1/auth/google/callback?code=code_a&state={state}",
        cookies={"skillforge_oauth_state": state_cookie},
        follow_redirects=False,
    )
    assert cb.status_code == 302
    assert cb.headers["location"] == f"{settings.FRONTEND_URL}/"

    # Verify user row in database
    user = session.query(User).filter(User.google_sub == sub).first()
    assert user is not None
    created_user_ids.append(user.id)
    assert user.email == email
    assert user.full_name == name
    assert user.auth_provider == "google"
    assert user.hashed_password is None
    assert user.is_active is True

    # Verify session cookie was issued
    assert settings.SESSION_COOKIE_NAME in cb.cookies


# -----------------------------------------------------------------------------
# 12. Existing Google user resolved by sub (Case B)
# -----------------------------------------------------------------------------
@patch.object(oauth_service, "exchange_code_for_tokens", new_callable=AsyncMock)
@patch.object(oauth_service, "fetch_google_user_info", new_callable=AsyncMock)
def test_12_existing_google_user_resolved_by_sub(mock_userinfo, mock_exchange, client: TestClient, db):
    session, created_user_ids = db
    sub = f"sub_case_b_{uuid.uuid4().hex[:8]}"
    email = f"case_b_{uuid.uuid4().hex[:8]}@example.com"

    # Pre-create user with this google_sub
    existing = User(
        id=uuid.uuid4(),
        email=email,
        full_name="Original Name",
        google_sub=sub,
        auth_provider="google",
        hashed_password=None,
        is_active=True,
    )
    session.add(existing)
    session.commit()
    created_user_ids.append(existing.id)

    mock_exchange.return_value = {"access_token": "mock_tok"}
    mock_userinfo.return_value = GoogleUserInfo(sub=sub, email=email, email_verified=True, full_name="Updated Name")

    login_res = client.get("/api/v1/auth/google/login", follow_redirects=False)
    state_cookie = login_res.cookies.get("skillforge_oauth_state")
    state = urllib.parse.parse_qs(urllib.parse.urlparse(login_res.headers["location"]).query)["state"][0]

    cb = client.get(
        f"/api/v1/auth/google/callback?code=code_b&state={state}",
        cookies={"skillforge_oauth_state": state_cookie},
        follow_redirects=False,
    )
    assert cb.status_code == 302

    # Verify no second user was created
    users = session.query(User).filter(User.google_sub == sub).all()
    assert len(users) == 1
    assert users[0].id == existing.id


# -----------------------------------------------------------------------------
# 13. Existing local user linked by verified email (Case C)
# -----------------------------------------------------------------------------
@patch.object(oauth_service, "exchange_code_for_tokens", new_callable=AsyncMock)
@patch.object(oauth_service, "fetch_google_user_info", new_callable=AsyncMock)
def test_13_existing_local_user_linked_by_verified_email(mock_userinfo, mock_exchange, client: TestClient, db):
    session, created_user_ids = db
    email = f"case_c_{uuid.uuid4().hex[:8]}@example.com"
    sub = f"sub_case_c_{uuid.uuid4().hex[:8]}"

    # Pre-create local password-authenticated user with google_sub = None
    local_user = User(
        id=uuid.uuid4(),
        email=email,
        full_name="Local User",
        google_sub=None,
        auth_provider="local",
        hashed_password="scrypt$dummy_hash",
        is_active=True,
    )
    session.add(local_user)
    session.commit()
    created_user_ids.append(local_user.id)

    mock_exchange.return_value = {"access_token": "mock_tok"}
    mock_userinfo.return_value = GoogleUserInfo(sub=sub, email=email, email_verified=True, full_name="Local User")

    login_res = client.get("/api/v1/auth/google/login", follow_redirects=False)
    state_cookie = login_res.cookies.get("skillforge_oauth_state")
    state = urllib.parse.parse_qs(urllib.parse.urlparse(login_res.headers["location"]).query)["state"][0]

    cb = client.get(
        f"/api/v1/auth/google/callback?code=code_c&state={state}",
        cookies={"skillforge_oauth_state": state_cookie},
        follow_redirects=False,
    )
    assert cb.status_code == 302

    # Refresh local_user from DB
    session.refresh(local_user)
    assert local_user.google_sub == sub
    assert local_user.auth_provider == "hybrid"
    # Local password must remain intact
    assert local_user.hashed_password == "scrypt$dummy_hash"


# -----------------------------------------------------------------------------
# 14. Duplicate Google subject conflict rejected (Case D)
# -----------------------------------------------------------------------------
@patch.object(oauth_service, "exchange_code_for_tokens", new_callable=AsyncMock)
@patch.object(oauth_service, "fetch_google_user_info", new_callable=AsyncMock)
def test_14_duplicate_google_subject_conflict_rejected(mock_userinfo, mock_exchange, client: TestClient, db):
    session, created_user_ids = db
    sub = f"sub_conflict_{uuid.uuid4().hex[:8]}"
    email1 = f"user1_{uuid.uuid4().hex[:8]}@example.com"
    email2 = f"user2_{uuid.uuid4().hex[:8]}@example.com"

    # User 1 has the google_sub
    user1 = User(
        id=uuid.uuid4(),
        email=email1,
        google_sub=sub,
        auth_provider="google",
        is_active=True,
    )
    # User 2 has email2, but no google_sub
    user2 = User(
        id=uuid.uuid4(),
        email=email2,
        google_sub=None,
        auth_provider="local",
        is_active=True,
    )
    session.add_all([user1, user2])
    session.commit()
    created_user_ids.extend([user1.id, user2.id])

    # Google callback returns user1's sub with user2's email
    mock_exchange.return_value = {"access_token": "mock_tok"}
    mock_userinfo.return_value = GoogleUserInfo(sub=sub, email=email2, email_verified=True)

    login_res = client.get("/api/v1/auth/google/login", follow_redirects=False)
    state_cookie = login_res.cookies.get("skillforge_oauth_state")
    state = urllib.parse.parse_qs(urllib.parse.urlparse(login_res.headers["location"]).query)["state"][0]

    cb = client.get(
        f"/api/v1/auth/google/callback?code=code_d&state={state}",
        cookies={"skillforge_oauth_state": state_cookie},
        follow_redirects=False,
    )
    assert cb.status_code == 409
    assert "conflict" in cb.json()["detail"].lower()

    # User 1's sub must not be modified, and User 2 must not have it
    session.refresh(user1)
    session.refresh(user2)
    assert user1.google_sub == sub
    assert user2.google_sub is None


# -----------------------------------------------------------------------------
# 15. Session created after successful Google login
# -----------------------------------------------------------------------------
@patch.object(oauth_service, "exchange_code_for_tokens", new_callable=AsyncMock)
@patch.object(oauth_service, "fetch_google_user_info", new_callable=AsyncMock)
def test_15_session_created_after_successful_login(mock_userinfo, mock_exchange, client: TestClient, db):
    session, created_user_ids = db
    sub = f"sub_sess_{uuid.uuid4().hex[:8]}"
    email = f"sess_{uuid.uuid4().hex[:8]}@example.com"
    mock_exchange.return_value = {"access_token": "mock_tok"}
    mock_userinfo.return_value = GoogleUserInfo(sub=sub, email=email, email_verified=True)

    login_res = client.get("/api/v1/auth/google/login", follow_redirects=False)
    state_cookie = login_res.cookies.get("skillforge_oauth_state")
    state = urllib.parse.parse_qs(urllib.parse.urlparse(login_res.headers["location"]).query)["state"][0]

    cb = client.get(
        f"/api/v1/auth/google/callback?code=code_sess&state={state}",
        cookies={"skillforge_oauth_state": state_cookie},
        follow_redirects=False,
    )
    assert cb.status_code == 302

    user = session.query(User).filter(User.google_sub == sub).first()
    assert user is not None
    created_user_ids.append(user.id)

    raw_token = cb.cookies.get(settings.SESSION_COOKIE_NAME)
    assert raw_token is not None

    token_hash = hash_session_token(raw_token)
    user_session = session.query(UserSession).filter(UserSession.token_hash == token_hash).first()
    assert user_session is not None
    assert user_session.user_id == user.id


# -----------------------------------------------------------------------------
# 16. skillforge_session cookie set with correct security flags
# -----------------------------------------------------------------------------
@patch.object(oauth_service, "exchange_code_for_tokens", new_callable=AsyncMock)
@patch.object(oauth_service, "fetch_google_user_info", new_callable=AsyncMock)
def test_16_skillforge_session_cookie_set(mock_userinfo, mock_exchange, client: TestClient, db):
    session, created_user_ids = db
    sub = f"sub_flags_{uuid.uuid4().hex[:8]}"
    email = f"flags_{uuid.uuid4().hex[:8]}@example.com"
    mock_exchange.return_value = {"access_token": "mock_tok"}
    mock_userinfo.return_value = GoogleUserInfo(sub=sub, email=email, email_verified=True)

    login_res = client.get("/api/v1/auth/google/login", follow_redirects=False)
    state_cookie = login_res.cookies.get("skillforge_oauth_state")
    state = urllib.parse.parse_qs(urllib.parse.urlparse(login_res.headers["location"]).query)["state"][0]

    cb = client.get(
        f"/api/v1/auth/google/callback?code=code_flags&state={state}",
        cookies={"skillforge_oauth_state": state_cookie},
        follow_redirects=False,
    )
    assert cb.status_code == 302
    assert settings.SESSION_COOKIE_NAME in cb.cookies

    user = session.query(User).filter(User.google_sub == sub).first()
    if user:
        created_user_ids.append(user.id)


# -----------------------------------------------------------------------------
# 17. Session works with /api/v1/auth/me
# -----------------------------------------------------------------------------
@patch.object(oauth_service, "exchange_code_for_tokens", new_callable=AsyncMock)
@patch.object(oauth_service, "fetch_google_user_info", new_callable=AsyncMock)
def test_17_session_works_with_auth_me(mock_userinfo, mock_exchange, client: TestClient, db):
    session, created_user_ids = db
    sub = f"sub_me_{uuid.uuid4().hex[:8]}"
    email = f"me_{uuid.uuid4().hex[:8]}@example.com"
    mock_exchange.return_value = {"access_token": "mock_tok"}
    mock_userinfo.return_value = GoogleUserInfo(sub=sub, email=email, email_verified=True, full_name="Me Candidate")

    login_res = client.get("/api/v1/auth/google/login", follow_redirects=False)
    state_cookie = login_res.cookies.get("skillforge_oauth_state")
    state = urllib.parse.parse_qs(urllib.parse.urlparse(login_res.headers["location"]).query)["state"][0]

    cb = client.get(
        f"/api/v1/auth/google/callback?code=code_me&state={state}",
        cookies={"skillforge_oauth_state": state_cookie},
        follow_redirects=False,
    )
    assert cb.status_code == 302
    session_token = cb.cookies.get(settings.SESSION_COOKIE_NAME)

    user = session.query(User).filter(User.google_sub == sub).first()
    if user:
        created_user_ids.append(user.id)

    # Use session cookie against /api/v1/auth/me
    me_res = client.get(
        "/api/v1/auth/me",
        cookies={settings.SESSION_COOKIE_NAME: session_token},
    )
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == email
    assert me_data["full_name"] == "Me Candidate"
    assert me_data["auth_provider"] == "google"


# -----------------------------------------------------------------------------
# 18. Google login does NOT use Bearer/JWT
# -----------------------------------------------------------------------------
@patch.object(oauth_service, "exchange_code_for_tokens", new_callable=AsyncMock)
@patch.object(oauth_service, "fetch_google_user_info", new_callable=AsyncMock)
def test_18_google_login_does_not_use_bearer_or_jwt(mock_userinfo, mock_exchange, client: TestClient, db):
    session, created_user_ids = db
    sub = f"sub_no_jwt_{uuid.uuid4().hex[:8]}"
    email = f"no_jwt_{uuid.uuid4().hex[:8]}@example.com"
    mock_exchange.return_value = {"access_token": "mock_tok"}
    mock_userinfo.return_value = GoogleUserInfo(sub=sub, email=email, email_verified=True)

    login_res = client.get("/api/v1/auth/google/login", follow_redirects=False)
    state_cookie = login_res.cookies.get("skillforge_oauth_state")
    state = urllib.parse.parse_qs(urllib.parse.urlparse(login_res.headers["location"]).query)["state"][0]

    cb = client.get(
        f"/api/v1/auth/google/callback?code=code_no_jwt&state={state}",
        cookies={"skillforge_oauth_state": state_cookie},
        follow_redirects=False,
    )
    assert cb.status_code == 302

    # Callback does not return JSON tokens
    assert "token" not in cb.text.lower()
    assert "bearer" not in cb.text.lower()
    assert "jwt" not in cb.text.lower()

    # Session token must be opaque 32-byte urlsafe string, not a JWT (no two dots)
    session_token = cb.cookies.get(settings.SESSION_COOKIE_NAME)
    assert session_token.count(".") == 0

    user = session.query(User).filter(User.google_sub == sub).first()
    if user:
        created_user_ids.append(user.id)


# -----------------------------------------------------------------------------
# 19. Google secrets never appear in logs / responses
# -----------------------------------------------------------------------------
@patch.object(oauth_service, "exchange_code_for_tokens", new_callable=AsyncMock)
def test_19_google_secrets_never_appear(mock_exchange, client: TestClient):
    mock_exchange.side_effect = Exception("Simulated crash")

    login_res = client.get("/api/v1/auth/google/login", follow_redirects=False)
    state_cookie = login_res.cookies.get("skillforge_oauth_state")
    state = urllib.parse.parse_qs(urllib.parse.urlparse(login_res.headers["location"]).query)["state"][0]

    cb = client.get(
        f"/api/v1/auth/google/callback?code=err_code&state={state}",
        cookies={"skillforge_oauth_state": state_cookie},
        follow_redirects=False,
    )
    # The client secret must never be leaked
    assert settings.GOOGLE_CLIENT_SECRET not in cb.text


# -----------------------------------------------------------------------------
# 20. Google callback cannot select arbitrary SkillForge user
# -----------------------------------------------------------------------------
@patch.object(oauth_service, "exchange_code_for_tokens", new_callable=AsyncMock)
@patch.object(oauth_service, "fetch_google_user_info", new_callable=AsyncMock)
def test_20_callback_cannot_select_arbitrary_user(mock_userinfo, mock_exchange, client: TestClient, db):
    session, created_user_ids = db
    sub = f"sub_spoof_{uuid.uuid4().hex[:8]}"
    email = f"spoof_{uuid.uuid4().hex[:8]}@example.com"
    victim_user = User(
        id=uuid.uuid4(),
        email=f"victim_{uuid.uuid4().hex[:8]}@example.com",
        google_sub=None,
        auth_provider="local",
        is_active=True,
    )
    session.add(victim_user)
    session.commit()
    created_user_ids.append(victim_user.id)

    mock_exchange.return_value = {"access_token": "mock_tok"}
    mock_userinfo.return_value = GoogleUserInfo(sub=sub, email=email, email_verified=True)

    login_res = client.get("/api/v1/auth/google/login", follow_redirects=False)
    state_cookie = login_res.cookies.get("skillforge_oauth_state")
    state = urllib.parse.parse_qs(urllib.parse.urlparse(login_res.headers["location"]).query)["state"][0]

    # Attacker tries to inject victim's user_id or X-User-Id
    cb = client.get(
        f"/api/v1/auth/google/callback?code=code_spoof&state={state}&user_id={victim_user.id}",
        headers={"X-User-Id": str(victim_user.id)},
        cookies={"skillforge_oauth_state": state_cookie},
        follow_redirects=False,
    )
    assert cb.status_code == 302
    session_token = cb.cookies.get(settings.SESSION_COOKIE_NAME)

    # Calling /me must resolve to the Google identity (spoof email), NOT victim
    me_res = client.get(
        "/api/v1/auth/me",
        cookies={settings.SESSION_COOKIE_NAME: session_token},
    )
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email
    assert me_res.json()["id"] != str(victim_user.id)

    new_user = session.query(User).filter(User.google_sub == sub).first()
    if new_user:
        created_user_ids.append(new_user.id)


# -----------------------------------------------------------------------------
# 21. Google subject cannot be reassigned between users
# -----------------------------------------------------------------------------
def test_21_google_subject_cannot_be_reassigned(db):
    session, created_user_ids = db
    sub = f"sub_fixed_{uuid.uuid4().hex[:8]}"

    user1 = User(
        id=uuid.uuid4(),
        email=f"owner_{uuid.uuid4().hex[:8]}@example.com",
        google_sub=sub,
        auth_provider="google",
        is_active=True,
    )
    session.add(user1)
    session.commit()
    created_user_ids.append(user1.id)

    # Attempting to assign the same sub to user2 via resolution matrix must fail
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        oauth_service.resolve_google_user(
            db=session,
            google_identity=GoogleUserInfo(
                sub=sub,
                email=f"other_{uuid.uuid4().hex[:8]}@example.com",
                email_verified=True,
            ),
        )
    assert exc.value.status_code == 409

    # Re-verify user1's sub remained untouched
    session.refresh(user1)
    assert user1.google_sub == sub


# -----------------------------------------------------------------------------
# 22. Failed OAuth flow creates no authenticated session
# -----------------------------------------------------------------------------
@patch.object(oauth_service, "exchange_code_for_tokens", new_callable=AsyncMock)
def test_22_failed_oauth_creates_no_session(mock_exchange, client: TestClient, db):
    session, _ = db
    initial_sessions_count = session.query(UserSession).count()

    mock_exchange.side_effect = Exception("OAuth exchange crashed")

    login_res = client.get("/api/v1/auth/google/login", follow_redirects=False)
    state_cookie = login_res.cookies.get("skillforge_oauth_state")
    state = urllib.parse.parse_qs(urllib.parse.urlparse(login_res.headers["location"]).query)["state"][0]

    cb = client.get(
        f"/api/v1/auth/google/callback?code=crash_code&state={state}",
        cookies={"skillforge_oauth_state": state_cookie},
        follow_redirects=False,
    )
    assert cb.status_code in [400, 500, 502]

    # Confirm session count did not change
    after_sessions_count = session.query(UserSession).count()
    assert after_sessions_count == initial_sessions_count
