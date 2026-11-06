"""TC-447: chunker limits, headings and overlap (Amendment A1 §6.4)."""

import hashlib
import math

from app.rag.chunker import chunk_guide, make_chunk
from app.rag.constants import RAG_CHUNK_MAX_CHARS, RAG_CHUNK_OVERLAP_CHARS

SENTENCE = "The market square has a small fountain near the clock tower."


def paragraph(sentences: int) -> str:
    return " ".join([SENTENCE] * sentences)


def test_tc_447_each_section_keeps_its_heading_and_chunks_count_up() -> None:
    chunks = chunk_guide(f"## One\n\n{paragraph(2)}\n\n## Two\n\n{paragraph(2)}")

    assert [(chunk.index, chunk.heading) for chunk in chunks] == [(0, "One"), (1, "Two")]


def test_tc_447_paragraphs_are_packed_up_to_the_limit() -> None:
    body = "## One\n\n" + "\n\n".join(paragraph(3) for _ in range(10))

    chunks = chunk_guide(body)

    assert len(chunks) > 1
    assert all(chunk.heading == "One" for chunk in chunks)
    assert len(chunks[0].content) <= RAG_CHUNK_MAX_CHARS
    assert chunks[0].content.count("\n\n") >= 1


def test_tc_447_every_chunk_holds_1_to_1200_characters() -> None:
    long_word = "x" * 2500
    body = f"## One\n\n{paragraph(40)}\n\n{'word ' * 600}\n\n{long_word}\n\ntail."

    chunks = chunk_guide(body)

    assert all(1 <= len(chunk.content) <= 1200 for chunk in chunks)


def test_tc_447_a_long_paragraph_splits_at_sentence_ends() -> None:
    chunks = chunk_guide(f"## One\n\n{paragraph(30)}")

    assert len(chunks) > 1
    assert all(chunk.content.endswith(".") for chunk in chunks)


def test_tc_447_a_long_sentence_splits_at_word_boundaries() -> None:
    chunks = chunk_guide("## One\n\n" + "word " * 400)

    assert len(chunks) > 1
    assert all(set(chunk.content.split()) == {"word"} for chunk in chunks)


def test_tc_447_later_chunks_start_with_the_end_of_the_previous_one_at_a_boundary() -> None:
    first, second = chunk_guide(f"## One\n\n{paragraph(14)}\n\n{paragraph(14)}")[:2]

    overlap = second.content[: RAG_CHUNK_OVERLAP_CHARS + 1]
    assert second.content.startswith(SENTENCE)
    assert first.content.endswith(SENTENCE)
    assert overlap.startswith("The market")


def test_tc_447_no_overlap_crosses_a_heading() -> None:
    first, second = chunk_guide(f"## One\n\n{paragraph(2)}\n\n## Two\n\nOnly this text.")

    assert second.content == "Only this text."
    assert first.heading != second.heading


def test_tc_447_token_estimate_and_hash_follow_the_rule() -> None:
    chunk = make_chunk(0, "One", "x" * 41)

    assert chunk.token_estimate == math.ceil(41 / 4)
    assert chunk.sha256 == hashlib.sha256(("One\n" + "x" * 41).encode()).hexdigest()
    assert make_chunk(0, "Two", "x" * 41).sha256 != chunk.sha256


def test_text_before_the_first_heading_is_kept_without_a_heading() -> None:
    [chunk] = chunk_guide("Intro text.")

    assert (chunk.heading, chunk.content) == (None, "Intro text.")
