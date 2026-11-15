"""Budget alerts and the contingency buffer (§9.3.1 BF-08, BF-09, BF-11; FR-074, FR-075; IMP-608).

TC-227: a total at 92 percent of the budget is near (BUDGET_NEAR, ratio 92). TC-228: a total above
the budget is exceeded and the alert names the excess. TC-229: a 10 percent buffer equals 10 percent
of the high estimate. TC-230: no buffer gives a zero buffer line. TC-298: the buffer applies to S_hi
and the category and day tables still add up to the planning total.

The switches: with 'contingency' off the API passes p = 0 (``itinerary.service``), the case of
TC-230; with 'budget_alerts' off API-33 drops the alerts but the engine, and so the validator
finding, is unchanged (API cases in ``tests/api/test_costs.py``).
"""

from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.budget import engine, service
from app.budget.engine import BUDGET_NEAR_PCT, CostedItem, CostInputs
from app.budget.schemas import BudgetSettingsPatch


def item(lo: int, hi: int | None = None, day: int = 1, category: str = "sight") -> CostedItem:
    return CostedItem(uuid4(), day, category, lo, lo if hi is None else hi, "curated")


def inputs(**overrides: Any) -> CostInputs:
    values: dict[str, Any] = {
        "num_days": 2,
        "adults": 2,
        "children": 0,
        "currency": "INR",
        "budget": None,
        "transport_per_day": None,
        "stay_per_night": None,
        "contingency_pct": 0,
    }
    return CostInputs(**(values | overrides))


def test_the_near_threshold_is_the_imd_29_code_constant() -> None:
    assert BUDGET_NEAR_PCT == 90


# Alerts, BF-11 (FR-074)


def test_tc_227_alerts_a_total_at_92_percent_of_the_budget_is_near() -> None:
    summary = engine.compute_costs([item(9200)], inputs(budget=10000))

    assert (summary.status, summary.ratio_pct, summary.excess) == ("near", 92, None)
    assert [(a.code, a.severity) for a in summary.alerts] == [("BUDGET_NEAR", "info")]
    assert "92%" in summary.alerts[0].message


def test_tc_228_alerts_a_total_above_the_budget_names_the_excess() -> None:
    summary = engine.compute_costs([item(10250)], inputs(budget=10000))

    assert (summary.status, summary.excess) == ("exceeded", 250)
    assert [(a.code, a.severity) for a in summary.alerts] == [("BUDGET_EXCEEDED", "warning")]
    assert "2.50 INR" in summary.alerts[0].message


def test_tc_228_alerts_the_buffer_counts_towards_the_budget() -> None:
    # S_hi 95.00 is under the budget, P = 95.00 + 10 percent is over it (DR-22).
    summary = engine.compute_costs([item(9500)], inputs(budget=10000, contingency_pct=10))

    assert (summary.planning_total, summary.status, summary.excess) == (10450, "exceeded", 450)


@pytest.mark.parametrize(
    ("total", "status"), [(8999, "none"), (9000, "near"), (10000, "near"), (10001, "exceeded")]
)
def test_alerts_boundaries_around_the_threshold_and_the_budget(total: int, status: str) -> None:
    assert engine.compute_costs([item(total)], inputs(budget=10000)).status == status


def test_alerts_have_stable_ids_and_carry_the_engine_message() -> None:
    trip_id = uuid4()
    alert = engine.compute_costs([item(9200)], inputs(budget=10000)).alerts[0]

    first, again = service._alert(trip_id, alert), service._alert(trip_id, alert)

    assert first.id == again.id
    assert (first.code, first.severity, first.message) == (alert.code, "info", alert.message)
    assert {"BUDGET_NEAR", "BUDGET_EXCEEDED"} == service.BUDGET_ALERTS


# Contingency, BF-08 and BF-09 (FR-075)


def test_tc_229_contingency_of_10_percent_is_10_percent_of_the_high_estimate() -> None:
    summary = engine.compute_costs([item(8000, 12000)], inputs(contingency_pct=10))

    assert (summary.estimate_lo, summary.estimate_hi) == (8000, 12000)
    assert summary.contingency == 1200
    assert summary.planning_total == 13200
    line = next(row for row in summary.by_category if row.category == "contingency")
    assert (line.lo, line.hi, line.label) == (1200, 1200, "estimate")


def test_tc_230_contingency_off_or_zero_gives_a_zero_buffer_line() -> None:
    summary = engine.compute_costs([item(8000, 12000)], inputs(contingency_pct=0))

    assert summary.contingency == 0
    assert summary.planning_total == summary.estimate_hi == 12000
    line = next(row for row in summary.by_category if row.category == "contingency")
    assert (line.lo, line.hi) == (0, 0)
    assert all(day.contingency_share == 0 for day in summary.by_day)


def test_tc_298_contingency_applies_to_s_hi_and_the_tables_add_up() -> None:
    rows = [item(1001, 1333, day=1), item(500, 777, day=2, category="food")]
    summary = engine.compute_costs(
        rows, inputs(contingency_pct=7, transport_per_day=333, stay_per_night=4999)
    )

    s_hi = 1333 + 777 + 2 * 333 + 4999
    assert summary.estimate_hi == s_hi
    assert summary.contingency == engine.half_up(s_hi * 7, 100)
    total = summary.planning_total
    assert total == s_hi + summary.contingency
    assert sum(line.hi for line in summary.by_category) == total
    assert sum(day.hi + day.contingency_share for day in summary.by_day) == total


@pytest.mark.parametrize("pct", [0, 10, 50])
def test_contingency_percentages_0_to_50_are_accepted(pct: int) -> None:
    assert BudgetSettingsPatch(contingency_pct=pct).contingency_pct == pct


@pytest.mark.parametrize("pct", [-1, 51])
def test_contingency_percentages_outside_0_to_50_are_refused(pct: int) -> None:
    with pytest.raises(ValidationError):
        BudgetSettingsPatch(contingency_pct=pct)
