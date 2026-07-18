"""Security helpers: password hashing + JWT issuance/verification.

TODO: checklist "Auth + multi-tenancy: JWT, organizations, users, roles".
This is a skeleton — no real crypto flow is wired yet.
"""
from datetime import datetime, timedelta, timezone

# from jose import jwt              # python-jose (declared in requirements.txt)
# from passlib.context import CryptContext  # passlib[bcrypt]

from app.core.config import settings

# TODO: pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash of the given password."""
    # TODO: return pwd_context.hash(plain_password)
    raise NotImplementedError("hash_password not implemented")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored hash."""
    # TODO: return pwd_context.verify(plain_password, hashed_password)
    raise NotImplementedError("verify_password not implemented")


def create_access_token(subject: str, org_id: str) -> str:
    """Issue a signed JWT carrying the user subject and tenant (org) id."""
    _expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    # TODO: payload = {"sub": subject, "org": org_id, "exp": _expire}
    # TODO: return jwt.encode(payload, settings.jwt_secret, settings.jwt_algorithm)
    raise NotImplementedError("create_access_token not implemented")


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT, returning its claims."""
    # TODO: return jwt.decode(token, settings.jwt_secret, [settings.jwt_algorithm])
    raise NotImplementedError("decode_access_token not implemented")
