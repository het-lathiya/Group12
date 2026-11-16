"""Route inventory and identity rules (§3.4, §6.2; IMP-108: TC-344, TC-058, TC-059, TC-348).

Every route of the app, except the public allow-list, must answer 401 UNAUTHENTICATED without a
valid token. The walk covers routes added by later cards automatically, so an unprotected route
fails this test. A request body can never name a user: request models forbid unknown fields, and a
body field such as user_id is rejected with 422 (IMD-45).
"""

import re
import uuid
from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.routing import APIRoute, iter_route_contexts
from fixtures.auth import AuthUser, auth_test_settings, bearer, client_for, make_token
from pydantic import BaseModel, ConfigDict

from app.auth import deps
from app.auth.deps import CurrentUser, current_user
from app.main import create_app

# The public allow-list of the IMP-108 card (§6.2 API-01, API-02 and the API docs).
PUBLIC_PATHS = frozenset({"/health", "/health/ready", "/docs", "/openapi.json"})
# Static pages FastAPI serves next to /docs when the docs are enabled (outside production,
# IMP-103): the ReDoc page and the Swagger UI OAuth redirect. They hold no data.
DOCS_COMPANION_PATHS = frozenset({"/redoc", "/docs/oauth2-redirect"})
UNPROTECTED = PUBLIC_PATHS | DOCS_COMPANION_PATHS
PATH_PARAMETER = re.compile(r"\{[^}]+\}")


def route_inventory(app: FastAPI) -> list[tuple[str, str]]:
    """(method, path) for every route the app serves, routers included."""
    routes = []
    for context in iter_route_contexts(app.routes):
        path = context.path
        for method in sorted((context.methods or set()) - {"HEAD", "OPTIONS"}):
            routes.append((method, path))
    return routes


def protected_routes(app: FastAPI) -> list[tuple[str, str]]:
    return [(m, p) for m, p in route_inventory(app) if p not in UNPROTECTED]


async def no_database() -> AsyncIterator[Any]:
    raise AssertionError("the database was reached without a valid token")
    yield  # pragma: no cover


def app_without_database() -> FastAPI:
    app = create_app(auth_test_settings())
    app.dependency_overrides[deps.db_session] = no_database
    return app


BAD_TOKENS = {
    "none": {},
    "expired": bearer(make_token(uuid.uuid4(), expired=True)),
    "wrong audience": bearer(make_token(uuid.uuid4(), wrong_aud=True)),
    "tampered": bearer(make_token(uuid.uuid4())[:-2] + "xx"),
}


@pytest.mark.asyncio
@pytest.mark.parametrize("token", BAD_TOKENS, ids=str)
async def test_tc_344_every_non_public_route_needs_a_token(token: str) -> None:
    app = app_without_database()
    routes = protected_routes(app)
    assert ("GET", "/api/v1/me") in routes  # the walk is not empty

    reachable = []
    async with client_for(app) as client:
        for method, path in routes:
            url = PATH_PARAMETER.sub(str(uuid.uuid4()), path)
            response = await client.request(method, url, headers=BAD_TOKENS[token])
            body = response.json()
            if response.status_code != 401 or body["error"]["code"] != "UNAUTHENTICATED":
                reachable.append(f"{method} {path} -> {response.status_code}")
    assert reachable == []


@pytest.mark.asyncio
async def test_inventory_public_routes_answer_without_a_token() -> None:
    app = app_without_database()
    public = [(m, p) for m, p in route_inventory(app) if p in UNPROTECTED]
    assert ("GET", "/health") in public
    async with client_for(app) as client:
        for method, path in public:
            response = await client.request(method, path)
            if response.status_code == 501:
                # IMD-37: a declared, unbuilt route (API-02 until IMP-201) is skipped by this suite.
                assert response.json()["error"]["code"] == "NOT_IMPLEMENTED", f"{method} {path}"
                continue
            if path == "/health/ready" and response.status_code == 503:
                # §6 API-02: this app has no database, so readiness answers 503 not_ready.
                assert response.json()["checks"]["database"] == "down"
                continue
            assert response.status_code == 200, f"{method} {path}"


