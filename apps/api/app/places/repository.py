"""Read-only queries over the place reference tables (MOD-B04; §6.6.3 API-06, API-16, API-17).

Destinations and places are shared reference data with no owner, so no query takes a user_id;
every query reads active rows only (§6.2: inactive destinations and places are invisible). Only
the seed writes these tables, except that ``insert_data_source`` adds the source of a guide (A1 §5.1).

Any-city mode (Amendment A2 §5, §6.1; IMP-725): the live-destination reads, the resolve-time
insert and re-queue of a live destination row, and the attribution read. API-06 lists curated
destinations only. The live import job (A2 §6.2) writes, through the places service, the claim and
state of a live destination, the shared OpenStreetMap source and the live places (section at the
end of this file).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    ColumnElement,
    Text,
    and_,
    func,
    literal,
    null,
    or_,
    select,
    tuple_,
    update,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DataSource, Destination, Place, PlaceOpeningHours, RagDocument
from app.routing.estimate import EARTH_RADIUS_M


async def active_destinations(session: AsyncSession) -> Sequence[Destination]:
    """API-06: active curated destinations (A2 §5: live ones are reached through API-76 to 79)."""
    query = (
        select(Destination)
        .where(Destination.is_active.is_(True), Destination.data_tier == "curated")
        .order_by(Destination.name, Destination.id)
    )
    return (await session.scalars(query)).all()


async def destinations_by_refs(
    session: AsyncSession, provider: str, external_refs: Sequence[str]
) -> dict[str, Destination]:
    """Destinations already resolved for these OSM references, keyed by reference."""
    if not external_refs:
        return {}
    query = select(Destination).where(
        Destination.provider == provider, Destination.external_ref.in_(list(external_refs))
    )
    return {row.external_ref: row for row in await session.scalars(query) if row.external_ref}


async def destination_by_ref(
    session: AsyncSession, provider: str, external_ref: str
) -> Destination | None:
    query = select(Destination).where(
        Destination.provider == provider, Destination.external_ref == external_ref
    )
    return (await session.scalars(query)).first()


async def imports_started_since(
    session: AsyncSession, since: datetime, user_id: UUID | None = None
) -> int:
    """New live imports started since ``since``: by ``user_id``, or by everyone (A2 §6.1 caps).

    A queued row has no ``import_started_at`` yet, so its creation time counts until then.
    """
    started = func.coalesce(Destination.import_started_at, Destination.created_at)
    query = select(func.count()).where(Destination.data_tier == "live", started >= since)
    if user_id is not None:
        query = query.where(Destination.import_requested_by == user_id)
    return int(await session.scalar(query) or 0)


async def insert_live_destination(session: AsyncSession, row: Destination) -> Destination:
    """Add a resolved live destination (queued, inactive); the caller handles a duplicate ref."""
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def requeue_live_import(session: AsyncSession, destination_id: UUID) -> None:
    """Queue a failed or expired live import again (A2 §6.1); places stay as they are."""
    await session.execute(
        update(Destination)
        .where(Destination.id == destination_id, Destination.data_tier == "live")
        .values(
            import_status="queued",
            import_failure_reason=None,
            nearby_city=None,
            import_started_at=None,
            updated_at=func.now(),
        )
    )


async def destination_sources(session: AsyncSession, destination_id: UUID) -> list[DataSource]:
    """Sources of the destination's active places and active guide documents (API-79)."""
    place_sources = select(Place.source_id).where(
        Place.destination_id == destination_id, Place.is_active.is_(True)
    )
    guide_sources = select(RagDocument.source_id).where(
        RagDocument.destination_id == destination_id,
        RagDocument.kind == "guide",
        RagDocument.is_active.is_(True),
    )
    query = (
        select(DataSource)
        .where(or_(DataSource.id.in_(place_sources), DataSource.id.in_(guide_sources)))
        .order_by(DataSource.name)
    )
    return list((await session.scalars(query)).all())


