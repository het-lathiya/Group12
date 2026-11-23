"""TC-465, TC-466, TC-467: live normaliser, dedupe, cap and gate (Amendment A2 §6.3, §6.4; IMP-724).

Inputs are SAMPLE-style OSM elements built inline; no network and no database.
"""

import itertools
import random

import pytest

from app.livedata.normalise import (
    LIVE_MAX_PLACES,
    MAX_FOOD_PLACES,
    LivePlace,
    choose_nearby_city,
    evaluate_gate,
    map_tags,
    normalise,
)
from app.livedata.providers.base import OVERPASS_TAGS, BBox, OsmElement, OsmType
from app.places.vocabulary import Category, SourceLabel, Tag, VerificationStatus

BBOX = BBox(south=10.0, west=20.0, north=10.2, east=20.2)
REF = "R1234567"
LAT, LON = 10.1, 20.1
# About 0.00045 degrees of latitude is 50 m; 0.0009 is 100 m.
NEAR = 0.00045
FAR = 0.0009
OSM_TYPES: list[OsmType] = ["n", "w", "r"]


def el(
    osm_id: int,
    tags: dict[str, str],
    *,
    osm_type: OsmType = "n",
    lat: float = LAT,
    lon: float = LON,
    name: str | None = "Sample Place",
) -> OsmElement:
    full = dict(tags)
    if name is not None:
        full.setdefault("name", name)
    return OsmElement(osm_type=osm_type, osm_id=osm_id, lat=lat, lon=lon, tags=full)


def run(elements: list[OsmElement]) -> tuple[LivePlace, ...]:
    return normalise(elements, destination_external_ref=REF, bbox=BBOX).places


def one(tags: dict[str, str], *, name: str | None = "Sample Place") -> LivePlace:
    places = run([el(1, tags, name=name)])
    assert len(places) == 1
    return places[0]


# ---------------------------------------------------------------- TC-465 mapping table


@pytest.mark.parametrize(
    ("tags", "category", "expected_tags", "duration"),
    [
        ({"tourism": "museum"}, Category.MUSEUM, (Tag.HISTORY, Tag.INDOOR), 90),
        ({"tourism": "gallery"}, Category.MUSEUM, (Tag.ART, Tag.INDOOR), 90),
        ({"historic": "monument"}, Category.SIGHT, (Tag.HISTORY, Tag.ARCHITECTURE), 60),
        ({"historic": "palace"}, Category.SIGHT, (Tag.HISTORY, Tag.ARCHITECTURE), 60),
        ({"tourism": "attraction"}, Category.SIGHT, (Tag.HISTORY, Tag.ARCHITECTURE), 60),
        (
            {"tourism": "viewpoint"},
            Category.SIGHT,
            (Tag.HISTORY, Tag.ARCHITECTURE, Tag.VIEWS),
            60,
        ),
        ({"leisure": "park"}, Category.NATURE, (Tag.OUTDOOR, Tag.WALKING), 75),
        ({"leisure": "garden"}, Category.NATURE, (Tag.OUTDOOR, Tag.GARDEN), 75),
        ({"leisure": "nature_reserve"}, Category.NATURE, (Tag.OUTDOOR, Tag.WALKING), 75),
        ({"natural": "beach"}, Category.NATURE, (Tag.OUTDOOR, Tag.WATER), 75),
        ({"natural": "peak"}, Category.NATURE, (Tag.OUTDOOR, Tag.VIEWS), 75),
        ({"amenity": "restaurant"}, Category.FOOD, (Tag.LUNCH, Tag.DINNER), 60),
        ({"amenity": "fast_food"}, Category.FOOD, (Tag.LUNCH, Tag.DINNER), 60),
        ({"amenity": "food_court"}, Category.FOOD, (Tag.LUNCH, Tag.DINNER), 60),
        (
            {"amenity": "cafe"},
            Category.FOOD,
            (Tag.LUNCH, Tag.DINNER, Tag.CAFE, Tag.TEA),
            60,
        ),
        (
            {"amenity": "restaurant", "diet:vegetarian": "yes"},
            Category.FOOD,
            (Tag.LUNCH, Tag.DINNER, Tag.VEGETARIAN),
            60,
        ),
        (
            {"amenity": "cafe", "diet:vegetarian": "only"},
            Category.FOOD,
            (Tag.LUNCH, Tag.DINNER, Tag.CAFE, Tag.TEA, Tag.VEGETARIAN),
            60,
        ),
        (
            {"amenity": "restaurant", "diet:vegetarian": "limited"},
            Category.FOOD,
            (Tag.LUNCH, Tag.DINNER),
            60,
        ),
        ({"amenity": "marketplace"}, Category.SHOPPING, (Tag.MARKET, Tag.LOCAL), 60),
        ({"shop": "mall"}, Category.SHOPPING, (Tag.MARKET, Tag.LOCAL), 60),
        ({"shop": "department_store"}, Category.SHOPPING, (Tag.MARKET, Tag.LOCAL), 60),
        (
            {"amenity": "theatre"},
            Category.ENTERTAINMENT,
            (Tag.THEATRE, Tag.MUSIC, Tag.EVENING),
            120,
        ),
        (
            {"amenity": "arts_centre"},
            Category.ENTERTAINMENT,
            (Tag.ART, Tag.MUSIC, Tag.EVENING),
            120,
        ),
        (
            {"amenity": "place_of_worship"},
            Category.RELIGIOUS,
            (Tag.ARCHITECTURE, Tag.QUIET),
            45,
        ),
        ({"tourism": "zoo"}, Category.ACTIVITY, (Tag.FAMILY, Tag.WILDLIFE), 120),
        ({"tourism": "aquarium"}, Category.ACTIVITY, (Tag.FAMILY, Tag.WILDLIFE), 120),
        ({"tourism": "theme_park"}, Category.ACTIVITY, (Tag.FAMILY, Tag.WILDLIFE), 120),
    ],
)
def test_tc465_mapping_rows(
    tags: dict[str, str], category: Category, expected_tags: tuple[Tag, ...], duration: int
) -> None:
    place = one(tags)
    assert place.category is category
    assert place.tags == expected_tags
    assert place.typical_duration_min == duration


