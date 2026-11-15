"""The owned-route matrix of the two-user authorization suite (IMP-215 step 1; FR-005, NFR-012).

One entry per implemented owned MVP route (§6.2 "Own resources"): its API id, method, path
template as FastAPI declares it, and how to build a valid request for user A's resource. Entries
marked ``foreign`` name A's resource in the path and must answer user B with 404 NOT_FOUND; entries
marked ``scoped`` name no resource and must answer B with B's own data only.

``unlisted_routes`` walks the app and returns every /api/v1 route that is neither in the matrix,
nor reference data (§6.2), nor a declared stub that answers 501 NOT_IMPLEMENTED (IMD-37). When a
card builds a stubbed route, the walk reports it until its entry is added here; see
docs/guides/authz-suite.md.
"""

import ast
import inspect
import textwrap
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from fastapi import FastAPI
from fastapi.routing import APIRoute, iter_route_contexts

API_PREFIX = "/api/v1"


@dataclass(frozen=True)
class Owned:
    """User A's resources, built by the suite's fixture through the API and the MOCK job path."""

    user_id: uuid.UUID
    email: str
    trip_id: uuid.UUID
    trip_title: str
    generation_id: uuid.UUID
    destination_id: uuid.UUID
    place_id: uuid.UUID
    item_id: uuid.UUID

    def secrets(self) -> list[str]:
        """Values of A that must never appear in a response to B."""
        return [
            str(self.user_id),
            self.email,
            str(self.trip_id),
            self.trip_title,
            str(self.generation_id),
        ]


Body = Callable[[Owned], dict[str, Any]]


@dataclass(frozen=True)
class RouteCase:
    api_id: str
    method: str
    path: str
    access: Literal["foreign", "scoped"]
    body: Body | None = None
    params: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return f"{self.api_id} {self.method} {self.path}"

    def url(self, owned: Owned) -> str:
        return self.path.format(
            trip_id=owned.trip_id, generation_id=owned.generation_id, item_id=owned.item_id
        )


def trip_body(owned: Owned) -> dict[str, Any]:
    return {
        "title": "B's own trip",
        "destination_id": str(owned.destination_id),
        "start_date": "2026-12-04",
        "end_date": "2026-12-06",
        "adults": 1,
    }


def preferences_body(owned: Owned) -> dict[str, Any]:
    return {
        "interests": ["food"],
        "pace": "relaxed",
        "budget_priority": "saving",
        "transport_pref": "walking",
        "accommodation_type": "any",
        "step_free_required": True,
        "notes": "Written by user B.",
        "must_visit_place_ids": [str(owned.place_id)],
    }


MATRIX: tuple[RouteCase, ...] = (
    RouteCase("API-03", "GET", "/api/v1/me", "scoped"),
    RouteCase(
        "API-04", "PATCH", "/api/v1/me", "scoped", body=lambda _: {"ai_notice_acknowledged": True}
    ),
    RouteCase("API-07", "POST", "/api/v1/trips", "scoped", body=trip_body),
    RouteCase("API-08", "GET", "/api/v1/trips", "scoped", params={"include_archived": "true"}),
    RouteCase("API-10", "GET", "/api/v1/trips/{trip_id}", "foreign"),
    RouteCase(
        "API-11", "PATCH", "/api/v1/trips/{trip_id}", "foreign", body=lambda _: {"title": "B's"}
    ),
    RouteCase(
        "API-14", "PUT", "/api/v1/trips/{trip_id}/preferences", "foreign", body=preferences_body
    ),
    RouteCase("API-15", "GET", "/api/v1/trips/{trip_id}/preferences", "foreign"),
    RouteCase(
        "API-22",
        "POST",
        "/api/v1/trips/{trip_id}/generations",
        "foreign",
        body=lambda _: {"mode": "ai"},
    ),
    RouteCase("API-23", "GET", "/api/v1/generations/{generation_id}", "foreign"),
    RouteCase("API-09", "GET", "/api/v1/itineraries/latest", "scoped"),
    RouteCase("API-24", "GET", "/api/v1/trips/{trip_id}/itinerary", "foreign"),
    RouteCase(
        "API-25",
        "POST",
        "/api/v1/trips/{trip_id}/itinerary/items",
        "foreign",
        body=lambda owned: {"plan_revision": 1, "day_number": 1, "place_id": str(owned.place_id)},
    ),
    RouteCase(
        "API-26",
        "PATCH",
        "/api/v1/itinerary/items/{item_id}",
        "foreign",
        body=lambda _: {"plan_revision": 1, "duration_min": 60, "is_locked": False},
    ),
    RouteCase(
        "API-27",
        "DELETE",
        "/api/v1/itinerary/items/{item_id}",
        "foreign",
        params={"plan_revision": 1},
    ),
    RouteCase("API-28", "GET", "/api/v1/itinerary/items/{item_id}/alternatives", "foreign"),
    RouteCase(
        "API-29",
        "POST",
        "/api/v1/itinerary/items/{item_id}/replace",
        "foreign",
        # A's item already visits owned.place_id (its must-visit place), and Owned names no
        # alternative, so A's control call uses revision 0: 409 STALE_PLAN proves the request is
        # well formed and reaches A's item, while B still gets 404 before the revision check.
        body=lambda owned: {"plan_revision": 0, "place_id": str(owned.place_id)},
    ),
    RouteCase(
        "API-32",
        "POST",
        "/api/v1/trips/{trip_id}/itinerary/validate",
        "foreign",
        body=lambda _: {"plan_revision": 1},
    ),
    RouteCase("API-33", "GET", "/api/v1/trips/{trip_id}/costs", "foreign"),
    RouteCase(
        "API-34",
        "PATCH",
        "/api/v1/trips/{trip_id}/budget-settings",
        "foreign",
        body=lambda _: {"transport_allowance_per_day": "1.00"},
    ),
)

