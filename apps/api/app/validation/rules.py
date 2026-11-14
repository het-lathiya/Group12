"""Validator rules (MOD-B07, §8.12, §9.3.4 to §9.3.7; IMP-404).

Pure: no I/O and no framework imports. Each rule reads a recalculated plan (the times and travel
that step 9 stored, IMP-308) and a ``ValidationContext`` and returns findings. ``RULES`` is the
fixed order in which ``app.validation.validator.validate`` runs them. A plan is any object with
the attributes of the ``Plan*`` protocols, so ``PlannedDay`` and the saved rows both fit and this
module imports no other module's schemas.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Final, Protocol
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo

from app.budget import engine
from app.generation.presets import pace_limits
from app.routing.estimate import BUFFER_MIN
from app.schemas.ai import MAX_TRIP_DAYS, FindingCode, PlanFinding, Severity

Finding = PlanFinding  # {code, severity, message, day_number, item_ref, place_id, suggested_fix}

# §8.12: the 13 finding codes and their severities. OUTSIDE_HOURS is an error when the hours are
# curated and a warning when they are an estimate (its rule, IMP-309, picks); ESTIMATE_USED is in
# the catalogue but never emitted (IMD-124 B6).
CATALOGUE: Final[Mapping[FindingCode, Severity]] = {
    "OVERLAP": "error",
    "TRANSFER_TOO_SHORT": "warning",
    "CLOSED_ON_DAY": "error",
    "OUTSIDE_HOURS": "error",
    "HOURS_UNVERIFIED": "info",
    "DAY_TOO_LONG": "warning",
    "BUDGET_EXCEEDED": "warning",
    "BUDGET_NEAR": "info",
    "MUST_VISIT_MISSING": "error",
    "UNKNOWN_PLACE": "error",
    "OUTSIDE_TRIP_DATES": "error",
    "COST_INCOMPLETE": "warning",
    "ESTIMATE_USED": "info",
}


class PlanItem(Protocol):
    @property
    def place_id(self) -> str: ...
    @property
    def start_time(self) -> str: ...
    @property
    def duration_min(self) -> int: ...
    @property
    def travel_from_prev_min(self) -> int | None: ...
    @property
    def travel_source(self) -> str | None: ...


class PlanDay(Protocol):
    @property
    def day_number(self) -> int: ...
    @property
    def items(self) -> Sequence[PlanItem]: ...


@dataclass(frozen=True)
class OpeningRow:
    weekday: int
    is_closed: bool
    open_time: str | None = None
    close_time: str | None = None
    closes_next_day: bool = False


@dataclass(frozen=True)
class HoursInfo:
    label: str
    rows: Sequence[OpeningRow] = ()


@dataclass(frozen=True)
class ValidationContext:
    """What the rules know besides the plan. Travel times are on the items (step 9 stored them).

    ``places`` maps active place IDs to names; ``shortlist_ids`` is None outside generation, where
    no shortlist exists. ``pace_limits`` (items, active minutes) is read by IMP-309's DAY_TOO_LONG.
    """

    start_date: date
    end_date: date
    places: Mapping[str, str] = field(default_factory=dict)
    must_visit_ids: frozenset[str] = frozenset()
    shortlist_ids: frozenset[str] | None = None
    pace_limits: tuple[int, int] | None = None
    pace: str | None = None
    timezone: str = "UTC"
    day_dates: Mapping[int, date] = field(default_factory=dict)
    opening_hours: Mapping[str, HoursInfo] | None = None
    cost_inputs: engine.CostInputs | None = None
    # BF-04 substitutions only; known SAMPLE prices labelled estimate are not category estimates.
    category_estimate_refs: frozenset[str] = frozenset()

    @property
    def num_days(self) -> int:
        return (self.end_date - self.start_date).days + 1

    @property
    def active_place_ids(self) -> frozenset[str]:
        return frozenset(self.places)


Rule = Callable[[Sequence[PlanDay], ValidationContext], list[Finding]]


def minutes(hhmm: str) -> int:
    hours, mins = hhmm.split(":")
    return int(hours) * 60 + int(mins)


def item_ref(day_number: int, position: int) -> str:
    return f"d{day_number}-i{position}"


def finding(
    code: FindingCode,
    message: str,
    *,
    day_number: int | None = None,
    item_ref: str | None = None,
    place_id: str | None = None,
    suggested_fix: str | None = None,
) -> Finding:
    return Finding.model_validate(
        {
            "code": code,
            "severity": CATALOGUE[code],
            "message": message,
            "day_number": day_number,
            "item_ref": item_ref,
            "place_id": place_id,
            "suggested_fix": suggested_fix,
        }
    )


def _gaps(plan: Sequence[PlanDay]) -> list[tuple[int, int, PlanItem, int]]:
    """(day, position of the later item, the later item, gap in minutes) for consecutive items of
    one day; items of different days are never paired (TC-306)."""
    pairs = []
    for day in plan:
        for position in range(2, len(day.items) + 1):
            previous, current = day.items[position - 2], day.items[position - 1]
            gap = minutes(current.start_time) - minutes(previous.start_time) - previous.duration_min
            pairs.append((day.day_number, position, current, gap))
    return pairs


def overlap(plan: Sequence[PlanDay], ctx: ValidationContext) -> list[Finding]:
    """§9.3.4: the next item starts before the previous one ends; back-to-back (gap 0) is fine."""
    return [
        finding(
            "OVERLAP",
            f"{item_ref(day, position)} starts {-gap} min before {item_ref(day, position - 1)} "
            "ends.",
            day_number=day,
            item_ref=item_ref(day, position),
            suggested_fix="Move one of the two items, shorten the earlier visit or start later.",
        )
        for day, position, _, gap in _gaps(plan)
        if gap < 0
    ]


def transfer_too_short(plan: Sequence[PlanDay], ctx: ValidationContext) -> list[Finding]:
    """§9.3.5: 0 <= gap < travel + buffer (5 after routing_api, 15 after fallback_estimate)."""
    findings = []
    for day, position, item, gap in _gaps(plan):
        if gap < 0 or item.travel_from_prev_min is None or item.travel_source is None:
            continue
        need = item.travel_from_prev_min + BUFFER_MIN[item.travel_source]
        if gap < need:
            estimate = " (estimate)" if item.travel_source == "fallback_estimate" else ""
            findings.append(
                finding(
                    "TRANSFER_TOO_SHORT",
                    f"{gap} min to reach {item_ref(day, position)}, but the transfer needs "
                    f"{item.travel_from_prev_min} min{estimate} plus a "
                    f"{BUFFER_MIN[item.travel_source]}-min buffer: {need - gap} min short.",
                    day_number=day,
                    item_ref=item_ref(day, position),
                    suggested_fix=f"Start {item_ref(day, position)} {need - gap} min later.",
                )
            )
    return findings


def must_visit_missing(plan: Sequence[PlanDay], ctx: ValidationContext) -> list[Finding]:
    """§9.3.7: a must-visit place with no item; referenced by place_id, item_ref null (IMD-42)."""
    planned = {item.place_id for day in plan for item in day.items}
    return [
        finding(
            "MUST_VISIT_MISSING",
            f"Must-visit place {ctx.places.get(place_id, place_id)} is not in the plan.",
            place_id=place_id,
            suggested_fix="Add it to a day with room, or remove it from the must-visit list.",
        )
        for place_id in sorted(ctx.must_visit_ids - planned)
    ]


def unknown_place(plan: Sequence[PlanDay], ctx: ValidationContext) -> list[Finding]:
    """§9.3.6: not an active place of the destination or, in generation, not in the shortlist."""
    return [
        finding(
            "UNKNOWN_PLACE",
            f"{item_ref(day.day_number, position)} is not an active place of this trip's "
            "shortlist or destination.",
            day_number=day.day_number,
            item_ref=item_ref(day.day_number, position),
            suggested_fix="Remove this item or replace it with an active place.",
        )
        for day in plan
        for position, item in enumerate(day.items, start=1)
        if item.place_id not in ctx.places
        or (ctx.shortlist_ids is not None and item.place_id not in ctx.shortlist_ids)
    ]


def outside_trip_dates(plan: Sequence[PlanDay], ctx: ValidationContext) -> list[Finding]:
    """§9.3.6: a day outside 1..num_days; days 1 and num_days (start and end dates) are inside."""
    return [
        finding(
            "OUTSIDE_TRIP_DATES",
            f"{item_ref(day.day_number, position)} is on day {day.day_number}, outside the "
            f"trip's {ctx.num_days} days.",
            # PlanFinding.day_number holds 1..14 only; the message and item_ref keep the day
            day_number=day.day_number if 1 <= day.day_number <= MAX_TRIP_DAYS else None,
            item_ref=item_ref(day.day_number, position),
            suggested_fix="Move this item to a day of the trip or change the trip dates.",
        )
        for day in plan
        if not 1 <= day.day_number <= ctx.num_days
        for position in range(1, len(day.items) + 1)
    ]


def opening_hours(plan: Sequence[PlanDay], ctx: ValidationContext) -> list[Finding]:
    """§9.3.6: six decisions on destination-local wall times, including overnight intervals."""
    if ctx.opening_hours is None:
        return []  # Pure callers may supply schedule-only context; services load hours.
    found = []
    for day in plan:
        plan_date = ctx.day_dates.get(
            day.day_number, ctx.start_date + timedelta(days=day.day_number - 1)
        )
        for position, item in enumerate(day.items, 1):
            info = ctx.opening_hours.get(item.place_id, HoursInfo("unavailable"))
            local = datetime.combine(
                plan_date, time.fromisoformat(item.start_time), ZoneInfo(ctx.timezone)
            )
            weekday = local.isoweekday()
            start = local.hour * 60 + local.minute
            end = start + item.duration_min
            code: FindingCode | None = None
            if info.label == "unavailable" or not info.rows:
                code = "HOURS_UNVERIFIED"
            else:

                def covers(
                    row: OpeningRow, offset: int = 0, visit_start: int = start, visit_end: int = end
                ) -> bool:
                    if row.is_closed or row.open_time is None or row.close_time is None:
                        return False
                    opened = minutes(row.open_time) + offset
                    closed = minutes(row.close_time) + offset + (1440 if row.closes_next_day else 0)
                    return opened <= visit_start and visit_end <= closed

                previous = (weekday - 2) % 7 + 1
                if any(
                    row.weekday == previous and row.closes_next_day and covers(row, -1440)
                    for row in info.rows
                ):
                    continue
                today = [row for row in info.rows if row.weekday == weekday]
                if not today:
                    code = "HOURS_UNVERIFIED"
                elif all(row.is_closed for row in today):
                    code = "CLOSED_ON_DAY"
                elif not any(covers(row) for row in today):
                    code = "OUTSIDE_HOURS"
            if code is not None:
                message = {
                    "HOURS_UNVERIFIED": "Opening hours are unavailable for this visit; check before going.",
                    "CLOSED_ON_DAY": "This place is closed on the planned day.",
                    "OUTSIDE_HOURS": "This visit falls outside the place's opening hours.",
                }[code]
                result = finding(
                    code,
                    message,
                    day_number=day.day_number,
                    item_ref=item_ref(day.day_number, position),
                )
                if code == "OUTSIDE_HOURS" and info.label == "estimate":
                    result = result.model_copy(update={"severity": "warning"})
                found.append(result)
    return found


def day_length(plan: Sequence[PlanDay], ctx: ValidationContext) -> list[Finding]:
    """Active minutes include visits and transfers; the pace accessor owns every threshold."""
    if ctx.pace is not None:
        preset = pace_limits(ctx.pace)
        max_items, max_minutes = preset.max_items_per_day, preset.max_active_minutes_per_day
    elif ctx.pace_limits is not None:
        max_items, max_minutes = ctx.pace_limits
    else:
        return []
    return [
        finding(
            "DAY_TOO_LONG",
            f"Day {day.day_number} has {len(day.items)} items and {active} active min; "
            f"the pace limits are {max_items} items and {max_minutes} active min.",
            day_number=day.day_number,
        )
        for day in plan
        if (
            active := sum(
                item.duration_min + (item.travel_from_prev_min or 0) for item in day.items
            )
        )
        > max_minutes
        or len(day.items) > max_items
    ]


def budget_conflicts(plan: Sequence[PlanDay], ctx: ValidationContext) -> list[Finding]:
    """BF-11 and BF-04: use the pure engine's totals and alerts, never sum prices here."""
    if ctx.cost_inputs is None:
        return []
    costs = []
    estimates = []
    incomplete_count = 0
    for day in plan:
        for position, item in enumerate(day.items, 1):
            ref = item_ref(day.day_number, position)
            low, high = getattr(item, "cost_min", None), getattr(item, "cost_max", None)
            label = getattr(item, "cost_label", None) or "unavailable"
            costs.append(
                engine.CostedItem(
                    uuid5(NAMESPACE_URL, ref),
                    day.day_number,
                    "other",
                    None if low is None else engine.to_minor(low),
                    None if high is None else engine.to_minor(high),
                    label,
                )
            )
            category_estimate = label == "estimate" and ref in ctx.category_estimate_refs
            if label == "unavailable" or low is None or category_estimate:
                incomplete_count += 1
            if category_estimate:
                estimates.append(
                    finding(
                        "ESTIMATE_USED",
                        "This item uses a category price estimate.",
                        day_number=day.day_number,
                        item_ref=ref,
                    )
                )
    summary = engine.compute_costs(costs, ctx.cost_inputs)
    found = [
        finding(alert.code, alert.message)
        for alert in summary.alerts
        if alert.code != "COST_INCOMPLETE"
    ]
    if incomplete_count:
        found.append(
            finding(
                "COST_INCOMPLETE",
                f"{incomplete_count} planned items have unavailable or estimated prices; the total is incomplete.",
            )
        )
    return [*found, *estimates]


# The order of the §8.12 table.
RULES: Final[tuple[Rule, ...]] = (
    overlap,
    transfer_too_short,
    opening_hours,
    day_length,
    budget_conflicts,
    must_visit_missing,
    unknown_place,
    outside_trip_dates,
)
