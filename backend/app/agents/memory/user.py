"""User memory — durable per-user facts/preferences.

TODO: checklist "Memory subsystems: user".
"""


class UserMemory:
    """Cross-conversation memory about an individual user."""

    def remember(self, user_id: str, fact: str) -> None:
        """Store a salient fact/preference about a user."""
        # TODO: persist to a user_memory table
        raise NotImplementedError

    def recall(self, user_id: str) -> list[str]:
        """Retrieve stored facts for a user."""
        # TODO: query user_memory
        raise NotImplementedError