@pytest.mark.parametrize(
    ("tags", "category"),
    [
        ({"tourism": "museum", "historic": "castle"}, Category.MUSEUM),
        ({"historic": "fort", "leisure": "park"}, Category.SIGHT),
        ({"tourism": "attraction", "amenity": "restaurant"}, Category.SIGHT),
        ({"leisure": "garden", "amenity": "cafe"}, Category.NATURE),
        ({"amenity": "restaurant", "shop": "mall"}, Category.FOOD),
        ({"shop": "mall", "tourism": "zoo"}, Category.SHOPPING),
        ({"amenity": "place_of_worship", "tourism": "zoo"}, Category.RELIGIOUS),
        ({"tourism": "viewpoint", "historic": "ruins"}, Category.SIGHT),
    ],
)
def test_tc465_first_row_wins(tags: dict[str, str], category: Category) -> None:
    assert one(tags).category is category


def test_tc465_viewpoint_with_historic_keeps_views() -> None:
    assert Tag.VIEWS in one({"tourism": "viewpoint", "historic": "ruins"}).tags


@pytest.mark.parametrize(
    "tags",
    [
        {"tourism": "hotel"},
        {"tourism": "guest_house"},
        {"amenity": "bank"},
        {"historic": "wayside_cross"},
        {"leisure": "pitch"},
        {"shop": "bakery"},
        {},
    ],
)
def test_tc465_unmapped_dropped_and_counted(tags: dict[str, str]) -> None:
    result = normalise(
        [el(1, tags), el(2, {"tourism": "museum"}, name="Other")],
        destination_external_ref=REF,
        bbox=BBOX,
    )
    assert result.dropped_unmapped == 1
    assert result.found == 2
    assert [p.osm_id for p in result.places] == [2]


def _all_fixed_tag_combinations() -> list[dict[str, str]]:
    keys = [key for key, _ in OVERPASS_TAGS]
    choices = [[None, *values] for _, values in OVERPASS_TAGS]
    combos = []
    for picked in itertools.product(*choices):
        combos.append({k: v for k, v in zip(keys, picked, strict=True) if v is not None})
    return combos


def test_tc465_stay_never_and_only_vocabulary_values() -> None:
    combos = _all_fixed_tag_combinations()
    assert len(combos) > 1000
    for tags in combos:
        for diet in ({}, {"diet:vegetarian": "yes"}):
            mapped = map_tags({**tags, **diet})
            if not tags:
                assert mapped is None
                continue
            assert mapped is not None, tags
            assert mapped.category is not Category.STAY
            assert Category(mapped.category.value) is mapped.category
            for tag in mapped.tags:
                assert Tag(tag.value) is tag
            assert 15 <= mapped.typical_duration_min <= 480
            assert len(set(mapped.tags)) == len(mapped.tags)


