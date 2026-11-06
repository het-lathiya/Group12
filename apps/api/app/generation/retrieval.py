"""Candidate retrieval and hard-constraint filters (§8.9; FR-027, IMP-304).

The filters come from pm-2 (``trips/preference_mapping.py``) and run in the card's order: step-free,
excluded categories, closed on every trip day (explicit closed rows only), minimum group cost
above the activity budget. The children rule of pm-2 runs after step-free. A place that fails is
removed unless it is a must-visit place, which stays with ``conflict_note`` set (FR-027 AC2).
Ranking and the shortlist cut are in ``generation/ranking.py``; ``ranked_shortlist`` runs both.
``semantic_retrieval`` runs before ranking, outside any transaction, and never raises for a
retrieval failure; its result carries ``retrieval_ms`` for IMP-316 (Amendment A1 §6.7, §6.11).
"""

from collections.abc import Callable, Collection, Iterable, Sequence
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Final
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers.base import ModelProvider
from app.core.errors import NotFound
from app.db.models import Place, PlaceOpeningHours
from app.generation import ranking, repository
from app.places import repository as places_repository
from app.rag import service as rag_service
from app.rag.query import build_query_text
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


async def _trip_activity_budget(session: AsyncSession, trip: TripOut) -> Decimal | None:
    settings = await repository.budget_settings(session, trip.id)
    return activity_budget(
        trip.budget.amount if trip.budget else None,
        num_days=trip.num_days,
        transport_per_day=settings.transport_allowance_per_day if settings else None,
        stay_per_night=settings.stay_budget_per_night if settings else None,
        contingency_pct=settings.contingency_pct if settings else DEFAULT_CONTINGENCY_PCT,
    )


async def retrieve_candidates(
    session: AsyncSession, trip: TripOut, prefs: PreferencesOut, must_visit: Collection[UUID]
) -> list[Candidate]:
    """The filtered candidates of the trip's destination (§8.9 Retrieve and Hard filters)."""
    budget = await _trip_activity_budget(session, trip)
    rows = await places_repository.candidates(session, trip.destination_id)
    return apply_filters(rows, trip, prefs, must_visit, budget)


async def semantic_retrieval(
    trip: TripOut,
    prefs: PreferencesOut,
    notes_quoted: str | None,
    provider: ModelProvider,
    sessions: Callable[[], AbstractAsyncContextManager[AsyncSession]],
) -> rag_service.RetrievalResult:
    """Step 3 of §8.2 as A1 §6.7 extends it: similarities of the candidates and guide passages."""
    async with sessions() as session:
        candidates = await retrieve_candidates(session, trip, prefs, prefs.must_visit_place_ids)
    context = rag_service.RetrievalContext(
        destination_id=trip.destination_id,
        query_text=build_query_text(
            destination=trip.destination.name,
            interests=[interest.value for interest in prefs.interests],
            pace=prefs.pace.value,
            budget_priority=prefs.budget_priority.value,
            transport=prefs.transport_pref.value,
            group_needs=[need.value for need in trip.group_needs],
            step_free=prefs.step_free_required,
            notes_quoted=notes_quoted,
        ),
        place_ids=[candidate.place.id for candidate in candidates],
    )
    return await rag_service.retrieve(context, provider=provider, sessions=sessions)


async def ranked_shortlist(
    session: AsyncSession,
    trip: TripOut,
    prefs: PreferencesOut,
    must_visit: Collection[UUID],
    *,
    meal_slots_per_day: int,
    retrieved: rag_service.RetrievalResult | None = None,
) -> list[Candidate]:
    """Steps 3 and 4 of §8.2: the candidates that make the shortlist, best first.

    Without a ``vector`` retrieval result the ranking is lexical: no semantic weight.
    """
    semantic = retrieved is not None and retrieved.mode == "vector"
    candidates = await retrieve_candidates(session, trip, prefs, must_visit)
    destination = await places_repository.destination_by_id(session, trip.destination_id)
    if destination is None:
        raise NotFound()
    mapped = preference_mapping.map_preferences(
        preference_mapping.Preferences(
            interests=[interest.value for interest in prefs.interests],
            pace=preference_mapping.Pace(prefs.pace),
            budget_priority=preference_mapping.BudgetPriority(prefs.budget_priority),
            step_free_required=prefs.step_free_required,
            must_visit_place_ids=list(must_visit),
        ),
        preference_mapping.TripFacts(children=trip.children),
        semantic=semantic,
    )
    context = ranking.build_context(
        candidates,
        mapped,
        destination,
        num_days=trip.num_days,
        meal_slots_per_day=meal_slots_per_day,
        activity_budget=await _trip_activity_budget(session, trip),
        similarities=retrieved.place_similarity if retrieved and semantic else None,
    )
    return [entry.candidate for entry in ranking.rank_shortlist(candidates, context).entries]
