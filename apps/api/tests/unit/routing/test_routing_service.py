"""Routing service with OpenRouteService and the route cache (§9.3.5; FR-078, FR-079, NFR-038:
TC-234, TC-235, TC-341, and the TC-236 and TC-237 path; IMP-307).

HTTP is mocked with respx from the format fixtures in provider_recordings/ors/ (see its README);
the cache is an in-memory stand-in. tests/api/test_route_cache.py covers the real table.
"""

import json
import logging
import uuid
from collections.abc import Iterator
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
import respx

from app.routing import client as client_module
from app.routing.cache import FALLBACK_TTL
from app.routing.client import OrsClient, RoutingUnavailable
from app.routing.estimate import TravelEstimate, TravelMode, buffer_minutes
from app.routing.service import RoutingService

RECORDINGS = Path(__file__).resolve().parents[2] / "fixtures" / "provider_recordings" / "ors"
WALK_URL = "https://api.openrouteservice.org/v2/directions/foot-walking/json"
DRIVE_URL = "https://api.openrouteservice.org/v2/directions/driving-car/json"
KEY = "test-ors-key-not-real"


def recording(name: str) -> Any:
    return json.loads((RECORDINGS / name).read_text(encoding="utf-8"))


def place(lat: str = "53.868", lon: str = "2.115") -> Any:
    return SimpleNamespace(id=uuid.uuid4(), lat=Decimal(lat), lon=Decimal(lon))


class MemoryCache:
    def __init__(self) -> None:
        self.rows: dict[tuple[Any, Any, str], Any] = {}
        self.ttls: list[timedelta] = []

    async def get(self, from_id: Any, to_id: Any, mode: TravelMode) -> Any:
        return self.rows.get((from_id, to_id, mode.value))

    async def upsert(
        self, from_id: Any, to_id: Any, result: TravelEstimate, *, ttl: timedelta
    ) -> None:
        self.ttls.append(ttl)
        self.rows[(from_id, to_id, result.mode.value)] = SimpleNamespace(
            travel_minutes=result.minutes,
            distance_m=result.distance_m,
            travel_source=result.travel_source,
        )


@pytest.fixture
def cache() -> MemoryCache:
    return MemoryCache()


@pytest.fixture
def ors() -> Iterator[respx.MockRouter]:
    with respx.mock(assert_all_called=False) as router:
        yield router


def service(cache: MemoryCache, key: str = KEY, allowance: int = 2000) -> Any:
    return RoutingService(cache, OrsClient(key, 8, allowance))  # type: ignore[arg-type]  # stand-in


@pytest.mark.asyncio
async def test_tc_234_a_route_is_estimated_from_ors_and_cached(
    cache: MemoryCache, ors: respx.MockRouter
) -> None:
    route = ors.post(WALK_URL).respond(json=recording("directions_foot_walking.json"))
    a, b = place(), place("53.876", "2.120")
    result = await service(cache).travel(a, b, "walking")
    assert result == TravelEstimate(15, 1241, TravelMode.WALKING, "routing_api")
    assert result.label is None
    assert buffer_minutes(result.travel_source) == 5
    assert cache.ttls == [timedelta(days=30)]
    request = route.calls.last.request
    assert request.headers["authorization"] == KEY
    assert json.loads(request.content) == {"coordinates": [[2.115, 53.868], [2.12, 53.876]]}


@pytest.mark.asyncio
async def test_tc_235_a_cached_pair_makes_no_http_call(
    cache: MemoryCache, ors: respx.MockRouter, caplog: pytest.LogCaptureFixture
) -> None:
    route = ors.post(WALK_URL).respond(json=recording("directions_foot_walking.json"))
    routing, a, b = service(cache), place(), place("53.876", "2.120")
    first = await routing.travel(a, b, "walking")
    with caplog.at_level(logging.INFO, logger="app.routing.service"):
        second = await routing.travel(a, b, "walking")
    assert second == first
    assert route.call_count == 1
    assert "route cache hit mode=walking travel_source=routing_api" in caplog.messages


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["car", "local_transport"])
async def test_driving_modes_use_driving_car(
    cache: MemoryCache, ors: respx.MockRouter, mode: str
) -> None:
    ors.post(DRIVE_URL).respond(json=recording("directions_driving_car.json"))
    result = await service(cache).travel(place(), place("53.876", "2.120"), mode)
    assert (result.minutes, result.distance_m, result.travel_source) == (4, 1502, "routing_api")
    assert result.label == ("Estimate" if mode == "local_transport" else None)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response", "reason"),
    [
        (httpx.Response(404, json=recording("directions_error_no_route.json")), "http 404"),
        (httpx.Response(429), "http 429"),
        (httpx.Response(500), "http 500"),
        (httpx.Response(200, json={"routes": []}), "malformed response"),
        (httpx.Response(200, text="not json"), "malformed response"),
        (httpx.TimeoutException("slow"), "timeout"),
        (httpx.ConnectError("down"), "connection"),
    ],
)
async def test_ors_failure_falls_back_to_the_labelled_estimate(
    cache: MemoryCache,
    ors: respx.MockRouter,
    caplog: pytest.LogCaptureFixture,
    response: Any,
    reason: str,
) -> None:
    ors.post(WALK_URL).mock(
        side_effect=response if isinstance(response, Exception) else None,
        return_value=None if isinstance(response, Exception) else response,
    )
    with caplog.at_level(logging.INFO, logger="app.routing.service"):
        result = await service(cache).travel(place(), place("53.876", "2.120"), "walking")
    assert result.travel_source == "fallback_estimate"
    assert result.label == "Estimate"
    assert buffer_minutes(result.travel_source) == 15
    assert cache.ttls == [timedelta(days=1)]
    assert f"route fallback mode=walking reason={reason}" in caplog.messages


