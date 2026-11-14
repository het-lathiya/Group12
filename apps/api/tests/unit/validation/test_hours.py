"""Hours decision list, overnight and destination-local boundaries (IMP-501)."""

from datetime import date

import pytest

from app.itinerary.schemas import PlannedDay, PlannedItem
from app.validation.rules import HoursInfo, OpeningRow, ValidationContext
from app.validation.validator import validate

PLACE = "00000000-0000-4000-8000-000000000001"


def check(
    info: HoursInfo, start: str = "09:00", duration: int = 60, timezone: str = "Asia/Kolkata"
):
    ctx = ValidationContext(
        date(2026, 12, 7),
        date(2026, 12, 7),
        places={PLACE: "Place"},
        timezone=timezone,
        opening_hours={PLACE: info},
    )
    return validate([PlannedDay(1, "", [PlannedItem(PLACE, "activity", start, duration, "")])], ctx)


@pytest.mark.parametrize(
    "info",
    [
        HoursInfo("unavailable", [OpeningRow(1, True)]),
        HoursInfo("curated"),
        HoursInfo("curated", [OpeningRow(2, True)]),
    ],
)
def test_hours_tc_181_unknown_never_claims_a_conflict(info: HoursInfo) -> None:
    assert [(f.code, f.severity) for f in check(info)] == [("HOURS_UNVERIFIED", "info")]


def test_hours_tc_180_closed_day() -> None:
    assert [(f.code, f.severity) for f in check(HoursInfo("curated", [OpeningRow(1, True)]))] == [
        ("CLOSED_ON_DAY", "error")
    ]


@pytest.mark.parametrize(("label", "severity"), [("curated", "error"), ("estimate", "warning")])
def test_hours_outside_boundary_and_label_severity(label: str, severity: str) -> None:
    info = HoursInfo(label, [OpeningRow(1, False, "09:00", "10:00")])
    assert check(info) == []
    assert [(f.code, f.severity) for f in check(info, duration=61)] == [("OUTSIDE_HOURS", severity)]


def test_hours_tc_301_overnight_covers_midnight_and_precedes_closed_day() -> None:
    info = HoursInfo("curated", [OpeningRow(7, False, "22:00", "02:00", True), OpeningRow(1, True)])
    assert check(info, "00:30", 90) == []
    assert check(info, "01:00", 61)[0].code == "CLOSED_ON_DAY"
    assert (
        check(HoursInfo("curated", [OpeningRow(1, False, "22:00", "02:00", True)]), "23:30", 120)
        == []
    )


def test_hours_tc_302_uses_local_weekday_not_utc() -> None:
    info = HoursInfo("curated", [OpeningRow(1, False, "00:00", "02:00"), OpeningRow(7, True)])
    assert check(info, "00:30", 60, "Asia/Kolkata") == []


def test_hours_multiple_intervals() -> None:
    info = HoursInfo(
        "curated", [OpeningRow(1, False, "09:00", "11:00"), OpeningRow(1, False, "13:00", "17:00")]
    )
    assert check(info, "13:00") == []
    assert check(info, "10:30")[0].code == "OUTSIDE_HOURS"
