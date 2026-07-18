"""Execution model (one agent run + its trace).

TODO: checklist "Execution history + analytics".
"""

# from app.models import Base


class Execution:  # TODO: subclass Base, __tablename__ = "executions"
    """Placeholder attributes: id, org_id, agent_id, conversation_id, status,
    steps (JSON trace), tokens_used, started_at, finished_at.
    """

    # TODO: map columns; index on (org_id, started_at) for analytics queries
    pass
