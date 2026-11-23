"""Injection pass of the security test pass (IMP-702 step 3; TC-349, TC-357, ACC-15; NFR-014,
NFR-016, NFR-024).

TC-349: SQL attack strings from fixtures/injection_corpus.json go into a trip title, the trip notes
and the place search; each is stored and read back byte for byte, or searched as plain text, and
every table it names still holds its rows. TC-357: a prompt-injection note runs through the whole
generation pipeline with the MOCK provider. The shortlist the provider receives, the saved places
and the computed costs equal those of the same trip with a harmless note, and neither the note,
the user's e-mail nor the provider request body reaches the log (TC-358, TC-025). The model-side
cases (an answer that obeys a note) are tests/unit/validation/test_injection_cases.py (TC-028).
"""

import dataclasses
import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from fixtures.auth import AuthUser, auth_test_settings, client_for
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.errors import ProviderUnavailable
from app.ai.factory import get_model_provider
from app.ai.providers.mock import MockProvider
from app.auth import deps
from app.core.config import Settings
from app.db.models import Destination, Place
from app.generation import jobs
from app.livedata.factory import LiveProviders
from app.livedata.providers.base import BBox, OsmElement, WikiSection
from app.livedata.providers.fake import LIVETON, FakeGeocoder, liveton_elements
from app.main import create_app
from app.places import live_import, live_jobs, seed
from app.places import repository as places_repository
from app.schemas.ai import GenerationRequest

REPO_ROOT = Path(__file__).resolve().parents[4]
SAMPLETON = REPO_ROOT / "data" / "fixtures" / "sampleton"
CORPUS = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures" / "injection_corpus.json").read_text("utf-8")
)
SQL: list[str] = CORPUS["sql"]
PROMPT: list[str] = CORPUS["prompt"]
HARMLESS_NOTE = "We like quiet mornings near the river."
# Tables the SQL strings name; their row counts must not move.
NAMED_TABLES = ("trips", "itinerary_items", "profiles", "places", "destinations")


@pytest_asyncio.fixture
async def sampleton(db_session: AsyncSession) -> Destination:
    await seed.load_fixture(db_session, seed.read_fixture(SAMPLETON))
    destination = await db_session.scalar(
        select(Destination).where(Destination.slug == "sampleton")
    )
    assert destination is not None
    return destination


async def row_counts(session: AsyncSession) -> dict[str, int]:
    counts = {}
    for table in NAMED_TABLES:
        query = f"select count(*) from public.{table}"  # noqa: S608  # fixed table names
        counts[table] = int(await session.scalar(text(query)) or 0)
    return counts


async def new_trip(
    client: httpx.AsyncClient, user: AuthUser, destination: Destination, title: str
) -> str:
    response = await client.post(
        "/api/v1/trips",
        json={
            "title": title,
            "destination_id": str(destination.id),
            "start_date": "2026-12-04",
            "end_date": "2026-12-06",
            "adults": 2,
        },
        headers=user.headers,
    )
    assert response.status_code == 201, response.text
    trip_id: str = response.json()["id"]
    return trip_id


