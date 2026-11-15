"""Itinerary service (MOD-B08): the only writer of the plan (§3, IMD-13).

``save_generated_plan`` is step 11 of the pipeline (§8.2): it runs in the caller's transaction,
which also completes the generation record, so the plan, the version and the record are saved
together or not at all (NFR-008). ``get_itinerary`` (API-24) and ``latest_itinerary`` (API-09)
read the saved plan for its owner (IMP-211); ``trip_summary`` is API-35 (IMP-609).
``revalidate`` (API-32) re-runs the validator on the
current plan and replaces that revision's warnings; ``version_findings`` reads a stored version's
warnings and summary (FR-058, IMP-405). ``plan_out`` builds the days and totals that API-24 and
the edit core (``edits.apply_edit``, IMP-407) return.
"""

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from typing import Any, Final, Literal
from uuid import UUID

from sqlalchemy import Row
from sqlalchemy.ext.asyncio import AsyncSession

from app.budget import engine
from app.budget import repository as budget_repository
from app.budget.schemas import AmountRange, CostSummaryOut
from app.core.config import get_settings
from app.core.errors import InvalidEdit, NotFound, StalePlan
from app.core.flags import is_enabled
from app.db.models import AiGeneration, ItineraryDay, ItineraryItem, Place
from app.itinerary import repository
from app.itinerary.schemas import (
    Day,
    DayCost,
    Item,
    ItineraryOut,
    ItinerarySource,
    LatestItineraryOut,
    PlannedDay,
    PlannedItem,
    SourceRef,
    Totals,
    TripSummaryOut,
    ValidateOut,
)
from app.places import repository as places_repository
from app.places import service as places_service
from app.rag import service as rag_service
from app.routing.cache import RouteCacheRepository
from app.routing.client import get_client
from app.routing.estimate import buffer_minutes
from app.routing.service import RoutingService
from app.schemas.ai import LockedItem, PlanFinding
from app.trips import service as trips_service
from app.trips.schemas import TripOut
from app.validation import validator
from app.validation.rules import HoursInfo, OpeningRow, ValidationContext
from app.validation.schemas import Finding, ValidationSummary

SNAPSHOT_SCHEMA = "snap-1"
MAX_VERSIONS: Final = 20  # IMD-18
# Switch 'versions' off: the current plan's version and one backup copy of the previous plan.
BACKUP_VERSIONS: Final = 2


@dataclass(frozen=True)
class SavedPlan:
    version_id: UUID
    plan_revision: int


async def save_generated_plan(
    session: AsyncSession,
    trip_id: UUID,
    user_id: UUID,
    plan: Sequence[PlannedDay],
    generation_id: UUID,
    *,
    validation_summary: dict[str, Any],
    origin: Literal["model", "fallback_rule_based"] = "model",
    findings: Sequence[PlanFinding] = (),
    base_revision: int | None = None,
) -> SavedPlan:
    """``origin`` fallback_rule_based saves no note (IMD-131) and a version of reason fallback.

    ``findings`` are the validator's on this plan, saved as its warnings (§8.12, IMD-42). Model
    text is stored only in the day theme and the item note (note_origin ai); hours, prices and
    travel come only from backend columns (FR-035).
    """
    trip = await repository.lock_trip(session, trip_id, user_id)
    if trip is None:
        raise NotFound()
    if base_revision is not None and trip.plan_revision != base_revision:
        raise StalePlan()
    prefs = await trips_service.get_preferences(session, user_id, trip_id)
    days = await repository.replace_plan(
        session,
        trip_id,
        trip.start_date,
        plan,
        origin=origin,
        generation_id=generation_id,
        locked_place_ids=frozenset(str(place_id) for place_id in prefs.must_visit_place_ids),
    )
    plan_revision = await repository.mark_plan_saved(session, trip_id)
    await repository.insert_warnings(session, trip_id, plan_revision, findings)
    snapshot = {
        "schema": SNAPSHOT_SCHEMA,
        "plan_revision": plan_revision,
        "days": days,
        "budget_settings": await repository.budget_settings_snapshot(session, trip_id),
    }
    version = await repository.insert_version(
        session,
        trip_id,
        reason="generation" if origin == "model" else "fallback",
        plan_revision=plan_revision,
        snapshot=snapshot,
        validation_summary=validation_summary,
        generation_id=generation_id,
        created_by=user_id,
    )
    await retain_versions(session, trip_id)
    return SavedPlan(version_id=version.id, plan_revision=plan_revision)


