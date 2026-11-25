"""Offline live-data providers for local runs and tests (Amendment A2 §7.1, §7.4; IMP-723). SAMPLE.

Every name here is invented and labelled SAMPLE: "Liveton (SAMPLE)" has enough places to pass the
minimum-places gate of A2 §6.4, "Tinyham (SAMPLE)" has too few, and its nearby city is
"Bigtown (SAMPLE)". The places are generated deterministically from the fixed tag list, inside the
bounding box they are asked for. The fakes refuse to be built unless ``APP_ENV`` is local or test.

Scenarios (one per instance): ``ok`` (data by name or box), ``small`` (the Tinyham data
everywhere), ``empty`` (no results), ``timeout``, ``rate_limited`` and ``malformed`` (the three
live-data errors). The file is ``fake.py``, not ``mock.py``: the vendor-adapters import contract
protects ``app.*.providers.mock``.
"""

import math
from typing import Final, Literal, get_args

from app.core.config import ConfigError
from app.livedata.providers.base import (
    BBox,
    GeoCandidate,
    GeoPlace,
    LiveDataRateLimited,
    LiveDataTimeout,
    LiveDataUnavailable,
    OsmElement,
    OsmType,
    WikiSection,
)

FakeScenario = Literal["ok", "small", "empty", "timeout", "rate_limited", "malformed"]
FAKE_SCENARIOS: Final[tuple[str, ...]] = get_args(FakeScenario)
ALLOWED_ENVS: Final = frozenset({"local", "test"})

LIVETON_REF: Final = "R9000001"
TINYHAM_REF: Final = "R9000002"
BIGTOWN_NAME: Final = "Bigtown (SAMPLE)"

LIVETON: Final = GeoPlace(
    osm_ref=LIVETON_REF,
    name="Liveton (SAMPLE)",
    name_en="Liveton (SAMPLE)",
    display_name="Liveton (SAMPLE), Sample State, India",
    region="Sample State",
    country_code="IN",
    lat=23.5,
    lon=77.5,
    kind="city",
    bbox=BBox(south=23.44, west=77.44, north=23.56, east=77.56),
)
TINYHAM: Final = GeoPlace(
    osm_ref=TINYHAM_REF,
    name="Tinyham (SAMPLE)",
    name_en="Tinyham (SAMPLE)",
    display_name="Tinyham (SAMPLE), Sample State, India",
    region="Sample State",
    country_code="IN",
    lat=24.9,
    lon=79.1,
    kind="village",
    bbox=BBox(south=24.875, west=79.075, north=24.925, east=79.125),
)
_PLACES_BY_REF: Final = {LIVETON_REF: LIVETON, TINYHAM_REF: TINYHAM}
_SEARCH_KEYS: Final = (("liveton", LIVETON), ("tinyham", TINYHAM))

# (key, value) pairs of the fixed Overpass tag list (A2 §6.3), split into non-food and food.
_FOOD_VALUES: Final = ("restaurant", "cafe", "fast_food", "food_court")
_NON_FOOD: Final[tuple[tuple[str, str], ...]] = (
    ("tourism", "museum"),
    ("historic", "fort"),
    ("leisure", "park"),
    ("tourism", "viewpoint"),
    ("historic", "palace"),
    ("amenity", "place_of_worship"),
    ("tourism", "gallery"),
    ("natural", "peak"),
    ("amenity", "marketplace"),
    ("historic", "monument"),
    ("leisure", "garden"),
    ("tourism", "attraction"),
    ("amenity", "theatre"),
    ("historic", "memorial"),
    ("tourism", "zoo"),
    ("shop", "mall"),
    ("historic", "ruins"),
    ("leisure", "nature_reserve"),
    ("amenity", "arts_centre"),
    ("natural", "beach"),
    ("historic", "castle"),
    ("tourism", "aquarium"),
    ("shop", "department_store"),
    ("historic", "archaeological_site"),
    ("tourism", "theme_park"),
)
_FOOD: Final[tuple[tuple[str, str], ...]] = tuple(("amenity", v) for v in _FOOD_VALUES)
_TYPES: Final[tuple[OsmType, ...]] = ("n", "w", "r")

LIVETON_NON_FOOD: Final = 32
LIVETON_FOOD: Final = 12
LIVETON_DUPLICATES: Final = 4
TINYHAM_NON_FOOD: Final = 5
TINYHAM_FOOD: Final = 3
# A duplicate sits about 17 m north of its original, well inside the 75 m dedupe radius.
DUPLICATE_OFFSET_DEG: Final = 0.00015


