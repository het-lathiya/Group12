"""OSM element normalisation, dedupe, cap and minimum-places gate (Amendment A2 §6.3, §6.4; IMP-724).

``normalise(elements, destination_external_ref=..., bbox=...)`` maps Overpass elements to place
records of the existing vocabulary, merges duplicates and keeps at most ``LIVE_MAX_PLACES`` of
them. ``evaluate_gate`` decides whether a live destination has enough places, and
``choose_nearby_city`` names the larger city the "not enough data" message suggests.

Pure: no I/O, no settings, no database. The output depends only on the input set, never on its
order. Prices and opening hours are always unknown and OSM free text is never stored.
"""

import math
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final, Literal

from app.livedata.providers.base import BBox, OsmElement
from app.places.vocabulary import Category, SourceLabel, Tag, VerificationStatus

LIVE_MAX_PLACES: Final = 300
FOOD_SHARE: Final = 0.35
MAX_FOOD_PLACES: Final = math.floor(FOOD_SHARE * LIVE_MAX_PLACES)  # 105
DEDUPE_RADIUS_M: Final = 75.0
MIN_FOOD_PLACES: Final = 6
MIN_NON_FOOD_PLACES: Final = 12
DEFAULT_MIN_USABLE_PLACES: Final = 40

NAME_MAX_CHARS: Final = 160  # places.name CHECK (migration 0002)
ADDRESS_MAX_CHARS: Final = 150
WEBSITE_MAX_CHARS: Final = 2048
EARTH_RADIUS_M: Final = 6_371_008.8

_OSM_TYPE_ORDER: Final[Mapping[str, int]] = {"n": 0, "w": 1, "r": 2}
_HISTORIC_VALUES: Final[frozenset[str]] = frozenset(
    {"monument", "memorial", "castle", "fort", "ruins", "archaeological_site", "palace"}
)
_NATURE_TAGS: Final[Mapping[tuple[str, str], tuple[Tag, ...]]] = {
    ("leisure", "park"): (Tag.OUTDOOR, Tag.WALKING),
    ("leisure", "garden"): (Tag.OUTDOOR, Tag.GARDEN),
    ("leisure", "nature_reserve"): (Tag.OUTDOOR, Tag.WALKING),
    ("natural", "beach"): (Tag.OUTDOOR, Tag.WATER),
    ("natural", "peak"): (Tag.OUTDOOR, Tag.VIEWS),
}
_ENTERTAINMENT_TAGS: Final[Mapping[str, tuple[Tag, ...]]] = {
    "theatre": (Tag.THEATRE, Tag.MUSIC, Tag.EVENING),
    "arts_centre": (Tag.ART, Tag.MUSIC, Tag.EVENING),
}
_FOOD_AMENITIES: Final[frozenset[str]] = frozenset(
    {"restaurant", "fast_food", "food_court", "cafe"}
)
_ADDRESS_LOCALITY_KEYS: Final[tuple[str, ...]] = ("addr:suburb", "addr:city")


@dataclass(frozen=True)
class Mapped:
    """The category, tags and default duration of one mapping-table row."""

    category: Category
    tags: tuple[Tag, ...]
    typical_duration_min: int


@dataclass(frozen=True)
class LivePlace:
    """One normalised live place, with the field names of the ``places`` table."""

    external_ref: str
    osm_type: str
    osm_id: int
    name: str
    category: Category
    tags: tuple[Tag, ...]
    typical_duration_min: int
    lat: float
    lon: float
    address: str | None
    website_url: str | None
    step_free: bool | None
    indoor: bool | None
    richness: int
    preference: int
    child_friendly: None = None
    booking_url: None = None
    description: None = None
    price_min: None = None
    price_max: None = None
    price_currency: None = None
    price_label: SourceLabel = SourceLabel.UNAVAILABLE
    hours_label: SourceLabel = SourceLabel.UNAVAILABLE
    hours_checked_on: None = None
    verification_status: VerificationStatus = VerificationStatus.IMPORTED_OSM


@dataclass(frozen=True)
class NormaliseResult:
    places: tuple[LivePlace, ...]
    found: int
    dropped_unmapped: int
    dropped_outside: int
    dropped_invalid: int
    duplicates_merged: int
    capped: int


GateStatus = Literal["passed", "insufficient_data"]


@dataclass(frozen=True)
class GateResult:
    status: GateStatus
    usable: int
    food: int
    non_food: int
    min_usable: int

    @property
    def passed(self) -> bool:
        return self.status == "passed"


