"""Throttle, breakers, query safety and socket-guard hosts of the live-data module (IMP-723).

TC-468 (throttle part: at least 1 s between Nominatim calls), TC-469 (the Overpass query holds
only numbers and the fixed tag list) and TC-471 (socket-guard part: the new hosts are blocked).
Nothing here opens a socket: the inner providers are in-memory stubs and the clock is fake.
"""

import asyncio
import inspect
import itertools
import math
import re
import socket
from typing import Any

import pytest

from app.ai.breaker import QUOTA_COOL_DOWN_S, TRANSIENT_COOL_DOWN_S, CircuitBreaker
from app.livedata import throttle as throttle_module
from app.livedata.providers.base import (
    OVERPASS_MAXSIZE_BYTES,
    OVERPASS_TAGS,
    BBox,
    GeoCandidate,
    GeocodingProvider,
    GeoPlace,
    GuideSourceProvider,
    LiveDataError,
    LiveDataRateLimited,
    LiveDataTimeout,
    LiveDataUnavailable,
    OsmElement,
    PlacesProvider,
    WikiSection,
    overpass_city_query,
    overpass_places_query,
)
from app.livedata.throttle import (
    MEDIAWIKI_SPACING_S,
    NOMINATIM_SPACING_S,
    OVERPASS_SPACING_S,
    GuardedGeocoder,
    GuardedGuides,
    GuardedPlaces,
    Throttle,
)

BOX = BBox(south=12.9, west=77.5, north=13.1, east=77.7)


