"""The documents of the RAG corpus (Amendment A1 §6.2). Pure: no I/O.

A place document is built from the name, category, tags, description and address only, so prices,
hours and URLs of ``places`` cannot reach it.
"""

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Final, Literal
from uuid import UUID

from app.rag.chunker import Chunk, chunk_guide, make_chunk
from app.rag.guides import Guide

PLACE_MAX_TAGS: Final = 10
PLACE_MAX_ADDRESS: Final = 150
PLACE_MAX_TEXT: Final = 1200


@dataclass(frozen=True)
class CorpusDocument:
    kind: Literal["place", "guide"]
    doc_key: str
    title: str
    url: str | None
    retrieved_on: date | None
    content_sha256: str
    chunks: list[Chunk]
    place_id: UUID | None = None


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _cut_at_word(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    cut = text[: limit + 1].rsplit(maxsplit=1)[0]
    return cut if len(cut) <= limit else text[:limit]


def place_text(
    name: str, category: str, tags: Sequence[str], description: str | None, address: str | None
) -> str:
    parts = [f"{name} ({category})."]
    if tags:
        parts.append(f"Tags: {', '.join(tags[:PLACE_MAX_TAGS])}.")
    if description and description.strip():
        parts.append(description.strip())
    if address and address.strip():
        parts.append(f"Area: {address.strip()[:PLACE_MAX_ADDRESS]}")
    return _cut_at_word(" ".join(parts), PLACE_MAX_TEXT)


def place_document(
    place_id: UUID,
    name: str,
    category: str,
    tags: Sequence[str],
    description: str | None,
    address: str | None,
    retrieved_on: date | None,
) -> CorpusDocument:
    text = place_text(name, category, tags, description, address)
    return CorpusDocument(
        kind="place",
        doc_key=f"place:{place_id}",
        title=name,
        url=None,
        retrieved_on=retrieved_on,
        content_sha256=_hash(text),
        chunks=[make_chunk(0, None, text)],
        place_id=place_id,
    )


def guide_document(slug: str, stem: str, guide: Guide) -> CorpusDocument:
    return CorpusDocument(
        kind="guide",
        doc_key=f"guide:{slug}/{stem}",
        title=guide.title,
        url=guide.url,
        retrieved_on=guide.retrieved_on,
        content_sha256=_hash(guide.body),
        chunks=chunk_guide(guide.body),
    )
