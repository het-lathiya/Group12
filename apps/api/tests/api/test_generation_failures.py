"""Provider failure, timeout and quota outcomes end to end (IMP-403; FR-037: TC-148, TC-149,
TC-150; TC-005, TC-017, TC-307, TC-308; NFR-024; IMD-22, IMD-27, IMD-44).

Each failure is injected with a MOCK scenario or ``raise_error`` (IMD-27); no provider host is
reached. API-22 starts the generation, the captured job runs on the test's session, and API-23
and the itinerary tables are read afterwards.
"""

import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from fixtures.auth import AuthUser
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import factory
from app.ai.errors import (
    ALL_PROVIDER_ERRORS,
    ProviderAuthError,
    ProviderBadRequest,
    ProviderError,
    ProviderInvalidOutput,
    ProviderQuotaExhausted,
    ProviderRateLimited,
    ProviderTimeout,
    ProviderUnavailable,
)
from app.ai.factory import get_model_provider
from app.ai.providers.base import ModelProvider
from app.ai.providers.mock import MockProvider
from app.db.models import (
    Destination,
    ItineraryDay,
    ItineraryItem,
    ItineraryVersion,
    ItineraryWarning,
    Trip,
    TripPreferences,
)
from app.generation import fallback_planner, jobs, outcomes, records
from app.generation import repository as generation_repository
from app.places import seed

REPOSITORY = Path(__file__).resolve().parents[4]
SAMPLETON = REPOSITORY / "data" / "fixtures" / "sampleton"
VENDOR_TEXT = "vendor detail: echo of the prompt 7f3a"

Queue = list[tuple[uuid.UUID, ModelProvider]]


@pytest_asyncio.fixture
async def destination(db_session: AsyncSession) -> Destination:
    await seed.load_fixture(db_session, seed.read_fixture(SAMPLETON))
    row = await db_session.scalar(select(Destination).where(Destination.slug == "sampleton"))
    assert row is not None
    return row


@pytest.fixture
def queue(api_app: FastAPI) -> Queue:
    captured: Queue = []
    api_app.dependency_overrides[jobs.get_submit] = lambda: lambda g, p: captured.append((g, p))
    return captured


def use(app: FastAPI, provider: ModelProvider) -> ModelProvider:
    app.dependency_overrides[get_model_provider] = lambda: provider
    return provider


