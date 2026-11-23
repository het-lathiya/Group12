"""TC-487: authorization of the any-city routes API-76 to API-79 (Amendment A2 §11, §3.4; IMP-731).

With the switch ON (a settings override) every any-city route needs a bearer token (401 without
one); destinations are reference data, so any signed-in user reads a destination another user
resolved; no response carries ``import_requested_by``; the daily cap of new cities is counted per
user (one user's cap does not stop another). ``route_matrix.py`` is unchanged: it pins the OFF
route set, and this file is the ON counterpart of its walk (§3.4).

Offline only: the SAMPLE fake geocoder; the import runner is replaced by a recorder.
"""

import uuid
from collections.abc import AsyncIterator, Iterator
from typing import Any

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.routing import iter_route_contexts
from fixtures.auth import AuthUser, auth_test_settings, client_for
from fixtures.db import insert_auth_user
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import deps
from app.livedata.factory import get_geocoder
from app.livedata.providers.fake import LIVETON_REF, TINYHAM_REF, FakeGeocoder
from app.main import create_app
from app.places import live_service
from app.places.live_service import get_import_submitter

pytestmark = [pytest.mark.any_city, pytest.mark.asyncio]

V1 = "/api/v1"
ANY_CITY_ROUTES = {
    ("GET", "/api/v1/destinations/search"),
    ("POST", "/api/v1/destinations/resolve"),
    ("GET", "/api/v1/destinations/{destination_id}/import"),
    ("GET", "/api/v1/destinations/{destination_id}"),
}


@pytest.fixture(autouse=True)
def fresh_search_cache() -> Iterator[None]:
    live_service.search_cache.clear()
    yield
    live_service.search_cache.clear()


def build(db_session: AsyncSession, **settings: Any) -> FastAPI:
    app = create_app(auth_test_settings(features_disabled="!any_city_mode", **settings))

    async def test_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[deps.db_session] = test_session
    app.dependency_overrides[get_geocoder] = lambda: FakeGeocoder("ok", app_env="test")
    app.dependency_overrides[get_import_submitter] = lambda: lambda destination_id: None
    return app


@pytest_asyncio.fixture
async def live(db_session: AsyncSession) -> AsyncIterator[httpx.AsyncClient]:
    async with client_for(build(db_session)) as client:
        yield client


async def make_user(session: AsyncSession, name: str) -> AuthUser:
    user_id = uuid.uuid4()
    email = f"{name}-{user_id}@example.test"
    await insert_auth_user(session, user_id, email)
    return AuthUser(user_id=user_id, email=email)


def requests_for(destination_id: str) -> list[tuple[str, str, dict[str, Any] | None]]:
    return [
        ("GET", f"{V1}/destinations/search?q=liveton", None),
        ("POST", f"{V1}/destinations/resolve", {"osm_ref": LIVETON_REF}),
        ("GET", f"{V1}/destinations/{destination_id}/import", None),
        ("GET", f"{V1}/destinations/{destination_id}", None),
    ]


def walk(body: Any) -> Iterator[str]:
    """Every key of a JSON body, at any depth."""
    if isinstance(body, dict):
        for key, value in body.items():
            yield key
            yield from walk(value)
    elif isinstance(body, list):
        for value in body:
            yield from walk(value)


def off_app() -> FastAPI:
    """The switch-OFF app, pinned explicitly so ANY_CITY_SUITE_ON=1 (TC-490) cannot turn it ON."""
    return create_app(auth_test_settings(features_disabled=""))


def served(app: FastAPI) -> set[tuple[str, str]]:
    """(method, path) of every route the app serves, routers included."""
    return {
        (method, context.path)
        for context in iter_route_contexts(app.routes)
        for method in (context.methods or set()) - {"HEAD", "OPTIONS"}
    }


async def test_tc_487_any_city_the_four_routes_are_exactly_the_any_city_set(
    db_session: AsyncSession,
) -> None:
    assert served(build(db_session)) - served(off_app()) == ANY_CITY_ROUTES


async def test_tc_487_any_city_routes_need_a_token(live: httpx.AsyncClient) -> None:
    for method, path, body in requests_for(str(uuid.uuid4())):
        response = await live.request(method, path, json=body)
        assert response.status_code == 401, (method, path)
        assert response.json()["error"]["code"] == "UNAUTHENTICATED", (method, path)
        bad = await live.request(
            method, path, json=body, headers={"Authorization": "Bearer not-a-token"}
        )
        assert bad.status_code == 401, (method, path)


async def test_tc_487_any_city_reference_access_for_any_user_and_no_requester_field(
    live: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    alice, bob = await make_user(db_session, "a"), await make_user(db_session, "b")
    resolved = await live.post(
        f"{V1}/destinations/resolve", json={"osm_ref": LIVETON_REF}, headers=alice.headers
    )
    assert resolved.status_code == 202, resolved.text
    destination_id = resolved.json()["destination_id"]

    for user in (alice, bob):
        for method, path, body in requests_for(destination_id):
            response = await live.request(method, path, json=body, headers=user.headers)
            assert response.status_code == 200, (user.email, method, path, response.text)
            keys = set(walk(response.json()))
            assert "import_requested_by" not in keys, (method, path)
            assert str(alice.user_id) not in response.text, (method, path)


async def test_tc_487_any_city_daily_cap_is_counted_per_user(db_session: AsyncSession) -> None:
    app = build(db_session, live_daily_imports_per_user=1, live_daily_imports_global=50)
    alice, bob = await make_user(db_session, "a"), await make_user(db_session, "b")
    async with client_for(app) as client:
        first = await client.post(
            f"{V1}/destinations/resolve", json={"osm_ref": LIVETON_REF}, headers=alice.headers
        )
        assert first.status_code == 202, first.text
        capped = await client.post(
            f"{V1}/destinations/resolve", json={"osm_ref": TINYHAM_REF}, headers=alice.headers
        )
        assert capped.status_code == 429, capped.text
        assert capped.json()["error"]["code"] == "RATE_LIMITED"
        # Another user's cap is untouched, and a known city needs no new import.
        other = await client.post(
            f"{V1}/destinations/resolve", json={"osm_ref": TINYHAM_REF}, headers=bob.headers
        )
        assert other.status_code == 202, other.text
        known = await client.post(
            f"{V1}/destinations/resolve", json={"osm_ref": LIVETON_REF}, headers=alice.headers
        )
        assert known.status_code == 200, known.text
