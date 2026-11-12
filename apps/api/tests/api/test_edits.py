"""The edit transaction core, ``app.itinerary.edits.apply_edit`` (IMP-407; §5.8, §6.6.5; FR-064:
TC-206, TC-207, TC-312; IMD-18, IMD-23; A1 §6.10).

The routes (API-25 to API-29) are later cards, so the core is called directly on the test's
session, inside a savepoint that stands in for the request's transaction. The plan comes from
API-22 in mode rule_based (no provider call) with the MOCK job path, as in test_itinerary.py.
"""

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import time
from pathlib import Path
from typing import Any

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from fixtures.auth import AuthUser
from fixtures.db import insert_auth_user
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.factory import get_model_provider
from app.ai.providers.base import ModelProvider
from app.ai.providers.mock import MockProvider
from app.core.errors import GenerationInProgress, InvalidEdit, NotFound, StalePlan
from app.db.models import (
    Destination,
    ItineraryItem,
    ItineraryVersion,
    ItineraryWarning,
    Place,
    Trip,
)
from app.generation import jobs, records
from app.generation import repository as generation_repository
from app.itinerary import edits
from app.itinerary.edits import Add, Lock, Move, Remove, Replace, Retime
from app.itinerary.schemas import EditResultOut
from app.places import seed

REPOSITORY = Path(__file__).resolve().parents[4]
SAMPLETON = REPOSITORY / "data" / "fixtures" / "sampleton"

Queue = list[tuple[uuid.UUID, ModelProvider]]


@pytest_asyncio.fixture
async def destination(db_session: AsyncSession) -> Destination:
    await seed.load_fixture(db_session, seed.read_fixture(SAMPLETON))
    row = await db_session.scalar(select(Destination).where(Destination.slug == "sampleton"))
    assert row is not None
    return row


@pytest.fixture
def jobs_queue(api_app: FastAPI) -> Queue:
    queue: Queue = []
    api_app.dependency_overrides[jobs.get_submit] = lambda: lambda g, p: queue.append((g, p))
    api_app.dependency_overrides[get_model_provider] = lambda: MockProvider("ok", app_env="test")
    return queue


async def planned_trip(
    client: httpx.AsyncClient,
    session: AsyncSession,
    queue: Queue,
    user: AuthUser,
    destination: Destination,
    end_date: str = "2026-12-06",
) -> uuid.UUID:
    """A trip from 4 December with a saved rule-based plan."""
    created = await client.post(
        "/api/v1/trips",
        json={
            "title": "Edits in Sampleton",
            "destination_id": str(destination.id),
            "start_date": "2026-12-04",
            "end_date": end_date,
            "adults": 2,
        },
        headers=user.headers,
    )
    assert created.status_code == 201, created.text
    trip_id = created.json()["id"]
    saved = await client.put(
        f"/api/v1/trips/{trip_id}/preferences",
        json={"interests": ["museum", "food", "nature"], "must_visit_place_ids": []},
        headers=user.headers,
    )
    assert saved.status_code == 200, saved.text
    started = await client.post(
        f"/api/v1/trips/{trip_id}/generations", json={"mode": "rule_based"}, headers=user.headers
    )
    assert started.status_code == 202, started.text

    @asynccontextmanager
    async def job_transaction() -> AsyncIterator[AsyncSession]:
        async with session.begin_nested():
            yield session

    while queue:
        await jobs.run(*queue.pop(0), job_transaction)
    return uuid.UUID(trip_id)


async def items(session: AsyncSession, trip_id: uuid.UUID) -> list[ItineraryItem]:
    """The trip's items in day and position order, read fresh."""
    session.expire_all()
    rows = await session.scalars(
        select(ItineraryItem)
        .where(ItineraryItem.trip_id == trip_id)
        .order_by(ItineraryItem.day_id, ItineraryItem.position)
    )
    return list(rows)