async def live_guide_pages(
    session: AsyncSession, destination_id: UUID
) -> list[tuple[str, str, str, str | None]]:
    """(source name, licence, document title, page URL) of the destination's active guide
    documents, in title order (API-79 per-page attribution, A2 §9.3). Read only."""
    query = (
        select(DataSource.name, DataSource.licence, RagDocument.title, RagDocument.url)
        .join(DataSource, DataSource.id == RagDocument.source_id)
        .where(
            RagDocument.destination_id == destination_id,
            RagDocument.kind == "guide",
            RagDocument.is_active.is_(True),
        )
        .order_by(DataSource.name, RagDocument.title, RagDocument.url)
    )
    return [(row[0], row[1], row[2], row[3]) for row in await session.execute(query)]


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@dataclass(frozen=True)
class PlaceFilters:
    """The API-16 filters (§6.6.3; IMP-604). Empty or None means the filter is not applied."""

    q: str | None = None
    categories: Sequence[str] = ()
    tags: Sequence[str] = ()
    price_max: Decimal | None = None
    currency: str | None = None  # the destination's; price_max is in it
    duration_max_min: int | None = None
    step_free: bool = False
    near: tuple[float, float] | None = None
    max_distance_m: int | None = None


def _distance_m(lat: float, lon: float) -> ColumnElement[float]:
    """Great-circle distance in metres from (lat, lon) to the place: the haversine formula of
    routing/estimate.py, in SQL."""
    d_lat = func.radians(Place.lat - lat)
    d_lon = func.radians(Place.lon - lon)
    a = func.power(func.sin(d_lat / 2), 2) + func.cos(func.radians(lat)) * func.cos(
        func.radians(Place.lat)
    ) * func.power(func.sin(d_lon / 2), 2)
    return 2 * EARTH_RADIUS_M * func.asin(func.least(1.0, func.sqrt(a)))


async def search_places(
    session: AsyncSession,
    destination_id: UUID,
    filters: PlaceFilters,
    *,
    limit: int,
    offset: int,
) -> tuple[list[tuple[Place, str, float | None]], int]:
    """One page of (place, source name, distance in metres or None) of an active destination,
    and the total; ordered by name, or by distance when ``filters.near`` is given.

    ``q`` matches anywhere in the name or a tag, case-insensitively; ``categories`` keeps places
    in any of them (index ix_places_dest_cat); ``tags`` keeps places with any of them (GIN index
    ix_places_tags). A price filter keeps only priced places whose lowest price in the
    destination's currency is at most ``price_max``: an unknown price never matches.
    ``step_free`` keeps confirmed step-free places only (unknown is not step-free). Rows the
    quality gate rejected are never loaded or are deactivated (§5.6), so the active filter also
    hides them.
    """
    distance = _distance_m(*filters.near) if filters.near else None
    query = (
        select(
            Place,
            DataSource.name,
            distance.label("distance_m") if distance is not None else null(),
        )
        .join(Destination, Destination.id == Place.destination_id)
        .join(DataSource, DataSource.id == Place.source_id)
        .where(
            Place.destination_id == destination_id,
            Place.is_active.is_(True),
            Destination.is_active.is_(True),
        )
    )
    if filters.q:
        pattern = f"%{_escape_like(filters.q)}%"
        query = query.where(
            or_(
                Place.name.ilike(pattern, escape="\\"),
                func.array_to_string(Place.tags, " ").ilike(pattern, escape="\\"),
            )
        )
    if filters.categories:
        query = query.where(Place.category.in_(list(filters.categories)))
    if filters.tags:
        query = query.where(Place.tags.op("&&")(literal(list(filters.tags), ARRAY(Text))))
    if filters.price_max is not None:
        query = query.where(
            Place.price_min.is_not(None),
            Place.price_currency == filters.currency,
            Place.price_min <= filters.price_max,
        )
    if filters.duration_max_min is not None:
        query = query.where(Place.typical_duration_min <= filters.duration_max_min)
    if filters.step_free:
        query = query.where(Place.step_free.is_(True))
    if distance is not None and filters.max_distance_m is not None:
        query = query.where(distance <= filters.max_distance_m)
    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    order = (distance, Place.id) if distance is not None else (Place.name, Place.id)
    page = query.order_by(*order).limit(limit).offset(offset)
    rows = [(row[0], row[1], row[2]) for row in await session.execute(page)]
    return rows, int(total or 0)


