"""Nominatim and Overpass clients (Amendment A2 §6.1, §6.3, §7.1; IMP-723).

The only Nominatim and Overpass HTTP calls. They follow the ORS client conventions
(``app/routing/client.py``): one attempt and no retry, a timeout from settings, an identifying
``User-Agent`` on every request, and every failure raised as a live-data error with a safe message.
The search text travels only as a URL-encoded query parameter; the Overpass query is built in
``base`` from numbers and the fixed tag list. Overpass HTTP failures log a bounded, redacted body
snippet and defer later calls; they never retry a query within an import. Nominatim logs counts.
"""

import asyncio
import logging
import math
import re
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from html import unescape
from typing import Any, Final

import httpx

from app.ai.breaker import QUOTA_COOL_DOWN_S, TRANSIENT_COOL_DOWN_S
from app.core.logging import redact_text
from app.livedata import throttle
from app.livedata.normalise import haversine_m
from app.livedata.providers.base import (
    NEARBY_CITY_MAX_KM,
    BBox,
    GeoCandidate,
    GeoPlace,
    LiveDataRateLimited,
    LiveDataTimeout,
    LiveDataUnavailable,
    OsmElement,
    OsmType,
    SettlementKind,
    overpass_city_query,
    overpass_places_query,
)

logger = logging.getLogger(__name__)

OSM_REF_PATTERN: Final = re.compile(r"^[NWR][0-9]{1,12}$")
SEARCH_LIMIT: Final = 10
MAX_CANDIDATES: Final = 8
# Overpass ends a query at its own [timeout:]; the HTTP timeout leaves room for the answer.
OVERPASS_HTTP_MARGIN_S: Final = 5.0
FAILURE_SNIPPET_CHARS: Final = 256
NEARBY_CITY_RADII_KM: Final = (25.0, 50.0, 100.0, NEARBY_CITY_MAX_KM)

_SENSITIVE_VALUE: Final = re.compile(
    r"""(?ix)
    (["']?[\w-]*(?:key|token|secret|password|authorization|cookie)[\w-]*["']?\s*[:=]\s*)
    (?:"[^"\n]*"|'[^'\n]*'|[^\s,;<>]+)
    """
)


def _failure_snippet(response: httpx.Response, query: str) -> str:
    """Diagnostic text only: no echoed query, credentials, contact details, URLs or IPs."""
    text = unescape(response.text).replace(query, "[query]")[:4096]
    text = re.sub(r"<[^>]*>", " ", text)
    text = re.sub(r"(?i)\b(?:bearer|basic)\s+[^\s,;\"'<>]+", "[redacted]", text)
    text = _SENSITIVE_VALUE.sub(lambda match: match[1] + "[redacted]", text)
    text = re.sub(r"https?://[^\s<>\"']+", "[url]", text)
    text = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[ip]", text)
    text = re.sub(r"(?i)(?<!\w)(?:[a-f0-9]{0,4}:){2,}[a-f0-9:]+", "[ip]", text)
    text = re.sub(r"[\w+/=-]{32,}", "[redacted]", text)
    return " ".join(redact_text(text).split())[:FAILURE_SNIPPET_CHARS] or "[empty]"


def _retry_after_s(value: str | None, *, now: datetime | None = None) -> float | None:
    """Retry-After's delay-seconds or HTTP date; invalid values use the local backoff."""
    if value is None:
        return None
    value = value.strip()
    if value.isascii() and value.isdigit() and len(value) <= 12:
        return float(value)
    try:
        date = parsedate_to_datetime(value)
        if date.tzinfo is None:
            date = date.replace(tzinfo=UTC)
        return max(0.0, (date - (now or datetime.now(UTC))).total_seconds())
    except (ValueError, TypeError, OverflowError):
        return None


_SETTLEMENTS: Final[dict[str, SettlementKind]] = {
    "city": "city",
    "town": "town",
    "village": "village",
    "municipality": "municipality",
}
_REF_LETTERS: Final[dict[str, str]] = {"node": "N", "way": "W", "relation": "R"}
_ELEMENT_TYPES: Final[dict[str, OsmType]] = {"node": "n", "way": "w", "relation": "r"}
_DETAIL_PARAMS: Final[dict[str, str | int]] = {
    "format": "jsonv2",
    "addressdetails": 1,
    "namedetails": 1,
    "accept-language": "en",
}


async def _send(
    method: str,
    url: str,
    *,
    timeout_s: float,
    user_agent: str,
    params: dict[str, str | int] | None = None,
    data: dict[str, str] | None = None,
    on_http_failure: Callable[[httpx.Response], float] | None = None,
) -> Any:
    """One request; the decoded JSON body, or a live-data error with a safe message."""
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            response = await client.request(
                method, url, params=params, data=data, headers={"User-Agent": user_agent}
            )
        response.raise_for_status()
        return response.json()
    except httpx.TimeoutException:
        raise LiveDataTimeout("timeout") from None
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        retry_after_s = on_http_failure(exc.response) if on_http_failure is not None else 0.0
        if status == 429:
            raise LiveDataRateLimited("http 429", retry_after_s=retry_after_s) from None
        raise LiveDataUnavailable(f"http {status}", retry_after_s=retry_after_s) from None
    except httpx.HTTPError:
        raise LiveDataUnavailable("connection") from None
    except (ValueError, LookupError, TypeError):
        raise LiveDataUnavailable("malformed response") from None


