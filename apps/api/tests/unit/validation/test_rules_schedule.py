"""OVERLAP and TRANSFER_TOO_SHORT (§9.3.4, §9.3.5; FR-050, FR-051; IMP-404)."""

from datetime import date
from typing import get_args

from app.itinerary.schemas import PlannedDay, PlannedItem
from app.schemas.ai import FindingCode
from app.validation import rules
from app.validation.rules import CATALOGUE, ValidationContext
from app.validation.validator import validate

CTX = ValidationContext(
    start_date=date(2026, 12, 1), end_date=date(2026, 12, 3), places={"p": "A place"}
)


def item(
    start: str,
    duration: int = 60,
    travel: int | None = None,
    source: str | None = "routing_api",
    place_id: str = "p",
) -> PlannedItem:
    return PlannedItem(
        place_id=place_id,
        slot_type="activity",
        start_time=start,
        duration_min=duration,
        note="",
        travel_from_prev_min=travel,
        travel_source=source if travel is not None else None,
    )


def day(number: int, *items: PlannedItem) -> PlannedDay:
    return PlannedDay(number, "", list(items))


def codes(plan: list[PlannedDay]) -> list[str]:
    return [f.code for f in validate(plan, CTX)]


def test_catalogue_holds_the_13_codes_with_their_severities() -> None:
    assert set(CATALOGUE) == set(get_args(FindingCode))
    assert len(CATALOGUE) == 13
    assert CATALOGUE["OVERLAP"] == "error"
    assert CATALOGUE["TRANSFER_TOO_SHORT"] == "warning"
    assert CATALOGUE["MUST_VISIT_MISSING"] == "error"


def test_rules_run_in_a_fixed_order() -> None:
    assert rules.RULES[:2] == (rules.overlap, rules.transfer_too_short)


def test_tc_176_overlap_by_15_minutes_names_both_items() -> None:
    findings = validate([day(1, item("09:00"), item("09:45", travel=0))], CTX)
    assert [f.code for f in findings] == ["OVERLAP"]
    found = findings[0]
    assert (found.severity, found.day_number, found.item_ref) == ("error", 1, "d1-i2")
    for text in ("d1-i1", "d1-i2", "15 min"):
        assert text in found.message
    assert found.suggested_fix


def test_tc_177_back_to_back_items_give_no_overlap() -> None:
    assert "OVERLAP" not in codes([day(1, item("09:00"), item("10:00", travel=0))])


def test_tc_306_same_clock_time_on_different_days_is_never_compared() -> None:
    assert codes([day(1, item("09:00", 120)), day(2, item("09:00"))]) == []


def test_tc_178_10_minute_gap_with_30_minute_transfer_reports_the_shortfall() -> None:
    findings = validate([day(1, item("09:00"), item("10:10", travel=30))], CTX)
    assert [f.code for f in findings] == ["TRANSFER_TOO_SHORT"]
    found = findings[0]
    assert (found.severity, found.item_ref) == ("warning", "d1-i2")
    # need = 30 + 5 (routing_api) = 35; gap 10 -> 25 min short
    assert "25 min short" in found.message
    assert "(estimate)" not in found.message


def test_tc_179_fallback_estimate_is_labelled_and_takes_the_15_minute_buffer() -> None:
    findings = validate(
        [day(1, item("09:00"), item("10:10", travel=30, source="fallback_estimate"))], CTX
    )
    assert "(estimate)" in findings[0].message
    assert "35 min short" in findings[0].message  # 30 + 15 - 10


def test_gap_equal_to_travel_plus_buffer_is_enough() -> None:
    assert codes([day(1, item("09:00"), item("10:35", travel=30))]) == []
    assert codes([day(1, item("09:00"), item("10:34", travel=30))]) == ["TRANSFER_TOO_SHORT"]


def test_back_to_back_with_travel_is_a_short_transfer_not_an_overlap() -> None:
    assert codes([day(1, item("09:00"), item("10:00", travel=10))]) == ["TRANSFER_TOO_SHORT"]


def test_an_overlap_is_not_also_a_short_transfer() -> None:
    assert codes([day(1, item("09:00"), item("09:30", travel=30))]) == ["OVERLAP"]


def test_an_item_without_travel_data_is_not_checked_for_transfer() -> None:
    assert codes([day(1, item("09:00"), item("10:00"))]) == []


def test_empty_plan_and_single_items_give_no_schedule_findings() -> None:
    assert codes([]) == []
    assert codes([day(1, item("09:00")), day(2, item("23:00", 59))]) == []
