"""Itinerary versions: snap-1 snapshots, API-36 list, API-37 save, API-24 with version_id and
API-38 restore (IMP-610; FR-095: TC-256; IMD-18, IMD-23; Amendment A1 §5.5).

The plan comes from API-22 in mode rule_based with the MOCK job path, as in test_edits.py; the job
runs on the test's rolled-back session, so no provider is reached.
"""

import uuid
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
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
from app.db.models import Destination, ItineraryItem, ItineraryVersion, ItineraryWarning, Trip
from app.generation import jobs, records
from app.generation import repository as generation_repository
from app.itinerary import versions
from app.places import seed

SAMPLETON = Path(__file__).resolve().parents[4] / "data" / "fixtures" / "sampleton"

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


@pytest.fixture
def versions_off(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("FEATURES_DISABLED", "versions")
    get_settings.cache_clear()
    yield
    monkeypatch.undo()
    get_settings.cache_clear()


async def planned_trip(
    client: httpx.AsyncClient,
    session: AsyncSession,
    queue: Queue,
    user: AuthUser,
    dest: Destination,
) -> uuid.UUID:
    """A three-day trip with a saved rule-based plan (plan_revision 1, one fallback version)."""
    created = await client.post(
        "/api/v1/trips",
        json={
            "title": "Versions in Sampleton",
            "destination_id": str(dest.id),
            "start_date": "2026-12-04",
            "end_date": "2026-12-06",
            "adults": 2,
        },
        headers=user.headers,
    )
    assert created.status_code == 201, created.text
    trip_id = created.json()["id"]
    saved = await client.put(
        f"/api/v1/trips/{trip_id}/preferences",
        json={"interests": ["museum", "food", "nature"]},
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


async def revision(session: AsyncSession, trip_id: uuid.UUID) -> int:
    session.expire_all()
    value = await session.scalar(select(Trip.plan_revision).where(Trip.id == trip_id))
    assert value is not None
    return value


async def counts(session: AsyncSession, trip_id: uuid.UUID) -> dict[str, Any]:
    """What a version write or a restore changes, to compare before and after."""
    session.expire_all()

    async def count(model: Any) -> int:
        value = await session.scalar(
            select(func.count()).select_from(model).where(model.trip_id == trip_id)
        )
        return int(value or 0)

    return {
        "revision": await revision(session, trip_id),
        "versions": await count(ItineraryVersion),
        "items": await count(ItineraryItem),
        "warnings": await count(ItineraryWarning),
    }


async def start_generation(session: AsyncSession, user: AuthUser, trip_id: uuid.UUID) -> None:
    await generation_repository.create_queued(
        session,
        trip_id=trip_id,
        user_id=user.user_id,
        provider="MOCK",
        model_id="mock-v1",
        prompt_template_id="itinerary_generate",
        prompt_version="v1",
        mapping_version="pm-2",
        scope="full",
        request_hash=records.request_hash({"trip_id": str(trip_id), "mode": "ai"}),
    )


async def save(
    client: httpx.AsyncClient, user: AuthUser, trip_id: uuid.UUID, name: str, base: int
) -> httpx.Response:
    return await client.post(
        f"/api/v1/trips/{trip_id}/versions",
        json={"plan_revision": base, "name": name},
        headers=user.headers,
    )


# FR-095 AC1, TC-256: a snapshot of the current plan is stored when a regeneration starts.


@pytest.mark.asyncio
async def test_tc_256_regeneration_hook_stores_a_snap_1_snapshot_of_the_current_plan(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    chunk = str(uuid.uuid4())
    first = await db_session.scalar(
        select(ItineraryItem).where(ItineraryItem.trip_id == trip_id).limit(1)
    )
    assert first is not None
    await db_session.execute(
        update(ItineraryItem)
        .where(ItineraryItem.id == first.id)
        .values(source_chunk_ids=[uuid.UUID(chunk)], is_locked=True)
    )
    before = await counts(db_session, trip_id)

    async with db_session.begin_nested():
        row = await versions.snapshot_before_regeneration(db_session, auth_user.user_id, trip_id)

    reason, name, plan_revision, snap = row.reason, row.name, row.plan_revision, row.snapshot
    assert reason == "regeneration"
    assert name is None
    assert plan_revision == before["revision"]
    assert (await counts(db_session, trip_id))["versions"] == before["versions"] + 1
    assert snap["schema"] == "snap-1"
    assert snap["plan_revision"] == before["revision"]
    assert "budget_settings" in snap
    items = [item for day in snap["days"] for item in day["items"]]
    assert len(items) == before["items"]
    # No costs, travel or findings in a snapshot (§5.2); locks, notes and citations kept (A1 §5.5).
    assert all("cost_min" not in item and "travel_from_prev_min" not in item for item in items)
    cited = [item for item in items if item["source_chunk_ids"]]
    assert cited == [next(item for item in items if item["source_chunk_ids"] == [chunk])]
    assert cited[0]["is_locked"] is True


@pytest.mark.asyncio
async def test_regeneration_snapshot_is_written_with_the_versions_switch_off(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
    versions_off: None,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    async with db_session.begin_nested():
        row = await versions.snapshot_before_regeneration(db_session, auth_user.user_id, trip_id)
    assert row.reason == "regeneration"


# API-36 and API-37


@pytest.mark.asyncio
async def test_versions_list_newest_first_with_kind_and_finding_counts(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    base = await revision(db_session, trip_id)

    saved = await save(api_client, auth_user, trip_id, "  Before changes ", base)
    listed = await api_client.get(f"/api/v1/trips/{trip_id}/versions", headers=auth_user.headers)

    assert saved.status_code == 201, saved.text
    body = saved.json()
    assert body["reason"] == "manual"
    assert body["kind"] == "named"
    assert body["name"] == "Before changes"
    assert body["plan_revision"] == base
    assert listed.status_code == 200, listed.text
    rows = listed.json()
    assert [row["version_no"] for row in rows] == sorted(
        (row["version_no"] for row in rows), reverse=True
    )
    assert rows[0]["id"] == body["id"]
    assert rows[-1]["reason"] == "fallback"
    assert rows[-1]["kind"] == "automatic"
    assert set(rows[-1]["validation_summary"]) == {"errors", "warnings", "infos"}
    # Saving a version does not change the plan.
    assert await revision(db_session, trip_id) == base


@pytest.mark.asyncio
async def test_versions_a_duplicate_name_is_409_conflict(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    base = await revision(db_session, trip_id)
    assert (await save(api_client, auth_user, trip_id, "Plan A", base)).status_code == 201
    before = await counts(db_session, trip_id)

    again = await save(api_client, auth_user, trip_id, "Plan A", base)

    assert again.status_code == 409, again.text
    assert again.json()["error"]["code"] == "CONFLICT"
    assert await counts(db_session, trip_id) == before


@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["", "   ", "x" * 61])
async def test_versions_a_name_outside_1_to_60_characters_is_422(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
    name: str,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    response = await save(api_client, auth_user, trip_id, name, await revision(db_session, trip_id))
    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test_versions_save_with_a_stale_revision_is_409_stale_plan(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    response = await save(
        api_client, auth_user, trip_id, "Old", await revision(db_session, trip_id) - 1
    )
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "STALE_PLAN"


@pytest.mark.asyncio
async def test_versions_save_and_restore_are_refused_while_a_generation_is_active(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    base = await revision(db_session, trip_id)
    version_id = (
        await api_client.get(f"/api/v1/trips/{trip_id}/versions", headers=auth_user.headers)
    ).json()[0]["id"]
    await start_generation(db_session, auth_user, trip_id)
    before = await counts(db_session, trip_id)

    saved = await save(api_client, auth_user, trip_id, "During a job", base)
    restored = await api_client.post(
        f"/api/v1/trips/{trip_id}/versions/{version_id}/restore",
        json={"plan_revision": base},
        headers=auth_user.headers,
    )

    for response in (saved, restored):  # IMD-23
        assert response.status_code == 409, response.text
        assert response.json()["error"]["code"] == "GENERATION_IN_PROGRESS"
    assert await counts(db_session, trip_id) == before


# API-24 with version_id (IMD-18)


@pytest.mark.asyncio
async def test_reading_a_version_prices_and_validates_the_snapshot_and_writes_nothing(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    current = (
        await api_client.get(f"/api/v1/trips/{trip_id}/itinerary", headers=auth_user.headers)
    ).json()
    before = await counts(db_session, trip_id)

    response = await api_client.get(
        f"/api/v1/trips/{trip_id}/itinerary",
        params={"version_id": current["version_id"]},
        headers=auth_user.headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["is_current"] is False
    assert body["version_id"] == current["version_id"]
    assert body["plan_revision"] == current["plan_revision"]

    def visits(itinerary: dict[str, Any]) -> list[tuple[Any, ...]]:
        return [
            (day["day_number"], i["place"]["id"], i["start_time"], i["duration_min"], i["cost"])
            for day in itinerary["days"]
            for i in day["items"]
        ]

    # Same places, times and engine prices as the plan the snapshot was taken from.
    assert visits(body) == visits(current)
    assert body["totals"] == current["totals"]
    assert {f["code"] for f in body["findings"]} <= {f["code"] for f in current["findings"]} | {
        "OVERLAP"  # travel is not stored in a snapshot (§5.2), so a preview has none
    }
    assert await counts(db_session, trip_id) == before


@pytest.mark.asyncio
async def test_reading_a_snapshot_without_citations_reads_them_as_empty(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    row = await db_session.scalar(
        select(ItineraryVersion).where(ItineraryVersion.trip_id == trip_id)
    )
    assert row is not None
    snapshot = dict(row.snapshot)
    snapshot["days"] = [
        {
            **day,
            "items": [
                {k: v for k, v in i.items() if k != "source_chunk_ids"} for i in day["items"]
            ],
        }
        for day in snapshot["days"]
    ]
    await db_session.execute(
        update(ItineraryVersion).where(ItineraryVersion.id == row.id).values(snapshot=snapshot)
    )

    response = await api_client.get(
        f"/api/v1/trips/{trip_id}/itinerary",
        params={"version_id": str(row.id)},
        headers=auth_user.headers,
    )

    assert response.status_code == 200, response.text
    assert all(i["sources"] == [] for day in response.json()["days"] for i in day["items"])


@pytest.mark.asyncio
async def test_versions_of_another_trip_or_user_answer_404(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    mine = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    other_id = uuid.uuid4()
    await insert_auth_user(db_session, other_id)
    other = AuthUser(user_id=other_id, email=f"{other_id}@example.test")
    theirs = await planned_trip(api_client, db_session, jobs_queue, other, destination)
    their_version = (
        await api_client.get(f"/api/v1/trips/{theirs}/versions", headers=other.headers)
    ).json()[0]["id"]

    by_other_trip = await api_client.get(
        f"/api/v1/trips/{mine}/itinerary",
        params={"version_id": their_version},
        headers=auth_user.headers,
    )
    foreign_list = await api_client.get(
        f"/api/v1/trips/{theirs}/versions", headers=auth_user.headers
    )

    for response in (by_other_trip, foreign_list):
        assert response.status_code == 404, response.text
        assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_versions_switch_off_hides_the_routes_and_version_reads(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
    versions_off: None,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    base = await revision(db_session, trip_id)
    version_id = await db_session.scalar(
        select(ItineraryVersion.id).where(ItineraryVersion.trip_id == trip_id)
    )
    url = f"/api/v1/trips/{trip_id}"

    responses = [
        await api_client.get(f"{url}/versions", headers=auth_user.headers),
        await save(api_client, auth_user, trip_id, "Off", base),
        await api_client.post(
            f"{url}/versions/{version_id}/restore",
            json={"plan_revision": base},
            headers=auth_user.headers,
        ),
        await api_client.get(
            f"{url}/itinerary", params={"version_id": str(version_id)}, headers=auth_user.headers
        ),
    ]

    for response in responses:  # IMD-11
        assert response.status_code == 404, response.text
        assert response.json()["error"]["code"] == "NOT_FOUND"
    # The current plan stays readable (TC-372 floor journey).
    current = await api_client.get(f"{url}/itinerary", headers=auth_user.headers)
    assert current.status_code == 200
