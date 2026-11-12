"""Read-only queries over the place reference tables (MOD-B04; §6.6.3 API-06, API-16).

Destinations and places are shared reference data with no owner, so no query takes a user_id;
every query reads active rows only (§6.2: inactive destinations and places are invisible). Only
the seed writes these tables, except that ``insert_data_source`` adds the source of a guide (A1 §5.1).
"""

from collections.abc import Sequence
from datetime import date
from uuid import UUID

from sqlalchemy import func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DataSource, Destination, Place, PlaceOpeningHours


async def active_destinations(session: AsyncSession) -> Sequence[Destination]:
    query = (
        select(Destination)
        .where(Destination.is_active.is_(True))
        .order_by(Destination.name, Destination.id)
    )
    return (await session.scalars(query)).all()


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def search_places(
    session: AsyncSession,
    destination_id: UUID,
    *,
    q: str | None,
    categories: Sequence[str],
    limit: int,
    offset: int,
) -> tuple[list[Place], int]:
    """One page of active places of an active destination, ordered by name, and the total.

    ``q`` matches anywhere in the name, case-insensitively; ``categories`` keeps places in any of
    them (index ix_places_dest_cat).
    """
    query = (
        select(Place)
        .join(Destination, Destination.id == Place.destination_id)
        .where(
            Place.destination_id == destination_id,
            Place.is_active.is_(True),
            Destination.is_active.is_(True),
        )
    )
    if q:
        query = query.where(Place.name.ilike(f"%{_escape_like(q)}%", escape="\\"))
    if categories:
        query = query.where(Place.category.in_(list(categories)))
    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    page = query.order_by(Place.name, Place.id).limit(limit).offset(offset)
    return list((await session.scalars(page)).all()), int(total or 0)


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
