"""Corpus indexing and retrieval (Amendment A1 §6.6, §6.7). ``resolve_sources`` comes with IMP-316.

``index`` loads the corpus and runs the gate, writes each destination in one transaction, then
embeds what is missing, one transaction per batch; none stays open across a provider call.
``retrieve`` embeds the query once, then runs the two similarity queries in one transaction. It
never raises for a retrieval failure: it answers ``lexical_fallback`` (§6.11, IMD-112).
"""

import logging
import time
from collections.abc import Callable, Mapping, Sequence
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Final, Literal
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.errors import ProviderError
from app.ai.factory import get_provider
from app.ai.providers.base import ModelProvider
from app.core.config import get_settings
from app.db.session import transaction
from app.places import service as places_service
from app.places.schemas import Destination
from app.rag import documents as corpus
from app.rag import guides as guide_gate
from app.rag import mmr, repository
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
    """One destination or all active ones. With gate errors under ``strict``, nothing is written."""
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
