"""Scoring and shortlist ranking (§8.9; FR-028: TC-126, TC-127, TC-128; IMP-304).

The SAMPLE tests read data/fixtures/sampleton/places.csv directly, so no database is needed.
"""

import csv
import logging
import uuid
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.generation import ranking
from app.trips import preference_mapping as pm

REPO_ROOT = Path(__file__).resolve().parents[5]
PLACES_CSV = REPO_ROOT / "data" / "fixtures" / "sampleton" / "places.csv"
AREA = SimpleNamespace(
    center_lat=Decimal("53.9"),
    center_lon=Decimal("2.2"),
    bbox_min_lat=Decimal("53.85"),
    bbox_max_lat=Decimal("53.95"),
    bbox_min_lon=Decimal("2.1"),
    bbox_max_lon=Decimal("2.3"),
)


@dataclass(frozen=True)
class Fake:
    place: Any
    must_visit: bool = False
    min_group_cost: Decimal | None = None


def fake(**overrides: Any) -> Fake:
    must_visit = overrides.pop("must_visit", False)
    cost = overrides.pop("cost", None)
    values = {
        "id": uuid.uuid4(),
        "category": "sight",
        "tags": [],
        "lat": Decimal("53.9"),
        "lon": Decimal("2.2"),
        "typical_duration_min": 60,
    }
    return Fake(SimpleNamespace(**(values | overrides)), must_visit, cost)


def context(
    candidates: list[Fake],
    *,
    days: int = 3,
    budget: str | None = None,
    meals: int = 1,
    **prefs: Any,
) -> ranking.RankingContext:
    return ranking.build_context(
        candidates,
        pm.map_preferences(pm.Preferences(**prefs), pm.TripFacts()),
        AREA,
        num_days=days,
        meal_slots_per_day=meals,
        activity_budget=Decimal(budget) if budget else None,
    )


def sample_candidates(must_visit: tuple[str, ...] = ()) -> list[Fake]:
    with PLACES_CSV.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    return [
        fake(
            id=uuid.uuid5(uuid.NAMESPACE_URL, row["external_ref"]),
            category=row["category"],
            tags=row["tags"].split(";"),
            lat=Decimal(row["lat"]),
            lon=Decimal(row["lon"]),
            typical_duration_min=int(row["typical_duration_min"]),
            cost=Decimal(row["price_min"]) * 2 if row["price_min"] else None,
            must_visit=row["external_ref"] in must_visit,
            ref=row["external_ref"],
        )
        for row in rows
    ]


def test_tc_126_a_better_interest_match_ranks_higher() -> None:
    match = fake(category="museum", tags=["history"], id=uuid.UUID(int=2))
    half = fake(category="sight", tags=["history"], id=uuid.UUID(int=1))
    candidates = [half, match]
    ctx = context(candidates, interests=["museum", "history"])
    ids = [entry.candidate for entry in ranking.rank_shortlist(candidates, ctx).entries]
    assert ids == [match, half]
    assert ranking.score(match, ctx).interest == 1
    assert ranking.score(half, ctx).interest == 0.5


def test_tc_127_two_runs_give_the_same_order_and_ties_break_on_place_id() -> None:
    candidates = [fake(id=uuid.UUID(int=n)) for n in (3, 1, 2)]
    ctx = context(candidates)
    first = ranking.rank_shortlist(candidates, ctx)
    second = ranking.rank_shortlist(list(reversed(candidates)), ctx)
    assert first.entries == second.entries
    assert [e.candidate.place.id.int for e in first.entries] == [1, 2, 3]


def test_tc_128_score_parts_are_logged_at_debug_only(caplog: pytest.LogCaptureFixture) -> None:
    candidates = [fake()]
    ctx = context(candidates, notes="private note text")
    with caplog.at_level(logging.INFO, logger=ranking.__name__):
        ranking.rank_shortlist(candidates, ctx)
    assert not caplog.records
    with caplog.at_level(logging.DEBUG, logger=ranking.__name__):
        ranking.rank_shortlist(candidates, ctx)
    (record,) = caplog.records
    assert record.levelno == logging.DEBUG
    message = record.getMessage()
    for name in ("interest=", "price=", "distance=", "pace=", "signal=", "total="):
        assert name in message
    assert "private" not in message


def test_the_score_uses_the_renormalised_pm_1_weights() -> None:
    candidate = fake(cost=Decimal("0.00"), typical_duration_min=180, tags=["history"])
    ctx = context([candidate], budget="90.00", interests=["history"], pace=pm.Pace.BUSY)
    parts = ranking.score(candidate, ctx)
    assert (parts.interest, parts.price, parts.distance, parts.pace) == (1, 1, 1, 1)
    assert parts.signal == 0
    assert parts.total == pytest.approx(1)


