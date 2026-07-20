"""Authentication routes: register (org + owner), login, refresh, me.

Multi-tenant: registering creates an organization and its first owner user.
Login issues an access + refresh token pair carrying the tenant (org) id.
"""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core import security
from app.db.session import get_db
from app.deps import get_current_org, get_current_user
from app.models.org import Org
from app.models.role import Role
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    MeResponse,
    RefreshRequest,
    RegisterRequest,
    Token,
)

router = APIRouter()


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "org"


def _unique_slug(db: Session, name: str) -> str:
    base = _slugify(name)
    slug = base
    i = 2
    while db.query(Org).filter(Org.slug == slug).first() is not None:
        slug = f"{base}-{i}"
        i += 1
    return slug


def _issue_tokens(user: User) -> Token:
    return Token(
        access_token=security.create_access_token(user.id, user.org_id),
        refresh_token=security.create_refresh_token(user.id, user.org_id),
    )


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Create a new organization and its first (owner) user, then log them in."""
    org = Org(name=payload.org_name, slug=_unique_slug(db, payload.org_name))
    db.add(org)
    db.flush()  # assigns org.id without a second round trip

    exists = (
        db.query(User)
        .filter(User.org_id == org.id, User.email == payload.email)
        .first()
    )
    if exists is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        org_id=org.id,
        email=payload.email,
        hashed_password=security.hash_password(payload.password),
        role=Role.OWNER.value,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _issue_tokens(user)


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate credentials (optionally within a specific org) and issue tokens."""
    query = db.query(User).filter(User.email == payload.email)
    if payload.org_slug:
        org = db.query(Org).filter(Org.slug == payload.org_slug).first()
        if org is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
        query = query.filter(User.org_id == org.id)

    user = query.first()
    if user is None or not security.verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")
    return _issue_tokens(user)


@router.post("/refresh", response_model=Token)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    """Exchange a valid refresh token for a fresh access + refresh pair."""
    try:
        claims = security.decode_token(payload.refresh_token)
    except security.JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    if claims.get("type") != security.REFRESH:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not a refresh token")
    user = db.get(User, int(claims["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return _issue_tokens(user)


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user), org: Org = Depends(get_current_org)):
    """Return the current user together with their tenant context."""
    return MeResponse(user=current_user, org=org)
