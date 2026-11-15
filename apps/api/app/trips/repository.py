"""The trips, trip_preferences and trip_places tables (migration 0003). MOD-B03 is their only
writer (§3, §5.2).

Every trip query takes the caller's user_id and filters by it and by deleted_at IS NULL, so a
foreign, missing or soft-deleted trip looks the same: absent (CLAUDE.md §4 rule 4, FR-005). The
preference and must-visit functions take a trip_id that the service has just read with
``get_owned`` in the same transaction. destinations and itinerary_days are only read here.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Select, delete, exists, func, literal, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Destination, ItineraryDay, Trip, TripPlace, TripPreferences


@dataclass(frozen=True)
class TripRow:
    trip: Trip
    destination: Destination
    has_itinerary: bool


def _owned_trips(user_id: UUID) -> Select[Trip, Destination, bool]:
    has_itinerary = exists().where(ItineraryDay.trip_id == Trip.id).label("has_itinerary")
    return (
        select(Trip, Destination, has_itinerary)
        .join(Destination, Destination.id == Trip.destination_id)
        .where(Trip.user_id == user_id, Trip.deleted_at.is_(None))
    )


async def active_destinations(session: AsyncSession) -> Sequence[Destination]:
    query = select(Destination).where(Destination.is_active.is_(True)).order_by(Destination.name)
    return (await session.scalars(query)).all()


async def insert_trip(
    session: AsyncSession,
    user_id: UUID,
    *,
    title: str,
    destination_id: UUID,
    start_date: date,
    end_date: date,
    adults: int,
    children: int,
    group_needs: list[str],
    budget_amount: Decimal | None,
    budget_currency: str | None,
) -> UUID:
    """Insert a draft trip with plan_revision 0 (API-07) and return its id."""
    trip = Trip(
        user_id=user_id,
        title=title,
        destination_id=destination_id,
        start_date=start_date,
        end_date=end_date,
        adults=adults,
        children=children,
        group_needs=group_needs,
        budget_amount=budget_amount,
        budget_currency=budget_currency,
        status="draft",
        plan_revision=0,
    )
    session.add(trip)
    await session.flush()
    return trip.id


async def get_owned(session: AsyncSession, user_id: UUID, trip_id: UUID) -> TripRow | None:
    # populate_existing reloads the server-side defaults of a trip inserted in this session.
    query = (
        _owned_trips(user_id).where(Trip.id == trip_id).execution_options(populate_existing=True)
    )
    row = (await session.execute(query)).one_or_none()
    return None if row is None else TripRow(row[0], row[1], bool(row[2]))


async def update_trip(session: AsyncSession, trip_id: UUID, values: dict[str, Any]) -> None:
    """API-11: write the given columns of a trip the service has just read with ``get_owned``."""
    await session.execute(update(Trip).where(Trip.id == trip_id).values(**values))


async def list_owned(
    session: AsyncSession, user_id: UUID, *, limit: int, offset: int, include_archived: bool
) -> tuple[list[TripRow], int]:
    """One page of the caller's trips, newest first (index ix_trips_user), and the total."""
    owned = _owned_trips(user_id)
    if not include_archived:
        owned = owned.where(Trip.status != "archived")
    total = await session.scalar(select(func.count()).select_from(owned.subquery()))
    query = (
        owned.order_by(Trip.updated_at.desc(), Trip.created_at.desc(), Trip.id)
        .limit(limit)
        .offset(offset)
    )
    rows = [TripRow(r[0], r[1], bool(r[2])) for r in (await session.execute(query)).all()]
    return rows, int(total or 0)


# ---------- Preferences and must-visit places (API-14, API-15) ----------

MUST_VISIT = "must_visit"


async def get_preferences(session: AsyncSession, trip_id: UUID) -> TripPreferences | None:
    # populate_existing: a row upserted earlier in this transaction is read back as stored.
    query = (
        select(TripPreferences)
        .where(TripPreferences.trip_id == trip_id)
        .execution_options(populate_existing=True)
    )
    return await session.scalar(query)


async def upsert_preferences(session: AsyncSession, trip_id: UUID, values: dict[str, Any]) -> None:
    """Insert the trip's preferences row or replace every value of the existing one."""
    statement = insert(TripPreferences).values(trip_id=trip_id, **values)
    statement = statement.on_conflict_do_update(
        index_elements=["trip_id"], set_={**values, "updated_at": func.now()}
    )
    await session.execute(statement)


async def must_visit_place_ids(session: AsyncSession, trip_id: UUID) -> list[UUID]:
    query = (
        select(TripPlace.place_id)
        .where(TripPlace.trip_id == trip_id, TripPlace.relation == MUST_VISIT)
        .order_by(TripPlace.created_at, TripPlace.place_id)
    )
    return list((await session.scalars(query)).all())


