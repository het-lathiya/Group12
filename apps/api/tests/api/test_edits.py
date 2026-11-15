"""The edit transaction core, ``app.itinerary.edits.apply_edit`` (IMP-407; §5.8, §6.6.5; FR-064:
TC-206, TC-207, TC-312; IMD-18, IMD-23; A1 §6.10).

The routes (API-25 to API-29) are later cards, so the core is called directly on the test's
session, inside a savepoint that stands in for the request's transaction. The plan comes from
API-22 in mode rule_based (no provider call) with the MOCK job path, as in test_itinerary.py.
"""

import uuid
from collections.abc import AsyncIterator, Iterator
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
from app.core.config import get_settings
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
    must_visit: tuple[uuid.UUID, ...] = (),
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
        json={
            "interests": ["museum", "food", "nature"],
            "must_visit_place_ids": [str(place_id) for place_id in must_visit],
        },
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


# The routes API-26 and API-27 (IMP-408, IMP-409): bodies go through apply_edit unchanged


async def route_state(
    client: httpx.AsyncClient, user: AuthUser, trip_id: uuid.UUID
) -> dict[str, Any]:
    response = await client.get(f"/api/v1/trips/{trip_id}/itinerary", headers=user.headers)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def assert_matches_itinerary(result: dict[str, Any], current: dict[str, Any]) -> None:
    """The edit response equals API-24 read straight after it (totals, findings, changed days)."""
    assert result["plan_revision"] == current["plan_revision"]
    assert result["totals"] == current["totals"]
    assert result["findings"] == current["findings"]
    by_number = {day["day_number"]: day for day in current["days"]}
    for day in result["changed_days"]:
        assert day == by_number[day["day_number"]]


def item_url(item_id: Any) -> str:
    return f"/api/v1/itinerary/items/{item_id}"


# FR-061 AC1, TC-200