async def save_notes(client: httpx.AsyncClient, user: AuthUser, trip_id: str, notes: str) -> None:
    response = await client.put(
        f"/api/v1/trips/{trip_id}/preferences",
        json={"interests": ["museum", "food"], "notes": notes, "must_visit_place_ids": []},
        headers=user.headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["notes"] == notes


# TC-349


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", SQL)
async def test_tc_349_sql_in_title_and_notes_is_stored_as_text(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sampleton: Destination,
    payload: str,
) -> None:
    trip_id = await new_trip(api_client, auth_user, sampleton, "seed trip")
    before = await row_counts(db_session)

    created = await new_trip(api_client, auth_user, sampleton, payload)
    await save_notes(api_client, auth_user, created, payload)
    renamed = await api_client.patch(
        f"/api/v1/trips/{trip_id}", json={"title": payload}, headers=auth_user.headers
    )
    assert renamed.status_code == 200, renamed.text

    for read in (created, trip_id):
        trip = await api_client.get(f"/api/v1/trips/{read}", headers=auth_user.headers)
        assert trip.json()["title"] == payload.strip()
    preferences = await api_client.get(
        f"/api/v1/trips/{created}/preferences", headers=auth_user.headers
    )
    assert preferences.json()["notes"] == payload
    listed = await api_client.get("/api/v1/trips", headers=auth_user.headers)
    assert sorted(t["title"] for t in listed.json()["items"]) == sorted([payload.strip()] * 2)
    # Only the one new trip was added; nothing the payload names was dropped or emptied.
    assert await row_counts(db_session) == {**before, "trips": before["trips"] + 1}


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", SQL)
async def test_tc_349_sql_in_place_search_is_searched_as_text(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sampleton: Destination,
    payload: str,
) -> None:
    await api_client.get("/api/v1/me", headers=auth_user.headers)  # creates the profile row first
    before = await row_counts(db_session)
    response = await api_client.get(
        "/api/v1/places",
        params={"destination_id": str(sampleton.id), "q": payload},
        headers=auth_user.headers,
    )
    assert response.status_code == 200, response.text
    # No SAMPLE place name or tag contains these strings, so a text search finds nothing; an
    # injected OR '1'='1' or a LIKE wildcard would return every place.
    assert response.json()["total"] == 0
    assert await row_counts(db_session) == before


# TC-357, TC-358, TC-025


class Recorded(MockProvider):
    """The MOCK provider with a log of the requests it received."""

    def __init__(self) -> None:
        super().__init__("ok", app_env="test")
        self.requests: list[GenerationRequest] = []

    async def generate_itinerary(self, request: GenerationRequest) -> Any:
        self.requests.append(request)
        return await super().generate_itinerary(request)


async def generate(
    app: FastAPI,
    client: httpx.AsyncClient,
    session: AsyncSession,
    user: AuthUser,
    destination: Destination,
    note: str,
) -> tuple[GenerationRequest, list[list[str]], dict[str, Any]]:
    """The request the provider got, the saved place IDs per day and API-33's costs."""
    provider = Recorded()
    queue: list[Any] = []
    app.dependency_overrides[get_model_provider] = lambda: provider
    app.dependency_overrides[jobs.get_submit] = lambda: lambda g, p: queue.append((g, p))

    @asynccontextmanager
    async def job_transaction() -> AsyncIterator[AsyncSession]:
        async with session.begin_nested():
            yield session

    trip_id = await new_trip(client, user, destination, "Weekend in Sampleton")
    await save_notes(client, user, trip_id, note)
    started = await client.post(
        f"/api/v1/trips/{trip_id}/generations", json={"mode": "ai"}, headers=user.headers
    )
    assert started.status_code == 202, started.text
    while queue:
        await jobs.run(*queue.pop(0), job_transaction)
    done = await client.get(f"/api/v1/generations/{started.json()['id']}", headers=user.headers)
    assert (done.json()["status"], done.json()["outcome"]) == ("completed", "model"), done.text

    plan = (await client.get(f"/api/v1/trips/{trip_id}/itinerary", headers=user.headers)).json()
    places = [
        [item["place"]["id"] for item in day["items"] if item["place"]] for day in plan["days"]
    ]
    costs = (await client.get(f"/api/v1/trips/{trip_id}/costs", headers=user.headers)).json()
    # Item IDs differ between the two trips; their number and the finding codes must not.
    costs["incomplete_items"] = len(costs["incomplete_items"])
    costs["alerts"] = sorted(alert["code"] for alert in costs["alerts"])
    assert len(provider.requests) == 1
    return provider.requests[0], places, costs


async def acknowledge(client: httpx.AsyncClient, user: AuthUser) -> None:
    response = await client.patch(
        "/api/v1/me", json={"ai_notice_acknowledged": True}, headers=user.headers
    )
    assert response.status_code == 200, response.text


@pytest.mark.asyncio
@pytest.mark.parametrize("note", PROMPT)
async def test_tc_357_injected_note_leaves_places_and_costs_unchanged(
    api_app: FastAPI,
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    sampleton: Destination,
    caplog: pytest.LogCaptureFixture,
    note: str,
) -> None:
    await acknowledge(api_client, auth_user)
    baseline, base_places, base_costs = await generate(
        api_app, api_client, db_session, auth_user, sampleton, HARMLESS_NOTE
    )
    with caplog.at_level(logging.DEBUG):
        hostile, places, costs = await generate(
            api_app, api_client, db_session, auth_user, sampleton, note
        )

    # The note reaches the provider only as quoted data, and the allowed place set is the same.
    assert hostile.preferences.notes_quoted is not None
    assert "00000000-0000-4000-8000-00000000bad0" not in {
        str(p.place_id) for p in hostile.shortlist
    }
    assert [p.place_id for p in hostile.shortlist] == [p.place_id for p in baseline.shortlist]
    active = set(
        map(
            str,
            await db_session.scalars(
                select(Place.id).where(Place.destination_id == sampleton.id, Place.is_active)
            ),
        )
    )
    saved = {place for day in places for place in day}
    assert saved
    assert saved <= active
    assert places == base_places
    assert costs == base_costs
    # TC-358, TC-025: no note, e-mail or provider request body in the log lines.
    assert note not in caplog.text
    assert auth_user.email not in caplog.text
    assert hostile.model_dump_json() not in caplog.text
    assert hostile.preferences.notes_quoted not in caplog.text


# ---------- IMP-731, TC-488 (Amendment A2 §11): hostile live data ----------
#
# One live destination (the SAMPLE Liveton fakes) is imported, planned, imported again with hostile
# text and planned again. The places keep their IDs across imports (upsert by OSM reference), so
# the saved place IDs per day and API-33's costs must be equal. Hostile wiki paragraphs reach the
# provider only as quoted context passages. Hostile OSM names reach it only as shortlist names; that
# run has no embeddings on either import, because a changed name legitimately changes a place's
# vector similarity, so lexical ranking isolates "an instruction changes nothing".

OSM_NAMES: list[str] = CORPUS["osm_names"]
WIKI_PARAGRAPHS: list[str] = CORPUS["wiki_paragraphs"]
BAD_PLACE = "00000000-0000-4000-8000-00000000bad0"
FILLER = (
    "The old quarter of narrow lanes climbs from the river towards the hill fort, and its "
    "courtyard houses keep carved wooden balconies above the street. "
)


class _Guides:
    """A GuideSourceProvider with fixed sections."""

    def __init__(self, sections: list[WikiSection]) -> None:
        self.sections = sections

    async def fetch(self, name: str, lat: float, lon: float) -> list[WikiSection]:
        return self.sections


class _Places:
    """The SAMPLE Liveton elements, with some names replaced."""

    def __init__(self, names: dict[int, str]) -> None:
        self.names = names

    async def fetch(self, bbox: BBox) -> list[OsmElement]:
        return [
            dataclasses.replace(e, tags={**e.tags, "name": self.names[i]}) if i in self.names else e
            for i, e in enumerate(liveton_elements(bbox))
        ]

    async def largest_city_near(self, lat: float, lon: float, radius_km: float) -> str | None:
        return None


def _wiki(paragraphs: list[str]) -> list[WikiSection]:
    text = "\n\n".join([FILLER * 2, *paragraphs, FILLER * 2])
    return [
        WikiSection(
            source="wikivoyage",
            page_id=9_000_001,
            revision_id=90_000_010,
            page_title="Liveton (SAMPLE)",
            page_url="https://en.wikivoyage.org/wiki/Liveton_(SAMPLE)",
            index=1,
            heading="Understand",
            text=text,
        )
    ]


@pytest_asyncio.fixture
async def live_app(db_session: AsyncSession) -> FastAPI:
    app = create_app(
        auth_test_settings(features_disabled="!any_city_mode", live_data_provider="FAKE")
    )

    async def test_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[deps.db_session] = test_session
    return app


async def _import(
    session: AsyncSession,
    destination_id: Any,
    places: Any,
    guides: Any,
    embedder: MockProvider,
) -> None:
    @asynccontextmanager
    async def job_transaction() -> AsyncIterator[AsyncSession]:
        async with session.begin_nested():
            yield session

    outcome = await live_jobs.run_import(
        destination_id,
        providers=LiveProviders(
            geocoder=FakeGeocoder("ok", app_env="test"), places=places, guides=guides
        ),
        sessions=job_transaction,
        settings=Settings(_env_file=None, app_env="test", ai_provider="MOCK"),
        embedder=embedder,
    )
    assert outcome == "completed"


async def _live_plan(
    app: FastAPI, session: AsyncSession, user: AuthUser, destination: Destination
) -> tuple[GenerationRequest, list[list[str]], dict[str, Any]]:
    async with client_for(app) as client:
        await acknowledge(client, user)
        return await generate(app, client, session, user, destination, HARMLESS_NOTE)


async def _live_destination(session: AsyncSession) -> Destination:
    row = await places_repository.insert_live_destination(
        session, live_import.build_live_row(LIVETON, LIVETON.osm_ref)
    )
    return row


async def _requeue(session: AsyncSession, destination: Destination) -> None:
    await places_repository.requeue_live_import(session, destination.id)
    await session.flush()


def _assert_live_plan_safe(
    request: GenerationRequest, places: list[list[str]], active: set[str]
) -> None:
    saved = {place for day in places for place in day}
    assert saved
    assert saved <= active
    assert BAD_PLACE not in saved
    assert BAD_PLACE not in {str(p.place_id) for p in request.shortlist}


async def _active_places(session: AsyncSession, destination: Destination) -> set[str]:
    rows = await session.scalars(
        select(Place.id).where(Place.destination_id == destination.id, Place.is_active)
    )
    return set(map(str, rows))


@pytest.mark.asyncio
@pytest.mark.any_city
async def test_tc_488_injection_hostile_wiki_paragraphs_leave_places_and_costs_unchanged(
    live_app: FastAPI, db_session: AsyncSession, auth_user: AuthUser
) -> None:
    destination = await _live_destination(db_session)
    embedder = MockProvider("ok", app_env="test")
    await _import(db_session, destination.id, _Places({}), _Guides(_wiki([])), embedder)
    _, base_places, base_costs = await _live_plan(live_app, db_session, auth_user, destination)

    await _requeue(db_session, destination)
    await _import(
        db_session, destination.id, _Places({}), _Guides(_wiki(WIKI_PARAGRAPHS)), embedder
    )
    hostile, places, costs = await _live_plan(live_app, db_session, auth_user, destination)

    _assert_live_plan_safe(hostile, places, await _active_places(db_session, destination))
    assert places == base_places
    assert costs == base_costs
    # The paragraphs were stored (no price or hours pattern) and reach the provider only inside
    # quoted guide passages, never in the shortlist or the notes.
    passages = getattr(hostile, "context_passages", [])
    quoted = " ".join(p.text for p in passages if p.kind == "guide")
    assert any(paragraph in quoted for paragraph in WIKI_PARAGRAPHS)
    shortlist_text = " ".join(p.name for p in hostile.shortlist)
    assert not any(paragraph in shortlist_text for paragraph in WIKI_PARAGRAPHS)


@pytest.mark.asyncio
@pytest.mark.any_city
async def test_tc_488_injection_hostile_osm_names_leave_places_and_costs_unchanged(
    live_app: FastAPI, db_session: AsyncSession, auth_user: AuthUser
) -> None:
    destination = await _live_destination(db_session)
    no_vectors = MockProvider(
        "ok", app_env="test", embed_error=ProviderUnavailable("mock provider: embedding outage")
    )
    await _import(db_session, destination.id, _Places({}), _Guides([]), no_vectors)
    _, base_places, base_costs = await _live_plan(live_app, db_session, auth_user, destination)

    # Elements 0 to 3 have near-copies (dedupe merges same names), so unique places are renamed.
    renamed = dict(zip((10, 11, 12), OSM_NAMES, strict=True))
    await _requeue(db_session, destination)
    await _import(db_session, destination.id, _Places(renamed), _Guides([]), no_vectors)
    hostile, places, costs = await _live_plan(live_app, db_session, auth_user, destination)

    _assert_live_plan_safe(hostile, places, await _active_places(db_session, destination))
    assert places == base_places
    assert costs == base_costs
    stored = set(
        await db_session.scalars(select(Place.name).where(Place.destination_id == destination.id))
    )
    assert set(OSM_NAMES) <= stored  # stored as plain text
    names_sent = {p.name for p in hostile.shortlist}
    assert all(name in OSM_NAMES or "(SAMPLE)" in name for name in names_sent)
