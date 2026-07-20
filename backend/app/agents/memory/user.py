"""User memory — durable facts / preferences remembered across conversations.

Facts are captured from natural-language cues like "remember that ..." and can
be recalled by the responder to personalise replies. Fully offline (DB-backed).
"""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.models.user_fact import UserFact

_REMEMBER_RE = re.compile(r"\bremember(?:\s+that)?\s+(.+)$", re.IGNORECASE)


class UserMemory:
    def __init__(self, db: Session, user_id: int) -> None:
        self.db = db
        self.user_id = user_id

    def maybe_capture(self, text: str) -> str | None:
        """If the text asks to remember something, store and return the fact."""
        match = _REMEMBER_RE.search(text.strip())
        if not match:
            return None
        fact = match.group(1).strip().rstrip(".")
        if not fact:
            return None
        self.add(fact)
        return fact

    def add(self, fact: str) -> UserFact:
        row = UserFact(user_id=self.user_id, fact=fact)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def all_facts(self) -> list[str]:
        rows = (
            self.db.query(UserFact)
            .filter(UserFact.user_id == self.user_id)
            .order_by(UserFact.id.asc())
            .all()
        )
        return [r.fact for r in rows]