def test_inventory_docs_companions_are_only_fastapi_doc_pages() -> None:
    app = app_without_database()
    for context in iter_route_contexts(app.routes):
        if context.path in DOCS_COMPANION_PATHS:
            # FastAPI's own HTML routes, never an application endpoint.
            assert not isinstance(context.original_route, APIRoute), context.path
    production = create_app(
        auth_test_settings(
            app_env="production",
            ai_provider="GEMINI",
            gemini_api_key="unused-test-value",
            gemini_model_id="unused-test-model",
            gemini_embedding_model_id="gemini-embedding-2",
        )
    )
    paths = {path for _, path in route_inventory(production)}
    assert not paths & (DOCS_COMPANION_PATHS | {"/docs", "/openapi.json"})


def test_tc_348_no_request_body_can_name_a_user() -> None:
    # Every request model forbids unknown fields and declares no user field (IMD-45).
    offenders = []
    for context in iter_route_contexts(create_app(auth_test_settings()).routes):
        route = context.original_route
        if not isinstance(route, APIRoute) or route.body_field is None:
            continue
        model = route.body_field.field_info.annotation
        if not (isinstance(model, type) and issubclass(model, BaseModel)):
            offenders.append(f"{context.path}: body is not a model")
            continue
        if model.model_config.get("extra") != "forbid" or "user_id" in model.model_fields:
            offenders.append(f"{context.path}: {model.__name__}")
    assert offenders == []


class ProbeIn(BaseModel):
    """A request model as every card writes them: unknown fields are rejected."""

    model_config = ConfigDict(extra="forbid")
    title: str


@pytest.mark.asyncio
async def test_tc_058_a_body_naming_another_user_is_rejected(
    api_app: FastAPI, auth_user: AuthUser
) -> None:
    # A probe route behind the same router-level CurrentUser as /api/v1 in app.main.
    probe = APIRouter(prefix="/api/v1", dependencies=[Depends(current_user)])

    @probe.post("/probe/inventory")
    async def echo(body: ProbeIn, user: CurrentUser) -> dict[str, str]:
        return {"user_id": str(user.user_id), "title": body.title}

    api_app.include_router(probe)
    other_user = str(uuid.uuid4())

    async with client_for(api_app) as client:
        rejected = await client.post(
            "/api/v1/probe/inventory",
            json={"title": "Trip", "user_id": other_user},
            headers=auth_user.headers,
        )
        accepted = await client.post(
            "/api/v1/probe/inventory", json={"title": "Trip"}, headers=auth_user.headers
        )

    assert rejected.status_code == 422
    error = rejected.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert [detail["field"] for detail in error["details"]] == ["user_id"]
    assert other_user not in rejected.text
    # TC-057: the handler sees the token's user, never one from the request.
    assert accepted.status_code == 200
    assert accepted.json() == {"user_id": str(auth_user.user_id), "title": "Trip"}


# IMP-702 (TC-344, TC-347, TC-431, TC-432): the contract file, more token failures and the cut
# extension routes.

import hashlib  # noqa: E402  # IMP-702 append-only block
import json  # noqa: E402
from pathlib import Path  # noqa: E402

from route_matrix import MATRIX, REFERENCE  # noqa: E402

CONTRACT = Path(__file__).resolve().parents[4] / "contracts" / "openapi.v1.json"
PUBLIC_OPERATIONS = frozenset({("GET", "/health"), ("GET", "/health/ready")})  # API-01, API-02
# A key that is not the project's: a token another issuer signed (derived, no secret-like literal).
FOREIGN_KEY = hashlib.sha256(b"imp-702 another issuer, pytest only").hexdigest()

MORE_BAD_TOKENS = {
    "wrong issuer with valid signature": bearer(
        make_token(uuid.uuid4(), iss="https://evil.example/auth/v1")
    ),
    "signed by another issuer": bearer(
        make_token(uuid.uuid4(), secret=FOREIGN_KEY, iss="https://evil.example/auth/v1")
    ),
    "algorithm none": bearer(make_token(uuid.uuid4(), algorithm="none", secret="")),
    "no exp": bearer(make_token(uuid.uuid4(), omit=["exp"])),
    "sub not a uuid": bearer(make_token("not-a-uuid")),
    "not a jwt": bearer("not.a.jwt"),
    "basic scheme": {"Authorization": "Basic dXNlcjpwYXNz"},
}


