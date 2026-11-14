"""Deterministic repair, the first half of step 10 (§8.13, FR-057; IMP-502).

Pure: no I/O. ``repair`` takes an answer that step 8 has checked (unknown places, items outside the
trip and repeated places are already dropped), the findings of its recalculated plan and the
travel step 9 found, and returns the answer with the cheapest fixes and how many it made:

1. forward shift: each unlocked item starts at max(own start, previous end + travel + buffer);
2. for each error finding, codes in the order of ``FIX_ORDER``, the first fix of ``FIXES`` that
   works: move the item to another trip day with room, swap it with the next item, or drop the
   lowest-ranked unlocked item that is not a must-visit place;
3. each missing must-visit place goes at the end of the trip day with the most room.

Never: a locked item moves or goes, a must-visit place goes, a price, hour or travel time
changes, or a budget finding is acted on. One pass, so it always ends; the pipeline validates the
result again, and step 9 recalculates every time it holds.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final, Literal

from app.routing.estimate import BUFFER_MIN
from app.schemas.ai import FindingCode, GenerationRequest, ItineraryOutput, ShortlistPlace
from app.validation.rules import Finding, PlanDay, minutes

LAST_START: Final = 23 * 60 + 59
FIX_ORDER: Final[tuple[FindingCode, ...]] = (
    "UNKNOWN_PLACE",
    "OUTSIDE_TRIP_DATES",
    "CLOSED_ON_DAY",
    "OUTSIDE_HOURS",
    "OVERLAP",
)

Fix = Literal["move", "swap", "drop"]
# The cheapest fix first (§8.13). OVERLAP after the shift remains only against a locked item.
FIXES: Final[Mapping[FindingCode, tuple[Fix, ...]]] = {
    "UNKNOWN_PLACE": ("drop",),
    "OUTSIDE_TRIP_DATES": ("move", "drop"),
    "CLOSED_ON_DAY": ("move", "drop"),
    "OUTSIDE_HOURS": ("swap", "move", "drop"),
    "OVERLAP": ("move", "drop"),
}

Item = dict[str, Any]
Days = dict[int, list[Item]]


@dataclass(frozen=True)
class RepairScope:
    """What repair may use besides the answer. ``shortlist`` is in rank order, best first."""

    day_numbers: Sequence[int]  # the days the plan may use: every trip day, or the one of scope day
    max_items_per_day: int
    max_active_minutes_per_day: int
    day_start: str
    shortlist: Sequence[ShortlistPlace]
    must_visit_ids: Sequence[str] = ()
    locked: frozenset[tuple[int, str]] = frozenset()  # (day_number, place_id)


@dataclass(frozen=True)
class Repaired[O: ItineraryOutput]:
    output: O | None  # None when every item was dropped
    fixes: int


def scope_for(request: GenerationRequest) -> RepairScope:
    day_numbers = range(1, request.trip.num_days + 1)
    if request.scope.day_number is not None:
        day_numbers = range(request.scope.day_number, request.scope.day_number + 1)
    return RepairScope(
        day_numbers=day_numbers,
        max_items_per_day=request.limits.max_items_per_day,
        max_active_minutes_per_day=request.limits.max_active_minutes_per_day,
        day_start=request.limits.day_start,
        shortlist=request.shortlist,
        must_visit_ids=[str(place_id) for place_id in request.must_visit_place_ids],
        locked=frozenset((item.day_number, str(item.place_id)) for item in request.locked_items),
    )


def travel_gaps(plan: Sequence[PlanDay]) -> dict[str, int]:
    """Travel plus buffer before each item of a recalculated plan, by place ID (unique there)."""
    return {
        item.place_id: item.travel_from_prev_min + BUFFER_MIN[item.travel_source]
        for day in plan
        for item in day.items
        if item.travel_from_prev_min is not None and item.travel_source is not None
    }


def retimed[O: ItineraryOutput](output: O, plan: Sequence[PlanDay]) -> O:
    """The answer with step 9's times and durations, so a plan step 9 already put right needs no
    fix: the model's own times are replaced by step 9 and are never repaired or counted."""
    times = {
        item.place_id: (item.start_time, item.duration_min) for day in plan for item in day.items
    }
    data = output.model_dump()
    for day in data["days"]:
        for item in day["items"]:
            item["start_time"], item["duration_min"] = times.get(
                item["place_id"], (item["start_time"], item["duration_min"])
            )
    return type(output).model_validate(data)


def _hhmm(clock: int) -> str:
    clock = min(clock, LAST_START)
    return f"{clock // 60:02d}:{clock % 60:02d}"


def _end(item: Item) -> int:
    return minutes(item["start_time"]) + int(item["duration_min"])