async def replace_must_visit(session: AsyncSession, trip_id: UUID, place_ids: list[UUID]) -> None:
    """Make ``place_ids`` the trip's must-visit set (§6.6.2 API-14).

    Must-visit rows no longer listed are removed; a listed place that is already saved (or
    rejected) for the trip becomes must_visit, since trip_places holds one row per place.
    """
    removed = delete(TripPlace).where(
        TripPlace.trip_id == trip_id, TripPlace.relation == MUST_VISIT
    )
    if place_ids:
        removed = removed.where(TripPlace.place_id.not_in(place_ids))
    await session.execute(removed)
    if place_ids:
        statement = insert(TripPlace).values(
            [
                {"trip_id": trip_id, "place_id": place_id, "relation": MUST_VISIT}
                for place_id in place_ids
            ]
        )
        statement = statement.on_conflict_do_update(
            index_elements=["trip_id", "place_id"], set_={"relation": MUST_VISIT}
        )
        await session.execute(statement)


async def mark_preferences_saved(
    session: AsyncSession, trip_id: UUID, *, make_ready: bool, make_stale: bool
) -> None:
    """IMD-25: a draft becomes ready; an existing itinerary is flagged stale (FR-011)."""
    values: dict[str, Any] = {}
    if make_ready:
        values["status"] = "ready"
    if make_stale:
        values["plan_stale"] = True
    if values:
        await session.execute(update(Trip).where(Trip.id == trip_id).values(**values))


# IMP-605 saved places (API-19 to API-21): trip_places rows with relation saved.
SAVED = "saved"


async def place_relations(session: AsyncSession, trip_id: UUID) -> dict[UUID, str]:
    """The trip_places relation of each place the trip names (must_visit, saved, rejected)."""
    query = select(TripPlace.place_id, TripPlace.relation).where(TripPlace.trip_id == trip_id)
    return {row[0]: row[1] for row in await session.execute(query)}


async def insert_saved(session: AsyncSession, trip_id: UUID, place_id: UUID) -> None:
    """Save a place the trip does not name yet; the unique (trip_id, place_id) keeps one row."""
    statement = insert(TripPlace).values(trip_id=trip_id, place_id=place_id, relation=SAVED)
    await session.execute(statement.on_conflict_do_nothing(index_elements=["trip_id", "place_id"]))


async def delete_saved(session: AsyncSession, trip_id: UUID, place_id: UUID) -> None:
    """Remove the saved row only; a must-visit or rejected row of the place stays."""
    await session.execute(
        delete(TripPlace).where(
            TripPlace.trip_id == trip_id,
            TripPlace.place_id == place_id,
            TripPlace.relation == SAVED,
        )
    )


# ---------- Delete, duplicate and purge (API-12, API-13, IMD-31; IMP-602) ----------


async def soft_delete(session: AsyncSession, trip_id: UUID) -> None:
    """API-12: hide a trip the service has just read with ``get_owned``; purged after 30 days."""
    await session.execute(update(Trip).where(Trip.id == trip_id).values(deleted_at=func.now()))


async def insert_copy(session: AsyncSession, source: Trip, *, title: str, status: str) -> UUID:
    """API-13: a new trip with the source's settings, plan_revision 0 until its plan is copied."""
    trip = Trip(
        user_id=source.user_id,
        title=title,
        destination_id=source.destination_id,
        start_date=source.start_date,
        end_date=source.end_date,
        adults=source.adults,
        children=source.children,
        group_needs=list(source.group_needs),
        budget_amount=source.budget_amount,
        budget_currency=source.budget_currency,
        status=status,
        plan_revision=0,
        plan_stale=source.plan_stale,
    )
    session.add(trip)
    await session.flush()
    return trip.id


_NOT_COPIED = frozenset({"id", "trip_id", "created_at", "updated_at"})


async def copy_preferences_and_places(
    session: AsyncSession, source_id: UUID, target_id: UUID
) -> None:
    """API-13: the source's trip_preferences row and every trip_places row (any relation)."""
    for model in (TripPreferences, TripPlace):
        table = model.__table__
        columns = [c.name for c in table.columns if c.name not in _NOT_COPIED]
        rows = select(literal(target_id), *(table.c[name] for name in columns)).where(
            table.c.trip_id == source_id
        )
        await session.execute(insert(model).from_select(["trip_id", *columns], rows))


async def purge_deleted(session: AsyncSession, deleted_before: datetime) -> int:
    """IMD-31: delete trips soft-deleted before the cut-off; their child rows go by cascade."""
    removed = await session.scalars(
        delete(Trip).where(Trip.deleted_at < deleted_before).returning(Trip.id)
    )
    return len(removed.all())
