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


@pytest.mark.parametrize(
    ("percent", "code"),
    [(89, None), (90, "BUDGET_NEAR"), (100, "BUDGET_NEAR"), (101, "BUDGET_EXCEEDED")],
)
def test_budget_tc_184_tc_185_tc_304_exact_thresholds(percent: int, code: str | None) -> None:
    from decimal import Decimal

    from app.budget.engine import CostInputs
    from app.validation.rules import budget_conflicts

    ctx = ValidationContext(
        date(2026, 12, 7), date(2026, 12, 7), cost_inputs=CostInputs(1, 1, 0, "INR", 10000, 0, 0, 0)
    )
    item = PlannedItem(
        PLACE,
        "activity",
        "09:00",
        60,
        "",
        cost_min=Decimal(percent),
        cost_max=Decimal(percent),
        cost_label="curated",
    )
    findings = budget_conflicts([PlannedDay(1, "", [item])], ctx)
    assert [f.code for f in findings] == ([] if code is None else [code])
    if percent == 101:
        assert "1.00 INR" in findings[0].message
        assert findings[0].severity == "warning"


@pytest.mark.parametrize("budget", [None, 0])
def test_budget_empty_has_no_budget_finding(budget: int | None) -> None:
    from app.budget.engine import CostInputs
    from app.validation.rules import budget_conflicts

    ctx = ValidationContext(
        date(2026, 12, 7),
        date(2026, 12, 7),
        cost_inputs=CostInputs(1, 1, 0, "INR", budget, 0, 0, 0),
    )
    assert budget_conflicts([], ctx) == []


def test_budget_incomplete_and_estimated_item_findings() -> None:
    from decimal import Decimal

    from app.budget.engine import CostInputs
    from app.validation.rules import budget_conflicts

    ctx = ValidationContext(
        date(2026, 12, 7),
        date(2026, 12, 7),
        cost_inputs=CostInputs(1, 1, 0, "INR", None, 0, 0, 0),
        category_estimate_refs=frozenset({"d1-i2"}),
    )
    items = [
        PlannedItem(PLACE, "activity", "09:00", 60, "", cost_label="unavailable"),
        PlannedItem(
            PLACE,
            "activity",
            "10:00",
            60,
            "",
            cost_min=Decimal("5.00"),
            cost_max=Decimal("6.00"),
            cost_label="estimate",
        ),
    ]
    found = budget_conflicts([PlannedDay(1, "", items)], ctx)
    assert [(f.code, f.severity) for f in found] == [
        ("COST_INCOMPLETE", "warning"),
        ("ESTIMATE_USED", "info"),
    ]
    assert found[0].item_ref is None
    assert "2 planned items" in found[0].message
    assert found[1].item_ref == "d1-i2"


def test_budget_findings_never_drop_repair_items_even_if_severity_is_error() -> None:
    from fixtures.ai import sample_request

    from app.schemas.ai import ItineraryOutput, PlanFinding
    from app.validation.repair import repair, scope_for

    request = sample_request()
    output = ItineraryOutput.model_validate(
        {
            "days": [
                {
                    "day_number": 1,
                    "theme": "Day",
                    "items": [
                        {
                            "place_id": str(request.shortlist[0].place_id),
                            "start_time": "09:00",
                            "duration_min": 60,
                            "slot_type": "activity",
                            "note": "",
                        }
                    ],
                }
            ],
            "assumptions": [],
        }
    )
    findings = [
        PlanFinding(
            code=code, severity="error", message="Budget finding", day_number=1, item_ref="d1-i1"
        )
        for code in ("BUDGET_EXCEEDED", "BUDGET_NEAR", "COST_INCOMPLETE", "ESTIMATE_USED")
    ]
    result = repair(
        output, findings, scope_for(request.model_copy(update={"must_visit_place_ids": []})), {}
    )
    assert result.output == output
    assert result.fixes == 0


def test_budget_known_estimated_price_is_not_a_bf_04_category_estimate() -> None:
    from decimal import Decimal

    from app.budget.engine import CostInputs
    from app.validation.rules import budget_conflicts

    ctx = ValidationContext(
        date(2026, 12, 7), date(2026, 12, 7), cost_inputs=CostInputs(1, 1, 0, "INR", None, 0, 0, 0)
    )
    item = PlannedItem(
        PLACE,
        "activity",
        "09:00",
        60,
        "",
        cost_min=Decimal("5.00"),
        cost_max=Decimal("6.00"),
        cost_label="estimate",
    )
    assert budget_conflicts([PlannedDay(1, "", [item])], ctx) == []
