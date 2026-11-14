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
from datetime import time, timedelta
from typing import Any, Final
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.budget import engine
from app.budget.schemas import AmountRange
from app.core.config import get_settings
from app.core.errors import (
    EndpointNotImplemented,
    GenerationInProgress,
    InvalidEdit,
    NotFound,
    StalePlan,
)
from app.core.flags import is_enabled
from app.db.models import ItineraryDay, ItineraryItem, Place
from app.generation import ranking, retrieval
from app.itinerary import repository, service
from app.itinerary.schemas import (
    Alternative,
    AlternativesOut,
    EditResultOut,
    ItemAddIn,
    ItemPatchIn,
    ReplaceIn,
)
from app.places import repository as places_repository
from app.places.schemas import PlaceSummary
from app.routing.cache import RouteCacheRepository
from app.routing.client import get_client
from app.routing.estimate import buffer_minutes, estimate
from app.routing.service import RoutingService
from app.trips import preference_mapping
from app.trips import service as trips_service
from app.trips.schemas import PreferencesOut, TripOut
from app.validation import validator

DAY_START: Final = time(9, 0)  # §8.6 limits.day_start, for an item added to an empty day
LAST_MINUTE: Final = 24 * 60 - 1
FOOD: Final = "food"
MAX_ALTERNATIVES: Final = 3  # FR-065
NO_ALTERNATIVE: Final = "No alternative fits"  # FR-065 AC3, §6.6.5 API-28
LOCKED: Final = "This item is locked; unlock it to replace it."


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
    ranked: bool = False  # API-29: the place must be one of the item's current alternatives


EditOperation = Move | Retime | Remove | Add | Lock | Replace


@dataclass
class Plan:
    """The trip's plan as mutable rows: items per day number, in position order."""

    user_id: UUID
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
        user_id=user_id,
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
    day_rows = [plan.days[number] for number in sorted(plan.days)]  # with any day row just added

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


async def add_item(
    session: AsyncSession, user_id: UUID, trip_id: UUID, body: ItemAddIn
) -> EditResultOut:
    """API-25 (FR-062): without start_time the place follows the previous item (previous end +
    travel + buffer); conflicts it causes are saved and returned as findings."""
    start = None if body.start_time is None else time.fromisoformat(body.start_time)
    op = Add(body.day_number, body.place_id, body.position, start, body.duration_min)
    return await apply_edit(session, user_id, trip_id, body.plan_revision, op)


async def _day(session: AsyncSession, plan: Plan, day_number: int) -> list[ItineraryItem]:
    """The items of a trip day. IMD-152 (PD-IMP-407-2): the save writes only days with items, so a
    trip day without a row gets one on its first add or move; a day outside the trip is refused."""
    if day_number not in plan.items:
        if not 1 <= day_number <= plan.trip.num_days:
            raise InvalidEdit(f"Day {day_number} is not in the trip.")
        day = ItineraryDay(
            id=uuid4(),
            trip_id=plan.trip.id,
            day_number=day_number,
            plan_date=plan.trip.start_date + timedelta(days=day_number - 1),
            theme=None,
        )
        session.add(day)
        await session.flush()  # before any item points at it
        plan.days[day_number], plan.items[day_number] = day, []
    return plan.items[day_number]


def _alternatives_enabled() -> None:
    if not is_enabled(get_settings(), "alternatives"):
        raise NotFound()  # IMD-11: a switched-off feature's routes answer 404


async def _alternatives(
    session: AsyncSession,
    trip: TripOut,
    prefs: PreferencesOut,
    item: ItineraryItem,
    planned: set[UUID],
) -> list[retrieval.Candidate]:
    """IMP-505: the best places for the item's slot, by the generation score (§8.9).

    The candidates are the trip's places that pass the IMP-304 hard filters; the context is built
    from all of them, as generation builds it, and the ranking is lexical (no query text here).
    Kept: same slot family (a meal takes a food place, an activity any other), not in the plan.
    """
    candidates = await retrieval.retrieve_candidates(
        session, trip, prefs, prefs.must_visit_place_ids
    )
    destination = await places_repository.destination_by_id(session, trip.destination_id)
    if destination is None:
        raise NotFound()
    mapped = preference_mapping.map_preferences(
        preference_mapping.Preferences(
            interests=[interest.value for interest in prefs.interests],
            pace=preference_mapping.Pace(prefs.pace),
            budget_priority=preference_mapping.BudgetPriority(prefs.budget_priority),
            step_free_required=prefs.step_free_required,
            must_visit_place_ids=list(prefs.must_visit_place_ids),
        ),
        preference_mapping.TripFacts(children=trip.children),
        semantic=False,
    )
    context = ranking.build_context(
        candidates,
        mapped,
        destination,
        num_days=trip.num_days,
        meal_slots_per_day=0,  # read only by the shortlist cut, not by the score
        # shortcut: generation's private helper, so the price part matches; PD-IMP-505-2.
        activity_budget=await retrieval._trip_activity_budget(session, trip),
    )
    meal = item.slot_type == "meal"
    fitting = (
        candidate
        for candidate in candidates
        if candidate.conflict_note is None  # a must-visit place that fails a filter stays out
        and candidate.place.id not in planned
        and (candidate.place.category == FOOD) == meal
    )
    return [entry.candidate for entry in ranking.rank(fitting, context)[:MAX_ALTERNATIVES]]


