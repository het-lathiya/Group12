"""Pace presets (§8.9, FR-029: TC-129, TC-130; IMP-503). No database, no network."""

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest
from test_request_builder import build, prefs, shortlist, trip

from app.ai.providers.mock import MockProvider
from app.generation import presets
from app.schemas.ai import GenerationRequest, ShortlistPlace

CASES = Path(__file__).resolve().parents[5] / "eval" / "datasets" / "trips" / "v1" / "cases.jsonl"


def many_places(count: int) -> list[ShortlistPlace]:
    base = shortlist()[0].model_dump()
    return [
        ShortlistPlace.model_validate(
            base
            | {
                "place_id": f"00000000-0000-4000-8000-{n:012d}",
                "name": f"Place {n}",
                "lat": 12.3 + n / 1000,
                "typical_duration_min": 60,
            }
        )
        for n in range(1, count + 1)
    ]


@pytest.mark.parametrize(
    ("pace", "items", "minutes"),
    [("relaxed", 3, 300), ("balanced", 5, 480), ("busy", 7, 600)],
)
def test_pace_presets_cap_items_per_day(pace: str, items: int, minutes: int) -> None:
    limits = presets.pace_limits(pace)
    assert (limits.max_items_per_day, limits.max_active_minutes_per_day) == (items, minutes)
    request = build(prefs=prefs(pace=pace), must_visit=[], shortlist=many_places(30))
    assert (request.limits.max_items_per_day, request.limits.max_active_minutes_per_day) == (
        items,
        minutes,
    )
    assert len(request.day_hints) == 3
    assert all(len(hint.place_ids) == items for hint in request.day_hints)


def test_pace_unknown_value_is_refused() -> None:
    with pytest.raises(ValueError, match="sprint"):
        presets.pace_limits("sprint")


def test_pace_tc_129_relaxed_mock_days_keep_to_3_items_and_300_minutes() -> None:
    case: dict[str, Any] = next(
        json.loads(line)
        for line in CASES.read_text(encoding="utf-8").splitlines()
        if json.loads(line)["request"]["preferences"]["pace"] == "relaxed"
    )
    request = GenerationRequest.model_validate(case["request"])
    output = asyncio.run(MockProvider("ok", app_env="test").generate_itinerary(request)).output
    assert output.days
    for day in output.days:
        assert len(day.items) <= 3
        assert sum(item.duration_min for item in day.items) <= 300


def test_pace_tc_130_a_changed_pace_applies_the_new_limit() -> None:
    places = many_places(30)
    relaxed = build(prefs=prefs(pace="relaxed"), must_visit=[], shortlist=places)
    busy = build(prefs=prefs(pace="busy"), must_visit=[], shortlist=places, trip=trip())
    assert relaxed.limits.max_items_per_day == 3
    assert busy.limits.max_items_per_day == 7
    assert max(len(h.place_ids) for h in relaxed.day_hints) == 3
    assert max(len(h.place_ids) for h in busy.day_hints) == 7
