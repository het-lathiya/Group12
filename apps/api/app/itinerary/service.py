"""Itinerary service (MOD-B08): the only writer of the plan (§3, IMD-13).

``save_generated_plan`` is step 11 of the pipeline (§8.2): it runs in the caller's transaction,
which also completes the generation record, so the plan, the version and the record are saved
together or not at all (NFR-008). ``get_itinerary`` (API-24) and ``latest_itinerary`` (API-09)
read the saved plan for its owner (IMP-211). ``revalidate`` (API-32) re-runs the validator on the
current plan and replaces that revision's warnings; ``version_findings`` reads a stored version's
warnings and summary (FR-058, IMP-405). ``plan_out`` builds the days and totals that API-24 and
the edit core (``edits.apply_edit``, IMP-407) return.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import Row
from sqlalchemy.ext.asyncio import AsyncSession

from app.budget import engine
from app.budget import repository as budget_repository
from app.budget.schemas import AmountRange
from app.core.config import get_settings
from app.core.errors import EndpointNotImplemented, NotFound, StalePlan
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
    ValidateOut,
)
from app.places import service as places_service
from app.rag import service as rag_service
from app.schemas.ai import LockedItem, PlanFinding
from app.trips import preference_mapping
from app.trips import service as trips_service
from app.trips.schemas import TripOut
from app.validation import validator
from app.validation.rules import ValidationContext
from app.validation.schemas import Finding, ValidationSummary

SNAPSHOT_SCHEMA = "snap-1"


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
) -> SavedPlan:
    """``origin`` fallback_rule_based saves no note (IMD-131) and a version of reason fallback.

    ``findings`` are the validator's on this plan, saved as its warnings (§8.12, IMD-42). Model
    text is stored only in the day theme and the item note (note_origin ai); hours, prices and
    travel come only from backend columns (FR-035).
    """
    trip = await repository.lock_trip(session, trip_id, user_id)
    if trip is None:
        raise NotFound()
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
    version_id = await repository.insert_version(
        session,
        trip_id,
        reason="generation" if origin == "model" else "fallback",
        plan_revision=plan_revision,
        snapshot=snapshot,
        validation_summary=validation_summary,
        generation_id=generation_id,
        created_by=user_id,
    )
    return SavedPlan(version_id=version_id, plan_revision=plan_revision)


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
    settings = await budget_repository.get_settings(session, trip.id)
    pct = int(settings.contingency_pct) if settings else DEFAULT_CONTINGENCY_PCT
    if not is_enabled(get_settings(), "contingency"):
        pct = 0  # BF-08

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
        engine.CostInputs(
            num_days=trip.num_days,
            adults=trip.adults,
            children=trip.children,
            currency=trip_currency(trip),
            budget=minor(trip.budget.amount) if trip.budget else None,
            transport_per_day=minor(settings.transport_allowance_per_day) if settings else None,
            stay_per_night=minor(settings.stay_budget_per_night) if settings else None,
            contingency_pct=pct,
        ),
    )
    return summary, pct


async def cost_summary(session: AsyncSession, trip: TripOut) -> tuple[engine.CostSummary, int]:
    """The engine's result over the stored plan and the contingency percentage it used."""
    days = await repository.plan_days(session, trip.id)
    return await _summary(session, trip, days, await repository.plan_items(session, trip.id))


async def get_itinerary(
    session: AsyncSession, user_id: UUID, trip_id: UUID, version_id: UUID | None = None
) -> ItineraryOut:
    """API-24: the trip's current plan; a missing or foreign trip and an empty plan answer 404."""
    trip = await trips_service.get_trip(session, user_id, trip_id)
    if version_id is not None:
        raise EndpointNotImplemented()  # reading a stored version is IMP-610 (IMD-37)
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
    return ValidationContext(
        start_date=trip.start_date,
        end_date=trip.end_date,
        places={str(place_id): name for place_id, name in names.items()},
        must_visit_ids=frozenset(str(place_id) for place_id in prefs.must_visit_place_ids),
        pace_limits=preference_mapping.PACE_LIMITS[preference_mapping.Pace(prefs.pace)],
    )


async def revalidate(
    session: AsyncSession, user_id: UUID, trip_id: UUID, plan_revision: int
) -> ValidateOut:
    """API-32: validate the current plan again and replace the warnings of its revision; the
    plan and plan_revision do not change. A foreign trip or no plan is 404 (owner only)."""
    trip_row = await repository.lock_trip(session, trip_id, user_id)
    if trip_row is None:
        raise NotFound()
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
