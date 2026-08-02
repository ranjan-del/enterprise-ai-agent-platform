"""UserFact model — durable per-user memory (facts/preferences)."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserFact(Base):
    __tablename__ = "user_facts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # org_id duplicates the owner's org on purpose: every read filters on
    # org_id AND user_id, so a leaked or guessed user id still cannot reach
    # another tenant's facts.
    org_id: Mapped[int] = mapped_column(ForeignKey("orgs.id"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    fact: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