async def create_trip(client: httpx.AsyncClient, user: AuthUser, destination: Destination) -> str:
    created = await client.post(
        "/api/v1/trips",
        json={
            "title": "Failures in Sampleton",
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
    await client.patch("/api/v1/me", json={"ai_notice_acknowledged": True}, headers=user.headers)
    return trip_id


def job_sessions(session: AsyncSession) -> Any:
    @asynccontextmanager
    async def job_transaction() -> AsyncIterator[AsyncSession]:
        async with session.begin_nested():
            yield session

    return job_transaction


async def generate(
    client: httpx.AsyncClient,
    session: AsyncSession,
    captured: Queue,
    user: AuthUser,
    trip_id: str,
    mode: str = "ai",
) -> dict[str, Any]:
    """API-22, the captured job, then API-23's final body."""
    started = await client.post(
        f"/api/v1/trips/{trip_id}/generations", json={"mode": mode}, headers=user.headers
    )
    assert started.status_code == 202, started.text
    while captured:
        await jobs.run(*captured.pop(0), job_sessions(session))
    done = await client.get(f"/api/v1/generations/{started.json()['id']}", headers=user.headers)
    assert done.status_code == 200, done.text
    body: dict[str, Any] = done.json()
    return body


async def plan_state(session: AsyncSession, trip_id: str) -> dict[str, Any]:
    """The itinerary tables and the trip's revision and preferences, to compare after a failure."""
    trip_uuid = uuid.UUID(trip_id)
    session.expire_all()

    async def count(model: Any) -> int:
        statement = select(func.count()).select_from(model).where(model.trip_id == trip_uuid)
        return int(await session.scalar(statement) or 0)

    trip = await session.get(Trip, trip_uuid)
    prefs = await session.get(TripPreferences, trip_uuid)
    assert trip is not None
    assert prefs is not None
    items = await session.execute(
        select(ItineraryItem.id, ItineraryItem.place_id, ItineraryItem.start_time)
        .where(ItineraryItem.trip_id == trip_uuid)
        .order_by(ItineraryItem.id)
    )
    return {
        "plan_revision": trip.plan_revision,
        "status": trip.status,
        "updated_prefs": prefs.updated_at,
        "days": await count(ItineraryDay),
        "items": list(items),
        "warnings": await count(ItineraryWarning),
        "versions": await count(ItineraryVersion),
    }


def assert_fallback(body: dict[str, Any], cause: str) -> None:
    assert body["status"] == "completed"
    assert body["outcome"] == "fallback_rule_based"
    assert body["fallback_reason"] == cause  # validation_summary.provider_failure
    assert body["failure_reason"] is None  # IMD-22
    assert body["failure_message"] is None
    assert body["plan_revision"] is not None


async def assert_rule_based_plan(session: AsyncSession, trip_id: str) -> None:
    rows = list(
        await session.execute(
            select(ItineraryItem.origin, ItineraryItem.note).where(
                ItineraryItem.trip_id == uuid.UUID(trip_id)
            )
        )
    )
    assert rows
    assert {origin for origin, _ in rows} == {"fallback_rule_based"}
    assert {note for _, note in rows} == {None}  # IMD-131: no note on a fallback item


# TC-005, TC-017: every shared provider error has exactly one outcome and reason


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (ProviderTimeout(), outcomes.Outcome("fallback", "provider_timeout")),
        (ProviderRateLimited(), outcomes.Outcome("fallback", "provider_rate_limited")),
        (ProviderUnavailable(), outcomes.Outcome("fallback", "provider_unavailable")),
        (ProviderInvalidOutput("malformed_json"), outcomes.Outcome("fallback", "invalid_output")),
        (ProviderQuotaExhausted(), outcomes.Outcome("failed", "provider_quota_exhausted")),
        (ProviderAuthError(), outcomes.Outcome("failed", "config_error")),
        (ProviderBadRequest(), outcomes.Outcome("failed", "config_error")),
        (ProviderError(), outcomes.INTERNAL),
        (ValueError("a bug"), outcomes.INTERNAL),
    ],
)
def test_tc_005_tc_017_generation_failures_map_to_one_outcome(
    error: BaseException, expected: outcomes.Outcome
) -> None:
    assert outcomes.resolve(error) == expected


def test_generation_failures_every_shared_error_type_has_a_message_and_a_db_reason() -> None:
    for error_type in ALL_PROVIDER_ERRORS:
        error = (
            error_type("malformed_json") if error_type is ProviderInvalidOutput else error_type()
        )
        reason = outcomes.resolve(error).reason
        assert reason in records.FAILURE_REASONS
        assert reason in outcomes.MESSAGES
    assert set(outcomes.MESSAGES) == records.FAILURE_REASONS


@pytest.mark.parametrize(
    ("open_reason", "expected"),
    [
        ("provider_timeout", outcomes.Outcome("fallback", "provider_timeout")),
        ("provider_unavailable", outcomes.Outcome("fallback", "provider_unavailable")),
        ("provider_quota_exhausted", outcomes.Outcome("failed", "provider_quota_exhausted")),
        ("config_error", outcomes.Outcome("failed", "config_error")),
    ],
)
def test_generation_failures_an_open_breaker_keeps_a_quota_or_auth_cause(
    open_reason: Any, expected: outcomes.Outcome
) -> None:
    assert outcomes.resolve_open_breaker(open_reason) == expected  # IMD-44


# FR-037 AC1, TC-148: transient failures after the retries give the labelled rule-based plan


@pytest.mark.parametrize(
    ("provider", "cause"),
    [
        (lambda: MockProvider("timeout", app_env="test"), "provider_timeout"),
        (lambda: MockProvider("rate_limited", app_env="test"), "provider_rate_limited"),
        (
            lambda: MockProvider("ok", app_env="test", raise_error=ProviderUnavailable()),
            "provider_unavailable",
        ),
        (lambda: MockProvider("invalid_json", app_env="test"), "invalid_output"),
        (lambda: MockProvider("unknown_place", app_env="test"), "invalid_output"),  # TC-307
    ],
    ids=["timeout", "rate_limited", "unavailable", "invalid_json", "unknown_place"],
)
@pytest.mark.asyncio
async def test_tc_148_tc_307_generation_failures_fall_back_to_a_labelled_rule_based_plan(
    api_app: FastAPI,
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    queue: Queue,
    provider: Any,
    cause: str,
) -> None:
    use(api_app, provider())
    trip_id = await create_trip(api_client, auth_user, destination)

    body = await generate(api_client, db_session, queue, auth_user, trip_id)

    assert_fallback(body, cause)
    await assert_rule_based_plan(db_session, trip_id)
    read = await api_client.get(f"/api/v1/trips/{trip_id}/itinerary", headers=auth_user.headers)
    assert read.json()["source"]["outcome"] == "fallback_rule_based"


