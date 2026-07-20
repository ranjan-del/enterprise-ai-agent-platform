"""Agent model — a configured assistant (system prompt + enabled tools)."""

import json
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("orgs.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, default="", nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # JSON-encoded list of enabled tool names (validated against the registry).
    enabled_tools: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    org = relationship("Org", back_populates="agents")

    @property
    def tools(self) -> list[str]:
        try:
            value = json.loads(self.enabled_tools or "[]")
            return value if isinstance(value, list) else []
        except (ValueError, TypeError):
            return []

    @tools.setter
    def tools(self, value: list[str]) -> None:
        self.enabled_tools = json.dumps(list(value or []))
