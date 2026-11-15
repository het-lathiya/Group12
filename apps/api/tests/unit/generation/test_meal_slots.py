"""Meal slots (FR-083; IMP-606: TC-243, TC-244, TC-372).

The meal windows and the lunch rule are code constants (IMD-29) in ``generation/presets.py``.
"""

import uuid

import pytest
from fixtures.ai import FORT, SAMPLE_OUTPUT, THALI, sample_request, sample_request_data

from app.generation import presets
from app.generation.fallback_planner import (
    LUNCH_FROM,
    LUNCH_TO,
    NO_FOOD_NOTE,
    THEME_MAX,
    _minutes,
    plan_rule_based,
)
from app.generation.presets import MEAL_WINDOWS, meal_slots
from app.schemas.ai import GenerationRequest, ItineraryOutput
from app.validation.output_check import MEAL_NOT_FOOD_MESSAGE, check_output, without_meals


def test_meal_windows_are_the_card_constants() -> None:
    assert MEAL_WINDOWS == {
        "breakfast": ("07:30", "09:30"),
        "lunch": ("12:00", "14:00"),
        "dinner": ("18:30", "20:30"),
    }


@pytest.mark.parametrize("pace", ["relaxed", "balanced", "busy"])
def test_meal_imd_189_every_pace_gets_a_lunch_slot(pace: str) -> None:
    assert meal_slots(pace) == ["lunch"]


def test_meal_slots_reject_an_unknown_pace() -> None:
    with pytest.raises(ValueError, match="frantic"):
        meal_slots("frantic")


@pytest.mark.parametrize("pace", ["relaxed", "balanced", "busy"])
def test_meal_tc_372_switch_off_plans_no_meal_slots(pace: str) -> None:
    assert meal_slots(pace, enabled=False) == []


# ---------- Meal slots in the request builder and the fallback planner (meal-builder part) ----------


def _request(meal_slots: list[str], *, food: bool = True) -> GenerationRequest:
    """One full day: three long visits around a food place, all within a short walk."""
    data = sample_request_data()
    data["trip"] |= {"end_date": "2027-01-12", "num_days": 1}
    data["must_visit_place_ids"] = []
    data["day_hints"] = []
    shortlist = [
        data["shortlist"][0] | {"place_id": str(uuid.UUID(int=n)), "name": f"Sight {n}"}
        for n in range(1, 4)
    ]
    if food:
        shortlist.append(data["shortlist"][2])  # Example Thali House, food, 60 minutes
    data["shortlist"] = shortlist
    data["limits"]["meal_slots"] = meal_slots
    return GenerationRequest.model_validate(data)


def test_meal_tc_243_fallback_fills_the_lunch_slot_from_a_food_place() -> None:
    output = plan_rule_based(_request(["lunch"]))
    (day,) = output.days
    meals = [item for item in day.items if item.slot_type == "meal"]
    assert [item.place_id for item in meals] == [THALI]
    assert LUNCH_FROM <= _minutes(meals[0].start_time) <= LUNCH_TO
    assert NO_FOOD_NOTE not in day.theme


def test_meal_imd_189_a_relaxed_full_day_gets_lunch_from_a_food_place() -> None:
    request = _request(meal_slots("relaxed"))
    relaxed = presets.pace_limits("relaxed")
    for place in request.shortlist[:3]:
        place.typical_duration_min = 90  # two visits reach the lunch window within 300 minutes
    request.limits.max_items_per_day = relaxed.max_items_per_day
    request.limits.max_active_minutes_per_day = relaxed.max_active_minutes_per_day
    (day,) = plan_rule_based(request).days
    meals = [item for item in day.items if item.slot_type == "meal"]
    assert [item.place_id for item in meals] == [THALI]
    assert LUNCH_FROM <= _minutes(meals[0].start_time) <= LUNCH_TO
    assert len(day.items) <= relaxed.max_items_per_day


def test_meal_tc_243_no_food_place_leaves_the_slot_empty_with_a_day_note() -> None:
    output = plan_rule_based(_request(["lunch"], food=False))
    (day,) = output.days
    assert all(item.slot_type == "activity" for item in day.items)
    assert day.theme.endswith(f" · {NO_FOOD_NOTE}")
    assert len(day.theme) <= THEME_MAX
    assert all(item.note == "" for item in day.items)  # a day-level message, not an item note


def test_meal_tc_372_switch_off_inserts_no_meal_and_no_note() -> None:
    output = plan_rule_based(_request([]))
    (day,) = output.days
    assert all(item.slot_type == "activity" for item in day.items)
    assert NO_FOOD_NOTE not in day.theme


def test_meal_item_on_a_place_that_is_not_food_is_an_invalid_reference() -> None:
    request = sample_request()
    answer = ItineraryOutput.model_validate(
        {
            "days": [
                {
                    "day_number": 1,
                    "theme": "Day 1",
                    "items": [
                        {
                            "place_id": FORT,
                            "start_time": "09:00",
                            "duration_min": 120,
                            "slot_type": "meal",
                            "note": "",
                        },
                        {
                            "place_id": THALI,
                            "start_time": "12:30",
                            "duration_min": 60,
                            "slot_type": "meal",
                            "note": "",
                        },
                    ],
                }
            ],
            "summary": "s",
            "assumptions": [],
        }
    )
    food = {str(p.place_id) for p in request.shortlist if p.category == "food"}
    checked = check_output(answer, set(request.shortlist_ids()), 2, food_ids=food)
    assert [item.place_id for item in checked.output.days[0].items] == [THALI]
    assert [(f.code, f.message) for f in checked.findings] == [
        ("UNKNOWN_PLACE", MEAL_NOT_FOOD_MESSAGE)
    ]
    assert checked.invalid_ids == 1
    # Without food_ids (the fallback planner's own plan) the check is not applied.
    assert len(check_output(answer, set(request.shortlist_ids()), 2).output.days[0].items) == 2


def test_meal_tc_372_without_a_meal_slot_a_meal_item_is_an_ordinary_activity() -> None:
    answer = ItineraryOutput.model_validate(SAMPLE_OUTPUT)
    assert any(item.slot_type == "meal" for day in answer.days for item in day.items)
    plain = without_meals(answer)
    assert {item.slot_type for day in plain.days for item in day.items} == {"activity"}
    assert [i.place_id for d in plain.days for i in d.items] == [
        i.place_id for d in answer.days for i in d.items
    ]
