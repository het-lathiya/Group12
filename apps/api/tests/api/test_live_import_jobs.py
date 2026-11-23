"""The live import job, claim, reaper and repository writes (Amendment A2 §6.2 to §6.5; IMP-725).

TC-474 (the job goes queued → running → completed, stores labelled places and activates the
destination; a repeat import deactivates missing places without deleting them), TC-475 (provider
timeout and rate limit give ``failed`` with the reason; the reaper fails stale imports; the claim
lets only one job run) and the IMP-725 share of TC-479 (a MOCK plan for a live city uses stored
place IDs only).

Offline only: the live-data providers are the SAMPLE fakes ("Liveton (SAMPLE)" R9000001, "Tinyham
(SAMPLE)" R9000002, nearby "Bigtown (SAMPLE)") or small stubs, and embeddings come from the MOCK
provider. The job's transactions are savepoints of the test's rolled-back session, as in
``test_generations.py``; the app is built with ``any_city_mode`` ON through a settings override.
"""

import asyncio
import dataclasses
import logging
import uuid
from collections import Counter
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fixtures.auth import AuthUser, auth_test_settings, client_for
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.errors import ProviderUnavailable
from app.ai.factory import get_model_provider
from app.ai.providers.base import ModelProvider
from app.ai.providers.mock import EMBED_MODEL_ID, MockProvider
from app.auth import deps
from app.core.config import Settings
from app.db.models import (
    DataSource,
    Destination,
    Place,
    PlaceOpeningHours,
    RagChunk,
    RagDocument,
)
from app.generation import jobs
from app.livedata.countries import capital
from app.livedata.factory import LiveProviders, get_geocoder
from app.livedata.providers.base import BBox, LiveDataUnavailable, OsmElement, PlacesProvider
from app.livedata.providers.fake import (
    BIGTOWN_NAME,
    LIVETON,
    LIVETON_REF,
    TINYHAM,
    FakeGeocoder,
    FakeGuides,
    FakePlaces,
    FakeScenario,
    liveton_elements,
    tinyham_elements,
)
from app.main import create_app
from app.places import live_import, live_jobs, repository
from app.places import service as places_service
from app.places.live_service import get_import_submitter

pytestmark = [pytest.mark.any_city, pytest.mark.asyncio]

Sessions = Callable[[], AbstractAsyncContextManager[AsyncSession]]
Job = tuple[uuid.UUID, ModelProvider]

V1 = "/api/v1"
LIVETON_USABLE = 44  # 32 non-food and 12 food places; 4 near-copies are merged
LIVETON_FOUND = 48
TINYHAM_FOUND = 8


def job_settings(**overrides: Any) -> Settings:
    return Settings(_env_file=None, app_env="test", ai_provider="MOCK", **overrides)


def fakes(scenario: FakeScenario = "ok") -> LiveProviders:
    return LiveProviders(
        geocoder=FakeGeocoder(scenario, app_env="test"),
        places=FakePlaces(scenario, app_env="test"),
        guides=FakeGuides(scenario, app_env="test"),
    )


def with_places(places: PlacesProvider) -> LiveProviders:
    base = fakes()
    return LiveProviders(geocoder=base.geocoder, places=places, guides=base.guides)


def embedder(**kwargs: Any) -> MockProvider:
    return MockProvider("ok", app_env="test", **kwargs)


class StubPlaces:
    """A PlacesProvider with fixed elements and a nearby-city answer or error."""

    def __init__(
        self,
        elements: Callable[[BBox], list[OsmElement]],
        *,
        nearby: str | None = None,
        nearby_error: Exception | None = None,
        fetch_error: Exception | None = None,
        delay_s: float = 0.0,
    ) -> None:
        self.elements = elements
        self.nearby = nearby
        self.nearby_error = nearby_error
        self.fetch_error = fetch_error
        self.delay_s = delay_s

    async def fetch(self, bbox: BBox) -> list[OsmElement]:
        if self.delay_s:
            await asyncio.sleep(self.delay_s)
        if self.fetch_error is not None:
            raise self.fetch_error
        return self.elements(bbox)

    async def largest_city_near(self, lat: float, lon: float, radius_km: float) -> str | None:
        if self.nearby_error is not None:
            raise self.nearby_error
        return self.nearby