async def save_regenerated_plan(
    session: AsyncSession,
    trip_id: UUID,
    user_id: UUID,
    plan: Sequence[PlannedDay],
    generation_id: UUID,
    *,
    base_revision: int,
    scope_day_number: int | None,
    origin: Literal["model", "fallback_rule_based"],
    blocking_codes: Collection[str],
    repairs: Mapping[str, int],
) -> tuple[SavedPlan, list[PlanFinding]]:
    """IMP-607 step 11: merge around fixed rows, then validate and snapshot the whole plan.

    The caller's transaction also completes the generation. Other days are only read for day
    scope; locked rows keep their identity, position, time, duration, notes and citations.
    """
    trip_row = await repository.lock_trip(session, trip_id, user_id)
    if trip_row is None:
        raise NotFound()
    if trip_row.plan_revision != base_revision:
        raise StalePlan()
    trip = await trips_service.get_trip(session, user_id, trip_id)
    prefs = await trips_service.get_preferences(session, user_id, trip_id)
    days = {day.day_number: day for day in await repository.plan_days(session, trip_id)}
    rows = await repository.plan_items(session, trip_id)
    numbers = {day.id: day.day_number for day in days.values()}
    target = (
        {scope_day_number}
        if scope_day_number is not None
        else set(days) | {day.day_number for day in plan}
    )
    if scope_day_number is not None and any(day.day_number != scope_day_number for day in plan):
        raise InvalidEdit("The generated plan is outside the requested day.")
    proposals = {day.day_number: day for day in plan}
    fixed = {
        str(item.place_id)
        for item, _, _ in rows
        if item.is_locked or numbers[item.day_id] not in target
    }
    seen = set(fixed)
    for item, _, _ in rows:
        if numbers[item.day_id] in target and not item.is_locked:
            await session.delete(item)
    await session.flush()  # release unlocked positions before inserting their replacements
    must_visit = {str(place_id) for place_id in prefs.must_visit_place_ids}
    for number in sorted(target):
        proposal = proposals.get(number)
        if number not in days:
            days[number] = ItineraryDay(
                trip_id=trip_id,
                day_number=number,
                plan_date=trip.start_date + timedelta(days=number - 1),
            )
            session.add(days[number])
            await session.flush()
        day = days[number]
        numbers[day.id] = number
        day.theme = proposal.theme if proposal else day.theme
        day.source_generation_id = generation_id
        locked = {
            item.position: item for item, _, _ in rows if item.day_id == day.id and item.is_locked
        }
        slots = dict(locked)
        # The output's item limit includes fixed slots, even when the model omitted them.
        capacity = max(len(locked), len(proposal.items) if proposal else 0)
        position = 1
        for item in proposal.items if proposal else ():
            if item.place_id in seen or len(slots) >= capacity:
                continue
            while position in slots:
                position += 1
            note = (item.note or None) if origin == "model" else None
            row = ItineraryItem(
                trip_id=trip_id,
                day_id=day.id,
                place_id=UUID(item.place_id),
                position=position,
                slot_type=item.slot_type,
                start_time=time.fromisoformat(item.start_time),
                duration_min=item.duration_min,
                origin=origin,
                note=note,
                note_origin="ai" if note else "none",
                is_locked=item.place_id in must_visit,
                source_chunk_ids=[UUID(chunk) for chunk in item.source_chunk_ids],
            )
            slots[position] = row
            seen.add(item.place_id)
            position += 1
        await _schedule_regenerated_day(
            session, trip, prefs.transport_pref.value, slots, set(locked)
        )
        for position, row in slots.items():
            if position not in locked:
                session.add(row)
    await session.flush()

    day_rows = [days[number] for number in sorted(days)]
    current = await repository.plan_items(session, trip_id)
    merged = planned_days(day_rows, current)
    ctx = await validation_context(
        session, user_id, trip, [item.place_id for day in merged for item in day.items]
    )
    findings = validator.validate(merged, ctx)
    if not any(day.items for day in merged) or any(f.code in blocking_codes for f in findings):
        raise InvalidEdit("No regenerated plan satisfied the checks around the locked items.")
    revision = await repository.mark_plan_saved(session, trip_id)
    # Fixed positions can leave a gap when fewer new items fit; validator refs are ordinal.
    ordinal: dict[UUID, int] = {}
    refs = {}
    for item, _, _ in current:
        ordinal[item.day_id] = ordinal.get(item.day_id, 0) + 1
        number = numbers[item.day_id]
        refs[f"d{number}-i{ordinal[item.day_id]}"] = f"d{number}-i{item.position}"
    await repository.insert_warnings(
        session,
        trip_id,
        revision,
        [f.model_copy(update={"item_ref": refs.get(f.item_ref, f.item_ref)}) for f in findings],
    )
    counts = {
        key: sum(f.severity == severity for f in findings)
        for severity, key in validator.SEVERITY_KEYS.items()
    }
    snapshot_items: dict[UUID, list[dict[str, Any]]] = {day.id: [] for day in day_rows}
    for item, _, _ in current:
        snapshot_items[item.day_id].append(
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
                "source_chunk_ids": [str(chunk) for chunk in item.source_chunk_ids],
            }
        )
    version = await repository.insert_version(
        session,
        trip_id,
        reason="regeneration",
        plan_revision=revision,
        snapshot={
            "schema": SNAPSHOT_SCHEMA,
            "plan_revision": revision,
            "days": [
                {
                    "day_number": day.day_number,
                    "plan_date": day.plan_date.isoformat(),
                    "theme": day.theme,
                    "items": snapshot_items[day.id],
                }
                for day in day_rows
            ],
            "budget_settings": await repository.budget_settings_snapshot(session, trip_id),
        },
        validation_summary={**counts, **repairs},
        generation_id=generation_id,
        created_by=user_id,
    )
    await retain_versions(session, trip_id)
    return SavedPlan(version.id, revision), findings


