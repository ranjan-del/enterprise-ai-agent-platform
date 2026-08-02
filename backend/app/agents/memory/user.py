"""User memory — durable facts / preferences remembered across conversations.

Facts are captured from natural-language cues like "remember that ..." and can
be recalled by the responder to personalise replies. Fully offline (DB-backed).

Every query filters on org_id *and* user_id: user memory is the one layer that
follows a person across conversations, so it is also the layer where a scoping
mistake would leak the most.
"""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.models.user_fact import UserFact

_REMEMBER_RE = re.compile(r"\bremember(?:\s+that)?\s+(.+)$", re.IGNORECASE)
_FORGET_RE = re.compile(r"\bforget(?:\s+that)?\s+(.+)$", re.IGNORECASE)


class UserMemory:
    def __init__(self, db: Session, org_id: int, user_id: int) -> None:
        self.db = db
        self.org_id = org_id
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

    def maybe_forget(self, text: str) -> str | None:
        """If the text asks to forget something, drop the closest fact.

        Matching is substring-based and deliberately conservative: it removes at
        most one fact, so a vague "forget my colour" cannot wipe all memory.
        """
        match = _FORGET_RE.search(text.strip())
        if not match:
            return None
        needle = match.group(1).strip().rstrip(".").lower()
        if not needle:
            return None
        for row in self._rows():
            if needle in row.fact.lower() or row.fact.lower() in needle:
                fact = row.fact
                self.db.delete(row)
                self.db.commit()
                return fact
        return None

    def add(self, fact: str) -> UserFact:
        row = UserFact(org_id=self.org_id, user_id=self.user_id, fact=fact)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def _rows(self) -> list[UserFact]:
        return (
            self.db.query(UserFact)
            .filter(UserFact.org_id == self.org_id, UserFact.user_id == self.user_id)
            .order_by(UserFact.id.asc())
            .all()
        )

    def all_facts(self) -> list[str]:
        return [r.fact for r in self._rows()]

    def rows(self) -> list[UserFact]:
        """Full rows (id + timestamp), used by the memory API and the UI."""
        return self._rows()

    def delete(self, fact_id: int) -> bool:
        """Delete one fact by id within the tenant. Returns True if removed."""
        row = (
            self.db.query(UserFact)
            .filter(
                UserFact.id == fact_id,
                UserFact.org_id == self.org_id,
                UserFact.user_id == self.user_id,
            )
            .first()
        )
        if row is None:
            return False
        self.db.delete(row)
        self.db.commit()
        return True
