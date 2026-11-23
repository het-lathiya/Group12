"""Country table, time-zone choice, capital fallback and bbox clipping (A2 §6.1, §6.4; IMP-724).

TC-464: every zone in the table loads in zoneinfo, every country has a currency, a capital and at
least one zone, and the nearest-point zone choice picks the expected zone in multi-zone
countries. Pure: no database, no network.
"""

import math
import re
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from app.livedata import countries
from app.livedata.countries import (
    COUNTRIES,
    MAX_HALF_SPAN_DEG,
    MIN_COS_LAT,
    POINT_HALF_SPAN_DEG,
    capital,
    choose_timezone,
    clip_bbox,
    country,
)
from app.livedata.providers.base import BBox

ALL_ZONES = sorted({point.zone for c in COUNTRIES.values() for point in c.zones})
# Uninhabited, with no zone in zone1970.tab or zone.tab (see the module docstring).
NO_ZONE_CODES = {"BV", "HM"}
ISO3166_TAB = Path("/usr/share/zoneinfo/iso3166.tab")
EPS = 1e-9


@pytest.mark.parametrize("zone", ALL_ZONES)
def test_every_zone_loads_in_zoneinfo(zone: str) -> None:
    assert ZoneInfo(zone).key == zone


def test_every_country_has_currency_capital_and_zone() -> None:
    for code, entry in COUNTRIES.items():
        assert re.fullmatch(r"[A-Z]{2}", code)
        assert entry.code == code
        assert entry.name.strip()
        assert re.fullmatch(r"[A-Z]{3}", entry.currency), code
        assert entry.capital.strip(), code
        assert entry.zones, code
        for point in entry.zones:
            assert -90 <= point.lat <= 90
            assert -180 <= point.lon <= 180


def test_table_covers_iso3166() -> None:
    assert len(COUNTRIES) >= 240
    if not ISO3166_TAB.is_file():
        return
    codes = {
        line.split("\t", 1)[0]
        for line in ISO3166_TAB.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }
    assert codes - set(COUNTRIES) <= NO_ZONE_CODES
    assert set(COUNTRIES) <= codes


@pytest.mark.parametrize(
    ("code", "lat", "lon", "expected"),
    [
        ("US", 40.7128, -74.0060, "America/New_York"),
        ("US", 34.0522, -118.2437, "America/Los_Angeles"),
        ("US", 41.8781, -87.6298, "America/Chicago"),
        ("US", 21.3069, -157.8583, "Pacific/Honolulu"),
        ("IN", 24.5854, 73.7125, "Asia/Kolkata"),
        ("RU", 55.7558, 37.6173, "Europe/Moscow"),
        ("RU", 43.1155, 131.8855, "Asia/Vladivostok"),
        ("RU", 55.0084, 82.9357, "Asia/Novosibirsk"),
        ("BR", -23.5505, -46.6333, "America/Sao_Paulo"),
        ("BR", -3.1190, -60.0217, "America/Manaus"),
        ("AU", -33.8688, 151.2093, "Australia/Sydney"),
        ("AU", -31.9505, 115.8605, "Australia/Perth"),
    ],
)
def test_choose_timezone_nearest_point(code: str, lat: float, lon: float, expected: str) -> None:
    assert choose_timezone(code, lat, lon) == expected


def test_single_zone_country_ignores_position() -> None:
    assert choose_timezone("IN", -60.0, 0.0) == "Asia/Kolkata"


def test_multi_zone_countries_exist() -> None:
    multi = {code for code, entry in COUNTRIES.items() if len(entry.zones) > 1}
    assert {"US", "RU", "BR", "AU", "CA", "MX", "ID"} <= multi


def test_unknown_code_is_none() -> None:
    assert country("ZZ") is None
    assert choose_timezone("ZZ", 0.0, 0.0) is None
    assert capital("ZZ") is None


def test_lowercase_code_accepted() -> None:
    found = country("in")
    assert found is not None
    assert found.code == "IN"
    assert found.currency == "INR"
    assert choose_timezone("us", 40.7128, -74.0060) == "America/New_York"