async def active_place_detail(
    session: AsyncSession, place_id: UUID
) -> tuple[Place, DataSource, list[PlaceOpeningHours]] | None:
    """An active place of an active destination with its source and opening hours (API-17)."""
    query = (
        select(Place, DataSource)
        .join(Destination, Destination.id == Place.destination_id)
        .join(DataSource, DataSource.id == Place.source_id)
        .where(Place.id == place_id, Place.is_active.is_(True), Destination.is_active.is_(True))
    )
    row = (await session.execute(query)).first()
    if row is None:
        return None
    hours = await session.scalars(
        select(PlaceOpeningHours)
        .where(PlaceOpeningHours.place_id == place_id)
        .order_by(PlaceOpeningHours.weekday, PlaceOpeningHours.open_time)
    )
    return row[0], row[1], list(hours.all())


async def destination_by_id(session: AsyncSession, destination_id: UUID) -> Destination | None:
    return await session.get(Destination, destination_id)


async def active_places_by_ids(
    session: AsyncSession, destination_id: UUID, place_ids: Sequence[UUID]
) -> list[Place]:
    """The places among ``place_ids`` that are active and belong to an active destination."""
    if not place_ids:
        return []
    query = (
        select(Place)
        .join(Destination, Destination.id == Place.destination_id)
        .where(
            Place.id.in_(list(place_ids)),
            Place.destination_id == destination_id,
            Place.is_active.is_(True),
            Destination.is_active.is_(True),
        )
        .order_by(Place.name, Place.id)
    )
    return list((await session.scalars(query)).all())


async def active_places_by_refs(
    session: AsyncSession, destination_slug: str, refs: Sequence[tuple[str, str]]
) -> list[tuple[str, Place]]:
    """(source name, place) of the active places of an active destination named by
    ``(source_name, external_ref)``; the stable reference of a seeded place (IMD-145)."""
    if not refs:
        return []
    query = (
        select(DataSource.name, Place)
        .join(DataSource, DataSource.id == Place.source_id)
        .join(Destination, Destination.id == Place.destination_id)
        .where(
            Destination.slug == destination_slug,
            Destination.is_active.is_(True),
            Place.is_active.is_(True),
            tuple_(DataSource.name, Place.external_ref).in_(list(refs)),
        )
    )
    return [(row[0], row[1]) for row in await session.execute(query)]


async def active_places_with_source_date(
    session: AsyncSession, destination_id: UUID
) -> list[tuple[Place, date | None]]:
    """Every active place of a destination, with its data source's retrieval date."""
    query = (
        select(Place, DataSource.retrieved_on)
        .join(DataSource, DataSource.id == Place.source_id)
        .where(Place.destination_id == destination_id, Place.is_active.is_(True))
        .order_by(Place.name, Place.id)
    )
    return [(row[0], row[1]) for row in await session.execute(query)]


async def data_sources_by_name(session: AsyncSession, names: Sequence[str]) -> list[DataSource]:
    query = select(DataSource).where(DataSource.name.in_(list(names)))
    return list((await session.scalars(query)).all())


async def insert_data_source(
    session: AsyncSession,
    *,
    name: str,
    source_type: str,
    licence: str,
    url: str | None,
    retrieved_on: date | None,
    attribution_text: str | None,
) -> DataSource:
    row = DataSource(
        name=name,
        source_type=source_type,
        licence=licence,
        url=url,
        retrieved_on=retrieved_on,
        attribution_text=attribution_text,
    )
    session.add(row)
    await session.flush()
    return row


async def candidates(
    session: AsyncSession, destination_id: UUID
) -> list[tuple[Place, list[PlaceOpeningHours]]]:
    """Every active place of an active destination with its opening hours (§8.9), in one query.

    Category ``stay`` is not removed here: a must-visit place must reach the filters to keep its
    conflict note (FR-027 AC2).
    """
    query = (
        select(Place, PlaceOpeningHours)
        .join(Destination, Destination.id == Place.destination_id)
        .outerjoin(PlaceOpeningHours, PlaceOpeningHours.place_id == Place.id)
        .where(
            Place.destination_id == destination_id,
            Place.is_active.is_(True),
            Destination.is_active.is_(True),
        )
        .order_by(Place.id, PlaceOpeningHours.weekday)
    )
    grouped: dict[UUID, tuple[Place, list[PlaceOpeningHours]]] = {}
    for place, hours in (await session.execute(query)).all():
        entry = grouped.setdefault(place.id, (place, []))
        if hours is not None:
            entry[1].append(hours)
    return list(grouped.values())


# ---------- Live import writes (Amendment A2 §6.2; IMP-725 job runner) ----------
# Written only by the live import job through the places service: the claim and the state of a
# live destination row, the shared OpenStreetMap source, the live places and the reaper.

