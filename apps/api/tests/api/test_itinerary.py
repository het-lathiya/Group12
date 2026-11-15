"""API-24 and API-09, reading the saved itinerary (§6.6.5; IMP-211: US-153 AC1, FR-005 AC2, TC-064;
FR-059; Amendment A1 §7.1).

A's plan is made through API-07, API-14 and API-22 with the MOCK provider; the submitted job runs on
the test's rolled-back session, as in test_generations.py. No provider host is reached.
"""

import uuid
from collections import Counter
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from fixtures.auth import AuthUser
from fixtures.db import insert_auth_user
from sqlalchemy import event, select, update
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from app.ai.factory import get_model_provider
from app.ai.providers.base import ModelProvider
from app.ai.providers.mock import MockProvider
from app.db.models import (
    Destination,
    ItineraryDay,
    ItineraryItem,
    ItineraryVersion,
    ItineraryWarning,
    Place,
    PlaceOpeningHours,
    Trip,
)
from app.db.models.rag import RagChunk
from app.generation import jobs
from app.itinerary import repository
from app.itinerary import service as itinerary_service
from app.itinerary.schemas import PlannedDay, PlannedItem
from app.places import seed
from app.rag import service as rag_service
from app.schemas.ai import GenerationRequest

REPOSITORY = Path(__file__).resolve().parents[4]
SAMPLETON = REPOSITORY / "data" / "fixtures" / "sampleton"

Generate = Callable[[AuthUser], Any]


@pytest_asyncio.fixture
async def destination(db_session: AsyncSession) -> Destination:
    await seed.load_fixture(db_session, seed.read_fixture(SAMPLETON))
    row = await db_session.scalar(select(Destination).where(Destination.slug == "sampleton"))
    assert row is not None
    return row


async def make_user(session: AsyncSession) -> AuthUser:
    user_id = uuid.uuid4()
    await insert_auth_user(session, user_id)
    return AuthUser(user_id=user_id, email=f"{user_id}@example.test")


@pytest.fixture
def jobs_queue(api_app: FastAPI) -> list[tuple[uuid.UUID, ModelProvider]]:
    queue: list[tuple[uuid.UUID, ModelProvider]] = []
    api_app.dependency_overrides[jobs.get_submit] = lambda: lambda g, p: queue.append((g, p))
    api_app.dependency_overrides[get_model_provider] = lambda: MockProvider("ok", app_env="test")
    return queue


async def create_trip(client: httpx.AsyncClient, user: AuthUser, destination: Destination) -> str:
    created = await client.post(
        "/api/v1/trips",
        json={
            "title": "Weekend in Sampleton",
            "destination_id": str(destination.id),
            "start_date": "2026-12-04",
            "end_date": "2026-12-06",
            "adults": 2,
        },
        headers=user.headers,
    )
    assert created.status_code == 201, created.text
    trip_id: str = created.json()["id"]
    saved = await client.put(
        f"/api/v1/trips/{trip_id}/preferences",
        json={"interests": ["museum", "food"], "must_visit_place_ids": []},
        headers=user.headers,
    )
    assert saved.status_code == 200, saved.text
    return trip_id


async def generate(
    client: httpx.AsyncClient,
    session: AsyncSession,
    queue: list[tuple[uuid.UUID, ModelProvider]],
    user: AuthUser,
    trip_id: str,
) -> dict[str, Any]:
    """Start API-22, run the captured job, and return the completed generation (API-23)."""
    await client.patch("/api/v1/me", json={"ai_notice_acknowledged": True}, headers=user.headers)
    started = await client.post(
        f"/api/v1/trips/{trip_id}/generations", json={"mode": "ai"}, headers=user.headers
    )
    assert started.status_code == 202, started.text

    @asynccontextmanager
    async def job_transaction() -> AsyncIterator[AsyncSession]:
        async with session.begin_nested():
            yield session

    while queue:
        await jobs.run(*queue.pop(0), job_transaction)
    done = await client.get(f"/api/v1/generations/{started.json()['id']}", headers=user.headers)
    body: dict[str, Any] = done.json()
    assert body["status"] == "completed", done.text
    return body


def item_selects(session: AsyncSession) -> list[str]:
    """Collects the SQL of every statement that reads itinerary_items on this session."""
    statements: list[str] = []
    assert isinstance(session.bind, AsyncConnection)  # db_session is bound to one connection
    connection = session.bind.sync_connection

    @event.listens_for(connection, "before_cursor_execute")
    def record(*args: Any) -> None:
        statement = str(args[2])
        if statement.lstrip().lower().startswith("select") and "itinerary_items" in statement:
            statements.append(statement)

    return statements


# US-153 AC1, TC-064, FR-059