# ---------------------------------------------------------------- TC-465 field rules


def test_tc465_price_hours_description_always_unknown() -> None:
    place = one(
        {
            "tourism": "museum",
            "fee": "yes",
            "charge": "100 INR",
            "opening_hours": "Mo-Su 09:00-17:00",
            "description": "A free text description",
            "wikidata": "Q1",
        }
    )
    assert place.price_min is None
    assert place.price_max is None
    assert place.price_currency is None
    assert place.price_label is SourceLabel.UNAVAILABLE
    assert place.hours_label is SourceLabel.UNAVAILABLE
    assert place.hours_checked_on is None
    assert place.description is None
    assert place.booking_url is None
    assert place.child_friendly is None
    assert place.verification_status is VerificationStatus.IMPORTED_OSM


def test_tc465_external_ref_and_name() -> None:
    result = run([el(987, {"tourism": "museum"}, osm_type="w", name="  Sampleton Museum  ")])
    assert result[0].external_ref == "R1234567:w987"
    assert result[0].name == "Sampleton Museum"


@pytest.mark.parametrize("name", [None, "", "   ", "x" * 161])
def test_tc465_bad_name_dropped_and_counted(name: str | None) -> None:
    result = normalise(
        [el(1, {"tourism": "museum"}, name=name)], destination_external_ref=REF, bbox=BBOX
    )
    assert result.places == ()
    assert result.dropped_invalid == 1


def test_tc465_name_at_limit_kept() -> None:
    assert one({"tourism": "museum"}, name="x" * 160).name == "x" * 160


@pytest.mark.parametrize(
    ("tags", "expected"),
    [
        ({"website": "https://sample.example/"}, "https://sample.example/"),
        ({"website": "http://sample.example/"}, None),
        ({"website": "sample.example"}, None),
        ({"website": "ftp://sample.example"}, None),
        ({"website": "https://"}, None),
        ({"website": "https://bad host.example"}, None),
        ({"contact:website": "https://contact.example/"}, "https://contact.example/"),
        (
            {"website": "http://sample.example/", "contact:website": "https://c.example/"},
            "https://c.example/",
        ),
        ({}, None),
    ],
)
def test_tc465_only_https_websites(tags: dict[str, str], expected: str | None) -> None:
    assert one({"tourism": "museum", **tags}).website_url == expected


def test_tc465_address_built_and_cut() -> None:
    place = one(
        {
            "tourism": "museum",
            "addr:housenumber": "12",
            "addr:street": "Sample Street",
            "addr:suburb": "Old Town",
            "addr:city": "Sampleton",
            "addr:postcode": "000001",
        }
    )
    assert place.address == "12 Sample Street, Old Town, Sampleton, 000001"
    long_place = one({"tourism": "museum", "addr:street": "S" * 400, "addr:city": "Sampleton"})
    assert long_place.address is not None
    assert len(long_place.address) <= 150
    assert one({"tourism": "museum"}).address is None


@pytest.mark.parametrize(
    ("value", "expected"), [("yes", True), ("no", False), ("limited", None), (None, None)]
)
def test_tc465_wheelchair(value: str | None, expected: bool | None) -> None:
    tags = {"tourism": "museum"}
    if value is not None:
        tags["wheelchair"] = value
    assert one(tags).step_free is expected


def test_tc465_indoor_flag() -> None:
    assert one({"tourism": "museum"}).indoor is True
    assert one({"leisure": "park"}).indoor is False
    assert one({"amenity": "restaurant"}).indoor is None


@pytest.mark.parametrize(("lat", "lon"), [(9.99, LON), (10.21, LON), (LAT, 19.9), (LAT, 20.3)])
def test_tc465_outside_bbox_dropped_and_counted(lat: float, lon: float) -> None:
    result = normalise(
        [el(1, {"tourism": "museum"}, lat=lat, lon=lon)], destination_external_ref=REF, bbox=BBOX
    )
    assert result.places == ()
    assert result.dropped_outside == 1


# ---------------------------------------------------------------- TC-466 dedupe


