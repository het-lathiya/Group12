"""Places service (MOD-B04): read-only use cases behind API-06, API-16 and API-17 (§6.6.3).

The session is the request's transaction (app.auth.deps.DbSession), as in trips/service.py. Only
active destinations and places are read. The seed writes the reference tables; the one write here
is ``ensure_data_source``, the source of a RAG guide (A1 §5.1).

Any-city mode (Amendment A2 §6.2; IMP-725): the live import job stores through this service: the
claim and end state of a live destination, the shared OpenStreetMap source and the live places,
upserted and deactivated in the job's one transaction (section at the end of this file).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Final
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound, ValidationFailed
from app.db.models import Destination as DestinationRow
from app.db.models import Place
from app.livedata.normalise import LivePlace
from app.places import repository
from app.places.schemas import Destination, PlaceOut, PlaceSummary
from app.schemas.common import ErrorDetail, Page


class DataSourceConflictError(Exception):
    """A source name already exists with another licence or attribution text (a gate error)."""


async def list_destinations(session: AsyncSession) -> list[Destination]:
    """API-06: the active destinations, ordered by name."""
    return [Destination.from_row(row) for row in await repository.active_destinations(session)]


async def search_places(
    session: AsyncSession,
    destination_id: UUID,
    *,
    q: str | None,
    categories: Sequence[str],
    tags: Sequence[str] = (),
    price_max: Decimal | None = None,
    duration_max_min: int | None = None,
    step_free: bool = False,
    near_lat: float | None = None,
    near_lon: float | None = None,
    max_distance_m: int | None = None,
    limit: int,
    offset: int,
) -> Page[PlaceSummary]:
    """API-16: active places of an active destination, filtered (IMP-604) and paged.

    An inactive or unknown destination is 404 NOT_FOUND: §6.2 makes inactive destinations
    invisible, so they answer like a missing one (IMD-127). ``near_lat`` and ``near_lon`` come
    together, and ``max_distance_m`` needs them; otherwise 422. No match is an empty page with
    total 0, for which the explore page explains which filters to relax (FR-017 AC2).
    """
    details = [
        ErrorDetail(field=name, message="Give near_lat and near_lon together.")
        for name, value, other in (
            ("near_lat", near_lat, near_lon),
            ("near_lon", near_lon, near_lat),
        )
        if value is None and other is not None
    ]
    near = (near_lat, near_lon) if near_lat is not None and near_lon is not None else None
    if max_distance_m is not None and near is None:
        details.append(ErrorDetail(field="max_distance_m", message="Needs near_lat and near_lon."))
    if details:
        raise ValidationFailed(details=details)
    destination = await repository.destination_by_id(session, destination_id)
    if destination is None or not destination.is_active:
        raise NotFound()
    rows, total = await repository.search_places(
        session,
        destination_id,
        repository.PlaceFilters(
            q=q.strip() if q else None,
            categories=categories,
            tags=tags,
            price_max=price_max,
            currency=destination.currency,
            duration_max_min=duration_max_min,
            step_free=step_free,
            near=near,
            max_distance_m=max_distance_m,
        ),
        limit=limit,
        offset=offset,
    )
    return Page[PlaceSummary](
        items=[PlaceSummary.from_row(row, source, distance) for row, source, distance in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


async def get_place(session: AsyncSession, place_id: UUID) -> PlaceOut:
    """API-17: one active place of an active destination with hours, source and labels; an
    inactive or unknown place is 404 (§6.2)."""
    found = await repository.active_place_detail(session, place_id)
    if found is None:
        raise NotFound()
    return PlaceOut.from_rows(*found)


async def active_place_names(
    session: AsyncSession, destination_id: UUID, place_ids: Sequence[UUID]
) -> dict[UUID, str]:
    """Name by id of the given places that are active in the destination, ordered by name.

    Used by the trips module (IMP-204) to check must-visit places and to name them; an id that
    is missing, inactive or of another destination is simply absent from the result.
    """
    rows = await repository.active_places_by_ids(session, destination_id, place_ids)
    return {row.id: row.name for row in rows}


async def active_place_summaries(
    session: AsyncSession, destination_id: UUID, place_ids: Sequence[UUID]
) -> list[PlaceSummary]:
    """The given places that are active in the destination, ordered by name (API-21, IMP-605)."""
    rows = await repository.active_places_by_ids(session, destination_id, place_ids)
    return [PlaceSummary.from_row(row) for row in rows]


async def active_places_with_source_date(
    session: AsyncSession, destination_id: UUID
) -> list[tuple[Place, date | None]]:
    """The RAG corpus of a destination's places (A1 §6.2)."""
    return await repository.active_places_with_source_date(session, destination_id)


async def active_places_by_refs(
    session: AsyncSession, destination_slug: str, refs: Sequence[tuple[str, str]]
) -> dict[tuple[str, str], PlaceSummary]:
    """Active places by ``(source_name, external_ref)``; a missing or inactive one is absent."""
    rows = await repository.active_places_by_refs(session, destination_slug, refs)
    return {
        (source, place.external_ref or ""): PlaceSummary.from_row(place) for source, place in rows
    }


async def data_source_terms(
    session: AsyncSession, names: Sequence[str]
) -> dict[str, tuple[str, str | None]]:
    """Licence and attribution text by name, for the sources that exist."""
    rows = await repository.data_sources_by_name(session, names)
    return {row.name: (row.licence, row.attribution_text) for row in rows}


