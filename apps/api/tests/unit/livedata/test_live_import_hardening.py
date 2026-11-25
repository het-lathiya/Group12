"""Live import hardening (any-city readiness gaps G8, G10, G11; A2 §6.3, §6.5, §7.2; IMP-725).

G8: an Overpass answer with an error note is a failure, never data. G10: a guide page carries its
coordinates, and only sections of a page inside the destination's box are kept. G11: the import CLI
runs the API's start-up checks. Offline only: respx and synthetic SAMPLE bodies.
"""

import json
import logging
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

import httpx
import pytest
import respx

from app.core.config import ConfigError, Settings
from app.livedata.providers.base import BBox, LiveDataUnavailable, WikiSection
from app.livedata.providers.osm import OverpassPlaces
from app.livedata.providers.wiki import WIKIVOYAGE_API, MediaWikiGuides
from app.places import live_import
from app.rag.live_guides import sections_inside

pytestmark = pytest.mark.any_city

FIXTURES = Path(__file__).parents[2] / "fixtures" / "livedata"
OVERPASS = "https://overpass-api.de/api/interpreter"
USER_AGENT = "AITravelPlanner-tests/1.0 (contact: none)"
BBOX = BBox(south=23.4, west=77.4, north=23.6, east=77.6)
NOTE = "runtime error: Query timed out MARKER-NOTE-4410"


def load(name: str) -> dict[str, Any]:
    body: dict[str, Any] = json.loads((FIXTURES / name).read_text())
    return body


def overpass() -> OverpassPlaces:
    return OverpassPlaces(OVERPASS, 90, USER_AGENT)


# ---------- G8: the error note ----------


@pytest.mark.asyncio
@pytest.mark.parametrize("elements", [[], None], ids=["empty", "partial"])
async def test_overpass_error_note_is_a_failure(
    elements: list[Any] | None, caplog: pytest.LogCaptureFixture
) -> None:
    body = load("overpass_liveton.json")
    if elements is not None:
        body["elements"] = elements
    body["remark"] = NOTE
    with respx.mock() as router, caplog.at_level(logging.DEBUG, logger="app.livedata"):
        router.post(OVERPASS).respond(200, json=body)
        with pytest.raises(LiveDataUnavailable, match=r"^error note$"):
            await overpass().fetch(BBOX)
        with pytest.raises(LiveDataUnavailable, match=r"^error note$"):
            await overpass().largest_city_near(23.5, 77.5, 150)
    assert "MARKER-NOTE-4410" not in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize("remark", [None, "", "a plain remark", 7])
async def test_overpass_without_an_error_note_is_data(remark: object) -> None:
    body = load("overpass_liveton.json")
    if remark is not None:
        body["remark"] = remark
    with respx.mock() as router:
        router.post(OVERPASS).respond(200, json=body)
        assert await overpass().fetch(BBOX)


# ---------- G10: the guide page's coordinates ----------


def voyage() -> MediaWikiGuides:
    return MediaWikiGuides(10, USER_AGENT, sources=(("wikivoyage", WIKIVOYAGE_API),))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("coordinates", "expected"),
    [
        ([{"lat": 23.5, "lon": 77.5, "primary": True, "globe": "earth"}], (23.5, 77.5)),
        ([], (None, None)),
        (None, (None, None)),
    ],
    ids=["given", "empty", "absent"],
)
async def test_mediawiki_asks_for_and_keeps_the_page_coordinates(
    coordinates: list[Any] | None, expected: tuple[float | None, float | None]
) -> None:
    body = load("mediawiki_liveton.json")
    if coordinates is not None:
        body["query"]["pages"][0]["coordinates"] = coordinates
    with respx.mock() as router:
        route = router.get(WIKIVOYAGE_API).respond(200, json=body)
        sections = await voyage().fetch("Liveton (SAMPLE)", 23.5, 77.5)
    assert sections
    assert {(s.page_lat, s.page_lon) for s in sections} == {expected}
    params = parse_qs(route.calls.last.request.url.query.decode())
    assert "coordinates" in params["prop"][0].split("|")