def map_tags(tags: Mapping[str, str]) -> Mapped | None:
    """The first matching row of the A2 §6.3 table, or None for an unmapped element."""
    tourism = tags.get("tourism")
    historic = tags.get("historic")
    amenity = tags.get("amenity")
    if tourism in ("museum", "gallery"):
        first = Tag.HISTORY if tourism == "museum" else Tag.ART
        return Mapped(Category.MUSEUM, (first, Tag.INDOOR), 90)
    if historic in _HISTORIC_VALUES or tourism in ("attraction", "viewpoint"):
        sight_tags: tuple[Tag, ...] = (Tag.HISTORY, Tag.ARCHITECTURE)
        if tourism == "viewpoint":
            sight_tags = (*sight_tags, Tag.VIEWS)
        return Mapped(Category.SIGHT, sight_tags, 60)
    for key in ("leisure", "natural"):
        nature_tags = _NATURE_TAGS.get((key, tags.get(key, "")))
        if nature_tags is not None:
            return Mapped(Category.NATURE, nature_tags, 75)
    if amenity in _FOOD_AMENITIES:
        food_tags: tuple[Tag, ...] = (Tag.LUNCH, Tag.DINNER)
        if amenity == "cafe":
            food_tags = (*food_tags, Tag.CAFE, Tag.TEA)
        if tags.get("diet:vegetarian") in ("yes", "only"):
            food_tags = (*food_tags, Tag.VEGETARIAN)
        return Mapped(Category.FOOD, food_tags, 60)
    if amenity == "marketplace" or tags.get("shop") in ("mall", "department_store"):
        return Mapped(Category.SHOPPING, (Tag.MARKET, Tag.LOCAL), 60)
    if amenity is not None and amenity in _ENTERTAINMENT_TAGS:
        return Mapped(Category.ENTERTAINMENT, _ENTERTAINMENT_TAGS[amenity], 120)
    if amenity == "place_of_worship":
        return Mapped(Category.RELIGIOUS, (Tag.ARCHITECTURE, Tag.QUIET), 45)
    if tourism in ("zoo", "aquarium", "theme_park"):
        return Mapped(Category.ACTIVITY, (Tag.FAMILY, Tag.WILDLIFE), 120)
    return None


def build_address(tags: Mapping[str, str]) -> str | None:
    """``housenumber street, suburb, city, postcode`` from ``addr:*`` tags, at most 150 chars."""
    street = " ".join(
        part
        for part in (_clean(tags.get("addr:housenumber")), _clean(tags.get("addr:street")))
        if part
    )
    parts = [street] if street else []
    for key in _ADDRESS_LOCALITY_KEYS:
        value = _clean(tags.get(key))
        if value and value not in parts:
            parts.append(value)
    postcode = _clean(tags.get("addr:postcode"))
    if postcode:
        parts.append(postcode)
    if not parts:
        full = _clean(tags.get("addr:full"))
        if full:
            parts.append(full)
    if not parts:
        return None
    return ", ".join(parts)[:ADDRESS_MAX_CHARS].rstrip(" ,") or None


def website_url(tags: Mapping[str, str]) -> str | None:
    """The first ``website`` or ``contact:website`` value that is an ``https://`` URL."""
    for key in ("website", "contact:website"):
        value = (tags.get(key) or "").strip()
        if (
            value[:8].lower() == "https://"
            and len(value) > 8
            and len(value) <= WEBSITE_MAX_CHARS
            and not any(ch.isspace() for ch in value)
        ):
            return value
    return None


def step_free(tags: Mapping[str, str]) -> bool | None:
    value = tags.get("wheelchair")
    if value == "yes":
        return True
    if value == "no":
        return False
    return None


def richness(tags: Mapping[str, str]) -> int:
    """Cap ranking score: wikidata +3, wikipedia +2, website +1, any ``addr:*`` +1."""
    score = 0
    if tags.get("wikidata"):
        score += 3
    if tags.get("wikipedia"):
        score += 2
    if tags.get("website") or tags.get("contact:website"):
        score += 1
    if any(key.startswith("addr:") and value for key, value in tags.items()):
        score += 1
    return score


def dedupe_preference(tags: Mapping[str, str]) -> int:
    """How many of wikidata, wikipedia and website a place has (the dedupe keep rule)."""
    return sum(
        1
        for present in (
            tags.get("wikidata"),
            tags.get("wikipedia"),
            tags.get("website") or tags.get("contact:website"),
        )
        if present
    )


def name_key(name: str) -> str:
    """Case folded, accents removed and whitespace collapsed: the dedupe name comparison."""
    decomposed = unicodedata.normalize("NFKD", name)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(stripped.casefold().split())


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))


def _clean(value: str | None) -> str:
    return " ".join((value or "").split())


def _osm_key(place: LivePlace) -> tuple[int, int]:
    return (place.osm_id, _OSM_TYPE_ORDER[place.osm_type])


def _element_order(
    element: OsmElement,
) -> tuple[int, int, float, float, tuple[tuple[str, str], ...]]:
    return (
        _OSM_TYPE_ORDER.get(element.osm_type, 3),
        element.osm_id,
        element.lat,
        element.lon,
        tuple(sorted(element.tags.items())),
    )


@dataclass
class _Counts:
    unmapped: int = 0
    outside: int = 0
    invalid: int = 0


