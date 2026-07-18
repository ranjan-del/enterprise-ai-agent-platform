"""Session memory — short-lived, per-conversation context (Redis-backed).

TODO: checklist "Memory subsystems: session (Redis)".
"""


class SessionMemory:
    """Ephemeral working memory scoped to a single conversation/session."""

    def load(self, session_id: str) -> list[dict]:
        """Return the recent turn buffer for a session."""
        # TODO: read from Redis with TTL
        raise NotImplementedError

    def append(self, session_id: str, item: dict) -> None:
        """Append a turn to the session buffer."""
        # TODO: write to Redis list, trim to window
        raise NotImplementedError