def test_tc466_same_name_within_75m_merged_keeps_richer() -> None:
    result = normalise(
        [
            el(5, {"amenity": "restaurant"}, name="Sample Diner"),
            el(9, {"amenity": "restaurant", "wikidata": "Q9"}, name="Sample Diner", lat=LAT + NEAR),
        ],
        destination_external_ref=REF,
        bbox=BBOX,
    )
    assert [p.osm_id for p in result.places] == [9]
    assert result.duplicates_merged == 1


def test_tc466_tie_keeps_lower_osm_id() -> None:
    places = run(
        [
            el(7, {"amenity": "restaurant"}, name="Sample Diner"),
            el(3, {"amenity": "restaurant"}, name="Sample Diner", lat=LAT + NEAR),
        ]
    )
    assert [p.osm_id for p in places] == [3]


def test_tc466_beyond_75m_not_merged() -> None:
    places = run(
        [
            el(1, {"amenity": "restaurant"}, name="Sample Diner"),
            el(2, {"amenity": "restaurant"}, name="Sample Diner", lat=LAT + FAR),
        ]
    )
    assert len(places) == 2


def test_tc466_different_category_not_merged() -> None:
    places = run(
        [
            el(1, {"amenity": "restaurant"}, name="Sample Hall"),
            el(2, {"amenity": "theatre"}, name="Sample Hall"),
        ]
    )
    assert len(places) == 2


def test_tc466_accent_case_whitespace_variants_merged() -> None:
    result = normalise(
        [
            el(1, {"tourism": "museum"}, name="Musée  Sample"),
            el(2, {"tourism": "museum"}, name="musee sample", lat=LAT + NEAR / 2),
            el(3, {"tourism": "museum"}, name="MUSÉE\tSAMPLE ", lon=LON + NEAR / 2),
        ],
        destination_external_ref=REF,
        bbox=BBOX,
    )
    assert [p.osm_id for p in result.places] == [1]
    assert result.duplicates_merged == 2


def _sample_elements(count: int, seed: int) -> list[OsmElement]:
    rng = random.Random(seed)  # noqa: S311  # seeded test data, not security
    kinds = [
        {"tourism": "museum"},
        {"historic": "monument"},
        {"leisure": "park"},
        {"amenity": "restaurant"},
        {"amenity": "cafe"},
        {"shop": "mall"},
        {"amenity": "place_of_worship"},
    ]
    elements = []
    for i in range(1, count + 1):
        tags = dict(rng.choice(kinds))
        for key in ("wikidata", "wikipedia", "website", "addr:street"):
            if rng.random() < 0.3:
                tags[key] = "https://s.example" if key == "website" else "Sample"
        elements.append(
            el(
                i,
                tags,
                osm_type=rng.choice(OSM_TYPES),
                name=f"Sample {rng.randint(1, count // 3)}",
                lat=10.1 + rng.uniform(-0.001, 0.001),
                lon=20.1 + rng.uniform(-0.001, 0.001),
            )
        )
    return elements


def test_tc466_deterministic_under_shuffle() -> None:
    elements = _sample_elements(400, seed=7)
    baseline = normalise(elements, destination_external_ref=REF, bbox=BBOX)
    assert baseline.duplicates_merged > 0
    for seed in range(5):
        shuffled = list(elements)
        random.Random(seed).shuffle(shuffled)  # noqa: S311  # seeded test order
        assert normalise(shuffled, destination_external_ref=REF, bbox=BBOX) == baseline


def test_tc466_repeated_element_counted_once() -> None:
    element = el(1, {"tourism": "museum"})
    result = normalise([element, element], destination_external_ref=REF, bbox=BBOX)
    assert len(result.places) == 1
    assert result.found == 2


# ---------------------------------------------------------------- TC-466 cap


