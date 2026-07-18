"""File System tool — sandboxed file read/write.

TODO: checklist "Tool integrations: file system".
"""


def run(action: str, **kwargs) -> dict:
    """Execute a filesystem action (e.g. read, write, list) in a sandbox."""
    # TODO: confine to a per-tenant sandbox root; block path traversal
    raise NotImplementedError("filesystem tool not implemented")
