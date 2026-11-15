"""Scoring and shortlist ranking (§8.9; FR-028, IMP-304). Pure: no I/O and no framework imports.

score = w_interest·interest + w_semantic·semantic + w_price·price + w_distance·distance
+ w_pace·pace + w_signal·signal. The weights, the budget-priority shift and the pace factors come
only from pm-2 (``trips/preference_mapping.py``, IMD-29, IMD-108); the signal weight is 0 in the MVP.

- interest: the trip's interests the place matches, by tag or by category, ÷ interests. Interests
  are category names (§6.5) and tags are not, so tags alone could never match a museum.
- semantic: the place's similarity to the query, min-max normalised over the candidates, 0.5 when
  all are equal or there is one, 0 without an embedded chunk (A1 §6.7).
- price: 1 up to the per-item share of the activity budget, falling to 0 at twice that share,
  0.5 when unavailable. The share is the budget ÷ (days x the pace's items per day).
- distance: 1 - d/radius to the must-visit centroid or the destination centre, never below 0. The
  radius is half the destination bounding box's diagonal.
- pace: ``RankingWeights.duration_component``.
- signal (IMP-605): 1 for a place the traveller saved, 0 for a rejected one, 0.5 otherwise, when
  the ``wishlist`` switch is on (``relations`` given); 0 when it is off. A saved place is only this
  signal: it never becomes must-visit or locked.

The share and the radius are PD-IMP-304-4: blueprint §20.2 is not in the repository.
"""

import logging
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Final, Protocol

from app.routing.estimate import haversine_m
from app.trips.preference_mapping import MAPPING_VERSION, MappedPreferences

logger = logging.getLogger(__name__)

SHORTLIST_MIN: Final = 12
SHORTLIST_MAX: Final = 40
SHORTLIST_PER_DAY: Final = 8
PRICE_UNAVAILABLE: Final = 0.5
FOOD_CATEGORY: Final = "food"
SIGNAL_BY_RELATION: Final = {"saved": 1.0, "rejected": 0.0}
SIGNAL_NEUTRAL: Final = 0.5


class RankablePlace(Protocol):
    @property
    def id(self) -> object: ...
    @property
    def category(self) -> str: ...
    @property
    def tags(self) -> list[str]: ...
    @property
    def lat(self) -> Decimal: ...
    @property
    def lon(self) -> Decimal: ...
    @property
    def typical_duration_min(self) -> int: ...


class Rankable(Protocol):
    """What ranking reads from a ``generation.retrieval.Candidate``."""

    @property
    def place(self) -> RankablePlace: ...
    @property
    def must_visit(self) -> bool: ...
    @property
    def min_group_cost(self) -> Decimal | None: ...


class DestinationArea(Protocol):
    @property
    def center_lat(self) -> Decimal: ...
    @property
    def center_lon(self) -> Decimal: ...
    @property
    def bbox_min_lat(self) -> Decimal: ...
    @property
    def bbox_max_lat(self) -> Decimal: ...
    @property
    def bbox_min_lon(self) -> Decimal: ...
    @property
    def bbox_max_lon(self) -> Decimal: ...


@dataclass(frozen=True)
class RankingContext:
    mapped: MappedPreferences
    num_days: int
    meal_slots_per_day: int
    activity_budget: Decimal | None
    centre_lat: float
    centre_lon: float
    radius_m: float
    semantic: Mapping[object, float] = field(default_factory=dict)  # by place ID
    relations: Mapping[object, str] | None = None  # trip_places relation by place ID; None: off


@dataclass(frozen=True)
class ScoreParts:
    interest: float
    semantic: float
    price: float
    distance: float
    pace: float
    signal: float
    total: float


@dataclass(frozen=True)
class Scored[C: Rankable]:
    candidate: C
    parts: ScoreParts


@dataclass(frozen=True)
class Shortlist[C: Rankable]:
    entries: list[Scored[C]]
    mapping_version: str = MAPPING_VERSION


def c_semantic(
    place_ids: Iterable[object], similarities: Mapping[Any, float]
) -> dict[object, float]:
    """The normalised similarity of the places that have one; the others score 0 in ``score``."""
    known = {id_: similarities[id_] for id_ in place_ids if id_ in similarities}
    if not known:
        return {}
    low, high = min(known.values()), max(known.values())
    if low == high:
        return dict.fromkeys(known, 0.5)
    return {id_: (value - low) / (high - low) for id_, value in known.items()}


def c_signal(place_id: object, relations: Mapping[Any, str] | None) -> float:
    """The saved or rejected signal (IMP-605); 0 when the wishlist is switched off. Its pm-2
    weight is 0 in the MVP (§8.9), so it does not change the total yet."""
    if relations is None:
        return 0.0
    return SIGNAL_BY_RELATION.get(relations.get(place_id, ""), SIGNAL_NEUTRAL)