@pytest.mark.asyncio
async def test_us_153_the_saved_plan_is_returned_in_order(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: list[tuple[uuid.UUID, ModelProvider]],
) -> None:
    trip_id = await create_trip(api_client, auth_user, destination)
    generation = await generate(api_client, db_session, jobs_queue, auth_user, trip_id)
    selects = item_selects(db_session)

    response = await api_client.get(f"/api/v1/trips/{trip_id}/itinerary", headers=auth_user.headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert len(selects) == 1  # every item in one query, not one per day
    assert body["trip_id"] == trip_id
    assert body["plan_revision"] == generation["plan_revision"] == 1
    assert body["version_id"] == generation["itinerary_version_id"]
    assert (body["is_current"], body["plan_stale"]) == (True, False)
    # PD-RUN-069-1: nothing outside the curated hours; unpriced places and one without hours.
    assert {f["code"]: f["severity"] for f in body["findings"]} == {
        "HOURS_UNVERIFIED": "info",
        "COST_INCOMPLETE": "warning",
    }
    assert len(body["findings"]) == 2
    assert body["source"] == {
        "generation_id": generation["id"],
        "provider": "MOCK",
        "outcome": "model",
    }

    # Days and items in the stored order, as saved by the generation.
    stored = (
        await db_session.execute(
            select(ItineraryDay.day_number, ItineraryItem.id)
            .join(ItineraryItem, ItineraryItem.day_id == ItineraryDay.id)
            .where(ItineraryDay.trip_id == uuid.UUID(trip_id))
            .order_by(ItineraryDay.day_number, ItineraryItem.position)
        )
    ).all()
    assert [d["day_number"] for d in body["days"]] == [1, 2, 3]
    assert [d["date"] for d in body["days"]] == ["2026-12-04", "2026-12-05", "2026-12-06"]
    returned = [(d["day_number"], i["id"]) for d in body["days"] for i in d["items"]]
    assert returned == [(day, str(item_id)) for day, item_id in stored]

    items = [item for day in body["days"] for item in day["items"]]
    for day in body["days"]:
        assert [i["position"] for i in day["items"]] == list(range(1, len(day["items"]) + 1))
        assert day["theme_origin"] == ("ai" if day["theme"] else "none")
        priced = [item["cost"] for item in day["items"] if item["cost"]]
        assert day["day_cost"] == {
            "min": f"{sum(Decimal(cost['min']) for cost in priced):.2f}",
            "max": f"{sum(Decimal(cost['max']) for cost in priced):.2f}",
            "currency": "GBP",
            "complete": len(priced) == len(day["items"]),
        }
    for item in items:
        # A1 §7.1: sources is always present and empty until IMP-316.
        assert item["sources"] == []
        assert item["cost"] is None or item["cost"]["currency"] == "GBP"
        leg = item["travel_from_previous"]
        assert leg is None if item["position"] == 1 else leg["source"] == "fallback_estimate"
        assert item["origin"] == "model"
        assert item["must_visit"] is False
        start = datetime.strptime(item["start_time"], "%H:%M")
        end = start + timedelta(minutes=item["duration_min"])
        assert item["end_time"] == end.strftime("%H:%M")
        assert set(item["place"]) == {"id", "name", "category", "lat", "lon", "hours_label"}
    # BF-07 to BF-09 with no traveller inputs and the default 10 percent contingency.
    priced = [item["cost"] for item in items if item["cost"]]
    high = sum(Decimal(cost["max"]) for cost in priced)
    contingency = (high / 10).quantize(Decimal("0.01"), ROUND_HALF_UP)
    assert body["totals"] == {
        "currency": "GBP",
        "estimate": {
            "min": f"{sum(Decimal(cost['min']) for cost in priced):.2f}",
            "max": f"{high:.2f}",
        },
        "planning_total": f"{high + contingency:.2f}",
        "complete": len(priced) == len(items),
        "incomplete_count": len(items) - len(priced),
    }


@pytest.mark.asyncio
async def test_tc_195_each_day_lists_its_items_in_time_order(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: list[tuple[uuid.UUID, ModelProvider]],
) -> None:
    trip_id = await create_trip(api_client, auth_user, destination)
    await generate(api_client, db_session, jobs_queue, auth_user, trip_id)

    response = await api_client.get(f"/api/v1/trips/{trip_id}/itinerary", headers=auth_user.headers)

    days = response.json()["days"]
    assert sum(len(day["items"]) for day in days) > 0
    for day in days:
        starts = [item["start_time"] for item in day["items"]]
        assert starts == sorted(starts)
        for earlier, later in zip(day["items"], day["items"][1:], strict=False):
            assert earlier["end_time"] <= later["start_time"]


@pytest.mark.asyncio
async def test_findings_are_the_warnings_of_the_current_revision_only(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: list[tuple[uuid.UUID, ModelProvider]],
) -> None:
    trip_id = await create_trip(api_client, auth_user, destination)
    generation = await generate(api_client, db_session, jobs_queue, auth_user, trip_id)
    revision = generation["plan_revision"]
    trip_uuid = uuid.UUID(trip_id)
    item_id = await db_session.scalar(
        select(ItineraryItem.id).where(ItineraryItem.trip_id == trip_uuid).limit(1)
    )
    db_session.add_all(
        [
            ItineraryWarning(
                trip_id=trip_uuid,
                plan_revision=revision,
                code="HOURS_UNVERIFIED",
                severity="info",
                message="Opening hours unavailable.",
                day_number=1,
                item_id=item_id,
                suggested_fix="Check opening times before the visit.",
            ),
            ItineraryWarning(
                trip_id=trip_uuid,
                plan_revision=revision - 1,
                code="COST_INCOMPLETE",
                severity="warning",
                message="From an older revision.",
            ),
        ]
    )
    await db_session.flush()

    response = await api_client.get(f"/api/v1/trips/{trip_id}/itinerary", headers=auth_user.headers)

    assert response.status_code == 200, response.text
    current = response.json()["findings"]
    assert Counter(f["code"] for f in current) == {
        "HOURS_UNVERIFIED": 2,  # the generation's (a place without stored hours) and this one
        "COST_INCOMPLETE": 1,
    }
    assert all(f["message"] != "From an older revision." for f in current)
    (finding,) = [f for f in current if f["message"] == "Opening hours unavailable."]
    assert uuid.UUID(finding.pop("id"))
    assert finding == {
        "code": "HOURS_UNVERIFIED",
        "severity": "info",
        "message": "Opening hours unavailable.",
        "day_number": 1,
        "item_id": str(item_id),
        "place_id": None,
        "suggested_fix": "Check opening times before the visit.",
    }


@pytest.mark.asyncio
async def test_version_id_is_null_when_no_version_has_the_current_revision(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: list[tuple[uuid.UUID, ModelProvider]],
) -> None:
    trip_id = await create_trip(api_client, auth_user, destination)
    await generate(api_client, db_session, jobs_queue, auth_user, trip_id)
    await db_session.execute(
        update(Trip)
        .where(Trip.id == uuid.UUID(trip_id))
        .values(plan_revision=Trip.plan_revision + 1)
    )

    response = await api_client.get(f"/api/v1/trips/{trip_id}/itinerary", headers=auth_user.headers)

    assert response.status_code == 200, response.text
    assert response.json()["version_id"] is None


@pytest.mark.asyncio
async def test_a_must_visit_place_in_the_plan_is_flagged(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: list[tuple[uuid.UUID, ModelProvider]],
) -> None:
    trip_id = await create_trip(api_client, auth_user, destination)
    await generate(api_client, db_session, jobs_queue, auth_user, trip_id)
    url = f"/api/v1/trips/{trip_id}/itinerary"
    first = (await api_client.get(url, headers=auth_user.headers)).json()["days"][0]["items"][0]
    saved = await api_client.put(
        f"/api/v1/trips/{trip_id}/preferences",
        json={"must_visit_place_ids": [first["place"]["id"]]},
        headers=auth_user.headers,
    )
    assert saved.status_code == 200, saved.text

    items = [
        i
        for d in (await api_client.get(url, headers=auth_user.headers)).json()["days"]
        for i in d["items"]
    ]
    flagged = {i["place"]["id"] for i in items if i["must_visit"]}
    assert flagged == {first["place"]["id"]}


# FR-005 AC2, TC-064: no itinerary, another user's trip, a reserved query


@pytest.mark.asyncio
async def test_tc_064_a_trip_without_an_itinerary_answers_404_no_itinerary_yet(
    api_client: httpx.AsyncClient, auth_user: AuthUser, destination: Destination
) -> None:
    trip_id = await create_trip(api_client, auth_user, destination)

    response = await api_client.get(f"/api/v1/trips/{trip_id}/itinerary", headers=auth_user.headers)

    assert response.status_code == 404
    error = response.json()["error"]
    assert (error["code"], error["message"], error["details"]) == (
        "NOT_FOUND",
        "No itinerary yet.",
        [],
    )
    assert error["request_id"]


@pytest.mark.asyncio
async def test_tc_064_another_users_itinerary_answers_like_a_missing_trip(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: list[tuple[uuid.UUID, ModelProvider]],
) -> None:
    trip_id = await create_trip(api_client, auth_user, destination)
    await generate(api_client, db_session, jobs_queue, auth_user, trip_id)
    other = await make_user(db_session)

    foreign = await api_client.get(f"/api/v1/trips/{trip_id}/itinerary", headers=other.headers)
    missing = await api_client.get(f"/api/v1/trips/{uuid.uuid4()}/itinerary", headers=other.headers)

    assert foreign.status_code == missing.status_code == 404
    strip = [{**r.json()["error"], "request_id": None} for r in (foreign, missing)]
    assert strip[0] == strip[1]
    assert strip[0]["message"] == "Not found."  # never says whether a plan exists
    assert trip_id not in foreign.text


# IMP-405: stored warnings, API-32 (FR-056, FR-058: TC-193, TC-194)


async def leave_out_a_must_visit_place(
    client: httpx.AsyncClient, session: AsyncSession, user: AuthUser, trip_id: str
) -> uuid.UUID:
    """Makes an active place that is not in the plan the trip's must-visit place."""
    trip_uuid = uuid.UUID(trip_id)
    planned = select(ItineraryItem.place_id).where(ItineraryItem.trip_id == trip_uuid)
    trip = await session.get(Trip, trip_uuid)
    assert trip is not None
    place_id = await session.scalar(
        select(Place.id)
        .where(
            Place.destination_id == trip.destination_id,
            Place.is_active.is_(True),
            Place.id.not_in(planned),
        )
        .order_by(Place.name)
        .limit(1)
    )
    assert place_id is not None
    saved = await client.put(
        f"/api/v1/trips/{trip_id}/preferences",
        json={"interests": ["museum", "food"], "must_visit_place_ids": [str(place_id)]},
        headers=user.headers,
    )
    assert saved.status_code == 200, saved.text
    return place_id


async def warning_rows(session: AsyncSession, trip_id: str) -> list[tuple[int, str]]:
    rows = await session.execute(
        select(ItineraryWarning.plan_revision, ItineraryWarning.code)
        .where(ItineraryWarning.trip_id == uuid.UUID(trip_id))
        .order_by(ItineraryWarning.plan_revision, ItineraryWarning.code)
    )
    return [(revision, code) for revision, code in rows]


@pytest.mark.asyncio
async def test_tc_194_api_32_revalidates_and_replaces_the_warnings_of_the_revision(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: list[tuple[uuid.UUID, ModelProvider]],
) -> None:
    trip_id = await create_trip(api_client, auth_user, destination)
    revision = (await generate(api_client, db_session, jobs_queue, auth_user, trip_id))[
        "plan_revision"
    ]
    place_id = await leave_out_a_must_visit_place(api_client, db_session, auth_user, trip_id)
    db_session.add_all(
        [
            ItineraryWarning(
                trip_id=uuid.UUID(trip_id),
                plan_revision=revision,
                code="COST_INCOMPLETE",
                severity="warning",
                message="Replaced by the revalidation.",
            ),
            ItineraryWarning(
                trip_id=uuid.UUID(trip_id),
                plan_revision=revision - 1,
                code="COST_INCOMPLETE",
                severity="warning",
                message="Another revision keeps its warnings.",
            ),
        ]
    )
    await db_session.flush()

    response = await api_client.post(
        f"/api/v1/trips/{trip_id}/itinerary/validate",
        json={"plan_revision": revision},
        headers=auth_user.headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["plan_revision"] == revision
    assert body["validation_summary"] == {"errors": 1, "warnings": 1, "infos": 1}
    assert Counter(f["code"] for f in body["findings"]) == {
        "HOURS_UNVERIFIED": 1,
        "MUST_VISIT_MISSING": 1,
        "COST_INCOMPLETE": 1,
    }
    (finding,) = [f for f in body["findings"] if f["code"] == "MUST_VISIT_MISSING"]
    assert finding["code"] == "MUST_VISIT_MISSING"
    assert finding["severity"] == "error"
    assert (finding["place_id"], finding["item_id"]) == (str(place_id), None)  # IMD-42
    assert finding["message"]
    assert finding["suggested_fix"]
    assert await warning_rows(db_session, trip_id) == [
        (revision - 1, "COST_INCOMPLETE"),
        (revision, "COST_INCOMPLETE"),
        (revision, "HOURS_UNVERIFIED"),
        (revision, "MUST_VISIT_MISSING"),
    ]
    trip = await db_session.get(Trip, uuid.UUID(trip_id))
    assert trip is not None
    assert trip.plan_revision == revision  # the plan is not changed
    read = await api_client.get(f"/api/v1/trips/{trip_id}/itinerary", headers=auth_user.headers)
    assert read.json()["findings"] == body["findings"]  # API-24: the current revision's


@pytest.mark.asyncio
async def test_api_32_warnings_need_the_current_revision(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: list[tuple[uuid.UUID, ModelProvider]],
) -> None:
    trip_id = await create_trip(api_client, auth_user, destination)
    revision = (await generate(api_client, db_session, jobs_queue, auth_user, trip_id))[
        "plan_revision"
    ]
    before = await warning_rows(db_session, trip_id)

    response = await api_client.post(
        f"/api/v1/trips/{trip_id}/itinerary/validate",
        json={"plan_revision": revision - 1},
        headers=auth_user.headers,
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "STALE_PLAN"
    assert await warning_rows(db_session, trip_id) == before


@pytest.mark.asyncio
async def test_api_32_warnings_of_another_users_trip_or_no_plan_are_not_found(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: list[tuple[uuid.UUID, ModelProvider]],
) -> None:
    empty_trip = await create_trip(api_client, auth_user, destination)
    trip_id = await create_trip(api_client, auth_user, destination)
    revision = (await generate(api_client, db_session, jobs_queue, auth_user, trip_id))[
        "plan_revision"
    ]
    other = await make_user(db_session)

    foreign = await api_client.post(
        f"/api/v1/trips/{trip_id}/itinerary/validate",
        json={"plan_revision": revision},
        headers=other.headers,
    )
    no_plan = await api_client.post(
        f"/api/v1/trips/{empty_trip}/itinerary/validate",
        json={"plan_revision": 0},
        headers=auth_user.headers,
    )

    assert foreign.status_code == no_plan.status_code == 404
    assert foreign.json()["error"]["code"] == "NOT_FOUND"
    assert foreign.json()["error"]["message"] == "Not found."
    assert no_plan.json()["error"]["message"] == "No itinerary yet."


@pytest.mark.asyncio
async def test_tc_193_a_saved_version_returns_its_warnings_and_repair_summary(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: list[tuple[uuid.UUID, ModelProvider]],
) -> None:
    trip_id = await create_trip(api_client, auth_user, destination)
    generation = await generate(api_client, db_session, jobs_queue, auth_user, trip_id)
    revision, version_id = generation["plan_revision"], generation["itinerary_version_id"]
    place_id = await leave_out_a_must_visit_place(api_client, db_session, auth_user, trip_id)
    await api_client.post(
        f"/api/v1/trips/{trip_id}/itinerary/validate",
        json={"plan_revision": revision},
        headers=auth_user.headers,
    )
    # A later revision (an edit) with warnings of its own leaves the version's untouched.
    await db_session.execute(
        update(Trip).where(Trip.id == uuid.UUID(trip_id)).values(plan_revision=revision + 1)
    )
    db_session.add(
        ItineraryWarning(
            trip_id=uuid.UUID(trip_id),
            plan_revision=revision + 1,
            code="COST_INCOMPLETE",
            severity="warning",
            message="Of the later revision.",
        )
    )
    await db_session.flush()

    findings, summary = await itinerary_service.version_findings(
        db_session, auth_user.user_id, uuid.UUID(trip_id), uuid.UUID(version_id)
    )

    assert Counter(f.code for f in findings) == {
        "HOURS_UNVERIFIED": 1,
        "MUST_VISIT_MISSING": 1,
        "COST_INCOMPLETE": 1,
    }
    assert [(f.place_id, f.item_id) for f in findings if f.code == "MUST_VISIT_MISSING"] == [
        (place_id, None)
    ]
    assert all(f.message != "Of the later revision." for f in findings)
    assert all(f.suggested_fix for f in findings)
    assert summary["deterministic_repairs"] == 0
    assert summary["repair_attempts"] == 0
    assert {"errors", "warnings", "infos"} <= set(summary)


@pytest.mark.asyncio
async def test_generation_saves_warnings_with_fixes_and_the_versions_repair_counts(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: list[tuple[uuid.UUID, ModelProvider]],
) -> None:
    trip_id = await create_trip(api_client, auth_user, destination)
    generation = await generate(api_client, db_session, jobs_queue, auth_user, trip_id)

    version = await db_session.get(ItineraryVersion, uuid.UUID(generation["itinerary_version_id"]))
    assert version is not None
    assert version.validation_summary["deterministic_repairs"] == 0
    assert version.validation_summary["repair_attempts"] == 0
    rows = await db_session.scalars(
        select(ItineraryWarning).where(ItineraryWarning.trip_id == uuid.UUID(trip_id))
    )
    assert all(row.suggested_fix for row in rows)


# API-09 (FR-014: TC-087, TC-088; IMD-122 keeps the §6 shape, 200 with nulls when none)


@pytest.mark.asyncio
async def test_tc_088_latest_is_null_when_the_caller_has_no_itinerary(
    api_client: httpx.AsyncClient, auth_user: AuthUser, destination: Destination
) -> None:
    await create_trip(api_client, auth_user, destination)  # a trip, but no plan

    response = await api_client.get("/api/v1/itineraries/latest", headers=auth_user.headers)

    assert response.status_code == 200
    assert response.json() == {"trip_id": None, "plan_revision": None, "updated_at": None}


@pytest.mark.asyncio
async def test_tc_087_latest_returns_the_callers_most_recently_changed_itinerary_only(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: list[tuple[uuid.UUID, ModelProvider]],
) -> None:
    older = await create_trip(api_client, auth_user, destination)
    newer = await create_trip(api_client, auth_user, destination)
    await generate(api_client, db_session, jobs_queue, auth_user, older)
    await generate(api_client, db_session, jobs_queue, auth_user, newer)
    other = await make_user(db_session)
    foreign = await create_trip(api_client, other, destination)
    await generate(api_client, db_session, jobs_queue, other, foreign)
    # now() is fixed within the test's transaction: date the versions apart explicitly.
    for trip_id, age in ((older, 2), (newer, 1), (foreign, 0)):
        await db_session.execute(
            update(ItineraryVersion)
            .where(ItineraryVersion.trip_id == uuid.UUID(trip_id))
            .values(created_at=datetime(2026, 11, 3, 12) - timedelta(hours=age))
        )

    response = await api_client.get("/api/v1/itineraries/latest", headers=auth_user.headers)

    assert response.status_code == 200
    assert response.json() == {
        "trip_id": newer,
        "plan_revision": 1,
        "updated_at": "2026-11-03T11:00:00Z",
    }


# ---------- Saved citations and sources (A1 §5.5, §6.10, §7.1; FR-138 AC3, FR-139, TC-456) ----


class RecordingMock(MockProvider):
    """MOCK that keeps the requests it was given, to compare citations with what was supplied."""

    def __init__(self) -> None:
        super().__init__("ok", app_env="test")
        self.requests: list[GenerationRequest] = []

    async def generate_itinerary(self, request: GenerationRequest) -> Any:
        self.requests.append(request)
        return await super().generate_itinerary(request)


@pytest_asyncio.fixture
async def indexed(db_session: AsyncSession, destination: Destination) -> Destination:
    @asynccontextmanager
    async def job_transaction() -> AsyncIterator[AsyncSession]:
        async with db_session.begin_nested():
            yield db_session

    await rag_service.index(
        "sampleton",
        provider=MockProvider("ok", app_env="test"),
        sessions=job_transaction,
        root=REPOSITORY / "data",
        today=date(2026, 11, 7),
    )
    return destination


@pytest_asyncio.fixture
async def recording(
    api_app: FastAPI, jobs_queue: list[tuple[uuid.UUID, ModelProvider]]
) -> RecordingMock:
    provider = RecordingMock()
    api_app.dependency_overrides[get_model_provider] = lambda: provider
    return provider


def cited_items(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for day in plan["days"] for item in day["items"] if item["sources"]]


async def grounded_plan(
    client: httpx.AsyncClient,
    session: AsyncSession,
    queue: list[tuple[uuid.UUID, ModelProvider]],
    user: AuthUser,
    destination: Destination,
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    trip_id = await create_trip(client, user, destination)
    generation = await generate(client, session, queue, user, trip_id)
    answer = await client.get(f"/api/v1/trips/{trip_id}/itinerary", headers=user.headers)
    assert answer.status_code == 200, answer.text
    return trip_id, generation, answer.json()


@pytest.mark.asyncio
async def test_tc_456_the_itinerary_returns_sources_with_every_source_ref_field(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    indexed: Destination,
    jobs_queue: list[tuple[uuid.UUID, ModelProvider]],
) -> None:
    _, generation, plan = await grounded_plan(
        api_client, db_session, jobs_queue, auth_user, indexed
    )

    assert generation["retrieval_mode"] == "vector"
    cited = cited_items(plan)
    assert cited
    for item in cited:
        [source] = item["sources"]
        assert set(source) == {
            "chunk_id",
            "kind",
            "title",
            "source_name",
            "licence",
            "attribution_text",
            "url",
            "retrieved_on",
        }
        assert source["kind"] == "place"
        assert item["place"]["name"] in source["title"]
        assert source["source_name"]
        assert source["licence"]


@pytest.mark.asyncio
async def test_tc_456_saved_ids_are_a_subset_of_the_passages_supplied(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    indexed: Destination,
    jobs_queue: list[tuple[uuid.UUID, ModelProvider]],
    recording: RecordingMock,
) -> None:
    trip_id, _, _ = await grounded_plan(api_client, db_session, jobs_queue, auth_user, indexed)

    [request] = recording.requests
    rows = await db_session.scalars(
        select(ItineraryItem).where(ItineraryItem.trip_id == uuid.UUID(trip_id))
    )
    saved = {str(chunk_id) for row in rows for chunk_id in row.source_chunk_ids}
    assert saved
    assert saved <= request.passage_ids()


@pytest.mark.asyncio
async def test_the_snapshot_items_carry_their_citations(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    indexed: Destination,
    jobs_queue: list[tuple[uuid.UUID, ModelProvider]],
) -> None:
    trip_id, _, plan = await grounded_plan(api_client, db_session, jobs_queue, auth_user, indexed)

    version = await db_session.scalar(
        select(ItineraryVersion).where(ItineraryVersion.trip_id == uuid.UUID(trip_id))
    )
    assert version is not None
    stored = [item for day in version.snapshot["days"] for item in day["items"]]
    read = [item for day in plan["days"] for item in day["items"]]
    assert [item["source_chunk_ids"] for item in stored] == [
        [source["chunk_id"] for source in item["sources"]] for item in read
    ]


@pytest.mark.asyncio
async def test_tc_456_a_foreign_trip_still_answers_404_with_sources_saved(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    indexed: Destination,
    jobs_queue: list[tuple[uuid.UUID, ModelProvider]],
) -> None:
    trip_id, _, _ = await grounded_plan(api_client, db_session, jobs_queue, auth_user, indexed)
    other = await make_user(db_session)

    answer = await api_client.get(f"/api/v1/trips/{trip_id}/itinerary", headers=other.headers)

    assert answer.status_code == 404
    assert answer.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_an_inactive_chunk_resolves_and_a_missing_id_is_skipped(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    indexed: Destination,
    jobs_queue: list[tuple[uuid.UUID, ModelProvider]],
) -> None:
    trip_id, _, plan = await grounded_plan(api_client, db_session, jobs_queue, auth_user, indexed)
    item = cited_items(plan)[0]
    chunk_id = uuid.UUID(item["sources"][0]["chunk_id"])
    await db_session.execute(
        update(RagChunk).where(RagChunk.id == chunk_id).values(is_active=False)
    )
    await db_session.execute(
        update(ItineraryItem)
        .where(ItineraryItem.id == uuid.UUID(item["id"]))
        .values(source_chunk_ids=[uuid.uuid4(), chunk_id])
    )
    db_session.expire_all()

    answer = await api_client.get(f"/api/v1/trips/{trip_id}/itinerary", headers=auth_user.headers)

    read = next(i for day in answer.json()["days"] for i in day["items"] if i["id"] == item["id"])
    assert [source["chunk_id"] for source in read["sources"]] == [str(chunk_id)]


@pytest.mark.asyncio
async def test_sources_are_read_in_one_query_however_many_items_cite(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    indexed: Destination,
    jobs_queue: list[tuple[uuid.UUID, ModelProvider]],
) -> None:
    trip_id, _, plan = await grounded_plan(api_client, db_session, jobs_queue, auth_user, indexed)
    assert len(cited_items(plan)) > 1
    assert isinstance(db_session.bind, AsyncConnection)
    statements: list[str] = []

    @event.listens_for(db_session.bind.sync_connection, "before_cursor_execute")
    def record(*args: Any) -> None:
        if "rag_chunks" in str(args[2]):
            statements.append(str(args[2]))

    await api_client.get(f"/api/v1/trips/{trip_id}/itinerary", headers=auth_user.headers)

    assert len(statements) == 1


@pytest.mark.asyncio
async def test_a_plan_without_an_index_saves_no_citation(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: list[tuple[uuid.UUID, ModelProvider]],
) -> None:
    trip_id, generation, plan = await grounded_plan(
        api_client, db_session, jobs_queue, auth_user, destination
    )

    assert generation["retrieval_mode"] == "lexical_fallback"
    assert cited_items(plan) == []
    version = await db_session.scalar(
        select(ItineraryVersion).where(ItineraryVersion.trip_id == uuid.UUID(trip_id))
    )
    assert version is not None
    assert version.snapshot["days"][0]["items"][0]["source_chunk_ids"] == []


@pytest.mark.asyncio
async def test_a_fallback_plan_is_saved_without_an_ai_note_or_citation(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: list[tuple[uuid.UUID, ModelProvider]],
) -> None:
    trip_id, generation, plan = await grounded_plan(
        api_client, db_session, jobs_queue, auth_user, destination
    )
    place_id = plan["days"][0]["items"][0]["place"]["id"]
    item = PlannedItem(
        place_id=place_id,
        slot_type="activity",
        start_time="09:00",
        duration_min=60,
        note="Written from a fixed template.",
    )

    days = await repository.replace_plan(
        db_session,
        uuid.UUID(trip_id),
        date(2026, 12, 4),
        [PlannedDay(1, "", [item])],
        origin="fallback_rule_based",
        generation_id=uuid.UUID(generation["id"]),
    )

    [stored] = days[0]["items"]
    assert (stored["note"], stored["note_origin"], stored["source_chunk_ids"]) == (None, "none", [])


@pytest.mark.asyncio
async def test_tc_180_validate_persists_closed_hours(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: list[tuple[uuid.UUID, ModelProvider]],
) -> None:
    trip_id = await create_trip(api_client, auth_user, destination)
    generation = await generate(api_client, db_session, jobs_queue, auth_user, trip_id)
    plan = (
        await api_client.get(f"/api/v1/trips/{trip_id}/itinerary", headers=auth_user.headers)
    ).json()
    day = plan["days"][0]
    place_id = uuid.UUID(day["items"][0]["place"]["id"])
    await db_session.execute(
        update(Place)
        .where(Place.id == place_id)
        .values(hours_label="curated", hours_checked_on=date(2026, 11, 14))
    )
    await db_session.execute(
        update(PlaceOpeningHours)
        .where(PlaceOpeningHours.place_id == place_id)
        .values(is_closed=True, open_time=None, close_time=None, closes_next_day=False)
    )
    await db_session.flush()
    result = await api_client.post(
        f"/api/v1/trips/{trip_id}/itinerary/validate",
        json={"plan_revision": generation["plan_revision"]},
        headers=auth_user.headers,
    )
    assert result.status_code == 200, result.text
    assert any(
        f["code"] == "CLOSED_ON_DAY" and f["severity"] == "error" for f in result.json()["findings"]
    )
    read = (
        await api_client.get(f"/api/v1/trips/{trip_id}/itinerary", headers=auth_user.headers)
    ).json()
    assert any(f["code"] == "CLOSED_ON_DAY" for f in read["findings"])


# IMP-609: API-35 summary (FR-094: TC-254, TC-255)


@pytest.mark.asyncio
async def test_tc_254_summary_lists_every_day_with_times_places_travel_and_labels(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: list[tuple[uuid.UUID, ModelProvider]],
) -> None:
    trip_id = await create_trip(api_client, auth_user, destination)
    await generate(api_client, db_session, jobs_queue, auth_user, trip_id)
    itinerary = (
        await api_client.get(f"/api/v1/trips/{trip_id}/itinerary", headers=auth_user.headers)
    ).json()
    costs = (
        await api_client.get(f"/api/v1/trips/{trip_id}/costs", headers=auth_user.headers)
    ).json()

    response = await api_client.get(f"/api/v1/trips/{trip_id}/summary", headers=auth_user.headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["trip"]["id"] == trip_id
    # The same projection as API-24 and API-33: nothing recalculated for the print view.
    assert body["days"] == itinerary["days"]
    assert body["costs"] == costs
    assert body["generated_at"].endswith("Z") or body["generated_at"].endswith("+00:00")
    items = [item for day in body["days"] for item in day["items"]]
    assert items
    assert all(item["start_time"] and item["end_time"] for item in items)
    assert all(item["place"]["hours_label"] for item in items)
    assert all(item["cost"] is None or item["cost"]["label"] for item in items)
    legs = [item["travel_from_previous"] for item in items if item["travel_from_previous"]]
    assert legs
    assert all(leg["source"] for leg in legs)
    # AI-written themes carry their origin, so the page can show the AI badge.
    assert all(day["theme_origin"] == ("ai" if day["theme"] else "none") for day in body["days"])


@pytest.mark.asyncio
async def test_tc_255_summary_shows_the_unresolved_warnings_of_the_current_plan(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: list[tuple[uuid.UUID, ModelProvider]],
) -> None:
    trip_id = await create_trip(api_client, auth_user, destination)
    generation = await generate(api_client, db_session, jobs_queue, auth_user, trip_id)
    revision = generation["plan_revision"]
    db_session.add_all(
        [
            ItineraryWarning(
                trip_id=uuid.UUID(trip_id),
                plan_revision=revision,
                code="HOURS_UNVERIFIED",
                severity="info",
                message="Opening hours unavailable.",
                day_number=1,
            ),
            ItineraryWarning(
                trip_id=uuid.UUID(trip_id),
                plan_revision=revision - 1,
                code="COST_INCOMPLETE",
                severity="warning",
                message="From an older revision.",
            ),
        ]
    )
    await db_session.flush()

    response = await api_client.get(f"/api/v1/trips/{trip_id}/summary", headers=auth_user.headers)

    assert response.status_code == 200, response.text
    messages = [finding["message"] for finding in response.json()["unresolved_findings"]]
    assert "Opening hours unavailable." in messages
    assert "From an older revision." not in messages


@pytest.mark.asyncio
async def test_summary_without_an_itinerary_or_of_another_user_is_404(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: list[tuple[uuid.UUID, ModelProvider]],
) -> None:
    empty = await create_trip(api_client, auth_user, destination)
    other = await make_user(db_session)
    theirs = await create_trip(api_client, other, destination)
    await generate(api_client, db_session, jobs_queue, other, theirs)

    for trip_id in (empty, theirs):
        response = await api_client.get(
            f"/api/v1/trips/{trip_id}/summary", headers=auth_user.headers
        )
        assert response.status_code == 404, response.text
        assert response.json()["error"]["code"] == "NOT_FOUND"
