"""RUN-105B D2: retries under the real per-request transaction context, with offline providers."""

import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import UTC, datetime, timedelta

import httpx
import pytest
import pytest_asyncio
from fixtures.auth import AuthUser, auth_test_settings, client_for
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.breaker import QUOTA_COOL_DOWN_S, CircuitBreaker
from app.ai.providers.mock import MockProvider
from app.auth import deps
from app.db.models import Destination, Place
from app.livedata import throttle
from app.livedata.factory import LiveProviders, get_geocoder
from app.livedata.providers.fake import FakeGeocoder, FakeGuides, FakePlaces, FakeScenario
from app.main import create_app
from app.places import live_jobs
from app.places.live_service import get_import_submitter

pytestmark = [pytest.mark.any_city, pytest.mark.asyncio]

RESOLVE = "/api/v1/destinations/resolve"
OSM_REF = "R9000001"
Sessions = Callable[[], AbstractAsyncContextManager[AsyncSession]]


@pytest_asyncio.fixture
async def transactions(db_session: AsyncSession, auth_user: AuthUser) -> AsyncIterator[Sessions]:
    # The shared fixture normally has no session.begin() around a request, so it missed D2.
    # Release its auth-user savepoint, then use the same context as db.session.transaction().
    await db_session.commit()

    @asynccontextmanager
    async def transaction() -> AsyncIterator[AsyncSession]:
        async with db_session.begin():
            yield db_session

    yield transaction


@asynccontextmanager
async def client(
    transactions: Sessions, submitted: list[uuid.UUID]
) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(
        auth_test_settings(
            features_disabled="!any_city_mode",
            live_daily_imports_per_user=1,
            live_daily_imports_global=1,
        )
    )

    async def request_session() -> AsyncIterator[AsyncSession]:
        async with transactions() as session:
            yield session

    app.dependency_overrides[deps.db_session] = request_session
    app.dependency_overrides[get_geocoder] = lambda: FakeGeocoder("ok", app_env="test")
    app.dependency_overrides[get_import_submitter] = lambda: submitted.append
    async with client_for(app) as value:
        yield value


async def run(
    destination_id: uuid.UUID,
    transactions: Sessions,
    scenario: FakeScenario,
    *,
    guarded: bool = False,
) -> str | None:
    places = FakePlaces(scenario, app_env="test")
    return await live_jobs.run_import(
        destination_id,
        sessions=transactions,
        providers=LiveProviders(
            geocoder=FakeGeocoder("ok", app_env="test"),
            places=throttle.guard_places(places) if guarded else places,
            guides=FakeGuides("ok", app_env="test"),
        ),
        settings=auth_test_settings(),
        embedder=MockProvider("ok", app_env="test"),
    )


async def test_failed_import_retry_completes_with_same_destination(
    transactions: Sessions, auth_user: AuthUser
) -> None:
    submitted: list[uuid.UUID] = []
    async with client(transactions, submitted) as api:
        first = await api.post(RESOLVE, json={"osm_ref": OSM_REF}, headers=auth_user.headers)
        assert first.status_code == 202
        destination_id = uuid.UUID(first.json()["destination_id"])
        assert await run(destination_id, transactions, "timeout") == "failed"

        retry = await api.post(RESOLVE, json={"osm_ref": OSM_REF}, headers=auth_user.headers)
        assert retry.status_code == 202
        assert retry.json()["destination_id"] == str(destination_id)
        assert retry.json()["import"]["status"] == "queued"
        assert retry.json()["import"]["failure_reason"] is None
        assert await run(destination_id, transactions, "ok") == "completed"
        ready = await api.get(
            f"/api/v1/destinations/{destination_id}/import", headers=auth_user.headers
        )
        assert ready.status_code == 200
        assert ready.json()["import"]["status"] == "completed"
    assert submitted == [destination_id, destination_id]


async def test_failed_retry_during_cooldown_is_429_then_succeeds(
    transactions: Sessions, auth_user: AuthUser, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = [1000.0]
    clock = lambda: now[0]  # noqa: E731  # same clock for the throttle and breaker
    spacing = throttle.Throttle(0, clock=clock)
    breaker = CircuitBreaker(clock=clock)
    monkeypatch.setattr(throttle, "overpass_throttle", lambda: spacing)
    monkeypatch.setattr(throttle, "overpass_breaker", lambda: breaker)
    submitted: list[uuid.UUID] = []
    async with client(transactions, submitted) as api:
        first = await api.post(RESOLVE, json={"osm_ref": OSM_REF}, headers=auth_user.headers)
        destination_id = uuid.UUID(first.json()["destination_id"])
        assert await run(destination_id, transactions, "rate_limited", guarded=True) == "failed"

        for elapsed, remaining in ((0, 900), (899.1, 1)):
            now[0] = 1000 + elapsed
            retry = await api.post(RESOLVE, json={"osm_ref": OSM_REF}, headers=auth_user.headers)
            assert retry.status_code == 429
            assert retry.json()["error"]["code"] == "RATE_LIMITED"
            assert retry.json()["error"]["retry_after_s"] == remaining
            assert retry.headers["Retry-After"] == str(remaining)
            assert submitted == [destination_id]
        now[0] = 1000 + QUOTA_COOL_DOWN_S
        retry = await api.post(RESOLVE, json={"osm_ref": OSM_REF}, headers=auth_user.headers)
        assert retry.status_code == 202
        assert await run(destination_id, transactions, "ok", guarded=True) == "completed"
    assert submitted == [destination_id, destination_id]


async def test_failed_refresh_retry_preserves_active_destination_and_places(
    transactions: Sessions, auth_user: AuthUser
) -> None:
    submitted: list[uuid.UUID] = []
    async with client(transactions, submitted) as api:
        first = await api.post(RESOLVE, json={"osm_ref": OSM_REF}, headers=auth_user.headers)
        destination_id = uuid.UUID(first.json()["destination_id"])
        assert await run(destination_id, transactions, "ok") == "completed"
        async with transactions() as session:
            count = await session.scalar(
                select(func.count())
                .select_from(Place)
                .where(Place.destination_id == destination_id)
            )
            await session.execute(
                update(Destination)
                .where(Destination.id == destination_id)
                .values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
            )
        refresh = await api.post(RESOLVE, json={"osm_ref": OSM_REF}, headers=auth_user.headers)
        assert refresh.status_code == 202
        assert await run(destination_id, transactions, "timeout") == "failed"
        retry = await api.post(RESOLVE, json={"osm_ref": OSM_REF}, headers=auth_user.headers)
        assert retry.status_code == 202
        async with transactions() as session:
            row = await session.get(Destination, destination_id, populate_existing=True)
            assert row is not None
            assert row.is_active
            assert row.imported_at is not None
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(Place)
                    .where(Place.destination_id == destination_id)
                )
                == count
            )
