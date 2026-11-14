"""API-22 and API-23, the generation job (§6.4, §6.6.4, §8.2; IMP-210: TC-012, TC-151, TC-162;
IMP-305: TC-114 to TC-119, TC-134, TC-135, TC-309; IMP-502: TC-011, TC-191, TC-192; FR-024,
FR-025, FR-031, FR-038, FR-057, NFR-008, IMD-24).

MOCK provider, or the Gemini adapter replaying the ok fixture through a fake transport; the socket
guard of tests/conftest.py blocks every provider host. API-22's
job is captured instead of started, and each test runs it with ``jobs.run`` on its rolled-back
session, so the request and the job never share the session at the same time.
"""

import asyncio
import json
import logging
import re
import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import UTC, datetime, timedelta
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

from app.ai.errors import ProviderUnavailable
from app.ai.factory import get_model_provider
from app.ai.providers.base import ModelProvider
from app.ai.providers.gemini import GeminiProvider
from app.ai.providers.mock import MockProvider
from app.core.config import MockScenario, Settings
from app.db.models import (
    AiGeneration,
    Destination,
    ItineraryDay,
    ItineraryItem,
    ItineraryVersion,
    Place,
    Trip,
)
from app.generation import jobs, pipeline, ranking, records, repository
from app.itinerary import repository as itinerary_repository
from app.places import seed
from app.schemas.ai import GenerationRequest, ItineraryOutput, ProviderResult

REPO_ROOT = Path(__file__).resolve().parents[4]
SAMPLETON = REPO_ROOT / "data" / "fixtures" / "sampleton"
GEMINI_OK = REPO_ROOT / "apps/api/tests/fixtures/provider_recordings/gemini/ok.json"
FIXTURE_PLACES = ("00000000-0000-4000-8000-000000000001", "00000000-0000-4000-8000-000000000005")
NOTES = "We like quiet mornings near the river."
PREFERENCES: dict[str, Any] = {
    "interests": ["museum", "food"],
    "pace": "balanced",
    "budget_priority": "balanced",
    "transport_pref": "walking",
    "accommodation_type": "any",
    "step_free_required": False,
    "notes": NOTES,
}
TERMINAL = ("completed", "failed")

Job = tuple[uuid.UUID, ModelProvider]
Sessions = Callable[[], AbstractAsyncContextManager[AsyncSession]]


@pytest_asyncio.fixture
async def sampleton(db_session: AsyncSession) -> Destination:
    await seed.load_fixture(db_session, seed.read_fixture(SAMPLETON))
    destination = await db_session.scalar(
        select(Destination).where(Destination.slug == "sampleton")
    )
    assert destination is not None
    return destination


@pytest.fixture
def submitted(api_app: FastAPI) -> list[Job]:
    """The jobs API-22 submitted, in order, instead of asyncio tasks."""
    queue: list[Job] = []
    api_app.dependency_overrides[jobs.get_submit] = lambda: lambda gid, p: queue.append((gid, p))
    return queue


@pytest.fixture
def sessions(db_session: AsyncSession) -> Sessions:
    """The job's transactions, as savepoints of the test's rolled-back session."""

    @asynccontextmanager
    async def job_transaction() -> AsyncIterator[AsyncSession]:
        async with db_session.begin_nested():
            yield db_session

    return job_transaction


def use_provider(app: FastAPI, scenario: MockScenario) -> None:
    app.dependency_overrides[get_model_provider] = lambda: MockProvider(scenario, app_env="test")


async def acknowledge_notice(client: httpx.AsyncClient, user: AuthUser) -> None:
    response = await client.patch(
        "/api/v1/me", json={"ai_notice_acknowledged": True}, headers=user.headers
    )
    assert response.status_code == 200, response.text