@pytest.fixture
def sessions(db_session: AsyncSession) -> Sessions:
    """The job's transactions, as savepoints of the test's rolled-back session."""

    @asynccontextmanager
    async def job_transaction() -> AsyncIterator[AsyncSession]:
        async with db_session.begin_nested():
            yield db_session

    return job_transaction


async def queued(db_session: AsyncSession, place: Any = LIVETON) -> uuid.UUID:
    row = live_import.build_live_row(place, place.osm_ref)
    row = await repository.insert_live_destination(db_session, row)
    return row.id


async def run(
    destination_id: uuid.UUID,
    sessions: Sessions,
    providers: LiveProviders | None = None,
    **kwargs: Any,
) -> str | None:
    return await live_jobs.run_import(
        destination_id,
        providers=providers or fakes(),
        sessions=sessions,
        settings=kwargs.pop("settings", job_settings()),
        embedder=kwargs.pop("embedder", embedder()),
    )


async def row_of(db_session: AsyncSession, destination_id: uuid.UUID) -> Destination:
    row = await db_session.get(Destination, destination_id, populate_existing=True)
    assert row is not None
    return row


async def places_of(db_session: AsyncSession, destination_id: uuid.UUID) -> list[Place]:
    query = (
        select(Place)
        .where(Place.destination_id == destination_id)
        .execution_options(populate_existing=True)
    )
    return list((await db_session.scalars(query)).all())


async def requeue(db_session: AsyncSession, destination_id: uuid.UUID) -> None:
    await repository.requeue_live_import(db_session, destination_id)
    await db_session.flush()


# TC-474


async def test_tc_474_ok_import_completes_with_labelled_places(
    db_session: AsyncSession, sessions: Sessions
) -> None:
    destination_id = await queued(db_session)
    before = datetime.now(UTC)

    assert await run(destination_id, sessions) == "completed"

    row = await row_of(db_session, destination_id)
    assert (row.import_status, row.import_failure_reason, row.is_active) == (
        "completed",
        None,
        True,
    )
    assert (row.places_found, row.places_usable, row.nearby_city) == (
        LIVETON_FOUND,
        LIVETON_USABLE,
        None,
    )
    assert row.import_started_at is not None
    assert row.import_started_at >= before
    assert row.imported_at is not None
    assert row.expires_at is not None
    assert row.expires_at - row.imported_at == timedelta(days=30)

    places = await places_of(db_session, destination_id)
    assert len(places) == LIVETON_USABLE
    assert all(p.is_active for p in places)
    assert all(
        p.price_min is None
        and p.price_max is None
        and p.price_currency is None
        and p.price_label == "unavailable"
        and p.hours_label == "unavailable"
        and p.hours_checked_on is None
        and p.verification_status == "imported_osm"
        and p.description is None
        and p.booking_url is None
        and p.external_ref is not None
        and p.external_ref.startswith(f"{LIVETON_REF}:")
        for p in places
    )
    assert Counter(p.category for p in places)["food"] == 12
    hours = await db_session.scalar(
        select(func.count())
        .select_from(PlaceOpeningHours)
        .where(PlaceOpeningHours.place_id.in_([p.id for p in places]))
    )
    assert hours == 0

    source = await db_session.scalar(select(DataSource).where(DataSource.name == "OpenStreetMap"))
    assert source is not None
    assert (source.source_type, source.licence, source.url) == (
        "osm_import",
        "ODbL 1.0",
        "https://www.openstreetmap.org/copyright",
    )
    assert source.attribution_text == (
        "Place data © OpenStreetMap contributors, available under the Open Database Licence (ODbL)"
    )
    assert {p.source_id for p in places} == {source.id}

    documents = list(
        await db_session.scalars(
            select(RagDocument).where(
                RagDocument.destination_id == destination_id, RagDocument.kind == "place"
            )
        )
    )
    assert len(documents) == LIVETON_USABLE
    assert all(d.is_active for d in documents)
    chunks = list(
        await db_session.scalars(
            select(RagChunk).where(RagChunk.document_id.in_([d.id for d in documents]))
        )
    )
    assert chunks
    assert all(c.embedding_model_id == EMBED_MODEL_ID for c in chunks)