class FakeClock:
    """A monotonic clock that only moves when the fake sleep is awaited."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds
        await asyncio.sleep(0)


class StubGeocoder:
    def __init__(self, error: LiveDataError | None = None) -> None:
        self.error = error
        self.calls: list[str] = []

    async def search(self, q: str) -> list[GeoCandidate]:
        self.calls.append(q)
        if self.error is not None:
            raise self.error
        return []

    async def lookup(self, osm_ref: str) -> GeoPlace | None:
        self.calls.append(osm_ref)
        if self.error is not None:
            raise self.error
        return None


class StubPlaces:
    def __init__(self, error: LiveDataError | None = None) -> None:
        self.error = error
        self.calls = 0

    async def fetch(self, bbox: BBox) -> list[OsmElement]:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return [OsmElement(osm_type="n", osm_id=1, lat=13.0, lon=77.6, tags={"name": "A"})]

    async def largest_city_near(self, lat: float, lon: float, radius_km: float) -> str | None:
        self.calls += 1
        return None


class StubGuides:
    def __init__(self, clock: FakeClock) -> None:
        self.clock = clock
        self.starts: list[float] = []
        self.active = 0
        self.max_active = 0

    async def fetch(self, name: str, lat: float, lon: float) -> list[WikiSection]:
        self.starts.append(self.clock())
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        await asyncio.sleep(0)
        self.active -= 1
        return []


def _protocol_conformance(
    geocoder: GuardedGeocoder, places: GuardedPlaces, guides: GuardedGuides
) -> tuple[GeocodingProvider, PlacesProvider, GuideSourceProvider]:
    # mypy checks that the wrappers satisfy the protocols of providers.base.
    return geocoder, places, guides


# --- throttle ------------------------------------------------------------------------------------


def test_spacing_constants_follow_a2_7_3() -> None:
    assert NOMINATIM_SPACING_S == 1.0
    assert OVERPASS_SPACING_S == 2.0
    assert MEDIAWIKI_SPACING_S == 0.2


@pytest.mark.asyncio
async def test_first_call_does_not_wait_and_second_waits_the_spacing() -> None:
    clock = FakeClock()
    throttle = Throttle(NOMINATIM_SPACING_S, clock=clock, sleep=clock.sleep)
    starts: list[float] = []
    for _ in range(2):
        async with throttle.slot():
            starts.append(clock())
    assert clock.sleeps == [pytest.approx(1.0)]
    assert starts[1] - starts[0] >= NOMINATIM_SPACING_S


@pytest.mark.asyncio
async def test_no_wait_when_the_spacing_has_already_passed() -> None:
    clock = FakeClock()
    throttle = Throttle(OVERPASS_SPACING_S, clock=clock, sleep=clock.sleep)
    async with throttle.slot():
        pass
    clock.now += 5.0
    async with throttle.slot():
        pass
    assert clock.sleeps == []


@pytest.mark.asyncio
async def test_spacing_is_measured_from_the_end_of_the_previous_call() -> None:
    clock = FakeClock()
    throttle = Throttle(OVERPASS_SPACING_S, clock=clock, sleep=clock.sleep)
    async with throttle.slot():
        clock.now += 1.5  # the request itself took 1.5 s
    async with throttle.slot():
        pass
    assert clock.sleeps == [pytest.approx(2.0)]


@pytest.mark.asyncio
async def test_concurrent_calls_are_serialised_and_spaced() -> None:
    clock = FakeClock()
    throttle = Throttle(OVERPASS_SPACING_S, clock=clock, sleep=clock.sleep)
    starts: list[float] = []
    active = 0
    max_active = 0

    async def call() -> None:
        nonlocal active, max_active
        async with throttle.slot():
            active += 1
            max_active = max(max_active, active)
            starts.append(clock())
            await asyncio.sleep(0)
            active -= 1

    await asyncio.gather(*(call() for _ in range(4)))
    assert max_active == 1
    gaps = [b - a for a, b in itertools.pairwise(starts)]
    assert len(gaps) == 3
    assert all(gap >= OVERPASS_SPACING_S for gap in gaps)


@pytest.mark.asyncio
async def test_a_failed_call_still_counts_for_the_spacing() -> None:
    clock = FakeClock()
    throttle = Throttle(NOMINATIM_SPACING_S, clock=clock, sleep=clock.sleep)
    with pytest.raises(LiveDataUnavailable):
        async with throttle.slot():
            raise LiveDataUnavailable("down")
    async with throttle.slot():
        pass
    assert clock.sleeps == [pytest.approx(1.0)]


def test_negative_spacing_is_refused() -> None:
    with pytest.raises(ValueError, match="negative"):
        Throttle(-1.0)


@pytest.mark.asyncio
async def test_mediawiki_guard_is_serial_with_0_2_s_spacing() -> None:
    clock = FakeClock()
    inner = StubGuides(clock)
    guides = GuardedGuides(inner, Throttle(MEDIAWIKI_SPACING_S, clock=clock, sleep=clock.sleep))
    await asyncio.gather(*(guides.fetch("Liveton", 1.0, 2.0) for _ in range(3)))
    assert inner.max_active == 1
    gaps = [b - a for a, b in itertools.pairwise(inner.starts)]
    assert gaps == [pytest.approx(0.2), pytest.approx(0.2)]


@pytest.mark.asyncio
async def test_guarded_geocoder_keeps_one_second_between_nominatim_calls() -> None:
    clock = FakeClock()
    inner = StubGeocoder()
    geocoder = GuardedGeocoder(
        inner,
        Throttle(NOMINATIM_SPACING_S, clock=clock, sleep=clock.sleep),
        CircuitBreaker(clock=clock),
    )
    await geocoder.search("Liveton")
    await geocoder.lookup("N123")
    assert inner.calls == ["Liveton", "N123"]
    assert clock.sleeps == [pytest.approx(1.0)]


def _state(breaker: CircuitBreaker | None) -> str:
    # Read through a function so the type checker does not narrow the property between calls.
    assert breaker is not None
    return breaker.state


# --- breakers ------------------------------------------------------------------------------------


def _places(error: LiveDataError | None, clock: FakeClock) -> tuple[GuardedPlaces, StubPlaces]:
    inner = StubPlaces(error)
    guarded = GuardedPlaces(
        inner, Throttle(0.0, clock=clock, sleep=clock.sleep), CircuitBreaker(clock=clock)
    )
    return guarded, inner


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [LiveDataTimeout("t"), LiveDataUnavailable("u")])
async def test_breaker_opens_after_five_transient_failures_and_fails_fast(
    error: LiveDataError,
) -> None:
    clock = FakeClock()
    places, inner = _places(error, clock)
    for _ in range(4):
        with pytest.raises(type(error)):
            await places.fetch(BOX)
    assert places._guard.breaker is not None
    assert _state(places._guard.breaker) == "closed"
    with pytest.raises(type(error)):
        await places.fetch(BOX)
    assert _state(places._guard.breaker) == "open"
    assert inner.calls == 5

    with pytest.raises(LiveDataRateLimited):
        await places.fetch(BOX)
    with pytest.raises(LiveDataRateLimited):
        await places.largest_city_near(13.0, 77.6, 50)
    assert inner.calls == 5  # the provider was not called while open

    clock.now += TRANSIENT_COOL_DOWN_S
    assert _state(places._guard.breaker) == "half_open"


@pytest.mark.asyncio
async def test_a_429_opens_the_breaker_for_fifteen_minutes() -> None:
    clock = FakeClock()
    inner = StubGeocoder(LiveDataRateLimited("429"))
    breaker = CircuitBreaker(clock=clock)
    geocoder = GuardedGeocoder(inner, Throttle(0.0, clock=clock, sleep=clock.sleep), breaker)
    with pytest.raises(LiveDataRateLimited):
        await geocoder.search("Liveton")
    assert _state(breaker) == "open"
    assert QUOTA_COOL_DOWN_S == 15 * 60

    clock.now += TRANSIENT_COOL_DOWN_S
    with pytest.raises(LiveDataRateLimited, match="circuit breaker open"):
        await geocoder.search("Liveton")
    assert inner.calls == ["Liveton"]

    clock.now += QUOTA_COOL_DOWN_S
    assert _state(breaker) == "half_open"


@pytest.mark.asyncio
async def test_success_resets_the_failure_count_and_closes_a_half_open_breaker() -> None:
    clock = FakeClock()
    places, inner = _places(LiveDataTimeout("t"), clock)
    breaker = places._guard.breaker
    assert breaker is not None
    for _ in range(4):
        with pytest.raises(LiveDataTimeout):
            await places.fetch(BOX)
    inner.error = None
    assert len(await places.fetch(BOX)) == 1
    inner.error = LiveDataTimeout("t")
    for _ in range(4):
        with pytest.raises(LiveDataTimeout):
            await places.fetch(BOX)
    assert _state(breaker) == "closed"  # 4 + 4 failures with a success between them

    with pytest.raises(LiveDataTimeout):
        await places.fetch(BOX)
    assert _state(breaker) == "open"
    clock.now += TRANSIENT_COOL_DOWN_S
    inner.error = None
    await places.fetch(BOX)  # the half-open probe succeeds
    assert _state(breaker) == "closed"


@pytest.mark.asyncio
async def test_errors_are_re_raised_unchanged() -> None:
    clock = FakeClock()
    original = LiveDataUnavailable("bad status")
    places, _ = _places(original, clock)
    with pytest.raises(LiveDataUnavailable) as caught:
        await places.fetch(BOX)
    assert caught.value is original


@pytest.mark.asyncio
async def test_an_unexpected_error_is_not_recorded_or_swallowed() -> None:
    class Broken(StubPlaces):
        async def fetch(self, bbox: BBox) -> list[OsmElement]:
            raise KeyError("bug")

    clock = FakeClock()
    breaker = CircuitBreaker(clock=clock)
    places = GuardedPlaces(Broken(), Throttle(0.0, clock=clock, sleep=clock.sleep), breaker)
    for _ in range(6):
        with pytest.raises(KeyError):
            await places.fetch(BOX)
    assert _state(breaker) == "closed"


def test_per_process_instances_are_shared_and_wrap_the_protocols() -> None:
    assert throttle_module.nominatim_throttle() is throttle_module.nominatim_throttle()
    assert throttle_module.nominatim_throttle().spacing_s == NOMINATIM_SPACING_S
    assert throttle_module.overpass_throttle().spacing_s == OVERPASS_SPACING_S
    assert throttle_module.mediawiki_throttle().spacing_s == MEDIAWIKI_SPACING_S
    assert throttle_module.overpass_breaker() is throttle_module.overpass_breaker()
    assert throttle_module.overpass_breaker() is not throttle_module.nominatim_breaker()

    geocoder = throttle_module.guard_geocoder(StubGeocoder())
    places = throttle_module.guard_places(StubPlaces())
    guides = throttle_module.guard_guides(StubGuides(FakeClock()))
    assert geocoder._guard.breaker is throttle_module.nominatim_breaker()
    assert places._guard.breaker is throttle_module.overpass_breaker()
    assert guides._guard.breaker is None
    assert guides._guard.throttle is throttle_module.mediawiki_throttle()
    _protocol_conformance(geocoder, places, guides)


# --- query safety (TC-469) -----------------------------------------------------------------------

# Every word the places query may contain: QL keywords and the fixed tag keys and values.
_QL_WORDS = {"out", "json", "timeout", "maxsize", "nwr", "name", "center", "tags"}
_TAG_WORDS = {key for key, _ in OVERPASS_TAGS} | {v for _, vs in OVERPASS_TAGS for v in vs}
_NUMBER = r"-?\d+\.\d{6}"
_BOX_RE = rf"\({_NUMBER},{_NUMBER},{_NUMBER},{_NUMBER}\)"


def _words(query: str) -> set[str]:
    return set(re.findall(r"[A-Za-z_]+", query))


def test_places_query_matches_the_fixed_template() -> None:
    query = overpass_places_query(BOX, 90)
    lines = query.split("\n")
    assert lines[0] == f"[out:json][timeout:90][maxsize:{OVERPASS_MAXSIZE_BYTES}];"
    assert lines[1] == "("
    assert lines[-2:] == [");", "out center tags;"]
    body = lines[2:-2]
    assert len(body) == len(OVERPASS_TAGS)
    for line, (key, values) in zip(body, OVERPASS_TAGS, strict=True):
        alternatives = re.escape("|".join(values))
        pattern = rf'  nwr\["name"\]\["{re.escape(key)}"~"\^\({alternatives}\)\$"\]'
        assert re.fullmatch(pattern + _BOX_RE + ";", line), line
    assert "(12.900000,77.500000,13.100000,77.700000)" in query


def test_places_query_uses_only_the_fixed_vocabulary_and_characters() -> None:
    query = overpass_places_query(BBox(-33.95, 18.4, -33.85, 18.5), 90.5)
    assert _words(query) <= _QL_WORDS | _TAG_WORDS
    assert set(query) <= set('abcdefghijklmnopqrstuvwxyz_0123456789.,-:;()[]"~^$| \n')
    assert "[timeout:91]" in query


def test_city_query_matches_the_fixed_template() -> None:
    query = overpass_city_query(13.0, 77.6, 50, 90)
    assert re.fullmatch(
        rf"\[out:json\]\[timeout:90\]\[maxsize:{OVERPASS_MAXSIZE_BYTES}\];\n"
        rf'node\["place"="city"\]\["name"\]\(around:50000,{_NUMBER},{_NUMBER}\);\n'
        r"out center tags;",
        query,
    )
    assert _words(query) <= {
        "out",
        "json",
        "timeout",
        "maxsize",
        "center",
        "node",
        "place",
        "city",
        "name",
        "around",
        "tags",
    }


def test_query_builders_take_no_text_parameter() -> None:
    assert list(inspect.signature(overpass_places_query).parameters) == ["bbox", "timeout_s"]
    assert list(inspect.signature(overpass_city_query).parameters) == [
        "lat",
        "lon",
        "radius_km",
        "timeout_s",
    ]


_REFUSED = "finite|positive"
_BAD_NUMBERS: list[Any] = [math.nan, math.inf, -math.inf, "13.0", True, None, "Paris"]


@pytest.mark.parametrize("bad", _BAD_NUMBERS)
def test_places_query_refuses_a_non_number_coordinate(bad: Any) -> None:
    box = object.__new__(BBox)  # skip __post_init__ to reach the builder's own check
    for name, value in (("south", bad), ("west", 77.5), ("north", 13.1), ("east", 77.7)):
        object.__setattr__(box, name, value)
    with pytest.raises(ValueError, match=_REFUSED):
        overpass_places_query(box, 90)


# bool is left out: BBox accepts it as an int, and the query builder refuses it (test above).
@pytest.mark.parametrize("bad", [b for b in _BAD_NUMBERS if not isinstance(b, bool)])
def test_bbox_refuses_a_non_number_coordinate(bad: Any) -> None:
    with pytest.raises((ValueError, TypeError)):
        BBox(south=bad, west=77.5, north=13.1, east=77.7)


@pytest.mark.parametrize("bad", _BAD_NUMBERS)
def test_city_query_refuses_a_non_number_coordinate(bad: Any) -> None:
    with pytest.raises(ValueError, match=_REFUSED):
        overpass_city_query(bad, 77.6, 50, 90)
    with pytest.raises(ValueError, match=_REFUSED):
        overpass_city_query(13.0, bad, 50, 90)
    with pytest.raises(ValueError, match=_REFUSED):
        overpass_city_query(13.0, 77.6, bad, 90)
    with pytest.raises(ValueError, match=_REFUSED):
        overpass_city_query(13.0, 77.6, 50, bad)


@pytest.mark.parametrize("bad", [*_BAD_NUMBERS, 0, -5])
def test_places_query_refuses_a_bad_timeout(bad: Any) -> None:
    with pytest.raises(ValueError, match=_REFUSED):
        overpass_places_query(BOX, bad)


def test_city_text_cannot_reach_either_query() -> None:
    injected = 'Paris"];out;node["x'
    with pytest.raises(TypeError):
        overpass_places_query(BOX, 90, injected)  # type: ignore[call-arg]  # no text parameter
    with pytest.raises(TypeError):
        overpass_city_query(13.0, 77.6, 50, 90, name=injected)  # type: ignore[call-arg]  # same
    for query in (overpass_places_query(BOX, 90), overpass_city_query(13.0, 77.6, 50, 90)):
        assert "Paris" not in query


# --- socket guard (TC-471, guard part) ------------------------------------------------------------

LIVE_DATA_HOSTS = [
    "nominatim.openstreetmap.org",
    "overpass-api.de",
    "en.wikivoyage.org",
    "de.wikivoyage.org",
    "wikivoyage.org",
    "en.wikipedia.org",
    "wikipedia.org",
]


@pytest.mark.parametrize("host", LIVE_DATA_HOSTS)
def test_socket_guard_matches_the_live_data_hosts(provider_socket_guard: Any, host: str) -> None:
    assert provider_socket_guard.active
    assert provider_socket_guard.match(host) is not None
    assert provider_socket_guard.match(host.upper() + ".") is not None


@pytest.mark.parametrize("host", LIVE_DATA_HOSTS)
def test_socket_guard_blocks_resolving_the_live_data_hosts(
    provider_socket_guard: Any, monkeypatch: pytest.MonkeyPatch, host: str
) -> None:
    import _socket

    calls: list[object] = []

    def resolver(*args: object, **kwargs: object) -> list[object]:
        calls.append(args)
        return []

    monkeypatch.setattr(_socket, "getaddrinfo", resolver)
    with pytest.raises(provider_socket_guard.error, match=re.escape(host)):
        socket.getaddrinfo(host, 443)
    assert calls == []


@pytest.mark.parametrize(
    "host", ["openstreetmap.org", "overpass-api.de.example.com", "example.org"]
)
def test_socket_guard_does_not_match_other_hosts(provider_socket_guard: Any, host: str) -> None:
    assert provider_socket_guard.match(host) is None
