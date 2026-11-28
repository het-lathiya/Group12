"""route_cache through RouteCacheRepository (§9.3.5; FR-078; IMP-307). Runs against the migrated
test database with Sampleton loaded through the seed; every test is rolled back.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
import respx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Place, RouteCache
from app.places import seed
from app.routing.cache import FALLBACK_TTL, ROUTE_TTL, RouteCacheRepository
from app.routing.client import OrsClient
from app.routing.estimate import TravelEstimate, TravelMode
from app.routing.service import RoutingService

REPO_ROOT = Path(__file__).resolve().parents[4]
SAMPLETON = REPO_ROOT / "data" / "fixtures" / "sampleton"
WALK_URL = "https://api.heigit.org/openrouteservice/v2/directions/foot-walking/json"
ROUTE = TravelEstimate(12, 900, TravelMode.WALKING, "routing_api")
ESTIMATE = TravelEstimate(20, 800, TravelMode.WALKING, "fallback_estimate")
ANSWER: dict[str, Any] = {"routes": [{"summary": {"distance": 900.0, "duration": 720.0}}]}


@pytest_asyncio.fixture
async def pair(db_session: AsyncSession) -> tuple[Place, Place]:
    await seed.load_fixture(db_session, seed.read_fixture(SAMPLETON))
    places = (await db_session.scalars(select(Place).limit(2))).all()
    return places[0], places[1]


async def expire_all(session: AsyncSession) -> None:
    await session.execute(update(RouteCache).values(expires_at=datetime(2000, 1, 1, tzinfo=UTC)))


@pytest.mark.asyncio
async def test_a_stored_route_is_read_back_and_expires(
    db_session: AsyncSession, pair: tuple[Place, Place]
) -> None:
    a, b = pair
    cache = RouteCacheRepository(db_session)
    assert await cache.get(a.id, b.id, TravelMode.WALKING) is None
    await cache.upsert(a.id, b.id, ROUTE, ttl=ROUTE_TTL)
    row = await cache.get(a.id, b.id, TravelMode.WALKING)
    assert row is not None
    assert (row.travel_minutes, row.distance_m) == (12, 900)
    assert (row.travel_source, row.provider_name) == ("routing_api", "openrouteservice")
    assert timedelta(days=29) < row.expires_at - row.computed_at <= timedelta(days=30, seconds=1)
    assert await cache.get(b.id, a.id, TravelMode.WALKING) is None
    assert await cache.get(a.id, b.id, TravelMode.CAR) is None
    await expire_all(db_session)
    assert await cache.get(a.id, b.id, TravelMode.WALKING) is None


@pytest.mark.asyncio
async def test_a_routing_result_replaces_an_expired_estimate(
    db_session: AsyncSession, pair: tuple[Place, Place]
) -> None:
    a, b = pair
    cache = RouteCacheRepository(db_session)
    await cache.upsert(a.id, b.id, ESTIMATE, ttl=FALLBACK_TTL)
    first = await cache.get(a.id, b.id, TravelMode.WALKING)
    assert first is not None
    assert (first.travel_source, first.provider_name) == ("fallback_estimate", None)
    await expire_all(db_session)
    routing = RoutingService(cache, OrsClient("test-ors-key-not-real", 8, 2000))
    with respx.mock() as router:
        route = router.post(WALK_URL).respond(json=ANSWER)
        first_result = await routing.travel(a, b, "walking")
        second_result = await routing.travel(a, b, "walking")
    assert route.call_count == 1
    assert first_result.travel_source == second_result.travel_source == "routing_api"
    db_session.expire_all()
    rows = (await db_session.scalars(select(RouteCache))).all()
    assert len(rows) == 1