def contract_operations() -> list[tuple[str, str, dict[str, Any]]]:
    paths = json.loads(CONTRACT.read_text(encoding="utf-8"))["paths"]
    return [(m.upper(), p, op) for p, ops in paths.items() for m, op in ops.items()]


def test_tc_344_inventory_every_contract_operation_is_owned_or_reference_and_needs_a_bearer() -> (
    None
):
    listed = {(case.method, case.path) for case in MATRIX} | REFERENCE
    unlisted, open_ = [], []
    for method, path, operation in contract_operations():
        if (method, path) in PUBLIC_OPERATIONS:
            continue
        if (method, path) not in listed:
            unlisted.append(f"{method} {path}")
        if {"HTTPBearer": []} not in operation.get("security", []):
            open_.append(f"{method} {path}")
    assert unlisted == []
    assert open_ == []
    served = {(m, p) for m, p, _ in contract_operations()}
    assert served >= listed  # no stale matrix entry the contract does not declare


@pytest.mark.asyncio
@pytest.mark.parametrize("token", MORE_BAD_TOKENS, ids=str)
async def test_tc_347_inventory_more_bad_tokens_are_refused_everywhere(token: str) -> None:
    app = app_without_database()
    reachable = []
    async with client_for(app) as client:
        for method, path in protected_routes(app):
            url = PATH_PARAMETER.sub(str(uuid.uuid4()), path)
            response = await client.request(method, url, headers=MORE_BAD_TOKENS[token])
            if response.status_code != 401 or response.json()["error"]["code"] != "UNAUTHENTICATED":
                reachable.append(f"{method} {path} -> {response.status_code}")
    assert reachable == []


# §6.6 extension endpoints (API-43, API-63 to API-75); every card that would build them is cut.
EXTENSION_ROUTES = (
    ("API-43", "GET", "/api/v1/trips/{trip_id}/packing-list"),
    ("API-63", "GET", "/api/v1/trips/{trip_id}/places/{place_id}/why"),
    ("API-64", "POST", "/api/v1/trip-intake"),
    ("API-65", "POST", "/api/v1/trips/{trip_id}/itinerary/days/{day_number}/explanation"),
    ("API-66", "GET", "/api/v1/trips/{trip_id}/itinerary/days/{day_number}/optimise"),
    ("API-67", "POST", "/api/v1/trips/{trip_id}/itinerary/days/{day_number}/optimise"),
    ("API-68", "GET", "/api/v1/trips/{trip_id}/weather"),
    ("API-69", "POST", "/api/v1/trips/{trip_id}/itinerary/swap-days"),
    ("API-70", "GET", "/api/v1/trips/{trip_id}/today"),
    ("API-71", "GET", "/api/v1/trips/{trip_id}/budget-fit"),
    ("API-72", "GET", "/api/v1/places/{place_id}/context"),
    ("API-73", "GET", "/api/v1/destinations/{destination_id}/context"),
    ("API-74", "POST", "/api/v1/trips/{trip_id}/packing-list/refine"),
    ("API-75", "PATCH", "/api/v1/trips/{trip_id}/packing-list/items/{item_id}"),
)


@pytest.mark.asyncio
async def test_tc_432_extension_routes_are_not_mounted_and_answer_404() -> None:
    # IMD-65: no extension route is mounted, so each answers 404 NOT_FOUND like an unknown route,
    # even with a valid token. When a card mounts one, this fails until its cases are added.
    app = app_without_database()
    mounted = {(m, p) for m, p in route_inventory(app)}
    assert [api for api, m, p in EXTENSION_ROUTES if (m, p) in mounted] == []
    headers = bearer(make_token(uuid.uuid4()))
    async with client_for(app) as client:
        for api_id, method, path in EXTENSION_ROUTES:
            url = PATH_PARAMETER.sub("1", path) if "{day_number}" in path else path
            response = await client.request(
                method, PATH_PARAMETER.sub(str(uuid.uuid4()), url), headers=headers
            )
            assert response.status_code == 404, api_id
            assert response.json()["error"]["code"] == "NOT_FOUND", api_id


@pytest.mark.parametrize("route", EXTENSION_ROUTES, ids=lambda r: r[0])
def test_tc_431_extension_ownership_case(route: tuple[str, str, str]) -> None:
    pytest.skip("cut by IMD-65")
