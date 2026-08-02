"""Execution model — one agent run and its step trace (for logs + analytics)."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Lifecycle states an Execution can be in. A run that hit a human-approval gate
# stops at AWAITING_APPROVAL and is resumed (or dropped) by an explicit decision.
COMPLETED = "completed"
FAILED = "failed"
AWAITING_APPROVAL = "awaiting_approval"
REJECTED = "rejected"


class Execution(Base):
    __tablename__ = "executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("orgs.id"), index=True, nullable=False)
    # The user who triggered the run. Needed to resume an approval in the same
    # user context (their notes, files and facts) and to scope the logs page.
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    conversation_id: Mapped[int | None] = mapped_column(
        ForeignKey("conversations.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String, default=COMPLETED, nullable=False)
    # JSON-encoded {"message", "tool", "params"} kept while a run is paused for
    # approval, so the resumed run replays exactly what the user approved.
    pending_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    # JSON-encoded list of {node, detail} step records.
    steps: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    finished_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
