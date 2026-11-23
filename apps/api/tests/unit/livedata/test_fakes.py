"""Live-data fakes and factory (app/livedata/providers/fake.py, app/livedata/factory.py; A2 §7.1,
§7.4: TC-471). SAMPLE data only; no network.
"""

import math
from collections import Counter
from collections.abc import Awaitable, Callable, Iterator
from typing import Any

import pytest

from app.core.config import ConfigError, get_settings
from app.livedata import factory
from app.livedata.providers.base import (
    OVERPASS_TAGS,
    BBox,
    LiveDataError,
    LiveDataRateLimited,
    LiveDataTimeout,
    LiveDataUnavailable,
)
from app.livedata.providers.fake import (
    BIGTOWN_NAME,
    FAKE_SCENARIOS,
    LIVETON,
    TINYHAM,
    FakeGeocoder,
    FakeGuides,
    FakePlaces,
    FakeScenario,
)
from app.livedata.providers.osm import NominatimGeocoder, OverpassPlaces
from app.livedata.providers.wiki import MediaWikiGuides
from app.livedata.throttle import GuardedGeocoder, GuardedGuides, GuardedPlaces

FOOD = {"restaurant", "cafe", "fast_food", "food_court"}
ALLOWED_TAGS = {(key, value) for key, values in OVERPASS_TAGS for value in values}
ERRORS: dict[str, type[LiveDataError]] = {
    "timeout": LiveDataTimeout,
    "rate_limited": LiveDataRateLimited,
    "malformed": LiveDataUnavailable,
}


@pytest.fixture(autouse=True)
def fresh_factory() -> Iterator[None]:
    factory.reset_cache()
    yield
    factory.reset_cache()


