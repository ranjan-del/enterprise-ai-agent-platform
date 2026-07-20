"""Vector memory — a tiny, dependency-free semantic store.

A production system would use Qdrant or pgvector. To stay fully offline and
deterministic, this implements a bag-of-words vector with cosine similarity in
pure Python. It supports the same shape (add documents, query top-k) so it can
be swapped for a real vector store later.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _vectorize(text: str) -> Counter:
    return Counter(_TOKEN_RE.findall(text.lower()))


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
        scored.sort(key=lambda s: s[1], reverse=True)
        return scored[:k]

    def __len__(self) -> int:
        return len(self._docs)
