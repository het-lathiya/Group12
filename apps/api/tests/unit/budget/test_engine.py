"""The budget engine (§9.3.1 BF-01 to BF-12; FR-033, FR-071; IMP-308) and rulings B1 to B6.

TC-221, TC-296 and TC-297 follow their §13.3 row. TC-222, TC-295, TC-299, TC-314 and TC-316 have no
row there, so they follow the card's acceptance wording: rounding (TC-295), remainder split
(TC-296), group pricing (TC-297), missing prices (TC-299), category estimate (TC-314), zero price
(TC-316).
"""

from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.budget import engine
from app.budget.engine import CostedItem, CostInputs
from app.budget.schemas import BudgetStatus


def place(price_min: str | None, price_max: str | None = None, **overrides: Any) -> Any:
    values = {
        "price_min": None if price_min is None else Decimal(price_min),
        "price_max": None if price_max is None else Decimal(price_max),
        "price_currency": "GBP",
        "price_label": "curated",
        "tags": [],
    }
    return SimpleNamespace(**(values | overrides))


def cost(given: Any, adults: int = 2, children: int = 1, currency: str = "GBP") -> engine.ItemCost:
    return engine.item_cost(given, adults=adults, children=children, currency=currency)


def item(
    lo: int | None, hi: int | None = None, day: int = 1, category: str = "sight", label: str = ""
) -> CostedItem:
    high = lo if hi is None else hi
    return CostedItem(uuid4(), day, category, lo, high, label or "curated")


def inputs(**overrides: Any) -> CostInputs:
    values: dict[str, Any] = {
        "num_days": 3,
        "adults": 2,
        "children": 0,
        "currency": "GBP",
        "budget": None,
        "transport_per_day": None,
        "stay_per_night": None,
        "contingency_pct": 10,
    }
    return CostInputs(**(values | overrides))


def status_at(total: int, budget: int | None) -> engine.CostSummary:
    return engine.compute_costs([item(total)], inputs(budget=budget, contingency_pct=0))


# Money handling


def test_tc_295_amounts_convert_exactly_between_decimals_and_minor_units() -> None:
    assert engine.to_minor(Decimal("1234.56")) == 123456
    assert engine.from_minor(123456) == Decimal("1234.56")
    assert f"{engine.from_minor(5)}" == "0.05"


def test_tc_295_a_child_half_line_rounds_half_up_once() -> None:
    summary = cost(place("3.33", tags=["child_half"]), adults=2, children=1)
    assert (summary.lo, summary.hi) == (833, 833)  # 666 + round(166.5)


def test_tc_295_rounding_is_on_the_line_and_not_per_child() -> None:
    # Three children at 0.5 x 3.33 = 499.5, rounded once to 500; per child it would be 501.
    assert cost(place("3.33", tags=["child_half"]), adults=0, children=3).lo == 500


# BF-01 to BF-03


def test_tc_221_per_person_cost_counts_adults_and_children() -> None:
    summary = cost(place("10.00", "15.00"), adults=2, children=2)
    assert (summary.lo, summary.hi, summary.label) == (4000, 6000, "curated")


def test_child_free_and_child_half_factors() -> None:
    assert cost(place("10.00", tags=["child_free"]), adults=2, children=2).lo == 2000
    assert cost(place("10.00", tags=["child_half"]), adults=2, children=2).lo == 3000


def test_tc_297_a_group_price_is_counted_once() -> None:
    summary = cost(place("50.00", "60.00", tags=["price_per_group"]), adults=3, children=1)
    assert (summary.lo, summary.hi) == (5000, 6000)


def test_tc_221_tc_296_tc_297_known_costs_for_four_travellers_to_the_cent() -> None:
    each = cost(place("10.00", "15.00"), adults=4, children=0)
    group = cost(place("50.00", tags=["price_per_group"]), adults=4, children=0)
    summary = engine.compute_costs(
        [item(each.lo, each.hi), item(group.lo, group.hi)],
        inputs(adults=4, transport_per_day=1000, stay_per_night=3000),
    )
    assert (summary.estimate_lo, summary.estimate_hi) == (4000 + 5000 + 9000, 6000 + 5000 + 9000)
    assert summary.contingency == 2000
    assert summary.planning_total == 22000
    assert summary.largest_share == 5500


def test_the_same_place_on_two_days_counts_twice() -> None:
    summary = engine.compute_costs([item(1000, day=1), item(1000, day=2)], inputs())
    assert summary.estimate_hi == 2000


def test_tc_296_a_total_not_divisible_by_three_gives_the_remainder_to_the_first_shares() -> None:
    assert engine.split(1000, 3) == [334, 333, 333]
    summary = engine.compute_costs([item(1000)], inputs(adults=2, children=1, contingency_pct=0))
    assert (summary.travellers, summary.largest_share) == (3, 334)


