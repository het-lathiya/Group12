"""Maximal marginal relevance over guide chunks (Amendment A1 §6.7; TC-453, IMP-315)."""

import math
from collections import Counter
from uuid import UUID

from app.rag import mmr
from app.rag.mmr import RetrievedChunk

DOC_A = UUID(int=1001)
DOC_B = UUID(int=1002)
DOC_C = UUID(int=1003)


def chunk(
    number: int, similarity: float, vector: tuple[float, ...], document: UUID = DOC_A
) -> RetrievedChunk:
    return RetrievedChunk(UUID(int=number), document, None, "Guide", "text", similarity, vector)


def unit(degrees: float) -> tuple[float, float]:
    return (math.cos(math.radians(degrees)), math.sin(math.radians(degrees)))


def test_tc_453_at_most_two_chunks_come_from_one_document() -> None:
    chunks = [chunk(n, 1 - n / 100, unit(n)) for n in range(1, 6)]
    chunks += [chunk(10, 0.1, unit(90), DOC_B)]
    picked = mmr.select(chunks)
    assert Counter(item.document_id for item in picked) == {DOC_A: 2, DOC_B: 1}


def test_a_near_duplicate_loses_to_a_different_chunk() -> None:
    first = chunk(1, 0.90, unit(0), DOC_A)
    twin = chunk(2, 0.89, unit(1), DOC_B)
    other = chunk(3, 0.80, unit(90), DOC_C)
    assert mmr.select([twin, other, first], k=2) == [first, other]


def test_the_first_pick_is_the_most_similar_and_k_limits_the_result() -> None:
    chunks = [chunk(n, n / 10, unit(n * 20), UUID(int=n)) for n in range(1, 9)]
    picked = mmr.select(chunks)
    assert picked[0].similarity == 0.8
    assert len(picked) == 6


def test_ties_are_broken_by_chunk_id_whatever_the_input_order() -> None:
    low, high = chunk(1, 0.5, unit(0), DOC_A), chunk(2, 0.5, unit(0), DOC_B)
    assert mmr.select([high, low], k=1) == [low]
    assert mmr.select([low, high], k=1) == [low]


def test_no_chunks_give_no_passages() -> None:
    assert mmr.select([]) == []