# §6.2 reference data: shared read-only rows, no owner (API-06, API-16, API-17).
REFERENCE: frozenset[tuple[str, str]] = frozenset(
    {
        ("GET", "/api/v1/destinations"),
        ("GET", "/api/v1/places"),
        ("GET", "/api/v1/places/{place_id}"),
    }
)


def is_not_implemented(route: APIRoute) -> bool:
    """True when the handler's whole body is ``raise EndpointNotImplemented()`` (IMD-37)."""
    function = ast.parse(textwrap.dedent(inspect.getsource(route.endpoint))).body[0]
    assert isinstance(function, ast.AsyncFunctionDef | ast.FunctionDef)
    statements = [s for s in function.body if not isinstance(s, ast.Expr)]  # drop a docstring
    if len(statements) != 1 or not isinstance(statements[0], ast.Raise):
        return False
    raised = statements[0].exc
    return (
        isinstance(raised, ast.Call)
        and isinstance(raised.func, ast.Name)
        and raised.func.id == "EndpointNotImplemented"
    )


def api_routes(app: FastAPI) -> list[tuple[str, str, APIRoute]]:
    """(method, path, route) for every /api/v1 route of the app."""
    routes = []
    for context in iter_route_contexts(app.routes):
        route = context.original_route
        if not context.path.startswith(API_PREFIX) or not isinstance(route, APIRoute):
            continue
        for method in sorted((context.methods or set()) - {"HEAD", "OPTIONS"}):
            routes.append((method, context.path, route))
    return routes


def not_implemented_routes(app: FastAPI) -> list[tuple[str, str]]:
    return [(m, p) for m, p, route in api_routes(app) if is_not_implemented(route)]


def unlisted_routes(app: FastAPI) -> list[str]:
    """Implemented owned routes of the app that the matrix does not list."""
    listed = {(case.method, case.path) for case in MATRIX} | REFERENCE
    return [
        f"{method} {path}"
        for method, path, route in api_routes(app)
        if (method, path) not in listed and not is_not_implemented(route)
    ]


# IMP-605 saved places (API-19 to API-21; TC-345). The path also names A's must-visit place.
@dataclass(frozen=True)
class PlaceRouteCase(RouteCase):
    def url(self, owned: Owned) -> str:
        return self.path.format(trip_id=owned.trip_id, place_id=owned.place_id)


MATRIX = (
    *MATRIX,
    PlaceRouteCase("API-19", "PUT", "/api/v1/trips/{trip_id}/saved-places/{place_id}", "foreign"),
    PlaceRouteCase(
        "API-20", "DELETE", "/api/v1/trips/{trip_id}/saved-places/{place_id}", "foreign"
    ),
    RouteCase("API-21", "GET", "/api/v1/trips/{trip_id}/saved-places", "foreign"),
)


# IMP-610 versions: API-38's version_id is A's newest version, looked up by test_ownership's
# ``call`` (the matrix builds URLs from Owned alone).
MATRIX = (
    *MATRIX,
    RouteCase("API-36", "GET", "/api/v1/trips/{trip_id}/versions", "foreign"),
    RouteCase(
        "API-37",
        "POST",
        "/api/v1/trips/{trip_id}/versions",
        "foreign",
        body=lambda _: {"plan_revision": 1, "name": "B's version"},
    ),
    RouteCase(
        "API-38",
        "POST",
        "/api/v1/trips/{trip_id}/versions/{version_id}/restore",
        "foreign",
        body=lambda _: {"plan_revision": 1},
    ),
)

# IMP-609 summary
MATRIX = (*MATRIX, RouteCase("API-35", "GET", "/api/v1/trips/{trip_id}/summary", "foreign"))


# IMP-602 trip actions
MATRIX = (
    *MATRIX,
    RouteCase(
        "API-11 archive",
        "PATCH",
        "/api/v1/trips/{trip_id}",
        "foreign",
        body=lambda _: {"status": "archived"},
    ),
    RouteCase("API-12", "DELETE", "/api/v1/trips/{trip_id}", "foreign"),
    RouteCase("API-13", "POST", "/api/v1/trips/{trip_id}/duplicate", "foreign"),
)


# IMP-607 regeneration: revision 0 reaches the owner's stale-plan check without starting a job.
@dataclass(frozen=True)
class RegenerateRouteCase(RouteCase):
    def url(self, owned: Owned) -> str:
        return self.path.format(trip_id=owned.trip_id, day_number=1)


MATRIX = (
    *MATRIX,
    RegenerateRouteCase(
        "API-30",
        "POST",
        "/api/v1/trips/{trip_id}/itinerary/days/{day_number}/regenerate",
        "foreign",
        body=lambda _: {"plan_revision": 0},
    ),
    RouteCase(
        "API-31",
        "POST",
        "/api/v1/trips/{trip_id}/itinerary/regenerate",
        "foreign",
        body=lambda _: {"plan_revision": 0},
    ),
)
