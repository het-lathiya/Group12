"""Place and guide documents (Amendment A1 §6.2)."""

import inspect
from datetime import date
from uuid import UUID

from app.rag import documents
from app.rag.chunker import chunk_guide
from app.rag.documents import guide_document, place_document, place_text
from app.rag.guides import Guide

PLACE_ID = UUID("00000000-0000-4000-8000-000000000001")


def test_place_text_follows_the_format() -> None:
    text = place_text("Old Fort", "sight", ["history", "views"], "A hill fort.", "Fort Road")

    assert text == "Old Fort (sight). Tags: history, views. A hill fort. Area: Fort Road"


def test_empty_parts_are_left_out() -> None:
    assert place_text("Old Fort", "sight", [], None, None) == "Old Fort (sight)."
    assert place_text("Old Fort", "sight", [], "  ", "   ") == "Old Fort (sight)."


def test_at_most_ten_tags_and_150_address_characters_are_used() -> None:
    text = place_text("P", "sight", [f"t{n}" for n in range(12)], None, "a" * 200)

    assert "t9" in text
    assert "t10" not in text
    assert text.endswith("Area: " + "a" * 150)


def test_the_text_is_cut_to_1200_characters_at_a_word_boundary() -> None:
    text = place_text("P", "sight", [], "word " * 400, None)

    assert len(text) <= 1200
    assert text.endswith("word")


def test_a_place_document_has_one_chunk_and_its_key_and_date() -> None:
    document = place_document(
        PLACE_ID, "Old Fort", "sight", ["history"], "A hill fort.", None, date(2026, 10, 1)
    )

    assert document.doc_key == f"place:{PLACE_ID}"
    assert document.place_id == PLACE_ID
    assert document.retrieved_on == date(2026, 10, 1)
    assert document.url is None
    assert [chunk.index for chunk in document.chunks] == [0]
    assert document.chunks[0].heading is None


def test_a_place_document_cannot_take_prices_hours_or_urls() -> None:
    parameters = inspect.signature(documents.place_document).parameters

    assert set(parameters) == {
        "place_id",
        "name",
        "category",
        "tags",
        "description",
        "address",
        "retrieved_on",
    }


def test_a_guide_document_carries_its_page_url_and_key() -> None:
    body = "## Walking\n\nThe old quarter is compact."
    guide = Guide(
        file="a.md",
        title="Getting around",
        source_name="Wikivoyage",
        source_type="other",
        url="https://en.wikivoyage.org/wiki/One",
        licence="CC BY-SA 4.0",
        attribution_text="Adapted.",
        retrieved_on=date(2026, 11, 1),
        curated_by="A Member",
        body=body,
        licence_line=6,
    )

    document = guide_document("example", "getting-around", guide)

    assert document.doc_key == "guide:example/getting-around"
    assert document.url == guide.url
    assert document.place_id is None
    assert document.chunks == chunk_guide(body)
