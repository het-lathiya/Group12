"""Transport allowance, stay budget and source labels (§9.3.1 BF-05, BF-06; FR-072, FR-076;
IMP-411: TC-223, TC-224, TC-232)."""

from decimal import Decimal
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from app.budget import engine
from app.budget.engine import CostInputs
from app.budget.schemas import BudgetSettingsPatch, CategoryCostLine
from app.places.vocabulary import SourceLabel as PlacesSourceLabel
from app.schemas.labels import SOURCE_LABELS, SourceLabel


def inputs(**overrides: Any) -> CostInputs:
    values: dict[str, Any] = {
        "num_days": 3,
        "adults": 2,
        "children": 0,
        "currency": "GBP",
        "budget": None,
        "transport_per_day": None,
        "stay_per_night": None,
        "contingency_pct": 0,
    }
    return CostInputs(**(values | overrides))


def line(summary: engine.CostSummary, category: str) -> engine.CategoryLine:
    return next(row for row in summary.by_category if row.category == category)


def test_tc_223_allowances_enter_the_breakdown_as_traveller_input() -> None:
    # 3 days, 2 nights: BF-05 transport = 3 x 10.00, BF-06 stay = 2 x 45.00.
    summary = engine.compute_costs([], inputs(transport_per_day=1000, stay_per_night=4500))

    transport, stay = line(summary, "transport"), line(summary, "accommodation")
    assert (transport.lo, transport.hi, transport.label) == (3000, 3000, "traveller_input")
    assert (stay.lo, stay.hi, stay.label) == (9000, 9000, "traveller_input")
    assert summary.planning_total == 12000
    assert [day.lo for day in summary.by_day] == [5500, 5500, 1000]


def test_tc_224_missing_allowances_are_unavailable_and_add_nothing() -> None:
    summary = engine.compute_costs([], inputs(transport_per_day=None, stay_per_night=None))

    for category in ("transport", "accommodation"):
        row = line(summary, category)
        assert (row.lo, row.hi, row.label) == (0, 0, "unavailable")
    assert summary.planning_total == 0


def test_tc_224_one_allowance_set_leaves_the_other_unavailable() -> None:
    summary = engine.compute_costs([], inputs(transport_per_day=500))

    assert line(summary, "transport").label == "traveller_input"
    assert line(summary, "accommodation").label == "unavailable"


def test_allowances_patch_accepts_non_negative_decimals_and_null() -> None:
    patch = BudgetSettingsPatch.model_validate(
        {"transport_allowance_per_day": "0.00", "stay_budget_per_night": None}
    )
    assert patch.transport_allowance_per_day == Decimal("0.00")
    assert patch.model_fields_set == {"transport_allowance_per_day", "stay_budget_per_night"}


@pytest.mark.parametrize(
    "body",
    [
        {"transport_allowance_per_day": "-0.01"},
        {"stay_budget_per_night": "12.345"},
        {"contingency_pct": 51},
        {"budget_mode": "live"},
    ],
)
def test_allowances_patch_refuses_negative_or_unknown_values(body: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        BudgetSettingsPatch.model_validate(body)


# Labels (FR-076 AC2, TC-232)


class Labelled(BaseModel):
    label: SourceLabel


def test_tc_232_labels_are_exactly_curated_estimate_unavailable() -> None:
    assert {label.value for label in SourceLabel} == {"curated", "estimate", "unavailable"}
    assert {"curated", "estimate", "unavailable"} == SOURCE_LABELS
    assert PlacesSourceLabel is SourceLabel  # one definition


@pytest.mark.parametrize("value", ["live", "verified", "Live", "Verified", "traveller_input"])
def test_tc_232_labels_cannot_serialise_live_or_verified(value: str) -> None:
    with pytest.raises(ValidationError):
        Labelled.model_validate({"label": value})


@pytest.mark.parametrize("value", ["live", "verified"])
def test_tc_232_cost_lines_cannot_be_labelled_live_or_verified(value: str) -> None:
    with pytest.raises(ValidationError):
        CategoryCostLine.model_validate(
            {"category": "transport", "min": "0.00", "max": "0.00", "label": value}
        )