async def revision(session: AsyncSession, trip_id: uuid.UUID) -> int:
    value = await session.scalar(select(Trip.plan_revision).where(Trip.id == trip_id))
    assert value is not None
    return value


async def state(session: AsyncSession, trip_id: uuid.UUID) -> dict[str, Any]:
    """Everything an edit writes, to compare before and after a refused or failed edit."""
    rows = await items(session, trip_id)
    versions = await session.scalar(
        select(func.count())
        .select_from(ItineraryVersion)
        .where(ItineraryVersion.trip_id == trip_id)
    )
    warnings = await session.scalar(
        select(func.count())
        .select_from(ItineraryWarning)
        .where(ItineraryWarning.trip_id == trip_id)
    )
    return {
        "revision": await revision(session, trip_id),
        "items": [
            (i.id, i.day_id, i.position, i.place_id, i.start_time, i.duration_min, i.is_locked)
            for i in rows
        ],
        "versions": versions,
        "warnings": warnings,
    }


async def edit(
    session: AsyncSession, user: AuthUser, trip_id: uuid.UUID, op: edits.EditOperation
) -> EditResultOut:
    """One edit on the current revision, in its own savepoint (the request's transaction)."""
    base = await revision(session, trip_id)
    async with session.begin_nested():
        return await edits.apply_edit(session, user.user_id, trip_id, base, op)


async def unplanned_place(session: AsyncSession, trip_id: uuid.UUID) -> Place:
    trip = await session.get(Trip, trip_id)
    assert trip is not None
    planned = select(ItineraryItem.place_id).where(ItineraryItem.trip_id == trip_id)
    place = await session.scalar(
        select(Place)
        .where(
            Place.destination_id == trip.destination_id,
            Place.is_active.is_(True),
            Place.id.not_in(planned),
        )
        .order_by(Place.name)
        .limit(1)
    )
    assert place is not None
    return place


def minutes(clock: time) -> int:
    return clock.hour * 60 + clock.minute


# FR-064 AC1, TC-206: every operation recalculates, revalidates and moves the revision on


