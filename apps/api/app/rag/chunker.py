"""Chunking of RAG documents (Amendment A1 §6.4). Pure: no I/O."""

import hashlib
import math
import re
from dataclasses import dataclass
from typing import Final

from app.rag.constants import RAG_CHUNK_MAX_CHARS, RAG_CHUNK_OVERLAP_CHARS

HEADING_MAX: Final = 200  # the rag_chunks CHECK
_HEADING = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_PARAGRAPH_BREAK = re.compile(r"\n\s*\n")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class Chunk:
    index: int
    heading: str | None
    content: str
    sha256: str
    token_estimate: int


def make_chunk(index: int, heading: str | None, content: str) -> Chunk:
    digest = hashlib.sha256(f"{heading or ''}\n{content}".encode()).hexdigest()
    return Chunk(index, heading, content, digest, math.ceil(len(content) / 4))


def _by_words(text: str) -> list[str]:
    """A last resort: pieces cut at word boundaries, and inside a word only if it fills a piece."""
    pieces: list[str] = []
    current = ""
    for word in text.split():
        while len(word) > RAG_CHUNK_MAX_CHARS:
            if current:
                pieces.append(current)
                current = ""
            pieces.append(word[:RAG_CHUNK_MAX_CHARS])
            word = word[RAG_CHUNK_MAX_CHARS:]
        joined = f"{current} {word}" if current else word
        if len(joined) > RAG_CHUNK_MAX_CHARS:
            pieces.append(current)
            joined = word
        current = joined
    return [*pieces, current] if current else pieces


def _pieces(paragraph: str) -> list[str]:
    """The paragraph, or its sentences (and their word pieces) when it is over the limit."""
    if len(paragraph) <= RAG_CHUNK_MAX_CHARS:
        return [paragraph]
    pieces: list[str] = []
    for sentence in _SENTENCE_END.split(paragraph):
        fits = len(sentence) <= RAG_CHUNK_MAX_CHARS
        pieces.extend([sentence] if fits else _by_words(sentence))
    return pieces


def _pack(section: str) -> list[str]:
    packed: list[str] = []
    current = ""
    for paragraph in _PARAGRAPH_BREAK.split(section.strip()):
        for piece in _pieces(paragraph.strip()):
            joined = f"{current}\n\n{piece}" if current else piece
            if current and len(joined) > RAG_CHUNK_MAX_CHARS:
                packed.append(current)
                joined = piece
            current = joined
    return [*packed, current] if current else packed


def _overlap(previous: str) -> str:
    """Up to 120 characters from the end of a chunk, starting at a sentence, else a word."""
    if len(previous) <= RAG_CHUNK_OVERLAP_CHARS:
        return previous
    tail = previous[-RAG_CHUNK_OVERLAP_CHARS:]
    sentence = _SENTENCE_END.search(tail)
    if sentence and sentence.end() < len(tail):
        return tail[sentence.end() :]
    return tail.split(maxsplit=1)[1] if " " in tail.strip() else ""


def _sections(body: str) -> list[tuple[str | None, str]]:
    parts = _HEADING.split(body)  # text, heading, text, heading, text ...
    sections: list[tuple[str | None, str]] = [(None, parts[0])]
    sections += [
        (heading[:HEADING_MAX], text)
        for heading, text in zip(parts[1::2], parts[2::2], strict=True)
    ]
    return sections


def chunk_guide(body: str) -> list[Chunk]:
    """Each section packed on its own; its heading is on every chunk of the section."""
    chunks: list[Chunk] = []
    for heading, text in _sections(body):
        previous = ""
        for packed in _pack(text):
            overlap = _overlap(previous)
            content = f"{overlap} {packed}" if overlap else packed
            chunks.append(make_chunk(len(chunks), heading, content))
            previous = packed
    return chunks
