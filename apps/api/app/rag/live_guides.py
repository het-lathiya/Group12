"""Live guide corpus: Wikivoyage and Wikipedia sections as guide documents (Amendment A2 §6.5).

Pure: no I/O. ``app.rag.service`` fetches the sections through ``GuideSourceProvider`` and writes
what this module builds. Each ``==`` section becomes its own guide document, split at paragraph
boundaries into documents of at most ``GUIDE_MAX_CHARS``. Sections named Sleep, Buy, Eat, Drink,
Connect and Go next are skipped. Every paragraph that the guide content checks of
``app.rag.guides`` would flag (currency amount, clock-time range, hours or travel phrase) is
dropped and counted, so no price, hours or travel time from guide text reaches a passage. A
section shorter than ``GUIDE_MIN_CHARS`` after dropping is skipped. The text is stored as fetched,
apart from the dropped paragraphs.

Titles start with their source ("Wikivoyage: …", "Wikipedia: …", "OpenStreetMap: …"), so the
model sees where each quoted passage comes from (A2 §6.7).
"""

import dataclasses
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Final

from app.livedata.providers.base import BBox, WikiSection
from app.rag.chunker import HEADING_MAX
from app.rag.constants import GUIDE_MAX_CHARS, GUIDE_MIN_CHARS
from app.rag.documents import CorpusDocument, guide_document
from app.rag.guides import _CONTENT_RULES, Guide

LIVE_MAX_CHUNKS_PER_DESTINATION: Final = 400  # A2 §6.5 corpus cap (IMD-107)
RAG_MAX_ACTIVE_CHUNKS: Final = 5000  # A2 §6.5: all destinations together
TITLE_MAX: Final = 200  # the rag_documents CHECK
SKIPPED_SECTIONS: Final = frozenset({"sleep", "buy", "eat", "drink", "connect", "go next"})
LIVE_CURATED_BY: Final = "not checked by the team (live import)"
GUIDE_LICENCE: Final = "CC BY-SA 4.0"
GUIDE_SOURCE_TYPE: Final = "other"
OSM_SOURCE_NAME: Final = "OpenStreetMap"
SOURCE_NAMES: Final = {"wikivoyage": "Wikivoyage", "wikipedia": "Wikipedia"}
SOURCE_URLS: Final = {
    "Wikivoyage": "https://en.wikivoyage.org/",
    "Wikipedia": "https://en.wikipedia.org/",
}
_PARAGRAPH_BREAK = re.compile(r"\n\s*\n")
_SPACES = re.compile(r"[ \t]+")


def attribution_text(source_name: str, page_title: str | None = None) -> str:
    """A2 §9.3. The shared source row has no page title; each page's front matter has one."""
    page = f" ({page_title})" if page_title else ""
    return (
        f"Guide text from {source_name}{page}, by its contributors, under {GUIDE_LICENCE}; "
        "excerpts, some sections left out"
    )


def flagged(paragraph: str) -> bool:
    """True when a guide content check of ``app.rag.guides`` matches any line of the paragraph."""
    return any(
        pattern.search(line) for line in paragraph.splitlines() for _, pattern in _CONTENT_RULES
    )


def _cut(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _parts(paragraphs: Sequence[str]) -> list[str]:
    """Paragraphs packed into parts of at most ``GUIDE_MAX_CHARS``; an overlong paragraph is cut
    at that length (a part never ends inside a paragraph otherwise)."""
    parts: list[str] = []
    current = ""
    for paragraph in paragraphs:
        paragraph = paragraph[:GUIDE_MAX_CHARS]
        joined = f"{current}\n\n{paragraph}" if current else paragraph
        if current and len(joined) > GUIDE_MAX_CHARS:
            parts.append(current)
            joined = paragraph
        current = joined
    return [*parts, current] if current else parts


def sections_inside(sections: Iterable[WikiSection], bbox: BBox) -> list[WikiSection]:
    """The sections whose page coordinates lie inside the destination's box.

    A page is found by its title, so it can be about another place of the same name; a page
    without coordinates cannot be checked. Neither is stored.
    """
    return [
        section
        for section in sections
        if section.page_lat is not None
        and section.page_lon is not None
        and bbox.contains(section.page_lat, section.page_lon)
    ]


@dataclass(frozen=True)
class LiveGuideBuild:
    guides: list[tuple[CorpusDocument, Guide]]
    dropped_paragraphs: int = 0
    skipped_sections: int = 0


def build_guides(slug: str, sections: Iterable[WikiSection], retrieved_on: date) -> LiveGuideBuild:
    """The guide documents of one live destination, in page order, with the counts."""
    guides: list[tuple[CorpusDocument, Guide]] = []
    dropped = skipped = 0
    for section in sections:
        heading = " ".join(section.heading.split())
        if heading.casefold() in SKIPPED_SECTIONS:
            skipped += 1
            continue
        paragraphs = [
            _SPACES.sub(" ", p).strip() for p in _PARAGRAPH_BREAK.split(section.text.strip())
        ]
        paragraphs = [p for p in paragraphs if p]
        kept = [p for p in paragraphs if not flagged(p)]
        dropped += len(paragraphs) - len(kept)
        if len("\n\n".join(kept)) < GUIDE_MIN_CHARS:
            skipped += 1
            continue
        source_name = SOURCE_NAMES[section.source]
        title = _cut(f"{source_name}: {section.page_title} — {heading}", TITLE_MAX)
        for number, part in enumerate(_parts(kept), 1):
            stem = f"{section.source}-{section.page_id}-{section.index}"
            guide = Guide(
                file=f"{stem}.live",
                title=title,
                source_name=source_name,
                source_type=GUIDE_SOURCE_TYPE,
                url=section.page_url,
                licence=GUIDE_LICENCE,
                attribution_text=attribution_text(source_name, section.page_title),
                retrieved_on=retrieved_on,
                curated_by=LIVE_CURATED_BY,
                body=f"## {heading[:HEADING_MAX]}\n\n{part}",
                licence_line=1,
            )
            key_stem = stem if number == 1 else f"{stem}-{number}"
            guides.append((guide_document(slug, key_stem, guide), guide))
    return LiveGuideBuild(guides, dropped, skipped)


def live_place_document(document: CorpusDocument) -> CorpusDocument:
    """A place document of a live destination, its title prefixed with its source (A2 §6.7)."""
    return dataclasses.replace(
        document, title=_cut(f"{OSM_SOURCE_NAME}: {document.title}", TITLE_MAX)
    )


def chunk_count(documents: Iterable[CorpusDocument]) -> int:
    return sum(len(document.chunks) for document in documents)


def cap_guides(
    place_chunks: int,
    guides: Sequence[tuple[CorpusDocument, Guide]],
    limit: int = LIVE_MAX_CHUNKS_PER_DESTINATION,
) -> list[tuple[CorpusDocument, Guide]]:
    """A2 §6.5: place documents first, then guide documents in page order up to ``limit`` chunks.

    The first guide document that does not fit ends the list, so the kept ones stay in order.
    """
    kept: list[tuple[CorpusDocument, Guide]] = []
    used = place_chunks
    for document, guide in guides:
        if used + len(document.chunks) > limit:
            break
        kept.append((document, guide))
        used += len(document.chunks)
    return kept
