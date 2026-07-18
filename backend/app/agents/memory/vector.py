"""Vector memory — semantic retrieval over embeddings.

TODO: checklist "Memory subsystems: vector (Qdrant / pgvector)".
"""


class VectorMemory:
    """Embedding-backed semantic memory for RAG-style recall."""

    def upsert(self, namespace: str, documents: list[dict]) -> None:
        """Embed and store documents in the vector store."""
        # TODO: embed + upsert to Qdrant/pgvector
        raise NotImplementedError

    def search(self, namespace: str, query: str, k: int = 5) -> list[dict]:
        """Return the k most similar documents to the query."""
        # TODO: embed query + similarity search
        raise NotImplementedError