async def test_tc_474_repeat_import_updates_in_place_and_deactivates_missing(
    db_session: AsyncSession, sessions: Sessions
) -> None:
    destination_id = await queued(db_session)
    assert await run(destination_id, sessions) == "completed"
    first = {p.external_ref: p.id for p in await places_of(db_session, destination_id)}
    full = liveton_elements

    def fewer(bbox: BBox) -> list[OsmElement]:
        return [e for i, e in enumerate(full(bbox)) if i not in (10, 11)]

    dropped = {f"{LIVETON_REF}:{e.osm_type}{e.osm_id}" for e in full(LIVETON.bbox)[10:12]}

    await requeue(db_session, destination_id)
    assert await run(destination_id, sessions, with_places(StubPlaces(fewer))) == "completed"

    places = await places_of(db_session, destination_id)
    assert {p.external_ref: p.id for p in places} == first  # same rows, none deleted
    inactive = {p.external_ref for p in places if not p.is_active}
    assert inactive == dropped
    row = await row_of(db_session, destination_id)
    assert (row.import_status, row.places_usable) == ("completed", LIVETON_USABLE - 2)
    gone = await db_session.scalars(
        select(RagDocument.is_active).where(
            RagDocument.place_id.in_([first[ref] for ref in dropped])
        )
    )
    assert list(gone) == [False, False]

    # A third run with every place again brings the two back, still the same rows.
    await requeue(db_session, destination_id)
    assert await run(destination_id, sessions) == "completed"
    again = await places_of(db_session, destination_id)
    assert {p.external_ref: p.id for p in again} == first
    assert all(p.is_active for p in again)


async def test_tc_474_embedding_failure_leaves_the_import_completed(
    db_session: AsyncSession, sessions: Sessions
) -> None:
    destination_id = await queued(db_session)
    broken = embedder(embed_error=ProviderUnavailable("mock provider: embedding outage"))

    assert await run(destination_id, sessions, embedder=broken) == "completed"

    row = await row_of(db_session, destination_id)
    assert (row.import_status, row.is_active) == ("completed", True)
    unembedded = await db_session.scalar(
        select(func.count())
        .select_from(RagChunk)
        .join(RagDocument, RagDocument.id == RagChunk.document_id)
        .where(
            RagDocument.destination_id == destination_id,
            RagDocument.kind == "place",
            RagChunk.embedding.is_(None),
        )
    )
    assert unembedded == LIVETON_USABLE


# A2 §6.4: not enough data


async def test_small_gives_insufficient_data_with_the_nearby_city(
    db_session: AsyncSession, sessions: Sessions
) -> None:
    destination_id = await queued(db_session, TINYHAM)

    assert await run(destination_id, sessions, fakes("small")) == "insufficient_data"

    row = await row_of(db_session, destination_id)
    assert (row.import_status, row.import_failure_reason, row.is_active) == (
        "insufficient_data",
        None,
        False,
    )
    assert (row.places_found, row.places_usable, row.nearby_city) == (
        TINYHAM_FOUND,
        TINYHAM_FOUND,
        BIGTOWN_NAME,
    )
    assert row.expires_at is not None
    assert row.expires_at > datetime.now(UTC) + timedelta(days=29)
    assert row.imported_at is None
    assert await places_of(db_session, destination_id) == []
    documents = await db_session.scalar(
        select(func.count())
        .select_from(RagDocument)
        .where(RagDocument.destination_id == destination_id)
    )
    assert documents == 0


@pytest.mark.parametrize(
    "stub",
    [
        StubPlaces(tinyham_elements, nearby=None),
        StubPlaces(tinyham_elements, nearby_error=LiveDataUnavailable("http 504")),
        StubPlaces(tinyham_elements, nearby="Tinyham (SAMPLE)"),  # never the settlement itself
    ],
    ids=["none-found", "lookup-failed", "same-settlement"],
)
async def test_nearby_city_falls_back_to_the_capital(
    db_session: AsyncSession, sessions: Sessions, stub: StubPlaces
) -> None:
    destination_id = await queued(db_session, TINYHAM)

    assert await run(destination_id, sessions, with_places(stub)) == "insufficient_data"

    row = await row_of(db_session, destination_id)
    assert row.nearby_city == capital("IN")
    assert row.nearby_city


