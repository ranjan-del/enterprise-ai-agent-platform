"""Agent model — a configured assistant (system prompt + enabled tools)."""

import json
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
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
    # JSON-encoded list of agent ids this agent may delegate to (multi-agent).
    # Membership is re-checked against the org on every run, so a stale id can
    # never pull another tenant's agent into a run.
    teammate_ids: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    # Human-in-the-loop: when true, any tool call pauses for explicit approval.
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    org = relationship("Org", back_populates="agents")

    @staticmethod
    def _decode_list(raw: str | None) -> list:
        """Decode a JSON list column, tolerating legacy/corrupt values."""
        try:
            value = json.loads(raw or "[]")
        except (ValueError, TypeError):
            return []
        return value if isinstance(value, list) else []

    @property
    def tools(self) -> list[str]:
        return self._decode_list(self.enabled_tools)

    @tools.setter
    def tools(self, value: list[str]) -> None:
        self.enabled_tools = json.dumps(list(value or []))

    @property
    def teammates(self) -> list[int]:
        return [int(v) for v in self._decode_list(self.teammate_ids)]

    @teammates.setter
    def teammates(self, value: list[int]) -> None:
        self.teammate_ids = json.dumps([int(v) for v in (value or [])])
