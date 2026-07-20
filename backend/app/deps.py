"""Shared FastAPI dependencies: current-user resolution and role guards.

- ``get_current_user`` decodes the bearer access token, loads the user, and
  makes the tenant (org) available for scoping.
- ``require_role(...)`` builds a dependency enforcing one of several roles.

401 = we don't know who you are; 403 = we know you, but you're not allowed.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import ACCESS, JWTError, decode_token
from app.db.session import get_db
from app.models.org import Org
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=False)

_credentials_error = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        raise _credentials_error
    try:
        payload = decode_token(token)
    except JWTError:
        raise _credentials_error
    if payload.get("type") != ACCESS:
        raise _credentials_error
    user_id = payload.get("sub")
    if user_id is None:
        raise _credentials_error
    user = db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise _credentials_error
    return user


def get_current_org(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Org:
    org = db.get(Org, current_user.org_id)
    if org is None:
        raise _credentials_error
    return org


def require_role(*roles: str):
    """Dependency factory enforcing that the user has one of ``roles``."""

    def _guard(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return _guard