def _osm_ref(item: dict[str, Any]) -> str:
    ref = f"{_REF_LETTERS[item['osm_type']]}{int(item['osm_id'])}"
    if not OSM_REF_PATTERN.match(ref):
        raise ValueError("osm reference out of range")
    return ref


def _country_code(address: dict[str, Any]) -> str:
    code = str(address["country_code"]).upper()
    if len(code) != 2 or not code.isalpha():
        raise ValueError("country code is not ISO 3166-1 alpha-2")
    return code


def _name(item: dict[str, Any]) -> str:
    name = item.get("name") or (item.get("namedetails") or {}).get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("result without a name")
    return name


def _region(address: dict[str, Any]) -> str | None:
    state = address.get("state")
    return state if isinstance(state, str) and state else None


def _candidate(item: dict[str, Any]) -> GeoCandidate:
    address = item["address"]
    return GeoCandidate(
        osm_ref=_osm_ref(item),
        name=_name(item),
        display_name=str(item["display_name"]),
        region=_region(address),
        country_code=_country_code(address),
        lat=float(item["lat"]),
        lon=float(item["lon"]),
        kind=_SETTLEMENTS[item["addresstype"]],
    )


def _place(item: dict[str, Any]) -> GeoPlace:
    address = item["address"]
    # Nominatim's boundingbox is [south, north, west, east], as strings.
    south, north, west, east = (float(v) for v in item["boundingbox"])
    name_en = (item.get("namedetails") or {}).get("name:en")
    return GeoPlace(
        osm_ref=_osm_ref(item),
        name=_name(item),
        name_en=name_en if isinstance(name_en, str) and name_en else None,
        display_name=str(item["display_name"]),
        region=_region(address),
        country_code=_country_code(address),
        lat=float(item["lat"]),
        lon=float(item["lon"]),
        kind=str(item["addresstype"]),
        bbox=BBox(south=south, west=west, north=north, east=east),
    )


