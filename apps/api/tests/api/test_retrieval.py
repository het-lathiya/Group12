"""Candidate retrieval and hard filters on Sampleton (§8.9; FR-027: TC-123, TC-124, TC-125).

Runs against the migrated test database with Sampleton loaded through the seed; every test is
rolled back. The trip and preferences are plain stand-ins, so no budget_settings row exists unless
a test goes through ``activity_budget`` directly.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DataSource, Destination, Place
from app.generation import retrieval
from app.places import repository, seed

REPO_ROOT = Path(__file__).resolve().parents[4]
SAMPLETON = REPO_ROOT / "data" / "fixtures" / "sampleton"
MONDAY = date(2027, 3, 1)


@pytest_asyncio.fixture
async def sampleton(db_session: AsyncSession) -> Destination:
    await seed.load_fixture(db_session, seed.read_fixture(SAMPLETON))
    destination = await db_session.scalar(
        select(Destination).where(Destination.slug == "sampleton")
    )
    assert destination is not None
    return destination


@pytest_asyncio.fixture
async def by_ref(db_session: AsyncSession, sampleton: Destination) -> dict[str, Place]:
    places = await db_session.scalars(select(Place).where(Place.destination_id == sampleton.id))
    return {str(place.external_ref): place for place in places}


def trip_for(destination: Destination, **overrides: Any) -> Any:
    values: dict[str, Any] = {
        "id": uuid.uuid4(),
        "destination_id": destination.id,
        "start_date": MONDAY,
        "num_days": 7,
        "adults": 2,
        "children": 0,
        "budget": None,
    }
    return SimpleNamespace(**(values | overrides))


def money(amount: str) -> SimpleNamespace:
    return SimpleNamespace(amount=Decimal(amount), currency="GBP")


def prefs(*, step_free: bool = False) -> Any:
    return SimpleNamespace(step_free_required=step_free)


@pytest.mark.asyncio
async def test_candidates_reads_active_places_with_their_hours(
    db_session: AsyncSession, sampleton: Destination, by_ref: dict[str, Place]
) -> None:
    by_ref["sample-001"].is_active = False
    await db_session.flush()
    rows = await repository.candidates(db_session, sampleton.id)
    assert len(rows) == 29
    assert by_ref["sample-001"].id not in {place.id for place, _ in rows}
    hours = next(h for place, h in rows if place.external_ref == "sample-005")
    assert [row.weekday for row in hours] == sorted(row.weekday for row in hours)
    assert [row.weekday for row in hours if row.is_closed] == [1]


@pytest.mark.asyncio
async def test_tc_123_step_free_trips_hold_only_step_free_places(
    db_session: AsyncSession, sampleton: Destination
) -> None:
    candidates = await retrieval.retrieve_candidates(
        db_session, trip_for(sampleton), prefs(step_free=True), []
    )
    assert candidates
    assert {c.place.step_free for c in candidates} == {True}  # unknown is unsuitable


@pytest.mark.asyncio
async def test_tc_124_a_must_visit_place_failing_a_filter_stays_with_a_note(
    db_session: AsyncSession, sampleton: Destination, by_ref: dict[str, Place]
) -> None:
    place = by_ref["sample-004"]  # step_free false
    candidates = await retrieval.retrieve_candidates(
        db_session, trip_for(sampleton), prefs(step_free=True), [place.id]
    )
    kept = next(c for c in candidates if c.place.id == place.id)
    assert kept.must_visit is True
    assert kept.conflict_note == retrieval.NOTE_STEP_FREE
    others = [c for c in candidates if c.place.id != place.id]
    assert all(c.conflict_note is None and not c.must_visit for c in others)


@pytest.mark.asyncio
async def test_tc_125_every_candidate_id_exists_in_places(
    db_session: AsyncSession, sampleton: Destination
) -> None:
    candidates = await retrieval.retrieve_candidates(db_session, trip_for(sampleton), prefs(), [])
    ids = {c.place.id for c in candidates}
    assert len(ids) == len(candidates) == 30
    stored = await db_session.scalars(select(Place.id).where(Place.id.in_(ids)))
    assert set(stored) == ids


@pytest.mark.asyncio
async def test_a_place_of_excluded_category_is_removed_unless_must_visit(
    db_session: AsyncSession, sampleton: Destination, by_ref: dict[str, Place]
) -> None:
    source_id = (await db_session.scalars(select(DataSource.id))).first()
    stay = Place(
        destination_id=sampleton.id,
        source_id=source_id,
        external_ref="stay-1",
        name="Sample Stay (sample)",
        category="stay",
        lat=Decimal("53.9"),
        lon=Decimal("2.2"),
        typical_duration_min=60,
    )
    db_session.add(stay)
    await db_session.flush()
    trip = trip_for(sampleton)
    assert stay.id not in {
        c.place.id for c in await retrieval.retrieve_candidates(db_session, trip, prefs(), [])
    }
    kept = await retrieval.retrieve_candidates(db_session, trip, prefs(), [stay.id])
    assert next(c for c in kept if c.place.id == stay.id).conflict_note == retrieval.NOTE_CATEGORY


@pytest.mark.asyncio
async def test_closed_means_an_explicit_closed_row_on_every_trip_day(
    db_session: AsyncSession, sampleton: Destination, by_ref: dict[str, Place]
) -> None:
    closed_monday = by_ref["sample-005"].id
    one_monday = trip_for(sampleton, num_days=1)
    ids = {
        c.place.id for c in await retrieval.retrieve_candidates(db_session, one_monday, prefs(), [])
    }
    assert closed_monday not in ids
    two_days = trip_for(sampleton, num_days=2)
    ids = {
        c.place.id for c in await retrieval.retrieve_candidates(db_session, two_days, prefs(), [])
    }
    assert closed_monday in ids
    tuesday = trip_for(sampleton, start_date=MONDAY + timedelta(days=1), num_days=1)
    kept = await retrieval.retrieve_candidates(db_session, one_monday, prefs(), [closed_monday])
    assert next(c for c in kept if c.place.id == closed_monday).conflict_note == (
        retrieval.NOTE_CLOSED
    )
    ids = {
        c.place.id for c in await retrieval.retrieve_candidates(db_session, tuesday, prefs(), [])
    }
    assert closed_monday in ids


@pytest.mark.asyncio
async def test_a_place_costing_more_than_the_activity_budget_is_removed(
    db_session: AsyncSession, sampleton: Destination, by_ref: dict[str, Place]
) -> None:
    # Budget 33.00 with 10 % contingency leaves 30.00; the kayak costs 2 x 20.00 at least.
    trip = trip_for(sampleton, budget=money("33.00"))
    kayak, unpriced = by_ref["sample-028"], by_ref["sample-007"]
    candidates = await retrieval.retrieve_candidates(db_session, trip, prefs(), [])
    ids = {c.place.id for c in candidates}
    assert kayak.id not in ids
    assert unpriced.id in ids  # no price is never a budget failure
    kept = await retrieval.retrieve_candidates(db_session, trip, prefs(), [kayak.id])
    conflict = next(c for c in kept if c.place.id == kayak.id)
    assert conflict.conflict_note == retrieval.NOTE_OVER_BUDGET
    assert conflict.min_group_cost == Decimal("40.00")


@pytest.mark.asyncio
async def test_children_keep_unknown_places_and_lose_unsuitable_ones(
    db_session: AsyncSession, sampleton: Destination, by_ref: dict[str, Place]
) -> None:
    trip = trip_for(sampleton, children=1)
    ids = {c.place.id for c in await retrieval.retrieve_candidates(db_session, trip, prefs(), [])}
    assert by_ref["sample-008"].id not in ids  # child_friendly false
    assert by_ref["sample-003"].id in ids  # unknown is never read as false


@pytest.mark.parametrize(
    ("budget", "days", "transport", "stay", "pct", "expected"),
    [
        (None, 3, None, None, "10", None),
        ("110.00", 1, None, None, "10", "100.00"),
        ("220.00", 3, "10.00", "20.00", "10", "130.00"),
        ("100.00", 2, "60.00", None, "0", "0.00"),
    ],
)
def test_activity_budget(
    budget: str | None,
    days: int,
    transport: str | None,
    stay: str | None,
    pct: str,
    expected: str | None,
) -> None:
    result = retrieval.activity_budget(
        Decimal(budget) if budget else None,
        num_days=days,
        transport_per_day=Decimal(transport) if transport else None,
        stay_per_night=Decimal(stay) if stay else None,
        contingency_pct=Decimal(pct),
    )
    assert result == (Decimal(expected) if expected else None)


@pytest.mark.parametrize(
    ("tags", "currency", "expected"),
    [
        ([], "GBP", "30.00"),
        (["child_half"], "GBP", "25.00"),
        (["child_free"], "GBP", "20.00"),
        (["price_per_group"], "GBP", "10.00"),
        ([], "EUR", None),
    ],
)
def test_min_group_cost(tags: list[str], currency: str, expected: str | None) -> None:
    # 2 adults and 1 child at 10.00, in the rules of §9.3.1 BF-01, BF-02 and BF-04.
    place: Any = SimpleNamespace(price_min=Decimal("10.00"), price_currency="GBP", tags=tags)
    result = retrieval.min_group_cost(place, adults=2, children=1, currency=currency)
    assert result == (Decimal(expected) if expected else None)
