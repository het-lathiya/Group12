"""Every finding names its cause and a suggested fix, and is counted (FR-056; IMP-405: TC-188,
TC-189)."""

from datetime import date
from typing import get_args

import pytest

from app.itinerary.schemas import PlannedDay, PlannedItem
from app.schemas.ai import FindingCode
from app.validation import rules, validator
from app.validation.rules import ValidationContext

FORT = "00000000-0000-4000-8000-000000000001"
MARKET = "00000000-0000-4000-8000-000000000002"
LAKE = "00000000-0000-4000-8000-000000000003"
GONE = "00000000-0000-4000-8000-000000000009"
CTX = ValidationContext(
    start_date=date(2026, 12, 1),
    end_date=date(2026, 12, 2),
    places={FORT: "Old Fort", MARKET: "Spice Market", LAKE: "Lake Walk"},
    must_visit_ids=frozenset({LAKE}),
)


def item(place_id: str, start: str, travel: int | None = None) -> PlannedItem:
    return PlannedItem(
        place_id=place_id,
        slot_type="activity",
        start_time=start,
        duration_min=60,
        note="",
        travel_from_prev_min=travel,
        travel_source="routing_api" if travel is not None else None,
    )


# One plan that breaks every rule the validator runs: an overlap and a short transfer on day 1,
# an unknown place, a day outside the two-day trip, and the must-visit Lake Walk left out.
FLAWED = [
    PlannedDay(
        1,
        "",
        [item(FORT, "09:00"), item(MARKET, "09:30", 10), item(GONE, "10:35", 10)],
    ),
    PlannedDay(3, "", [item(FORT, "09:00")]),
]


def test_tc_188_every_finding_names_its_cause_and_a_suggested_fix() -> None:
    findings = validator.validate(FLAWED, CTX)
    assert {f.code for f in findings} == {
        "OVERLAP",
        "TRANSFER_TOO_SHORT",
        "UNKNOWN_PLACE",
        "OUTSIDE_TRIP_DATES",
        "MUST_VISIT_MISSING",
    }
    for found in findings:
        assert found.message.strip(), found.code
        assert found.suggested_fix, found.code
        assert found.suggested_fix.strip(), found.code


def test_every_catalogue_code_has_a_suggested_fix() -> None:
    assert set(validator.SUGGESTED_FIXES) == set(get_args(FindingCode)) == set(rules.CATALOGUE)
    assert all(fix.strip() and len(fix) <= 500 for fix in validator.SUGGESTED_FIXES.values())


def test_a_rules_own_fix_wins_and_the_catalogue_fills_a_missing_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def bare(plan: object, ctx: object) -> list[rules.Finding]:
        return [rules.finding("DAY_TOO_LONG", "Day 1 has 9 items.", day_number=1)]

    monkeypatch.setattr(validator, "RULES", (rules.transfer_too_short, bare))
    short, long_day = validator.validate(FLAWED, CTX)
    assert short.suggested_fix == "Start d1-i3 10 min later."
    assert long_day.suggested_fix == validator.SUGGESTED_FIXES["DAY_TOO_LONG"]


def test_tc_189_must_visit_missing_keeps_its_place_and_no_item_for_storage() -> None:
    (missing,) = [f for f in validator.validate(FLAWED, CTX) if f.code == "MUST_VISIT_MISSING"]
    assert str(missing.place_id) == LAKE
    assert missing.item_ref is None
    assert missing.suggested_fix


def test_summary_counts_findings_by_severity() -> None:
    findings = validator.validate(FLAWED, CTX)
    assert validator.summary(findings) == {"errors": 4, "warnings": 1, "infos": 0}
    assert validator.summary([]) == {"errors": 0, "warnings": 0, "infos": 0}
