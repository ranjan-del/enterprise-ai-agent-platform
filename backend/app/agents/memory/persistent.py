"""Persistent memory — durable conversation state (Postgres-backed).

TODO: checklist "Memory subsystems: persistent (Postgres)".
"""


class PersistentMemory:
    """Long-term memory persisted across sessions in PostgreSQL."""

    def save(self, conversation_id: str, state: dict) -> None:
        """Checkpoint conversation state to the database."""
        # TODO: upsert into a checkpoints table (LangGraph checkpointer)
        raise NotImplementedError

    def load(self, conversation_id: str) -> dict:
        """Restore the latest checkpoint for a conversation."""
        # TODO: read latest checkpoint row
        raise NotImplementedError
