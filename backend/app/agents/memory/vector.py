"""Vector memory — a tiny, dependency-free semantic store.

A production system would use Qdrant or pgvector. To stay fully offline and
deterministic, this implements a bag-of-words vector with cosine similarity in
pure Python. It keeps the same shape as a real vector store (index documents,
query top-k with scores) so the backing engine can be swapped later.

Two layers live here:

``VectorMemory``
    The pure scoring engine. No database, no tenancy, easy to unit-test.

``TenantVectorMemory``
    The engine wired to :class:`app.models.memory_document.MemoryDocument`, so
    recall is durable across restarts. Every read and write is filtered on
    org_id AND user_id, which is what keeps one tenant's recall out of
    another's answers.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.memory_document import MemoryDocument

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Words that match everything and therefore mean nothing for recall.
_STOPWORDS = frozenset(
    """a an and are as at be but by do does for from had has have how i if in is it its
    me my of on or our so that the their them then there they this to was we were what
    when where which who why will with you your""".split()
)


def _vectorize(text: str) -> Counter:
    """Tokenise to a bag of words, dropping stopwords so scores stay meaningful."""
    tokens = [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]
    return Counter(tokens)


def _cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    dot = sum(a[t] * b[t] for t in common)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


@dataclass
class VectorMemory:
    """In-memory bag-of-words vector store (offline, deterministic)."""

    _docs: list[tuple[str, Counter]] = field(default_factory=list)

    def add(self, text: str) -> None:
        if text.strip():
            self._docs.append((text, _vectorize(text)))

    def query(self, text: str, k: int = 3) -> list[tuple[str, float]]:
        qv = _vectorize(text)
        scored = [(doc, _cosine(qv, dv)) for doc, dv in self._docs]
        scored = [s for s in scored if s[1] > 0]
        # Sort by score, then by text, so equal scores come back in a stable
        # order (important: the tests assert on exact recall output).
        scored.sort(key=lambda s: (-s[1], s[0]))
        return scored[:k]

    def __len__(self) -> int:
        return len(self._docs)


@dataclass
class VectorHit:
    """One recall result: the stored text, where it came from, and its score."""

    id: int
    kind: str
    text: str
    score: float


class TenantVectorMemory:
    """Durable vector memory for a single (org, user) pair.

    Documents live in the ``memory_documents`` table. Scoring happens in Python
    over the tenant's own rows: an honest O(n) scan that is perfectly adequate
    for a workspace's memory and trivially replaceable by pgvector/Qdrant.
    """

    def __init__(self, db: Session, org_id: int, user_id: int) -> None:
        self.db = db
        self.org_id = org_id
        self.user_id = user_id

    def index(self, text: str, kind: str = "message", conversation_id: int | None = None) -> None:
        """Store a document, skipping blanks and exact duplicates."""
        text = (text or "").strip()
        if not text:
            return
        exists = (
            self.db.query(MemoryDocument.id)
            .filter(
                MemoryDocument.org_id == self.org_id,
                MemoryDocument.user_id == self.user_id,
                MemoryDocument.text == text,
            )
            .first()
        )
        if exists is not None:
            return
        self.db.add(
            MemoryDocument(
                org_id=self.org_id,
                user_id=self.user_id,
                conversation_id=conversation_id,
                kind=kind,
                text=text,
            )
        )
        self.db.commit()

    def _rows(self) -> list[MemoryDocument]:
        return (
            self.db.query(MemoryDocument)
            .filter(
                MemoryDocument.org_id == self.org_id,
                MemoryDocument.user_id == self.user_id,
            )
            .order_by(MemoryDocument.id.asc())
            .all()
        )

    def search(self, text: str, k: int = 3, min_score: float = 0.05) -> list[VectorHit]:
        """Return the top-k most similar documents for this tenant."""
        qv = _vectorize(text)
        if not qv:
            return []
        hits = [
            VectorHit(id=row.id, kind=row.kind, text=row.text, score=_cosine(qv, _vectorize(row.text)))
            for row in self._rows()
        ]
        hits = [h for h in hits if h.score >= min_score]
        hits.sort(key=lambda h: (-h.score, h.id))
        return hits[:k]

    def __len__(self) -> int:
        return (
            self.db.query(MemoryDocument)
            .filter(
                MemoryDocument.org_id == self.org_id,
                MemoryDocument.user_id == self.user_id,
            )
            .count()
        )
