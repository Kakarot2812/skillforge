"""Authentication API endpoints for candidate signup, login, logout, and current user profile."""

from fastapi import APIRouter, Depends, Request, Response, status
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
