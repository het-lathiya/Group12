"""Live-data HTTP clients (app/livedata/providers/osm.py, wiki.py; A2 §6.1, §6.3, §6.5, §7.1:
TC-468, TC-469, TC-470). HTTP is mocked with respx from the SAMPLE recordings in
tests/fixtures/livedata/; no socket is opened.
"""

import copy
import json
import logging
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

import httpx
import pytest
import respx

from app.livedata.providers.base import (
    BBox,
    LiveDataError,
    LiveDataRateLimited,
    LiveDataTimeout,
    LiveDataUnavailable,
    overpass_places_query,
)
from app.livedata.providers.osm import NominatimGeocoder, OverpassPlaces
from app.livedata.providers.wiki import (
    WIKIPEDIA_API,
    WIKIVOYAGE_API,
    MediaWikiGuides,
    split_sections,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "livedata"
NOMINATIM = "https://nominatim.sample.test"
OVERPASS = "https://overpass.sample.test/api/interpreter"
USER_AGENT = "AITravelPlanner-test/1.0 (contact: team@example.org)"
BBOX = BBox(south=23.44, west=77.44, north=23.56, east=77.56)
QUERY = "Liveton & Söder/../x?y=1"
BODY_MARKER = "MARKER-BODY-TEXT-7731"


def load(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def geocoder() -> NominatimGeocoder:
    return NominatimGeocoder(NOMINATIM, 10, USER_AGENT)


async def no_wait(_: float) -> None:
    return None


def overpass() -> OverpassPlaces:
    return OverpassPlaces(OVERPASS, 90, USER_AGENT, sleep=no_wait)


def guides() -> MediaWikiGuides:
    return MediaWikiGuides(10, USER_AGENT)


# ---------- Nominatim ----------


@pytest.mark.asyncio
async def test_livedata_search_keeps_settlements_with_user_agent_and_encoded_query() -> None:
    with respx.mock(assert_all_called=True) as router:
        route = router.get(f"{NOMINATIM}/search").respond(
            200, json=load("nominatim_search_liveton.json")
        )
        result = await geocoder().search(QUERY)

    assert [c.osm_ref for c in result] == ["R9000001", "N9000102"]
    first = result[0]
    assert first.name == "Liveton (SAMPLE)"
    assert first.country_code == "IN"
    assert first.region == "Sample State"
    assert first.kind == "city"
    assert (first.lat, first.lon) == (23.5, 77.5)
    request = route.calls.last.request
    assert request.headers["User-Agent"] == USER_AGENT
    assert request.url.path == "/search"
    assert QUERY not in str(request.url)
    params = parse_qs(request.url.query.decode())
    assert params["q"] == [QUERY]
    assert params["format"] == ["jsonv2"]
    assert params["addressdetails"] == ["1"]
    assert params["namedetails"] == ["1"]
    assert params["limit"] == ["10"]
    assert params["accept-language"] == ["en"]


@pytest.mark.asyncio
async def test_livedata_search_caps_settlements_at_eight() -> None:
    item = load("nominatim_search_liveton.json")[0]
    items = []
    for i in range(12):
        copy_ = copy.deepcopy(item)
        copy_["osm_id"] = 9000001 + i
        items.append(copy_)
    with respx.mock() as router:
        router.get(f"{NOMINATIM}/search").respond(200, json=items)
        result = await geocoder().search("liveton")
    assert len(result) == 8


@pytest.mark.asyncio
async def test_livedata_lookup_maps_bbox_and_english_name() -> None:
    with respx.mock(assert_all_called=True) as router:
        route = router.get(f"{NOMINATIM}/lookup").respond(
            200, json=load("nominatim_lookup_liveton.json")
        )
        place = await geocoder().lookup("R9000001")

    assert place is not None
    assert place.osm_ref == "R9000001"
    assert place.name == "Liveton Nagar (SAMPLE)"
    assert place.name_en == "Liveton (SAMPLE)"
    assert place.kind == "city"
    assert place.country_code == "IN"
    # Nominatim [south, north, west, east] -> BBox(south, west, north, east).
    assert place.bbox == BBox(south=23.44, west=77.44, north=23.56, east=77.56)
    request = route.calls.last.request
    assert request.headers["User-Agent"] == USER_AGENT
    params = parse_qs(request.url.query.decode())
    assert params["osm_ids"] == ["R9000001"]
    assert params["format"] == ["jsonv2"]


@pytest.mark.asyncio
async def test_livedata_lookup_empty_list_is_none_and_bad_ref_sends_nothing() -> None:
    with respx.mock() as router:
        route = router.get(f"{NOMINATIM}/lookup").respond(200, json=[])
        assert await geocoder().lookup("N123") is None
        assert await geocoder().lookup("X1; drop") is None
    assert route.call_count == 1


# ---------- Overpass ----------


@pytest.mark.asyncio
async def test_livedata_overpass_posts_fixed_query_and_parses_elements() -> None:
    with respx.mock(assert_all_called=True) as router:
        route = router.post(OVERPASS).respond(200, json=load("overpass_liveton.json"))
        elements = await overpass().fetch(BBOX)

    assert [(e.osm_type, e.osm_id) for e in elements] == [
        ("n", 9100001),
        ("w", 9100002),
        ("r", 9100003),
        ("n", 9100004),
        ("n", 9100007),
    ]
    assert elements[1].lat == 23.51
    assert elements[1].lon == 77.49
    assert elements[0].tags["tourism"] == "museum"
    assert elements[4].tags == {}
    request = route.calls.last.request
    assert request.headers["User-Agent"] == USER_AGENT
    form = parse_qs(request.content.decode())
    assert form["data"] == [overpass_places_query(BBOX, 90)]
    assert "Liveton" not in request.content.decode()


@pytest.mark.asyncio
async def test_livedata_largest_city_near_picks_highest_population() -> None:
    with respx.mock() as router:
        route = router.post(OVERPASS).respond(200, json=load("overpass_cities_tinyham.json"))
        # Both population-bearing cities lie in the 100-150 km band from this test centre.
        name = await overpass().largest_city_near(26.2, 79.2, 150)
    assert name == "Bigtown (SAMPLE)"
    body = parse_qs(route.calls.last.request.content.decode())["data"][0]
    assert 'node["place"="city"]' in body
    assert "around:150000" in body


@pytest.mark.asyncio
async def test_livedata_largest_city_near_without_population_takes_first_by_name() -> None:
    elements = {
        "elements": [
            {
                "type": "node",
                "id": 1,
                "lat": 1.1,
                "lon": 1.0,
                "tags": {"name": "Zed (SAMPLE)", "place": "city"},
            },
            {
                "type": "node",
                "id": 2,
                "lat": 1.1,
                "lon": 1.0,
                "tags": {"name": "Abe (SAMPLE)", "place": "city"},
            },
        ]
    }
    with respx.mock() as router:
        router.post(OVERPASS).respond(200, json=elements)
        assert await overpass().largest_city_near(1.0, 1.0, 150) == "Abe (SAMPLE)"
        router.post(OVERPASS).respond(200, json={"elements": []})
        assert await overpass().largest_city_near(1.0, 1.0, 150) is None


# ---------- error mapping, one attempt, only Overpass HTTP failure snippets ----------


async def call_search() -> object:
    return await geocoder().search(QUERY)


async def call_lookup() -> object:
    return await geocoder().lookup("R9000001")


async def call_overpass() -> object:
    return await overpass().fetch(BBOX)


async def call_wiki() -> object:
    return await guides().fetch("Liveton (SAMPLE)", 23.5, 77.5)


CLIENTS = [
    ("GET", f"{NOMINATIM}/search", call_search),
    ("GET", f"{NOMINATIM}/lookup", call_lookup),
    ("POST", OVERPASS, call_overpass),
    ("GET", WIKIVOYAGE_API, call_wiki),
]
FAILURES: list[tuple[str, Any, type[LiveDataError], str]] = [
    ("timeout", httpx.ReadTimeout("slow"), LiveDataTimeout, "timeout"),
    ("429", httpx.Response(429, text=BODY_MARKER), LiveDataRateLimited, "http 429"),
    ("503", httpx.Response(503, text=BODY_MARKER), LiveDataUnavailable, "http 503"),
    ("connection", httpx.ConnectError("refused"), LiveDataUnavailable, "connection"),
    (
        "malformed",
        httpx.Response(200, text=f"<html>{BODY_MARKER}"),
        LiveDataUnavailable,
        "malformed response",
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "url", "call"), CLIENTS, ids=["search", "lookup", "overpass", "wiki"]
)
@pytest.mark.parametrize(
    ("label", "outcome", "error", "message"), FAILURES, ids=[f[0] for f in FAILURES]
)
async def test_livedata_failures_map_to_safe_errors_after_one_attempt(
    method: str,
    url: str,
    call: Any,
    label: str,
    outcome: Any,
    error: type[LiveDataError],
    message: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with respx.mock() as router, caplog.at_level(logging.DEBUG, logger="app.livedata"):
        route = router.route(method=method, url__startswith=url)
        if isinstance(outcome, Exception):
            route.side_effect = outcome
        else:
            route.return_value = outcome
        with pytest.raises(error) as raised:
            await call()

    assert type(raised.value) is error
    assert str(raised.value) == message
    assert raised.value.__cause__ is None
    # N1: a busy Overpass (503) is retried twice; every other failure is one attempt.
    assert route.call_count == (3 if method == "POST" and label == "503" else 1)
    if method == "POST" and label in ("429", "503"):
        assert BODY_MARKER in caplog.text
    else:
        assert BODY_MARKER not in caplog.text
    assert QUERY not in caplog.text


@pytest.mark.asyncio
async def test_livedata_success_logs_counts_only(caplog: pytest.LogCaptureFixture) -> None:
    with respx.mock() as router, caplog.at_level(logging.DEBUG, logger="app.livedata"):
        router.get(f"{NOMINATIM}/search").respond(200, json=load("nominatim_search_liveton.json"))
        router.get(WIKIVOYAGE_API).respond(200, json=load("mediawiki_liveton.json"))
        router.get(WIKIPEDIA_API, params={"list": "geosearch"}).respond(
            200, json=load("mediawiki_geosearch_empty.json")
        )
        router.get(WIKIPEDIA_API).respond(200, json=load("mediawiki_missing.json"))
        await geocoder().search(QUERY)
        await guides().fetch("Liveton (SAMPLE)", 23.5, 77.5)
    assert caplog.records
    assert QUERY not in caplog.text
    assert BODY_MARKER not in caplog.text
    assert "Liveton" not in caplog.text


# ---------- MediaWiki ----------


def test_livedata_split_sections_level_two_only() -> None:
    sections = split_sections(load("mediawiki_liveton.json")["query"]["pages"][0]["extract"])
    assert [(i, h) for i, h, _ in sections] == [
        (0, "Introduction"),
        (1, "Understand"),
        (2, "See"),
        (4, "Eat"),
    ]
    understand = sections[1][2]
    assert "=== Climate ===" in understand
    assert "Winters are mild" in understand
    assert split_sections("== Only ==\ntext") == [(1, "Only", "text")]
    assert split_sections("") == []


@pytest.mark.asyncio
async def test_livedata_mediawiki_reads_both_sources_serially_with_maxlag() -> None:
    order: list[str] = []

    def answer(name: str) -> Any:
        def side_effect(request: httpx.Request) -> httpx.Response:
            order.append(name)
            return httpx.Response(200, json=load(name))

        return side_effect

    with respx.mock(assert_all_called=True) as router:
        voyage = router.get(WIKIVOYAGE_API)
        voyage.side_effect = answer("mediawiki_liveton.json")
        geo = router.get(WIKIPEDIA_API, params={"list": "geosearch"})
        geo.side_effect = answer("mediawiki_geosearch_empty.json")
        pedia = router.get(WIKIPEDIA_API)
        pedia.side_effect = answer("mediawiki_missing.json")
        sections = await guides().fetch("Liveton (SAMPLE)", 23.5, 77.5)

    assert order == [
        "mediawiki_liveton.json",
        "mediawiki_missing.json",
        "mediawiki_geosearch_empty.json",
    ]
    assert {s.source for s in sections} == {"wikivoyage"}
    assert [s.heading for s in sections] == ["Introduction", "Understand", "See", "Eat"]
    first = sections[0]
    assert first.page_id == 9000001
    assert first.revision_id == 90000010
    assert first.page_url == "https://en.wikivoyage.org/wiki/Liveton_(SAMPLE)"
    for route in (voyage, pedia, geo):
        for call in route.calls:
            assert call.request.headers["User-Agent"] == USER_AGENT
            params = parse_qs(call.request.url.query.decode())
            assert params["maxlag"] == ["5"]
            assert params["action"] == ["query"]
    page_params = parse_qs(voyage.calls.last.request.url.query.decode())
    assert page_params["titles"] == ["Liveton (SAMPLE)"]
    assert page_params["explaintext"] == ["1"]
    assert page_params["redirects"] == ["1"]
    assert page_params["inprop"] == ["url"]
    assert set(page_params["prop"][0].split("|")) >= {"extracts", "info"}
    geo_params = parse_qs(geo.calls.last.request.url.query.decode())
    assert geo_params["gscoord"] == ["23.5|77.5"]
    assert geo_params["gsradius"] == ["10000"]
    assert geo_params["gslimit"] == ["1"]


@pytest.mark.asyncio
async def test_livedata_mediawiki_missing_page_gives_no_sections() -> None:
    with respx.mock() as router:
        router.get(WIKIVOYAGE_API, params={"list": "geosearch"}).respond(
            200, json=load("mediawiki_geosearch_empty.json")
        )
        router.get(WIKIPEDIA_API, params={"list": "geosearch"}).respond(
            200, json=load("mediawiki_geosearch_empty.json")
        )
        router.get(WIKIVOYAGE_API).respond(200, json=load("mediawiki_missing.json"))
        router.get(WIKIPEDIA_API).respond(200, json=load("mediawiki_missing.json"))
        assert await guides().fetch("Nowhereville (SAMPLE)", 1.0, 2.0) == []


@pytest.mark.asyncio
async def test_livedata_mediawiki_geosearch_finds_the_title() -> None:
    titles: list[str] = []

    def page(request: httpx.Request) -> httpx.Response:
        title = parse_qs(request.url.query.decode())["titles"][0]
        titles.append(title)
        name = "mediawiki_liveton.json" if title == "Liveton (SAMPLE)" else "mediawiki_missing.json"
        return httpx.Response(200, json=load(name))

    guides_voyage_only = MediaWikiGuides(10, USER_AGENT, sources=(("wikivoyage", WIKIVOYAGE_API),))
    with respx.mock() as router:
        router.get(WIKIVOYAGE_API, params={"list": "geosearch"}).respond(
            200, json=load("mediawiki_geosearch_liveton.json")
        )
        router.get(WIKIVOYAGE_API).side_effect = page
        sections = await guides_voyage_only.fetch("Liveton Town", 23.5, 77.5)
    assert titles == ["Liveton Town", "Liveton (SAMPLE)"]
    assert sections
    assert sections[0].page_title == "Liveton (SAMPLE)"


@pytest.mark.asyncio
async def test_livedata_mediawiki_maxlag_is_unavailable() -> None:
    with respx.mock() as router:
        route = router.get(WIKIVOYAGE_API).respond(200, json=load("mediawiki_maxlag.json"))
        with pytest.raises(LiveDataUnavailable, match=r"^maxlag$"):
            await guides().fetch("Liveton (SAMPLE)", 23.5, 77.5)
    assert route.call_count == 1
