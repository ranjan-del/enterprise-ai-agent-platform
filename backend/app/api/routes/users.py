"""User + role management routes.

TODO: checklist "Auth + multi-tenancy: ... users, roles".
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def list_users() -> dict:
    """List users within the caller's organization."""
    # TODO: implement tenant-scoped user listing
    return {"detail": "TODO: implement list_users"}


@router.post("")
async def create_user() -> dict:
    """Invite / create a user and assign a role."""
    # TODO: implement user creation + role assignment
    return {"detail": "TODO: implement create_user"}


@router.get("/{user_id}")
async def get_user(user_id: str) -> dict:
    """Fetch a single user by id."""
    # TODO: implement user retrieval
    return {"detail": "TODO: implement get_user", "user_id": user_id}
