"""Retrieval metrics of the evaluation harness (Amendment A1 §6.14, FR-140; IMP-318). Pure.

Each function answers None when its denominator is empty (no relevant label, no saved citation, no
AI-written note): the share is undefined there, and ``mean`` leaves it out instead of counting it
as 0 or 1. Shares are rounded to four places so that two runs compare equal as JSON.
"""

from collections.abc import Collection, Iterable, Sequence
from typing import Final

PLACES: Final = 4


def _share(hits: int, total: int) -> float | None:
    return round(hits / total, PLACES) if total else None


def recall_at_k(
    selected_doc_keys: Sequence[str], relevant: Collection[str], k: int = 6
) -> float | None:
    """Share of the relevant guide documents among the documents of the first ``k`` passages."""
    return _share(len(set(selected_doc_keys[:k]) & set(relevant)), len(set(relevant)))


def place_hit_rate[T](
    ranked_place_ids: Sequence[T], relevant: Collection[T], top: int = 12
) -> float | None:
    """Share of the relevant places in the first ``top`` of the ranked shortlist."""
    return _share(len(set(ranked_place_ids[:top]) & set(relevant)), len(set(relevant)))


def citation_validity(saved_ids: Sequence[str], supplied_ids: Collection[str]) -> float | None:
    """Share of the saved citations that were supplied to their generation (must be 1.0)."""
    return _share(sum(chunk_id in supplied_ids for chunk_id in saved_ids), len(saved_ids))


def grounding_rate(items: Iterable[tuple[str | None, Sequence[str]]]) -> float | None:
    """Share of AI-written notes, as (note, citations) pairs, with at least one citation."""
    noted = [sources for note, sources in items if note and note.strip()]
    return _share(sum(bool(sources) for sources in noted), len(noted))


def mean(values: Iterable[float | None]) -> float | None:
    """Mean of the defined values, or None when there is none."""
    defined = [value for value in values if value is not None]
    return round(sum(defined) / len(defined), PLACES) if defined else None