def _check_env(app_env: str) -> None:
    if app_env not in ALLOWED_ENVS:
        raise ConfigError(
            ["LIVE_DATA_PROVIDER: FAKE is allowed only when APP_ENV is local or test"]
        )


def _check_scenario(scenario: str) -> None:
    if scenario not in FAKE_SCENARIOS:
        raise ConfigError(["live-data fake scenario must be one of " + ", ".join(FAKE_SCENARIOS)])


class _Fake:
    def __init__(self, scenario: FakeScenario = "ok", *, app_env: str) -> None:
        _check_env(app_env)
        _check_scenario(scenario)
        self.scenario: FakeScenario = scenario

    def _raise_for_scenario(self) -> None:
        if self.scenario == "timeout":
            raise LiveDataTimeout("timeout")
        if self.scenario == "rate_limited":
            raise LiveDataRateLimited("http 429")
        if self.scenario == "malformed":
            raise LiveDataUnavailable("malformed response")


def _candidate(place: GeoPlace) -> GeoCandidate:
    return GeoCandidate(
        osm_ref=place.osm_ref,
        name=place.name,
        display_name=place.display_name,
        region=place.region,
        country_code=place.country_code,
        lat=place.lat,
        lon=place.lon,
        kind="city" if place.kind == "city" else "village",
    )


class FakeGeocoder(_Fake):
    """``GeocodingProvider``: "liveton" and "tinyham" are found; nothing else is."""

    async def search(self, q: str) -> list[GeoCandidate]:
        self._raise_for_scenario()
        if self.scenario == "empty":
            return []
        text = q.casefold()
        return [_candidate(place) for key, place in _SEARCH_KEYS if key in text]

    async def lookup(self, osm_ref: str) -> GeoPlace | None:
        self._raise_for_scenario()
        if self.scenario == "empty":
            return None
        return _PLACES_BY_REF.get(osm_ref)


def _grid_point(bbox: BBox, slot: int, slots: int) -> tuple[float, float]:
    """The ``slot``-th cell centre of a square grid over the middle 80 % of ``bbox``."""
    side = max(1, math.ceil(math.sqrt(slots)))
    row, col = divmod(slot, side)
    lat = bbox.south + (bbox.north - bbox.south) * (0.1 + 0.8 * (row + 0.5) / side)
    lon = bbox.west + (bbox.east - bbox.west) * (0.1 + 0.8 * (col + 0.5) / side)
    return round(lat, 6), round(lon, 6)


def _label(value: str) -> str:
    return value.replace("_", " ").title()


def _elements(
    bbox: BBox, town: str, base_id: int, non_food: int, food: int, duplicates: int
) -> list[OsmElement]:
    kinds = [_NON_FOOD[i % len(_NON_FOOD)] for i in range(non_food)]
    kinds += [_FOOD[i % len(_FOOD)] for i in range(food)]
    elements: list[OsmElement] = []
    for i, (key, value) in enumerate(kinds):
        lat, lon = _grid_point(bbox, i, len(kinds))
        tags = {"name": f"{town} {_label(value)} {i + 1} (SAMPLE)", key: value}
        if i % 3 == 0:
            tags["wikidata"] = f"Q{base_id + i}"
        if i % 4 == 0:
            tags["wikipedia"] = f"en:{town} {_label(value)} {i + 1} (SAMPLE)"
        if i % 5 == 0:
            tags["website"] = f"https://example.org/{town.lower()}/{i + 1}"
        if i % 2 == 0:
            tags["addr:street"] = "Sample Road"
            tags["addr:housenumber"] = str(i + 1)
            tags["addr:city"] = f"{town} (SAMPLE)"
        if i % 6 == 0:
            tags["wheelchair"] = "yes"
        if value == "cafe":
            tags["diet:vegetarian"] = "yes"
        elements.append(OsmElement(_TYPES[i % 3], base_id + i, lat, lon, tags))
    # Near-copies of the first few places: same name and kind, fewer rich tags, a higher id.
    for j, original in enumerate(elements[:duplicates]):
        lat = min(original.lat + DUPLICATE_OFFSET_DEG, bbox.north)
        tags = {k: v for k, v in original.tags.items() if k not in ("wikidata", "wikipedia")}
        elements.append(OsmElement("n", base_id + 5000 + j, lat, original.lon, tags))
    return elements


def liveton_elements(bbox: BBox) -> list[OsmElement]:
    return _elements(bbox, "Liveton", 9_100_000, LIVETON_NON_FOOD, LIVETON_FOOD, LIVETON_DUPLICATES)