async def ensure_data_source(
    session: AsyncSession,
    name: str,
    source_type: str,
    licence: str,
    url: str | None,
    retrieved_on: date | None,
    attribution_text: str | None,
) -> UUID:
    """The id of the source called ``name``, created if missing (A1 §5.1, §6.3).

    Several pages of one source share this row, and each page URL stays on its own document, so
    an existing row is left as it is. Different terms raise ``DataSourceConflictError``.
    """
    rows = await repository.data_sources_by_name(session, [name])
    if not rows:
        row = await repository.insert_data_source(
            session,
            name=name,
            source_type=source_type,
            licence=licence,
            url=url,
            retrieved_on=retrieved_on,
            attribution_text=attribution_text,
        )
        return row.id
    if (rows[0].licence, rows[0].attribution_text) != (licence, attribution_text):
        raise DataSourceConflictError(name)
    return rows[0].id


# ---------- Live import store (Amendment A2 §6.2 steps 3, 4 and 6; IMP-725 job runner) ----------

OSM_SOURCE_NAME: Final = "OpenStreetMap"
OSM_SOURCE_TYPE: Final = "osm_import"
OSM_LICENCE: Final = "ODbL 1.0"
OSM_ATTRIBUTION: Final = (
    "Place data © OpenStreetMap contributors, available under the Open Database Licence (ODbL)"
)
OSM_COPYRIGHT_URL: Final = "https://www.openstreetmap.org/copyright"
NEARBY_CITY_MAX_CHARS: Final = 120
_SIX_PLACES: Final = Decimal("0.000001")


@dataclass(frozen=True)
class LiveStoreResult:
    stored: int
    deactivated: int


async def claim_live_import(
    session: AsyncSession, destination_id: UUID, now: datetime
) -> DestinationRow | None:
    """The live destination moved from queued to running, or None when no row changed."""
    return await repository.claim_live_import(session, destination_id, now)


def _coordinate(value: float) -> Decimal:
    return Decimal(str(value)).quantize(_SIX_PLACES, rounding=ROUND_HALF_UP)


def _live_place_values(
    place: LivePlace, destination_id: UUID, source_id: UUID
) -> dict[str, object]:
    """The places columns of one normalised place: no price, no hours, no description (§6.3)."""
    return {
        "destination_id": destination_id,
        "source_id": source_id,
        "external_ref": place.external_ref,
        "name": place.name,
        "category": place.category.value,
        "tags": [tag.value for tag in place.tags],
        "description": None,
        "address": place.address,
        "lat": _coordinate(place.lat),
        "lon": _coordinate(place.lon),
        "typical_duration_min": place.typical_duration_min,
        "price_min": None,
        "price_max": None,
        "price_currency": None,
        "price_label": place.price_label.value,
        "hours_label": place.hours_label.value,
        "hours_checked_on": None,
        "verification_status": place.verification_status.value,
        "step_free": place.step_free,
        "child_friendly": None,
        "indoor": place.indoor,
        "website_url": place.website_url,
        "booking_url": None,
        "is_active": True,
    }


async def store_live_places(
    session: AsyncSession,
    destination_id: UUID,
    places: Sequence[LivePlace],
    *,
    found: int,
    retrieved_on: date,
) -> LiveStoreResult:
    """A2 §6.2 step 4, inside the caller's one transaction: the shared OpenStreetMap source,
    the places upserted by ``(source_id, external_ref)``, the destination's places missing from
    this run deactivated (never deleted), and the counts. No opening-hours rows are written."""
    source_id = await repository.upsert_data_source(
        session,
        name=OSM_SOURCE_NAME,
        source_type=OSM_SOURCE_TYPE,
        licence=OSM_LICENCE,
        url=OSM_COPYRIGHT_URL,
        retrieved_on=retrieved_on,
        attribution_text=OSM_ATTRIBUTION,
    )
    stored = await repository.upsert_places(
        session, [_live_place_values(place, destination_id, source_id) for place in places]
    )
    deactivated = await repository.deactivate_places_except(
        session, destination_id, source_id, [place.external_ref for place in places]
    )
    await repository.set_live_counts(session, destination_id, found=found, usable=len(places))
    return LiveStoreResult(stored=stored, deactivated=deactivated)


async def record_live_insufficient_data(
    session: AsyncSession,
    destination_id: UUID,
    *,
    found: int,
    usable: int,
    nearby_city: str | None,
    expires_at: datetime,
) -> bool:
    """A2 §6.4: only the destination row changes (counts, nearby city, expiry); it stays as it
    is otherwise. False when the import is no longer running."""
    city = nearby_city.strip()[:NEARBY_CITY_MAX_CHARS] if nearby_city else None
    return await repository.finish_live_import(
        session,
        destination_id,
        import_status="insufficient_data",
        import_failure_reason=None,
        places_found=found,
        places_usable=usable,
        nearby_city=city or None,
        expires_at=expires_at,
    )


async def complete_live_import(
    session: AsyncSession, destination_id: UUID, *, now: datetime, expires_at: datetime
) -> bool:
    """A2 §6.2 step 6: active and completed; False when the import is no longer running."""
    return await repository.finish_live_import(
        session,
        destination_id,
        is_active=True,
        import_status="completed",
        import_failure_reason=None,
        nearby_city=None,
        imported_at=now,
        expires_at=expires_at,
    )


async def fail_live_import(session: AsyncSession, destination_id: UUID, reason: str) -> bool:
    """A failed import keeps the destination's earlier places and activity as they were."""
    return await repository.finish_live_import(
        session, destination_id, import_status="failed", import_failure_reason=reason
    )


async def reap_stale_live_imports(
    session: AsyncSession, *, running_before: datetime, queued_before: datetime
) -> int:
    return await repository.reap_live_imports(
        session, running_before=running_before, queued_before=queued_before
    )
