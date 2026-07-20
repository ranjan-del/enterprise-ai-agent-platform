"""User routes — list and create users within the caller's organization.

Creating users requires an owner/admin role. All queries are org-scoped.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import get_db
from app.deps import get_current_user, require_role
from app.models.role import Role
from app.models.user import User
from app.schemas.common import UserCreate, UserOut

router = APIRouter()


@router.get("", response_model=list[UserOut])
def list_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(User)
        .filter(User.org_id == current_user.org_id)
        .order_by(User.id.asc())
        .all()
    )


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    current_user: User = Depends(require_role(Role.OWNER.value, Role.ADMIN.value)),
    db: Session = Depends(get_db),
):
    exists = (
        db.query(User)
        .filter(User.org_id == current_user.org_id, User.email == payload.email)
        .first()
    )
    if exists is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    role = payload.role or Role.MEMBER.value
    if role not in Role.values():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")

    user = User(
        org_id=current_user.org_id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None or user.org_id != current_user.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user
