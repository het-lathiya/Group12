"""Maximal marginal relevance over guide chunks (Amendment A1 §6.7). Pure: no I/O.

Each step takes the chunk with the best λ·similarity - (1 - λ)·(closest chosen chunk), and no
document gives more than ``per_document`` chunks. Vectors are L2-normalised (A1 §6.5), so a dot
product is their cosine. Ties go to the lowest chunk ID.
"""

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from uuid import UUID

from app.rag.constants import RAG_MAX_CHUNKS_PER_DOCUMENT, RAG_MMR_LAMBDA, RAG_TOP_K_GUIDE


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: UUID
    document_id: UUID
    place_id: UUID | None
    title: str
    content: str
    similarity: float
    vector: Sequence[float] = ()  # only guide chunks need theirs, for this selection


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def select(
    chunks: Iterable[RetrievedChunk],
    *,
    k: int = RAG_TOP_K_GUIDE,
    lam: float = RAG_MMR_LAMBDA,
    per_document: int = RAG_MAX_CHUNKS_PER_DOCUMENT,
) -> list[RetrievedChunk]:
    """Up to ``k`` chunks in selection order."""
    remaining = sorted(chunks, key=lambda chunk: str(chunk.chunk_id))
    chosen: list[RetrievedChunk] = []
    taken: Counter[UUID] = Counter()

    def marginal(chunk: RetrievedChunk) -> float:
        closest = max((_cosine(chunk.vector, other.vector) for other in chosen), default=0.0)
        return lam * chunk.similarity - (1 - lam) * closest

    while len(chosen) < k:
        allowed = [chunk for chunk in remaining if taken[chunk.document_id] < per_document]
        if not allowed:
            break
        best = max(allowed, key=marginal)  # max keeps the first of equals: the lowest chunk ID
        chosen.append(best)
        taken[best.document_id] += 1
        remaining.remove(best)
    return chosen
