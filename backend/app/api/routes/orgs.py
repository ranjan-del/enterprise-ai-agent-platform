"""Organization routes — read the caller's own tenant.

Tenancy is strict: a user can only see their own organization.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import get_current_org, get_current_user
from app.models.org import Org
from app.models.user import User
from app.schemas.auth import OrgOut

router = APIRouter()


@router.get("", response_model=list[OrgOut])
def list_orgs(org: Org = Depends(get_current_org)):
    """List organizations visible to the caller (their own tenant only)."""
    return [org]


@router.get("/{org_id}", response_model=OrgOut)
def get_org(
    org_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if org_id != current_user.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your organization")
    org = db.get(Org, org_id)
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return org