def build_context(
    candidates: Iterable[Rankable],
    mapped: MappedPreferences,
    destination: DestinationArea,
    *,
    num_days: int,
    meal_slots_per_day: int,
    activity_budget: Decimal | None,
    similarities: Mapping[Any, float] | None = None,
    relations: Mapping[Any, str] | None = None,
) -> RankingContext:
    """The context of one trip: its centre is the must-visit centroid, else the destination's."""
    candidates = list(candidates)
    must_visit = [c.place for c in candidates if c.must_visit]
    if must_visit:
        lat = sum(float(place.lat) for place in must_visit) / len(must_visit)
        lon = sum(float(place.lon) for place in must_visit) / len(must_visit)
    else:
        lat, lon = float(destination.center_lat), float(destination.center_lon)
    diagonal = haversine_m(
        float(destination.bbox_min_lat),
        float(destination.bbox_min_lon),
        float(destination.bbox_max_lat),
        float(destination.bbox_max_lon),
    )
    return RankingContext(
        mapped=mapped,
        num_days=num_days,
        meal_slots_per_day=meal_slots_per_day,
        activity_budget=activity_budget,
        centre_lat=lat,
        centre_lon=lon,
        radius_m=max(diagonal / 2, 1.0),
        semantic=c_semantic((c.place.id for c in candidates), similarities or {}),
        relations=relations,
    )


def _interest(place: RankablePlace, wanted: frozenset[str]) -> float:
    if not wanted:
        return 0.0
    return len(wanted & {*place.tags, place.category}) / len(wanted)


def _price(cost: Decimal | None, ctx: RankingContext) -> float:
    if cost is None or ctx.activity_budget is None:
        return PRICE_UNAVAILABLE
    items = ctx.num_days * ctx.mapped.pace_limits.max_items_per_day
    share = ctx.activity_budget / items
    if cost <= share:
        return 1.0
    return max(0.0, float(2 - cost / share)) if share else 0.0


def _distance(place: RankablePlace, ctx: RankingContext) -> float:
    metres = haversine_m(ctx.centre_lat, ctx.centre_lon, float(place.lat), float(place.lon))
    return max(0.0, 1 - metres / ctx.radius_m)


def score(candidate: Rankable, ctx: RankingContext) -> ScoreParts:
    place, weights = candidate.place, ctx.mapped.weights
    interest = _interest(place, weights.interests)
    semantic = ctx.semantic.get(place.id, 0.0)
    price = _price(candidate.min_group_cost, ctx)
    distance = _distance(place, ctx)
    pace = weights.duration_component(place.typical_duration_min)
    signal = c_signal(place.id, ctx.relations)
    total = (
        weights.interest * interest
        + weights.semantic * semantic
        + weights.price * price
        + weights.distance * distance
        + weights.duration * pace
        + weights.c_signal * signal
    )
    return ScoreParts(interest, semantic, price, distance, pace, signal, total)


def shortlist_size(num_days: int) -> int:
    return min(SHORTLIST_MAX, max(SHORTLIST_MIN, SHORTLIST_PER_DAY * num_days))


def rank[C: Rankable](candidates: Iterable[C], ctx: RankingContext) -> list[Scored[C]]:
    """Every candidate by score, best first, ties by place ID: the order of the shortlist, and of
    the replacement alternatives of API-28 (IMP-505)."""
    return sorted(
        (Scored(candidate, score(candidate, ctx)) for candidate in candidates),
        key=lambda entry: (-entry.parts.total, str(entry.candidate.place.id)),
    )


def rank_shortlist[C: Rankable](candidates: Iterable[C], ctx: RankingContext) -> Shortlist[C]:
    """The best places by score (ties by place ID), plus every must-visit place, plus enough food
    places for the meal slots (§8.9), in rank order.

    Category stay is left out unless the traveller named it: a must-visit place is never dropped
    silently, and its conflict note already says it will not be planned.
    """
    excluded = ctx.mapped.filters.categories_excluded
    ranked = rank(
        (
            candidate
            for candidate in candidates
            if candidate.must_visit or candidate.place.category not in excluded
        ),
        ctx,
    )
    size = shortlist_size(ctx.num_days)
    chosen = ranked[:size]
    food_needed = ctx.num_days * ctx.meal_slots_per_day - sum(
        entry.candidate.place.category == FOOD_CATEGORY for entry in chosen
    )
    for entry in ranked[size:]:
        is_food = entry.candidate.place.category == FOOD_CATEGORY
        if entry.candidate.must_visit or (is_food and food_needed > 0):
            chosen.append(entry)
            food_needed -= is_food
    for entry in chosen:
        parts = entry.parts
        logger.debug(
            "score place=%s interest=%.3f semantic=%.3f price=%.3f distance=%.3f pace=%.3f "
            "signal=%.3f total=%.3f",
            entry.candidate.place.id,
            parts.interest,
            parts.semantic,
            parts.price,
            parts.distance,
            parts.pace,
            parts.signal,
            parts.total,
        )
    return Shortlist(chosen)
