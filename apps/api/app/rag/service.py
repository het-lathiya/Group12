"""Corpus indexing, retrieval and citations (Amendment A1 §6.6, §6.7, §6.10).

``index`` loads the corpus and runs the gate, writes each destination in one transaction, then
embeds what is missing, one transaction per batch; none stays open across a provider call.
``retrieve`` embeds the query once, then runs the two similarity queries in one transaction. It
never raises for a retrieval failure: it answers ``lexical_fallback`` (§6.11, IMD-112).
``resolve_sources`` turns saved citations into their provenance on read.
"""

import logging
import time
from collections.abc import Callable, Mapping, Sequence
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Final, Literal
from uuid import UUID

from sqlalchemy import Row
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.errors import ProviderError
from app.ai.factory import get_provider
from app.ai.providers.base import ModelProvider
from app.core.config import get_settings
from app.db.session import transaction
from app.livedata.providers.base import GuideSourceProvider, LiveDataError, WikiSection
from app.places import service as places_service
from app.places.schemas import Destination
from app.rag import documents as corpus
from app.rag import guides as guide_gate
from app.rag import live_guides, mmr, repository
from app.rag.constants import RAG_EMBED_BATCH, RAG_GUIDE_CANDIDATES
from app.rag.documents import CorpusDocument
from app.rag.guides import Guide, GuideFinding
from app.rag.mmr import RetrievedChunk

logger = logging.getLogger(__name__)

Sessions = Callable[[], AbstractAsyncContextManager[AsyncSession]]

SAMPLE_ENVIRONMENTS: Final = frozenset({"local", "test"})  # IMD-15
NOT_A_GUIDE: Final = "quality_report.md"
EXIT_OK: Final = 0
EXIT_GATE: Final = 1
EXIT_PROVIDER: Final = 3


RetrievalMode = Literal["vector", "lexical_fallback"]


@dataclass(frozen=True)
class RetrievalContext:
    destination_id: UUID
    query_text: str
    place_ids: Sequence[UUID]  # the candidates that passed the hard filters


@dataclass(frozen=True)
class RetrievalResult:
    mode: RetrievalMode
    embedding_model_id: str | None
    place_similarity: Mapping[UUID, float]
    place_best_chunk: Mapping[UUID, RetrievedChunk]
    guide_passages: Sequence[RetrievedChunk]
    retrieval_ms: int


class UnknownDestinationError(Exception):
    """``--destination`` names no active destination (exit 2)."""


@dataclass
class IndexReport:
    strict: bool = False
    documents: int = 0
    chunks: int = 0
    embedded: int = 0
    inactive: int = 0
    findings: list[GuideFinding] = field(default_factory=list)
    provider_failed: bool = False

    @property
    def warnings(self) -> int:
        return sum(finding.severity == "warning" for finding in self.findings)

    @property
    def errors(self) -> int:
        return sum(finding.severity == "error" for finding in self.findings)

    @property
    def exit_code(self) -> int:
        if self.strict and self.errors:
            return EXIT_GATE
        return EXIT_PROVIDER if self.provider_failed else EXIT_OK


@dataclass(frozen=True)
class _Loaded:
    destination: Destination
    places: list[tuple[CorpusDocument, UUID]]  # with the place's data source
    guides: list[tuple[CorpusDocument, Guide]]

    def keys(self) -> set[str]:
        return {doc.doc_key for doc, _ in self.places} | {doc.doc_key for doc, _ in self.guides}


def data_root() -> Path:
    """``data/`` beside the working directory (image) or above it (``make`` runs in apps/api)."""
    cwd = Path.cwd()
    return next((p / "data" for p in (cwd, *cwd.parents) if (p / "data").is_dir()), cwd / "data")


def _guide_dir(root: Path, destination: Destination) -> Path:
    if destination.is_sample:
        return root / "fixtures" / destination.slug / "guides"
    return root / "guides" / destination.slug


