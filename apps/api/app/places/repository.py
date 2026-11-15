"""Read-only queries over the place reference tables (MOD-B04; §6.6.3 API-06, API-16, API-17).

Destinations and places are shared reference data with no owner, so no query takes a user_id;
every query reads active rows only (§6.2: inactive destinations and places are invisible). Only
the seed writes these tables, except that ``insert_data_source`` adds the source of a guide (A1 §5.1).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import ColumnElement, Text, func, literal, null, or_, select, tuple_
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DataSource, Destination, Place, PlaceOpeningHours
from app.routing.estimate import EARTH_RADIUS_M


async def active_destinations(session: AsyncSession) -> Sequence[Destination]:
    query = (
        select(Destination)
        .where(Destination.is_active.is_(True))
        .order_by(Destination.name, Destination.id)
    )
    return (await session.scalars(query)).all()


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
