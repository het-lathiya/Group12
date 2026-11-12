"""The edit transaction core (IMP-407; §5.8 "Edit an item", §6.6.5; IMD-18, IMD-23; A1 §6.10).

``apply_edit`` runs one edit in the caller's transaction, in the order of §5.8: lock the trip row;
refuse while a generation for the trip is active (409 GENERATION_IN_PROGRESS, before the revision
check); compare plan_revision (409 STALE_PLAN); apply the operation; renumber positions; recompute
travel on the changed days and shift later start times forward; price new places with the budget
engine; validate the whole plan; plan_revision + 1; save that revision's warnings; write an
automatic version (reason edit); return ``EditResultOut``. Any exception before the caller commits
leaves every table as it was (NFR-008). Soft-rule breaks are saved and reported as findings
(PR-06); only structurally impossible edits raise 422 INVALID_EDIT.

Times: a retime keeps the traveller's values, and conflicts become findings. A moved item takes
the start time of the item it displaces (or follows the previous item when appended), and the
unlocked items after it shift forward to max(own start, previous end + travel + buffer)
(FR-060). Kept items keep their note and ``source_chunk_ids``; a replaced item drops them, since
they describe the old place. The routes (API-25 to API-29) are IMP-408, IMP-409, IMP-504 and
IMP-505; they translate their bodies into these operations (``patch_item`` and ``remove_item``
for API-26 and API-27).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import time
from typing import Any, Final
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.budget import engine
from app.core.errors import (
    EndpointNotImplemented,
    GenerationInProgress,
    InvalidEdit,
    NotFound,
    StalePlan,
)
from app.db.models import ItineraryDay, ItineraryItem, Place
from app.itinerary import repository, service
from app.itinerary.schemas import EditResultOut, ItemPatchIn
from app.places import repository as places_repository
from app.routing.cache import RouteCacheRepository
from app.routing.client import get_client
from app.routing.estimate import buffer_minutes
from app.routing.service import RoutingService
from app.trips import service as trips_service
from app.trips.schemas import TripOut
from app.validation import validator

DAY_START: Final = time(9, 0)  # §8.6 limits.day_start, for an item added to an empty day
LAST_MINUTE: Final = 24 * 60 - 1
FOOD: Final = "food"


@dataclass(frozen=True)
class Move:
    item_id: UUID
    day_number: int
    position: int | None = None  # None: after the target day's last item


@dataclass(frozen=True)
class Retime:
    item_id: UUID
    start_time: time | None = None
    duration_min: int | None = None


@dataclass(frozen=True)
class Remove:
    item_id: UUID


@dataclass(frozen=True)
class Add:
    day_number: int
    place_id: UUID
    position: int | None = None
    start_time: time | None = None
    duration_min: int | None = None


@dataclass(frozen=True)
class Lock:
    item_id: UUID
    is_locked: bool


@dataclass(frozen=True)
class Replace:
    item_id: UUID
    place_id: UUID


EditOperation = Move | Retime | Remove | Add | Lock | Replace


@dataclass
class Plan:
    """The trip's plan as mutable rows: items per day number, in position order."""

    trip: TripOut
    days: dict[int, ItineraryDay]
    items: dict[int, list[ItineraryItem]]
    places: dict[UUID, Place]
    changed: set[int]
    # Per changed day: the position from which start times shift, and an item whose start
    # follows the previous item (moved or added with no slot to take).
    shift_from: dict[int, int]
    follow: set[UUID]

    def find(self, item_id: UUID) -> tuple[int, ItineraryItem]:
        for day_number, items in self.items.items():
            for item in items:
                if item.id == item_id:
                    return day_number, item
        raise InvalidEdit("This item is not in the plan.")

    def day(self, day_number: int) -> list[ItineraryItem]:
        if day_number not in self.items:
            raise InvalidEdit(f"Day {day_number} is not in the plan.")
        return self.items[day_number]