def _to_place(
    element: OsmElement, destination_external_ref: str, bbox: BBox, counts: _Counts
) -> LivePlace | None:
    tags = element.tags
    if (
        element.osm_type not in _OSM_TYPE_ORDER
        or isinstance(element.osm_id, bool)
        or not isinstance(element.osm_id, int)
        or element.osm_id <= 0
    ):
        counts.invalid += 1
        return None
    mapped = map_tags(tags)
    if mapped is None:
        counts.unmapped += 1
        return None
    name = (tags.get("name") or "").strip()
    if not 1 <= len(name) <= NAME_MAX_CHARS:
        counts.invalid += 1
        return None
    lat, lon = element.lat, element.lon
    if not (math.isfinite(lat) and math.isfinite(lon)):
        counts.invalid += 1
        return None
    if not bbox.contains(lat, lon):
        counts.outside += 1
        return None
    indoor: bool | None = None
    if mapped.category is Category.MUSEUM:
        indoor = True
    elif mapped.category is Category.NATURE:
        indoor = False
    return LivePlace(
        external_ref=f"{destination_external_ref}:{element.osm_type}{element.osm_id}",
        osm_type=element.osm_type,
        osm_id=element.osm_id,
        name=name,
        category=mapped.category,
        tags=mapped.tags,
        typical_duration_min=mapped.typical_duration_min,
        lat=round(lat, 6),
        lon=round(lon, 6),
        address=build_address(tags),
        website_url=website_url(tags),
        step_free=step_free(tags),
        indoor=indoor,
        richness=richness(tags),
        preference=dedupe_preference(tags),
    )


def dedupe(places: Iterable[LivePlace]) -> tuple[list[LivePlace], int]:
    """Merge same-category places with equal name keys within 75 m; returns (kept, merged)."""
    ordered = sorted(places, key=lambda p: (-p.preference, *_osm_key(p)))
    kept: list[LivePlace] = []
    by_group: dict[tuple[Category, str], list[LivePlace]] = {}
    merged = 0
    for place in ordered:
        group = by_group.setdefault((place.category, name_key(place.name)), [])
        if any(
            haversine_m(place.lat, place.lon, other.lat, other.lon) <= DEDUPE_RADIUS_M
            for other in group
        ):
            merged += 1
            continue
        group.append(place)
        kept.append(place)
    return kept, merged


def cap(
    places: Iterable[LivePlace],
    max_places: int = LIVE_MAX_PLACES,
    max_food: int = MAX_FOOD_PLACES,
) -> list[LivePlace]:
    """At most ``max_places`` by richness then OSM id, with at most ``max_food`` food places."""
    ranked = sorted(places, key=lambda p: (-p.richness, *_osm_key(p)))
    kept: list[LivePlace] = []
    food = 0
    for place in ranked:
        if len(kept) >= max_places:
            break
        if place.category is Category.FOOD:
            if food >= max_food:
                continue
            food += 1
        kept.append(place)
    return kept


def normalise(
    elements: Iterable[OsmElement], *, destination_external_ref: str, bbox: BBox
) -> NormaliseResult:
    """Map, dedupe and cap Overpass elements; the result does not depend on the input order."""
    unique: dict[tuple[str, int], OsmElement] = {}
    found = 0
    for element in sorted(elements, key=_element_order):
        found += 1
        unique.setdefault((element.osm_type, element.osm_id), element)
    counts = _Counts()
    candidates = [
        place
        for element in unique.values()
        if (place := _to_place(element, destination_external_ref, bbox, counts)) is not None
    ]
    deduped, merged = dedupe(candidates)
    merged += found - len(unique)
    capped = cap(deduped)
    return NormaliseResult(
        places=tuple(capped),
        found=found,
        dropped_unmapped=counts.unmapped,
        dropped_outside=counts.outside,
        dropped_invalid=counts.invalid,
        duplicates_merged=merged,
        capped=len(deduped) - len(capped),
    )


def evaluate_gate(
    places: Sequence[LivePlace], *, min_usable: int = DEFAULT_MIN_USABLE_PLACES
) -> GateResult:
    """A2 §6.4: at least ``min_usable`` places, of which 6 food and 12 non-food."""
    food = sum(1 for place in places if place.category is Category.FOOD)
    usable = len(places)
    non_food = usable - food
    ok = usable >= min_usable and food >= MIN_FOOD_PLACES and non_food >= MIN_NON_FOOD_PLACES
    return GateResult(
        status="passed" if ok else "insufficient_data",
        usable=usable,
        food=food,
        non_food=non_food,
        min_usable=min_usable,
    )


def choose_nearby_city(
    settlement_name: str, nearby_city: str | None, capital: str | None
) -> str | None:
    """The nearby city, else the country's capital; never the settlement itself, else None."""
    own = name_key(settlement_name)
    for candidate in (nearby_city, capital):
        cleaned = _clean(candidate)
        if cleaned and name_key(cleaned) != own:
            return cleaned
    return None
