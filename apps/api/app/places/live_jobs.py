"""In-process live import jobs (Amendment A2 §6.2; IMP-725): the runner, the claim and the reaper.

It copies the runner pattern of ``app.generation.jobs``: ``submit`` starts an asyncio task (kept by
a strong reference) after the queued row is committed, under this module's own semaphore
(``IMPORT_MAX_CONCURRENT``) and overall timeout (``IMPORT_TIMEOUT_S``). The API reaches ``submit``
through ``app.places.live_service.get_import_submitter``, which tests override; the import CLI
(``app.places.live_import``) and tests call ``run_import`` themselves.

Steps of one import: claim the queued row; fetch the places of its bounding box; normalise, dedupe
and cap; apply the minimum-places gate; then, in one transaction through the places service, store
the OpenStreetMap source, the places (upserted, missing ones deactivated, never deleted) and the
counts, write the place and guide documents of the RAG corpus in one load
(``rag.service.index_live_destination``; the guide sections are fetched before that transaction,
best effort) and complete the row. Embeddings are computed
after that commit (no transaction stays open across a provider call); an embedding failure leaves
the chunks without vectors, so generation uses ``lexical_fallback`` (IMD-112), and never fails the
import. A failed import leaves the destination's earlier places as they were.

Logs carry counts and destination ids only, never a place name, a city name or query text.
"""

import asyncio
import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Final
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers.base import ModelProvider
from app.core.config import Settings, get_settings
from app.db.models import Destination as DestinationRow
from app.db.session import transaction
from app.livedata.countries import capital
from app.livedata.factory import LiveProviders, get_providers
from app.livedata.normalise import choose_nearby_city, evaluate_gate, normalise
from app.livedata.providers.base import (
    BBox,
    GuideSourceProvider,
    LiveDataRateLimited,
    LiveDataTimeout,
    LiveDataUnavailable,
    PlacesProvider,
)
from app.places import service as places_service
from app.places.schemas import Destination
from app.rag import live_guides
from app.rag import service as rag_service

logger = logging.getLogger(__name__)

Sessions = Callable[[], AbstractAsyncContextManager[AsyncSession]]

IMPORT_MAX_CONCURRENT: Final = 1
IMPORT_TIMEOUT_S: Final = 300
IMPORT_STALE_AFTER_S: Final = 360
IMPORT_QUEUED_STALE_AFTER_S: Final = 600  # A2 §6.2: queued rows older than 10 minutes
REAPER_INTERVAL_S: Final = 60
NEARBY_CITY_RADIUS_KM: Final = 150

ImportOutcome = str  # completed, insufficient_data or failed

_slots = asyncio.Semaphore(IMPORT_MAX_CONCURRENT)
_tasks: set[asyncio.Task[None]] = set()  # strong references, so a running task is not collected


@dataclass(frozen=True)
class _Claimed:
    """What the job needs of the claimed row, read in the claim's transaction."""

    destination: Destination
    external_ref: str
    country_code: str
    bbox: BBox


class _NoLongerRunningError(Exception):
    """The row left ``running`` (reaped) while the job worked; its transaction is rolled back."""


def _claimed(row: DestinationRow) -> _Claimed:
    return _Claimed(
        destination=Destination.from_row(row),
        external_ref=row.external_ref or "",
        country_code=row.country_code,
        bbox=BBox(
            south=float(row.bbox_min_lat),
            west=float(row.bbox_min_lon),
            north=float(row.bbox_max_lat),
            east=float(row.bbox_max_lon),
        ),
    )


async def _claim(destination_id: UUID, sessions: Sessions) -> _Claimed | None:
    async with sessions() as session:
        row = await places_service.claim_live_import(session, destination_id, datetime.now(UTC))
        return _claimed(row) if row is not None else None


async def run_import(
    destination_id: UUID,
    *,
    providers: LiveProviders | None = None,
    sessions: Sessions = transaction,
    settings: Settings | None = None,
    embedder: ModelProvider | None = None,
) -> ImportOutcome | None:
    """Run one queued import to its end state; None when the row was not queued (not claimed)."""
    async with _slots:
        claimed = await _claim(destination_id, sessions)
        if claimed is None:
            logger.info("live import %s not claimed: not queued", destination_id)
            return None
        reason: str
        try:
            async with asyncio.timeout(IMPORT_TIMEOUT_S):
                live = providers or get_providers()
                return await _import(
                    claimed,
                    places=live.places,
                    guides=live.guides,
                    sessions=sessions,
                    settings=settings or get_settings(),
                    embedder=embedder,
                )
        except _NoLongerRunningError:
            logger.warning("live import %s was reaped while it ran", destination_id)
            return "failed"
        except (TimeoutError, LiveDataTimeout):
            reason = "timeout"
        except LiveDataRateLimited:
            reason = "rate_limited"
        except LiveDataUnavailable:
            reason = "provider_unavailable"
        except Exception:
            logger.exception("live import %s failed with an unexpected error", destination_id)
            reason = "internal"
        async with sessions() as session:
            changed = await places_service.fail_live_import(session, destination_id, reason)
        if changed:
            logger.warning("live import %s failed: %s", destination_id, reason)
        return "failed"


