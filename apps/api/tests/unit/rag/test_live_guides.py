"""TC-478 (unit): live guide documents from Wikivoyage and Wikipedia sections (A2 §6.5; IMP-726)."""

import dataclasses
import re
from datetime import date
from typing import Literal
from uuid import uuid4

import pytest

from app.livedata.providers.base import WikiSection
from app.livedata.providers.fake import FakeGuides
from app.rag import documents as corpus
from app.rag import live_guides
from app.rag.constants import GUIDE_MAX_CHARS
from app.rag.guides import _CONTENT_RULES

TODAY = date(2026, 11, 23)
SLUG = "live-liveton-sample-r9000001"
LONG = (
    "The old quarter of narrow lanes climbs from the river towards the hill fort, and its "
    "courtyard houses keep carved wooden balconies above the street. "
)
DOC_KEY = re.compile(r"^guide:live-[a-z0-9-]+/(wikivoyage|wikipedia)-[0-9]+-[0-9]+(-[0-9]+)?$")


def section(
    heading: str,
    text: str,
    *,
    index: int = 1,
    source: Literal["wikivoyage", "wikipedia"] = "wikivoyage",
    page_id: int = 42,
) -> WikiSection:
    host = "en.wikivoyage.org" if source == "wikivoyage" else "en.wikipedia.org"
    return WikiSection(
        source=source,
        page_id=page_id,
        revision_id=page_id * 10,
        page_title="Liveton (SAMPLE)",
        page_url=f"https://{host}/wiki/Liveton_(SAMPLE)",
        index=index,
        heading=heading,
        text=text,
    )


def stored_text(build: live_guides.LiveGuideBuild) -> str:
    return "\n".join(chunk.content for doc, _ in build.guides for chunk in doc.chunks)


async def fake_sections() -> list[WikiSection]:
    return await FakeGuides("ok", app_env="test").fetch("Liveton (SAMPLE)", 23.0, 72.0)


@pytest.mark.asyncio
async def test_live_guides_fake_sections_drop_flagged_paragraphs_and_skip_eat() -> None:
    build = live_guides.build_guides(SLUG, await fake_sections(), TODAY)

    # The SAMPLE sections are short: only Understand keeps 300 characters. See drops its price
    # and opening-times paragraph and is then too short; Eat is a skipped section.
    assert [doc.title for doc, _ in build.guides] == ["Wikivoyage: Liveton (SAMPLE) — Understand"]
    assert build.dropped_paragraphs == 1
    assert build.skipped_sections == 6
    text = stored_text(build)
    assert "Rs 50" not in text
    assert "9:00" not in text


def test_live_guides_no_flagged_phrase_reaches_a_chunk() -> None:
    flagged = [
        "Entry costs ₹200 for adults and the gardens are lovely in the evening light.",
        "The museum is open 10:00-18:00 and has a large collection of local paintings.",
        "The temple is open daily and is a quiet place to rest after a long walk.",
        "It is 10 minutes by rickshaw from the station, past the old market square.",
        "Tickets are USD 15 and cover the fort, the museum and the stepwell together.",
    ]
    sections = [section("See", "\n\n".join([*flagged, LONG * 3]))]
    build = live_guides.build_guides(SLUG, sections, TODAY)

    assert build.dropped_paragraphs == len(flagged)
    for doc, _ in build.guides:
        for chunk in doc.chunks:
            for _, pattern in _CONTENT_RULES:
                assert not pattern.search(chunk.content)


@pytest.mark.parametrize(
    "heading", ["Sleep", "Buy", "Eat", "Drink", "Connect", "Go next", "go  NEXT"]
)
def test_live_guides_skips_named_sections(heading: str) -> None:
    build = live_guides.build_guides(SLUG, [section(heading, LONG * 5)], TODAY)
    assert build.guides == []
    assert build.skipped_sections == 1


def test_live_guides_skips_a_section_shorter_than_300_chars_after_dropping() -> None:
    text = "A short clean paragraph about the river.\n\nOpening hours vary; ask locally. " + LONG
    build = live_guides.build_guides(SLUG, [section("Understand", text)], TODAY)
    assert build.guides == []
    assert (build.dropped_paragraphs, build.skipped_sections) == (1, 1)