def _read_guides(
    root: Path, destination: Destination, *, today: date, strict: bool
) -> tuple[list[tuple[str, Guide]], list[GuideFinding]]:
    """(file stem, guide) of the files that pass the gate, and the findings of all of them."""
    sample_allowed = get_settings().app_env in SAMPLE_ENVIRONMENTS
    passed: list[tuple[str, Guide]] = []
    findings: list[GuideFinding] = []
    for path in sorted(_guide_dir(root, destination).glob("*.md")):
        if path.name == NOT_A_GUIDE:
            continue
        name = str(path.relative_to(root))
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            findings.append(GuideFinding(name, 1, "error", "not_utf8"))
            continue
        guide, found = guide_gate.check_guide(
            name,
            text,
            today=today,
            strict=strict,
            sample_fixture=destination.is_sample,
            sample_allowed=sample_allowed,
        )
        findings += found
        if guide is not None:
            passed.append((path.stem, guide))
    return passed, findings


async def _load(
    session: AsyncSession,
    destination: Destination,
    root: Path,
    report: IndexReport,
    terms: dict[str, tuple[str, str | None]],
    *,
    today: date,
    strict: bool,
) -> _Loaded:
    """``terms`` carries the source terms of this run across destinations."""
    read, findings = _read_guides(root, destination, today=today, strict=strict)
    stored = await places_service.data_source_terms(
        session, sorted({guide.source_name for _, guide in read})
    )
    terms.update(stored)
    kept, conflicts = guide_gate.check_sources([guide for _, guide in read], terms)
    terms.update({guide.source_name: (guide.licence, guide.attribution_text) for guide in kept})
    report.findings += findings + conflicts

    places = [
        (
            corpus.place_document(
                place.id,
                place.name,
                place.category,
                place.tags,
                place.description,
                place.address,
                retrieved_on,
            ),
            place.source_id,
        )
        for place, retrieved_on in await places_service.active_places_with_source_date(
            session, destination.id
        )
    ]
    guides = [
        (corpus.guide_document(destination.slug, stem, guide), guide)
        for stem, guide in read
        if guide in kept
    ]
    return _Loaded(destination, places, guides)


async def _write(session: AsyncSession, loaded: _Loaded) -> None:
    destination_id = loaded.destination.id
    for document, source_id in loaded.places:
        await repository.save_document(session, destination_id, document, source_id)
    for document, guide in loaded.guides:
        source_id = await places_service.ensure_data_source(
            session,
            guide.source_name,
            guide.source_type,
            guide.licence,
            guide.url,
            guide.retrieved_on,
            guide.attribution_text,
        )
        await repository.save_document(session, destination_id, document, source_id)
    await repository.deactivate_missing(session, destination_id, loaded.keys())


async def _embed(
    provider: ModelProvider,
    sessions: Sessions,
    destination_ids: Sequence[UUID],
    report: IndexReport,
) -> None:
    async with sessions() as session:
        pending = await repository.pending_chunks(
            session, provider.embedding_model_id, destination_ids
        )
    for start in range(0, len(pending), RAG_EMBED_BATCH):
        batch = pending[start : start + RAG_EMBED_BATCH]
        result = await provider.embed_texts(
            [content for _, content, _ in batch],
            "document",
            titles=[title for _, _, title in batch],
        )
        async with sessions() as session:
            await repository.store_embeddings(
                session, [chunk_id for chunk_id, _, _ in batch], result.vectors, result.model_id
            )
        report.embedded += len(batch)


@dataclass(frozen=True)
class LiveIndexReport:
    """What one live index write stored (A2 §6.5); counts only, safe to log."""

    place_documents: int
    guide_documents: int
    chunks: int
    dropped_paragraphs: int
    skipped_sections: int
    guides_capped: int  # guide documents left out by the per-destination or the global cap
    deactivated_destinations: int  # expired live destinations whose chunks made room


async def fetch_live_guides(
    provider: GuideSourceProvider, destination: Destination
) -> list[WikiSection]:
    """The guide sections of a live destination; best effort, outside any transaction.

    A guide source failure stores the places without guides and never fails the import (the
    places are the import; guides only add passages).
    """
    try:
        return await provider.fetch(
            destination.name, destination.center.lat, destination.center.lon
        )
    except LiveDataError as exc:
        logger.warning("live guides for %s not fetched: %s", destination.id, type(exc).__name__)
        return []