class NominatimGeocoder:
    """``GeocodingProvider`` over the Nominatim ``/search`` and ``/lookup`` endpoints."""

    def __init__(self, base_url: str, timeout_s: float, user_agent: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s
        self._user_agent = user_agent

    async def search(self, q: str) -> list[GeoCandidate]:
        """Settlements matching ``q`` (city, town, village or municipality), at most 8."""
        body = await _send(
            "GET",
            f"{self._base_url}/search",
            timeout_s=self._timeout_s,
            user_agent=self._user_agent,
            params={**_DETAIL_PARAMS, "limit": SEARCH_LIMIT, "q": q},
        )
        try:
            if not isinstance(body, list):
                raise TypeError("search answer is not a list")
            candidates = [
                _candidate(item)
                for item in body
                if isinstance(item, dict) and item.get("addresstype") in _SETTLEMENTS
            ][:MAX_CANDIDATES]
        except (ValueError, LookupError, TypeError):
            raise LiveDataUnavailable("malformed response") from None
        logger.info("nominatim search results=%d settlements=%d", len(body), len(candidates))
        return candidates

    async def lookup(self, osm_ref: str) -> GeoPlace | None:
        """The place named by ``osm_ref`` (for example ``R1234567``), or None if unknown."""
        if not OSM_REF_PATTERN.match(osm_ref):
            return None
        body = await _send(
            "GET",
            f"{self._base_url}/lookup",
            timeout_s=self._timeout_s,
            user_agent=self._user_agent,
            params={**_DETAIL_PARAMS, "osm_ids": osm_ref},
        )
        try:
            if not isinstance(body, list):
                raise TypeError("lookup answer is not a list")
            place = _place(body[0]) if body else None
        except (ValueError, LookupError, TypeError):
            raise LiveDataUnavailable("malformed response") from None
        logger.info("nominatim lookup results=%d", len(body))
        return place


def _element(item: Any) -> OsmElement | None:
    if not isinstance(item, dict):
        return None
    osm_type = _ELEMENT_TYPES.get(item.get("type", ""))
    if osm_type is None:
        return None
    point = item if osm_type == "n" else item.get("center")
    if not isinstance(point, dict) or "lat" not in point or "lon" not in point:
        return None
    raw_tags = item.get("tags") or {}
    if not isinstance(raw_tags, dict):
        raise TypeError("tags is not an object")
    tags = {k: v for k, v in raw_tags.items() if isinstance(k, str) and isinstance(v, str)}
    return OsmElement(
        osm_type=osm_type,
        osm_id=int(item["id"]),
        lat=float(point["lat"]),
        lon=float(point["lon"]),
        tags=tags,
    )


def _has_error_note(body: Any) -> bool:
    """True when the answer carries a server-side error note beside its elements.

    The elements of such an answer are missing or partial, so they are never used. The note itself
    is never logged or kept.
    """
    note = body.get("remark") if isinstance(body, dict) else None
    return isinstance(note, str) and "error" in note.casefold()


def _population(tags: dict[str, str]) -> int | None:
    raw = tags.get("population", "").replace(",", "").replace(" ", "")
    try:
        return int(raw)
    except ValueError:
        return None


# N1: a 502 or 503 means the instance is busy; the query is retried after these waits.
OVERPASS_BUSY_STATUSES: Final = (502, 503)
OVERPASS_BUSY_WAITS_S: Final = (5.0, 15.0)
OVERPASS_BUSY_MAX_WAIT_S: Final = 30.0  # caps a server Retry-After, so the import stays bounded


class OverpassPlaces:
    """``PlacesProvider`` over the Overpass API interpreter endpoint."""

    def __init__(
        self,
        base_url: str,
        timeout_s: float,
        user_agent: str,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._base_url = base_url
        self._timeout_s = timeout_s
        self._user_agent = user_agent
        self._backoff_s = throttle.OVERPASS_SPACING_S
        self._sleep = sleep
        self._busy_retry_after_s: float | None = None

    def _http_failure(self, response: httpx.Response, query: str) -> float:
        delay = 0.0
        if response.status_code in OVERPASS_BUSY_STATUSES:
            self._busy_retry_after_s = _retry_after_s(response.headers.get("Retry-After"))
        if response.status_code in (429, 504):
            minimum = QUOTA_COOL_DOWN_S if response.status_code == 429 else self._backoff_s
            delay = max(minimum, _retry_after_s(response.headers.get("Retry-After")) or 0.0)
            if response.status_code == 504:
                self._backoff_s = min(TRANSIENT_COOL_DOWN_S, self._backoff_s * 2)
        logger.warning(
            "overpass http failure status=%d body=%s retry_after_s=%d",
            response.status_code,
            _failure_snippet(response, query),
            math.ceil(delay),
        )
        return delay

    async def _elements(self, query: str) -> list[OsmElement]:
        busy = {f"http {status}" for status in OVERPASS_BUSY_STATUSES}
        for wait_s in (*OVERPASS_BUSY_WAITS_S, None):
            self._busy_retry_after_s = None
            try:
                body = await _send(
                    "POST",
                    self._base_url,
                    timeout_s=self._timeout_s + OVERPASS_HTTP_MARGIN_S,
                    user_agent=self._user_agent,
                    data={"data": query},
                    on_http_failure=lambda response: self._http_failure(response, query),
                )
                break
            except LiveDataUnavailable as exc:
                if wait_s is None or str(exc) not in busy:
                    raise
                hint = self._busy_retry_after_s
                await self._sleep(min(OVERPASS_BUSY_MAX_WAIT_S, wait_s if hint is None else hint))
        try:
            if _has_error_note(body):
                raise LiveDataUnavailable("error note")
            raw = body["elements"]
            if not isinstance(raw, list):
                raise TypeError("elements is not a list")
            elements = [e for e in (_element(item) for item in raw) if e is not None]
        except (ValueError, LookupError, TypeError):
            raise LiveDataUnavailable("malformed response") from None
        logger.info("overpass elements=%d kept=%d", len(raw), len(elements))
        self._backoff_s = throttle.OVERPASS_SPACING_S
        return elements

    async def fetch(self, bbox: BBox) -> list[OsmElement]:
        """Named places of the fixed tag list inside ``bbox``; elements without a point dropped."""
        return await self._elements(overpass_places_query(bbox, self._timeout_s))

    async def largest_city_near(self, lat: float, lon: float, radius_km: float) -> str | None:
        """Expand through distance bands, using one query capped at A2's 150 km maximum."""
        maximum = min(radius_km, NEARBY_CITY_MAX_KM)
        query = overpass_city_query(lat, lon, maximum, self._timeout_s)
        cities = [
            (e.tags.get("name", "").strip(), _population(e.tags), distance / 1000)
            for e in await self._elements(query)
            if e.osm_type == "n"
            and e.tags.get("place") == "city"
            and math.isfinite(e.lat)
            and math.isfinite(e.lon)
            and -90 <= e.lat <= 90
            and -180 <= e.lon <= 180
            and 1 < (distance := haversine_m(lat, lon, e.lat, e.lon)) <= maximum * 1000
        ]
        cities = [(name, pop, distance) for name, pop, distance in cities if name]
        for radius in (*[r for r in NEARBY_CITY_RADII_KM if r < maximum], maximum):
            nearby = [(name, pop) for name, pop, distance in cities if distance <= radius]
            if nearby:
                return min(nearby, key=lambda item: (-(item[1] or 0), item[0]))[0]
        return None