async def create_trip(
    client: httpx.AsyncClient,
    user: AuthUser,
    destination: Destination,
    *,
    prefs: bool = True,
    acknowledge: bool = True,
) -> str:
    if acknowledge:
        await acknowledge_notice(client, user)
    response = await client.post(
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
    assert response.status_code == 201, response.text
    trip_id: str = response.json()["id"]
    if prefs:
        saved = await client.put(
            f"/api/v1/trips/{trip_id}/preferences",
            json={**PREFERENCES, "must_visit_place_ids": []},
            headers=user.headers,
        )
        assert saved.status_code == 200, saved.text
    return trip_id


@pytest_asyncio.fixture
async def trip(api_client: httpx.AsyncClient, auth_user: AuthUser, sampleton: Destination) -> str:
    return await create_trip(api_client, auth_user, sampleton)


async def start(
    client: httpx.AsyncClient, user: AuthUser, trip_id: str, **body: Any
) -> httpx.Response:
    return await client.post(
        f"/api/v1/trips/{trip_id}/generations", json=body or {"mode": "ai"}, headers=user.headers
    )


async def poll(
    client: httpx.AsyncClient,
    user: AuthUser,
    generation_id: str,
    queue: list[Job],
    sessions: Sessions,
) -> dict[str, Any]:
    """Poll API-23 until a terminal status, running the submitted jobs between polls."""
    for _ in range(5):
        response = await client.get(f"/api/v1/generations/{generation_id}", headers=user.headers)
        assert response.status_code == 200, response.text
        body: dict[str, Any] = response.json()
        if body["status"] in TERMINAL:
            return body
        while queue:
            await jobs.run(*queue.pop(0), sessions)
    raise AssertionError("generation did not finish")


async def trip_destination(session: AsyncSession, trip_id: str) -> uuid.UUID:
    destination = await session.scalar(
        select(Trip.destination_id).where(Trip.id == uuid.UUID(trip_id))
    )
    assert destination is not None
    return destination


async def plan_rows(session: AsyncSession, trip_id: str) -> tuple[list[uuid.UUID], int]:
    trip = uuid.UUID(trip_id)
    days = list(await session.scalars(select(ItineraryDay.id).where(ItineraryDay.trip_id == trip)))
    items = await session.scalar(
        select(func.count()).select_from(ItineraryItem).where(ItineraryItem.trip_id == trip)
    )
    return days, int(items or 0)


async def queued_row(
    session: AsyncSession, user: AuthUser, trip_id: str, mode: str = "ai"
) -> uuid.UUID:
    """An active generation inserted directly, as another request for the trip would leave it."""
    return await repository.create_queued(
        session,
        trip_id=uuid.UUID(trip_id),
        user_id=user.user_id,
        provider="MOCK",
        model_id="mock-v1",
        prompt_template_id="itinerary_generate",
        prompt_version="v1",
        mapping_version="pm-2",
        scope="full",
        request_hash=records.request_hash({"trip_id": trip_id, "mode": mode}),
    )


# TC-134, TC-162, TC-012, TC-151


@pytest.mark.asyncio
async def test_tc_134_tc_162_mock_generation_completes_with_no_network_call(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    trip: str,
    submitted: list[Job],
    sessions: Sessions,
    provider_socket_guard: Any,
    caplog: pytest.LogCaptureFixture,
) -> None:
    assert provider_socket_guard.active  # any Gemini host lookup would raise

    response = await start(api_client, auth_user, trip)
    assert response.status_code == 202, response.text
    queued = response.json()
    assert (queued["status"], queued["scope"], queued["mode"]) == ("queued", "full", "ai")
    assert queued["itinerary_version_id"] is None

    with caplog.at_level(logging.DEBUG):
        done = await poll(api_client, auth_user, queued["id"], submitted, sessions)

    assert (done["status"], done["outcome"], done["failure_reason"]) == ("completed", "model", None)
    assert done["plan_revision"] == 1
    assert done["latency_ms"] is not None
    assert done["validation_summary"] == {"errors": 0, "warnings": 0, "infos": 0}
    days, items = await plan_rows(db_session, trip)
    assert len(days) == 3
    assert items > 0
    version = await db_session.get(ItineraryVersion, uuid.UUID(done["itinerary_version_id"]))
    assert version is not None
    assert (version.version_no, version.reason, version.plan_revision) == (1, "generation", 1)
    assert version.snapshot["schema"] == "snap-1"
    assert [d["day_number"] for d in version.snapshot["days"]] == [1, 2, 3]
    trip_row = await db_session.get(Trip, uuid.UUID(trip), populate_existing=True)
    assert trip_row is not None
    assert (trip_row.plan_revision, trip_row.status, trip_row.plan_stale) == (1, "ready", False)
    item_rows = list(
        await db_session.scalars(
            select(ItineraryItem).where(ItineraryItem.trip_id == uuid.UUID(trip))
        )
    )
    assert {item.origin for item in item_rows} == {"model"}
    assert all(item.cost_label is not None and item.source_chunk_ids == [] for item in item_rows)
    # FR-125 AC2: notes and model text never reach the log.
    assert NOTES not in caplog.text
    assert "SAMPLE note" not in caplog.text


@pytest.mark.asyncio
async def test_tc_012_tc_151_the_record_names_provider_model_template_and_mapping(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    trip: str,
    submitted: list[Job],
    sessions: Sessions,
) -> None:
    generation_id = (await start(api_client, auth_user, trip)).json()["id"]
    done = await poll(api_client, auth_user, generation_id, submitted, sessions)

    assert (done["provider"], done["model_id"], done["prompt_version"]) == ("MOCK", "mock-v1", "v2")
    # No index in this test, so retrieval falls back; API-23 says so (A1 §6.12).
    assert done["retrieval_mode"] == "lexical_fallback"
    assert done["embedding_model_id"] == "mock-embed-v1"
    assert done["retrieval_ms"] >= 0
    row = await db_session.get(AiGeneration, uuid.UUID(generation_id), populate_existing=True)
    assert row is not None
    assert (row.provider, row.model_id, row.prompt_template_id, row.prompt_version) == (
        "MOCK",
        "mock-v1",
        "itinerary_generate",
        "v2",
    )
    assert (row.mapping_version, row.adapter_version) == ("pm-2", "mock-1")
    assert row.generation_settings == {
        "truncated_count": 0,
        "passages_sent": 0,
        "passages_dropped": 0,
    }
    assert len(row.request_hash) == 64
    assert row.retrieval_mode == "lexical_fallback"
    assert row.embedding_model_id == "mock-embed-v1"


# TC-114, IMD-24: the AI notice comes first


@pytest.mark.asyncio
async def test_tc_114_mode_ai_needs_the_ai_notice_then_answers_202(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sampleton: Destination,
    submitted: list[Job],
) -> None:
    trip_id = await create_trip(api_client, auth_user, sampleton, acknowledge=False)

    refused = await start(api_client, auth_user, trip_id)

    assert refused.status_code == 422
    error = refused.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert [detail["field"] for detail in error["details"]] == ["ai_notice"]
    assert submitted == []
    rows = select(func.count()).select_from(AiGeneration)
    assert await db_session.scalar(rows.where(AiGeneration.trip_id == uuid.UUID(trip_id))) == 0

    await acknowledge_notice(api_client, auth_user)
    started = await start(api_client, auth_user, trip_id)

    assert started.status_code == 202, started.text
    assert uuid.UUID(started.json()["id"])
    assert len(submitted) == 1


# TC-116, G-01: idempotency and the in-progress conflict


@pytest.mark.asyncio
async def test_tc_116_same_request_while_active_returns_the_same_generation(
    api_client: httpx.AsyncClient, auth_user: AuthUser, trip: str, submitted: list[Job]
) -> None:
    first = await start(api_client, auth_user, trip)
    again = await start(api_client, auth_user, trip)

    assert (first.status_code, again.status_code) == (202, 200)
    assert again.json()["id"] == first.json()["id"]
    assert len(submitted) == 1


@pytest.mark.asyncio
async def test_a_different_request_while_active_is_refused(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    trip: str,
    submitted: list[Job],
) -> None:
    active_id = await queued_row(db_session, auth_user, trip, mode="rule_based")

    response = await start(api_client, auth_user, trip)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "GENERATION_IN_PROGRESS"
    assert response.json()["error"]["details"] == [
        {"field": "generation_id", "message": str(active_id)}
    ]
    assert submitted == []


# TC-115 and the other create rules


@pytest.mark.asyncio
async def test_tc_115_an_incomplete_trip_lists_the_missing_fields(
    api_client: httpx.AsyncClient, auth_user: AuthUser, sampleton: Destination, submitted: list[Job]
) -> None:
    trip_id = await create_trip(api_client, auth_user, sampleton, prefs=False)

    response = await start(api_client, auth_user, trip_id)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert [d["field"] for d in error["details"]] == ["preferences"]
    assert submitted == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("body", "field"), [({"mode": "ai", "scope": "day"}, "scope"), ({"mode": "plan"}, "mode")]
)
async def test_unknown_fields_and_modes_are_refused(
    api_client: httpx.AsyncClient,
    auth_user: AuthUser,
    trip: str,
    submitted: list[Job],
    body: dict[str, Any],
    field: str,
) -> None:
    response = await start(api_client, auth_user, trip, **body)

    assert response.status_code == 422
    assert field in [d["field"] for d in response.json()["error"]["details"]]
    assert submitted == []