@pytest.mark.asyncio
@pytest.mark.parametrize("coordinates", [[{"lat": "north"}], [{"lon": 77.5}], "text"])
async def test_mediawiki_malformed_coordinates_are_a_safe_failure(coordinates: object) -> None:
    body = load("mediawiki_liveton.json")
    body["query"]["pages"][0]["coordinates"] = coordinates
    with respx.mock() as router:
        router.get(WIKIVOYAGE_API).mock(return_value=httpx.Response(200, json=body))
        with pytest.raises(LiveDataUnavailable, match=r"^malformed response$"):
            await voyage().fetch("Liveton (SAMPLE)", 23.5, 77.5)


def page(lat: float | None, lon: float | None) -> WikiSection:
    return WikiSection(
        source="wikivoyage",
        page_id=1,
        revision_id=10,
        page_title="Liveton (SAMPLE)",
        page_url="https://en.wikivoyage.org/wiki/Liveton_(SAMPLE)",
        index=1,
        heading="See",
        text="SAMPLE",
        page_lat=lat,
        page_lon=lon,
    )


def test_sections_inside_keeps_only_pages_in_the_box() -> None:
    inside, edge = page(23.5, 77.5), page(23.4, 77.6)
    others = [page(52.2, 0.1), page(23.7, 77.5), page(None, None), page(23.5, None)]
    assert sections_inside([inside, *others, edge], BBOX) == [inside, edge]


# ---------- G11: the CLI's start-up checks ----------

ON = "!any_city_mode"


def settings(**values: Any) -> Settings:
    base: dict[str, Any] = {
        "app_env": "local",
        "ai_provider": "MOCK",
        "database_url": "postgresql+psycopg://u:p@localhost/db",
    }
    return Settings(_env_file=None, **{**base, **values})


@pytest.mark.parametrize("app_env", ["staging", "production"])
def test_cli_refuses_fake_when_deployed_and_on(app_env: str) -> None:
    with pytest.raises(ConfigError, match="LIVE_DATA_PROVIDER"):
        live_import.check_start(
            settings(app_env=app_env, features_disabled=ON, live_data_provider="FAKE")
        )


@pytest.mark.parametrize("features", ["", ON], ids=["off", "on"])
@pytest.mark.parametrize("agent", ["", "   ", "<AITravelPlanner/1.0 (contact: team email)>"])
def test_cli_refuses_live_without_a_user_agent_whatever_the_switch(
    features: str, agent: str
) -> None:
    with pytest.raises(ConfigError, match="WIKI_USER_AGENT") as raised:
        live_import.check_start(
            settings(features_disabled=features, live_data_provider="LIVE", wiki_user_agent=agent)
        )
    assert "contact" not in str(raised.value)


def test_cli_accepts_live_with_a_user_agent_and_local_fake() -> None:
    live_import.check_start(settings(live_data_provider="LIVE", wiki_user_agent=USER_AGENT))
    live_import.check_start(settings(features_disabled=ON, live_data_provider="FAKE"))


def test_cli_main_stops_before_any_work(
    clean_settings_env: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def never(**_: object) -> None:
        raise AssertionError("the import started")

    clean_settings_env.setattr(live_import, "import_destination", never)
    clean_settings_env.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost/db")
    clean_settings_env.setenv("LIVE_DATA_PROVIDER", "LIVE")
    assert live_import.main(["--osm-ref", "R9000001"]) == live_import.EXIT_FAILED
    captured = capsys.readouterr()
    assert captured.err.startswith("configuration error: WIKI_USER_AGENT")
    assert captured.out == ""


def test_cli_force_is_off_by_default() -> None:
    assert live_import.parse_args(["--osm-ref", "R9000001"]).force is False
    assert live_import.parse_args(["--osm-ref", "R9000001", "--force"]).force is True
