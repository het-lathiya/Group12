"""MUST_VISIT_MISSING, UNKNOWN_PLACE and OUTSIDE_TRIP_DATES (§9.3.6, §9.3.7; FR-055; IMP-404)."""

from datetime import date
from uuid import UUID

from app.itinerary.schemas import PlannedDay, PlannedItem
from app.validation import rules
from app.validation.rules import ValidationContext
from app.validation.validator import validate

FORT = "00000000-0000-4000-8000-000000000001"
MARKET = "00000000-0000-4000-8000-000000000002"
LAKE = "00000000-0000-4000-8000-000000000003"
GONE = "00000000-0000-4000-8000-000000000009"
PLACES = {FORT: "Old Fort", MARKET: "Spice Market", LAKE: "Lake Walk"}
# 3 days: 1 to 3 December
CTX = ValidationContext(start_date=date(2026, 12, 1), end_date=date(2026, 12, 3), places=PLACES)


def item(place_id: str, start: str = "09:00") -> PlannedItem:
    return PlannedItem(
        place_id=place_id, slot_type="activity", start_time=start, duration_min=60, note=""
    )


def day(number: int, *items: PlannedItem) -> PlannedDay:
    return PlannedDay(number, "", list(items))


def test_reference_rules_follow_the_schedule_rules_in_the_table_order() -> None:
    assert (
        rules.overlap,
        rules.transfer_too_short,
        rules.must_visit_missing,
        rules.unknown_place,
        rules.outside_trip_dates,
    ) == rules.RULES


def test_tc_186_missing_must_visit_names_the_place_with_place_id_and_no_item() -> None:
    ctx = ValidationContext(
        start_date=CTX.start_date,
        end_date=CTX.end_date,
        places=PLACES,
        must_visit_ids=frozenset({FORT, LAKE}),
    )
    findings = validate([day(1, item(FORT))], ctx)
    assert [f.code for f in findings] == ["MUST_VISIT_MISSING"]
    found = findings[0]
    assert found.severity == "error"
    assert found.place_id == UUID(LAKE)
    assert found.item_ref is None
    assert found.day_number is None
    assert "Lake Walk" in found.message
    assert "not in the plan" in found.message
    assert found.suggested_fix


def test_present_must_visit_places_give_no_finding() -> None:
    ctx = ValidationContext(
        start_date=CTX.start_date,
        end_date=CTX.end_date,
        places=PLACES,
        must_visit_ids=frozenset({FORT}),
    )
    assert validate([day(2, item(FORT))], ctx) == []


def test_tc_187_inactive_place_is_unknown() -> None:
    findings = validate([day(1, item(FORT), item(GONE, "11:00"))], CTX)
    assert [(f.code, f.item_ref, f.severity) for f in findings] == [
        ("UNKNOWN_PLACE", "d1-i2", "error")
    ]


def test_active_place_outside_the_shortlist_is_unknown_in_generation() -> None:
    ctx = ValidationContext(
        start_date=CTX.start_date,
        end_date=CTX.end_date,
        places=PLACES,
        shortlist_ids=frozenset({FORT}),
    )
    findings = validate([day(1, item(FORT), item(MARKET, "11:00"))], ctx)
    assert [(f.code, f.item_ref) for f in findings] == [("UNKNOWN_PLACE", "d1-i2")]


def test_without_a_shortlist_any_active_place_is_valid() -> None:
    assert validate([day(1, item(FORT), item(MARKET, "11:00"))], CTX) == []


def test_tc_305_items_on_start_and_end_dates_pass_and_the_day_after_is_outside_trip_dates() -> None:
    plan = [day(1, item(FORT)), day(3, item(MARKET)), day(4, item(LAKE), item(FORT, "11:00"))]
    findings = validate(plan, CTX)
    assert [(f.code, f.day_number, f.item_ref) for f in findings] == [
        ("OUTSIDE_TRIP_DATES", 4, "d4-i1"),
        ("OUTSIDE_TRIP_DATES", 4, "d4-i2"),
    ]
    assert all(f.severity == "error" for f in findings)
    assert "outside the trip's 3 days" in findings[0].message


def test_day_numbers_a_finding_cannot_hold_keep_the_day_in_the_reference() -> None:
    findings = validate([day(0, item(FORT)), day(15, item(MARKET))], CTX)
    assert [(f.code, f.day_number, f.item_ref) for f in findings] == [
        ("OUTSIDE_TRIP_DATES", None, "d0-i1"),
        ("OUTSIDE_TRIP_DATES", None, "d15-i1"),
    ]


def test_one_day_trip_accepts_day_1_only() -> None:
    ctx = ValidationContext(start_date=CTX.start_date, end_date=CTX.start_date, places=PLACES)
    assert ctx.num_days == 1
    assert [f.code for f in validate([day(1, item(FORT)), day(2, item(LAKE))], ctx)] == [
        "OUTSIDE_TRIP_DATES"
    ]
