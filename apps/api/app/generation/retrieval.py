"""Candidate retrieval and hard-constraint filters (§8.9; FR-027, IMP-304).

The filters come from pm-1 (``trips/preference_mapping.py``) and run in the card's order: step-free,
excluded categories, closed on every trip day (explicit closed rows only), minimum group cost
above the activity budget. The children rule of pm-1 runs after step-free. A place that fails is
removed unless it is a must-visit place, which stays with ``conflict_note`` set (FR-027 AC2).
Ranking and the shortlist cut are in ``generation/ranking.py``.
"""

from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Final
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Place, PlaceOpeningHours
from app.generation import repository
from app.places import repository as places_repository
from app.trips import preference_mapping
from app.trips.schemas import PreferencesOut, TripOut

CENT: Final = Decimal("0.01")
DEFAULT_CONTINGENCY_PCT: Final = Decimal("10")

NOTE_STEP_FREE: Final = "Must-visit place is not confirmed step-free."
NOTE_CATEGORY: Final = "Must-visit place is in a category that is not planned."
NOTE_CHILDREN: Final = "Must-visit place is not suitable for children."
NOTE_CLOSED: Final = "Must-visit place is closed on every day of the trip."
NOTE_OVER_BUDGET: Final = "Must-visit place costs more than the activity budget."


@dataclass(frozen=True)
class Candidate:
    place: Place
    hours: tuple[PlaceOpeningHours, ...]
    must_visit: bool
    conflict_note: str | None
    min_group_cost: Decimal | None  # None: no price in the trip's currency (§9.3.1 BF-04)


def activity_budget(
    budget: Decimal | None,
    *,
    num_days: int,
    transport_per_day: Decimal | None,
    stay_per_night: Decimal | None,
    contingency_pct: Decimal,
) -> Decimal | None:
    """What activities and meals may cost so that the planning total P stays within the budget.

    From §9.3.1: P = S·(1 + p/100) and S = activities + D·t + (D - 1)·s, with a missing line
    counted as 0. None when the trip has no budget. See PD-IMP-304-1: blueprint §20.2 is not in
    the repository, and this is the definition the specification's formulas give.
    """
    if budget is None:
        return None
    spendable = budget / (1 + contingency_pct / 100)
    lines = num_days * (transport_per_day or 0) + (num_days - 1) * (stay_per_night or 0)
    return max(spendable - lines, Decimal(0)).quantize(CENT, ROUND_HALF_UP)


def min_group_cost(
    place: Place, *, adults: int, children: int, currency: str | None
) -> Decimal | None:
    """The lowest cost of the place for the group: §9.3.1 BF-01 and BF-02 on ``price_min``."""
    if place.price_min is None or place.price_currency != currency:
        return None
    if "price_per_group" in place.tags:
        return place.price_min
    factor = (
        0 if "child_free" in place.tags else Decimal("0.5") if "child_half" in place.tags else 1
    )
    child_part = (children * factor * place.price_min).quantize(CENT, ROUND_HALF_UP)
    return adults * place.price_min + child_part


def _conflict(
    place: Place,
    hours: Iterable[PlaceOpeningHours],
    cost: Decimal | None,
    *,
    filters: preference_mapping.HardFilters,
    weekdays: set[int],
    budget: Decimal | None,
) -> str | None:
    """The note of the first hard filter the place fails, or None when it passes them all."""
    if not filters.keeps(step_free=place.step_free, child_friendly=None):
        return NOTE_STEP_FREE
    if place.category in filters.categories_excluded:
        return NOTE_CATEGORY
    if not filters.keeps(step_free=True, child_friendly=place.child_friendly):
        return NOTE_CHILDREN
    if weekdays <= {row.weekday for row in hours if row.is_closed}:
        return NOTE_CLOSED
    if budget is not None and cost is not None and cost > budget:
        return NOTE_OVER_BUDGET
    return None


def apply_filters(
    rows: Iterable[tuple[Place, Sequence[PlaceOpeningHours]]],
    trip: TripOut,
    prefs: PreferencesOut,
    must_visit: Collection[UUID],
    budget: Decimal | None,
) -> list[Candidate]:
    """The rows that pass the hard filters, and the must-visit rows with their conflict note."""
    filters = preference_mapping.map_preferences(
        preference_mapping.Preferences(
            step_free_required=prefs.step_free_required, must_visit_place_ids=list(must_visit)
        ),
        preference_mapping.TripFacts(children=trip.children),
    ).filters
    weekdays = {
        (trip.start_date + timedelta(days=offset)).isoweekday() for offset in range(trip.num_days)
    }
    currency = trip.budget.currency if trip.budget else None
    kept = []
    for place, hours in rows:
        cost = min_group_cost(place, adults=trip.adults, children=trip.children, currency=currency)
        note = _conflict(place, hours, cost, filters=filters, weekdays=weekdays, budget=budget)
        is_must_visit = place.id in filters.must_visit_place_ids
        if note is None or is_must_visit:
            kept.append(Candidate(place, tuple(hours), is_must_visit, note, cost))
    return kept


async def retrieve_candidates(
    session: AsyncSession, trip: TripOut, prefs: PreferencesOut, must_visit: Collection[UUID]
) -> list[Candidate]:
    """The filtered candidates of the trip's destination (§8.9 Retrieve and Hard filters)."""
    settings = await repository.budget_settings(session, trip.id)
    budget = activity_budget(
        trip.budget.amount if trip.budget else None,
        num_days=trip.num_days,
        transport_per_day=settings.transport_allowance_per_day if settings else None,
        stay_per_night=settings.stay_budget_per_night if settings else None,
        contingency_pct=settings.contingency_pct if settings else DEFAULT_CONTINGENCY_PCT,
    )
    rows = await places_repository.candidates(session, trip.destination_id)
    return apply_filters(rows, trip, prefs, must_visit, budget)
