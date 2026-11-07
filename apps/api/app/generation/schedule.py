"""Schedule recalculation, step 9 of §8.2 (§9.3.3, FR-033, IMP-308).

Every saved time comes from here: each day starts at DAY_START, a visit lasts the place's stored
``typical_duration_min``, and the next start is the previous end plus the travel time and its
buffer (§9.3.5). The model's order stays; its start times and durations are replaced. Only the
number of differences is logged.
"""

import logging
from collections.abc import Mapping, Sequence
from typing import Final, Protocol

from app.generation.request_builder import DAY_START
from app.itinerary.schemas import PlannedDay, PlannedItem
from app.routing.estimate import TravelEstimate, TravelMode, buffer_minutes
from app.routing.service import RoutablePlace
from app.schemas.ai import GroundedItemOutput, ItineraryDayOutput

logger = logging.getLogger(__name__)

LAST_MINUTE: Final = 24 * 60 - 1


class SchedulablePlace(RoutablePlace, Protocol):
    @property
    def typical_duration_min(self) -> int: ...


class Routing(Protocol):
    async def travel(
        self, origin: RoutablePlace, target: RoutablePlace, mode: TravelMode | str
    ) -> TravelEstimate: ...


def _minutes(hhmm: str) -> int:
    hours, minutes = hhmm.split(":")
    return int(hours) * 60 + int(minutes)


def _hhmm(minutes: int) -> str:
    # shortcut: a day that runs past midnight stops at 23:59, as `time` cannot hold more; the
    # DAY_TOO_LONG and OVERLAP findings of IMP-404 report such a day.
    clock = min(minutes, LAST_MINUTE)
    return f"{clock // 60:02d}:{clock % 60:02d}"


async def recalculate(
    days: Sequence[ItineraryDayOutput],
    places: Mapping[str, SchedulablePlace],
    routing: Routing,
    pace: str,  # in the card's signature; no rule here reads it (PD-IMP-308-2)
    *,
    mode: TravelMode | str,
) -> list[PlannedDay]:
    """The days in order with their items at the calculated times; ``places`` is keyed by ID."""
    planned = []
    differences = 0
    for day in sorted(days, key=lambda d: d.day_number):
        clock = _minutes(DAY_START)
        previous: SchedulablePlace | None = None
        items = []
        for item in day.items:
            place = places[item.place_id]
            travel = None
            if previous is not None:
                travel = await routing.travel(previous, place, mode)
                clock += travel.minutes + buffer_minutes(travel.travel_source)
            start, duration = _hhmm(clock), place.typical_duration_min
            differences += (start, duration) != (item.start_time, item.duration_min)
            items.append(
                PlannedItem(
                    place_id=item.place_id,
                    slot_type=item.slot_type,
                    start_time=start,
                    duration_min=duration,
                    note=item.note,
                    travel_from_prev_min=travel.minutes if travel else None,
                    travel_from_prev_m=travel.distance_m if travel else None,
                    travel_mode=travel.mode.value if travel else None,
                    travel_source=travel.travel_source if travel else None,
                    source_chunk_ids=(
                        item.source_ids if isinstance(item, GroundedItemOutput) else ()
                    ),
                )
            )
            clock += duration
            previous = place
        planned.append(PlannedDay(day.day_number, day.theme, items))
    logger.info("schedule replaced the model's times on %d items", differences)
    return planned
