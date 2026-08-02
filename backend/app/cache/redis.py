"""Session-memory cache with a transparent in-process fallback.

The platform is offline-first: Redis is optional. When ``REDIS_URL`` is set and
reachable, a real Redis client is used; otherwise (local dev, CI, tests) an
in-process dictionary provides the exact same small interface. Callers never
need to know which backend is active.
"""

from __future__ import annotations

import json
import threading
import time
from typing import Any, Optional

from app.core.config import settings


class _InProcessCache:
    """A minimal, thread-safe TTL cache implementing the subset we use.

    Only the operations the session memory needs are provided: get/set (with
    optional expiry) and delete. Values are JSON strings, matching Redis.
    """

    def __init__(self) -> None:
        self._data: dict[str, tuple[str, Optional[float]]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[str]:
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            value, expires_at = item
            if expires_at is not None and expires_at < time.time():
                self._data.pop(key, None)
                return None
            return value

    def set(self, key: str, value: str, ex: Optional[int] = None) -> None:
        expires_at = time.time() + ex if ex else None
        with self._lock:
            self._data[key] = (value, expires_at)

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)


class SessionCache:
    """High-level session memory used by the agent runtime.

    Stores a rolling window of recent conversation turns keyed by conversation
    id, so the responder has short-term context without hitting the database.
    """

    def __init__(self, backend: Any) -> None:
        self._backend = backend

    @staticmethod
    def _key(org_id: int, conversation_id: int) -> str:
        # The org id is part of the key on purpose. Conversation ids are unique
        # within one database, but a shared Redis can outlive a database (or be
        # shared by several deployments), and a recycled id must never hand one
        # tenant another tenant's short-term context.
        return f"session:org:{org_id}:conv:{conversation_id}"

    def append_turn(
        self, org_id: int, conversation_id: int, role: str, content: str, max_turns: int = 20
    ) -> None:
        key = self._key(org_id, conversation_id)
        raw = self._backend.get(key)
        turns = json.loads(raw) if raw else []
        turns.append({"role": role, "content": content})
        turns = turns[-max_turns:]
        self._backend.set(key, json.dumps(turns), ex=60 * 60)

    def recent_turns(self, org_id: int, conversation_id: int) -> list[dict[str, str]]:
        raw = self._backend.get(self._key(org_id, conversation_id))
        return json.loads(raw) if raw else []

    def clear(self, org_id: int, conversation_id: int) -> None:
        self._backend.delete(self._key(org_id, conversation_id))


def _build_backend() -> Any:
    """Return a real Redis client if configured + reachable, else in-process."""
    url = settings.REDIS_URL.strip()
    if not url:
        return _InProcessCache()
    try:  # pragma: no cover - exercised only when a real Redis is present
        import redis  # noqa: WPS433 (import inside function is intentional)

        client = redis.Redis.from_url(url, decode_responses=True)
        client.ping()
        return client
    except Exception:
        # Any failure (missing package, refused connection) -> safe fallback.
        return _InProcessCache()


_session_cache: Optional[SessionCache] = None


def get_session_cache() -> SessionCache:
    """Return the process-wide session cache (lazily initialised)."""
    global _session_cache
    if _session_cache is None:
        _session_cache = SessionCache(_build_backend())
    return _session_cache


def reset_session_cache() -> None:
    """Drop the cached backend. Used by tests so runs cannot bleed into each other."""
    global _session_cache
    _session_cache = None
