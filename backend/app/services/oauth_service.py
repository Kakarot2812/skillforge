"""Google OAuth 2.0 service implementing Authorization Code Flow with PKCE,
HMAC-SHA256 signed state protection, identity validation, and account resolution.
"""

import base64
from dataclasses import dataclass
import hashlib
import hmac
import json
import secrets
import time
from typing import Optional, Tuple
import urllib.parse
import uuid

from fastapi import HTTPException, status
import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import User


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

OAUTH_STATE_TTL_SECONDS = 600  # 10 minutes


@dataclass(frozen=True)
class GoogleUserInfo:
    """Strongly typed, validated identity payload from Google."""
    sub: str
    email: str
    email_verified: bool
    full_name: Optional[str] = None


class OAuthService:
    """Encapsulates PKCE, state signing, Google token exchange, and account resolution."""

    def is_configured(self) -> bool:
        """Returns True if Google OAuth credentials are configured."""
        return bool(
            settings.GOOGLE_CLIENT_ID
            and settings.GOOGLE_CLIENT_ID.strip()
            and settings.GOOGLE_CLIENT_SECRET
            and settings.GOOGLE_CLIENT_SECRET.strip()
        )

    def generate_pkce_pair(self) -> Tuple[str, str]:
        """
        Generates a PKCE code_verifier (high-entropy cryptographic random string)
        and derives its code_challenge using SHA-256 and Base64URL encoding without padding.
        """
        # 48 bytes urlsafe produces ~64 base64 characters, satisfying RFC 7636 (43-128 chars)
        verifier = secrets.token_urlsafe(48)
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
        return verifier, challenge

    def generate_state(self) -> str:
        """Generates a cryptographically random OAuth state token."""
        return secrets.token_urlsafe(32)

    def create_oauth_state_cookie(self, state: str, code_verifier: str) -> str:
        """
        Serializes and HMAC-SHA256 signs the OAuth transaction state, code verifier, and timestamp.
        Returns a tamper-proof string suitable for an HTTP-only secure cookie.
        Format: <base64url_payload>.<hex_signature>
        """
        payload = {
            "state": state,
            "verifier": code_verifier,
            "iat": int(time.time()),
        }
        payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        b64_payload = base64.urlsafe_b64encode(payload_bytes).decode("ascii").rstrip("=")

        signature = hmac.new(
            settings.SECRET_KEY.encode("utf-8"),
            b64_payload.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()

        return f"{b64_payload}.{signature}"

    def verify_and_unpack_oauth_state(
        self,
        cookie_value: Optional[str],
        incoming_state: str,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validates the signed state cookie:
        1. Verifies HMAC-SHA256 signature using constant-time comparison.
        2. Validates timestamp against TTL (600s).
        3. Validates that incoming query parameter state exactly matches the state in cookie.

        Returns: (is_valid, code_verifier, error_message)
        """
        if not cookie_value or not cookie_value.strip():
            return False, None, "Missing OAuth state cookie."

        parts = cookie_value.strip().split(".")
        if len(parts) != 2:
            return False, None, "Invalid OAuth state cookie format."

        b64_payload, signature = parts[0], parts[1]

        expected_sig = hmac.new(
            settings.SECRET_KEY.encode("utf-8"),
            b64_payload.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            return False, None, "Tampered or invalid OAuth state signature."

        try:
            # Restore padding if needed
            pad = len(b64_payload) % 4
            padded = b64_payload + ("=" * (4 - pad) if pad else "")
            payload_json = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
            data = json.loads(payload_json)
        except Exception:
            return False, None, "Corrupted OAuth state payload."

        cookie_state = data.get("state")
        verifier = data.get("verifier")
        iat = data.get("iat", 0)

        if not cookie_state or not verifier:
            return False, None, "Incomplete OAuth state payload."

        now = int(time.time())
        if now - iat > OAUTH_STATE_TTL_SECONDS:
            return False, None, "OAuth state transaction has expired."

        if not hmac.compare_digest(cookie_state, incoming_state):
            return False, None, "OAuth state parameter mismatch."

        return True, verifier, None

    def get_authorization_url(self, state: str, code_challenge: str) -> str:
        """Constructs the Google OAuth 2.0 authorization redirect URL with PKCE and state."""
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID or "",
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "access_type": "online",
            "prompt": "select_account",
        }
        return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"

    async def exchange_code_for_tokens(
        self,
        code: str,
        code_verifier: str,
    ) -> dict:
        """
        Exchanges the authorization code and PKCE code_verifier for Google OAuth tokens.
        Raises HTTPException on network failure or invalid grant.
        """
        if not self.is_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google OAuth is not configured.",
            )

        payload = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "code": code,
            "code_verifier": code_verifier,
            "grant_type": "authorization_code",
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    GOOGLE_TOKEN_URL,
                    data=payload,
                    headers={"Accept": "application/json"},
                )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to communicate with Google authentication servers.",
            )

        if res.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google authorization code exchange failed.",
            )

        try:
            tokens = res.json()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Invalid response payload from Google token endpoint.",
            )

        return tokens

    async def fetch_google_user_info(
        self,
        access_token: str,
        id_token_hint: Optional[str] = None,
    ) -> GoogleUserInfo:
        """
        Fetches and validates candidate identity from Google's OpenID Connect userinfo endpoint.
        Verifies subject, email, and email_verified.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(
                    GOOGLE_USERINFO_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to fetch candidate profile from Google.",
            )

        if res.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google identity verification failed.",
            )

        try:
            data = res.json()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Invalid profile data received from Google.",
            )

        sub = str(data.get("sub", "")).strip()
        email = str(data.get("email", "")).strip().lower()
        email_verified = bool(data.get("email_verified", False))
        name = data.get("name")
        if name and isinstance(name, str):
            name = name.strip() or None

        if not sub:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google identity missing subject identifier.",
            )

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google identity missing email address.",
            )

        return GoogleUserInfo(
            sub=sub,
            email=email,
            email_verified=email_verified,
            full_name=name,
        )

    def resolve_google_user(
        self,
        db: Session,
        google_identity: GoogleUserInfo,
    ) -> User:
        """
        Implements the Account Resolution Matrix (Cases A - E):
        - Case E: Unverified email -> HTTP 400 Bad Request
        - Case B: Existing Google user by google_sub -> Return user
        - Case D: Subject conflict -> HTTP 409 Conflict
        - Case C: Existing local user with verified matching email -> Safely link and update auth_provider="hybrid"
        - Case A: Brand-new Google user -> Create new user with auth_provider="google"
        """
        # CASE E: Unverified Google Email
        if not google_identity.email_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unverified Google accounts are not permitted for authentication.",
            )

        normalized_email = google_identity.email.strip().lower()

        # Check if google_sub already exists in the database
        user_by_sub = (
            db.query(User)
            .filter(User.google_sub == google_identity.sub)
            .first()
        )

        # Check if email exists in the database
        user_by_email = (
            db.query(User)
            .filter(User.email == normalized_email)
            .first()
        )

        # CASE D: Subject Conflict
        # 1. If google_sub belongs to an existing user, but incoming email does not match that user
        if user_by_sub and user_by_sub.email != normalized_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Google identity conflict: already linked to another SkillForge account.",
            )

        # 2. If incoming email belongs to a user that already has a DIFFERENT google_sub
        if user_by_email and user_by_email.google_sub is not None and user_by_email.google_sub != google_identity.sub:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Google identity conflict: already linked to another SkillForge account.",
            )

        # CASE B: Existing Google User
        if user_by_sub:
            if not user_by_sub.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User account is inactive.",
                )
            return user_by_sub

        # CASE C: Existing Local Account With Same Verified Email
        if user_by_email:
            if not user_by_email.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User account is inactive.",
                )

            # Safely associate Google subject and mark as hybrid
            user_by_email.google_sub = google_identity.sub
            user_by_email.auth_provider = "hybrid"
            db.commit()
            db.refresh(user_by_email)
            return user_by_email

        # CASE A: Brand New Google User
        new_user = User(
            id=uuid.uuid4(),
            email=normalized_email,
            full_name=google_identity.full_name,
            target_role=None,
            hashed_password=None,
            google_sub=google_identity.sub,
            auth_provider="google",
            is_active=True,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user


oauth_service = OAuthService()