# TC-475


@pytest.mark.parametrize(
    ("scenario", "reason"),
    [
        ("timeout", "timeout"),
        ("rate_limited", "rate_limited"),
        ("malformed", "provider_unavailable"),
    ],
)
async def test_tc_475_provider_errors_fail_with_the_reason(
    db_session: AsyncSession, sessions: Sessions, scenario: FakeScenario, reason: str
) -> None:
    destination_id = await queued(db_session)

    assert await run(destination_id, sessions, fakes(scenario)) == "failed"

    row = await row_of(db_session, destination_id)
    assert (row.import_status, row.import_failure_reason, row.is_active) == (
        "failed",
        reason,
        False,
    )
    assert row.imported_at is None
    assert await places_of(db_session, destination_id) == []


async def test_tc_475_failed_refresh_keeps_earlier_places(
    db_session: AsyncSession, sessions: Sessions
) -> None:
    destination_id = await queued(db_session)
    assert await run(destination_id, sessions) == "completed"
    imported_at = (await row_of(db_session, destination_id)).imported_at

    await requeue(db_session, destination_id)
    assert await run(destination_id, sessions, fakes("timeout")) == "failed"

    row = await row_of(db_session, destination_id)
    assert (row.import_status, row.import_failure_reason) == ("failed", "timeout")
    assert (row.is_active, row.imported_at, row.places_usable) == (
        True,
        imported_at,
        LIVETON_USABLE,
    )
    places = await places_of(db_session, destination_id)
    assert len(places) == LIVETON_USABLE
    assert all(p.is_active for p in places)