def metres(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dy = (lat2 - lat1) * 111_320
    dx = (lon2 - lon1) * 111_320 * math.cos(math.radians(lat1))
    return math.hypot(dx, dy)


def calls(scenario: FakeScenario) -> list[Callable[[], Awaitable[Any]]]:
    geo = FakeGeocoder(scenario, app_env="test")
    places = FakePlaces(scenario, app_env="test")
    guides = FakeGuides(scenario, app_env="test")
    return [
        lambda: geo.search("liveton"),
        lambda: geo.lookup(LIVETON.osm_ref),
        lambda: places.fetch(LIVETON.bbox),
        lambda: places.largest_city_near(TINYHAM.lat, TINYHAM.lon, 150),
        lambda: guides.fetch(LIVETON.name, LIVETON.lat, LIVETON.lon),
    ]


# ---------- scenarios ----------


@pytest.mark.asyncio
async def test_livedata_fake_geocoder_ok_finds_sample_cities() -> None:
    geo = FakeGeocoder("ok", app_env="test")
    [liveton] = await geo.search("Liveton")
    assert (liveton.osm_ref, liveton.country_code, liveton.name) == (
        "R9000001",
        "IN",
        "Liveton (SAMPLE)",
    )
    [tinyham] = await geo.search("  TINYHAM ")
    assert tinyham.osm_ref == "R9000002"
    assert await geo.search("Paris") == []
    assert await geo.lookup("R9000001") == LIVETON
    assert await geo.lookup("R9000002") == TINYHAM
    assert await geo.lookup("R1") is None


@pytest.mark.asyncio
async def test_livedata_fake_places_ok_pass_the_minimum_places_gate() -> None:
    elements = await FakePlaces("ok", app_env="test").fetch(LIVETON.bbox)
    for e in elements:
        assert LIVETON.bbox.contains(e.lat, e.lon)
        assert e.tags["name"].endswith("(SAMPLE)")
        kinds = {(k, v) for k, v in e.tags.items() if (k, v) in ALLOWED_TAGS}
        assert len(kinds) == 1
    # Duplicates: same name within 75 m; everything else is a unique name.
    by_name: dict[str, list[Any]] = {}
    for e in elements:
        by_name.setdefault(e.tags["name"], []).append(e)
    duplicates = [group for group in by_name.values() if len(group) > 1]
    assert len(duplicates) >= 2
    for a, b in duplicates:
        assert metres(a.lat, a.lon, b.lat, b.lon) < 75
    unique = list(by_name.values())
    food = [g for g in unique if g[0].tags.get("amenity") in FOOD]
    assert len(unique) >= 40
    assert len(food) >= 6
    assert len(unique) - len(food) >= 12
    rich = Counter(k for e in elements for k in e.tags if k in ("wikidata", "wikipedia", "website"))
    assert rich["wikidata"] > 0
    assert rich["wikipedia"] > 0
    assert rich["website"] > 0
    assert any(k.startswith("addr:") for e in elements for k in e.tags)
    assert all(e.tags["website"].startswith("https://") for e in elements if "website" in e.tags)
    assert elements == await FakePlaces("ok", app_env="test").fetch(LIVETON.bbox)


@pytest.mark.asyncio
async def test_livedata_fake_places_follow_the_requested_box() -> None:
    box = BBox(south=10.0, west=20.0, north=10.2, east=20.3)
    elements = await FakePlaces("ok", app_env="test").fetch(box)
    assert len(elements) > 40
    assert all(box.contains(e.lat, e.lon) for e in elements)
    tiny = await FakePlaces("ok", app_env="test").fetch(TINYHAM.bbox)
    assert len(tiny) == 8
    assert all(TINYHAM.bbox.contains(e.lat, e.lon) for e in tiny)


@pytest.mark.asyncio
async def test_livedata_fake_small_scenario_is_tinyham() -> None:
    places = FakePlaces("small", app_env="test")
    elements = await places.fetch(LIVETON.bbox)
    assert len(elements) == 8
    assert all(LIVETON.bbox.contains(e.lat, e.lon) for e in elements)
    assert await places.largest_city_near(TINYHAM.lat, TINYHAM.lon, 150) == BIGTOWN_NAME
    assert BIGTOWN_NAME == "Bigtown (SAMPLE)"
    sections = await FakeGuides("small", app_env="test").fetch(TINYHAM.name, 0, 0)
    assert len(sections) == 1
    assert sections[0].page_title == "Tinyham (SAMPLE)"
    [tinyham] = await FakeGeocoder("small", app_env="test").search("tinyham")
    assert tinyham.osm_ref == "R9000002"


@pytest.mark.asyncio
async def test_livedata_fake_guides_ok_give_sample_sections() -> None:
    sections = await FakeGuides("ok", app_env="test").fetch(LIVETON.name, LIVETON.lat, LIVETON.lon)
    assert {s.source for s in sections} == {"wikivoyage", "wikipedia"}
    voyage = [s for s in sections if s.source == "wikivoyage"]
    assert [s.index for s in voyage] == list(range(len(voyage)))
    assert voyage[0].heading == "Introduction"
    assert all(s.page_url.startswith("https://") for s in sections)
    assert all("SAMPLE" in s.page_title for s in sections)


@pytest.mark.asyncio
async def test_livedata_fake_empty_scenario_returns_nothing() -> None:
    results = [await call() for call in calls("empty")]
    assert results == [[], None, [], None, []]


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", ["timeout", "rate_limited", "malformed"])
async def test_livedata_fake_error_scenarios_raise(scenario: FakeScenario) -> None:
    for call in calls(scenario):
        with pytest.raises(ERRORS[scenario]):
            await call()


def test_livedata_fake_scenarios_are_the_six_of_the_amendment() -> None:
    assert set(FAKE_SCENARIOS) == {"ok", "small", "empty", "timeout", "rate_limited", "malformed"}
    with pytest.raises(ConfigError):
        FakeGeocoder("nope", app_env="test")  # type: ignore[arg-type]  # an unknown scenario


@pytest.mark.parametrize("fake", [FakeGeocoder, FakePlaces, FakeGuides])
@pytest.mark.parametrize("app_env", ["staging", "production", ""])
def test_livedata_fakes_refuse_outside_local_and_test(fake: Any, app_env: str) -> None:
    with pytest.raises(ConfigError, match="local or test"):
        fake("ok", app_env=app_env)


@pytest.mark.parametrize("fake", [FakeGeocoder, FakePlaces, FakeGuides])
@pytest.mark.parametrize("app_env", ["local", "test"])
def test_livedata_fakes_build_in_local_and_test(fake: Any, app_env: str) -> None:
    assert fake("ok", app_env=app_env).scenario == "ok"


# ---------- factory ----------


@pytest.mark.parametrize("app_env", ["local", "test"])
def test_livedata_factory_builds_fakes_by_default(
    clean_settings_env: pytest.MonkeyPatch, app_env: str
) -> None:
    clean_settings_env.setenv("APP_ENV", app_env)
    assert get_settings().live_data_provider == "FAKE"
    assert isinstance(factory.get_geocoder(), FakeGeocoder)
    assert isinstance(factory.get_places_provider(), FakePlaces)
    guides = factory.get_guide_provider()
    assert isinstance(guides, FakeGuides)
    assert guides.scenario == factory.DEFAULT_FAKE_SCENARIO == "ok"
    assert factory.get_providers() is factory.get_providers()


@pytest.mark.parametrize("app_env", ["staging", "production"])
def test_livedata_factory_refuses_fakes_when_deployed(
    clean_settings_env: pytest.MonkeyPatch, app_env: str
) -> None:
    clean_settings_env.setenv("APP_ENV", app_env)
    clean_settings_env.setenv("LIVE_DATA_PROVIDER", "FAKE")
    with pytest.raises(ConfigError, match="FAKE is refused"):
        factory.get_geocoder()


def test_livedata_factory_builds_real_clients_for_live(
    clean_settings_env: pytest.MonkeyPatch,
) -> None:
    clean_settings_env.setenv("APP_ENV", "test")
    clean_settings_env.setenv("LIVE_DATA_PROVIDER", "LIVE")
    clean_settings_env.setenv("WIKI_USER_AGENT", "AITravelPlanner-test/1.0")
    # The real clients sit inside the throttle and breaker wrappers (A2 §7.1, §7.3).
    geocoder = factory.get_geocoder()
    places = factory.get_places_provider()
    guides = factory.get_guide_provider()
    assert isinstance(geocoder, GuardedGeocoder)
    assert isinstance(geocoder.inner, NominatimGeocoder)
    assert isinstance(places, GuardedPlaces)
    assert isinstance(places.inner, OverpassPlaces)
    assert isinstance(guides, GuardedGuides)
    assert isinstance(guides.inner, MediaWikiGuides)
