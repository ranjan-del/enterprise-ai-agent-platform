"""User model (belongs to an Org, has a Role).

TODO: checklist "Auth + multi-tenancy: ... users".
"""

# from app.models import Base


class User:  # TODO: subclass Base, __tablename__ = "users"
    """Placeholder attributes: id, org_id, email, hashed_password, role_id,
    is_active, created_at.
    """

    # TODO: map columns + relationship("Org") and relationship("Role")
    pass
