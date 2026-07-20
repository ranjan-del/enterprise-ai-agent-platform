"""Security helpers: password hashing (bcrypt) and JWT encode/decode.

- Passwords are hashed with bcrypt (slow + salted) and never stored in plaintext.
- Tokens are signed JWTs. Two kinds are issued:
    * access  (short-lived, sent on every request)
    * refresh (long-lived, used only to mint new access tokens)
  Each token carries the tenant (org) id plus a unique ``jti``.
"""

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

ACCESS = "access"
REFRESH = "refresh"

# bcrypt only considers the first 72 bytes of a password; truncate explicitly so
# longer inputs are handled predictably instead of raising.
_BCRYPT_MAX_BYTES = 72


def _to_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password with bcrypt (includes a random salt)."""
    return bcrypt.hashpw(_to_bytes(plain_password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if the plaintext matches the stored bcrypt hash."""
    try:
        return bcrypt.checkpw(_to_bytes(plain_password), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _create_token(
    subject: str, org_id: str, token_type: str, expires_delta: timedelta
) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(subject),          # user id
        "org": str(org_id),           # tenant id (multi-tenancy)
        "type": token_type,           # "access" | "refresh"
        "iat": int(now.timestamp()),
        "exp": now + expires_delta,   # jose serialises datetimes
        "jti": uuid.uuid4().hex,      # unique id -> enables revocation
    }
    return jwt.encode(claims, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_access_token(subject: str, org_id: str) -> str:
    """Issue a short-lived access token."""
    return _create_token(
        subject, org_id, ACCESS,
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(subject: str, org_id: str) -> str:
    """Issue a long-lived refresh token."""
    return _create_token(
        subject, org_id, REFRESH,
        timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES),
    )


def decode_token(token: str) -> dict:
    """Decode + validate a JWT (signature and expiry). Raises jose.JWTError."""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


__all__ = [
    "hash_password", "verify_password",
    "create_access_token", "create_refresh_token", "decode_token",
    "ACCESS", "REFRESH", "JWTError",
]
