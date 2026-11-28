"""Any-city use cases behind API-76 to API-79 (Amendment A2 §5, §6.1; IMP-725).

City search goes to the geocoder only on an explicit request and is cached in process for 24 hours.
Resolve looks the OSM reference up again (the client never supplies coordinates, names or a
country), builds the live destination row from the geocoder and the country table, and queues
its import through the runner's submit dependency after the row is committed. Destinations are
reference data: every signed-in user reads them, and ``import_requested_by`` only counts the daily
cap and is never returned.

The search text goes only to the geocoder and never reaches a log; logs keep counts and ids.
"""

import importlib
import logging
import re
import time
import unicodedata
from collections import OrderedDict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Final
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import NotFound, RateLimited, ServiceUnavailable, ValidationFailed
from app.db.models import Destination as DestinationRow
from app.livedata.countries import choose_timezone, clip_bbox, country
from app.livedata.providers.base import (
    SETTLEMENT_KINDS,
    GeoCandidate,
    GeocodingProvider,
    LiveDataError,
)
from app.livedata.throttle import overpass_retry_after_s
from app.places import repository
from app.places.live_schemas import (
    Attribution,
    CityCandidate,
    CitySearchOut,
    DataTier,
    DestinationDetailOut,
    ImportState,
    LiveDestinationOut,
)
from app.places.schemas import Destination
from app.schemas.common import ErrorDetail

logger = logging.getLogger(__name__)

PROVIDER: Final = "osm"
SEARCH_MIN_CHARS: Final = 2
SEARCH_MAX_CHARS: Final = 100
SEARCH_MAX_RESULTS: Final = 8
SEARCH_CACHE_TTL_S: Final = 86400  # A2 §6.1: code constant
SEARCH_CACHE_MAX_KEYS: Final = 1000
SLUG_NAME_MAX_CHARS: Final = 40
NAME_MAX_CHARS: Final = 120
CAP_WINDOW: Final = timedelta(hours=24)

NOT_A_SETTLEMENT: Final = "Choose a city, town or village"
COUNTRY_NOT_SUPPORTED: Final = "This country is not supported yet"
GEOCODER_UNAVAILABLE: Final = "City search is not available right now. Try again in a few minutes."
DAILY_CAP_REACHED: Final = "The daily limit for new cities is reached. Try again tomorrow."
GUIDE_SOURCES: Final = frozenset({"Wikivoyage", "Wikipedia"})  # A2 §6.5 live guide sources

ImportSubmitter = Callable[[UUID], None]
_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")
_SIX_PLACES = Decimal("0.000001")