@pytest.mark.asyncio
async def test_a_trip_with_an_itinerary_is_refused(
    api_client: httpx.AsyncClient,
    auth_user: AuthUser,
    trip: str,
    submitted: list[Job],
    sessions: Sessions,
) -> None:
    await poll(
        api_client,
        auth_user,
        (await start(api_client, auth_user, trip)).json()["id"],
        submitted,
        sessions,
    )

    response = await start(api_client, auth_user, trip)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


# TC-117: polling shows each status while the job runs


class WatchingProvider(MockProvider):
    """Reads API-23 during the provider call, when the job is running."""

    def __init__(self, read: Callable[[], Any]) -> None:
        super().__init__("ok", app_env="test")
        self.read = read
        self.seen: list[str] = []

    async def generate_itinerary(
        self, request: GenerationRequest
    ) -> ProviderResult[ItineraryOutput]:
        self.seen.append(await self.read())
        return await super().generate_itinerary(request)


@pytest.mark.asyncio
async def test_tc_117_polling_returns_the_status_while_the_job_runs(
    api_client: httpx.AsyncClient,
    auth_user: AuthUser,
    trip: str,
    submitted: list[Job],
    sessions: Sessions,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started = await start(api_client, auth_user, trip)
    generation_id = started.json()["id"]
    assert started.json()["status"] == "queued"

    async def status() -> str:
        url = f"/api/v1/generations/{generation_id}"
        response = await api_client.get(url, headers=auth_user.headers)
        assert response.status_code == 200, response.text
        value: str = response.json()["status"]
        return value

    provider = WatchingProvider(status)
    seen_at_save: list[str] = []
    real_save = pipeline.itinerary_service.save_generated_plan

    async def watched_save(*args: Any, **kwargs: Any) -> Any:
        seen_at_save.append(await status())
        return await real_save(*args, **kwargs)

    monkeypatch.setattr(pipeline.itinerary_service, "save_generated_plan", watched_save)
    await jobs.run(uuid.UUID(generation_id), provider, sessions)

    assert provider.seen == ["running"]
    assert seen_at_save == ["validating"]
    assert await status() == "completed"


# NFR-008: a failing job leaves the previous plan as it was


@pytest.mark.asyncio
async def test_tc_118_a_failed_job_gives_a_reason_and_leaves_the_previous_plan_untouched(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    trip: str,
    submitted: list[Job],
    sessions: Sessions,
) -> None:
    await poll(
        api_client,
        auth_user,
        (await start(api_client, auth_user, trip)).json()["id"],
        submitted,
        sessions,
    )
    before = await plan_rows(db_session, trip)

    # API-22 refuses a trip with a plan, so the second job is started as API-31 will start it.
    generation_id = await queued_row(db_session, auth_user, trip)
    await jobs.run(generation_id, MockProvider("quota", app_env="test"), sessions)
    failed = await poll(api_client, auth_user, str(generation_id), submitted, sessions)

    # A timeout now ends in the rule-based plan (IMP-402); quota still fails (IMD-44).
    assert (failed["status"], failed["outcome"]) == ("failed", "failed")
    assert failed["failure_reason"] == "provider_quota_exhausted"
    assert failed["failure_message"] == "AI generation is paused for today."
    assert failed["next_action"] == "retry_rule_based"
    assert failed["itinerary_version_id"] is None
    assert await plan_rows(db_session, trip) == before
    trip_row = await db_session.get(Trip, uuid.UUID(trip), populate_existing=True)
    assert trip_row is not None
    assert trip_row.plan_revision == 1


def replaying_gemini() -> GeminiProvider:
    """The Gemini adapter answering with the ok fixture, naming two places of the real prompt.

    The fixture's place IDs belong to the SAMPLE unit-test request, so they are swapped for IDs
    the request carried; the fake transport keeps everything else as recorded.
    """
    recording = json.loads(GEMINI_OK.read_text(encoding="utf-8"))

    def respond(request: httpx.Request) -> httpx.Response:
        sent = re.findall(r'place_id\\?": ?\\?"([0-9a-f-]{36})', request.content.decode())
        body = json.dumps(recording["body"])
        for fixture_id, real_id in zip(FIXTURE_PLACES, sent, strict=False):
            body = body.replace(fixture_id, real_id)
        return httpx.Response(recording["http_status"], json=json.loads(body))

    settings = Settings(gemini_api_key="not-a-real-key", gemini_model_id="gemini-3.5-flash-lite")
    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    return GeminiProvider(settings, http_client=client)


@pytest.mark.asyncio
async def test_the_recorded_gemini_answer_runs_the_whole_pipeline(
    api_app: FastAPI,
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    trip: str,
    submitted: list[Job],
    sessions: Sessions,
) -> None:
    provider = replaying_gemini()
    api_app.dependency_overrides[get_model_provider] = lambda: provider
    generation_id = (await start(api_client, auth_user, trip)).json()["id"]

    done = await poll(api_client, auth_user, generation_id, submitted, sessions)

    assert (done["status"], done["outcome"]) == ("completed", "model")
    assert (done["provider"], done["model_id"]) == ("GEMINI", "gemini-3.5-flash-lite")
    row = await db_session.get(AiGeneration, uuid.UUID(generation_id), populate_existing=True)
    assert row is not None
    assert (row.input_tokens, row.output_tokens, row.thinking_tokens) == (812, 146, 37)
    assert row.adapter_version == "gemini-interactions-1"
    assert row.generation_settings["api_style"] == "interactions"
    assert row.generation_settings["structured_output"] is True
    assert row.generation_settings["truncated_count"] == 0
    items = list(
        await db_session.scalars(
            select(ItineraryItem)
            .where(ItineraryItem.trip_id == uuid.UUID(trip))
            .order_by(ItineraryItem.position)
        )
    )
    assert [(item.origin, item.note_origin) for item in items] == [("model", "ai")] * 2
    assert items[0].note == "Start at the fort while it is cool."
    assert all(item.cost_currency == "GBP" and item.cost_label for item in items)


@pytest.mark.asyncio
async def test_tc_139_saved_times_are_the_recalculation_and_not_the_models(
    api_app: FastAPI,
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    trip: str,
    submitted: list[Job],
    sessions: Sessions,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The model's start times are injected; the saved ones are 09:00 plus durations and travel."""
    injected = "06:06"
    real_generate = MockProvider.generate_itinerary

    async def with_odd_times(self: MockProvider, request: GenerationRequest) -> Any:
        result = await real_generate(self, request)
        for day in result.output.days:
            for item in day.items:
                item.start_time = injected
        return result

    monkeypatch.setattr(MockProvider, "generate_itinerary", with_odd_times)
    use_provider(api_app, "ok")
    queued = (await start(api_client, auth_user, trip)).json()

    done = await poll(api_client, auth_user, queued["id"], submitted, sessions)

    assert done["status"] == "completed"
    rows = await db_session.execute(
        select(ItineraryItem, Place, ItineraryDay.day_number)
        .join(Place, Place.id == ItineraryItem.place_id)
        .join(ItineraryDay, ItineraryDay.id == ItineraryItem.day_id)
        .where(ItineraryItem.trip_id == uuid.UUID(trip))
        .order_by(ItineraryDay.day_number, ItineraryItem.position)
    )
    clock, day_number, seen = 0, 0, 0
    for item, place, number in rows:
        seen += 1
        assert item.start_time.strftime("%H:%M") != injected
        assert item.duration_min == place.typical_duration_min
        if number != day_number:
            day_number, clock = number, 9 * 60
            assert item.travel_from_prev_min is None
        else:
            assert item.travel_source == "fallback_estimate"  # no routing key in tests
            assert item.travel_mode == "walking"
            clock += item.travel_from_prev_min + 15
        assert item.start_time.hour * 60 + item.start_time.minute == clock
        clock += item.duration_min
    assert seen > 0
    version = await db_session.get(ItineraryVersion, uuid.UUID(done["itinerary_version_id"]))
    assert version is not None
    assert "travel_from_prev_min" not in version.snapshot["days"][0]["items"][0]  # §5.2


@pytest.mark.asyncio
async def test_a_second_generation_replaces_the_plan_and_clears_plan_stale(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    trip: str,
    submitted: list[Job],
    sessions: Sessions,
) -> None:
    await poll(
        api_client,
        auth_user,
        (await start(api_client, auth_user, trip)).json()["id"],
        submitted,
        sessions,
    )
    first_days, _ = await plan_rows(db_session, trip)
    await db_session.execute(update(Trip).where(Trip.id == uuid.UUID(trip)).values(plan_stale=True))

    generation_id = await queued_row(db_session, auth_user, trip)
    await jobs.run(generation_id, MockProvider("ok", app_env="test"), sessions)

    done = await poll(api_client, auth_user, str(generation_id), submitted, sessions)
    assert (done["status"], done["plan_revision"]) == ("completed", 2)
    second_days, _ = await plan_rows(db_session, trip)
    assert len(second_days) == len(first_days)
    assert not set(second_days) & set(first_days)
    version = await db_session.get(ItineraryVersion, uuid.UUID(done["itinerary_version_id"]))
    assert version is not None
    assert (version.version_no, version.reason, version.plan_revision) == (2, "generation", 2)
    trip_row = await db_session.get(Trip, uuid.UUID(trip), populate_existing=True)
    assert trip_row is not None
    assert (trip_row.plan_revision, trip_row.plan_stale) == (2, False)


@pytest.mark.asyncio
async def test_a_crash_between_items_and_version_leaves_the_previous_plan_intact(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    trip: str,
    submitted: list[Job],
    sessions: Sessions,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await poll(
        api_client,
        auth_user,
        (await start(api_client, auth_user, trip)).json()["id"],
        submitted,
        sessions,
    )
    before = await plan_rows(db_session, trip)

    async def crash(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("injected crash after the items were written")

    monkeypatch.setattr(itinerary_repository, "insert_version", crash)
    generation_id = await queued_row(db_session, auth_user, trip)
    await jobs.run(generation_id, MockProvider("ok", app_env="test"), sessions)

    failed = await poll(api_client, auth_user, str(generation_id), submitted, sessions)
    assert (failed["status"], failed["failure_reason"]) == ("failed", "internal")
    assert failed["itinerary_version_id"] is None
    assert await plan_rows(db_session, trip) == before
    trip_row = await db_session.get(Trip, uuid.UUID(trip), populate_existing=True)
    assert trip_row is not None
    assert trip_row.plan_revision == 1
    versions = select(func.count()).select_from(ItineraryVersion)
    assert await db_session.scalar(versions.where(ItineraryVersion.trip_id == trip_row.id)) == 1


@pytest.mark.asyncio
async def test_tc_135_tc_307_an_id_outside_the_shortlist_is_never_saved_and_repair_drops_it(
    api_app: FastAPI,
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    trip: str,
    submitted: list[Job],
    sessions: Sessions,
) -> None:
    use_provider(api_app, "unknown_place")
    generation_id = (await start(api_client, auth_user, trip)).json()["id"]

    done = await poll(api_client, auth_user, generation_id, submitted, sessions)

    # IMP-502: step 8 drops the item, a deterministic repair; the rest of the answer is saved.
    assert (done["status"], done["outcome"]) == ("completed", "model_repaired")
    assert (done["failure_reason"], done["fallback_reason"]) == (None, None)
    assert (done["deterministic_repairs"], done["repair_attempts"]) == (1, 0)
    places = set(
        await db_session.scalars(
            select(Place.id).where(
                Place.destination_id == (await trip_destination(db_session, trip))
            )
        )
    )
    saved = set(
        await db_session.scalars(
            select(ItineraryItem.place_id).where(ItineraryItem.trip_id == uuid.UUID(trip))
        )
    )
    assert saved
    assert saved <= places
    row = await db_session.get(AiGeneration, uuid.UUID(generation_id), populate_existing=True)
    assert row is not None
    assert (row.validation_summary["invalid_ids"], row.validation_summary["rejected_items"]) == (
        1,
        1,
    )
    assert "provider_failure" not in row.validation_summary


class Logged(MockProvider):
    """The mock with a call log: every request generate_itinerary received."""

    def __init__(self, scenario: MockScenario) -> None:
        super().__init__(scenario, app_env="test")
        self.calls: list[GenerationRequest] = []

    async def generate_itinerary(self, request: GenerationRequest) -> Any:
        self.calls.append(request)
        return await super().generate_itinerary(request)


def use_logged(app: FastAPI, scenario: MockScenario) -> Logged:
    provider = Logged(scenario)
    app.dependency_overrides[get_model_provider] = lambda: provider
    return provider


@pytest.mark.asyncio
async def test_tc_011_invalid_output_goes_to_one_repair_call_never_a_blind_retry(
    api_app: FastAPI,
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    trip: str,
    submitted: list[Job],
    sessions: Sessions,
) -> None:
    provider = use_logged(api_app, "invalid_json")
    generation_id = (await start(api_client, auth_user, trip)).json()["id"]

    done = await poll(api_client, auth_user, generation_id, submitted, sessions)

    assert len(provider.calls) == 2  # 1 generate + 1 repair (IMP-502)
    assert provider.calls[1].repair_context is not None
    assert (done["status"], done["outcome"]) == ("completed", "fallback_rule_based")
    assert (done["failure_reason"], done["fallback_reason"]) == (None, "invalid_output")
    assert done["repair_attempts"] == 1
    row = await db_session.get(AiGeneration, uuid.UUID(generation_id), populate_existing=True)
    assert row is not None
    assert row.validation_summary["kind"] == "malformed_json"


@pytest.mark.asyncio
async def test_tc_191_repair_fixes_the_overlap_deterministically_without_a_model_call(
    api_app: FastAPI,
    api_client: httpx.AsyncClient,
    auth_user: AuthUser,
    trip: str,
    submitted: list[Job],
    sessions: Sessions,
) -> None:
    provider = use_logged(api_app, "flawed")  # the trip has no must-visit place: overlap only
    generation_id = (await start(api_client, auth_user, trip)).json()["id"]

    done = await poll(api_client, auth_user, generation_id, submitted, sessions)

    # FR-057 AC1: step 9 re-times the overlap in code; nothing is left to repair, no model call.
    assert len(provider.calls) == 1
    assert (done["status"], done["outcome"]) == ("completed", "model")
    assert (done["deterministic_repairs"], done["repair_attempts"]) == (0, 0)
    body = await itinerary(api_client, auth_user, trip)
    assert [f for f in body["findings"] if f["code"] == "OVERLAP"] == []


@pytest.mark.asyncio
async def test_tc_192_repair_leaves_what_it_cannot_fix_as_a_warning_after_one_call(
    api_app: FastAPI,
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sampleton: Destination,
    submitted: list[Job],
    sessions: Sessions,
) -> None:
    provider = use_logged(api_app, "flawed")  # every day full: no room for the must-visit place
    square = await place_id(db_session, "Sample Clock Square (sample)")
    trip_id = await trip_with(api_client, auth_user, sampleton, must_visit=[square])

    generation_id = (await start(api_client, auth_user, trip_id)).json()["id"]
    done = await poll(api_client, auth_user, generation_id, submitted, sessions)

    assert len(provider.calls) == 2  # FR-057 AC2: at most one repair call
    context = provider.calls[1].repair_context
    assert context is not None
    assert "MUST_VISIT_MISSING" in [f.code for f in context.findings]
    assert (done["outcome"], done["repair_attempts"]) == ("model_repaired", 1)
    body = await itinerary(api_client, auth_user, trip_id)
    assert [f["place_id"] for f in body["findings"] if f["code"] == "MUST_VISIT_MISSING"] == [
        square
    ]  # FR-057 AC3


class SlowProvider(MockProvider):
    """Expires the job's timeout during the provider call, where a real timeout fires.

    A short wall-clock timeout can fire during the job's database work instead. SQLAlchemy then
    invalidates the cancelled connection, and here that connection holds the whole test's outer
    transaction. A real job's transaction() has a connection of its own.
    """

    def __init__(self, job_timeouts: list[asyncio.Timeout]) -> None:
        super().__init__("ok", app_env="test")
        self.job_timeouts = job_timeouts

    async def generate_itinerary(
        self, request: GenerationRequest
    ) -> ProviderResult[ItineraryOutput]:
        self.job_timeouts[0].reschedule(asyncio.get_running_loop().time())
        await asyncio.sleep(5)
        return await super().generate_itinerary(request)


@pytest.mark.asyncio
async def test_tc_119_the_job_timeout_fails_with_internal_and_says_timed_out(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    trip: str,
    sessions: Sessions,
    submitted: list[Job],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generation_id = await queued_row(db_session, auth_user, trip)
    job_timeouts: list[asyncio.Timeout] = []
    real_timeout = asyncio.timeout

    def recorded_timeout(delay: float | None) -> asyncio.Timeout:
        job_timeouts.append(real_timeout(delay))
        return job_timeouts[-1]

    monkeypatch.setattr(asyncio, "timeout", recorded_timeout)

    await jobs.run(generation_id, SlowProvider(job_timeouts), sessions)
    failed = await poll(api_client, auth_user, str(generation_id), submitted, sessions)

    assert (failed["status"], failed["failure_reason"]) == ("failed", "internal")
    assert (failed["failure_message"], failed["next_action"]) == ("Generation timed out.", "retry")
    assert await plan_rows(db_session, trip) == ([], 0)


@pytest.mark.asyncio
async def test_a_timeout_after_the_plan_commit_leaves_the_completed_row(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    trip: str,
    submitted: list[Job],
    sessions: Sessions,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    generation_id = (await start(api_client, auth_user, trip)).json()["id"]
    real_run = pipeline.run

    async def commit_then_time_out(*args: Any) -> None:
        await real_run(*args)
        raise TimeoutError

    monkeypatch.setattr(pipeline, "run", commit_then_time_out)
    with caplog.at_level(logging.INFO):
        await jobs.run(*submitted.pop(0), sessions)  # IllegalTransitionError escaped here before

    done = await poll(api_client, auth_user, generation_id, submitted, sessions)
    assert (done["status"], done["outcome"]) == ("completed", "model")
    assert done["failure_reason"] is None
    assert done["itinerary_version_id"] is not None
    assert (await plan_rows(db_session, trip))[1] > 0
    assert "timed out" not in caplog.text


@pytest.mark.asyncio
async def test_a_job_failure_after_the_plan_commit_leaves_the_completed_row(
    api_client: httpx.AsyncClient,
    auth_user: AuthUser,
    trip: str,
    submitted: list[Job],
    sessions: Sessions,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generation_id = (await start(api_client, auth_user, trip)).json()["id"]
    real_run = pipeline.run

    async def commit_then_fail(*args: Any) -> None:
        await real_run(*args)
        raise RuntimeError("after the commit")

    monkeypatch.setattr(pipeline, "run", commit_then_fail)
    await jobs.run(*submitted.pop(0), sessions)

    done = await poll(api_client, auth_user, generation_id, submitted, sessions)
    assert done["status"] == "completed"


@pytest.mark.asyncio
async def test_tc_309_the_reaper_closes_a_job_left_running_and_keeps_the_plan(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    trip: str,
    submitted: list[Job],
    sessions: Sessions,
) -> None:
    await poll(
        api_client,
        auth_user,
        (await start(api_client, auth_user, trip)).json()["id"],
        submitted,
        sessions,
    )
    before = await plan_rows(db_session, trip)
    generation_id = await queued_row(db_session, auth_user, trip)
    await repository.mark_running(db_session, generation_id)
    await db_session.execute(
        update(AiGeneration)
        .where(AiGeneration.id == generation_id)
        .values(created_at=func.now() - jobs.STALE_AFTER - timedelta(seconds=1))
    )

    count = await repository.fail_stale(
        db_session, jobs.STALE_AFTER, validation_summary=jobs.TIMED_OUT
    )

    assert count == 1
    reaped = await poll(api_client, auth_user, str(generation_id), submitted, sessions)
    assert (reaped["status"], reaped["failure_reason"]) == ("failed", "internal")
    assert await plan_rows(db_session, trip) == before


@pytest.mark.asyncio
async def test_api_23_reaps_a_stale_active_generation(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    trip: str,
    submitted: list[Job],
    sessions: Sessions,
) -> None:
    generation_id = await queued_row(db_session, auth_user, trip)
    await db_session.execute(
        update(AiGeneration)
        .where(AiGeneration.id == generation_id)
        .values(created_at=func.now() - jobs.STALE_AFTER - timedelta(seconds=1))
    )

    reaped = await poll(api_client, auth_user, str(generation_id), submitted, sessions)

    assert (reaped["status"], reaped["failure_reason"]) == ("failed", "internal")
    assert reaped["failure_message"] == "Generation timed out."


# Ownership: another user's trip or generation is 404, never 403


@pytest.mark.asyncio
async def test_another_users_trip_and_generation_are_not_found(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    trip: str,
    submitted: list[Job],
) -> None:
    other_id = await insert_auth_user(db_session)
    other = AuthUser(user_id=other_id, email=f"{other_id}@example.test")
    generation_id = (await start(api_client, auth_user, trip)).json()["id"]

    started = await start(api_client, other, trip)
    read = await api_client.get(f"/api/v1/generations/{generation_id}", headers=other.headers)
    missing = await api_client.get(f"/api/v1/generations/{uuid.uuid4()}", headers=auth_user.headers)

    for response in (started, read, missing):
        assert response.status_code == 404, response.text
        assert response.json()["error"]["code"] == "NOT_FOUND"
    assert len(submitted) == 1


@pytest.mark.asyncio
async def test_another_users_start_is_not_found_before_the_in_progress_conflict(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    trip: str,
    submitted: list[Job],
) -> None:
    other_id = await insert_auth_user(db_session)
    other = AuthUser(user_id=other_id, email=f"{other_id}@example.test")
    active_id = await queued_row(db_session, auth_user, trip, mode="rule_based")

    response = await start(api_client, other, trip)

    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert response.json()["error"]["details"] == []
    assert str(active_id) not in response.text
    assert submitted == []


@pytest.mark.asyncio
async def test_tc_121_the_request_is_built_from_the_stored_trip_with_its_notes_quoted(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sampleton: Destination,
    trip: str,
) -> None:
    from app.generation import request_builder

    build = {
        "trip_id": uuid.UUID(trip),
        "user_id": auth_user.user_id,
        "prompt_template_id": "itinerary_generate",
        "prompt_version": "v1",
    }
    first = await request_builder.build(db_session, **build)
    second = await request_builder.build(db_session, **build)

    assert GenerationRequest.model_validate(first.model_dump(mode="json")) == first
    assert first.preferences.notes_quoted == NOTES
    assert (
        NOTES
        not in first.model_copy(
            update={"preferences": first.preferences.model_copy(update={"notes_quoted": None})}
        ).model_dump_json()
    )
    assert request_builder.generation_request_hash(
        first
    ) == request_builder.generation_request_hash(second)


@pytest.mark.asyncio
async def test_the_request_holds_only_trip_data_and_shortlisted_places(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sampleton: Destination,
    trip: str,
) -> None:
    from app.generation import request_builder

    request = await request_builder.build(
        db_session,
        trip_id=uuid.UUID(trip),
        user_id=auth_user.user_id,
        prompt_template_id="itinerary_generate",
        prompt_version="v1",
    )

    active = dict(
        (
            await db_session.execute(
                select(Place.id, Place.category).where(
                    Place.destination_id == sampleton.id, Place.is_active.is_(True)
                )
            )
        ).all()
    )
    place_ids = [p.place_id for p in request.shortlist]
    assert len(set(place_ids)) == len(place_ids)
    assert set(place_ids) <= set(active)
    assert len(place_ids) <= ranking.shortlist_size(3) + 3  # the meal slots may add food places
    assert "stay" not in {active[place_id] for place_id in place_ids}
    assert request.trip.num_days == 3
    assert request.scope.kind == "full"
    assert request.preferences.notes_quoted == NOTES
    dumped = request.model_dump_json()
    assert auth_user.email not in dumped
    assert str(auth_user.user_id) not in dumped
    assert "Weekend in Sampleton" not in dumped


# IMP-402: the rule-based fallback planner (TC-145, TC-331; IMD-22, IMD-43, IMD-131)


@pytest.mark.asyncio
async def test_tc_145_fallback_an_unavailable_provider_saves_a_labelled_rule_based_plan(
    api_app: FastAPI,
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    trip: str,
    submitted: list[Job],
    sessions: Sessions,
) -> None:
    api_app.dependency_overrides[get_model_provider] = lambda: MockProvider(
        "ok", app_env="test", raise_error=ProviderUnavailable()
    )
    generation_id = (await start(api_client, auth_user, trip)).json()["id"]

    done = await poll(api_client, auth_user, generation_id, submitted, sessions)

    assert (done["status"], done["outcome"]) == ("completed", "fallback_rule_based")
    assert (done["failure_reason"], done["fallback_reason"]) == (None, "provider_unavailable")
    # IMD-43: a fallback after an AI attempt keeps the configured model and reports mode ai.
    assert (done["mode"], done["provider"], done["model_id"]) == ("ai", "MOCK", "mock-v1")
    items = list(
        await db_session.scalars(
            select(ItineraryItem).where(ItineraryItem.trip_id == uuid.UUID(trip))
        )
    )
    assert items
    assert {(i.origin, i.note, i.note_origin) for i in items} == {
        ("fallback_rule_based", None, "none")
    }
    version = await db_session.get(ItineraryVersion, uuid.UUID(done["itinerary_version_id"]))
    assert version is not None
    assert version.reason == "fallback"
    plan = await api_client.get(f"/api/v1/trips/{trip}/itinerary", headers=auth_user.headers)
    assert plan.status_code == 200, plan.text
    body = plan.json()
    assert body["source"]["outcome"] == "fallback_rule_based"
    assert {day["theme_origin"] for day in body["days"]} == {"none"}
    assert all(day["theme"].startswith(f"Day {day['day_number']} around ") for day in body["days"])
    assert {item["note_origin"] for day in body["days"] for item in day["items"]} == {"none"}


@pytest.mark.asyncio
async def test_tc_331_fallback_mode_rule_based_is_recorded_as_rule_based_planner_v1(
    api_app: FastAPI,
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sampleton: Destination,
    submitted: list[Job],
    sessions: Sessions,
) -> None:
    calls = 0

    class Counting(MockProvider):
        async def generate_itinerary(self, request: GenerationRequest) -> Any:
            nonlocal calls
            calls += 1
            return await super().generate_itinerary(request)

    api_app.dependency_overrides[get_model_provider] = lambda: Counting("ok", app_env="test")
    # Mode rule_based needs no AI notice (§6.4).
    trip_id = await create_trip(api_client, auth_user, sampleton, acknowledge=False)

    response = await start(api_client, auth_user, trip_id, mode="rule_based")
    assert response.status_code == 202, response.text
    queued = response.json()
    assert (queued["mode"], queued["provider"], queued["model_id"]) == (
        "rule_based",
        "MOCK",
        "rule_based_planner_v1",
    )
    done = await poll(api_client, auth_user, queued["id"], submitted, sessions)

    assert calls == 0
    assert (done["status"], done["outcome"]) == ("completed", "fallback_rule_based")
    assert (done["failure_reason"], done["fallback_reason"]) == (None, None)
    row = await db_session.get(AiGeneration, uuid.UUID(queued["id"]), populate_existing=True)
    assert row is not None
    assert (row.model_id, row.retrieval_mode, row.adapter_version) == (
        "rule_based_planner_v1",
        None,
        None,
    )


@pytest.mark.asyncio
async def test_fallback_mode_rule_based_twice_gives_the_same_plan(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sampleton: Destination,
    submitted: list[Job],
    sessions: Sessions,
) -> None:
    plans = []
    for _ in range(2):
        trip_id = await create_trip(api_client, auth_user, sampleton, acknowledge=False)
        queued = (await start(api_client, auth_user, trip_id, mode="rule_based")).json()
        await poll(api_client, auth_user, queued["id"], submitted, sessions)
        body = (
            await api_client.get(f"/api/v1/trips/{trip_id}/itinerary", headers=auth_user.headers)
        ).json()
        plans.append(
            [
                (
                    day["day_number"],
                    day["theme"],
                    [(i["place"]["id"], i["start_time"]) for i in day["items"]],
                )
                for day in body["days"]
            ]
        )

    assert plans[0] == plans[1]  # FR-036 AC2 through the whole pipeline


# IMP-406: must-visit places, explicit constraints and AI-written text (TC-141 to TC-144)


async def place_id(session: AsyncSession, name: str) -> str:
    found = await session.scalar(select(Place.id).where(Place.name == name))
    assert found is not None, name
    return str(found)


async def trip_with(
    client: httpx.AsyncClient,
    user: AuthUser,
    destination: Destination,
    *,
    must_visit: list[str],
    end_date: str = "2026-12-06",
    acknowledge: bool = True,
    **preferences: Any,
) -> str:
    if acknowledge:
        await acknowledge_notice(client, user)
    response = await client.post(
        "/api/v1/trips",
        json={
            "title": "Must-visit trip",
            "destination_id": str(destination.id),
            "start_date": "2026-12-04",
            "end_date": end_date,
            "adults": 2,
        },
        headers=user.headers,
    )
    assert response.status_code == 201, response.text
    trip_id: str = response.json()["id"]
    saved = await client.put(
        f"/api/v1/trips/{trip_id}/preferences",
        json={**PREFERENCES, **preferences, "must_visit_place_ids": must_visit},
        headers=user.headers,
    )
    assert saved.status_code == 200, saved.text
    return trip_id


async def itinerary(client: httpx.AsyncClient, user: AuthUser, trip_id: str) -> dict[str, Any]:
    response = await client.get(f"/api/v1/trips/{trip_id}/itinerary", headers=user.headers)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


@pytest.mark.asyncio
async def test_tc_141_must_visit_places_that_fit_are_all_in_the_plan(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sampleton: Destination,
    submitted: list[Job],
    sessions: Sessions,
) -> None:
    names = [
        "Sample Clock Square (sample)",
        "Sample Maritime Museum (sample)",
        "Sample Pier Bookshop (sample)",
    ]
    must_visit = [await place_id(db_session, name) for name in names]
    trip_id = await trip_with(api_client, auth_user, sampleton, must_visit=must_visit)

    # The rule-based plan places must-visit places first; the model's own answer is IMP-502's
    # deterministic repair to complete (§8.13).
    queued = (await start(api_client, auth_user, trip_id, mode="rule_based")).json()
    await poll(api_client, auth_user, queued["id"], submitted, sessions)

    body = await itinerary(api_client, auth_user, trip_id)
    planned = {item["place"]["id"] for day in body["days"] for item in day["items"]}
    assert set(must_visit) <= planned
    assert all(
        item["must_visit"] == (item["place"]["id"] in must_visit)
        for day in body["days"]
        for item in day["items"]
    )
    assert [f for f in body["findings"] if f["code"] == "MUST_VISIT_MISSING"] == []


@pytest.mark.asyncio
async def test_must_visit_place_is_forced_into_the_shortlist_beyond_the_cap(
    api_app: FastAPI,
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sampleton: Destination,
    submitted: list[Job],
    sessions: Sessions,
) -> None:
    sent: list[GenerationRequest] = []

    class Watching(MockProvider):
        async def generate_itinerary(self, request: GenerationRequest) -> Any:
            sent.append(request)
            return await super().generate_itinerary(request)

    api_app.dependency_overrides[get_model_provider] = lambda: Watching("ok", app_env="test")
    # A one-day trip shortlists 12 of the 30 places; a religious place matches no interest.
    abbey = await place_id(db_session, "Sample Quiet Abbey Ruins (sample)")
    trip_id = await trip_with(
        api_client, auth_user, sampleton, must_visit=[abbey], end_date="2026-12-04"
    )

    generation_id = (await start(api_client, auth_user, trip_id)).json()["id"]
    await poll(api_client, auth_user, generation_id, submitted, sessions)

    request = sent[0]  # a repair call may follow when no day has room for it (IMP-502)
    assert request.repair_context is None
    assert abbey in request.shortlist_ids()
    assert [str(i) for i in request.must_visit_place_ids] == [abbey]


@pytest.mark.asyncio
async def test_tc_142_must_visit_missing_names_the_place_and_the_reason(
    api_app: FastAPI,
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sampleton: Destination,
    submitted: list[Job],
    sessions: Sessions,
) -> None:
    use_provider(api_app, "flawed")  # leaves the first shortlisted must-visit place out
    square = await place_id(db_session, "Sample Clock Square (sample)")
    trip_id = await trip_with(api_client, auth_user, sampleton, must_visit=[square])

    generation_id = (await start(api_client, auth_user, trip_id)).json()["id"]
    done = await poll(api_client, auth_user, generation_id, submitted, sessions)

    # IMP-502: no day has room, so the error left gets the one repair call and stays visible.
    assert (done["status"], done["outcome"]) == ("completed", "model_repaired")
    assert done["validation_summary"]["errors"] >= 1
    body = await itinerary(api_client, auth_user, trip_id)
    [missing] = [f for f in body["findings"] if f["code"] == "MUST_VISIT_MISSING"]
    assert (missing["place_id"], missing["item_id"], missing["severity"]) == (square, None, "error")
    assert "Sample Clock Square (sample)" in missing["message"]
    assert "No day of the plan had room for it." in missing["message"]
    assert missing["suggested_fix"]
    planned = {item["place"]["id"] for day in body["days"] for item in day["items"]}
    assert square not in planned


@pytest.mark.asyncio
async def test_must_visit_missing_gives_a_filter_conflict_as_the_reason(
    api_app: FastAPI,
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sampleton: Destination,
    submitted: list[Job],
    sessions: Sessions,
) -> None:
    use_provider(api_app, "flawed")
    bridge = await place_id(db_session, "Sample Lantern Bridge (sample)")  # step_free false
    trip_id = await trip_with(
        api_client, auth_user, sampleton, must_visit=[bridge], step_free_required=True
    )

    generation_id = (await start(api_client, auth_user, trip_id)).json()["id"]
    await poll(api_client, auth_user, generation_id, submitted, sessions)

    body = await itinerary(api_client, auth_user, trip_id)
    [missing] = [f for f in body["findings"] if f["code"] == "MUST_VISIT_MISSING"]
    assert missing["place_id"] == bridge
    assert "It is not confirmed step-free." in missing["message"]
    assert missing["suggested_fix"].startswith("Change the trip's preferences")


@pytest.mark.asyncio
async def test_tc_143_tc_144_ai_text_and_retrieved_facts_are_separate_columns_and_labels(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    trip: str,
    submitted: list[Job],
    sessions: Sessions,
) -> None:
    generation_id = (await start(api_client, auth_user, trip)).json()["id"]
    await poll(api_client, auth_user, generation_id, submitted, sessions)

    body = await itinerary(api_client, auth_user, trip)
    days = body["days"]
    assert {(day["theme_origin"], day["theme"].startswith("SAMPLE")) for day in days} == {
        ("ai", True)
    }
    for day in days:
        for item in day["items"]:
            # FR-035 AC1: the AI note and the facts carry their own labels.
            assert (item["note_origin"], item["note"].startswith("SAMPLE")) == ("ai", True)
            assert item["place"]["hours_label"] in ("curated", "estimate", "unavailable")
            if item["cost"] is not None:
                assert item["cost"]["label"] in ("curated", "estimate", "unavailable")
    # FR-035 AC2: distinct columns; the model's text never lands in a fact column.
    rows = list(
        await db_session.scalars(
            select(ItineraryItem).where(ItineraryItem.trip_id == uuid.UUID(trip))
        )
    )
    assert all(row.note and row.note_origin == "ai" for row in rows)
    assert all(row.cost_label in (None, "curated", "estimate", "unavailable") for row in rows)


@pytest.mark.asyncio
@pytest.mark.parametrize("scope", ["user", "global"])
async def test_quota_tc_171_tc_172_tc_310_refuses_before_insert_and_provider_call(
    api_app: FastAPI,
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sampleton: Destination,
    submitted: list[Job],
    monkeypatch: pytest.MonkeyPatch,
    scope: str,
) -> None:
    monkeypatch.setenv("AI_DAILY_GENERATIONS_PER_USER", "1" if scope == "user" else "100")
    monkeypatch.setenv("AI_DAILY_GENERATIONS_GLOBAL", "1" if scope == "global" else "100")
    provider = Logged("ok")
    api_app.dependency_overrides[get_model_provider] = lambda: provider
    first = await create_trip(api_client, auth_user, sampleton)
    assert (await start(api_client, auth_user, first)).status_code == 202
    second = await create_trip(api_client, auth_user, sampleton)
    count = await db_session.scalar(select(func.count()).select_from(AiGeneration))
    refused = await start(api_client, auth_user, second)
    assert refused.status_code == 429, refused.text
    error = refused.json()["error"]
    assert error["code"] == "AI_QUOTA_REACHED"
    assert {d["field"]: d["message"] for d in error["details"]}["scope"] == scope
    assert int(refused.headers["Retry-After"]) == error["retry_after_s"]
    assert await db_session.scalar(select(func.count()).select_from(AiGeneration)) == count
    assert provider.calls == []
    allowed = await start(api_client, auth_user, second, mode="rule_based")
    assert allowed.status_code == 202, allowed.text
    assert allowed.json()["model_id"] == "rule_based_planner_v1"


@pytest.mark.asyncio
async def test_rate_limit_tc_353_does_not_insert_or_submit_again(
    api_app: FastAPI,
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    trip: str,
    submitted: list[Job],
) -> None:
    api_app.state.settings.rate_limit_per_min = 1
    assert (await start(api_client, auth_user, trip)).status_code == 202
    before = await db_session.scalar(select(func.count()).select_from(AiGeneration))
    refused = await start(api_client, auth_user, trip)
    assert refused.status_code == 429
    assert refused.json()["error"]["code"] == "RATE_LIMITED"
    assert int(refused.headers["Retry-After"]) > 0
    assert await db_session.scalar(select(func.count()).select_from(AiGeneration)) == before
    assert len(submitted) == 1


@pytest.mark.asyncio
async def test_purge_expired_generations_keeps_plan_and_version(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    trip: str,
    submitted: list[Job],
    sessions: Sessions,
) -> None:
    generation_id = (await start(api_client, auth_user, trip)).json()["id"]
    done = await poll(api_client, auth_user, generation_id, submitted, sessions)
    assert done["status"] == "completed"
    version_id = uuid.UUID(done["itinerary_version_id"])
    now = datetime.now(UTC)
    await db_session.execute(
        update(AiGeneration)
        .where(AiGeneration.id == uuid.UUID(generation_id))
        .values(retention_until=now - timedelta(seconds=1))
    )
    assert await repository.purge_expired(db_session, now) == 1
    version = await db_session.get(ItineraryVersion, version_id, populate_existing=True)
    assert version is not None
    assert version.generation_id is None
    days = list(
        await db_session.scalars(
            select(ItineraryDay)
            .where(ItineraryDay.trip_id == uuid.UUID(trip))
            .execution_options(populate_existing=True)
        )
    )
    assert days
    assert all(d.source_generation_id is None for d in days)
    assert (
        await api_client.get(f"/api/v1/trips/{trip}/itinerary", headers=auth_user.headers)
    ).status_code == 200
