"""Rule-based fallback planner (§8.15, FR-036; IMP-402).

Pure and deterministic: the same gr-1 request always gives the same io-1 answer, with no model,
no I/O and no randomness, so the plan goes through steps 8 to 11 like a model answer. Per day:
start at ``limits.day_start``; pick must-visit places first, then the day's hinted places, then
the rest, each time the nearest one that still fits (ties by shortlist rank); one ``food`` place
becomes the meal once the clock reaches the lunch window; stop at the pace limits or ``day_end``.
Travel is the labelled distance estimate (§9.3.5) plus its buffer, the arithmetic step 9 repeats.

Only shortlisted places on days 1..num_days are used, items never overlap, so no UNKNOWN_PLACE,
OUTSIDE_TRIP_DATES or OVERLAP can come from here. A must-visit place that does not fit is left out
and step 9's validator reports it as MUST_VISIT_MISSING. Themes come from a fixed template and
items carry no note (IMD-131), so nothing here is ever labelled AI-written. This module shares no
code with the mock provider (card step 6).
"""

from typing import Final

from app.routing.estimate import BUFFER_MIN, estimate
from app.schemas.ai import (
    GenerationRequest,
    ItineraryDayOutput,
    ItineraryItemOutput,
    ItineraryOutput,
    ShortlistPlace,
)

MODEL_ID: Final = "rule_based_planner_v1"  # IMD-43: only when mode rule_based was requested
LUNCH_FROM: Final = 12 * 60
LUNCH_TO: Final = 14 * 60
THEME_MAX: Final = 80
SUMMARY: Final = "Plan built by rules, without AI."
FOOD: Final = "food"


def _minutes(hhmm: str) -> int:
    hours, mins = hhmm.split(":")
    return int(hours) * 60 + int(mins)


def _hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _travel(previous: ShortlistPlace | None, place: ShortlistPlace, mode: str) -> int:
    """Minutes from the previous item's end to this item's start: travel plus its buffer."""
    if previous is None:
        return 0
    leg = estimate(previous.lat, previous.lon, place.lat, place.lon, mode)
    return leg.minutes + BUFFER_MIN[leg.travel_source]


def _day_numbers(request: GenerationRequest) -> list[int]:
    if request.scope.kind == "day" and request.scope.day_number is not None:
        return [request.scope.day_number]
    return list(range(1, request.trip.num_days + 1))


class NoPlanError(Exception):
    """No shortlisted place fits any day, so there is no io-1 answer to give."""


def _wanted(place: ShortlistPlace, must: set[str], lunch_due: bool, had_meal: bool) -> bool:
    if place.category != FOOD:
        return not lunch_due
    # The meal place in the lunch window; a must-visit food place at any time.
    return not had_meal and (lunch_due or str(place.place_id) in must)


def _by_preference(
    pool: list[ShortlistPlace],
    previous: ShortlistPlace | None,
    tiers: tuple[set[str], set[str]],
    rank: dict[str, int],
    mode: str,
) -> list[ShortlistPlace]:
    """Must-visit, then hinted for the day, then the rest; nearest first, ties by rank."""
    must, hinted = tiers

    def key(place: ShortlistPlace) -> tuple[int, int, int]:
        place_id = str(place.place_id)
        tier = 0 if place_id in must else 1 if place_id in hinted else 2
        return (tier, _travel(previous, place, mode), rank[place_id])

    return sorted(pool, key=key)


def plan_rule_based(request: GenerationRequest) -> ItineraryOutput:
    """Raises ``NoPlanError`` when not one item fits, as io-1 needs at least one."""
    limits = request.limits
    mode = request.preferences.transport_pref
    must = {str(place_id) for place_id in request.must_visit_place_ids}
    hints = {hint.day_number: {str(i) for i in hint.place_ids} for hint in request.day_hints}
    rank = {str(place.place_id): index for index, place in enumerate(request.shortlist)}
    remaining = list(request.shortlist)
    day_start, day_end = _minutes(limits.day_start), _minutes(limits.day_end)
    days: list[ItineraryDayOutput] = []

    for day_number in _day_numbers(request):
        tiers = (must, hints.get(day_number, set()))
        items: list[ItineraryItemOutput] = []
        names: list[str] = []
        clock, active, had_meal = day_start, 0, False
        previous: ShortlistPlace | None = None

        while remaining and len(items) < limits.max_items_per_day:
            lunch_due = not had_meal and LUNCH_FROM <= clock <= LUNCH_TO
            pool = [p for p in remaining if _wanted(p, must, lunch_due, had_meal)]
            chosen = None
            for place in _by_preference(pool, previous, tiers, rank, mode):
                travel = _travel(previous, place, mode)
                if lunch_due and clock + travel > LUNCH_TO:
                    continue  # the meal starts inside the lunch window or not at all
                end = clock + travel + place.typical_duration_min
                spent = active + travel + place.typical_duration_min
                if end <= day_end and spent <= limits.max_active_minutes_per_day:
                    chosen, clock, active = place, end, spent
                    break
            if chosen is None:
                if lunch_due:  # no food place fits: the day goes on without a meal
                    had_meal = True
                    continue
                break

            is_meal = chosen.category == FOOD
            had_meal = had_meal or is_meal
            remaining.remove(chosen)
            names.append(chosen.name)
            items.append(
                ItineraryItemOutput(
                    place_id=str(chosen.place_id),
                    start_time=_hhmm(clock - chosen.typical_duration_min),
                    duration_min=chosen.typical_duration_min,
                    slot_type="meal" if is_meal else "activity",
                    note="",
                )
            )
            previous = chosen

        if items:
            theme = f"Day {day_number} around {names[0]}"[:THEME_MAX]
            days.append(ItineraryDayOutput(day_number=day_number, theme=theme, items=items))

    if not days:
        raise NoPlanError()
    return ItineraryOutput(days=days, summary=SUMMARY, assumptions=[])