# BF-04, rulings B3 and B6


def test_ruling_b3_a_null_price_max_uses_the_low_price() -> None:
    summary = cost(place("10.00"), adults=1, children=0)
    assert (summary.lo, summary.hi) == (1000, 1000)


def test_tc_316_zero_is_a_real_price() -> None:
    assert cost(place("0.00", "0.00")) == engine.ItemCost(0, 0, "curated")
    summary = engine.compute_costs([item(0)], inputs())
    assert (summary.complete, summary.incomplete_items) == (True, [])


def test_tc_299_a_missing_price_or_an_unavailable_label_is_unavailable() -> None:
    assert cost(place(None)) == engine.ITEM_UNAVAILABLE
    assert cost(place("5.00", price_label="unavailable")) == engine.ITEM_UNAVAILABLE


def test_a_price_in_another_currency_is_unavailable_and_never_converted() -> None:
    assert cost(place("5.00", price_currency="EUR")) == engine.ITEM_UNAVAILABLE


def test_tc_222_ruling_b6_a_missing_cost_counts_0_and_flags_the_trip_incomplete() -> None:
    missing = CostedItem(uuid4(), 1, "sight", None, None, "unavailable")
    summary = engine.compute_costs([item(1000), missing], inputs())
    assert summary.estimate_hi == 1000
    assert summary.incomplete_items == [missing.item_id]
    assert summary.complete is False
    [alert] = summary.alerts
    assert (alert.code, alert.severity) == ("COST_INCOMPLETE", "warning")
    assert alert.message.startswith("1 planned items")


def test_tc_314_ruling_b6_with_no_estimate_data_no_estimate_used_is_emitted() -> None:
    missing = CostedItem(uuid4(), 1, "sight", None, None, "unavailable")
    summary = engine.compute_costs([missing], inputs())
    assert [alert.code for alert in summary.alerts] == ["COST_INCOMPLETE"]
    assert summary.by_category[0].label == "unavailable"


# BF-05 to BF-10


def test_transport_covers_every_day_and_stay_every_night() -> None:
    summary = engine.compute_costs(
        [], inputs(transport_per_day=60000, stay_per_night=350000, contingency_pct=0)
    )
    lines = {line.category: line for line in summary.by_category}
    assert lines["transport"].hi == 180000
    assert lines["accommodation"].hi == 700000
    assert summary.estimate_lo == summary.estimate_hi == 880000


def test_missing_inputs_make_their_lines_unavailable() -> None:
    lines = {line.category: line for line in engine.compute_costs([], inputs()).by_category}
    assert (lines["transport"].hi, lines["transport"].label) == (0, "unavailable")
    assert (lines["accommodation"].hi, lines["accommodation"].label) == (0, "unavailable")


def test_ruling_b2_input_lines_are_labelled_traveller_input() -> None:
    summary = engine.compute_costs([], inputs(transport_per_day=0, stay_per_night=100))
    lines = {line.category: line.label for line in summary.by_category}
    assert lines["transport"] == lines["accommodation"] == "traveller_input"


def test_the_contingency_rounds_half_up_on_the_high_estimate() -> None:
    summary = engine.compute_costs([item(100, 105)], inputs(contingency_pct=10))
    assert summary.contingency == 11  # 10.5
    assert summary.planning_total == 116


def test_an_empty_trip_is_not_complete() -> None:
    summary = engine.compute_costs([], inputs())
    assert (summary.complete, summary.planning_total) == (False, 0)


def test_the_stated_figures_of_the_section_9_3_1_example() -> None:
    """Only figures §9.3.1 states; its item inputs are in blueprint §20.3, which is not here."""
    assert engine.half_up(1230000 * 10, 100) == 123000
    assert engine.split(1353000, 3)[0] == 451000
    assert engine.BUDGET_NEAR_PCT * 1500000 <= 100 * 1353000


# BF-11, ruling B4 and F-3


@pytest.mark.parametrize(
    ("total", "status", "code"),
    [
        (8900, "none", None),
        (9000, "near", "BUDGET_NEAR"),
        (10000, "near", "BUDGET_NEAR"),
        (10100, "exceeded", "BUDGET_EXCEEDED"),
    ],
)
def test_tc_304_budget_thresholds(total: int, status: str, code: str | None) -> None:
    summary = status_at(total, 10000)
    assert summary.status == status
    assert [alert.code for alert in summary.alerts] == ([code] if code else [])


def test_f_3_there_is_no_excess_unless_the_budget_is_exceeded() -> None:
    assert status_at(10100, 10000).excess == 100
    for total in (8900, 9000, 10000):
        assert status_at(total, 10000).excess is None