@pytest.mark.asyncio
async def test_generation_failures_a_breaker_opened_by_timeouts_falls_back_without_a_call(
    api_app: FastAPI,
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    queue: Queue,
) -> None:
    provider = use(api_app, MockProvider("ok", app_env="test"))
    breaker = factory.breaker_for(provider)
    for _ in range(5):
        breaker.record_failure(ProviderTimeout())
    assert breaker.state == "open"
    trip_id = await create_trip(api_client, auth_user, destination)

    body = await generate(api_client, db_session, queue, auth_user, trip_id)

    assert_fallback(body, "provider_timeout")
    await assert_rule_based_plan(db_session, trip_id)


# FR-037 AC2, TC-149: quota pauses AI with a rule-based option; config errors fail cleanly


@pytest.mark.parametrize(
    ("provider", "reason", "message"),
    [
        (
            lambda: MockProvider("quota", app_env="test"),
            "provider_quota_exhausted",
            "AI generation is paused for today.",
        ),
        (
            lambda: MockProvider("ok", app_env="test", raise_error=ProviderAuthError()),
            "config_error",
            "The AI service is not available right now.",
        ),
        (
            lambda: MockProvider("ok", app_env="test", raise_error=ProviderError()),
            "internal",
            "Something went wrong on our side.",
        ),
    ],
    ids=["quota", "auth", "unclassified"],
)
@pytest.mark.asyncio
async def test_tc_149_generation_failures_quota_and_config_errors_end_failed_with_no_plan(
    api_app: FastAPI,
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    queue: Queue,
    provider: Any,
    reason: str,
    message: str,
) -> None:
    use(api_app, provider())
    trip_id = await create_trip(api_client, auth_user, destination)
    before = await plan_state(db_session, trip_id)

    body = await generate(api_client, db_session, queue, auth_user, trip_id)

    assert (body["status"], body["outcome"], body["failure_reason"]) == ("failed", "failed", reason)
    assert body["failure_message"] == message
    assert body["next_action"] == ("retry" if reason == "internal" else "retry_rule_based")
    assert body["fallback_reason"] is None
    assert body["plan_revision"] is None
    assert await plan_state(db_session, trip_id) == before  # nothing written (FR-037 AC3)


@pytest.mark.asyncio
async def test_tc_149_generation_failures_after_quota_the_rule_based_option_builds_a_plan(
    api_app: FastAPI,
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    queue: Queue,
) -> None:
    provider = use(api_app, MockProvider("quota", app_env="test"))
    trip_id = await create_trip(api_client, auth_user, destination)
    failed = await generate(api_client, db_session, queue, auth_user, trip_id)
    assert failed["failure_reason"] == "provider_quota_exhausted"
    assert factory.breaker_for(provider).state == "open"  # later AI calls are paused

    paused = await generate(api_client, db_session, queue, auth_user, trip_id)
    rule_based = await generate(api_client, db_session, queue, auth_user, trip_id, "rule_based")

    assert paused["failure_reason"] == "provider_quota_exhausted"  # IMD-44: no fallback
    assert rule_based["status"] == "completed"
    assert rule_based["mode"] == "rule_based"
    assert rule_based["outcome"] == "fallback_rule_based"
    assert rule_based["fallback_reason"] is None
    await assert_rule_based_plan(db_session, trip_id)


# FR-037 AC3, TC-150, TC-308: the trip is never left half-changed


async def queued_on(session: AsyncSession, user: AuthUser, trip_id: str) -> uuid.UUID:
    """An AI generation for a trip that already has a plan, as a regeneration would leave it."""
    return await generation_repository.create_queued(
        session,
        trip_id=uuid.UUID(trip_id),
        user_id=user.user_id,
        provider="MOCK",
        model_id="mock-v1",
        prompt_template_id="itinerary_generate",
        prompt_version="v1",
        mapping_version="pm-2",
        scope="full",
        request_hash=records.request_hash({"trip_id": trip_id, "case": str(uuid.uuid4())}),
    )


