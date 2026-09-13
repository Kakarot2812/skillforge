"""Authentication API endpoints for candidate signup, login, logout, and current user profile."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.config import settings
from app.db.database import get_db
from app.db.models import User
from app.schemas.auth import (
    LoginRequest,
    LogoutResponse,
    SignupRequest,
    UserAuthResponse,
)
from app.services.auth_service import auth_service
from app.services.oauth_service import oauth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/signup",
    response_model=UserAuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Candidate Signup with Email/Password",
    description=(
        "Registers a new candidate with an email and password credential, hashes the password via scrypt, "
        "issues a persistent server-side session, and sets a secure HTTP-only cookie."
    ),
)
def signup(
    payload: SignupRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> UserAuthResponse:
    """Registers a candidate and establishes an authenticated session."""
    user = auth_service.signup_user(db, payload)

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    _, raw_token, lifetime = auth_service.create_session(
        db=db,
        user=user,
        remember_me=False,
        ip_address=client_ip,
        user_agent=user_agent,
    )

    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=raw_token,
        max_age=lifetime,
        httponly=True,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        secure=settings.SESSION_COOKIE_SECURE,
        path="/",
    )

    return UserAuthResponse.model_validate(user)


@router.post(
    "/login",
    response_model=UserAuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Candidate Login with Email/Password",
    description=(
        "Authenticates a candidate using email and password, creates a new server-side session, "
        "and sets a secure HTTP-only cookie."
    ),
)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> UserAuthResponse:
    """Authenticates credentials and establishes a session cookie."""
    user = auth_service.authenticate_user(db, payload)

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    _, raw_token, lifetime = auth_service.create_session(
        db=db,
        user=user,
        remember_me=payload.remember_me,
        ip_address=client_ip,
        user_agent=user_agent,
    )

    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=raw_token,
        max_age=lifetime,
        httponly=True,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        secure=settings.SESSION_COOKIE_SECURE,
        path="/",
    )

    return UserAuthResponse.model_validate(user)


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Candidate Logout",
    description="Revokes the active server-side session from the database and clears the session cookie.",
)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> LogoutResponse:
    """Revokes the current session and clears the HTTP-only cookie."""
    raw_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    auth_service.revoke_session(db, raw_token)

    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite=settings.SESSION_COOKIE_SAMESITE,
    )
    return LogoutResponse(message="Logged out successfully")


@router.get(
    "/me",
    response_model=UserAuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Current Authenticated Candidate Profile",
    description="Returns the profile of the candidate authenticated by the HTTP-only session cookie.",
)
def get_me(
    current_user: User = Depends(get_current_active_user),
) -> UserAuthResponse:
    """Returns safe candidate profile fields for the authenticated session."""
    return UserAuthResponse.model_validate(current_user)


@router.get(
    "/google/login",
    summary="Initiate Google OAuth 2.0 Flow",
    description="Generates PKCE challenge and signed state, sets temporary state cookie, and redirects to Google.",
)
def google_login() -> Response:
    """Initiates backend-driven Google OAuth 2.0 authorization code flow with PKCE."""
    if not oauth_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured.",
        )

    state = oauth_service.generate_state()
    verifier, challenge = oauth_service.generate_pkce_pair()
    signed_cookie_val = oauth_service.create_oauth_state_cookie(state, verifier)

    auth_url = oauth_service.get_authorization_url(state, challenge)

    response = RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="skillforge_oauth_state",
        value=signed_cookie_val,
        max_age=600,
        httponly=True,
        samesite="lax",
        secure=settings.SESSION_COOKIE_SECURE,
        path="/",
    )
    return response


@router.get(
    "/google/callback",
    summary="Handle Google OAuth 2.0 Callback",
    description="Validates state and PKCE verifier, exchanges code, resolves candidate identity, and establishes session.",
)
async def google_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Response:
    """Processes Google OAuth callback, verifies identity, establishes server-side session, and redirects to application."""
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google OAuth error: {error}",
        )

    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required authorization code or state parameter.",
        )

    cookie_val = request.cookies.get("skillforge_oauth_state")
    is_valid, code_verifier, err_msg = oauth_service.verify_and_unpack_oauth_state(
        cookie_value=cookie_val,
        incoming_state=state,
    )

    if not is_valid or not code_verifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg or "Invalid or expired OAuth state transaction.",
        )

    try:
        # Exchange code for tokens
        tokens = await oauth_service.exchange_code_for_tokens(code, code_verifier)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to communicate with Google authentication servers.",
        )

    access_token = tokens.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google token exchange returned no access token.",
        )

    try:
        # Fetch and validate Google candidate identity
        google_identity = await oauth_service.fetch_google_user_info(access_token)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch candidate profile from Google.",
        )

    # Resolve or create candidate User (Cases A-E)
    user = oauth_service.resolve_google_user(db, google_identity)

    # Establish normal server-side session
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    _, raw_token, lifetime = auth_service.create_session(
        db=db,
        user=user,
        remember_me=True,  # SSO logins default to extended lifetime
        ip_address=client_ip,
        user_agent=user_agent,
    )

    # Redirect to application dashboard /
    response = RedirectResponse(
        url=f"{settings.FRONTEND_URL}/",
        status_code=status.HTTP_302_FOUND,
    )

    # Set normal skillforge_session cookie
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=raw_token,
        max_age=lifetime,
        httponly=True,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        secure=settings.SESSION_COOKIE_SECURE,
        path="/",
    )

    # Invalidate one-time state cookie immediately
    response.delete_cookie(
        key="skillforge_oauth_state",
        path="/",
        httponly=True,
        samesite="lax",
    )

    return response
