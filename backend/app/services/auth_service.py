"""Authentication service orchestrating candidate registration, credential verification,
server-side session issuance, and session revocation.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import (
    generate_session_token,
    hash_password,
    hash_session_token,
    validate_password_length,
    verify_dummy_password,
    verify_password,
)
from app.db.models import User, UserSession
from app.schemas.auth import LoginRequest, SignupRequest


class AuthService:
    """Encapsulates business logic for authentication, password hashing, and session management."""

    def signup_user(self, db: Session, payload: SignupRequest) -> User:
        """
        Registers a new candidate with an email/password credential.
        Rejects duplicate accounts with 409 Conflict.
        Never converts or adops synthetic candidate accounts.
        """
        normalized_email = payload.email.strip().lower()

        # Check for existing account
        existing_user = db.query(User).filter(User.email == normalized_email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            )

        # Validate password boundaries
        try:
            validate_password_length(payload.password)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            )

        # Hash password and persist user
        hashed = hash_password(payload.password)
        new_user = User(
            id=uuid.uuid4(),
            email=normalized_email,
            hashed_password=hashed,
            full_name=payload.full_name,
            target_role=payload.target_role,
            auth_provider="local",
            is_active=True,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user

    def authenticate_user(self, db: Session, payload: LoginRequest) -> User:
        """
        Verifies candidate credentials against stored scrypt hash.
        Mitigates timing attacks for nonexistent accounts.
        Rejects inactive users and invalid passwords with 401.
        """
        normalized_email = payload.email.strip().lower()
        user = db.query(User).filter(User.email == normalized_email).first()

        if not user:
            verify_dummy_password()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive",
            )

        if not user.hashed_password:
            verify_dummy_password()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if not verify_password(payload.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        return user

    def create_session(
        self,
        db: Session,
        user: User,
        remember_me: bool = False,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[UserSession, str, int]:
        """
        Generates an opaque session token, hashes it with SHA-256 for persistent database storage,
        and returns the session record, raw token, and max_age in seconds.
        """
        days = settings.SESSION_REMEMBER_ME_DAYS if remember_me else settings.SESSION_LIFETIME_DAYS
        lifetime_seconds = days * 24 * 3600
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=lifetime_seconds)

        raw_token = generate_session_token()
        token_hash = hash_session_token(raw_token)

        session = UserSession(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=token_hash,
            created_at=now,
            expires_at=expires_at,
            last_seen_at=now,
            ip_address=ip_address[:45] if ip_address else None,
            user_agent=user_agent[:500] if user_agent else None,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        return session, raw_token, lifetime_seconds

    def revoke_session(self, db: Session, raw_token: Optional[str]) -> bool:
        """
        Revokes an active session by matching its SHA-256 token hash and deleting it from PostgreSQL.
        Safe and idempotent if session is already missing or expired.
        """
        if not raw_token or not raw_token.strip():
            return False

        token_hash = hash_session_token(raw_token.strip())
        deleted = (
            db.query(UserSession)
            .filter(UserSession.token_hash == token_hash)
            .delete(synchronize_session=False)
        )
        db.commit()
        return deleted > 0


auth_service = AuthService()