@pytest.mark.parametrize(
    "provider",
    [
        lambda: MockProvider("quota", app_env="test"),
        lambda: MockProvider("ok", app_env="test", raise_error=ProviderAuthError()),
    ],
    ids=["quota", "auth"],
)
@pytest.mark.asyncio
async def test_tc_150_tc_308_generation_failures_leave_the_earlier_plan_unchanged(
    api_app: FastAPI,
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    queue: Queue,
    provider: Any,
) -> None:
    use(api_app, MockProvider("ok", app_env="test"))
    trip_id = await create_trip(api_client, auth_user, destination)
    await generate(api_client, db_session, queue, auth_user, trip_id)
    before = await plan_state(db_session, trip_id)
    generation_id = await queued_on(db_session, auth_user, trip_id)

    await jobs.run(generation_id, provider(), job_sessions(db_session))

    row = await generation_repository.get_for_user(db_session, generation_id, auth_user.user_id)
    assert row.status == "failed"
    assert await plan_state(db_session, trip_id) == before


@pytest.mark.asyncio
async def test_tc_308_generation_failures_an_outage_keeps_the_trip_preferences_and_versions(
    api_app: FastAPI,
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    queue: Queue,
) -> None:
    use(api_app, MockProvider("ok", app_env="test"))
    trip_id = await create_trip(api_client, auth_user, destination)
    await generate(api_client, db_session, queue, auth_user, trip_id)
    earlier = list(
        await db_session.execute(
            select(ItineraryVersion.id, ItineraryVersion.snapshot).where(
                ItineraryVersion.trip_id == uuid.UUID(trip_id)
            )
        )
    )
    before = await plan_state(db_session, trip_id)
    generation_id = await queued_on(db_session, auth_user, trip_id)

    await jobs.run(generation_id, MockProvider("timeout", app_env="test"), job_sessions(db_session))

    after = await plan_state(db_session, trip_id)
    assert after["updated_prefs"] == before["updated_prefs"]
    assert after["plan_revision"] == before["plan_revision"] + 1  # the labelled fallback plan
    kept = list(
        await db_session.execute(
            select(ItineraryVersion.id, ItineraryVersion.snapshot).where(
                ItineraryVersion.id.in_([version_id for version_id, _ in earlier])
            )
        )
    )
    assert sorted(kept) == sorted(earlier)  # earlier versions unchanged


@pytest.mark.asyncio
async def test_generation_failures_a_failing_fallback_ends_failed_internal(
    api_app: FastAPI,
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    queue: Queue,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use(api_app, MockProvider("timeout", app_env="test"))
    trip_id = await create_trip(api_client, auth_user, destination)
    before = await plan_state(db_session, trip_id)

    def broken(*args: Any) -> Any:
        raise RuntimeError("planner bug")

    monkeypatch.setattr(fallback_planner, "plan_rule_based", broken)

    body = await generate(api_client, db_session, queue, auth_user, trip_id)

    assert (body["status"], body["failure_reason"]) == ("failed", "internal")
    assert await plan_state(db_session, trip_id) == before


# NFR-024: no vendor text in API-23 or the logs


@pytest.mark.parametrize(
    "error",
    [ProviderUnavailable(VENDOR_TEXT), ProviderQuotaExhausted(VENDOR_TEXT)],
    ids=["fallback", "failed"],
)
@pytest.mark.asyncio
async def test_nfr_024_generation_failures_show_and_log_no_vendor_text(
    api_app: FastAPI,
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    queue: Queue,
    caplog: pytest.LogCaptureFixture,
    error: ProviderError,
) -> None:
    use(api_app, MockProvider("ok", app_env="test", raise_error=error))
    trip_id = await create_trip(api_client, auth_user, destination)

    with caplog.at_level(logging.DEBUG):
        body = await generate(api_client, db_session, queue, auth_user, trip_id)

    assert body["status"] in {"completed", "failed"}
    assert VENDOR_TEXT not in str(body)
    assert VENDOR_TEXT not in caplog.text
