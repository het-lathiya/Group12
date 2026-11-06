"""OpenRouteService directions client (§9.3.5, §10; FR-078, NFR-038). The only ORS HTTP calls.

One attempt, no retry: a timeout, a 4xx or 5xx answer, an answer without a route or a missing key
raises ``RoutingUnavailable`` and the service falls back to the distance estimate. The key travels
in a header and never appears in a message.
"""

import logging
import math
from dataclasses import dataclass
from datetime import UTC, date, datetime
from functools import lru_cache
from typing import Final

import httpx

from app.core.config import get_settings
from app.routing.estimate import TravelMode

logger = logging.getLogger(__name__)

DIRECTIONS_URL: Final = "https://api.openrouteservice.org/v2/directions/{profile}/json"
PROFILES: Final[dict[TravelMode, str]] = {
    TravelMode.WALKING: "foot-walking",
    TravelMode.LOCAL_TRANSPORT: "driving-car",
    TravelMode.CAR: "driving-car",
}
NEAR_QUOTA_SHARE: Final = 0.8

LatLon = tuple[float, float]


class RoutingUnavailable(Exception):  # noqa: N818  # the name is fixed by the IMP-307 card
    """No route from the routing service; the message is safe to log."""


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
        self._count_call()
        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
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
            raise RoutingUnavailable("timeout") from None
        except httpx.HTTPStatusError as exc:
            raise RoutingUnavailable(f"http {exc.response.status_code}") from None
        except httpx.HTTPError:
            raise RoutingUnavailable("connection") from None
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
