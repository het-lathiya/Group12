"""Grouping nearby places into days (§8.9, FR-030: TC-131, TC-132; IMP-503). Pure, no I/O."""

import json
from uuid import UUID

from test_pace import many_places
from test_request_builder import build

from app.evaluation import metrics
from app.generation.grouping import group_days
from app.schemas.ai import DayHint, ShortlistPlace


def place(number: int, lat: float, lon: float) -> ShortlistPlace:
    return many_places(1)[0].model_copy(
        update={"place_id": UUID(int=number), "name": f"P{number}", "lat": lat, "lon": lon}
    )


# Two areas about 50 km apart, listed interleaved so rank order alone would mix them.
NORTH = [place(n, 12.80 + n / 1000, 76.60) for n in (1, 3, 5, 7)]
SOUTH = [place(n, 12.35 + n / 1000, 76.60) for n in (2, 4, 6, 8)]
MIXED = [p for pair in zip(NORTH, SOUTH, strict=True) for p in pair]


def ids(hint: DayHint) -> set[UUID]:
    return set(hint.place_ids)


def test_grouping_tc_131_two_distant_areas_fall_on_separate_days() -> None:
    hints = group_days(MIXED, [], num_days=2, max_items=5)
    assert {frozenset(ids(h)) for h in hints} == {
        frozenset(p.place_id for p in NORTH),
        frozenset(p.place_id for p in SOUTH),
    }


def test_grouping_tc_132_the_same_input_twice_gives_byte_identical_day_hints() -> None:
    first = build(must_visit=[], shortlist=many_places(20))
    second = build(must_visit=[], shortlist=many_places(20))
    dump = [json.dumps([h.model_dump(mode="json") for h in r.day_hints]) for r in (first, second)]
    assert dump[0] == dump[1]
    assert group_days(MIXED, [], 2, 5) == group_days(MIXED, [], 2, 5)


def test_grouping_must_visit_places_seed_the_days_first() -> None:
    must = [SOUTH[-1].place_id]
    hints = group_days(MIXED, must, num_days=2, max_items=5)
    assert hints[0].place_ids[0] == SOUTH[-1].place_id
    assert ids(hints[0]) == {p.place_id for p in SOUTH}


def test_grouping_caps_each_day_and_leaves_out_what_has_no_room() -> None:
    hints = group_days(MIXED, [], num_days=2, max_items=3)
    assert [len(h.place_ids) for h in hints] == [3, 3]


def test_grouping_more_days_than_places_gives_one_hint_per_place() -> None:
    hints = group_days(MIXED[:2], [], num_days=5, max_items=3)
    assert [h.day_number for h in hints] == [1, 2]
    assert group_days([], [], num_days=3, max_items=3) == []


def test_grouping_fr_030_ac2_metrics_record_avg_daily_travel_min() -> None:
    scores = [
        {
            "schema_valid": True,
            "place_ids_valid": True,
            "usable": True,
            "daily_travel_min": [10, 20],
        },
        {"schema_valid": False, "place_ids_valid": False, "usable": False, "daily_travel_min": []},
        {"schema_valid": True, "place_ids_valid": True, "usable": True, "daily_travel_min": [45]},
    ]
    assert metrics.compute(scores)["avg_daily_travel_min"] == 25.0
    assert metrics.compute(scores[1:2])["avg_daily_travel_min"] is None