class _SearchCache:
    """Per-process cache of geocoder candidates by normalised query (A2 §6.1)."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._entries: OrderedDict[str, tuple[float, list[GeoCandidate]]] = OrderedDict()

    def get(self, key: str) -> list[GeoCandidate] | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        stored_at, candidates = entry
        if self._clock() - stored_at >= SEARCH_CACHE_TTL_S:
            del self._entries[key]
            return None
        self._entries.move_to_end(key)
        return candidates

    def put(self, key: str, candidates: list[GeoCandidate]) -> None:
        self._entries[key] = (self._clock(), candidates)
        self._entries.move_to_end(key)
        while len(self._entries) > SEARCH_CACHE_MAX_KEYS:
            self._entries.popitem(last=False)

    def clear(self) -> None:
        self._entries.clear()


search_cache = _SearchCache()


def clean_query(raw: str) -> str:
    """Strip control characters and surrounding space; 2 to 100 characters, else 422."""
    text = " ".join(_CONTROL.sub(" ", raw).split())
    if not SEARCH_MIN_CHARS <= len(text) <= SEARCH_MAX_CHARS:
        raise ValidationFailed(
            details=[
                ErrorDetail(
                    field="q",
                    message=f"Type {SEARCH_MIN_CHARS} to {SEARCH_MAX_CHARS} characters.",
                )
            ]
        )
    return text


async def search(
    session: AsyncSession, geocoder: GeocodingProvider, raw_query: str
) -> CitySearchOut:
    """API-76: settlements only, at most 8, each marked when it is already a destination."""
    query = clean_query(raw_query)
    key = query.casefold()
    candidates = search_cache.get(key)
    if candidates is None:
        try:
            found = await geocoder.search(query)
        except LiveDataError:
            raise ServiceUnavailable(GEOCODER_UNAVAILABLE) from None
        candidates = [c for c in found if c.kind in SETTLEMENT_KINDS][:SEARCH_MAX_RESULTS]
        search_cache.put(key, candidates)
    known = await repository.destinations_by_refs(
        session, PROVIDER, [c.osm_ref for c in candidates]
    )
    logger.info("city search results=%d known=%d", len(candidates), len(known))
    return CitySearchOut(
        results=[
            CityCandidate(
                osm_ref=c.osm_ref,
                name=c.name,
                display_name=c.display_name,
                region=c.region,
                country_code=c.country_code,
                lat=c.lat,
                lon=c.lon,
                kind=c.kind,
                destination_id=known[c.osm_ref].id if c.osm_ref in known else None,
                data_tier=_tier(known[c.osm_ref]) if c.osm_ref in known else None,
            )
            for c in candidates
        ]
    )


def live_slug(name: str, external_ref: str) -> str:
    """`live-` + ASCII transliteration (cut to 40) + `-` + the reference (A2 §6.1)."""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    words = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")
    words = words[:SLUG_NAME_MAX_CHARS].strip("-")
    ref = external_ref.lower()
    return f"live-{words}-{ref}" if words else f"live-{ref}"


@dataclass(frozen=True)
class ResolveResult:
    destination: LiveDestinationOut
    queued: bool  # True: a new or repeated import was queued (202); False: as it is (200)


async def resolve(
    session: AsyncSession,
    settings: Settings,
    user_id: UUID,
    osm_ref: str,
    geocoder: GeocodingProvider,
    submit: ImportSubmitter,
    now: datetime | None = None,
) -> ResolveResult:
    """API-77: the live destination of one settlement, created and queued when new."""
    now = now or datetime.now(UTC)
    existing = await repository.destination_by_ref(session, PROVIDER, osm_ref)
    if existing is not None:
        return await _existing(session, existing, submit, now)

    try:
        place = await geocoder.lookup(osm_ref)
    except LiveDataError:
        raise ServiceUnavailable(GEOCODER_UNAVAILABLE) from None
    if place is None:
        raise NotFound()
    if place.kind not in SETTLEMENT_KINDS:
        raise ValidationFailed(NOT_A_SETTLEMENT)
    facts = country(place.country_code)
    timezone = choose_timezone(place.country_code, place.lat, place.lon)
    if facts is None or timezone is None:
        raise ValidationFailed(COUNTRY_NOT_SUPPORTED)

    since = now - CAP_WINDOW
    if (
        await repository.imports_started_since(session, since, user_id)
        >= settings.live_daily_imports_per_user
        or await repository.imports_started_since(session, since)
        >= settings.live_daily_imports_global
    ):
        raise RateLimited(DAILY_CAP_REACHED)

    name = (place.name_en or place.name).strip()[:NAME_MAX_CHARS]
    box = clip_bbox(place.lat, place.lon, place.bbox)
    row = DestinationRow(
        slug=live_slug(name, osm_ref),
        name=name,
        region=place.region,
        country_code=facts.code,
        timezone=timezone,
        currency=facts.currency,
        center_lat=_six(place.lat),
        center_lon=_six(place.lon),
        bbox_min_lat=_six(box.south),
        bbox_max_lat=_six(box.north),
        bbox_min_lon=_six(box.west),
        bbox_max_lon=_six(box.east),
        is_active=False,
        is_sample=False,
        data_tier="live",
        provider=PROVIDER,
        external_ref=osm_ref,
        import_status="queued",
        import_requested_by=user_id,
    )
    try:
        async with session.begin_nested():
            row = await repository.insert_live_destination(session, row)
    except IntegrityError:
        # Another request resolved the same settlement first: answer with that row.
        raced = await repository.destination_by_ref(session, PROVIDER, osm_ref)
        if raced is None:
            raise
        return ResolveResult(live_destination_out(raced), queued=False)
    await session.commit()  # the job reads the row in its own transaction
    submit(row.id)
    logger.info("live destination %s queued", row.id)
    return ResolveResult(live_destination_out(row), queued=True)


async def _existing(
    session: AsyncSession, row: DestinationRow, submit: ImportSubmitter, now: datetime
) -> ResolveResult:
    expired = row.expires_at is not None and row.expires_at <= now
    if row.import_status == "failed" or (row.import_status == "completed" and expired):
        if retry_after_s := overpass_retry_after_s():
            raise RateLimited(
                "The map data service is busy. Try again after the cooldown.",
                retry_after_s=retry_after_s,
            )
        await repository.requeue_live_import(session, row.id)
        # Load the response while the request's transaction is still open. Committing inside
        # session.begin() closes it, so a refresh after commit raises InvalidRequestError.
        await session.refresh(row)
        result = live_destination_out(row)
        await session.commit()
        submit(row.id)
        logger.info("live destination %s queued again", row.id)
        return ResolveResult(result, queued=True)
    return ResolveResult(live_destination_out(row), queued=False)


async def import_state(session: AsyncSession, destination_id: UUID) -> LiveDestinationOut:
    """API-78: the import state of a live destination; unknown or curated is 404."""
    row = await repository.destination_by_id(session, destination_id)
    if row is None or row.data_tier != "live":
        raise NotFound()
    return live_destination_out(row)


async def destination_detail(session: AsyncSession, destination_id: UUID) -> DestinationDetailOut:
    """API-79: a curated or live destination with its tier, attribution and import state."""
    row = await repository.destination_by_id(session, destination_id)
    if row is None or (not row.is_active and row.data_tier != "live"):
        raise NotFound()
    sources = await repository.destination_sources(session, row.id)
    attribution = [
        Attribution(
            source_name=source.name,
            licence=source.licence,
            attribution_text=source.attribution_text,
            url=source.url,
        )
        for source in sources
        if row.data_tier != "live" or source.name not in GUIDE_SOURCES
    ]
    if row.data_tier == "live":
        attribution += guide_page_attribution(await repository.live_guide_pages(session, row.id))
    item = Destination.from_row(row)
    return DestinationDetailOut.model_validate(
        {
            **item.model_dump(),
            "data_tier": _tier(row),
            "imported_at": row.imported_at,
            "attribution": attribution,
            "import": _import_state(row) if row.data_tier == "live" else None,
        }
    )


def guide_page_attribution(
    pages: Sequence[tuple[str, str, str, str | None]],
) -> list[Attribution]:
    """One A2 §9.3 entry per live guide page, from the stored guide documents (no migration).

    A live guide document's title is "<Source>: <page title> — <section>" (IMP-726), so the page
    title is the text between the source prefix and the last " — "; documents of one page share
    its URL and give one entry.
    """
    entries: dict[tuple[str, str], Attribution] = {}
    for source_name, licence, title, url in pages:
        if source_name not in GUIDE_SOURCES:
            continue
        page = title.removeprefix(f"{source_name}: ").rsplit(" — ", 1)[0].strip()
        key = (source_name, url or page)
        if page and key not in entries:
            entries[key] = Attribution(
                source_name=source_name,
                licence=licence,
                attribution_text=(
                    f"Guide text from {source_name} ({page}), by its contributors, under "
                    f"{licence}; excerpts, some sections left out"
                ),
                url=url,
            )
    return list(entries.values())


def live_destination_out(row: DestinationRow) -> LiveDestinationOut:
    return LiveDestinationOut(
        destination_id=row.id,
        slug=row.slug,
        name=row.name,
        region=row.region,
        country_code=row.country_code,
        timezone=row.timezone,
        currency=row.currency,
        data_tier="live",
        import_=_import_state(row),  # alias "import"; populate_by_name
    )


def _import_state(row: DestinationRow) -> ImportState:
    return ImportState.model_validate(
        {
            "status": row.import_status,
            "failure_reason": row.import_failure_reason,
            "places_found": row.places_found,
            "places_usable": row.places_usable,
            "nearby_city": row.nearby_city,
            "started_at": row.import_started_at,
            "imported_at": row.imported_at,
            "expires_at": row.expires_at,
        }
    )


def _tier(row: DestinationRow) -> DataTier:
    return "live" if row.data_tier == "live" else "curated"


def _six(value: float) -> Decimal:
    return Decimal(str(value)).quantize(_SIX_PLACES, rounding=ROUND_HALF_UP)


def get_import_submitter() -> ImportSubmitter:
    """FastAPI dependency: the live import runner's submit (IMP-725 job runner); tests override."""
    # Imported on use, so this module does not depend on the runner at import time (the runner
    # imports the places service and repository).
    runner = importlib.import_module("app.places.live_jobs")
    submitter: ImportSubmitter = runner.submit
    return submitter
