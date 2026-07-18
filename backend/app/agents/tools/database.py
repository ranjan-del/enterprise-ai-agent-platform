"""Database tool — scoped read-only SQL queries.

TODO: checklist "Tool integrations: database".
"""


def run(query: str, **kwargs) -> dict:
    """Run a guarded, read-only query and return rows."""
    # TODO: enforce read-only + tenant scoping; use app.db.session
    raise NotImplementedError("database tool not implemented")