async def index_live_destination(
    session: AsyncSession,
    destination: Destination,
    guide_sections: Sequence[WikiSection],
    *,
    retrieved_on: date,
    now: datetime,
) -> LiveIndexReport:
    """Write the place and guide documents of one live destination in one load (A2 §6.5).

    Runs in the caller's transaction; embeddings come after it (``embed_destinations``). Places and
    guides share one key set, so the deactivation of documents that left the corpus touches
    neither the destination's other kind nor any other destination. Caps (IMD-107): at most 400
    chunks for the destination, place documents first; when all active chunks would pass 5,000,
    the oldest expired live destinations are deactivated first, and if that is not enough the
    places are stored without guides.
    """
    places = [
        (
            live_guides.live_place_document(
                corpus.place_document(
                    place.id,
                    place.name,
                    place.category,
                    place.tags,
                    place.description,
                    place.address,
                    source_date,
                )
            ),
            place.source_id,
        )
        for place, source_date in await places_service.active_places_with_source_date(
            session, destination.id
        )
    ]
    place_chunks = live_guides.chunk_count(doc for doc, _ in places)
    built = live_guides.build_guides(destination.slug, guide_sections, retrieved_on)
    guides = live_guides.cap_guides(place_chunks, built.guides)

    others = await repository.count_active_chunks(session, excluding=destination.id)
    deactivated = 0
    needed = place_chunks + live_guides.chunk_count(doc for doc, _ in guides)
    if others + needed > live_guides.RAG_MAX_ACTIVE_CHUNKS:
        for expired_id, count in await repository.expired_live_destinations(
            session, now, excluding=destination.id
        ):
            await repository.deactivate_destination_documents(session, expired_id)
            deactivated += 1
            others -= count
            if others + needed <= live_guides.RAG_MAX_ACTIVE_CHUNKS:
                break
    if guides and others + needed > live_guides.RAG_MAX_ACTIVE_CHUNKS:
        logger.warning(
            "live index %s: corpus cap reached, places stored without guides", destination.id
        )
        guides = []

    for document, source_id in places:
        await repository.save_document(session, destination.id, document, source_id)
    sources: dict[str, UUID] = {}
    for document, guide in guides:
        if guide.source_name not in sources:
            sources[guide.source_name] = await places_service.ensure_data_source(
                session,
                guide.source_name,
                guide.source_type,
                guide.licence,
                live_guides.SOURCE_URLS[guide.source_name],
                retrieved_on,
                live_guides.attribution_text(guide.source_name),
            )
        await repository.save_document(
            session, destination.id, document, sources[guide.source_name]
        )
    keys = {doc.doc_key for doc, _ in places} | {doc.doc_key for doc, _ in guides}
    await repository.deactivate_missing(session, destination.id, keys)
    return LiveIndexReport(
        place_documents=len(places),
        guide_documents=len(guides),
        chunks=place_chunks + live_guides.chunk_count(doc for doc, _ in guides),
        dropped_paragraphs=built.dropped_paragraphs,
        skipped_sections=built.skipped_sections,
        guides_capped=len(built.guides) - len(guides),
        deactivated_destinations=deactivated,
    )


async def embed_destinations(
    destination_ids: Sequence[UUID],
    *,
    provider: ModelProvider | None = None,
    sessions: Sessions = transaction,
) -> IndexReport:
    """Embed the destinations' active chunks that have no vector from the active model.

    A provider failure stops it with ``provider_failed`` set and the chunks left without vectors,
    so generation uses ``lexical_fallback`` (IMD-112); ``embedded`` counts what was stored.
    """
    report = IndexReport()
    try:
        await _embed(provider or get_provider(), sessions, destination_ids, report)
    except ProviderError as exc:
        report.provider_failed = True
        logger.warning(
            "embeddings incomplete (%s): embedded=%d", exc.failure_reason, report.embedded
        )
    return report