def test_saving_moves_weight_from_interest_to_price() -> None:
    match = fake(tags=["history"], cost=Decimal("100.00"), id=uuid.UUID(int=1))
    cheap = fake(cost=Decimal("0.00"), id=uuid.UUID(int=2))
    both = [match, cheap]
    balanced = context(both, budget="90.00", interests=["history"])
    saving = context(
        both, budget="90.00", interests=["history"], budget_priority=pm.BudgetPriority.SAVING
    )
    assert ranking.rank_shortlist(both, balanced).entries[0].candidate is match
    assert ranking.score(cheap, saving).total > ranking.score(cheap, balanced).total
    assert ranking.score(match, saving).total < ranking.score(match, balanced).total


@pytest.mark.parametrize(
    ("cost", "budget", "expected"),
    [
        ("6.00", "90.00", 1.0),  # share = 90 / (3 days x 5 items) = 6
        ("9.00", "90.00", 0.5),
        ("12.00", "90.00", 0.0),
        ("30.00", "90.00", 0.0),
        (None, "90.00", 0.5),
        ("6.00", None, 0.5),
        ("0.00", "0.00", 1.0),
        ("1.00", "0.00", 0.0),
    ],
)
def test_the_price_component(cost: str | None, budget: str | None, expected: float) -> None:
    candidate = fake(cost=Decimal(cost) if cost else None)
    assert ranking.score(candidate, context([candidate], budget=budget)).price == expected


def test_distance_runs_from_the_must_visit_centroid_or_the_destination_centre() -> None:
    far = fake(lat=Decimal("53.95"), lon=Decimal("2.3"))
    centre = fake()
    assert ranking.score(centre, context([far, centre])).distance == 1
    assert ranking.score(far, context([far, centre])).distance < 0.5
    must = fake(lat=far.place.lat, lon=far.place.lon, must_visit=True)
    assert ranking.score(far, context([must, centre])).distance == 1


def test_a_relaxed_pace_lowers_long_visits() -> None:
    long_visit = fake(typical_duration_min=180)
    relaxed = ranking.score(long_visit, context([long_visit], pace=pm.Pace.RELAXED))
    busy = ranking.score(long_visit, context([long_visit], pace=pm.Pace.BUSY))
    assert (relaxed.pace, busy.pace) == (0.5, 1)


@pytest.mark.parametrize(("days", "size"), [(1, 12), (2, 16), (3, 24), (5, 40), (14, 40)])
def test_the_shortlist_size_rule(days: int, size: int) -> None:
    assert ranking.shortlist_size(days) == size
    candidates = [fake(category="sight") for _ in range(60)]
    ctx = context(candidates, days=days, meals=0)
    assert len(ranking.rank_shortlist(candidates, ctx).entries) == size


def test_must_visit_and_food_places_are_added_beyond_the_cut() -> None:
    near = [fake(tags=["history"]) for _ in range(12)]
    must = fake(lat=Decimal("53.85"), lon=Decimal("2.1"), must_visit=True)
    food = [fake(category="food", lat=Decimal("53.95"), lon=Decimal("2.3")) for _ in range(5)]
    candidates = [*near, must, *food]
    ctx = context(candidates, days=1, meals=2, interests=["history"])
    ctx = ranking.RankingContext(**{**vars(ctx), "centre_lat": 53.9, "centre_lon": 2.2})
    kept = [entry.candidate for entry in ranking.rank_shortlist(candidates, ctx).entries]
    assert must in kept
    assert sum(c.place.category == "food" for c in kept) == 2
    assert len(kept) == 15
    totals = [ranking.score(c, ctx).total for c in kept[:12]]
    assert totals == sorted(totals, reverse=True)


def test_stay_is_left_out_unless_it_is_a_must_visit_place() -> None:
    stay, named = fake(category="stay"), fake(category="stay", must_visit=True)
    candidates = [stay, named, fake()]
    kept = [e.candidate for e in ranking.rank_shortlist(candidates, context(candidates)).entries]
    assert stay not in kept
    assert named in kept


def test_the_mapping_version_is_exposed() -> None:
    assert ranking.rank_shortlist([], context([])).mapping_version == "pm-1"


def test_sample_ranking_keeps_the_size_rule_food_and_must_visit() -> None:
    candidates = sample_candidates(must_visit=("sample-030",))
    ctx = context(candidates, days=1, budget="120.00", meals=1, interests=["museum", "nature"])
    entries = ranking.rank_shortlist(candidates, ctx).entries
    refs = [entry.candidate.place.ref for entry in entries]
    assert len(refs) == len(set(refs))
    assert "sample-030" in refs
    assert len(refs) in (12, 13)  # the size rule, plus the must-visit place if it ranks lower
    assert sum(e.candidate.place.category == "food" for e in entries) >= 1
    assert ranking.rank_shortlist(candidates, ctx).entries == entries


def test_sample_three_day_trip_keeps_all_the_size_rule_allows() -> None:
    candidates = sample_candidates()
    ctx = context(candidates, days=3, budget="300.00", interests=["museum"])
    assert len(ranking.rank_shortlist(candidates, ctx).entries) == 24
