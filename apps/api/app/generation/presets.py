"""Planning presets that are code, not environment settings (IMD-29; §8.9, FR-029; IMP-503).

``PACE_PRESETS`` holds the per-day item and active-minute limits of each pace (Provisional:
relaxed 3 / 300, balanced 5 / 480, busy 7 / 600). ``pace_limits`` is the one accessor that
grouping, the request builder and, through the request's limits, the DAY_TOO_LONG rule read.
The numbers are taken from pm-2's ``PACE_LIMITS`` (IMP-315), which ranking already reads, so they
are written once (PD-IMP-503-1).
"""

from collections.abc import Mapping
from typing import Final

from app.trips.preference_mapping import PACE_LIMITS, Pace, PaceLimits

PACE_PRESETS: Final[Mapping[Pace, PaceLimits]] = {
    pace: PaceLimits(max_items_per_day=items, max_active_minutes_per_day=minutes)
    for pace, (items, minutes) in PACE_LIMITS.items()
}


def pace_limits(pace: str) -> PaceLimits:
    """The limits of ``pace`` (relaxed, balanced or busy); ValueError for any other value."""
    return PACE_PRESETS[Pace(pace)]


# IMP-606: meal windows as (start, end) in the destination's time (Provisional). Only lunch is
# planned in the MVP: every full day gets a lunch slot, relaxed pace included (IMD-189).
MEAL_WINDOWS: Final[Mapping[str, tuple[str, str]]] = {
    "breakfast": ("07:30", "09:30"),
    "lunch": ("12:00", "14:00"),
    "dinner": ("18:30", "20:30"),
}


def meal_slots(pace: str, *, enabled: bool = True) -> list[str]:
    """The meal slots of a day at ``pace``: lunch at every pace (IMD-189); none when the
    ``meal_slots`` switch is off (IMD-11). ValueError for an unknown pace."""
    pace_limits(pace)
    return ["lunch"] if enabled else []
