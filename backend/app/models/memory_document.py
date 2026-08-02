"""MemoryDocument model: durable backing store for vector memory.

Every fact the user teaches the agent, every message they exchange, and every
note they save is indexed here as a plain text document. The vector layer
(``app.agents.memory.vector.TenantVectorMemory``) scores these rows so recall
survives a process restart instead of living only in RAM.

Rows carry both org_id and user_id and are always queried on both, keeping
recall inside the tenant boundary.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MemoryDocument(Base):
    __tablename__ = "memory_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("orgs.id"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    conversation_id: Mapped[int | None] = mapped_column(
        ForeignKey("conversations.id"), nullable=True
    )
    # Where the text came from: fact | message | note. Useful for filtering and
    # for showing the user *why* something was recalled.
    kind: Mapped[str] = mapped_column(String, default="message", nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