def _leg(origin: Place | None, target: Place | None, mode: str) -> int:
    """Estimated travel minutes between two places (§9.3.5); 0 at either end of the day."""
    if origin is None or target is None:
        return 0
    travel = estimate(
        float(origin.lat), float(origin.lon), float(target.lat), float(target.lon), mode
    )
    return travel.minutes


async def alternatives(session: AsyncSession, user_id: UUID, item_id: UUID) -> AlternativesOut:
    """API-28 (FR-065 AC1, AC3): at most three ranked alternatives with their cost and time
    differences against the current place; a locked item has none. Reads only."""
    _alternatives_enabled()
    trip_id, _ = await _locate(session, user_id, item_id)
    rows = await repository.plan_items(session, trip_id)
    item, current = next((i, p) for i, p, _ in rows if i.id == item_id)
    if item.is_locked:
        return AlternativesOut(item_id=item_id, alternatives=[], message=LOCKED)
    trip = await trips_service.get_trip(session, user_id, trip_id)
    prefs = await trips_service.get_preferences(session, user_id, trip_id)
    planned = {row.place_id for row, _, _ in rows}
    day = [place for row, place, _ in rows if row.day_id == item.day_id]
    index = item.position - 1
    previous = day[index - 1] if index > 0 else None
    following = day[index + 1] if index + 1 < len(day) else None
    mode = prefs.transport_pref.value
    currency = service.trip_currency(trip)

    def cost(place: Place) -> engine.ItemCost:
        return engine.item_cost(
            place, adults=trip.adults, children=trip.children, currency=currency
        )

    def visit(place: Place) -> int:
        travel = _leg(previous, place, mode) + _leg(place, following, mode)
        return place.typical_duration_min + travel

    old = cost(current)
    wanted = {interest.value for interest in prefs.interests}
    out = []
    for candidate in await _alternatives(session, trip, prefs, item, planned):
        place = candidate.place
        new = cost(place)
        known = None not in (new.lo, new.hi, old.lo, old.hi)
        # shortcut: cost_delta is required by contract v1; an unknown price counts 0 and the
        # reason says so (PD-IMP-505-3).
        lo = (new.lo or 0) - (old.lo or 0)
        hi = (new.hi or 0) - (old.hi or 0)
        matched = sorted(wanted & {*place.tags, place.category})
        reason = (
            f"Matches your interests: {', '.join(matched)}"
            if matched
            else f"A {place.category} place that fits this slot"
        )
        out.append(
            Alternative(
                place=PlaceSummary.from_row(place),
                cost_delta=AmountRange(min=engine.from_minor(lo), max=engine.from_minor(hi)),
                time_delta_min=visit(place) - visit(current),
                reason=reason if known else f"{reason}; price unavailable",
            )
        )
    return AlternativesOut(
        item_id=item_id, alternatives=out, message=None if out else NO_ALTERNATIVE
    )


async def replace_item(
    session: AsyncSession, user_id: UUID, item_id: UUID, body: ReplaceIn
) -> EditResultOut:
    """API-29 (FR-065 AC2): keep the start time, take the new place's typical duration,
    recalculate and revalidate. The place must be a current alternative; a locked item is 422."""
    _alternatives_enabled()
    trip_id, _ = await _locate(session, user_id, item_id)
    op = Replace(item_id, body.place_id, ranked=True)
    return await apply_edit(session, user_id, trip_id, body.plan_revision, op)


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
            target = await _day(session, plan, day_number)
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
            target = await _day(session, plan, day_number)
            if position is None and start_time is not None:  # a chosen time keeps the day in order
                position = 1 + sum(other.start_time <= start_time for other in target)
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
            if op.ranked:
                prefs = await trips_service.get_preferences(session, plan.user_id, plan.trip.id)
                planned = {other.place_id for day in plan.items.values() for other in day}
                ranked = await _alternatives(session, plan.trip, prefs, item, planned)
                if place_id not in {candidate.place.id for candidate in ranked}:
                    raise InvalidEdit("This place is not one of the item's alternatives.")
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
