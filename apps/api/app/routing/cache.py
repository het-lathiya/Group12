"""The route_cache table (migration 0004). MOD-B10 is its only writer (§3, §9.3.5)."""

from datetime import UTC, datetime, timedelta
from typing import Final
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import RouteCache
from app.routing.estimate import TravelEstimate, TravelMode

ROUTE_TTL: Final = timedelta(days=30)  # Provisional (IMD-30)
FALLBACK_TTL: Final = timedelta(days=1)  # at most 1 day (IMD-30)
PROVIDER_NAME: Final = "openrouteservice"


class RouteCacheRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, from_id: UUID, to_id: UUID, mode: TravelMode) -> RouteCache | None:
        """The pair's row if it has not expired."""
        query = select(RouteCache).where(
            RouteCache.from_place_id == from_id,
            RouteCache.to_place_id == to_id,
            RouteCache.mode == mode.value,
            RouteCache.expires_at > func.now(),
        )
        return await self._session.scalar(query.execution_options(populate_existing=True))

    async def upsert(
        self, from_id: UUID, to_id: UUID, result: TravelEstimate, *, ttl: timedelta
    ) -> None:
        """Store the pair's result, replacing an older row such as an expired estimate."""
        values = {
            "travel_minutes": result.minutes,
            "distance_m": result.distance_m,
            "travel_source": result.travel_source,
            "provider_name": PROVIDER_NAME if result.travel_source == "routing_api" else None,
            "computed_at": datetime.now(UTC),
            "expires_at": datetime.now(UTC) + ttl,
        }
        statement = insert(RouteCache).values(
            from_place_id=from_id, to_place_id=to_id, mode=result.mode.value, **values
        )
        await self._session.execute(
            statement.on_conflict_do_update(
                index_elements=["from_place_id", "to_place_id", "mode"], set_=values
            )
        )
