"""Persistent (long-term) memory — durable conversation history in the DB."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.message import Message


class PersistentMemory:
    def __init__(self, db: Session, conversation_id: int) -> None:
        self.db = db
        self.conversation_id = conversation_id

    def add(self, role: str, content: str, tool_calls: str = "[]") -> Message:
        msg = Message(
            conversation_id=self.conversation_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def history(self, limit: int = 50) -> list[Message]:
        return (
            self.db.query(Message)
            .filter(Message.conversation_id == self.conversation_id)
            .order_by(Message.id.asc())
            .limit(limit)
            .all()
        )

    def recent(self, limit: int = 10) -> list[Message]:
        """The last ``limit`` messages, oldest-first.

        Session memory is the fast path for short-term context, but it is a
        cache: it can expire or be lost on a Redis restart. This is the durable
        equivalent the agent falls back to.
        """
        rows = (
            self.db.query(Message)
            .filter(Message.conversation_id == self.conversation_id)
            .order_by(Message.id.desc())
            .limit(limit)
            .all()
        )
        return list(reversed(rows))
