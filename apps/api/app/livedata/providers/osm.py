"""Nominatim and Overpass clients (Amendment A2 §6.1, §6.3, §7.1; IMP-723).

The only Nominatim and Overpass HTTP calls. They follow the ORS client conventions
(``app/routing/client.py``): one attempt and no retry, a timeout from settings, an identifying
``User-Agent`` on every request, and every failure raised as a live-data error with a safe message.
The search text travels only as a URL-encoded query parameter; the Overpass query is built in
``base`` from numbers and the fixed tag list. Logs hold counts, never a query or a response body.
"""

import logging
import re
from typing import Any, Final

import httpx

from app.livedata.providers.base import (
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
        if status == 429:
            raise LiveDataRateLimited("http 429") from None
        raise LiveDataUnavailable(f"http {status}") from None
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


class OverpassPlaces:
    """``PlacesProvider`` over the Overpass API interpreter endpoint."""

    def __init__(self, base_url: str, timeout_s: float, user_agent: str) -> None:
        self._base_url = base_url
        self._timeout_s = timeout_s
        self._user_agent = user_agent

    async def _elements(self, query: str) -> list[OsmElement]:
        body = await _send(
            "POST",
            self._base_url,
            timeout_s=self._timeout_s + OVERPASS_HTTP_MARGIN_S,
            user_agent=self._user_agent,
            data={"data": query},
        )
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
        return elements

    async def fetch(self, bbox: BBox) -> list[OsmElement]:
        """Named places of the fixed tag list inside ``bbox``; elements without a point dropped."""
        return await self._elements(overpass_places_query(bbox, self._timeout_s))

    async def largest_city_near(self, lat: float, lon: float, radius_km: float) -> str | None:
        """The most populous ``place=city`` node within ``radius_km``, or None."""
        query = overpass_city_query(lat, lon, radius_km, self._timeout_s)
        named = [(e.tags.get("name", ""), _population(e.tags)) for e in await self._elements(query)]
        named = [(name, pop) for name, pop in named if name.strip()]
        if not named:
            return None
        with_population = [(name, pop) for name, pop in named if pop is not None]
        if with_population:
            return min(with_population, key=lambda item: (-(item[1] or 0), item[0]))[0]
        return min(name for name, _ in named)
