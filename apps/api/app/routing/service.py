"""Routing service (MOD-B10): the travel time between two consecutive places (§9.3.5, FR-078, FR-079).

``RoutingService.travel`` follows the lookup order of §9.3.5: a non-expired route_cache row (no
external call), then OpenRouteService (cached 30 days), then the distance estimate of
``routing/estimate.py`` (``travel_time``, cached 1 day).
"""

import logging
from decimal import Decimal
from typing import Protocol, cast
from uuid import UUID

from app.routing.cache import FALLBACK_TTL, ROUTE_TTL, RouteCacheRepository
from app.routing.client import OrsClient, RoutingUnavailable
from app.routing.estimate import TravelEstimate, TravelMode, TravelSource, estimate

logger = logging.getLogger(__name__)


class Located(Protocol):
    """Anything with coordinates, such as a ``places`` row."""

    @property
    def lat(self) -> Decimal | float: ...
    @property
    def lon(self) -> Decimal | float: ...


class RoutablePlace(Located, Protocol):
    @property
    def id(self) -> UUID: ...


async def travel_time(place_a: Located, place_b: Located, mode: TravelMode | str) -> TravelEstimate:
    """The labelled distance estimate from ``place_a`` to ``place_b`` (no cache, no external call)."""
    return estimate(
        float(place_a.lat), float(place_a.lon), float(place_b.lat), float(place_b.lon), mode
    )


class RoutingService:
    def __init__(self, cache: RouteCacheRepository, client: OrsClient) -> None:
        self._cache = cache
        self._client = client

    async def travel(
        self, origin: RoutablePlace, target: RoutablePlace, mode: TravelMode | str
    ) -> TravelEstimate:
        """Travel time and distance with its source: cache, then ORS, then the estimate."""
        travel_mode = TravelMode(mode)
        if origin.id == target.id:  # route_cache refuses a pair of one place
            return await travel_time(origin, target, travel_mode)
        cached = await self._cache.get(origin.id, target.id, travel_mode)
        if cached is not None:
            logger.info(
                "route cache hit mode=%s travel_source=%s", travel_mode, cached.travel_source
            )
            return TravelEstimate(
                minutes=cached.travel_minutes,
                distance_m=cached.distance_m,
                mode=travel_mode,
                travel_source=cast(TravelSource, cached.travel_source),
            )
        try:
            route = await self._client.route(
                (float(origin.lat), float(origin.lon)),
                (float(target.lat), float(target.lon)),
                travel_mode,
            )
        except RoutingUnavailable as exc:
            logger.info("route fallback mode=%s reason=%s", travel_mode, exc)
            result = await travel_time(origin, target, travel_mode)
            await self._cache.upsert(origin.id, target.id, result, ttl=FALLBACK_TTL)
            return result
        result = TravelEstimate(route.minutes, route.metres, travel_mode, "routing_api")
        await self._cache.upsert(origin.id, target.id, result, ttl=ROUTE_TTL)
        logger.info("route from routing service mode=%s", travel_mode)
        return result