class _Repair:
    def __init__(self, days: Days, scope: RepairScope) -> None:
        self.days = days
        self.scope = scope
        self.places = {str(place.place_id): place for place in scope.shortlist}
        self.rank = {place_id: rank for rank, place_id in enumerate(self.places)}
        self.must_visit = frozenset(scope.must_visit_ids)

    def locked(self, day: int, place_id: str) -> bool:
        return (day, place_id) in self.scope.locked

    def find(self, day: int, place_id: str) -> int | None:
        items = self.days.get(day, [])
        return next((i for i, item in enumerate(items) if item["place_id"] == place_id), None)

    def shift(self, day: int, gaps: Mapping[str, int]) -> int:
        shifted, clock = 0, None
        for item in self.days[day]:
            start = minutes(item["start_time"])
            if clock is not None and not self.locked(day, item["place_id"]):
                earliest = clock + gaps.get(item["place_id"], 0)
                if start < earliest:
                    item["start_time"] = _hhmm(earliest)
                    start, shifted = minutes(item["start_time"]), shifted + 1
            clock = start + int(item["duration_min"])
        return shifted

    def room_day(self, duration: int, exclude: int | None = None) -> int | None:
        """The trip day with the most room for ``duration`` minutes: fewest items, then minutes."""
        rooms = []
        for day in self.scope.day_numbers:
            items = self.days.get(day, [])
            active = sum(int(item["duration_min"]) for item in items)
            if (
                day != exclude
                and len(items) < self.scope.max_items_per_day
                and active + duration <= self.scope.max_active_minutes_per_day
            ):
                rooms.append((len(items), active, day))
        return min(rooms)[2] if rooms else None

    def append(self, day: int, item: Item) -> None:
        items = self.days.setdefault(day, [])
        start = _end(items[-1]) if items else minutes(self.scope.day_start)
        items.append({**item, "start_time": _hhmm(start)})

    def move(self, day: int, place_id: str) -> bool:
        index = self.find(day, place_id)
        if index is None or self.locked(day, place_id):
            return False
        target = self.room_day(int(self.days[day][index]["duration_min"]), exclude=day)
        if target is None:
            return False
        self.append(target, self.days[day].pop(index))
        return True

    def swap(self, day: int, place_id: str) -> bool:
        index = self.find(day, place_id)
        items = self.days.get(day, [])
        if index is None or index + 1 >= len(items):
            return False
        first, second = items[index], items[index + 1]
        if self.locked(day, first["place_id"]) or self.locked(day, second["place_id"]):
            return False
        second["start_time"] = first["start_time"]
        first["start_time"] = _hhmm(_end(second))
        items[index], items[index + 1] = second, first
        return True

    def drop(self, day: int, candidates: Sequence[str]) -> bool:
        droppable = [
            place_id
            for place_id in candidates
            if self.find(day, place_id) is not None
            and not self.locked(day, place_id)
            and place_id not in self.must_visit
        ]
        if not droppable:
            return False
        lowest = max(droppable, key=lambda place_id: self.rank.get(place_id, len(self.rank)))
        self.days[day] = [item for item in self.days[day] if item["place_id"] != lowest]
        return True

    def overlaps(self, day: int, later: str, earlier: str) -> bool:
        """Still an overlap after the shift (it remains only against a locked item)."""
        at, before = self.find(day, later), self.find(day, earlier)
        items = self.days.get(day, [])
        return (
            at is not None
            and before == at - 1
            and minutes(items[at]["start_time"]) < _end(items[before])
        )

    def fix(self, code: FindingCode, day: int, candidates: Sequence[str]) -> bool:
        """The first fix of ``FIXES[code]`` that works; moves and swaps take an unlocked item."""
        if code == "OVERLAP" and not self.overlaps(day, *candidates):
            return False
        movable = next((p for p in candidates if not self.locked(day, p)), None)
        for action in FIXES[code]:
            if action == "drop":
                done = self.drop(day, candidates)
            elif movable is None:
                done = False
            else:
                done = self.move(day, movable) if action == "move" else self.swap(day, movable)
            if done:
                return True
        return False

    def insert_must_visit(self) -> int:
        planned = {item["place_id"] for items in self.days.values() for item in items}
        inserted = 0
        for place_id in self.scope.must_visit_ids:
            place = self.places.get(place_id)
            if place_id in planned or place is None:
                continue
            day = self.room_day(place.typical_duration_min)
            if day is None:
                continue  # stays MUST_VISIT_MISSING, shown with its reason (FR-034)
            self.append(
                day,
                {
                    "place_id": place_id,
                    "duration_min": place.typical_duration_min,
                    "slot_type": "meal" if place.category == "food" else "activity",
                    "note": "",
                },
            )
            planned.add(place_id)
            inserted += 1
        return inserted


def _targets(days: Days, findings: Sequence[Finding]) -> list[tuple[FindingCode, int, list[str]]]:
    """(code, day, place IDs the fix may act on), resolved before anything moves."""
    targets = []
    for code in FIX_ORDER:
        for finding in findings:
            if finding.code != code or finding.severity != "error" or not finding.item_ref:
                continue
            day_text, position_text = finding.item_ref[1:].split("-i")
            day, position = int(day_text), int(position_text)
            items = days.get(day, [])
            if not 1 <= position <= len(items):
                continue
            candidates = [items[position - 1]["place_id"]]
            if code == "OVERLAP":
                if position == 1:
                    continue
                candidates.append(items[position - 2]["place_id"])
            targets.append((code, day, candidates))
    return targets


def repair[O: ItineraryOutput](
    output: O, findings: Sequence[Finding], scope: RepairScope, gaps: Mapping[str, int]
) -> Repaired[O]:
    data = output.model_dump()
    days: Days = {day["day_number"]: day["items"] for day in data["days"]}
    themes = {day["day_number"]: day["theme"] for day in data["days"]}
    work = _Repair(days, scope)

    fixes = sum(work.shift(day, gaps) for day in days)
    for code, day, candidates in _targets(days, findings):
        fixes += work.fix(code, day, candidates)
    fixes += work.insert_must_visit()

    data["days"] = [
        {"day_number": day, "theme": themes.get(day, ""), "items": items}
        for day, items in sorted(days.items())
        if items
    ]
    if not data["days"]:
        return Repaired(None, fixes)
    return Repaired(type(output).model_validate(data), fixes)