async def apply_edit(
    session: AsyncSession, user_id: UUID, trip_id: UUID, base_revision: int, op: EditOperation
) -> EditResultOut:
    trip_row = await repository.lock_trip(session, trip_id, user_id)
    if trip_row is None:
        raise NotFound()
    if await repository.generation_active(session, trip_id):  # IMD-23: before the revision
        raise GenerationInProgress()
    if base_revision != trip_row.plan_revision:
        raise StalePlan()
    day_rows = await repository.plan_days(session, trip_id)
    if not day_rows:
        raise NotFound(service.NO_ITINERARY)
    trip = await trips_service.get_trip(session, user_id, trip_id)
    plan = Plan(
        trip=trip,
        days={day.day_number: day for day in day_rows},
        items={day.day_number: [] for day in day_rows},
        places={},
        changed=set(),
        shift_from={},
        follow=set(),
    )
    numbers = {day.id: day.day_number for day in day_rows}
    for item, place, _ in await repository.plan_items(session, trip_id):
        plan.items[numbers[item.day_id]].append(item)
        plan.places[place.id] = place

    await _apply(session, plan, op)
    await _recalculate(session, user_id, plan)

    rows = await repository.plan_items(session, trip_id)
    planned = service.planned_days(day_rows, rows)
    ctx = await service.validation_context(
        session, user_id, trip, [item.place_id for day in planned for item in day.items]
    )
    findings = validator.validate(planned, ctx)
    plan_revision = await repository.bump_revision(session, trip_id)
    await repository.insert_warnings(session, trip_id, plan_revision, findings)
    await repository.insert_version(
        session,
        trip_id,
        reason="edit",
        plan_revision=plan_revision,
        snapshot={
            "schema": service.SNAPSHOT_SCHEMA,
            "plan_revision": plan_revision,
            "days": _snapshot_days(day_rows, rows),
            "budget_settings": await repository.budget_settings_snapshot(session, trip_id),
        },
        validation_summary=validator.summary(findings),
        generation_id=None,
        created_by=user_id,
    )
    generation = await repository.latest_completed_generation(session, trip_id)
    days_out, totals = await service.plan_out(session, trip, day_rows, rows, generation)
    return EditResultOut(
        plan_revision=plan_revision,
        changed_days=[day for day in days_out if day.day_number in plan.changed],
        totals=totals,
        findings=await service.stored_findings(session, trip_id, plan_revision),
    )


async def _locate(session: AsyncSession, user_id: UUID, item_id: UUID) -> tuple[UUID, int]:
    location = await repository.item_location(session, item_id, user_id)
    if location is None:
        raise NotFound()  # another user's item reads as missing, never 403
    return location


async def patch_item(
    session: AsyncSession, user_id: UUID, item_id: UUID, body: ItemPatchIn
) -> EditResultOut:
    """API-26: day_number and/or position is a move (FR-060); start_time and/or duration_min is a
    retime (FR-063). A move without day_number stays on its day; without position it goes last."""
    if body.is_locked is not None:
        raise EndpointNotImplemented()  # lock and unlock are IMP-506
    moves = body.day_number is not None or body.position is not None
    retimes = body.start_time is not None or body.duration_min is not None
    if moves and retimes:  # PD-IMP-409-1: §6 does not define a combined move and retime
        raise InvalidEdit("Move and retime are separate edits; send one, then the other.")
    if not moves and not retimes:
        raise InvalidEdit("The request changes nothing.")
    trip_id, day_number = await _locate(session, user_id, item_id)
    op: EditOperation
    if moves:
        op = Move(item_id, body.day_number or day_number, body.position)
    else:
        start = None if body.start_time is None else time.fromisoformat(body.start_time)
        op = Retime(item_id, start_time=start, duration_min=body.duration_min)
    return await apply_edit(session, user_id, trip_id, body.plan_revision, op)


async def remove_item(
    session: AsyncSession, user_id: UUID, item_id: UUID, plan_revision: int
) -> EditResultOut:
    """API-27 (FR-061); a removed must-visit item comes back as MUST_VISIT_MISSING."""
    trip_id, _ = await _locate(session, user_id, item_id)
    return await apply_edit(session, user_id, trip_id, plan_revision, Remove(item_id))


async def _active_place(session: AsyncSession, trip: TripOut, place_id: UUID) -> Place:
    rows = await places_repository.active_places_by_ids(session, trip.destination_id, [place_id])
    if not rows:
        raise InvalidEdit("This place is unknown or not available for this trip.")
    return rows[0]


def _priced(item: ItineraryItem, place: Place, trip: TripOut) -> None:
    currency = service.trip_currency(trip)
    cost = engine.item_cost(place, adults=trip.adults, children=trip.children, currency=currency)
    item.cost_min = None if cost.lo is None else engine.from_minor(cost.lo)
    item.cost_max = None if cost.hi is None else engine.from_minor(cost.hi)
    item.cost_currency = currency
    item.cost_label = cost.label


def _unlocked(item: ItineraryItem) -> None:
    if item.is_locked:
        raise InvalidEdit("This item is locked; unlock it first.")


