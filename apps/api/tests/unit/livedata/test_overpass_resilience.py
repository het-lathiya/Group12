"""RUN-105B D4/D6: recorded HTTP failures, fake time, one bounded nearby query; no sockets."""

import logging
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from typing import Any
from urllib.parse import parse_qs

import pytest
import respx

from app.ai.breaker import CircuitBreaker
from app.livedata import throttle
from app.livedata.providers.base import BBox, LiveDataRateLimited, LiveDataUnavailable
from app.livedata.providers.osm import FAILURE_SNIPPET_CHARS, OverpassPlaces, _retry_after_s

pytestmark = [pytest.mark.any_city, pytest.mark.asyncio]

OVERPASS = "https://overpass.sample.test/api/interpreter"
USER_AGENT = "TravelPlanner-tests/1.0 (contact: none)"
BBOX = BBox(south=23.4, west=77.4, north=23.6, east=77.6)


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def guarded(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[throttle.GuardedPlaces, Clock, throttle.Throttle]:
    clock = Clock()
    spacing = throttle.Throttle(2, clock=clock, sleep=clock.sleep)
    monkeypatch.setattr(throttle, "overpass_throttle", lambda: spacing)
    return (
        throttle.GuardedPlaces(
            OverpassPlaces(OVERPASS, 90, USER_AGENT), spacing, CircuitBreaker(clock=clock)
        ),
        clock,
        spacing,
    )


@pytest.mark.parametrize(
    ("status", "header", "delay"),
    [
        (429, None, 900),
        (429, "12", 900),
        (429, "1200", 1200),
        (429, "invalid", 900),
        (504, None, 2),
        (504, "17", 17),
        (504, "invalid", 2),
    ],
)
async def test_overpass_defers_later_calls_without_retrying_the_failed_query(
    monkeypatch: pytest.MonkeyPatch, status: int, header: str | None, delay: int
) -> None:
    places, clock, spacing = guarded(monkeypatch)
    with respx.mock() as router:
        route = router.post(OVERPASS).respond(
            status, text="Service busy", headers={"Retry-After": header} if header else {}
        )
        with pytest.raises(LiveDataUnavailable if status == 504 else LiveDataRateLimited):
            await places.fetch(BBOX)
        assert route.call_count == 1
        assert spacing.retry_after_s == delay

        clock.now = 1000 + delay - 0.1
        with pytest.raises(LiveDataRateLimited):
            await places.fetch(BBOX)
        with pytest.raises(LiveDataRateLimited):
            await places.largest_city_near(23.5, 77.5, 150)
        assert route.call_count == 1
        assert spacing.retry_after_s == 1
        assert clock.sleeps == []

        clock.now = 1000 + delay
        route.respond(200, json={"elements": []})
        assert await places.fetch(BBOX) == []
        assert route.call_count == 2
        assert spacing.retry_after_s == 0


async def test_overpass_honours_retry_after_http_date(monkeypatch: pytest.MonkeyPatch) -> None:
    places, _, spacing = guarded(monkeypatch)
    date = format_datetime(datetime.now(UTC) + timedelta(seconds=1200), usegmt=True)
    with respx.mock() as router:
        route = router.post(OVERPASS).respond(429, headers={"Retry-After": date})
        with pytest.raises(LiveDataRateLimited):
            await places.fetch(BBOX)
    assert 1199 <= spacing.retry_after_s <= 1200
    assert route.call_count == 1


async def test_repeated_504_backoff_then_breaker_and_success_reset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    places, clock, spacing = guarded(monkeypatch)
    with respx.mock() as router:
        route = router.post(OVERPASS).respond(504)
        for calls, delay in enumerate((2, 4, 8, 16, 60), 1):
            with pytest.raises(LiveDataUnavailable, match="http 504"):
                await places.fetch(BBOX)
            assert route.call_count == calls
            assert spacing.retry_after_s == delay
            with pytest.raises(LiveDataRateLimited):
                await places.fetch(BBOX)
            assert route.call_count == calls
            clock.now += delay

        route.respond(200, json={"elements": []})
        await places.fetch(BBOX)
        route.respond(504)
        with pytest.raises(LiveDataUnavailable):
            await places.fetch(BBOX)
        assert spacing.retry_after_s == 2
        assert route.call_count == 7
        assert clock.sleeps == [2]


@pytest.mark.parametrize("status", [406, 429, 504])
async def test_overpass_failure_logs_status_and_a_bounded_redacted_body(
    status: int, caplog: pytest.LogCaptureFixture
) -> None:
    from app.livedata.providers.base import overpass_places_query

    query = overpass_places_query(BBOX, 90)
    private = [
        "fake-secret-1",
        "fake-token-2",
        "fake-password-3",
        "fake-cookie-4",
        "team@example.test",
        "192.0.2.4",
        "2001:db8::1",
        "fake-bearer-5",
    ]
    body = (
        "<html><h1>Query refused: server load.</h1>\n"
        '"api_key": "fake-secret-1", "access_token": "fake-token-2", '
        '"password": "fake-password-3", Cookie: fake-cookie-4; '
        '"Authorization": "Bearer fake-bearer-5" '
        "team@example.test 192.0.2.4 2001:db8::1 "
        "https://example.test/error?key=fake-secret-1 "
        f"{query} " + "detail " * 100 + "</html>"
    )
    with respx.mock() as router, caplog.at_level(logging.WARNING, logger="app.livedata"):
        route = router.post(OVERPASS).respond(status, text=body)
        with pytest.raises(LiveDataUnavailable if status != 429 else LiveDataRateLimited):
            await OverpassPlaces(OVERPASS, 90, USER_AGENT).fetch(BBOX)
    messages = [r.getMessage() for r in caplog.records if r.name == "app.livedata.providers.osm"]
    assert len(messages) == 1
    message = messages[0]
    assert f"status={status}" in message
    assert "body=Query refused: server load." in message
    assert len(message.split("body=", 1)[1].split(" retry_after_s=", 1)[0]) <= FAILURE_SNIPPET_CHARS
    assert all(value not in message for value in [*private, USER_AGENT, query, OVERPASS])
    assert "<html>" not in message
    assert route.call_count == 1


@pytest.mark.parametrize("value", [None, "", "invalid", "-1", "NaN", "Infinity", "1.5"])
async def test_invalid_retry_after_uses_local_backoff(value: str | None) -> None:
    assert _retry_after_s(value) is None


async def test_retry_after_accepts_seconds_and_dates_and_clamps_past_dates() -> None:
    now = datetime(2026, 11, 28, tzinfo=UTC)
    assert _retry_after_s(" 120 ", now=now) == 120
    assert _retry_after_s("Sat, 28 Nov 2026 00:02:00 GMT", now=now) == 120
    assert _retry_after_s("Fri, 27 Nov 2026 23:59:00 GMT", now=now) == 0


def city(osm_id: int, name: str, lat: float, population: int = 100) -> dict[str, Any]:
    return {
        "type": "node",
        "id": osm_id,
        "lat": lat,
        "lon": 0.0,
        "tags": {"place": "city", "name": name, "population": str(population)},
    }


@pytest.mark.parametrize("latitude", [0.1, 0.4, 0.8, 1.2])
async def test_nearby_search_expands_through_bands_with_only_one_http_query(
    latitude: float,
) -> None:
    elements = [
        city(1, "Close (SAMPLE)", latitude, 100),
        city(2, "Larger (SAMPLE)", latitude, 200),
        city(3, "Far capital (SAMPLE)", 4.0, 10_000_000),
        city(4, "Own city (SAMPLE)", 0.0, 20_000_000),
    ]
    with respx.mock() as router:
        route = router.post(OVERPASS).respond(200, json={"elements": elements})
        result = await OverpassPlaces(OVERPASS, 90, USER_AGENT).largest_city_near(0.0, 0.0, 150)
    assert result == "Larger (SAMPLE)"
    assert route.call_count == 1
    query = parse_qs(route.calls.last.request.content.decode())["data"][0]
    assert "around:150000" in query
    assert "[maxsize:67108864]" in query
    assert query.endswith("out center tags;")  # tags-only responses omitted node coordinates (D6)


async def test_nearby_search_prefers_the_first_populated_radius() -> None:
    elements = [city(1, "Near (SAMPLE)", 0.1, 100), city(2, "Farther (SAMPLE)", 1.2, 100_000)]
    with respx.mock() as router:
        router.post(OVERPASS).respond(200, json={"elements": elements})
        assert await OverpassPlaces(OVERPASS, 90, USER_AGENT).largest_city_near(0, 0, 150) == (
            "Near (SAMPLE)"
        )


@pytest.mark.parametrize("radius", [150, 1000])
async def test_far_cities_are_rejected_even_when_the_provider_returns_them(radius: int) -> None:
    elements = [city(1, "Far (SAMPLE)", 1.4), city(2, "Capital (SAMPLE)", 4.0, 10_000_000)]
    with respx.mock() as router:
        route = router.post(OVERPASS).respond(200, json={"elements": elements})
        assert (
            await OverpassPlaces(OVERPASS, 90, USER_AGENT).largest_city_near(0, 0, radius) is None
        )
    assert route.call_count == 1
    assert "around:150000" in parse_qs(route.calls.last.request.content.decode())["data"][0]


async def test_smaller_requested_radius_is_respected() -> None:
    with respx.mock() as router:
        route = router.post(OVERPASS).respond(
            200, json={"elements": [city(1, "City (SAMPLE)", 0.4)]}
        )
        assert await OverpassPlaces(OVERPASS, 90, USER_AGENT).largest_city_near(0, 0, 25) is None
    assert "around:25000" in parse_qs(route.calls.last.request.content.decode())["data"][0]


async def test_nearby_nodes_without_coordinates_are_not_suggestions() -> None:
    node = city(1, "Unknown location (SAMPLE)", 0.1)
    del node["lat"]
    del node["lon"]
    with respx.mock() as router:
        router.post(OVERPASS).respond(200, json={"elements": [node]})
        assert await OverpassPlaces(OVERPASS, 90, USER_AGENT).largest_city_near(0, 0, 150) is None