def test_capital_fallback() -> None:
    assert capital("IN") == "New Delhi"
    assert capital("fr") == "Paris"


def _lon_limit(lat: float) -> float:
    return MAX_HALF_SPAN_DEG / max(math.cos(math.radians(lat)), MIN_COS_LAT)


def test_huge_admin_box_is_clipped() -> None:
    lat, lon = 26.9124, 75.7873
    out = clip_bbox(lat, lon, BBox(south=23.0, west=69.5, north=30.2, east=78.3))
    assert out.south == pytest.approx(lat - MAX_HALF_SPAN_DEG)
    assert out.north == pytest.approx(lat + MAX_HALF_SPAN_DEG)
    assert out.west == pytest.approx(lon - _lon_limit(lat))
    assert out.east == pytest.approx(lon + _lon_limit(lat))
    assert out.contains(lat, lon)


def test_small_box_kept_as_is() -> None:
    box = BBox(south=24.50, west=73.60, north=24.68, east=73.80)
    assert clip_bbox(24.5854, 73.7125, box) == box


def test_point_box_widened() -> None:
    lat, lon = 48.8566, 2.3522
    out = clip_bbox(lat, lon, BBox(south=lat, west=lon, north=lat, east=lon))
    assert out.south == pytest.approx(lat - POINT_HALF_SPAN_DEG)
    assert out.north == pytest.approx(lat + POINT_HALF_SPAN_DEG)
    assert out.west == pytest.approx(lon - POINT_HALF_SPAN_DEG)
    assert out.east == pytest.approx(lon + POINT_HALF_SPAN_DEG)


def test_none_box_widened() -> None:
    out = clip_bbox(10.0, 20.0, None)
    assert out == BBox(
        south=10.0 - POINT_HALF_SPAN_DEG,
        west=20.0 - POINT_HALF_SPAN_DEG,
        north=10.0 + POINT_HALF_SPAN_DEG,
        east=20.0 + POINT_HALF_SPAN_DEG,
    )


def test_narrow_dimension_only_is_widened() -> None:
    out = clip_bbox(10.0, 20.0, BBox(south=9.9, west=19.99, north=10.1, east=20.01))
    assert (out.south, out.north) == (9.9, 10.1)
    assert out.west == pytest.approx(20.0 - POINT_HALF_SPAN_DEG)
    assert out.east == pytest.approx(20.0 + POINT_HALF_SPAN_DEG)


def test_centre_outside_box_is_included() -> None:
    out = clip_bbox(10.0, 20.0, BBox(south=10.2, west=20.2, north=10.4, east=20.4))
    assert out.contains(10.0, 20.0)


def test_high_latitude_does_not_blow_up() -> None:
    for lat in (78.2232, 89.99, -89.99, 90.0):
        out = clip_bbox(lat, 15.6267, BBox(south=-90.0, west=-180.0, north=90.0, east=180.0))
        assert out.contains(lat, 15.6267)
        assert out.east - out.west <= 2 * MAX_HALF_SPAN_DEG / MIN_COS_LAT + EPS
        assert -90 <= out.south <= out.north <= 90


def test_antimeridian_is_clamped() -> None:
    out = clip_bbox(-17.7134, 179.95, BBox(south=-18.0, west=177.0, north=-17.0, east=180.0))
    assert out.east == 180.0
    assert out.contains(-17.7134, 179.95)
    out = clip_bbox(-17.7134, -179.99, None)
    assert out.west == -180.0
    assert out.contains(-17.7134, -179.99)


def test_invalid_centre_rejected() -> None:
    with pytest.raises(ValueError, match="out of range"):
        clip_bbox(91.0, 0.0, None)
    with pytest.raises(ValueError, match="finite"):
        clip_bbox(math.nan, 0.0, None)


def test_module_is_pure() -> None:
    source = Path(countries.__file__).read_text(encoding="utf-8")
    for banned in ("fastapi", "sqlalchemy", "httpx", "google", "app.db", "app.core"):
        assert f"import {banned}" not in source
        assert f"from {banned}" not in source
