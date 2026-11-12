"""The itinerary tables (migration 0004): itinerary_days, itinerary_items, itinerary_warnings and
itinerary_versions, plus trips.plan_revision (§5.2), written only by MOD-B08 (§3). Every function
takes the caller's session and opens no transaction of its own. budget_settings, places,
trip_places and ai_generations are only read.
"""

from collections.abc import Sequence
from datetime import date, datetime, time, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import delete, exists, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AiGeneration,
    BudgetSettings,
    ItineraryDay,
    ItineraryItem,
    ItineraryVersion,
    ItineraryWarning,
    Place,
    Trip,
    TripPlace,
)
from app.itinerary.schemas import PlannedDay
from app.schemas.ai import PlanFinding


async def lock_trip(session: AsyncSession, trip_id: UUID, user_id: UUID) -> Trip | None:
    query = (
        select(Trip)
        .where(Trip.id == trip_id, Trip.user_id == user_id, Trip.deleted_at.is_(None))
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return await session.scalar(query)


async def replace_plan(
    session: AsyncSession,
    trip_id: UUID,
    start_date: date,
    plan: Sequence[PlannedDay],
    *,
    origin: str,
    generation_id: UUID,
) -> list[dict[str, Any]]:
    """Replace the trip's days, items and warnings with the plan; returns the snap-1 days.

    Times, durations, travel and costs are stored as step 9 calculated them; the snapshot leaves
    travel and costs out, because a restore recalculates them (§5.2). It keeps the citations, as
    strings (A1 §5.5). Only a model plan keeps its notes: note_origin is ai or none here, and the
    table ties none to a null note, so a fallback note cannot be stored as AI-written (§7.8).
    """
    await session.execute(delete(ItineraryWarning).where(ItineraryWarning.trip_id == trip_id))
    # Items go with their day (foreign key on delete cascade).
    await session.execute(delete(ItineraryDay).where(ItineraryDay.trip_id == trip_id))
    snapshot_days: list[dict[str, Any]] = []
    for day in sorted(plan, key=lambda d: d.day_number):
        plan_date = start_date + timedelta(days=day.day_number - 1)
        day_row = ItineraryDay(
            trip_id=trip_id,
            day_number=day.day_number,
            plan_date=plan_date,
            theme=day.theme or None,
            source_generation_id=generation_id,
        )
        session.add(day_row)
        await session.flush()
        items: list[dict[str, Any]] = []
        for position, item in enumerate(day.items, start=1):
            note = (item.note or None) if origin == "model" else None
            values: dict[str, Any] = {
                "position": position,
                "slot_type": item.slot_type,
                "duration_min": item.duration_min,
                "origin": origin,
                "note": note,
                "note_origin": "ai" if note else "none",
                "is_locked": False,
            }
            session.add(
                ItineraryItem(
                    trip_id=trip_id,
                    day_id=day_row.id,
                    place_id=UUID(item.place_id),
                    start_time=time.fromisoformat(item.start_time),
                    travel_from_prev_min=item.travel_from_prev_min,
                    travel_from_prev_m=item.travel_from_prev_m,
                    travel_mode=item.travel_mode,
                    travel_source=item.travel_source,
                    cost_min=item.cost_min,
                    cost_max=item.cost_max,
                    cost_currency=item.cost_currency,
                    cost_label=item.cost_label,
                    source_chunk_ids=[UUID(chunk_id) for chunk_id in item.source_chunk_ids],
                    **values,
                )
            )
            items.append(
                {
                    "place_id": item.place_id,
                    "start_time": item.start_time,
                    "source_chunk_ids": list(item.source_chunk_ids),
                    **values,
                }
            )
        snapshot_days.append(
            {
                "day_number": day.day_number,
                "plan_date": plan_date.isoformat(),
                "theme": day_row.theme,
                "items": items,
            }
        )
    await session.flush()
    return snapshot_days


async def insert_warnings(
    session: AsyncSession, trip_id: UUID, plan_revision: int, findings: Sequence[PlanFinding]
) -> None:
    """The warnings of one plan_revision (§8.12): item_ref becomes item_id; MUST_VISIT_MISSING has
    no item and keeps its place_id (IMD-42). Call after ``replace_plan`` or ``delete_warnings``,
    which removed what this replaces; other revisions keep theirs, for their versions (FR-058)."""
    if not findings:
        return
    numbers = {day.id: day.day_number for day in await plan_days(session, trip_id)}
    refs = {
        f"d{numbers[item.day_id]}-i{item.position}": item.id
        for item, _, _ in await plan_items(session, trip_id)
    }
    for finding in findings:
        session.add(
            ItineraryWarning(
                trip_id=trip_id,
                plan_revision=plan_revision,
                code=finding.code,
                severity=finding.severity,
                message=finding.message,
                day_number=finding.day_number,
                item_id=refs.get(finding.item_ref) if finding.item_ref else None,
                place_id=finding.place_id,
                suggested_fix=finding.suggested_fix,
            )
        )
    await session.flush()


async def delete_warnings(session: AsyncSession, trip_id: UUID, plan_revision: int) -> None:
    await session.execute(
        delete(ItineraryWarning).where(
            ItineraryWarning.trip_id == trip_id, ItineraryWarning.plan_revision == plan_revision
        )
    )


async def budget_settings_snapshot(session: AsyncSession, trip_id: UUID) -> dict[str, Any]:
    row = await session.get(BudgetSettings, trip_id)
    if row is None:
        return {}
    return {
        "transport_allowance_per_day": _amount(row.transport_allowance_per_day),
        "stay_budget_per_night": _amount(row.stay_budget_per_night),
        "contingency_pct": _amount(row.contingency_pct),
    }


def _amount(value: Any) -> str | None:
    return None if value is None else f"{value:.2f}"


async def mark_plan_saved(session: AsyncSession, trip_id: UUID) -> int:
    """plan_revision + 1, status ready, plan_stale false; returns the new plan_revision."""
    statement = (
        update(Trip)
        .where(Trip.id == trip_id)
        .values(
            plan_revision=Trip.plan_revision + 1,
            status="ready",
            plan_stale=False,
            updated_at=func.now(),
        )
        .returning(Trip.plan_revision)
    )
    return int((await session.execute(statement)).scalar_one())


async def insert_version(
    session: AsyncSession,
    trip_id: UUID,
    *,
    reason: str,
    plan_revision: int,
    snapshot: dict[str, Any],
    validation_summary: dict[str, Any],
    generation_id: UUID | None,
    created_by: UUID | None,
) -> UUID:
    """A version with version_no = the trip's highest + 1 (the trip row is locked by the caller).

    Its validation_summary always carries the repair counts (IMP-405), 0 when none were made."""
    highest = await session.scalar(
        select(func.max(ItineraryVersion.version_no)).where(ItineraryVersion.trip_id == trip_id)
    )
    row = ItineraryVersion(
        trip_id=trip_id,
        version_no=(highest or 0) + 1,
        reason=reason,
        plan_revision=plan_revision,
        snapshot=snapshot,
        validation_summary={"deterministic_repairs": 0, "repair_attempts": 0, **validation_summary},
        generation_id=generation_id,
        created_by=created_by,
    )
    session.add(row)
    await session.flush()
    return row.id


async def version_for_generation(
    session: AsyncSession, generation_id: UUID
) -> ItineraryVersion | None:
    query = (
        select(ItineraryVersion)
        .where(ItineraryVersion.generation_id == generation_id)
        .order_by(ItineraryVersion.version_no.desc())
        .limit(1)
    )
    return await session.scalar(query)


async def plan_days(session: AsyncSession, trip_id: UUID) -> list[ItineraryDay]:
    query = (
        select(ItineraryDay)
        .where(ItineraryDay.trip_id == trip_id)
        .order_by(ItineraryDay.day_number)
    )
    return list(await session.scalars(query))


async def plan_items(
    session: AsyncSession, trip_id: UUID
) -> list[tuple[ItineraryItem, Place, bool]]:
    """Every item of the trip with its place and must-visit flag, in day and position order."""
    must_visit = exists().where(
        TripPlace.trip_id == ItineraryItem.trip_id,
        TripPlace.place_id == ItineraryItem.place_id,
        TripPlace.relation == "must_visit",
    )
    query = (
        select(ItineraryItem, Place, must_visit)
        .join(Place, Place.id == ItineraryItem.place_id)
        .join(ItineraryDay, ItineraryDay.id == ItineraryItem.day_id)
        .where(ItineraryItem.trip_id == trip_id)
        .order_by(ItineraryDay.day_number, ItineraryItem.position)
    )
    return [(item, place, bool(flag)) for item, place, flag in await session.execute(query)]


async def latest_version_id(
    session: AsyncSession, trip_id: UUID, plan_revision: int
) -> UUID | None:
    """§5.9: the newest version of the current revision, else None."""
    query = (
        select(ItineraryVersion.id)
        .where(
            ItineraryVersion.trip_id == trip_id,
            ItineraryVersion.plan_revision == plan_revision,
        )
        .order_by(ItineraryVersion.version_no.desc())
        .limit(1)
    )
    return await session.scalar(query)


async def current_warnings(
    session: AsyncSession, trip_id: UUID, plan_revision: int
) -> list[ItineraryWarning]:
    query = (
        select(ItineraryWarning)
        .where(
            ItineraryWarning.trip_id == trip_id,
            ItineraryWarning.plan_revision == plan_revision,
        )
        .order_by(ItineraryWarning.day_number.nulls_first(), ItineraryWarning.created_at)
    )
    return list(await session.scalars(query))


async def version_for_trip(
    session: AsyncSession, trip_id: UUID, version_id: UUID
) -> ItineraryVersion | None:
    query = select(ItineraryVersion).where(
        ItineraryVersion.id == version_id, ItineraryVersion.trip_id == trip_id
    )
    return await session.scalar(query)


async def latest_completed_generation(session: AsyncSession, trip_id: UUID) -> AiGeneration | None:
    query = (
        select(AiGeneration)
        .where(AiGeneration.trip_id == trip_id, AiGeneration.status == "completed")
        .order_by(AiGeneration.completed_at.desc().nulls_last(), AiGeneration.created_at.desc())
        .limit(1)
    )
    return await session.scalar(query)


async def latest_itinerary_for_user(
    session: AsyncSession, user_id: UUID
) -> tuple[UUID, int, datetime] | None:
    """The caller's trip whose itinerary changed most recently (latest version created_at)."""
    changed = func.max(ItineraryVersion.created_at)
    query = (
        select(Trip.id, Trip.plan_revision, changed)
        .join(ItineraryVersion, ItineraryVersion.trip_id == Trip.id)
        .where(Trip.user_id == user_id, Trip.deleted_at.is_(None))
        .group_by(Trip.id, Trip.plan_revision)
        .order_by(changed.desc(), Trip.id)
        .limit(1)
    )
    row = (await session.execute(query)).first()
    return None if row is None else (row[0], row[1], row[2])
