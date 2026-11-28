"""Generation for a live city (Amendment A2 §6.6; IMP-727): TC-479 (IMP-727 share) and TC-480.

A completed live destination (the SAMPLE Liveton fakes through the import job) gets a trip, then:
a MOCK plan and a rule-based plan use stored place IDs only, carry no price and no hours from the
model, and raise ``COST_INCOMPLETE`` and ``HOURS_UNVERIFIED``. A provider timeout ends in the
labelled rule-based plan (items with origin ``fallback_rule_based``). A quota error ends in
``failed`` with the rule-based option (IMD-44), whose rule-based run then saves the labelled plan.

Offline only: live-data fakes, MOCK provider and embeddings. The app is built with
``any_city_mode`` ON through a settings override; jobs run in savepoints of the test session.
"""

import json
import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from fixtures.auth import AuthUser, auth_test_settings, client_for
from fixtures.guide_citations import GuideCitationMock
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.factory import get_model_provider
from app.ai.providers.base import ModelProvider
from app.ai.providers.mock import MockProvider
from app.auth import deps
from app.core.config import Settings
from app.db.models import AiGeneration, ItineraryItem, ItineraryVersion, Place
from app.generation import jobs
from app.livedata.factory import LiveProviders, get_geocoder
from app.livedata.providers.fake import LIVETON, FakeGeocoder, FakeGuides, FakePlaces
from app.main import create_app
from app.places import live_import, live_jobs, repository

pytestmark = [pytest.mark.any_city, pytest.mark.asyncio]

Sessions = Callable[[], AbstractAsyncContextManager[AsyncSession]]
Job = tuple[uuid.UUID, ModelProvider]
V1 = "/api/v1"


@pytest.fixture
def sessions(db_session: AsyncSession) -> Sessions:
    @asynccontextmanager
    async def job_transaction() -> AsyncIterator[AsyncSession]:
        async with db_session.begin_nested():
            yield db_session

    return job_transaction


@pytest.fixture
def submitted() -> list[Job]:
    return []


@pytest_asyncio.fixture
async def live_app(db_session: AsyncSession, submitted: list[Job]) -> FastAPI:
    app = create_app(
        auth_test_settings(features_disabled="!any_city_mode", live_data_provider="FAKE")
    )

    async def test_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[deps.db_session] = test_session
    app.dependency_overrides[get_geocoder] = lambda: FakeGeocoder("ok", app_env="test")
    app.dependency_overrides[jobs.get_submit] = lambda: lambda gid, p: submitted.append((gid, p))
    return app


async def live_destination(db_session: AsyncSession, sessions: Sessions) -> uuid.UUID:
    row = await repository.insert_live_destination(
        db_session, live_import.build_live_row(LIVETON, LIVETON.osm_ref)
    )
    outcome = await live_jobs.run_import(
        row.id,
        providers=LiveProviders(
            geocoder=FakeGeocoder("ok", app_env="test"),
            places=FakePlaces("ok", app_env="test"),
            guides=FakeGuides("ok", app_env="test"),
        ),
        sessions=sessions,
        settings=Settings(_env_file=None, app_env="test", ai_provider="MOCK"),
        embedder=MockProvider("ok", app_env="test"),
    )
    assert outcome == "completed"
    return row.id


async def live_trip(client: httpx.AsyncClient, user: AuthUser, destination_id: uuid.UUID) -> str:
    notice = await client.patch(
        f"{V1}/me", json={"ai_notice_acknowledged": True}, headers=user.headers
    )
    assert notice.status_code == 200, notice.text
    trip = await client.post(
        f"{V1}/trips",
        json={
            "title": "Weekend in Liveton (SAMPLE)",
            "destination_id": str(destination_id),
            "start_date": "2026-12-04",
            "end_date": "2026-12-05",
            "adults": 2,
        },
        headers=user.headers,
    )
    assert trip.status_code == 201, trip.text
    trip_id = str(trip.json()["id"])
    prefs = await client.put(
        f"{V1}/trips/{trip_id}/preferences",
        json={
            "interests": ["museum", "food"],
            "pace": "balanced",
            "budget_priority": "balanced",
            "transport_pref": "walking",
            "accommodation_type": "any",
            "step_free_required": False,
            "notes": None,
            "must_visit_place_ids": [],
        },
        headers=user.headers,
    )
    assert prefs.status_code == 200, prefs.text
    return trip_id


