"""Outbound spacing and circuit breakers for the live-data services (Amendment A2 §7.1, §7.3).

Each public service gets one ``Throttle`` per process: calls are serialised by one lock, and a call
starts no sooner than the spacing after the previous call ended (Nominatim 1.0 s, Overpass 2.0 s,
MediaWiki 0.2 s). Nominatim and Overpass also get a ``CircuitBreaker`` from ``app.ai.breaker``:
5 consecutive transient failures open it for 60 s and a 429 opens it for 15 minutes. While it is
open a call fails at once with ``LiveDataRateLimited`` and the service is not called, which the
places module turns into 503 (API-76, API-77) or ``failed`` / ``rate_limited`` for an import.

The ``Guarded*`` wrappers implement the protocols of ``providers.base`` around any inner provider;
``guard_geocoder``, ``guard_places`` and ``guard_guides`` wrap one with the per-process instances.
This module does no I/O of its own.
"""

import asyncio
import math
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Final, TypeVar

from app.ai.breaker import QUOTA_COOL_DOWN_S, TRANSIENT_COOL_DOWN_S, CircuitBreaker
from app.ai.errors import (
    ProviderError,
    ProviderQuotaExhausted,
    ProviderTimeout,
    ProviderUnavailable,
)
from app.livedata.providers.base import (
    BBox,
    GeoCandidate,
    GeocodingProvider,
    GeoPlace,
    GuideSourceProvider,
    LiveDataError,
    LiveDataRateLimited,
    LiveDataTimeout,
    OsmElement,
    PlacesProvider,
    WikiSection,
)

NOMINATIM_SPACING_S: Final = 1.0
OVERPASS_SPACING_S: Final = 2.0
MEDIAWIKI_SPACING_S: Final = 0.2

T = TypeVar("T")


class Throttle:
    """Serialises calls to one host and keeps at least ``spacing_s`` between them."""

    def __init__(
        self,
        spacing_s: float,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[object]] = asyncio.sleep,
    ) -> None:
        if spacing_s < 0:
            raise ValueError("spacing must not be negative")
        self.spacing_s = spacing_s
        self._clock = clock
        self._sleep = sleep
        self._last_end: float | None = None
        self._retry_at = 0.0
        self._lock: asyncio.Lock | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    @property
    def retry_after_s(self) -> int:
        """Seconds until this host's cooldown ends, rounded up for the error envelope."""
        return max(0, math.ceil(self._retry_at - self._clock()))

    def defer_for(self, seconds: float) -> None:
        """Extend a host cooldown without sleeping in an import or shortening an earlier one."""
        self._retry_at = max(self._retry_at, self._clock() + seconds)

    def _current_lock(self) -> asyncio.Lock:
        # An asyncio.Lock belongs to one event loop; a new loop (a new test) gets a new lock.
        loop = asyncio.get_running_loop()
        if self._lock is None or self._loop is not loop:
            self._lock = asyncio.Lock()
            self._loop = loop
        return self._lock

    @asynccontextmanager
    async def slot(self) -> AsyncIterator[None]:
        """Hold the host for one call, after waiting out the spacing."""
        async with self._current_lock():
            if self._last_end is not None:
                wait_s = self._last_end + self.spacing_s - self._clock()
                if wait_s > 0:
                    await self._sleep(wait_s)
            try:
                yield
            finally:
                self._last_end = self._clock()


def _as_provider_error(error: LiveDataError) -> ProviderError:
    """The breaker's view of a live-data error: a 429 counts as quota (15 min), others transient."""
    if isinstance(error, LiveDataRateLimited):
        return ProviderQuotaExhausted("live data rate limited")
    if isinstance(error, LiveDataTimeout):
        return ProviderTimeout("live data timeout")
    return ProviderUnavailable("live data unavailable")