async def _schedule_regenerated_day(
    session: AsyncSession,
    trip: TripOut,
    mode: str,
    slots: dict[int, ItineraryItem],
    locked_positions: set[int],
) -> None:
    """Fit new visits in position order around fixed slots; all prices and legs come from code."""
    places = {
        place.id: place
        for place in await repository.places_by_ids(
            session, {item.place_id for item in slots.values()}
        )
    }
    routing = RoutingService(RouteCacheRepository(session), get_client())
    clock, previous = 9 * 60, None
    for position, item in sorted(slots.items()):
        place = places[item.place_id]
        travel = await routing.travel(places[previous.place_id], place, mode) if previous else None
        gap = travel.minutes + buffer_minutes(travel.travel_source) if travel else 0
        if position not in locked_positions:
            start = clock + gap
            duration = place.typical_duration_min
            following = next(
                (
                    fixed
                    for pos, fixed in sorted(slots.items())
                    if pos > position and pos in locked_positions
                ),
                None,
            )
            bound = 19 * 60
            if following is not None:
                leg = await routing.travel(place, places[following.place_id], mode)
                bound = (
                    following.start_time.hour * 60
                    + following.start_time.minute
                    - leg.minutes
                    - buffer_minutes(leg.travel_source)
                )
            if start + duration > bound:
                del slots[position]
                continue
            item.start_time = time(start // 60, start % 60)
            item.duration_min = duration
        item.travel_from_prev_min = travel.minutes if travel else None
        item.travel_from_prev_m = travel.distance_m if travel else None
        item.travel_mode = travel.mode.value if travel else None
        item.travel_source = travel.travel_source if travel else None
        cost = engine.item_cost(
            place, adults=trip.adults, children=trip.children, currency=trip_currency(trip)
        )
        item.cost_min = None if cost.lo is None else engine.from_minor(cost.lo)
        item.cost_max = None if cost.hi is None else engine.from_minor(cost.hi)
        item.cost_currency, item.cost_label = trip_currency(trip), cost.label
        clock = item.start_time.hour * 60 + item.start_time.minute + item.duration_min
        previous = item


async def retain_versions(session: AsyncSession, trip_id: UUID) -> None:
    """IMD-18 retention, after every version write: past MAX_VERSIONS versions delete the oldest
    automatic ones; a named version and the newest version are never deleted. With the switch off
    only BACKUP_VERSIONS automatic versions stay."""
    heads = await repository.version_heads(session, trip_id)
    if is_enabled(get_settings(), "versions"):
        excess = len(heads) - MAX_VERSIONS
    else:
        excess = sum(name is None for _, name in heads) - BACKUP_VERSIONS
    oldest_automatic = [version_id for version_id, name in reversed(heads[1:]) if name is None]
    await repository.delete_versions(session, oldest_automatic[: max(excess, 0)])


async def saved_plan_for_generation(session: AsyncSession, generation_id: UUID) -> SavedPlan | None:
    """The version a generation saved, for API-23's itinerary_version_id and plan_revision."""
    version = await repository.version_for_generation(session, generation_id)
    return None if version is None else SavedPlan(version.id, version.plan_revision)


NO_ITINERARY = "No itinerary yet."
AI_OUTCOMES = frozenset({"model", "model_repaired"})
ZERO = Decimal("0.00")
DEFAULT_CONTINGENCY_PCT = 10


def trip_currency(trip: TripOut) -> str:
    """§6.5: the budget's currency, else the destination's."""
    return trip.budget.currency if trip.budget else trip.destination.currency


async def _summary(
    session: AsyncSession,
    trip: TripOut,
    days: list[ItineraryDay],
    rows: list[tuple[ItineraryItem, Place, bool]],
) -> tuple[engine.CostSummary, int]:
    inputs = await validation_cost_inputs(session, trip)

    def minor(amount: Decimal | None) -> int | None:
        return None if amount is None else engine.to_minor(amount)

    numbers = {day.id: day.day_number for day in days}
    summary = engine.compute_costs(
        [
            engine.CostedItem(
                item_id=item.id,
                day_number=numbers[item.day_id],
                place_category=place.category,
                lo=minor(item.cost_min),
                hi=minor(item.cost_max),
                label=item.cost_label or engine.UNAVAILABLE,
            )
            for item, place, _ in rows
        ],
        inputs,
    )
    return summary, inputs.contingency_pct


async def cost_summary(session: AsyncSession, trip: TripOut) -> tuple[engine.CostSummary, int]:
    """The engine's result over the stored plan and the contingency percentage it used."""
    days = await repository.plan_days(session, trip.id)
    return await _summary(session, trip, days, await repository.plan_items(session, trip.id))


async def get_itinerary(session: AsyncSession, user_id: UUID, trip_id: UUID) -> ItineraryOut:
    """API-24: the trip's current plan; a missing or foreign trip and an empty plan answer 404.
    A stored version (``version_id``) is read by ``versions.read_version`` (IMP-610)."""
    trip = await trips_service.get_trip(session, user_id, trip_id)
    days = await repository.plan_days(session, trip_id)
    if not days:
        raise NotFound(NO_ITINERARY)
    rows = await repository.plan_items(session, trip_id)
    generation = await repository.latest_completed_generation(session, trip_id)
    out_days, totals = await plan_out(session, trip, days, rows, generation)
    return ItineraryOut(
        trip_id=trip.id,
        plan_revision=trip.plan_revision,
        version_id=await repository.latest_version_id(session, trip_id, trip.plan_revision),
        is_current=True,
        plan_stale=trip.plan_stale,
        source=None
        if generation is None
        else ItinerarySource.model_validate(
            {
                "generation_id": generation.id,
                "provider": generation.provider,
                "outcome": generation.outcome,
            }
        ),
        days=out_days,
        findings=await stored_findings(session, trip_id, trip.plan_revision),
        totals=totals,
    )


async def trip_summary(
    session: AsyncSession, user_id: UUID, trip_id: UUID, costs: CostSummaryOut
) -> TripSummaryOut:
    """API-35 (FR-094): a read-only projection of the current plan for the print view: the days
    as API-24 shows them (times, travel with its source, labelled costs, AI-written themes and
    notes), the stored findings of the current revision and the budget engine's ``costs``
    (API-33's answer). Nothing is calculated here; an empty plan answers 404."""
    trip = await trips_service.get_trip(session, user_id, trip_id)
    days = await repository.plan_days(session, trip_id)
    if not days:
        raise NotFound(NO_ITINERARY)
    rows = await repository.plan_items(session, trip_id)
    generation = await repository.latest_completed_generation(session, trip_id)
    out_days, _ = await plan_out(session, trip, days, rows, generation)
    return TripSummaryOut(
        trip=trip,
        days=out_days,
        unresolved_findings=await stored_findings(session, trip_id, trip.plan_revision),
        costs=costs,
        generated_at=datetime.now(UTC),
    )


async def plan_out(
    session: AsyncSession,
    trip: TripOut,
    days: Sequence[ItineraryDay],
    rows: Sequence[tuple[ItineraryItem, Place, bool]],
    generation: AiGeneration | None,
) -> tuple[list[Day], Totals]:
    """The response days and the engine's totals for the stored plan (API-24, EditResultOut);
    ``generation`` is the trip's latest completed one, which decides the AI-text labels."""
    sources = await rag_service.resolve_sources(
        session, [chunk_id for item, _, _ in rows for chunk_id in item.source_chunk_ids]
    )
    ai_text = generation is not None and generation.outcome in AI_OUTCOMES
    currency = trip_currency(trip)

    items_by_day: dict[UUID, list[tuple[ItineraryItem, Place, bool]]] = {}
    for row in rows:
        items_by_day.setdefault(row[0].day_id, []).append(row)

    out_days = []
    for day in days:
        day_rows = items_by_day.get(day.id, [])
        out_days.append(
            Day(
                day_number=day.day_number,
                date=day.plan_date,
                theme=day.theme,
                theme_origin="ai" if ai_text and day.theme else "none",
                items=[_item(*row, sources) for row in day_rows],
                day_cost=DayCost(**_cost_sum([item for item, _, _ in day_rows]), currency=currency),
            )
        )

    summary, _ = await _summary(session, trip, list(days), list(rows))
    totals = Totals(
        currency=currency,
        estimate=AmountRange(
            min=engine.from_minor(summary.estimate_lo),
            max=engine.from_minor(summary.estimate_hi),
        ),
        planning_total=engine.from_minor(summary.planning_total),
        complete=summary.complete,
        incomplete_count=len(summary.incomplete_items),
    )
    return out_days, totals


def _cost_sum(items: list[ItineraryItem]) -> dict[str, Any]:
    """BF-04: an item without a stored cost counts as 0 and makes the sum incomplete."""
    return {
        "min": sum((item.cost_min or ZERO for item in items), ZERO),
        "max": sum((item.cost_max or ZERO for item in items), ZERO),
        "complete": all(item.cost_min is not None for item in items),
    }


def _item(
    item: ItineraryItem, place: Place, must_visit: bool, sources: Mapping[UUID, Row[Any]]
) -> Item:
    start = datetime.combine(datetime.min, item.start_time)
    end = (start + timedelta(minutes=item.duration_min)).time()
    cost = None
    if item.cost_min is not None and item.cost_max is not None:
        cost = {
            "min": item.cost_min,
            "max": item.cost_max,
            "currency": item.cost_currency,
            "label": item.cost_label,
        }
    travel = None
    if item.travel_from_prev_min is not None:
        travel = {
            "minutes": item.travel_from_prev_min,
            "distance_m": item.travel_from_prev_m,
            "mode": item.travel_mode,
            "source": item.travel_source,
        }
    # Stored text columns are checked against the response vocabularies here.
    return Item.model_validate(
        {
            "id": item.id,
            "position": item.position,
            "place": {
                "id": place.id,
                "name": place.name,
                "category": place.category,
                "lat": float(place.lat),
                "lon": float(place.lon),
                "hours_label": place.hours_label,
            },
            "slot_type": item.slot_type,
            "start_time": item.start_time.strftime("%H:%M"),
            "duration_min": item.duration_min,
            "end_time": end.strftime("%H:%M"),
            "origin": item.origin,
            "is_locked": item.is_locked,
            "must_visit": must_visit,
            "note": item.note,
            "note_origin": item.note_origin,
            "cost": cost,
            "travel_from_previous": travel,
            "sources": [
                SourceRef.model_validate(sources[chunk_id], from_attributes=True)
                for chunk_id in item.source_chunk_ids
                if chunk_id in sources
            ],
        }
    )


async def latest_itinerary(session: AsyncSession, user_id: UUID) -> LatestItineraryOut:
    """API-09: the caller's most recently changed itinerary, or nulls when there is none."""
    found = await repository.latest_itinerary_for_user(session, user_id)
    if found is None:
        return LatestItineraryOut(trip_id=None, plan_revision=None, updated_at=None)
    trip_id, plan_revision, updated_at = found
    return LatestItineraryOut(trip_id=trip_id, plan_revision=plan_revision, updated_at=updated_at)


def planned_days(
    days: Sequence[ItineraryDay], rows: Sequence[tuple[ItineraryItem, Place, bool]]
) -> list[PlannedDay]:
    """The stored plan in the shape the validator and the edit pipeline read."""
    numbers = {day.id: day.day_number for day in days}
    items: dict[int, list[PlannedItem]] = {day.day_number: [] for day in days}
    for item, _, _ in rows:
        items[numbers[item.day_id]].append(
            PlannedItem(
                place_id=str(item.place_id),
                slot_type=item.slot_type,
                start_time=item.start_time.strftime("%H:%M"),
                duration_min=item.duration_min,
                note=item.note or "",
                travel_from_prev_min=item.travel_from_prev_min,
                travel_from_prev_m=item.travel_from_prev_m,
                travel_mode=item.travel_mode,
                travel_source=item.travel_source,
                cost_min=item.cost_min,
                cost_max=item.cost_max,
                cost_currency=item.cost_currency,
                cost_label=item.cost_label,
                source_chunk_ids=[str(chunk_id) for chunk_id in item.source_chunk_ids],
            )
        )
    return [PlannedDay(day.day_number, day.theme or "", items[day.day_number]) for day in days]


async def validation_context(
    session: AsyncSession, user_id: UUID, trip: TripOut, place_ids: Sequence[str]
) -> ValidationContext:
    """What the validator needs outside generation: no shortlist, the trip's must-visit places."""
    prefs = await trips_service.get_preferences(session, user_id, trip.id)
    ids = {UUID(place_id) for place_id in place_ids} | set(prefs.must_visit_place_ids)
    names = await places_service.active_place_names(session, trip.destination_id, sorted(ids))
    timezone, hours = await validation_hours(session, trip.destination_id)
    day_dates = {
        day.day_number: day.plan_date for day in await repository.plan_days(session, trip.id)
    }
    return ValidationContext(
        start_date=trip.start_date,
        end_date=trip.end_date,
        places={str(place_id): name for place_id, name in names.items()},
        must_visit_ids=frozenset(str(place_id) for place_id in prefs.must_visit_place_ids),
        pace=prefs.pace.value,
        timezone=timezone,
        cost_inputs=await validation_cost_inputs(session, trip),
        opening_hours=hours,
        day_dates=day_dates,
    )


async def revalidate(
    session: AsyncSession, user_id: UUID, trip_id: UUID, plan_revision: int
) -> ValidateOut:
    """API-32: validate the current plan again and replace the warnings of its revision; the
    plan and plan_revision do not change. A foreign trip or no plan is 404 (owner only)."""
    trip_row = await repository.lock_trip(session, trip_id, user_id)
    if trip_row is None:
        raise NotFound()
    trips_service.ensure_not_archived(trip_row.status)  # IMD-35: archived trips are read-only
    days = await repository.plan_days(session, trip_id)
    if not days:
        raise NotFound(NO_ITINERARY)
    if plan_revision != trip_row.plan_revision:
        raise StalePlan()
    trip = await trips_service.get_trip(session, user_id, trip_id)
    plan = planned_days(days, await repository.plan_items(session, trip_id))
    ctx = await validation_context(
        session, user_id, trip, [item.place_id for day in plan for item in day.items]
    )
    findings = validator.validate(plan, ctx)
    await repository.delete_warnings(session, trip_id, plan_revision)
    await repository.insert_warnings(session, trip_id, plan_revision, findings)
    return ValidateOut(
        plan_revision=plan_revision,
        findings=await stored_findings(session, trip_id, plan_revision),
        validation_summary=ValidationSummary(**validator.summary(findings)),
    )


async def stored_findings(
    session: AsyncSession, trip_id: UUID, plan_revision: int
) -> list[Finding]:
    return [
        Finding.model_validate(warning, from_attributes=True)
        for warning in await repository.current_warnings(session, trip_id, plan_revision)
    ]


async def version_findings(
    session: AsyncSession, user_id: UUID, trip_id: UUID, version_id: UUID
) -> tuple[list[Finding], dict[str, Any]]:
    """FR-058 AC1: a stored version's warnings (those of its plan_revision) and its
    validation_summary with the repair counts. API-24 with version_id reads it in IMP-610."""
    await trips_service.get_trip(session, user_id, trip_id)
    version = await repository.version_for_trip(session, trip_id, version_id)
    if version is None:
        raise NotFound()
    findings = await stored_findings(session, trip_id, version.plan_revision)
    return findings, dict(version.validation_summary)


async def locked_constraints(
    session: AsyncSession, user_id: UUID, trip_id: UUID, day_number: int | None = None
) -> list[LockedItem]:
    """Fixed destination-local slots for full or day regeneration (IMP-506, TC-313)."""
    await trips_service.get_trip(session, user_id, trip_id)
    days = {day.id: day.day_number for day in await repository.plan_days(session, trip_id)}
    return [
        LockedItem(
            place_id=item.place_id,
            day_number=days[item.day_id],
            start_time=item.start_time.strftime("%H:%M"),
            duration_min=item.duration_min,
        )
        for item, _, _ in await repository.plan_items(session, trip_id)
        if item.is_locked and (day_number is None or days[item.day_id] == day_number)
    ]


async def validation_hours(
    session: AsyncSession, destination_id: UUID
) -> tuple[str, dict[str, HoursInfo] | None]:
    """Read the authoritative weekly hours for generation, edits and API-32 (IMP-501)."""
    destination = await places_repository.destination_by_id(session, destination_id)
    if destination is None:
        raise NotFound()
    return destination.timezone, {
        str(place.id): HoursInfo(
            place.hours_label,
            [
                OpeningRow(
                    row.weekday,
                    row.is_closed,
                    row.open_time.strftime("%H:%M") if row.open_time else None,
                    row.close_time.strftime("%H:%M") if row.close_time else None,
                    row.closes_next_day,
                )
                for row in rows
            ],
        )
        for place, rows in await places_repository.candidates(session, destination_id)
    }


async def validation_cost_inputs(session: AsyncSession, trip: TripOut) -> engine.CostInputs:
    """One input frame for API totals and generation/edit/validate budget rules (BF-11)."""
    settings = await budget_repository.get_settings(session, trip.id)
    pct = int(settings.contingency_pct) if settings else DEFAULT_CONTINGENCY_PCT

    def minor(amount: Decimal | None) -> int | None:
        return None if amount is None else engine.to_minor(amount)

    return engine.CostInputs(
        num_days=trip.num_days,
        adults=trip.adults,
        children=trip.children,
        currency=trip_currency(trip),
        budget=minor(trip.budget.amount) if trip.budget else None,
        transport_per_day=minor(settings.transport_allowance_per_day) if settings else None,
        stay_per_night=minor(settings.stay_budget_per_night) if settings else None,
        contingency_pct=pct if is_enabled(get_settings(), "contingency") else 0,
    )


# IMP-602 duplicate
_NOT_COPIED = frozenset({"id", "trip_id", "created_at", "updated_at"})


def _columns(row: Any) -> dict[str, Any]:
    """A plan row's column values, without its identity, trip and timestamps."""
    return {c.key: getattr(row, c.key) for c in row.__table__.columns if c.key not in _NOT_COPIED}


async def copy_plan(
    session: AsyncSession, source_trip_id: UUID, source_revision: int, target_trip_id: UUID
) -> None:
    """API-13 (FR-015 AC1, A1 §6.10): copy the source's days, items (locks and source_chunk_ids
    included) and its current revision's warnings to a new trip that has no plan, which then has
    plan_revision 1. The source is only read; generation links are not copied."""
    days: dict[UUID, UUID] = {}
    for day in await repository.plan_days(session, source_trip_id):
        copy = ItineraryDay(
            **{**_columns(day), "source_generation_id": None}, trip_id=target_trip_id
        )
        session.add(copy)
        await session.flush()
        days[day.id] = copy.id
    items: dict[UUID, UUID] = {}
    for item, _, _ in await repository.plan_items(session, source_trip_id):
        item_copy = ItineraryItem(
            **{**_columns(item), "day_id": days[item.day_id]}, trip_id=target_trip_id
        )
        session.add(item_copy)
        await session.flush()
        items[item.id] = item_copy.id
    revision = await repository.bump_revision(session, target_trip_id)
    for warning in await repository.current_warnings(session, source_trip_id, source_revision):
        values = _columns(warning)
        values["plan_revision"] = revision
        values["item_id"] = items.get(warning.item_id) if warning.item_id else None
        # type(warning) is ItineraryWarning; this block is append-only, so no new top-level import.
        session.add(type(warning)(**values, trip_id=target_trip_id))
    await session.flush()