@pytest.mark.asyncio
async def test_no_key_falls_back_without_any_http_call(
    cache: MemoryCache, ors: respx.MockRouter
) -> None:
    route = ors.post(WALK_URL).respond(json=recording("directions_foot_walking.json"))
    routing = service(cache, key="")
    a, b = place(), place("53.876", "2.120")
    assert (await routing.travel(a, b, "walking")).travel_source == "fallback_estimate"
    assert (await routing.travel(a, b, "walking")).travel_source == "fallback_estimate"
    assert route.call_count == 0
    assert cache.ttls == [FALLBACK_TTL]


@pytest.mark.asyncio
async def test_the_same_place_twice_is_neither_routed_nor_cached(
    cache: MemoryCache, ors: respx.MockRouter
) -> None:
    route = ors.post(WALK_URL).respond(json=recording("directions_foot_walking.json"))
    a = place()
    result = await service(cache).travel(a, a, "walking")
    assert (result.minutes, result.distance_m) == (0, 0)
    assert route.call_count == 0
    assert cache.rows == {}  # route_cache has CHECK (from_place_id <> to_place_id)


@pytest.mark.asyncio
async def test_tc_341_the_near_quota_warning_is_logged_once_at_80_percent(
    ors: respx.MockRouter, caplog: pytest.LogCaptureFixture
) -> None:
    ors.post(WALK_URL).respond(json=recording("directions_foot_walking.json"))
    ors_client = OrsClient(KEY, 8, 5)
    with caplog.at_level(logging.WARNING, logger="app.routing.client"):
        for _ in range(3):
            await ors_client.route((53.0, 2.0), (53.1, 2.1), TravelMode.WALKING)
        assert not caplog.records
        await ors_client.route((53.0, 2.0), (53.1, 2.1), TravelMode.WALKING)
        await ors_client.route((53.0, 2.0), (53.1, 2.1), TravelMode.WALKING)
    assert ors_client.calls_today == 5
    assert caplog.messages == ["routing near daily quota calls=4 allowance=5"]


@pytest.mark.asyncio
async def test_the_counter_starts_again_on_a_new_day(ors: respx.MockRouter) -> None:
    ors.post(WALK_URL).respond(json=recording("directions_foot_walking.json"))
    ors_client = OrsClient(KEY, 8, 5)
    await ors_client.route((53.0, 2.0), (53.1, 2.1), TravelMode.WALKING)
    ors_client._day = None
    await ors_client.route((53.0, 2.0), (53.1, 2.1), TravelMode.WALKING)
    assert ors_client.calls_today == 1


@pytest.mark.asyncio
async def test_an_error_never_carries_the_key(ors: respx.MockRouter) -> None:
    ors.post(WALK_URL).respond(status_code=403)
    with pytest.raises(RoutingUnavailable) as caught:
        await OrsClient(KEY, 8, 5).route((53.0, 2.0), (53.1, 2.1), TravelMode.WALKING)
    assert KEY not in str(caught.value)
    assert caught.value.__cause__ is None


def test_get_client_reads_the_settings_once(clean_settings_env: pytest.MonkeyPatch) -> None:
    clean_settings_env.setenv("ORS_API_KEY", KEY)
    clean_settings_env.setenv("ORS_DAILY_ALLOWANCE", "7")
    client_module.get_client.cache_clear()
    try:
        made = client_module.get_client()
        assert made is client_module.get_client()
        assert made._api_key == KEY
        assert made._daily_allowance == 7
    finally:
        client_module.get_client.cache_clear()