def tinyham_elements(bbox: BBox) -> list[OsmElement]:
    return _elements(bbox, "Tinyham", 9_200_000, TINYHAM_NON_FOOD, TINYHAM_FOOD, 0)


class FakePlaces(_Fake):
    """``PlacesProvider``: Liveton's many places, or Tinyham's few when the box holds Tinyham."""

    async def fetch(self, bbox: BBox) -> list[OsmElement]:
        self._raise_for_scenario()
        if self.scenario == "empty":
            return []
        if self.scenario == "small" or bbox.contains(TINYHAM.lat, TINYHAM.lon):
            return tinyham_elements(bbox)
        return liveton_elements(bbox)

    async def largest_city_near(self, lat: float, lon: float, radius_km: float) -> str | None:
        self._raise_for_scenario()
        if self.scenario == "empty":
            return None
        return BIGTOWN_NAME


_LIVETON_VOYAGE: Final[tuple[tuple[str, str], ...]] = (
    (
        "Introduction",
        "Liveton (SAMPLE) is an invented town used to test the live-data import. It has an old "
        "quarter of narrow lanes, a hill fort above the river and a large public garden. This "
        "text is synthetic sample content and describes no real place.",
    ),
    (
        "Understand",
        "The town grew around a river crossing and a weekly market. The old quarter keeps its "
        "carved wooden balconies and small courtyard temples, while the newer districts spread "
        "along the river road towards the hills.\n\nWinter is the most pleasant season for "
        "walking, and the monsoon turns the surrounding hills green.",
    ),
    (
        "See",
        "The hill fort gives wide views over the river and the old quarter. The town museum holds "
        "textiles, coins and folk paintings collected from the surrounding villages.\n\nThe "
        "public garden has shaded paths, a lily pond and an old stepwell near its north gate. "
        "Entry costs Rs 50 and the garden opens 9:00-17:00.",
    ),
    (
        "Do",
        "Walk the riverside promenade at sunset, when families gather along the steps and small "
        "boats cross to the far bank. The arts centre stages folk music and puppet shows on many "
        "evenings, and the weekly market fills the main square with stalls of spices and cloth.",
    ),
    (
        "Eat",
        "Small restaurants around the market square serve local thalis and sweets. Street stalls "
        "near the river sell fried snacks in the evening.",
    ),
)
_LIVETON_PEDIA: Final[tuple[tuple[str, str], ...]] = (
    (
        "Introduction",
        "Liveton (SAMPLE) is a fictional settlement created as test data for the travel planner. "
        "It stands on the bank of a river at the foot of a low range of hills, and its economy is "
        "said to rest on trade, crafts and small farms. Nothing in this sample article is real.",
    ),
    (
        "History",
        "According to the invented sample history, a fort was built on the hill above the river "
        "crossing, and the market town grew in its shadow. Merchants built courtyard houses in the "
        "old quarter, and temples and a stepwell were added over the following centuries.",
    ),
)
_TINYHAM_VOYAGE: Final[tuple[tuple[str, str], ...]] = (
    ("Introduction", "Tinyham (SAMPLE) is an invented village with a pond and a small temple."),
)


def _sections(
    source: Literal["wikivoyage", "wikipedia"],
    page_id: int,
    place: GeoPlace,
    parts: tuple[tuple[str, str], ...],
) -> list[WikiSection]:
    host = "en.wikivoyage.org" if source == "wikivoyage" else "en.wikipedia.org"
    slug = place.name.replace(" ", "_")
    return [
        WikiSection(
            source=source,
            page_id=page_id,
            revision_id=page_id * 10,
            page_title=place.name,
            page_url=f"https://{host}/wiki/{slug}",
            index=index,
            heading=heading,
            text=text,
            page_lat=place.lat,
            page_lon=place.lon,
        )
        for index, (heading, text) in enumerate(parts)
    ]


class FakeGuides(_Fake):
    """``GuideSourceProvider``: synthetic SAMPLE sections for Liveton, one short one for Tinyham."""

    async def fetch(self, name: str, lat: float, lon: float) -> list[WikiSection]:
        self._raise_for_scenario()
        if self.scenario == "empty":
            return []
        if self.scenario == "small" or "tinyham" in name.casefold():
            return _sections("wikivoyage", 9_000_002, TINYHAM, _TINYHAM_VOYAGE)
        return _sections("wikivoyage", 9_000_001, LIVETON, _LIVETON_VOYAGE) + _sections(
            "wikipedia", 9_000_011, LIVETON, _LIVETON_PEDIA
        )
