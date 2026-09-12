"""Core security utilities: password hashing via standard-library hashlib.scrypt,
constant-time comparison, timing-attack mitigation, and session token generation/hashing.
"""

import base64
import hashlib
import hmac
import os
import secrets
import unicodedata
from typing import Optional

# Standard scrypt parameters recommended for modern interactive logins
SCRYPT_N = 16384
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_MAXMEM = 0  # Python default / unrestricted
SALT_BYTES = 16
KEY_LEN = 64

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128


def normalize_password(password: str) -> str:
    """Normalizes password string using Unicode NFKC form."""
    return unicodedata.normalize("NFKC", password)


def validate_password_length(password: str) -> None:
    """Validates that password meets length boundaries. Raises ValueError on violation."""
    norm = normalize_password(password)
    if len(norm) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long.")
    if len(norm) > MAX_PASSWORD_LENGTH:
        raise ValueError(f"Password cannot exceed {MAX_PASSWORD_LENGTH} characters.")


def hash_password(password: str) -> str:
    """
    Hashes a password using standard-library hashlib.scrypt with a cryptographically
    random 16-byte salt. Returns a serialized string containing parameters, salt, and hash.
    Format: scrypt$<n>$<r>$<p>$<salt_b64>$<hash_b64>
    """
    norm = normalize_password(password)
    salt = os.urandom(SALT_BYTES)
    derived = hashlib.scrypt(
        norm.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        maxmem=SCRYPT_MAXMEM,
        dklen=KEY_LEN,
    )
    salt_b64 = base64.b64encode(salt).decode("ascii")
    hash_b64 = base64.b64encode(derived).decode("ascii")
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt_b64}${hash_b64}"


def verify_password(plain_password: str, hashed_password: Optional[str]) -> bool:
    """
    Verifies a plain-text password against a serialized scrypt hash using constant-time comparison.
    Returns False if hash format is invalid or password does not match.
    """
    if not hashed_password or not plain_password:
        return False

    try:
        parts = hashed_password.split("$")
        if len(parts) != 6 or parts[0] != "scrypt":
            return False

        n = int(parts[1])
        r = int(parts[2])
        p = int(parts[3])
        salt = base64.b64decode(parts[4].encode("ascii"))
        stored_hash = base64.b64decode(parts[5].encode("ascii"))

        norm = normalize_password(plain_password)
        derived = hashlib.scrypt(
            norm.encode("utf-8"),
            salt=salt,
            n=n,
            r=r,
            p=p,
            maxmem=SCRYPT_MAXMEM,
            dklen=len(stored_hash),
        )
        return hmac.compare_digest(derived, stored_hash)
    except Exception:
        return False


# Precomputed static dummy hash to mitigate timing differences on nonexistent accounts
_DUMMY_SALT = b"\x00" * SALT_BYTES
_DUMMY_HASH = (
    f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}$"
    f"{base64.b64encode(_DUMMY_SALT).decode('ascii')}$"
    f"{base64.b64encode(hashlib.scrypt(b'dummy', salt=_DUMMY_SALT, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, maxmem=SCRYPT_MAXMEM, dklen=KEY_LEN)).decode('ascii')}"
)


def verify_dummy_password() -> None:
    """Executes a dummy scrypt verification to equalize timing for nonexistent users."""
    verify_password("dummy_password_timing_check", _DUMMY_HASH)


def generate_session_token() -> str:
    """Generates a cryptographically random, URL-safe opaque session token."""
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    """Hashes an opaque session token using SHA-256 for persistent database storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