@pytest.mark.asyncio
async def test_tc_200_remove_route_recomputes_the_day_and_totals(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    before = await route_state(api_client, auth_user, trip_id)
    day_one = before["days"][0]["items"]
    removed = day_one[0]

    response = await api_client.delete(
        item_url(removed["id"]),
        params={"plan_revision": before["plan_revision"]},
        headers=auth_user.headers,
    )

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["plan_revision"] == before["plan_revision"] + 1
    assert [day["day_number"] for day in result["changed_days"]] == [1]
    left = result["changed_days"][0]["items"]
    assert [item["id"] for item in left] == [item["id"] for item in day_one[1:]]
    assert [item["position"] for item in left] == list(range(1, len(left) + 1))
    assert left[0]["travel_from_previous"] is None  # the new first item has no travel leg
    assert_matches_itinerary(result, await route_state(api_client, auth_user, trip_id))


# FR-061 AC2, TC-201


@pytest.mark.asyncio
async def test_tc_201_remove_route_reports_a_removed_must_visit_place(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    must = await db_session.scalar(
        select(Place)
        .where(Place.destination_id == destination.id, Place.is_active.is_(True))
        .order_by(Place.name)
        .limit(1)
    )
    assert must is not None
    trip_id = await planned_trip(
        api_client, db_session, jobs_queue, auth_user, destination, must_visit=(must.id,)
    )
    before = await route_state(api_client, auth_user, trip_id)
    assert "MUST_VISIT_MISSING" not in {f["code"] for f in before["findings"]}
    item = next(
        i for day in before["days"] for i in day["items"] if i["place"]["id"] == str(must.id)
    )

    response = await api_client.delete(
        item_url(item["id"]),
        params={"plan_revision": before["plan_revision"]},
        headers=auth_user.headers,
    )

    assert response.status_code == 200, response.text
    missing = [f for f in response.json()["findings"] if f["code"] == "MUST_VISIT_MISSING"]
    assert missing
    assert must.name in missing[0]["message"]


# FR-063 AC1, TC-204


@pytest.mark.asyncio
async def test_tc_204_retime_route_saves_the_new_values_and_flags_the_conflict(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    before = await route_state(api_client, auth_user, trip_id)
    first, second = before["days"][0]["items"][:2]

    response = await api_client.patch(
        item_url(first["id"]),
        json={"plan_revision": before["plan_revision"], "start_time": "10:15", "duration_min": 480},
        headers=auth_user.headers,
    )

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["plan_revision"] == before["plan_revision"] + 1
    retimed = result["changed_days"][0]["items"][0]
    assert (retimed["id"], retimed["start_time"], retimed["duration_min"]) == (
        first["id"],
        "10:15",
        480,
    )
    # PD-IMP-407-3: a retime keeps the traveller's values; the clash is a finding, not a refusal.
    assert [
        f for f in result["findings"] if f["code"] == "OVERLAP" and f["item_id"] == second["id"]
    ]
    assert_matches_itinerary(result, await route_state(api_client, auth_user, trip_id))


# FR-063 AC2, TC-205


@pytest.mark.parametrize("duration", [14, 481])
@pytest.mark.asyncio
async def test_tc_205_retime_route_refuses_a_duration_outside_15_to_480(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
    duration: int,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    first = (await items(db_session, trip_id))[0]
    before = await state(db_session, trip_id)

    response = await api_client.patch(
        item_url(first.id),
        json={"plan_revision": before["revision"], "duration_min": duration},
        headers=auth_user.headers,
    )

    assert response.status_code == 422, response.text
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["request_id"]
    assert await state(db_session, trip_id) == before


@pytest.mark.parametrize("method", ["retime", "remove"])
@pytest.mark.asyncio
async def test_retime_and_remove_routes_answer_another_users_item_with_not_found(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
    method: str,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    first = (await items(db_session, trip_id))[0]
    other = AuthUser(user_id=uuid.uuid4(), email="other@example.test")
    await insert_auth_user(db_session, other.user_id)
    before = await state(db_session, trip_id)

    if method == "retime":
        response = await api_client.patch(
            item_url(first.id),
            json={"plan_revision": before["revision"], "duration_min": 60},
            headers=other.headers,
        )
    else:
        response = await api_client.delete(
            item_url(first.id), params={"plan_revision": before["revision"]}, headers=other.headers
        )

    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert await state(db_session, trip_id) == before


@pytest.mark.asyncio
async def test_remove_and_retime_routes_refuse_a_stale_revision_or_an_active_generation(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    first = (await items(db_session, trip_id))[0]
    before = await state(db_session, trip_id)

    stale = await api_client.delete(
        item_url(first.id),
        params={"plan_revision": before["revision"] - 1},
        headers=auth_user.headers,
    )
    assert stale.status_code == 409, stale.text
    assert stale.json()["error"]["code"] == "STALE_PLAN"

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
    busy = await api_client.patch(
        item_url(first.id),
        json={"plan_revision": before["revision"], "duration_min": 60},
        headers=auth_user.headers,
    )
    assert busy.status_code == 409, busy.text
    assert busy.json()["error"]["code"] == "GENERATION_IN_PROGRESS"
    assert await state(db_session, trip_id) == before


@pytest.mark.parametrize(
    ("body", "status_code", "code"),
    [
        ({}, 422, "INVALID_EDIT"),  # nothing to change
    ],
)
@pytest.mark.asyncio
async def test_retime_route_refuses_a_body_without_a_retime(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
    body: dict[str, Any],
    status_code: int,
    code: str,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    first = (await items(db_session, trip_id))[0]
    before = await state(db_session, trip_id)

    response = await api_client.patch(
        item_url(first.id),
        json={"plan_revision": before["revision"], **body},
        headers=auth_user.headers,
    )

    assert response.status_code == status_code, response.text
    assert response.json()["error"]["code"] == code
    assert await state(db_session, trip_id) == before


# FR-060 (server side): API-26 move


@pytest.mark.asyncio
async def test_move_route_across_days_keeps_positions_dense_in_both_days(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    before = await route_state(api_client, auth_user, trip_id)
    moving = before["days"][1]["items"][0]

    response = await api_client.patch(
        item_url(moving["id"]),
        json={"plan_revision": before["plan_revision"], "day_number": 1, "position": 2},
        headers=auth_user.headers,
    )

    assert response.status_code == 200, response.text
    result = response.json()
    days = {day["day_number"]: day["items"] for day in result["changed_days"]}
    assert set(days) == {1, 2}
    assert days[1][1]["id"] == moving["id"]
    assert len(days[1]) == len(before["days"][0]["items"]) + 1
    assert len(days[2]) == len(before["days"][1]["items"]) - 1
    for day_items in days.values():
        assert [item["position"] for item in day_items] == list(range(1, len(day_items) + 1))
    assert_matches_itinerary(result, await route_state(api_client, auth_user, trip_id))


@pytest.mark.asyncio
async def test_move_route_within_a_day_and_to_the_end_of_a_day(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    before = await route_state(api_client, auth_user, trip_id)
    first, second = before["days"][0]["items"][:2]

    down = await api_client.patch(  # position only: stays on its day
        item_url(first["id"]),
        json={"plan_revision": before["plan_revision"], "position": 2},
        headers=auth_user.headers,
    )
    assert down.status_code == 200, down.text
    day_one = down.json()["changed_days"][0]["items"]
    assert [item["id"] for item in day_one[:2]] == [second["id"], first["id"]]

    last = await api_client.patch(  # day only: after that day's last item
        item_url(second["id"]),
        json={"plan_revision": down.json()["plan_revision"], "day_number": 2},
        headers=auth_user.headers,
    )
    assert last.status_code == 200, last.text
    day_two = next(d for d in last.json()["changed_days"] if d["day_number"] == 2)["items"]
    assert day_two[-1]["id"] == second["id"]


# FR-060 AC3, TC-199


@pytest.mark.asyncio
async def test_tc_199_move_route_saves_a_conflicting_move_and_reports_it(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    before = await route_state(api_client, auth_user, trip_id)
    codes_before = {f["code"] for f in before["findings"] if f["day_number"] == 1}
    revision_now = before["plan_revision"]
    moved = [item["id"] for day in before["days"][1:] for item in day["items"]]

    for item_id in moved:  # every later item onto day 1: more than the pace allows
        response = await api_client.patch(
            item_url(item_id),
            json={"plan_revision": revision_now, "day_number": 1},
            headers=auth_user.headers,
        )
        assert response.status_code == 200, response.text  # never refused, never reverted
        revision_now = response.json()["plan_revision"]

    result = response.json()
    new_codes = {f["code"] for f in result["findings"] if f["day_number"] == 1} - codes_before
    assert new_codes & {"DAY_TOO_LONG", "OVERLAP", "CLOSED_ON_DAY"}, result["findings"]
    current = await route_state(api_client, auth_user, trip_id)
    assert [item["id"] for item in current["days"][0]["items"]][-len(moved) :] == moved
    assert_matches_itinerary(result, current)


@pytest.mark.asyncio
async def test_move_route_refuses_a_stale_revision_and_changes_nothing(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    first = (await items(db_session, trip_id))[0]
    before = await state(db_session, trip_id)

    response = await api_client.patch(
        item_url(first.id),
        json={"plan_revision": before["revision"] - 1, "day_number": 2, "position": 1},
        headers=auth_user.headers,
    )

    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "STALE_PLAN"
    assert await state(db_session, trip_id) == before


@pytest.mark.parametrize(
    "body",
    [
        {"day_number": 2, "start_time": "10:00"},  # PD-IMP-409-1: move and retime together
        {"day_number": 9},  # a day the plan does not have
        {"position": 99},  # past the end of the day
    ],
)
@pytest.mark.asyncio
async def test_move_route_refuses_an_invalid_move_with_invalid_edit(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
    body: dict[str, Any],
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    first = (await items(db_session, trip_id))[0]
    before = await state(db_session, trip_id)

    response = await api_client.patch(
        item_url(first.id),
        json={"plan_revision": before["revision"], **body},
        headers=auth_user.headers,
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "INVALID_EDIT"
    assert await state(db_session, trip_id) == before


# API-25 add a place (IMP-504; FR-062, FR-069; IMD-152)


def add_url(trip_id: uuid.UUID) -> str:
    return f"/api/v1/trips/{trip_id}/itinerary/items"


def clock_minutes(value: str) -> int:
    return minutes(time.fromisoformat(value))


# FR-062 AC1, TC-202


@pytest.mark.asyncio
async def test_tc_202_add_place_route_inserts_at_a_feasible_time_and_revalidates(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    newcomer = await unplanned_place(db_session, trip_id)
    before = await route_state(api_client, auth_user, trip_id)
    day_one = before["days"][0]["items"]

    response = await api_client.post(
        add_url(trip_id),
        json={
            "plan_revision": before["plan_revision"],
            "day_number": 1,
            "place_id": str(newcomer.id),
        },
        headers=auth_user.headers,
    )

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["plan_revision"] == before["plan_revision"] + 1
    assert [day["day_number"] for day in result["changed_days"]] == [1]
    day = result["changed_days"][0]["items"]
    assert [item["id"] for item in day[:-1]] == [item["id"] for item in day_one]
    added, previous = day[-1], day[-2]
    assert added["place"]["id"] == str(newcomer.id)
    assert (added["position"], added["origin"]) == (len(day), "user")
    assert added["duration_min"] == newcomer.typical_duration_min
    # Earliest feasible time: previous end + travel (+ the buffer of that travel source).
    leg = added["travel_from_previous"]
    assert leg is not None
    assert clock_minutes(added["start_time"]) >= (
        clock_minutes(previous["end_time"]) + leg["minutes"]
    )
    assert_matches_itinerary(result, await route_state(api_client, auth_user, trip_id))


# FR-062 AC2, TC-203


@pytest.mark.asyncio
async def test_tc_203_add_place_route_keeps_a_conflicting_addition_and_reports_it(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    before = await route_state(api_client, auth_user, trip_id)
    first = before["days"][0]["items"][0]

    response = await api_client.post(  # the same place again, at the same time: no silent merge
        add_url(trip_id),
        json={
            "plan_revision": before["plan_revision"],
            "day_number": 1,
            "place_id": first["place"]["id"],
            "start_time": first["start_time"],
        },
        headers=auth_user.headers,
    )

    assert response.status_code == 200, response.text  # kept, never refused
    result = response.json()
    day = result["changed_days"][0]["items"]
    assert len(day) == len(before["days"][0]["items"]) + 1
    twins = [item for item in day if item["place"]["id"] == first["place"]["id"]]
    assert len(twins) == 2
    added = next(item for item in twins if item["id"] != first["id"])
    assert added["start_time"] == first["start_time"]
    assert [f for f in result["findings"] if f["code"] == "OVERLAP" and f["day_number"] == 1]
    assert_matches_itinerary(result, await route_state(api_client, auth_user, trip_id))


@pytest.mark.parametrize(
    ("day_number", "place", "code"),
    [
        (4, "new", "INVALID_EDIT"),  # num_days + 1 (3-day trip)
        (1, "unknown", "INVALID_EDIT"),
        (0, "new", "VALIDATION_ERROR"),  # PD-IMP-504-2: the contract bounds day_number to >= 1
    ],
)
@pytest.mark.asyncio
async def test_add_place_route_refuses_a_day_outside_the_trip_or_an_unknown_place(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
    day_number: int,
    place: str,
    code: str,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    newcomer = (await unplanned_place(db_session, trip_id)).id
    before = await state(db_session, trip_id)

    response = await api_client.post(
        add_url(trip_id),
        json={
            "plan_revision": before["revision"],
            "day_number": day_number,
            "place_id": str(newcomer if place == "new" else uuid.uuid4()),
        },
        headers=auth_user.headers,
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == code
    assert await state(db_session, trip_id) == before


@pytest.mark.asyncio
async def test_add_place_route_creates_the_row_of_a_trip_day_without_items(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    """IMD-152 (PD-IMP-407-2): the save writes only days with items; the first add makes the row."""
    trip_id = await planned_trip(
        api_client, db_session, jobs_queue, auth_user, destination, end_date="2026-12-13"
    )
    before = await route_state(api_client, auth_user, trip_id)
    planned = {day["day_number"] for day in before["days"]}
    empty = min(set(range(1, 11)) - planned)  # the 10-day SAMPLE plan leaves days without rows
    newcomer = await unplanned_place(db_session, trip_id)

    response = await api_client.post(
        add_url(trip_id),
        json={
            "plan_revision": before["plan_revision"],
            "day_number": empty,
            "place_id": str(newcomer.id),
        },
        headers=auth_user.headers,
    )

    assert response.status_code == 200, response.text
    result = response.json()
    [day] = result["changed_days"]
    assert day["day_number"] == empty
    assert day["date"] == f"2026-12-{3 + empty:02d}"
    assert [item["place"]["id"] for item in day["items"]] == [str(newcomer.id)]
    assert day["items"][0]["start_time"] == "09:00"  # §8.6 day start on an empty day
    current = await route_state(api_client, auth_user, trip_id)
    assert {d["day_number"] for d in current["days"]} == planned | {empty}
    assert_matches_itinerary(result, current)


# FR-069 AC1, TC-217


@pytest.mark.asyncio
async def test_tc_217_stale_edit_from_a_second_client_is_refused_and_rows_stay_identical(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    opened = await route_state(api_client, auth_user, trip_id)  # both tabs load this revision
    newcomer = await unplanned_place(db_session, trip_id)
    body = {"plan_revision": opened["plan_revision"], "day_number": 1, "place_id": str(newcomer.id)}

    first = await api_client.post(add_url(trip_id), json=body, headers=auth_user.headers)
    assert first.status_code == 200, first.text
    after_first = await state(db_session, trip_id)
    read_after_first = await route_state(api_client, auth_user, trip_id)
    item_id = opened["days"][0]["items"][0]["id"]

    second_tab = [
        api_client.post(add_url(trip_id), json=body, headers=auth_user.headers),
        api_client.patch(
            item_url(item_id),
            json={"plan_revision": opened["plan_revision"], "duration_min": 60},
            headers=auth_user.headers,
        ),
        api_client.delete(
            item_url(item_id),
            params={"plan_revision": opened["plan_revision"]},
            headers=auth_user.headers,
        ),
    ]
    for request in second_tab:
        response = await request
        assert response.status_code == 409, response.text
        assert response.json()["error"]["code"] == "STALE_PLAN"

    assert await state(db_session, trip_id) == after_first
    assert await route_state(api_client, auth_user, trip_id) == read_after_first


@pytest.mark.asyncio
async def test_add_place_route_refuses_an_active_generation_and_another_users_trip(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    newcomer = (await unplanned_place(db_session, trip_id)).id  # state() expires loaded rows
    before = await state(db_session, trip_id)
    body = {"plan_revision": before["revision"], "day_number": 1, "place_id": str(newcomer)}
    other = AuthUser(user_id=uuid.uuid4(), email="other@example.test")
    await insert_auth_user(db_session, other.user_id)

    foreign = await api_client.post(add_url(trip_id), json=body, headers=other.headers)
    assert foreign.status_code == 404, foreign.text
    assert foreign.json()["error"]["code"] == "NOT_FOUND"

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
    busy = await api_client.post(add_url(trip_id), json=body, headers=auth_user.headers)
    assert busy.status_code == 409, busy.text
    assert busy.json()["error"]["code"] == "GENERATION_IN_PROGRESS"
    assert await state(db_session, trip_id) == before


# API-28 and API-29: ranked alternatives and replace (IMP-505; FR-065; IMD-11)


def alternatives_url(item_id: Any) -> str:
    return f"{item_url(item_id)}/alternatives"


def replace_url(item_id: Any) -> str:
    return f"{item_url(item_id)}/replace"


def first_activity(itinerary: dict[str, Any]) -> dict[str, Any]:
    return next(
        item
        for day in itinerary["days"]
        for item in day["items"]
        if item["slot_type"] == "activity"
    )


@pytest.fixture
def alternatives_off(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("FEATURES_DISABLED", "alternatives")
    get_settings.cache_clear()
    yield
    monkeypatch.undo()
    get_settings.cache_clear()


# FR-065 AC1, TC-208


@pytest.mark.asyncio
async def test_tc_208_alternatives_route_lists_up_to_three_ranked_places_with_deltas(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    before = await state(db_session, trip_id)
    itinerary = await route_state(api_client, auth_user, trip_id)
    item = first_activity(itinerary)
    planned = {i["place"]["id"] for day in itinerary["days"] for i in day["items"]}

    response = await api_client.get(alternatives_url(item["id"]), headers=auth_user.headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["item_id"] == item["id"]
    assert 1 <= len(body["alternatives"]) <= 3
    assert body["message"] is None
    for alternative in body["alternatives"]:
        assert alternative["place"]["id"] not in planned
        assert alternative["place"]["category"] != "food"  # an activity slot takes no food place
        assert set(alternative["cost_delta"]) == {"min", "max"}
        for amount in alternative["cost_delta"].values():
            assert isinstance(amount, str)
            assert len(amount.split(".")[1]) == 2  # IMD-05 money strings
        assert isinstance(alternative["time_delta_min"], int)
        assert alternative["reason"]
    again = await api_client.get(alternatives_url(item["id"]), headers=auth_user.headers)
    assert again.json() == body  # same inputs, same ranking
    assert await state(db_session, trip_id) == before  # read only


# FR-065 AC2, TC-209


@pytest.mark.asyncio
async def test_tc_209_replace_route_applies_an_alternative_keeping_the_start_time(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    before = await route_state(api_client, auth_user, trip_id)
    item = first_activity(before)
    listed = await api_client.get(alternatives_url(item["id"]), headers=auth_user.headers)
    chosen = listed.json()["alternatives"][0]["place"]

    response = await api_client.post(
        replace_url(item["id"]),
        json={"plan_revision": before["plan_revision"], "place_id": chosen["id"]},
        headers=auth_user.headers,
    )

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["plan_revision"] == before["plan_revision"] + 1
    replaced = next(i for d in result["changed_days"] for i in d["items"] if i["id"] == item["id"])
    assert replaced["place"]["id"] == chosen["id"]
    assert replaced["start_time"] == item["start_time"]
    assert replaced["duration_min"] == chosen["typical_duration_min"]
    assert (replaced["origin"], replaced["sources"]) == ("user", [])  # A1 §6.10
    assert_matches_itinerary(result, await route_state(api_client, auth_user, trip_id))


@pytest.mark.parametrize("case", ["not_an_alternative", "stale"])
@pytest.mark.asyncio
async def test_replace_route_refuses_a_non_alternative_or_a_stale_revision(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
    case: str,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    itinerary = await route_state(api_client, auth_user, trip_id)
    item = first_activity(itinerary)
    listed = await api_client.get(alternatives_url(item["id"]), headers=auth_user.headers)
    alternative = listed.json()["alternatives"][0]["place"]["id"]
    planned_elsewhere = next(
        i["place"]["id"]
        for day in itinerary["days"]
        for i in day["items"]
        if i["place"]["id"] != item["place"]["id"]
    )
    before = await state(db_session, trip_id)
    body = (
        {"plan_revision": before["revision"], "place_id": planned_elsewhere}
        if case == "not_an_alternative"
        else {"plan_revision": before["revision"] - 1, "place_id": alternative}
    )

    response = await api_client.post(replace_url(item["id"]), json=body, headers=auth_user.headers)

    expected = (422, "INVALID_EDIT") if case == "not_an_alternative" else (409, "STALE_PLAN")
    assert (response.status_code, response.json()["error"]["code"]) == expected
    assert await state(db_session, trip_id) == before


# FR-065 AC3, TC-210


@pytest.mark.asyncio
async def test_tc_210_alternatives_route_says_none_fit_when_no_place_is_left(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    item = first_activity(await route_state(api_client, auth_user, trip_id))
    planned = select(ItineraryItem.place_id).where(ItineraryItem.trip_id == trip_id)
    await db_session.execute(
        update(Place)
        .where(Place.destination_id == destination.id, Place.id.not_in(planned))
        .values(is_active=False)
    )

    response = await api_client.get(alternatives_url(item["id"]), headers=auth_user.headers)

    assert response.status_code == 200, response.text
    assert response.json() == {
        "item_id": item["id"],
        "alternatives": [],
        "message": "No alternative fits",
    }


@pytest.mark.asyncio
async def test_alternatives_of_a_locked_item_are_empty_and_its_replace_is_invalid(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    item = first_activity(await route_state(api_client, auth_user, trip_id))
    newcomer = (await unplanned_place(db_session, trip_id)).id
    # API-26 locking is IMP-506 (IMD-158), so the core locks the item.
    await edit(db_session, auth_user, trip_id, Lock(uuid.UUID(item["id"]), True))
    before = await state(db_session, trip_id)

    listed = await api_client.get(alternatives_url(item["id"]), headers=auth_user.headers)
    assert listed.status_code == 200, listed.text
    assert listed.json()["alternatives"] == []
    assert "locked" in listed.json()["message"]

    replaced = await api_client.post(
        replace_url(item["id"]),
        json={"plan_revision": before["revision"], "place_id": str(newcomer)},
        headers=auth_user.headers,
    )
    assert replaced.status_code == 422, replaced.text
    assert replaced.json()["error"]["code"] == "INVALID_EDIT"
    assert await state(db_session, trip_id) == before


@pytest.mark.asyncio
async def test_alternatives_routes_answer_not_found_for_another_users_item(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    item = (await items(db_session, trip_id))[0]
    newcomer = (await unplanned_place(db_session, trip_id)).id
    other = AuthUser(user_id=uuid.uuid4(), email="other@example.test")
    await insert_auth_user(db_session, other.user_id)
    before = await state(db_session, trip_id)

    listed = await api_client.get(alternatives_url(item.id), headers=other.headers)
    replaced = await api_client.post(
        replace_url(item.id),
        json={"plan_revision": before["revision"], "place_id": str(newcomer)},
        headers=other.headers,
    )

    for response in (listed, replaced):
        assert response.status_code == 404, response.text
        assert response.json()["error"]["code"] == "NOT_FOUND"
    assert await state(db_session, trip_id) == before


# IMD-11 cut-list item 6, TC-372 (API side): switched off, both routes are 404 and the floor
# journey (remove an activity, add another place) still works.


@pytest.mark.asyncio
async def test_tc_372_alternative_routes_are_not_found_when_switched_off_and_the_floor_works(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
    alternatives_off: None,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    before = await route_state(api_client, auth_user, trip_id)
    item = first_activity(before)
    newcomer = await unplanned_place(db_session, trip_id)

    listed = await api_client.get(alternatives_url(item["id"]), headers=auth_user.headers)
    replaced = await api_client.post(
        replace_url(item["id"]),
        json={"plan_revision": before["plan_revision"], "place_id": str(newcomer.id)},
        headers=auth_user.headers,
    )
    for response in (listed, replaced):
        assert response.status_code == 404, response.text
        assert response.json()["error"]["code"] == "NOT_FOUND"

    removed = await api_client.delete(
        item_url(item["id"]),
        params={"plan_revision": before["plan_revision"]},
        headers=auth_user.headers,
    )
    assert removed.status_code == 200, removed.text
    added = await api_client.post(
        add_url(trip_id),
        json={
            "plan_revision": removed.json()["plan_revision"],
            "day_number": 1,
            "place_id": str(newcomer.id),
        },
        headers=auth_user.headers,
    )
    assert added.status_code == 200, added.text


@pytest.mark.asyncio
async def test_lock_tc_211_tc_212_patch_and_unlock_with_retime(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    item_id = (await items(db_session, trip_id))[0].id
    before = await state(db_session, trip_id)
    locked = await api_client.patch(
        item_url(item_id),
        json={
            "plan_revision": before["revision"],
            "is_locked": True,
        },
        headers=auth_user.headers,
    )
    assert locked.status_code == 200, locked.text
    revision = locked.json()["plan_revision"]
    assert any(
        i["is_locked"]
        for d in locked.json()["changed_days"]
        for i in d["items"]
        if i["id"] == str(item_id)
    )
    for change in ({"start_time": "15:00"}, {"day_number": 2}):
        refused = await api_client.patch(
            item_url(item_id), json={"plan_revision": revision, **change}, headers=auth_user.headers
        )
        assert refused.status_code == 422
        assert refused.json()["error"]["code"] == "INVALID_EDIT"
    unlocked = await api_client.patch(
        item_url(item_id),
        json={
            "plan_revision": revision,
            "is_locked": False,
            "duration_min": 45,
        },
        headers=auth_user.headers,
    )
    assert unlocked.status_code == 200, unlocked.text
    changed = next(
        i for d in unlocked.json()["changed_days"] for i in d["items"] if i["id"] == str(item_id)
    )
    assert not changed["is_locked"]
    assert changed["duration_min"] == 45
    stale = await api_client.patch(
        item_url(item_id),
        json={"plan_revision": revision, "is_locked": True},
        headers=auth_user.headers,
    )
    assert stale.status_code == 409


@pytest.mark.asyncio
async def test_lock_disabled_returns_404_and_must_visit_is_locked_on_save(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    place = await db_session.scalar(
        select(Place)
        .where(Place.destination_id == destination.id, Place.is_active.is_(True))
        .order_by(Place.name)
    )
    assert place is not None
    place_id = place.id
    trip_id = await planned_trip(
        api_client, db_session, jobs_queue, auth_user, destination, must_visit=(place_id,)
    )
    locked = next(i for i in await items(db_session, trip_id) if i.place_id == place_id)
    assert locked.is_locked
    from app.generation import request_builder

    request = await request_builder.build(
        db_session,
        trip_id=trip_id,
        user_id=auth_user.user_id,
        prompt_template_id="itinerary_generate",
        prompt_version="v1",
    )
    assert any(
        i.place_id == place_id and i.start_time == locked.start_time.strftime("%H:%M")
        for i in request.locked_items
    )
    item_id = locked.id
    revision = (await state(db_session, trip_id))["revision"]
    monkeypatch.setenv("FEATURES_DISABLED", "locks")
    get_settings.cache_clear()
    refused = await api_client.patch(
        item_url(item_id),
        json={"plan_revision": revision, "is_locked": False},
        headers=auth_user.headers,
    )
    assert refused.status_code == 404
    removed = await api_client.delete(
        item_url(item_id), params={"plan_revision": revision}, headers=auth_user.headers
    )
    assert removed.status_code == 200
    assert any(f["code"] == "MUST_VISIT_MISSING" for f in removed.json()["findings"])


# IMP-602 archived read-only (IMD-35, FR-015 AC3): itinerary edit routes answer 409 CONFLICT


@pytest.mark.asyncio
async def test_tc_091_an_archived_trip_refuses_itinerary_edits_until_restored(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    before = await route_state(api_client, auth_user, trip_id)
    item_id = before["days"][0]["items"][0]["id"]
    trip_url = f"/api/v1/trips/{trip_id}"
    archived = await api_client.patch(
        trip_url, json={"status": "archived"}, headers=auth_user.headers
    )
    assert archived.status_code == 200, archived.text

    removed = await api_client.delete(
        item_url(item_id),
        params={"plan_revision": before["plan_revision"]},
        headers=auth_user.headers,
    )
    validated = await api_client.post(
        f"{trip_url}/itinerary/validate",
        json={"plan_revision": before["plan_revision"]},
        headers=auth_user.headers,
    )

    for response in (removed, validated):
        assert response.status_code == 409, response.text
        assert response.json()["error"]["code"] == "CONFLICT"
    assert await route_state(api_client, auth_user, trip_id) == before
    restored = await api_client.patch(trip_url, json={"status": "ready"}, headers=auth_user.headers)
    assert restored.status_code == 200, restored.text
    again = await api_client.delete(
        item_url(item_id),
        params={"plan_revision": before["plan_revision"]},
        headers=auth_user.headers,
    )
    assert again.status_code == 200, again.text
