"""Pace boundaries from the common preset accessor (IMP-501, TC-182/183/303)."""

from datetime import date

import pytest

from app.generation.presets import pace_limits
from app.itinerary.schemas import PlannedDay, PlannedItem
from app.validation.rules import ValidationContext, day_length

PLACE = "00000000-0000-4000-8000-000000000001"


@pytest.mark.parametrize("pace", ["relaxed", "balanced", "busy"])
def test_day_length_tc_303_exact_and_one_above(pace: str) -> None:
    limits = pace_limits(pace)
    ctx = ValidationContext(date(2026, 12, 7), date(2026, 12, 7), pace=pace)

    def plan(duration: int, travel: int = 0, count: int = 1):
        return [
            PlannedDay(
                1,
                "",
                [
                    PlannedItem(
                        PLACE,
                        "activity",
                        "09:00",
                        duration if i == 0 else 0,
                        "",
                        travel_from_prev_min=travel if i == 0 else 0,
                    )
                    for i in range(count)
                ],
            )
        ]

    assert day_length(plan(limits.max_active_minutes_per_day), ctx) == []
    found = day_length(plan(limits.max_active_minutes_per_day, travel=1), ctx)
    assert [(f.code, f.severity) for f in found] == [("DAY_TOO_LONG", "warning")]
    assert str(limits.max_active_minutes_per_day + 1) in found[0].message
    assert day_length(plan(15, count=limits.max_items_per_day), ctx) == []
    assert day_length(plan(15, count=limits.max_items_per_day + 1), ctx)[0].code == "DAY_TOO_LONG"