async def _import(
    claimed: _Claimed,
    *,
    places: PlacesProvider,
    guides: GuideSourceProvider,
    sessions: Sessions,
    settings: Settings,
    embedder: ModelProvider | None,
) -> ImportOutcome:
    destination = claimed.destination
    elements = await places.fetch(claimed.bbox)
    result = normalise(elements, destination_external_ref=claimed.external_ref, bbox=claimed.bbox)
    gate = evaluate_gate(result.places, min_usable=settings.live_min_usable_places)
    now = datetime.now(UTC)
    expires_at = now + timedelta(days=settings.live_data_ttl_days)
    if not gate.passed:
        nearby = await _nearby_city(places, claimed)
        async with sessions() as session:
            changed = await places_service.record_live_insufficient_data(
                session,
                destination.id,
                found=result.found,
                usable=gate.usable,
                nearby_city=nearby,
                expires_at=expires_at,
            )
        if not changed:
            raise _NoLongerRunningError
        logger.info(
            "live import %s insufficient_data found=%d usable=%d food=%d non_food=%d",
            destination.id,
            result.found,
            gate.usable,
            gate.food,
            gate.non_food,
        )
        return "insufficient_data"

    fetched = await rag_service.fetch_live_guides(guides, destination)
    sections = live_guides.sections_inside(fetched, claimed.bbox)
    if len(sections) < len(fetched):
        logger.info(
            "live import %s guide sections outside the box or without coordinates: %d",
            destination.id,
            len(fetched) - len(sections),
        )
    async with sessions() as session:
        stored = await places_service.store_live_places(
            session, destination.id, result.places, found=result.found, retrieved_on=now.date()
        )
        indexed = await rag_service.index_live_destination(
            session, destination, sections, retrieved_on=now.date(), now=now
        )
        if not await places_service.complete_live_import(
            session, destination.id, now=now, expires_at=expires_at
        ):
            raise _NoLongerRunningError
    logger.info(
        "live import %s completed found=%d usable=%d stored=%d deactivated=%d documents=%d "
        "guides=%d dropped_paragraphs=%d guides_capped=%d",
        destination.id,
        result.found,
        len(result.places),
        stored.stored,
        stored.deactivated,
        indexed.place_documents,
        indexed.guide_documents,
        indexed.dropped_paragraphs,
        indexed.guides_capped,
    )
    await _embed(destination.id, sessions, embedder)
    return "completed"


async def _nearby_city(places: PlacesProvider, claimed: _Claimed) -> str | None:
    """A2 §6.4: the largest city within 150 km, else the capital; never the settlement itself.

    The extra lookup is best effort: any error there falls back to the capital and never fails
    the import.
    """
    destination = claimed.destination
    found: str | None = None
    try:
        found = await places.largest_city_near(
            destination.center.lat, destination.center.lon, NEARBY_CITY_RADIUS_KM
        )
    except Exception as exc:  # best effort by A2 §6.4: logged, then the capital is used
        logger.warning(
            "live import %s nearby-city lookup failed: %s", destination.id, type(exc).__name__
        )
    return choose_nearby_city(destination.name, found, capital(claimed.country_code))


async def _embed(destination_id: UUID, sessions: Sessions, embedder: ModelProvider | None) -> None:
    """Embed the destination's chunks that have no vector; a provider failure is logged only."""
    report = await rag_service.embed_destinations(
        [destination_id], provider=embedder, sessions=sessions
    )
    if report.provider_failed:
        logger.warning(
            "live import %s embeddings incomplete: embedded=%d", destination_id, report.embedded
        )


def submit(destination_id: UUID) -> None:
    """Start the import; call it only after the queued row is committed (A2 §6.2)."""
    task = asyncio.create_task(_run_job(destination_id))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def _run_job(destination_id: UUID) -> None:
    await run_import(destination_id)


async def reap_stale_imports(session: AsyncSession, now: datetime) -> int:
    """Fail with ``timeout`` the imports running longer than 360 s or queued longer than 10 min."""
    return await places_service.reap_stale_live_imports(
        session,
        running_before=now - timedelta(seconds=IMPORT_STALE_AFTER_S),
        queued_before=now - timedelta(seconds=IMPORT_QUEUED_STALE_AFTER_S),
    )


async def reap_imports_forever() -> None:
    """Lifespan task, started only with ``any_city_mode`` ON: reap stale imports every 60 s."""
    while True:
        try:
            async with transaction() as session:
                count = await reap_stale_imports(session, datetime.now(UTC))
            if count:
                logger.warning("live import reaper failed %d stale imports", count)
        except Exception:  # the loop must survive a database outage; the next round retries
            logger.exception("live import reaper round failed")
        await asyncio.sleep(REAPER_INTERVAL_S)