def test_live_guides_doc_key_and_front_matter() -> None:
    sections = [
        section("Understand", LONG * 3, index=1),
        section("History", LONG * 3, index=2, source="wikipedia", page_id=77),
    ]
    build = live_guides.build_guides(SLUG, sections, TODAY)

    keys = [doc.doc_key for doc, _ in build.guides]
    assert keys == [f"guide:{SLUG}/wikivoyage-42-1", f"guide:{SLUG}/wikipedia-77-2"]
    assert all(DOC_KEY.match(key) for key in keys)
    voyage, pedia = (guide for _, guide in build.guides)
    assert voyage.title == "Wikivoyage: Liveton (SAMPLE) — Understand"
    assert pedia.title == "Wikipedia: Liveton (SAMPLE) — History"
    assert (voyage.source_name, pedia.source_name) == ("Wikivoyage", "Wikipedia")
    assert {g.licence for g in (voyage, pedia)} == {"CC BY-SA 4.0"}
    assert {g.source_type for g in (voyage, pedia)} == {"other"}
    assert voyage.url == "https://en.wikivoyage.org/wiki/Liveton_(SAMPLE)"
    assert voyage.retrieved_on == TODAY
    assert voyage.curated_by == "not checked by the team (live import)"
    assert voyage.attribution_text == (
        "Guide text from Wikivoyage (Liveton (SAMPLE)), by its contributors, under CC BY-SA 4.0; "
        "excerpts, some sections left out"
    )
    assert pedia.attribution_text is not None
    assert pedia.attribution_text.startswith("Guide text from Wikipedia (Liveton (SAMPLE))")
    assert all(chunk.heading == "Understand" for chunk in build.guides[0][0].chunks)


def test_live_guides_shared_source_attribution_has_no_page_title() -> None:
    assert live_guides.attribution_text("Wikivoyage") == (
        "Guide text from Wikivoyage, by its contributors, under CC BY-SA 4.0; "
        "excerpts, some sections left out"
    )


def test_live_guides_long_section_splits_at_paragraphs_into_6000_char_documents() -> None:
    paragraphs = [f"Paragraph {n}. " + LONG * 4 for n in range(30)]
    build = live_guides.build_guides(SLUG, [section("Understand", "\n\n".join(paragraphs))], TODAY)

    assert len(build.guides) > 1
    keys = [doc.doc_key for doc, _ in build.guides]
    assert keys[0] == f"guide:{SLUG}/wikivoyage-42-1"
    assert keys[1] == f"guide:{SLUG}/wikivoyage-42-1-2"
    assert len(set(keys)) == len(keys)
    for _, guide in build.guides:
        body = guide.body.split("\n\n", 1)[1]
        assert len(body) <= GUIDE_MAX_CHARS
        assert body.startswith("Paragraph ")  # every document starts at a paragraph


def test_live_guides_place_document_title_starts_with_openstreetmap() -> None:
    doc = corpus.place_document(uuid4(), "Fort (SAMPLE)", "sight", ["history"], None, None, TODAY)
    live = live_guides.live_place_document(doc)
    assert live.title == "OpenStreetMap: Fort (SAMPLE)"
    assert (live.doc_key, live.chunks, live.place_id) == (doc.doc_key, doc.chunks, doc.place_id)


def test_live_guides_cap_keeps_places_first_then_guides_in_page_order() -> None:
    sections = [section(f"Part {n}", LONG * 3, index=n) for n in range(1, 6)]
    build = live_guides.build_guides(SLUG, sections, TODAY)
    per_doc = len(build.guides[0][0].chunks)

    kept = live_guides.cap_guides(400 - 2 * per_doc, build.guides)
    assert [doc.doc_key for doc, _ in kept] == [doc.doc_key for doc, _ in build.guides[:2]]
    assert live_guides.cap_guides(400, build.guides) == []
    assert live_guides.cap_guides(0, build.guides) == build.guides
    assert live_guides.LIVE_MAX_CHUNKS_PER_DESTINATION == 400
    assert live_guides.RAG_MAX_ACTIVE_CHUNKS == 5000


def test_live_guides_each_document_has_its_own_page_attribution_and_url() -> None:
    pages = [
        dataclasses.replace(
            section("Understand", LONG * 3, index=1), page_title="Liveton (SAMPLE)", page_id=42
        ),
        dataclasses.replace(
            section("Understand", LONG * 3, index=1),
            page_title="Liveton District (SAMPLE)",
            page_url="https://en.wikivoyage.org/wiki/Liveton_District_(SAMPLE)",
            page_id=43,
        ),
        section("History", LONG * 3, index=2, source="wikipedia", page_id=77),
    ]
    build = live_guides.build_guides(SLUG, pages, TODAY)

    assert len(build.guides) == 3
    for (document, guide), page in zip(build.guides, pages, strict=True):
        source = "Wikivoyage" if page.source == "wikivoyage" else "Wikipedia"
        assert guide.attribution_text == (
            f"Guide text from {source} ({page.page_title}), by its contributors, under "
            "CC BY-SA 4.0; excerpts, some sections left out"
        )
        assert guide.url == document.url == page.page_url
        assert page.page_title in document.title