class _Guard:
    def __init__(self, throttle: Throttle, breaker: CircuitBreaker | None) -> None:
        self.throttle = throttle
        self.breaker = breaker

    def _refuse_if_open(self) -> None:
        if self.breaker is not None and self.breaker.state == "open":
            raise LiveDataRateLimited("circuit breaker open")
        if self.throttle.retry_after_s:
            raise LiveDataRateLimited("provider cooldown")

    async def run(self, call: Callable[[], Awaitable[T]]) -> T:
        self._refuse_if_open()
        async with self.throttle.slot():
            self._refuse_if_open()  # it may have opened while this call waited for the host
            try:
                result = await call()
            except LiveDataError as exc:
                if self.breaker is not None:
                    self.breaker.record_failure(_as_provider_error(exc))
                    if self.breaker.state == "open":
                        self.throttle.defer_for(
                            QUOTA_COOL_DOWN_S
                            if isinstance(exc, LiveDataRateLimited)
                            else TRANSIENT_COOL_DOWN_S
                        )
                raise
        if self.breaker is not None:
            self.breaker.record_success()
        return result


class GuardedGeocoder:
    """A ``GeocodingProvider`` with the Nominatim throttle and breaker applied."""

    def __init__(
        self, inner: GeocodingProvider, throttle: Throttle, breaker: CircuitBreaker
    ) -> None:
        self.inner = inner
        self._guard = _Guard(throttle, breaker)

    async def search(self, q: str) -> list[GeoCandidate]:
        return await self._guard.run(lambda: self.inner.search(q))

    async def lookup(self, osm_ref: str) -> GeoPlace | None:
        return await self._guard.run(lambda: self.inner.lookup(osm_ref))


class GuardedPlaces:
    """A ``PlacesProvider`` with the Overpass throttle and breaker applied."""

    def __init__(self, inner: PlacesProvider, throttle: Throttle, breaker: CircuitBreaker) -> None:
        self.inner = inner
        self._guard = _Guard(throttle, breaker)

    async def fetch(self, bbox: BBox) -> list[OsmElement]:
        return await self._guard.run(lambda: self.inner.fetch(bbox))

    async def largest_city_near(self, lat: float, lon: float, radius_km: float) -> str | None:
        return await self._guard.run(lambda: self.inner.largest_city_near(lat, lon, radius_km))


class GuardedGuides:
    """A ``GuideSourceProvider`` with the MediaWiki throttle applied (serial, no breaker)."""

    def __init__(self, inner: GuideSourceProvider, throttle: Throttle) -> None:
        self.inner = inner
        self._guard = _Guard(throttle, None)

    async def fetch(self, name: str, lat: float, lon: float) -> list[WikiSection]:
        return await self._guard.run(lambda: self.inner.fetch(name, lat, lon))


# Per-process instances: one throttle per host and one breaker per Nominatim and Overpass.
@lru_cache(maxsize=1)
def nominatim_throttle() -> Throttle:
    return Throttle(NOMINATIM_SPACING_S)


@lru_cache(maxsize=1)
def overpass_throttle() -> Throttle:
    return Throttle(OVERPASS_SPACING_S)


@lru_cache(maxsize=1)
def mediawiki_throttle() -> Throttle:
    return Throttle(MEDIAWIKI_SPACING_S)


@lru_cache(maxsize=1)
def nominatim_breaker() -> CircuitBreaker:
    return CircuitBreaker()


@lru_cache(maxsize=1)
def overpass_breaker() -> CircuitBreaker:
    return CircuitBreaker()


def overpass_retry_after_s() -> int:
    """Read the shared Overpass cooldown before queuing another import; no provider call."""
    return overpass_throttle().retry_after_s


def guard_geocoder(inner: GeocodingProvider) -> GuardedGeocoder:
    return GuardedGeocoder(inner, nominatim_throttle(), nominatim_breaker())


def guard_places(inner: PlacesProvider) -> GuardedPlaces:
    return GuardedPlaces(inner, overpass_throttle(), overpass_breaker())


def guard_guides(inner: GuideSourceProvider) -> GuardedGuides:
    return GuardedGuides(inner, mediawiki_throttle())
