"""Live-data provider protocols, data shapes and errors (Amendment A2 §7.1; IMP-723).

Three protocols: ``GeocodingProvider`` (Nominatim), ``PlacesProvider`` (Overpass) and
``GuideSourceProvider`` (MediaWiki). Real adapters live in ``osm`` and ``wiki``, offline fakes in
``fake``; ``app.livedata.factory`` builds them. Every adapter raises only the three errors below,
with a message that is safe to log: never a response body, a query text or a user's input.

The Overpass query is built here, from the numeric bounding box and the fixed tag list only, so
the user's text can never reach Overpass QL (A2 §6.3, §11; TC-469). This module does no I/O.
"""

import math
from dataclasses import dataclass, field
from typing import Final, Literal, Protocol

SettlementKind = Literal["city", "town", "village", "municipality"]
SETTLEMENT_KINDS: Final[frozenset[str]] = frozenset({"city", "town", "village", "municipality"})
OsmType = Literal["n", "w", "r"]

# A2 §6.3: the only keys and values an Overpass places query asks for, in this order.
OVERPASS_TAGS: Final[tuple[tuple[str, tuple[str, ...]], ...]] = (
    (
        "tourism",
        ("attraction", "museum", "gallery", "viewpoint", "zoo", "aquarium", "theme_park"),
    ),
    (
        "historic",
        ("monument", "memorial", "castle", "fort", "ruins", "archaeological_site", "palace"),
    ),
    ("leisure", ("park", "garden", "nature_reserve")),
    ("natural", ("beach", "peak")),
    (
        "amenity",
        (
            "restaurant",
            "cafe",
            "fast_food",
            "food_court",
            "marketplace",
            "theatre",
            "arts_centre",
            "place_of_worship",
        ),
    ),
    ("shop", ("mall", "department_store")),
)
# A2 §6.3: [maxsize:] of the places query, 64 MiB.
OVERPASS_MAXSIZE_BYTES: Final = 67_108_864


class LiveDataError(Exception):
    """Base of the live-data errors; the message is safe to log."""


class LiveDataUnavailable(LiveDataError):  # noqa: N818  # names fixed by A2 §7.1
    """The service failed, answered with an error status or returned a malformed body."""


class LiveDataRateLimited(LiveDataError):  # noqa: N818
    """The service answered 429, or its circuit breaker is open."""


class LiveDataTimeout(LiveDataError):  # noqa: N818
    """No answer within the configured timeout."""


@dataclass(frozen=True)
class BBox:
    """A bounding box in degrees: south <= north and west <= east."""

    south: float
    west: float
    north: float
    east: float

    def __post_init__(self) -> None:
        values = (self.south, self.west, self.north, self.east)
        if not all(isinstance(v, int | float) and math.isfinite(v) for v in values):
            raise ValueError("bbox values must be finite numbers")
        if not (-90 <= self.south <= self.north <= 90):
            raise ValueError("bbox latitudes out of range")
        if not (-180 <= self.west <= self.east <= 180):
            raise ValueError("bbox longitudes out of range")

    def contains(self, lat: float, lon: float) -> bool:
        return self.south <= lat <= self.north and self.west <= lon <= self.east


@dataclass(frozen=True)
class GeoCandidate:
    """One Nominatim search result that is a settlement (A2 §5 `CityCandidate` source)."""

    osm_ref: str  # ^[NWR][0-9]{1,12}$
    name: str
    display_name: str
    region: str | None
    country_code: str  # ISO 3166-1 alpha-2, upper case
    lat: float
    lon: float
    kind: SettlementKind


@dataclass(frozen=True)
class GeoPlace:
    """A Nominatim lookup result: the settlement a live destination is built from (A2 §6.1)."""

    osm_ref: str
    name: str
    name_en: str | None
    display_name: str
    region: str | None
    country_code: str
    lat: float
    lon: float
    kind: str  # Nominatim `addresstype`; the service checks it is a settlement
    bbox: BBox


@dataclass(frozen=True)
class OsmElement:
    """One Overpass element with its tags; the coordinates are the node or the element centre."""

    osm_type: OsmType
    osm_id: int
    lat: float
    lon: float
    tags: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class WikiSection:
    """One `==` section of a Wikivoyage or Wikipedia page, as plain text (A2 §6.5)."""

    source: Literal["wikivoyage", "wikipedia"]
    page_id: int
    revision_id: int
    page_title: str
    page_url: str
    index: int
    heading: str
    text: str


class GeocodingProvider(Protocol):
    async def search(self, q: str) -> list[GeoCandidate]: ...

    async def lookup(self, osm_ref: str) -> GeoPlace | None: ...


class PlacesProvider(Protocol):
    async def fetch(self, bbox: BBox) -> list[OsmElement]: ...

    async def largest_city_near(self, lat: float, lon: float, radius_km: float) -> str | None: ...


class GuideSourceProvider(Protocol):
    async def fetch(self, name: str, lat: float, lon: float) -> list[WikiSection]: ...


def _number(value: float) -> str:
    """A coordinate as plain decimal text; anything but a finite number is refused."""
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise ValueError("coordinates must be finite numbers")
    return f"{float(value):.6f}"


def overpass_places_query(bbox: BBox, timeout_s: float) -> str:
    """The Overpass QL places query: numbers and the fixed tag list only (A2 §6.3)."""
    box = ",".join(_number(v) for v in (bbox.south, bbox.west, bbox.north, bbox.east))
    timeout = max(1, math.ceil(_seconds(timeout_s)))
    lines = [f"[out:json][timeout:{timeout}][maxsize:{OVERPASS_MAXSIZE_BYTES}];", "("]
    for key, values in OVERPASS_TAGS:
        lines.append(f'  nwr["name"]["{key}"~"^({"|".join(values)})$"]({box});')
    lines += [");", "out center tags;"]
    return "\n".join(lines)


def overpass_city_query(lat: float, lon: float, radius_km: float, timeout_s: float) -> str:
    """The nearby-city query: `place=city` nodes around a point (A2 §6.4), numbers only."""
    radius_m = round(_seconds(radius_km) * 1000)
    timeout = max(1, math.ceil(_seconds(timeout_s)))
    return (
        f"[out:json][timeout:{timeout}];\n"
        f'node["place"="city"]["name"](around:{radius_m},{_number(lat)},{_number(lon)});\n'
        "out tags;"
    )


def _seconds(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise ValueError("expected a finite number")
    if value <= 0:
        raise ValueError("expected a positive number")
    return float(value)
