"""Session (short-term) memory — a rolling window of recent turns.

Backed by :class:`app.cache.redis.SessionCache`, which uses Redis when available
and an in-process store otherwise. Keeps the last N turns per conversation.

The tenant id is part of the cache key, not only the conversation id: a cache
can outlive or be shared across databases, and a recycled conversation id must
never surface another tenant's short-term context.
"""

from __future__ import annotations

from app.cache.redis import get_session_cache


class SessionMemory:
    def __init__(self, org_id: int, conversation_id: int) -> None:
        self.org_id = org_id
        self.conversation_id = conversation_id
        self._cache = get_session_cache()

    def add(self, role: str, content: str) -> None:
        self._cache.append_turn(self.org_id, self.conversation_id, role, content)

    def history(self) -> list[dict[str, str]]:
        return self._cache.recent_turns(self.org_id, self.conversation_id)

    def clear(self) -> None:
        self._cache.clear(self.org_id, self.conversation_id)