def _spread(i: int) -> tuple[float, float]:
    # Distinct names make dedupe a no-op; spread the points inside the bbox.
    return 10.0 + (i % 100) * 0.001 + 0.01, 20.0 + (i // 100) * 0.001 + 0.01


def test_tc466_cap_300_by_richness_with_food_share() -> None:
    elements = []
    for i in range(1, 251):  # 250 food places, half with wikidata
        lat, lon = _spread(i)
        tags = {"amenity": "restaurant"}
        if i % 2 == 0:
            tags["wikidata"] = "Q"
        elements.append(el(i, tags, name=f"Sample Food {i}", lat=lat, lon=lon))
    for i in range(251, 551):  # 300 non-food places
        lat, lon = _spread(i)
        tags = {"tourism": "museum"}
        if i <= 300:
            tags.update({"wikidata": "Q", "wikipedia": "en:S", "website": "https://s.example"})
        elements.append(el(i, tags, name=f"Sample Sight {i}", lat=lat, lon=lon))
    result = normalise(elements, destination_external_ref=REF, bbox=BBOX)
    places = result.places
    assert len(places) == LIVE_MAX_PLACES
    assert result.capped == 550 - LIVE_MAX_PLACES
    food = [p for p in places if p.category is Category.FOOD]
    assert len(food) == MAX_FOOD_PLACES == 105
    # The richest food places win: all 125 with wikidata exist; the 105 lowest ids among them.
    assert all(p.richness == 3 for p in food)
    assert sorted(p.osm_id for p in food) == list(range(2, 2 + 2 * 105, 2))
    # All 50 richest non-food places are kept; the rest are the lowest ids.
    non_food_ids = sorted(p.osm_id for p in places if p.category is not Category.FOOD)
    assert non_food_ids == list(range(251, 251 + 195))
    shuffled = list(elements)
    random.Random(3).shuffle(shuffled)  # noqa: S311  # seeded test order
    assert normalise(shuffled, destination_external_ref=REF, bbox=BBOX) == result


def test_tc466_richness_scores() -> None:
    assert one({"tourism": "museum"}).richness == 0
    assert one({"tourism": "museum", "wikidata": "Q"}).richness == 3
    assert one({"tourism": "museum", "wikipedia": "en:S"}).richness == 2
    assert one({"tourism": "museum", "website": "http://s.example"}).richness == 1
    assert one({"tourism": "museum", "addr:city": "Sampleton"}).richness == 1
    full = {
        "tourism": "museum",
        "wikidata": "Q",
        "wikipedia": "en:S",
        "website": "https://s.example",
        "addr:street": "Sample",
    }
    assert one(full).richness == 7


# ---------------------------------------------------------------- TC-467 gate


def _places(food: int, non_food: int) -> list[LivePlace]:
    elements = []
    for i in range(1, food + non_food + 1):
        lat, lon = _spread(i)
        tags = {"amenity": "restaurant"} if i <= food else {"tourism": "museum"}
        elements.append(el(i, tags, name=f"Sample {i}", lat=lat, lon=lon))
    return list(run(elements))


@pytest.mark.parametrize(
    ("food", "non_food", "status"),
    [
        (6, 34, "passed"),
        (28, 12, "passed"),
        (6, 33, "insufficient_data"),  # 39 usable
        (5, 35, "insufficient_data"),  # food below 6
        (29, 11, "insufficient_data"),  # non-food below 12
        (0, 0, "insufficient_data"),
        (20, 30, "passed"),
    ],
)
def test_tc467_gate_thresholds(food: int, non_food: int, status: str) -> None:
    gate = evaluate_gate(_places(food, non_food))
    assert gate.status == status
    assert gate.passed is (status == "passed")
    assert (gate.food, gate.non_food, gate.usable) == (food, non_food, food + non_food)
    assert gate.min_usable == 40


def test_tc467_min_usable_parameter() -> None:
    places = _places(6, 14)
    assert evaluate_gate(places, min_usable=20).passed
    assert not evaluate_gate(places, min_usable=21).passed


@pytest.mark.parametrize(
    ("settlement", "nearby", "capital", "expected"),
    [
        ("Sampleville", "Sampleton", "Capital Sample", "Sampleton"),
        ("Sampleville", None, "Capital Sample", "Capital Sample"),
        ("Sampleville", "", "Capital Sample", "Capital Sample"),
        ("Sampleville", "  ", "Capital Sample", "Capital Sample"),
        ("Sampleville", "SAMPLEVILLE", "Capital Sample", "Capital Sample"),
        ("Sámpleville", "sampleville ", "Capital Sample", "Capital Sample"),
        ("Capital Sample", None, "Capital Sample", None),
        ("Capital Sample", "capital  sample", "Capital  Sample", None),
        ("Sampleville", None, None, None),
    ],
)
def test_tc467_nearby_city_never_the_settlement(
    settlement: str, nearby: str | None, capital: str | None, expected: str | None
) -> None:
    chosen = choose_nearby_city(settlement, nearby, capital)
    assert chosen == expected
    if chosen is not None:
        assert chosen.casefold() != settlement.casefold()