async def generate(
    client: httpx.AsyncClient,
    user: AuthUser,
    trip_id: str,
    mode: str,
    submitted: list[Job],
    sessions: Sessions,
    *,
    path: str | None = None,
) -> dict[str, Any]:
    started = await client.post(
        path or f"{V1}/trips/{trip_id}/generations", json={"mode": mode}, headers=user.headers
    )
    assert started.status_code == 202, started.text
    generation_id = started.json()["id"]
    while submitted:
        await jobs.run(*submitted.pop(0), sessions)
    done = await client.get(f"{V1}/generations/{generation_id}", headers=user.headers)
    assert done.status_code == 200, done.text
    body: dict[str, Any] = done.json()
    return body


async def stored_place_ids(db_session: AsyncSession, destination_id: uuid.UUID) -> set[str]:
    rows = await db_session.scalars(
        select(Place.id).where(Place.destination_id == destination_id, Place.is_active.is_(True))
    )
    return {str(place_id) for place_id in rows}


async def check_live_plan(
    client: httpx.AsyncClient,
    user: AuthUser,
    db_session: AsyncSession,
    trip_id: str,
    destination_id: uuid.UUID,
) -> dict[str, Any]:
    plan = await client.get(f"{V1}/trips/{trip_id}/itinerary", headers=user.headers)
    assert plan.status_code == 200, plan.text
    body: dict[str, Any] = plan.json()
    items = [item for day in body["days"] for item in day["items"]]
    assert items
    assert {item["place"]["id"] for item in items} <= await stored_place_ids(
        db_session, destination_id
    )
    rows = list(
        await db_session.scalars(
            select(Place).where(Place.id.in_([uuid.UUID(i["place"]["id"]) for i in items]))
        )
    )
    # Stored live places have no price and no hours, so no item can carry either.
    assert all(p.price_min is None and p.price_max is None for p in rows)
    assert {(p.price_label, p.hours_label) for p in rows} == {("unavailable", "unavailable")}
    codes = {finding["code"] for finding in body["findings"]}
    assert {"COST_INCOMPLETE", "HOURS_UNVERIFIED"} <= codes
    return body


async def origins(db_session: AsyncSession, trip_id: str) -> set[str]:
    rows = await db_session.scalars(
        select(ItineraryItem.origin).where(ItineraryItem.trip_id == uuid.UUID(trip_id))
    )
    return set(rows)


async def test_live_generation_tc_479_mock_plan_uses_stored_live_places_only(
    live_app: FastAPI,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sessions: Sessions,
    submitted: list[Job],
) -> None:
    live_app.dependency_overrides[get_model_provider] = lambda: MockProvider("ok", app_env="test")
    destination_id = await live_destination(db_session, sessions)
    async with client_for(live_app) as client:
        trip_id = await live_trip(client, auth_user, destination_id)
        done = await generate(client, auth_user, trip_id, "ai", submitted, sessions)
        assert (done["status"], done["outcome"]) == ("completed", "model"), done
        await check_live_plan(client, auth_user, db_session, trip_id, destination_id)


