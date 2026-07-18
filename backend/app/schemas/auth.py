"""Auth schemas.

TODO: checklist "Auth + multi-tenancy: JWT".
"""
from pydantic import BaseModel


class LoginRequest(BaseModel):
    """Credentials submitted to POST /auth/login."""

    email: str  # TODO: use EmailStr once validators are added
    password: str


class TokenResponse(BaseModel):
    """JWT bundle returned on successful auth."""

    access_token: str
    token_type: str = "bearer"
    # TODO: add refresh_token + expires_in