def test_f_3_the_response_shape_refuses_an_excess_that_does_not_match_the_status() -> None:
    with pytest.raises(ValidationError):
        BudgetStatus(amount=Decimal(100), status="near", ratio_pct=95, excess=Decimal(1))
    with pytest.raises(ValidationError):
        BudgetStatus(amount=Decimal(100), status="exceeded", ratio_pct=101, excess=None)


@pytest.mark.parametrize("budget", [None, 0])
def test_no_budget_or_a_zero_budget_has_no_status(budget: int | None) -> None:
    summary = status_at(500, budget)
    assert (summary.status, summary.ratio_pct, summary.excess) == ("none", None, None)


def test_ruling_b4_ratio_pct_is_an_integer_rounded_half_up_once() -> None:
    assert status_at(9020, 10000).ratio_pct == 90
    assert status_at(9050, 10000).ratio_pct == 91
    assert status_at(9049, 10000).ratio_pct == 90


def test_the_alert_messages_name_the_share_and_the_excess() -> None:
    assert status_at(9020, 10000).alerts[0].message == "The plan uses 90% of your budget."
    assert status_at(10150, 10000).alerts[0].message == "The plan is over your budget by 1.50 GBP."


# BF-12, rulings B1, B2 and B5


def test_ruling_b1_contingency_splits_evenly_with_earlier_days_taking_the_extra_unit() -> None:
    summary = engine.compute_costs([item(1000, 1000), item(1000, 1000, day=2)], inputs())
    assert summary.contingency == 200
    assert [line.contingency_share for line in summary.by_day] == [67, 67, 66]


def test_ruling_b1_the_day_table_sums_to_the_planning_total() -> None:
    summary = engine.compute_costs(
        [item(1234, 2345, day=1), item(77, 99, day=3)],
        inputs(transport_per_day=1111, stay_per_night=3333),
    )
    assert [line.day_number for line in summary.by_day] == [1, 2, 3]
    assert sum(line.hi + line.contingency_share for line in summary.by_day) == (
        summary.planning_total
    )


def test_a_day_gets_its_items_transport_and_a_night_except_the_last() -> None:
    summary = engine.compute_costs(
        [item(100, day=3)], inputs(transport_per_day=10, stay_per_night=1000, contingency_pct=0)
    )
    assert [(line.lo, line.hi) for line in summary.by_day] == [
        (1010, 1010),
        (1010, 1010),
        (110, 110),
    ]


def test_a_stale_plan_with_a_day_past_the_trip_still_sums_to_the_total() -> None:
    summary = engine.compute_costs([item(1000, day=5)], inputs(num_days=2))
    assert [line.day_number for line in summary.by_day] == [1, 2, 5]
    assert sum(line.hi + line.contingency_share for line in summary.by_day) == (
        summary.planning_total
    )


@pytest.mark.parametrize(
    ("place_category", "expected"),
    [
        ("food", "food"),
        ("shopping", "other"),
        ("stay", "other"),
        ("sight", "activities"),
        ("museum", "activities"),
        ("nature", "activities"),
        ("entertainment", "activities"),
        ("religious", "activities"),
        ("activity", "activities"),
    ],
)
def test_ruling_b2_place_categories_map_to_cost_categories(
    place_category: str, expected: str
) -> None:
    assert engine.cost_category(place_category) == expected


def test_ruling_b5_the_contingency_row_is_an_estimate_with_min_equal_to_max() -> None:
    summary = engine.compute_costs([item(100, 1000)], inputs())
    row = summary.by_category[-1]
    assert (row.category, row.lo, row.hi, row.label) == ("contingency", 100, 100, "estimate")


def test_the_category_table_sums_to_the_planning_total() -> None:
    summary = engine.compute_costs(
        [
            item(100, 200, category="sight"),
            item(300, 450, category="food"),
            item(10, 15, category="shopping"),
        ],
        inputs(transport_per_day=1000, stay_per_night=2000),
    )
    assert [line.category for line in summary.by_category] == [
        "activities",
        "food",
        "other",
        "transport",
        "accommodation",
        "contingency",
    ]
    assert sum(line.hi for line in summary.by_category) == summary.planning_total


def test_a_category_label_is_the_weakest_of_its_items() -> None:
    curated = engine.compute_costs([item(1), item(2)], inputs()).by_category[0]
    mixed = engine.compute_costs([item(1), item(2, label="estimate")], inputs()).by_category[0]
    empty = engine.compute_costs([], inputs()).by_category[0]
    assert (curated.label, mixed.label, empty.label) == ("curated", "estimate", "estimate")


def test_the_engine_keeps_item_ids_as_given() -> None:
    fixed = UUID(int=7)
    missing = CostedItem(fixed, 1, "sight", None, None, "unavailable")
    assert engine.compute_costs([missing], inputs()).incomplete_items == [fixed]