async def _apply(session: AsyncSession, plan: Plan, op: EditOperation) -> None:
    match op:
        case Move(item_id, day_number, position):
            source, item = plan.find(item_id)
            _unlocked(item)
            target = plan.day(day_number)
            plan.items[source].remove(item)
            position = len(target) + 1 if position is None else position
            if not 1 <= position <= len(target) + 1:
                raise InvalidEdit(f"Position {position} is outside day {day_number}.")
            if position <= len(target):
                item.start_time = target[position - 1].start_time  # take the displaced slot
            else:
                plan.follow.add(item.id)
            target.insert(position - 1, item)
            item.day_id = plan.days[day_number].id
            plan.changed |= {source, day_number}
            plan.shift_from[day_number] = position
        case Retime(item_id, start_time, duration_min):
            day_number, item = plan.find(item_id)
            _unlocked(item)
            if start_time is not None:
                item.start_time = start_time
            if duration_min is not None:
                item.duration_min = duration_min
            plan.changed.add(day_number)
        case Remove(item_id):
            day_number, item = plan.find(item_id)
            plan.items[day_number].remove(item)
            await session.delete(item)
            plan.changed.add(day_number)
        case Add(day_number, place_id, position, start_time, duration_min):
            target = plan.day(day_number)
            position = len(target) + 1 if position is None else position
            if not 1 <= position <= len(target) + 1:
                raise InvalidEdit(f"Position {position} is outside day {day_number}.")
            place = await _active_place(session, plan.trip, place_id)
            item = ItineraryItem(
                id=uuid4(),  # known before the flush, for plan.follow
                trip_id=plan.trip.id,
                day_id=plan.days[day_number].id,
                place_id=place.id,
                position=position,
                slot_type="meal" if place.category == FOOD else "activity",
                start_time=start_time or DAY_START,
                duration_min=duration_min or place.typical_duration_min,
                origin="user",
                note=None,
                note_origin="none",
                is_locked=False,
                source_chunk_ids=[],
            )
            _priced(item, place, plan.trip)
            session.add(item)
            target.insert(position - 1, item)
            plan.places[place.id] = place
            if start_time is None:
                plan.follow.add(item.id)
                plan.shift_from[day_number] = position
            plan.changed.add(day_number)
        case Lock(item_id, is_locked):
            day_number, item = plan.find(item_id)
            item.is_locked = is_locked
            plan.changed.add(day_number)
        case Replace(item_id, place_id):
            day_number, item = plan.find(item_id)
            _unlocked(item)
            if place_id == item.place_id:
                raise InvalidEdit("This item already visits that place.")
            place = await _active_place(session, plan.trip, place_id)
            item.place_id = place.id
            item.duration_min = place.typical_duration_min
            item.origin = "user"
            item.note, item.note_origin = None, "none"
            item.source_chunk_ids = []  # they cited the old place
            _priced(item, place, plan.trip)
            plan.places[place.id] = place
            plan.changed.add(day_number)
    await session.flush()  # new items get their IDs


def _minutes(clock: time) -> int:
    return clock.hour * 60 + clock.minute


def _clock(minutes: int) -> time:
    # shortcut: as in generation/schedule.py, a day past midnight stops at 23:59; DAY_TOO_LONG or
    # OVERLAP reports it.
    minutes = min(minutes, LAST_MINUTE)
    return time(minutes // 60, minutes % 60)


async def _recalculate(session: AsyncSession, user_id: UUID, plan: Plan) -> None:
    """Positions, travel and forward shifts on the changed days (§9.3.3, §9.3.5).

    shortcut: travel is looked up inside the locked transaction (route cache, then ORS, then the
    estimate) instead of before it (§5.8); move it out when edits show lock waits.
    """
    prefs = await trips_service.get_preferences(session, user_id, plan.trip.id)
    routing = RoutingService(RouteCacheRepository(session), get_client())
    for day_number in sorted(plan.changed):
        shift_from = plan.shift_from.get(day_number)
        previous: ItineraryItem | None = None
        for position, item in enumerate(plan.items[day_number], start=1):
            item.position = position
            if previous is None:
                item.travel_from_prev_min = item.travel_from_prev_m = None
                item.travel_mode = item.travel_source = None
            else:
                travel = await routing.travel(
                    plan.places[previous.place_id], plan.places[item.place_id], prefs.transport_pref
                )
                item.travel_from_prev_min = travel.minutes
                item.travel_from_prev_m = travel.distance_m
                item.travel_mode = travel.mode.value
                item.travel_source = travel.travel_source
                earliest = (
                    _minutes(previous.start_time)
                    + previous.duration_min
                    + travel.minutes
                    + buffer_minutes(travel.travel_source)
                )
                if item.id in plan.follow:
                    item.start_time = _clock(earliest)
                elif shift_from is not None and position > shift_from and not item.is_locked:
                    item.start_time = _clock(max(_minutes(item.start_time), earliest))
            previous = item
    await session.flush()


def _snapshot_days(
    days: Sequence[ItineraryDay], rows: Sequence[tuple[ItineraryItem, Place, bool]]
) -> list[dict[str, Any]]:
    """snap-1 days (§5.2): no costs, travel or findings; citations kept as strings (A1 §5.5)."""
    items: dict[UUID, list[dict[str, Any]]] = {day.id: [] for day in days}
    for item, _, _ in rows:
        items[item.day_id].append(
            {
                "place_id": str(item.place_id),
                "position": item.position,
                "slot_type": item.slot_type,
                "start_time": item.start_time.strftime("%H:%M"),
                "duration_min": item.duration_min,
                "origin": item.origin,
                "note": item.note,
                "note_origin": item.note_origin,
                "is_locked": item.is_locked,
                "source_chunk_ids": [str(chunk_id) for chunk_id in item.source_chunk_ids],
            }
        )
    return [
        {
            "day_number": day.day_number,
            "plan_date": day.plan_date.isoformat(),
            "theme": day.theme,
            "items": items[day.id],
        }
        for day in days
    ]
