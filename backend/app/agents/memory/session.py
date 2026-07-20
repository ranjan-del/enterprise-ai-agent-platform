"""Session (short-term) memory — a rolling window of recent turns.

Backed by :class:`app.cache.redis.SessionCache`, which uses Redis when available
and an in-process store otherwise. Keeps the last N turns per conversation.
"""

from __future__ import annotations

from app.cache.redis import get_session_cache


class SessionMemory:
    def __init__(self, conversation_id: int) -> None:
        self.conversation_id = conversation_id
        self._cache = get_session_cache()

    def add(self, role: str, content: str) -> None:
        self._cache.append_turn(self.conversation_id, role, content)

    def history(self) -> list[dict[str, str]]:
        return self._cache.recent_turns(self.conversation_id)

    def clear(self) -> None:
        self._cache.clear(self.conversation_id)
