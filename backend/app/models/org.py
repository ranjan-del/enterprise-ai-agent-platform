"""Organization (tenant) model.

TODO: checklist "Auth + multi-tenancy: ... organizations".
"""

# from sqlalchemy.orm import Mapped, mapped_column
# from app.models import Base


class Org:  # TODO: subclass Base and declare __tablename__ = "orgs"
    """Tenant boundary. Owns users, agents, conversations, and analytics.

    Placeholder attributes (to become mapped columns):
        id, name, slug, plan, created_at
    """

    # TODO: id: Mapped[str] = mapped_column(primary_key=True)
    # TODO: name / slug / plan / created_at
    pass
