"""The day and category breakdown, BF-12 (§9.3.1; FR-073 AC1; IMP-507: TC-225, TC-300).

TC-225: given an itinerary, the day and category tables each add up to the planning total, also
once turned into the IMD-05 money strings of API-33. TC-300: the same holds for every fixture: the
two SAMPLE itineraries priced from places.csv, under each set of traveller inputs below.
"""

import csv
import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from app.budget import engine
from app.budget.engine import CostedItem, CostInputs, CostSummary
from app.budget.schemas import CategoryCostLine, DayCostLine

SAMPLETON = Path(__file__).resolve().parents[5] / "data" / "fixtures" / "sampleton"
ITINERARIES = ["two_day_walking", "five_day_local_transport"]
INPUTS = {
    "no allowances, no buffer": {"transport": None, "stay": None, "pct": 0},
    "allowances and a 10 percent buffer": {"transport": 1250, "stay": 6000, "pct": 10},
    "a buffer that does not split evenly": {"transport": 333, "stay": None, "pct": 7},
    "the largest buffer": {"transport": None, "stay": 9999, "pct": 50},
}


def places() -> dict[str, Any]:
    with (SAMPLETON / "places.csv").open(encoding="utf-8") as handle:
        return {
            row["external_ref"]: SimpleNamespace(
                category=row["category"],
                price_min=Decimal(row["price_min"]) if row["price_min"] else None,
                price_max=Decimal(row["price_max"]) if row["price_max"] else None,
                price_currency=row["price_currency"] or None,
                price_label=row["price_label"],
                tags=row["tags"].split(";") if row["tags"] else [],
            )
            for row in csv.DictReader(handle)
        }


def fixture_trip(name: str, adults: int, children: int) -> tuple[list[CostedItem], int]:
    data = json.loads((SAMPLETON / "sample_itineraries" / f"{name}.json").read_text("utf-8"))
    trip = data["trip"]
    num_days = (date.fromisoformat(trip["end_date"]) - date.fromisoformat(trip["start_date"])).days
    by_ref = places()
    rows = []
    for day in data["itinerary"]["days"]:
        for entry in day["items"]:
            place = by_ref[entry["place_ref"]["external_ref"]]
            cost = engine.item_cost(place, adults=adults, children=children, currency="GBP")
            rows.append(
                CostedItem(uuid4(), day["day_number"], place.category, cost.lo, cost.hi, cost.label)
            )
    return rows, num_days + 1


def costs(
    rows: list[CostedItem], num_days: int, transport: Any, stay: Any, pct: int
) -> CostSummary:
    return engine.compute_costs(
        rows,
        CostInputs(num_days, 2, 1, "GBP", None, transport, stay, pct),
    )


def assert_tables_add_up(summary: CostSummary) -> None:
    total = summary.planning_total
    assert sum(line.hi + line.contingency_share for line in summary.by_day) == total
    assert sum(line.hi for line in summary.by_category) == total
    assert sum(line.contingency_share for line in summary.by_day) == summary.contingency
    assert [line.hi for line in summary.by_category if line.category == "contingency"] == [
        summary.contingency
    ]


def test_tc_225_both_tables_add_up_to_the_planning_total_in_api_money_strings() -> None:
    rows, num_days = fixture_trip("two_day_walking", adults=2, children=1)
    summary = costs(rows, num_days, transport=1250, stay=6000, pct=10)
    money = engine.from_minor
    days = [
        DayCostLine(
            day_number=line.day_number,
            min=money(line.lo),
            max=money(line.hi),
            contingency_share=money(line.contingency_share),
        )
        for line in summary.by_day
    ]
    categories = [
        CategoryCostLine(
            category=line.category, min=money(line.lo), max=money(line.hi), label=line.label
        )
        for line in summary.by_category
    ]
    total = money(summary.planning_total)
    as_json = [line.model_dump(mode="json") for line in days]
    assert sum(Decimal(row["max"]) + Decimal(row["contingency_share"]) for row in as_json) == total
    assert sum(Decimal(line.model_dump(mode="json")["max"]) for line in categories) == total
    assert [line.day_number for line in days] == list(range(1, num_days + 1))
    assert {line.category for line in categories} == {
        "activities",
        "food",
        "transport",
        "accommodation",
        "other",
        "contingency",
    }


@pytest.mark.parametrize("name", ITINERARIES)
@pytest.mark.parametrize("case", INPUTS.values(), ids=list(INPUTS))
def test_tc_300_category_and_day_sums_equal_the_trip_total_for_every_fixture(
    name: str, case: dict[str, Any]
) -> None:
    rows, num_days = fixture_trip(name, adults=2, children=1)
    assert rows, "the fixture has items"
    assert_tables_add_up(costs(rows, num_days, case["transport"], case["stay"], case["pct"]))


def test_tc_300_the_low_estimates_add_up_too() -> None:
    rows, num_days = fixture_trip("five_day_local_transport", adults=2, children=1)
    summary = costs(rows, num_days, transport=1250, stay=6000, pct=10)
    assert sum(line.lo for line in summary.by_day) == summary.estimate_lo
    no_buffer = [line for line in summary.by_category if line.category != "contingency"]
    assert sum(line.lo for line in no_buffer) == summary.estimate_lo


def test_tc_300_an_edit_that_moves_an_item_moves_its_cost_but_not_the_total() -> None:
    rows, num_days = fixture_trip("five_day_local_transport", adults=2, children=1)
    before = costs(rows, num_days, transport=1250, stay=6000, pct=10)
    priced = next(row for row in rows if row.hi)
    moved_to = 1 if priced.day_number != 1 else 2
    after_rows = [
        CostedItem(row.item_id, moved_to, row.place_category, row.lo, row.hi, row.label)
        if row is priced
        else row
        for row in rows
    ]
    after = costs(after_rows, num_days, transport=1250, stay=6000, pct=10)
    assert after.planning_total == before.planning_total
    day_hi = {line.day_number: line.hi for line in after.by_day}
    old_hi = {line.day_number: line.hi for line in before.by_day}
    assert day_hi[moved_to] == old_hi[moved_to] + (priced.hi or 0)
    assert day_hi[priced.day_number] == old_hi[priced.day_number] - (priced.hi or 0)
    assert_tables_add_up(after)
