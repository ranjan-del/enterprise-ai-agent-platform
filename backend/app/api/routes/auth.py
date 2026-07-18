"""Auth routes: login, token refresh, current user.

TODO: checklist "Auth + multi-tenancy: JWT, organizations, users, roles".
"""
from fastapi import APIRouter

router = APIRouter()


@router.post("/login")
async def login() -> dict:
    """Exchange credentials for a JWT access token."""
    # TODO: validate credentials, issue token via core.security.create_access_token
    return {"detail": "TODO: implement login"}


@router.post("/refresh")
async def refresh() -> dict:
    """Issue a new access token from a valid refresh token."""
    # TODO: implement refresh token rotation
    return {"detail": "TODO: implement refresh"}


@router.get("/me")
async def me() -> dict:
    """Return the currently authenticated user + tenant context."""
    # TODO: resolve user from bearer token
    return {"detail": "TODO: implement current-user"}