async def index(
    destination_slug: str | None = None,
    check_only: bool = False,
    strict: bool = False,
    *,
    provider: ModelProvider | None = None,
    sessions: Sessions = transaction,
    root: Path | None = None,
    today: date | None = None,
) -> IndexReport:
    """One curated destination or all active curated ones (the release task, A2 §6.5): live
    destinations are indexed by their import job (``index_live_destination``) and never here.
    With gate errors under ``strict``, nothing is written."""
    report = IndexReport(strict=strict)
    root = root or data_root()
    today = today or date.today()
    terms: dict[str, tuple[str, str | None]] = {}
    async with sessions() as session:
        destinations = await places_service.list_destinations(session)
        if destination_slug is not None:
            destinations = [d for d in destinations if d.slug == destination_slug]
            if not destinations:
                raise UnknownDestinationError(destination_slug)
        loaded = [
            await _load(session, destination, root, report, terms, today=today, strict=strict)
            for destination in destinations
        ]
    report.documents = sum(len(item.keys()) for item in loaded)
    report.chunks = sum(
        len(doc.chunks) for item in loaded for doc, _ in (*item.places, *item.guides)
    )
    if check_only or report.exit_code == EXIT_GATE:
        return report

    for item in loaded:
        async with sessions() as session:
            await _write(session, item)

    destination_ids = [item.destination.id for item in loaded]
    try:
        await _embed(provider or get_provider(), sessions, destination_ids, report)
    except ProviderError:
        report.provider_failed = True
    async with sessions() as session:
        report.inactive = await repository.count_inactive_documents(session, destination_ids)
    return report


async def retrieve(
    ctx: RetrievalContext,
    *,
    provider: ModelProvider | None = None,
    sessions: Sessions = transaction,
) -> RetrievalResult:
    """Place similarities, each place's best chunk and the guide passages of one generation.

    ``app.rag`` must not import the ranking, so the generation module picks the place passages
    after ranking (A1 §8.2). Runs outside any transaction: the embedding is a provider call.
    """
    started = time.perf_counter()
    active = provider or get_provider()

    def elapsed_ms() -> int:
        return round((time.perf_counter() - started) * 1000)

    def fallback(kind: str) -> RetrievalResult:
        logger.warning("retrieval fell back to lexical ranking: %s", kind)
        return RetrievalResult(
            "lexical_fallback", active.embedding_model_id or None, {}, {}, [], elapsed_ms()
        )

    try:
        embedded = await active.embed_texts([ctx.query_text], "query")
        query_vector = embedded.vectors[0]
        async with sessions() as session:
            places = await repository.best_place_chunks(
                session, ctx.destination_id, embedded.model_id, query_vector, ctx.place_ids
            )
            guides = await repository.top_guide_chunks(
                session, ctx.destination_id, embedded.model_id, query_vector, RAG_GUIDE_CANDIDATES
            )
    except ProviderError as exc:
        return fallback(exc.failure_reason)
    except SQLAlchemyError as exc:
        return fallback(type(exc).__name__)
    if not places and not guides:
        return fallback("no_index")
    best = {chunk.place_id: chunk for chunk in places if chunk.place_id is not None}
    return RetrievalResult(
        "vector",
        embedded.model_id,
        {place_id: chunk.similarity for place_id, chunk in best.items()},
        best,
        mmr.select(guides),
        elapsed_ms(),
    )


async def resolve_sources(session: AsyncSession, chunk_ids: Sequence[UUID]) -> dict[UUID, Row[Any]]:
    """The SourceRef fields of each chunk that still exists, by chunk ID, in one query (A1 §7.1)."""
    if not chunk_ids:
        return {}
    rows = await repository.source_rows(session, set(chunk_ids))
    return {row.chunk_id: row for row in rows}


async def document_keys(session: AsyncSession, document_ids: Sequence[UUID]) -> dict[UUID, str]:
    """``doc_key`` by document ID, so the retrieval evaluation can score guide passages (IMP-318)."""
    return await repository.document_keys(session, set(document_ids))