_RUNNING = "running"


async def claim_live_import(
    session: AsyncSession, destination_id: UUID, now: datetime
) -> Destination | None:
    """Move a queued live import to running; None when another job holds it or it is not queued."""
    query = (
        update(Destination)
        .where(Destination.id == destination_id, Destination.import_status == "queued")
        .values(import_status=_RUNNING, import_started_at=now, updated_at=func.now())
        .returning(Destination)
        .execution_options(populate_existing=True)
    )
    return (await session.scalars(query)).first()


async def finish_live_import(session: AsyncSession, destination_id: UUID, **values: object) -> bool:
    """Set the end state of a running import; False when the row is no longer running."""
    result = await session.execute(
        update(Destination)
        .where(Destination.id == destination_id, Destination.import_status == _RUNNING)
        .values(**values, updated_at=func.now())
        .returning(Destination.id)
    )
    return result.first() is not None


async def upsert_data_source(
    session: AsyncSession,
    *,
    name: str,
    source_type: str,
    licence: str,
    url: str | None,
    retrieved_on: date | None,
    attribution_text: str | None,
) -> UUID:
    """Insert the source, or bring the row of the same name to these terms; returns its id."""
    values = {
        "name": name,
        "source_type": source_type,
        "licence": licence,
        "url": url,
        "retrieved_on": retrieved_on,
        "attribution_text": attribution_text,
    }
    insert = pg_insert(DataSource).values(**values)
    statement = insert.on_conflict_do_update(
        index_elements=[DataSource.name],
        set_={key: insert.excluded[key] for key in values if key != "name"},
    ).returning(DataSource.id)
    source_id: UUID = (await session.execute(statement)).scalar_one()
    return source_id


_PLACE_KEY_COLUMNS = frozenset({"source_id", "external_ref"})


async def upsert_places(session: AsyncSession, rows: Sequence[dict[str, object]]) -> int:
    """Insert or update places by ``(source_id, external_ref)``, active; returns the row count.

    Each row holds the same keys (place columns). An existing place keeps its id, so trips and
    saved plans that refer to it stay valid.
    """
    if not rows:
        return 0
    insert = pg_insert(Place).values(list(rows))
    updated = {key: insert.excluded[key] for key in rows[0] if key not in _PLACE_KEY_COLUMNS}
    statement = insert.on_conflict_do_update(
        index_elements=[Place.source_id, Place.external_ref],
        index_where=Place.external_ref.is_not(None),
        set_={**updated, "is_active": True, "updated_at": func.now()},
    ).returning(Place.id)
    return len((await session.execute(statement)).all())


async def deactivate_places_except(
    session: AsyncSession, destination_id: UUID, source_id: UUID, keep_refs: Sequence[str]
) -> int:
    """Deactivate (never delete) the destination's active places of the source not in
    ``keep_refs``; returns how many changed."""
    query = (
        update(Place)
        .where(
            Place.destination_id == destination_id,
            Place.source_id == source_id,
            Place.is_active.is_(True),
            or_(Place.external_ref.is_(None), Place.external_ref.not_in(list(keep_refs))),
        )
        .values(is_active=False, updated_at=func.now())
        .returning(Place.id)
    )
    return len((await session.execute(query)).all())


async def reap_live_imports(
    session: AsyncSession, *, running_before: datetime, queued_before: datetime
) -> int:
    """Fail with ``timeout`` the imports running since before ``running_before`` and those
    queued (or queued again) before ``queued_before``; returns how many."""
    query = (
        update(Destination)
        .where(
            Destination.data_tier == "live",
            or_(
                and_(
                    Destination.import_status == _RUNNING,
                    Destination.import_started_at < running_before,
                ),
                and_(
                    Destination.import_status == "queued",
                    Destination.updated_at < queued_before,
                ),
            ),
        )
        .values(import_status="failed", import_failure_reason="timeout", updated_at=func.now())
        .returning(Destination.id)
    )
    return len((await session.execute(query)).all())


async def set_live_counts(
    session: AsyncSession, destination_id: UUID, *, found: int, usable: int
) -> None:
    await session.execute(
        update(Destination)
        .where(Destination.id == destination_id)
        .values(places_found=found, places_usable=usable, updated_at=func.now())
    )
