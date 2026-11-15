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


# API-38 restore (FR-095 AC2: TC-257, TC-318) and retention (IMD-18: TC-319)


def visits(itinerary: dict[str, Any]) -> list[tuple[Any, ...]]:
    return [
        (day["day_number"], i["place"]["id"], i["start_time"], i["duration_min"], i["is_locked"])
        for day in itinerary["days"]
        for i in day["items"]
    ]


async def read(client: httpx.AsyncClient, user: AuthUser, trip_id: uuid.UUID) -> dict[str, Any]:
    response = await client.get(f"/api/v1/trips/{trip_id}/itinerary", headers=user.headers)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


async def remove_first(
    client: httpx.AsyncClient, user: AuthUser, itinerary: dict[str, Any]
) -> httpx.Response:
    item = itinerary["days"][0]["items"][0]
    return await client.delete(
        f"/api/v1/itinerary/items/{item['id']}",
        params={"plan_revision": itinerary["plan_revision"]},
        headers=user.headers,
    )


@pytest.mark.asyncio
async def test_tc_257_tc_318_restore_makes_the_version_current_and_keeps_the_replaced_plan(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    original = await read(api_client, auth_user, trip_id)
    edited = await remove_first(api_client, auth_user, original)
    assert edited.status_code == 200, edited.text
    replaced = await read(api_client, auth_user, trip_id)
    assert visits(replaced) != visits(original)

    restored = await api_client.post(
        f"/api/v1/trips/{trip_id}/versions/{original['version_id']}/restore",
        json={"plan_revision": replaced["plan_revision"]},
        headers=auth_user.headers,
    )

    assert restored.status_code == 200, restored.text
    body = restored.json()
    assert body["is_current"] is True
    assert body["plan_revision"] == replaced["plan_revision"] + 1
    assert visits(body) == visits(original)
    # Costs and travel are recalculated by the engine and routing, not copied (§5.2).
    assert body["totals"] == original["totals"]
    assert [i["travel_from_previous"] is None for day in body["days"] for i in day["items"]] == [
        i["travel_from_previous"] is None for day in original["days"] for i in day["items"]
    ]
    assert body == await read(api_client, auth_user, trip_id)

    listed = (
        await api_client.get(f"/api/v1/trips/{trip_id}/versions", headers=auth_user.headers)
    ).json()
    newest, kept = listed[0], listed[1]
    assert (newest["reason"], newest["plan_revision"]) == ("restore", body["plan_revision"])
    assert body["version_id"] == newest["id"]
    # TC-318: the replaced plan stays in history and reads back as it was.
    assert (kept["reason"], kept["plan_revision"]) == ("restore", replaced["plan_revision"])
    old = await api_client.get(
        f"/api/v1/trips/{trip_id}/itinerary",
        params={"version_id": kept["id"]},
        headers=auth_user.headers,
    )
    assert visits(old.json()) == visits(replaced)


@pytest.mark.asyncio
async def test_restore_a_stale_screen_editing_after_a_restore_gets_409_stale_plan(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    screen = await read(api_client, auth_user, trip_id)
    restored = await api_client.post(
        f"/api/v1/trips/{trip_id}/versions/{screen['version_id']}/restore",
        json={"plan_revision": screen["plan_revision"]},
        headers=auth_user.headers,
    )
    assert restored.status_code == 200, restored.text
    before = await counts(db_session, trip_id)

    stale_edit = await api_client.delete(
        f"/api/v1/itinerary/items/{restored.json()['days'][0]['items'][0]['id']}",
        params={"plan_revision": screen["plan_revision"]},
        headers=auth_user.headers,
    )
    stale_restore = await api_client.post(
        f"/api/v1/trips/{trip_id}/versions/{screen['version_id']}/restore",
        json={"plan_revision": screen["plan_revision"]},
        headers=auth_user.headers,
    )

    for response in (stale_edit, stale_restore):
        assert response.status_code == 409, response.text
        assert response.json()["error"]["code"] == "STALE_PLAN"
    assert await counts(db_session, trip_id) == before


@pytest.mark.asyncio
async def test_restore_brings_back_locks_notes_and_citations(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    first = await db_session.scalar(
        select(ItineraryItem).where(ItineraryItem.trip_id == trip_id).limit(1)
    )
    assert first is not None
    place_id, chunk = first.place_id, uuid.uuid4()
    await db_session.execute(
        update(ItineraryItem)
        .where(ItineraryItem.id == first.id)
        .values(source_chunk_ids=[chunk], is_locked=True, note="Go early.", note_origin="user")
    )
    base = await revision(db_session, trip_id)
    saved = await save(api_client, auth_user, trip_id, "With notes", base)
    assert saved.status_code == 201, saved.text
    await db_session.execute(
        update(ItineraryItem)
        .where(ItineraryItem.trip_id == trip_id)
        .values(source_chunk_ids=[], is_locked=False, note=None, note_origin="none")
    )

    restored = await api_client.post(
        f"/api/v1/trips/{trip_id}/versions/{saved.json()['id']}/restore",
        json={"plan_revision": base},
        headers=auth_user.headers,
    )

    assert restored.status_code == 200, restored.text
    db_session.expire_all()
    row = await db_session.scalar(
        select(ItineraryItem).where(
            ItineraryItem.trip_id == trip_id, ItineraryItem.place_id == place_id
        )
    )
    assert row is not None
    assert (row.source_chunk_ids, row.is_locked, row.note, row.note_origin) == (
        [chunk],
        True,
        "Go early.",
        "user",
    )


@pytest.mark.asyncio
async def test_restore_of_a_missing_version_is_404_and_changes_nothing(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    before = await counts(db_session, trip_id)
    response = await api_client.post(
        f"/api/v1/trips/{trip_id}/versions/{uuid.uuid4()}/restore",
        json={"plan_revision": before["revision"]},
        headers=auth_user.headers,
    )
    assert response.status_code == 404, response.text
    assert await counts(db_session, trip_id) == before


async def version_rows(session: AsyncSession, trip_id: uuid.UUID) -> list[tuple[int, str | None]]:
    session.expire_all()
    rows = await session.execute(
        select(ItineraryVersion.version_no, ItineraryVersion.name)
        .where(ItineraryVersion.trip_id == trip_id)
        .order_by(ItineraryVersion.version_no)
    )
    return [(row.version_no, row.name) for row in rows]


async def snapshots(session: AsyncSession, user: AuthUser, trip_id: uuid.UUID, n: int) -> None:
    for _ in range(n):
        async with session.begin_nested():
            await versions.snapshot_before_regeneration(session, user.user_id, trip_id)


@pytest.mark.asyncio
async def test_tc_319_the_limit_removes_only_the_oldest_automatic_version(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    base = await revision(db_session, trip_id)
    for name in ("Named one", "Named two"):
        assert (await save(api_client, auth_user, trip_id, name, base)).status_code == 201
    # v1 fallback (automatic), v2 and v3 named, then automatic snapshots up to the limit.
    await snapshots(db_session, auth_user, trip_id, 17)
    assert len(await version_rows(db_session, trip_id)) == 20

    await snapshots(db_session, auth_user, trip_id, 1)

    rows = await version_rows(db_session, trip_id)
    assert len(rows) == 20
    assert rows[0] == (2, "Named one")  # v1, the oldest automatic one, is gone
    assert rows[1] == (3, "Named two")
    assert rows[-1][0] == 21

    # Named versions are never pruned, even past the limit: automatic ones go first.
    for index in range(19):
        response = await save(api_client, auth_user, trip_id, f"Kept {index}", base)
        assert response.status_code == 201, response.text
    rows = await version_rows(db_session, trip_id)
    named = [name for _, name in rows if name]
    assert len(named) == 21
    assert [no for no, name in rows if name is None] == []  # all automatic ones pruned
    assert len(rows) == 21


@pytest.mark.asyncio
async def test_retention_with_the_switch_off_keeps_one_backup_copy(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
    versions_off: None,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    await snapshots(db_session, auth_user, trip_id, 3)
    edited = await remove_first(api_client, auth_user, await read(api_client, auth_user, trip_id))
    assert edited.status_code == 200, edited.text

    rows = await version_rows(db_session, trip_id)
    assert [no for no, _ in rows] == [4, 5]  # the backup copy and the current plan's version
    current = await read(api_client, auth_user, trip_id)
    assert current["version_id"] is not None


async def full_rows(
    session: AsyncSession, trip_id: uuid.UUID
) -> list[tuple[uuid.UUID, int, str | None, str, int, uuid.UUID | None]]:
    session.expire_all()
    rows = await session.execute(
        select(ItineraryVersion)
        .where(ItineraryVersion.trip_id == trip_id)
        .order_by(ItineraryVersion.version_no)
    )
    return [
        (v.id, v.version_no, v.name, v.reason, v.plan_revision, v.generation_id)
        for v in rows.scalars()
    ]


# IMD-191 (blueprint §25.6 item 1): with 'versions' off exactly one backup copy of the previous
# itinerary is kept for regeneration, next to the current plan's own version.
@pytest.mark.asyncio
async def test_switch_off_keeps_exactly_one_backup_after_repeated_regenerations(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trip_id = await planned_trip(api_client, db_session, jobs_queue, auth_user, destination)
    named = await save(api_client, auth_user, trip_id, "Kept", await revision(db_session, trip_id))
    assert named.status_code == 201, named.text
    monkeypatch.setenv("FEATURES_DISABLED", "versions")
    get_settings.cache_clear()

    @asynccontextmanager
    async def job_transaction() -> AsyncIterator[AsyncSession]:
        async with db_session.begin_nested():
            yield db_session

    for _ in range(3):
        base = await revision(db_session, trip_id)
        started = await api_client.post(
            f"/api/v1/trips/{trip_id}/itinerary/regenerate",
            json={"plan_revision": base, "mode": "rule_based"},
            headers=auth_user.headers,
        )
        assert started.status_code == 202, started.text
        while jobs_queue:
            await jobs.run(*jobs_queue.pop(0), job_transaction)
        assert await revision(db_session, trip_id) == base + 1

    current = await read(api_client, auth_user, trip_id)
    rows = await full_rows(db_session, trip_id)
    assert [row[2] for row in rows if row[2]] == ["Kept"]  # a named version is never deleted
    backups = [row for row in rows if row[2] is None and row[0] != uuid.UUID(current["version_id"])]
    assert len(backups) == 1, rows
    # The backup is the snapshot taken when the last regeneration started: the previous plan.
    _, _, _, reason, plan_revision, generation_id = backups[0]
    assert (reason, plan_revision, generation_id) == (
        "regeneration",
        current["plan_revision"] - 1,
        None,
    )

    restored = await api_client.post(
        f"/api/v1/trips/{trip_id}/versions/{backups[0][0]}/restore",
        json={"plan_revision": current["plan_revision"]},
        headers=auth_user.headers,
    )
    assert restored.status_code == 404, restored.text  # IMD-11: no restore while switched off