async def test_n4_live_v2_guide_uuid_reaches_the_prompt_saved_plan_and_api(
    live_app: FastAPI,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sessions: Sessions,
    submitted: list[Job],
) -> None:
    provider = GuideCitationMock()
    live_app.dependency_overrides[get_model_provider] = lambda: provider
    destination_id = await live_destination(db_session, sessions)
    async with client_for(live_app) as client:
        trip_id = await live_trip(client, auth_user, destination_id)
        done = await generate(client, auth_user, trip_id, "ai", submitted, sessions)
        assert (done["status"], done["retrieval_mode"]) == ("completed", "vector"), done
        plan = await check_live_plan(client, auth_user, db_session, trip_id, destination_id)

    [request] = provider.requests
    guide = next(p for p in request.context_passages if p.kind == "guide")
    assert guide.place_id is None  # guide UUIDs are independent of shortlist place UUIDs
    system, user = provider.prompts[0]
    prompt = json.loads(user.split("<request_json>\n", 1)[1].split("\n</request_json>", 1)[0])
    assert any(p["passage_id"] == str(guide.passage_id) for p in prompt["context_passages"])
    assert "passage_id in source_ids" in system
    assert provider.outputs[0].days[0].items[0].source_ids[0] == str(guide.passage_id)

    items = [item for day in plan["days"] for item in day["items"]]
    first = items[0]
    [source] = first["sources"]
    assert (source["chunk_id"], source["kind"], source["title"]) == (
        str(guide.passage_id),
        "guide",
        guide.title,
    )
    assert (source["source_name"], source["licence"]) == ("Wikivoyage", "CC BY-SA 4.0")
    assert source["attribution_text"]
    assert source["url"]
    assert source["retrieved_on"]
    stored = await db_session.get(ItineraryItem, uuid.UUID(first["id"]), populate_existing=True)
    assert stored is not None
    assert stored.source_chunk_ids == [guide.passage_id]
    version = await db_session.scalar(
        select(ItineraryVersion).where(ItineraryVersion.trip_id == uuid.UUID(trip_id))
    )
    assert version is not None
    assert version.snapshot["days"][0]["items"][0]["source_chunk_ids"] == [str(guide.passage_id)]
    record = await db_session.get(AiGeneration, uuid.UUID(done["id"]), populate_existing=True)
    assert record is not None
    assert record.validation_summary["unknown_source_ids"] == 2


async def test_live_generation_tc_479_rule_based_plan_for_a_live_city(
    live_app: FastAPI,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sessions: Sessions,
    submitted: list[Job],
) -> None:
    destination_id = await live_destination(db_session, sessions)
    async with client_for(live_app) as client:
        trip_id = await live_trip(client, auth_user, destination_id)
        done = await generate(client, auth_user, trip_id, "rule_based", submitted, sessions)
        assert done["status"] == "completed", done
        await check_live_plan(client, auth_user, db_session, trip_id, destination_id)
    assert await origins(db_session, trip_id) == {"fallback_rule_based"}


async def test_live_generation_tc_480_provider_timeout_ends_in_the_labelled_rule_based_plan(
    live_app: FastAPI,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sessions: Sessions,
    submitted: list[Job],
) -> None:
    live_app.dependency_overrides[get_model_provider] = lambda: MockProvider(
        "timeout", app_env="test"
    )
    destination_id = await live_destination(db_session, sessions)
    async with client_for(live_app) as client:
        trip_id = await live_trip(client, auth_user, destination_id)
        done = await generate(client, auth_user, trip_id, "ai", submitted, sessions)
        assert (done["status"], done["outcome"]) == ("completed", "fallback_rule_based"), done
        assert done["fallback_reason"] == "provider_timeout"
        await check_live_plan(client, auth_user, db_session, trip_id, destination_id)
    assert await origins(db_session, trip_id) == {"fallback_rule_based"}


async def test_live_generation_tc_480_quota_fails_with_the_rule_based_option_which_plans(
    live_app: FastAPI,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sessions: Sessions,
    submitted: list[Job],
) -> None:
    live_app.dependency_overrides[get_model_provider] = lambda: MockProvider(
        "quota", app_env="test"
    )
    destination_id = await live_destination(db_session, sessions)
    async with client_for(live_app) as client:
        trip_id = await live_trip(client, auth_user, destination_id)
        failed = await generate(client, auth_user, trip_id, "ai", submitted, sessions)
        # IMD-44: quota ends in failed with the rule-based option, as for curated cities.
        assert (failed["status"], failed["failure_reason"]) == (
            "failed",
            "provider_quota_exhausted",
        )
        assert failed["next_action"] == "retry_rule_based"

        done = await generate(client, auth_user, trip_id, "rule_based", submitted, sessions)
        assert done["status"] == "completed", done
        await check_live_plan(client, auth_user, db_session, trip_id, destination_id)
    assert await origins(db_session, trip_id) == {"fallback_rule_based"}
