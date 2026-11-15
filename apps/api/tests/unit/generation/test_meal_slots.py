"""Meal slots (FR-083; IMP-606: TC-243, TC-244, TC-372).

The meal windows and the lunch rule are code constants (IMD-29) in ``generation/presets.py``.
"""

import pytest

from app.generation import presets
from app.generation.presets import LUNCH_MIN_ACTIVE_MIN, MEAL_WINDOWS, meal_slots


def test_meal_windows_are_the_card_constants() -> None:
    assert MEAL_WINDOWS == {
        "breakfast": ("07:30", "09:30"),
        "lunch": ("12:00", "14:00"),
        "dinner": ("18:30", "20:30"),
    }
    assert LUNCH_MIN_ACTIVE_MIN == 360


@pytest.mark.parametrize(
    ("pace", "expected"), [("relaxed", []), ("balanced", ["lunch"]), ("busy", ["lunch"])]
)
def test_meal_a_day_longer_than_six_active_hours_gets_lunch(pace: str, expected: list[str]) -> None:
    long_day = presets.pace_limits(pace).max_active_minutes_per_day > LUNCH_MIN_ACTIVE_MIN
    assert meal_slots(pace) == expected
    assert bool(expected) is long_day


@pytest.mark.parametrize("pace", ["relaxed", "balanced", "busy"])
def test_meal_tc_372_switch_off_plans_no_meal_slots(pace: str) -> None:
    assert meal_slots(pace, enabled=False) == []