async def test_tc_475_overall_timeout_fails_with_timeout(
    db_session: AsyncSession, sessions: Sessions, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(live_jobs, "IMPORT_TIMEOUT_S", 0.05)
    destination_id = await queued(db_session)
    slow = StubPlaces(liveton_elements, delay_s=1.0)

    assert await run(destination_id, sessions, with_places(slow)) == "failed"

    row = await row_of(db_session, destination_id)
    assert (row.import_status, row.import_failure_reason) == ("failed", "timeout")


async def test_unexpected_error_fails_internal_and_logs_only_the_id(
    db_session: AsyncSession, sessions: Sessions, caplog: pytest.LogCaptureFixture
) -> None:
    destination_id = await queued(db_session)
    broken = StubPlaces(liveton_elements, fetch_error=RuntimeError("boom"))

    with caplog.at_level(logging.INFO, logger="app.places.live_jobs"):
        assert await run(destination_id, sessions, with_places(broken)) == "failed"

    row = await row_of(db_session, destination_id)
    assert (row.import_status, row.import_failure_reason) == ("failed", "internal")
    messages = [r.getMessage() for r in caplog.records if r.name == "app.places.live_jobs"]
    assert any(str(destination_id) in m for m in messages)
    assert not any("Liveton" in m for m in messages)


async def test_tc_475_claim_is_exclusive(db_session: AsyncSession, sessions: Sessions) -> None:
    destination_id = await queued(db_session)
    started = datetime.now(UTC) - timedelta(seconds=5)
    await db_session.execute(
        update(Destination)
        .where(Destination.id == destination_id)
        .values(import_status="running", import_started_at=started)
    )

    assert await run(destination_id, sessions) is None  # another job holds it

    row = await row_of(db_session, destination_id)
    assert (row.import_status, row.import_started_at) == ("running", started)
    assert await places_of(db_session, destination_id) == []

    async with sessions() as session:
        assert await places_service.claim_live_import(session, destination_id, started) is None


async def test_a_completed_import_is_not_claimed_again(
    db_session: AsyncSession, sessions: Sessions
) -> None:
    destination_id = await queued(db_session)
    assert await run(destination_id, sessions) == "completed"
    assert await run(destination_id, sessions, fakes("timeout")) is None
    assert (await row_of(db_session, destination_id)).import_status == "completed"


async def test_tc_475_reaper_fails_stale_running_and_queued_imports(
    db_session: AsyncSession,
) -> None:
    # The updated_at trigger stamps every update with the transaction time, so a queued row's age
    # is shown by reaping at a later "now" rather than by back-dating the row.
    now = datetime.now(UTC)
    rows = {}
    for name, ref, status, started in (
        ("running-361s", "R9000101", "running", now - timedelta(seconds=361)),
        ("running-100s", "R9000102", "running", now - timedelta(seconds=100)),
        ("queued", "R9000103", "queued", None),
    ):
        place = dataclasses.replace(LIVETON, osm_ref=ref, name=f"{name} (SAMPLE)", name_en=None)
        destination_id = await queued(db_session, place)
        await db_session.execute(
            update(Destination)
            .where(Destination.id == destination_id)
            .values(import_status=status, import_started_at=started)
        )
        rows[name] = destination_id

    async def states() -> dict[str, tuple[str | None, str | None]]:
        result = {}
        for name, destination_id in rows.items():
            row = await row_of(db_session, destination_id)
            result[name] = (row.import_status, row.import_failure_reason)
        return result

    assert await live_jobs.reap_stale_imports(db_session, now) == 1
    assert await states() == {
        "running-361s": ("failed", "timeout"),
        "running-100s": ("running", None),
        "queued": ("queued", None),
    }

    # Eleven minutes later the other running row is past 360 s and the queued one past 10 min.
    assert await live_jobs.reap_stale_imports(db_session, now + timedelta(minutes=11)) == 2
    assert await states() == {
        "running-361s": ("failed", "timeout"),
        "running-100s": ("failed", "timeout"),
        "queued": ("failed", "timeout"),
    }


async def test_a_reaped_import_does_not_complete(
    db_session: AsyncSession, sessions: Sessions
) -> None:
    destination_id = await queued(db_session)

    class ReapedWhileFetching(StubPlaces):
        async def fetch(self, bbox: BBox) -> list[OsmElement]:
            await db_session.execute(
                update(Destination)
                .where(Destination.id == destination_id)
                .values(import_status="failed", import_failure_reason="timeout")
            )
            return liveton_elements(bbox)

    reaped = ReapedWhileFetching(liveton_elements)
    assert await run(destination_id, sessions, with_places(reaped)) == "failed"

    row = await row_of(db_session, destination_id)
    assert (row.import_status, row.import_failure_reason, row.is_active) == (
        "failed",
        "timeout",
        False,
    )
    assert await places_of(db_session, destination_id) == []  # the store was rolled back


# The import CLI (A2 §6.2), on the same path


async def test_cli_path_imports_once_per_reference(
    db_session: AsyncSession, sessions: Sessions
) -> None:
    providers = fakes()
    first = await live_import.import_destination(
        osm_ref=LIVETON_REF, providers=providers, sessions=sessions
    )
    assert first.ran
    assert first.row.import_status == "completed"
    assert first.row.import_requested_by is None
    assert live_import.exit_code(first) == live_import.EXIT_OK

    again = await live_import.import_destination(
        query="liveton", providers=providers, sessions=sessions
    )
    assert (again.destination_id, again.ran) == (first.destination_id, False)

    small = await live_import.import_destination(
        osm_ref=TINYHAM.osm_ref, providers=providers, sessions=sessions
    )
    assert small.row.import_status == "insufficient_data"
    assert live_import.exit_code(small) == live_import.EXIT_OK

    printed = await live_import.import_destination(
        osm_ref=LIVETON_REF, providers=fakes("timeout"), sessions=sessions
    )
    assert not printed.ran  # completed and not expired: only printed, no provider call
    assert printed.row.import_status == "completed"


async def test_cli_requeues_a_failed_import_and_reports_failure(
    db_session: AsyncSession, sessions: Sessions
) -> None:
    failed = await live_import.import_destination(
        osm_ref=LIVETON_REF,
        providers=with_places(FakePlaces("rate_limited", app_env="test")),
        sessions=sessions,
    )
    assert failed.row.import_status == "failed"
    assert live_import.exit_code(failed) == live_import.EXIT_FAILED

    retried = await live_import.import_destination(
        osm_ref=LIVETON_REF, providers=fakes(), sessions=sessions
    )
    assert retried.destination_id == failed.destination_id
    assert retried.row.import_status == "completed"


async def test_cli_refuses_a_bad_reference() -> None:
    with pytest.raises(SystemExit) as raised:
        live_import.parse_args(["--osm-ref", "1234; drop"])
    assert raised.value.code == live_import.EXIT_USAGE


# API-77 resolve, then the job, a trip (API-07) and a MOCK generation (API-22): TC-479 share


@pytest_asyncio.fixture
async def live_app(db_session: AsyncSession) -> FastAPI:
    app = create_app(
        auth_test_settings(features_disabled="!any_city_mode", live_data_provider="FAKE")
    )

    async def test_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[deps.db_session] = test_session
    app.dependency_overrides[get_geocoder] = lambda: FakeGeocoder("ok", app_env="test")
    return app


async def test_tc_479_resolve_import_trip_and_mock_generation(
    live_app: FastAPI, db_session: AsyncSession, auth_user: AuthUser, sessions: Sessions
) -> None:
    submitted_imports: list[uuid.UUID] = []
    live_app.dependency_overrides[get_import_submitter] = lambda: submitted_imports.append
    generation_jobs: list[Job] = []
    live_app.dependency_overrides[jobs.get_submit] = lambda: (
        lambda gid, p: generation_jobs.append((gid, p))
    )
    provider = MockProvider("ok", app_env="test")
    live_app.dependency_overrides[get_model_provider] = lambda: provider
    headers = auth_user.headers

    async with client_for(live_app) as client:
        first = await client.post(
            f"{V1}/destinations/resolve", json={"osm_ref": LIVETON_REF}, headers=headers
        )
        assert first.status_code == 202, first.text
        destination_id = uuid.UUID(first.json()["destination_id"])
        assert submitted_imports == [destination_id]
        second = await client.post(
            f"{V1}/destinations/resolve", json={"osm_ref": LIVETON_REF}, headers=headers
        )
        assert second.status_code == 200, second.text
        assert second.json()["destination_id"] == str(destination_id)
        assert submitted_imports == [destination_id]  # not queued again

        assert await run(destination_id, sessions) == "completed"
        state = await client.get(f"{V1}/destinations/{destination_id}/import", headers=headers)
        assert state.status_code == 200, state.text
        assert state.json()["import"]["status"] == "completed"
        assert state.json()["import"]["places_usable"] == LIVETON_USABLE

        notice = await client.patch(
            f"{V1}/me", json={"ai_notice_acknowledged": True}, headers=headers
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
            headers=headers,
        )
        assert trip.status_code == 201, trip.text
        assert trip.json()["destination"]["currency"] == "INR"
        trip_id = trip.json()["id"]
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
            headers=headers,
        )
        assert prefs.status_code == 200, prefs.text

        started = await client.post(
            f"{V1}/trips/{trip_id}/generations", json={"mode": "ai"}, headers=headers
        )
        assert started.status_code == 202, started.text
        generation_id = started.json()["id"]
        while generation_jobs:
            await jobs.run(*generation_jobs.pop(0), sessions)
        done = await client.get(f"{V1}/generations/{generation_id}", headers=headers)
        assert done.status_code == 200, done.text
        assert done.json()["status"] == "completed", done.json()

        plan = await client.get(f"{V1}/trips/{trip_id}/itinerary", headers=headers)
        assert plan.status_code == 200, plan.text
        body = plan.json()

    planned = {item["place"]["id"] for day in body["days"] for item in day["items"]}
    stored = {str(p.id) for p in await places_of(db_session, destination_id) if p.is_active}
    assert planned
    assert planned <= stored
    codes = {finding["code"] for finding in body["findings"]}
    assert {"COST_INCOMPLETE", "HOURS_UNVERIFIED"} <= codes
