"""Shared/common schema helpers.

TODO: checklist "API documentation" — pagination, error envelopes, etc.
"""
from pydantic import BaseModel


class Message(BaseModel):
    """Generic detail envelope for placeholder responses."""

    detail: str
