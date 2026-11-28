"""OpenRouteService directions client (§9.3.5, §10; FR-078, NFR-038). The only ORS HTTP calls.

One attempt, no retry: a timeout, a 4xx or 5xx answer, an answer without a route or a missing key
raises ``RoutingUnavailable`` and the service falls back to the distance estimate. A failure of the
service itself (timeout, connection, 401, 403, 410, 429, 5xx) is remembered for
``FAILURE_MEMO_S``: calls in that window fail at once, so a down ORS costs one attempt and not one
per leg (D5). A 404 or 400 is about the pair (no route) and is not remembered. The key travels in
a header and never appears in a message.

Host: api.openrouteservice.org was retired on 2026-11-24 (it answers 410 "Deprecated HeiGIT API
URL"); the same API and keys are served under api.heigit.org/openrouteservice.
"""

import logging
import math
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime
from functools import lru_cache
from typing import Final

import httpx

from app.core.config import get_settings
from app.routing.estimate import TravelMode

logger = logging.getLogger(__name__)

DIRECTIONS_URL: Final = "https://api.heigit.org/openrouteservice/v2/directions/{profile}/json"
PROFILES: Final[dict[TravelMode, str]] = {
    TravelMode.WALKING: "foot-walking",
    TravelMode.LOCAL_TRANSPORT: "driving-car",
    TravelMode.CAR: "driving-car",
}
NEAR_QUOTA_SHARE: Final = 0.8
CONNECT_TIMEOUT_S: Final = 2.0
FAILURE_MEMO_S: Final = 300.0
_SERVICE_DOWN_STATUSES: Final = frozenset({401, 403, 410, 429})

LatLon = tuple[float, float]


class RoutingUnavailable(Exception):  # noqa: N818  # the name is fixed by the IMP-307 card
    """No route from the routing service; the message is safe to log."""


class _ServiceDown(RoutingUnavailable):  # internal: remembered by the memo
    """ORS itself failed, not the pair."""


@dataclass(frozen=True)
class Route:
    minutes: int
    metres: int


class OrsClient:
    def __init__(self, api_key: str, timeout_s: float, daily_allowance: int) -> None:
        self._api_key = api_key
        self._timeout_s = timeout_s
        self._daily_allowance = daily_allowance
        self._day: date | None = None
        self.calls_today = 0
        self._down_until = 0.0  # time.monotonic() until which ORS is not called (the memo)

    def _count_call(self) -> None:
        # shortcut: in-process only, so each API instance counts its own calls; a shared counter
        # needs a table or service, which needs a decision first.
        today = datetime.now(UTC).date()
        if today != self._day:
            self._day, self.calls_today = today, 0
        self.calls_today += 1
        if self.calls_today == math.ceil(self._daily_allowance * NEAR_QUOTA_SHARE):
            logger.warning(
                "routing near daily quota calls=%d allowance=%d",
                self.calls_today,
                self._daily_allowance,
            )

    async def route(self, origin: LatLon, target: LatLon, mode: TravelMode) -> Route:
        """Minutes (rounded up) and metres from ``origin`` to ``target``, both (lat, lon)."""
        if not self._api_key:
            raise RoutingUnavailable("no key")
        if time.monotonic() < self._down_until:
            raise RoutingUnavailable("recent failure")
        self._count_call()
        try:
            return await self._call(origin, target, mode)
        except _ServiceDown as exc:
            self._down_until = time.monotonic() + FAILURE_MEMO_S
            raise RoutingUnavailable(str(exc)) from None

    async def _call(self, origin: LatLon, target: LatLon, mode: TravelMode) -> Route:
        timeout = httpx.Timeout(self._timeout_s, connect=min(CONNECT_TIMEOUT_S, self._timeout_s))
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    DIRECTIONS_URL.format(profile=PROFILES[mode]),
                    headers={"Authorization": self._api_key},
                    # ORS coordinates are [lon, lat].
                    json={"coordinates": [[origin[1], origin[0]], [target[1], target[0]]]},
                )
            response.raise_for_status()
            summary = response.json()["routes"][0]["summary"]
            return Route(math.ceil(summary["duration"] / 60), round(summary["distance"]))
        except httpx.TimeoutException:
            raise _ServiceDown("timeout") from None
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status in _SERVICE_DOWN_STATUSES or status >= 500:
                raise _ServiceDown(f"http {status}") from None
            raise RoutingUnavailable(f"http {status}") from None
        except httpx.HTTPError:
            raise _ServiceDown("connection") from None
        except (ValueError, LookupError, TypeError):
            raise RoutingUnavailable("malformed response") from None


@lru_cache
def get_client() -> OrsClient:
    """One client per process, so the daily counter covers every request."""
    settings = get_settings()
    return OrsClient(
        settings.ors_api_key.get_secret_value(),
        settings.ors_timeout_s,
        settings.ors_daily_allowance,
    )
