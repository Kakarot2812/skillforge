"""FastAPI dependencies for request authentication and user verification."""

from datetime import datetime, timezone
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import hash_session_token
from app.db.database import get_db
from app.db.models import User, UserSession


def get_current_active_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """
    Server-authenticated current candidate dependency.
    Extracts the opaque session token from the secure HTTP-only cookie,
    hashes it with SHA-256, verifies existence and expiry in user_sessions,
    and checks User.is_active.

    CRITICAL SECURITY INVARIANTS:
    - Never trusts or inspects X-User-Id header.
    - Never trusts or inspects query parameter user_id.
    - Never inspects Bearer / Authorization headers.
    - Missing, invalid, expired, or inactive credentials strictly return HTTP 401.
    """
    raw_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not raw_token or not raw_token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: session cookie missing.",
        )

    token_hash = hash_session_token(raw_token.strip())
    now = datetime.now(timezone.utc)

    session_record = (
        db.query(UserSession)
        .filter(UserSession.token_hash == token_hash)
        .first()
    )

    if not session_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked session.",
        )

    # Check expiration
    if session_record.expires_at <= now:
        db.delete(session_record)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please log in again.",
        )

    # Load associated user
    user = db.query(User).filter(User.id == session_record.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Associated user not found.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive.",
        )

    return user


def get_optional_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Optional server-authenticated candidate dependency.
    If valid active session cookie is present, returns User.
    If missing, expired, or invalid, returns None (does not raise 401).
    """
    raw_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not raw_token or not raw_token.strip():
        return None

    token_hash = hash_session_token(raw_token.strip())
    now = datetime.now(timezone.utc)

    session_record = (
        db.query(UserSession)
        .filter(UserSession.token_hash == token_hash)
        .first()
    )
    if not session_record or session_record.expires_at <= now:
        return None

    user = db.query(User).filter(User.id == session_record.user_id).first()
    if not user or not user.is_active:
        return None

    return user