@pytest.mark.asyncio
async def test_tc_206_every_edit_returns_recalculated_totals_findings_and_a_new_revision(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    first = (await items(db_session, trip_id))[0]
    newcomer = await unplanned_place(db_session, trip_id)
    operations: list[edits.EditOperation] = [
        Retime(first.id, duration_min=first.duration_min + 30),
        Add(1, newcomer.id),
        Move(first.id, 2, 1),
        Lock(first.id, True),
        Lock(first.id, False),
        Replace(first.id, (await unplanned_place(db_session, trip_id)).id),
        Remove(first.id),
    ]
    base = await revision(db_session, trip_id)
    url = f"/api/v1/trips/{trip_id}/itinerary"

    for count, operation in enumerate(operations, start=1):
        result = await edit(db_session, auth_user, trip_id, operation)

        assert result.plan_revision == base + count
        assert result.changed_days, operation
        current = (await api_client.get(url, headers=auth_user.headers)).json()
        assert current["plan_revision"] == result.plan_revision
        assert result.model_dump(mode="json")["totals"] == current["totals"]
        assert result.model_dump(mode="json")["findings"] == current["findings"]
        by_number = {day["day_number"]: day for day in current["days"]}
        for day in result.model_dump(mode="json")["changed_days"]:
            assert day == by_number[day["day_number"]]

    versions = await db_session.scalars(
        select(ItineraryVersion.reason, ItineraryVersion.plan_revision)
        .where(ItineraryVersion.trip_id == trip_id, ItineraryVersion.reason == "edit")
        .order_by(ItineraryVersion.version_no)
    )
    assert list(versions) == ["edit"] * len(operations)  # IMD-18: one automatic version each
    assert first.id not in {item.id for item in await items(db_session, trip_id)}


@pytest.mark.asyncio
async def test_edits_an_added_place_is_priced_and_follows_the_previous_item(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    newcomer = await unplanned_place(db_session, trip_id)

    result = await edit(db_session, auth_user, trip_id, Add(1, newcomer.id))

    day = next(d for d in result.changed_days if d.day_number == 1)
    previous, added = day.items[-2], day.items[-1]
    assert added.place.id == newcomer.id
    assert (added.origin, added.note, added.note_origin) == ("user", None, "none")
    assert added.duration_min == newcomer.typical_duration_min
    assert added.travel_from_previous is not None
    gap = minutes(time.fromisoformat(added.start_time)) - minutes(
        time.fromisoformat(previous.end_time)
    )
    assert gap >= added.travel_from_previous.minutes  # travel plus its buffer
    if newcomer.price_min is not None:
        assert added.cost is not None


@pytest.mark.asyncio
async def test_edits_a_move_shifts_the_following_start_times_and_renumbers(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    url = f"/api/v1/trips/{trip_id}/itinerary"
    days = (await api_client.get(url, headers=auth_user.headers)).json()["days"]
    moving = days[1]["items"][-1]

    result = await edit(db_session, auth_user, trip_id, Move(uuid.UUID(moving["id"]), 1, 1))

    assert {day.day_number for day in result.changed_days} == {1, 2}
    day_one = next(d for d in result.changed_days if d.day_number == 1)
    assert day_one.items[0].id == uuid.UUID(moving["id"])
    assert day_one.items[0].start_time == days[0]["items"][0]["start_time"]  # its new slot
    assert [item.position for item in day_one.items] == list(range(1, len(day_one.items) + 1))
    assert not [f for f in result.findings if f.code == "OVERLAP" and f.day_number == 1]


@pytest.mark.asyncio
async def test_edits_a_conflicting_retime_is_saved_and_reported(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    first, second = (await items(db_session, trip_id))[:2]
    assert first.day_id == second.day_id
    base = await revision(db_session, trip_id)

    result = await edit(
        db_session, auth_user, trip_id, Retime(second.id, start_time=first.start_time)
    )

    assert result.plan_revision == base + 1  # PR-06: accepted, not refused
    overlap = [f for f in result.findings if f.code == "OVERLAP"]
    assert overlap
    assert overlap[0].item_id == second.id
    assert overlap[0].suggested_fix
    stored = await db_session.scalars(
        select(ItineraryWarning.code).where(
            ItineraryWarning.trip_id == trip_id, ItineraryWarning.plan_revision == base + 1
        )
    )
    assert "OVERLAP" in list(stored)


@pytest.mark.asyncio
async def test_edits_kept_items_keep_their_citations(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    first, second = (await items(db_session, trip_id))[:2]
    cited = [uuid.uuid4(), uuid.uuid4()]
    await db_session.execute(
        update(ItineraryItem).where(ItineraryItem.id == second.id).values(source_chunk_ids=cited)
    )

    await edit(
        db_session, auth_user, trip_id, Retime(first.id, duration_min=first.duration_min + 15)
    )
    await edit(db_session, auth_user, trip_id, Move(second.id, 2, 1))

    kept = next(item for item in await items(db_session, trip_id) if item.id == second.id)
    assert kept.source_chunk_ids == cited  # A1 §6.10
    version = await db_session.scalar(
        select(ItineraryVersion)
        .where(ItineraryVersion.trip_id == trip_id)
        .order_by(ItineraryVersion.version_no.desc())
        .limit(1)
    )
    assert version is not None
    snapshot_items = [item for day in version.snapshot["days"] for item in day["items"]]
    assert [str(c) for c in cited] in [item["source_chunk_ids"] for item in snapshot_items]


# Refusals: nothing changes


@pytest.mark.asyncio
async def test_edits_a_stale_revision_is_refused_and_nothing_changes(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    first = (await items(db_session, trip_id))[0]
    before = await state(db_session, trip_id)

    with pytest.raises(StalePlan):
        async with db_session.begin_nested():
            await edits.apply_edit(
                db_session, auth_user.user_id, trip_id, before["revision"] - 1, Remove(first.id)
            )

    assert await state(db_session, trip_id) == before


@pytest.mark.asyncio
async def test_edits_an_active_generation_is_refused_before_the_revision_check(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    first = (await items(db_session, trip_id))[0]
    await generation_repository.create_queued(
        db_session,
        trip_id=trip_id,
        user_id=auth_user.user_id,
        provider="MOCK",
        model_id="mock-v1",
        prompt_template_id="itinerary_generate",
        prompt_version="v1",
        mapping_version="pm-2",
        scope="full",
        request_hash=records.request_hash({"trip_id": str(trip_id), "mode": "ai"}),
    )
    before = await state(db_session, trip_id)

    for base in (before["revision"], before["revision"] - 1):  # IMD-23: even when also stale
        with pytest.raises(GenerationInProgress):
            async with db_session.begin_nested():
                await edits.apply_edit(
                    db_session, auth_user.user_id, trip_id, base, Remove(first.id)
                )

    assert await state(db_session, trip_id) == before


@pytest.mark.asyncio
async def test_edits_structurally_impossible_edits_are_invalid_and_change_nothing(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    first = (await items(db_session, trip_id))[0].id
    await edit(db_session, auth_user, trip_id, Lock(first, True))
    newcomer = (await unplanned_place(db_session, trip_id)).id  # ids: a rollback expires rows
    before = await state(db_session, trip_id)
    impossible: list[edits.EditOperation] = [
        Add(4, newcomer),  # day out of range (3-day trip)
        Add(1, uuid.uuid4()),  # unknown place
        Add(1, newcomer, position=99),  # position out of range
        Move(first, 2, 1),  # moving a locked item
        Retime(first, start_time=time(15, 0)),  # retiming a locked item
        Replace(first, newcomer),  # replacing a locked item
        Remove(uuid.uuid4()),  # not in the plan
    ]

    for operation in impossible:
        with pytest.raises(InvalidEdit):
            async with db_session.begin_nested():
                await edits.apply_edit(
                    db_session, auth_user.user_id, trip_id, before["revision"], operation
                )

    assert await state(db_session, trip_id) == before


@pytest.mark.asyncio
async def test_edits_another_users_trip_is_not_found(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    first = (await items(db_session, trip_id))[0]
    other = uuid.uuid4()
    await insert_auth_user(db_session, other)
    before = await state(db_session, trip_id)

    with pytest.raises(NotFound):
        async with db_session.begin_nested():
            await edits.apply_edit(db_session, other, trip_id, before["revision"], Remove(first.id))

    assert await state(db_session, trip_id) == before


# FR-064 AC2, TC-207, TC-312: a failure inside the transaction leaves consistent data


@pytest.mark.parametrize("failing", ["validate", "insert_warnings", "insert_version"])
@pytest.mark.asyncio
async def test_tc_207_tc_312_a_failure_inside_the_edit_leaves_the_plan_as_it_was(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
    monkeypatch: pytest.MonkeyPatch,
    failing: str,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    first, second = (await items(db_session, trip_id))[:2]
    before = await state(db_session, trip_id)

    def fault(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError(f"injected fault in {failing}")

    target = edits.validator if failing == "validate" else edits.repository
    monkeypatch.setattr(target, failing, fault)

    with pytest.raises(RuntimeError, match="injected fault"):
        async with db_session.begin_nested():
            await edits.apply_edit(
                db_session, auth_user.user_id, trip_id, before["revision"], Move(second.id, 2, 1)
            )

    assert await state(db_session, trip_id) == before  # NFR-008
    monkeypatch.undo()
    result = await edit(db_session, auth_user, trip_id, Remove(first.id))
    assert result.plan_revision == before["revision"] + 1  # and the plan is still editable
