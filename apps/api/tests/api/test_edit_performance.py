"""Edit recalculation time on a 10-day plan (IMP-407; NFR-003: TC-330, recorded, not a gate).

Runs 30 edits through ``apply_edit`` on a 10-day rule-based plan and prints the p50 and p95 in
milliseconds (run with ``-s`` to see the line). The p95 target is 1.5 s; the assertion is loose
(5 s) so a slow CI runner does not fail the build.
"""

import statistics
import time

import httpx
import pytest
from fixtures.auth import AuthUser
from sqlalchemy.ext.asyncio import AsyncSession
from test_edits import Queue, destination, edit, items, jobs_queue, planned_trip

from app.db.models import Destination, Trip
from app.itinerary.edits import Lock, Retime

__all__ = ["destination", "jobs_queue"]  # the fixtures, used by name below

EDITS = 30
P95_TARGET_MS = 1500


@pytest.mark.asyncio
async def test_tc_330_edit_performance_on_a_ten_day_plan(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    auth_user: AuthUser,
    destination: Destination,
    jobs_queue: Queue,
) -> None:
    trip_id = await planned_trip(
        api_client, db_session, jobs_queue, auth_user, destination, end_date="2026-12-13"
    )
    rows = await items(db_session, trip_id)
    trip = await db_session.get(Trip, trip_id)
    assert trip is not None
    assert (trip.end_date - trip.start_date).days + 1 == 10
    targets = [(row.id, row.duration_min) for row in rows]
    timings = []

    for count in range(EDITS):
        item_id, duration = targets[count % len(targets)]
        operation = (
            Retime(item_id, duration_min=duration + 15) if count % 2 else Lock(item_id, True)
        )
        started = time.perf_counter()
        await edit(db_session, auth_user, trip_id, operation)
        timings.append((time.perf_counter() - started) * 1000)
        if count % 2 == 0:  # unlock again so the next retime of this item is allowed
            await edit(db_session, auth_user, trip_id, Lock(item_id, False))

    p50 = statistics.median(timings)
    p95 = statistics.quantiles(timings, n=20)[-1]
    print(
        f"\nTC-330 edit_performance: {EDITS} edits on a 10-day trip ({len(rows)} items on "
        f"{len({row.day_id for row in rows})} planned days): "
        f"p50 {p50:.0f} ms, p95 {p95:.0f} ms (target p95 < {P95_TARGET_MS} ms)"
    )
    assert p95 < 5000, f"p95 {p95:.0f} ms"
