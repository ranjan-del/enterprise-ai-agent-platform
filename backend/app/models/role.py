"""Role definitions for RBAC.

A small string enum stored on the user row. This is the simplest design that
fully supports the Owner / Admin / Member roles the platform needs; a separate
``roles`` table would be overkill for a fixed role set.
"""

import enum


class Role(str, enum.Enum):
    """Allowed roles. Inherits from ``str`` so it serialises cleanly to JSON."""

    OWNER = "owner"    # created the org; full control
    ADMIN = "admin"    # manage users/agents within the org
    MEMBER = "member"  # use agents + chat

    @classmethod
    def values(cls) -> list[str]:
        return [r.value for r in cls]
