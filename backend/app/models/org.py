"""Organization (tenant) model.

The tenant boundary: owns users, agents, conversations, and analytics. Every
scoped query filters by ``org_id`` so tenants never see each other's data.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Org(Base):
    __tablename__ = "orgs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    plan: Mapped[str] = mapped_column(String, default="free", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    users = relationship("User", back_populates="org", cascade="all, delete-orphan")
    agents = relationship("Agent", back_populates="org", cascade="all, delete-orphan")
