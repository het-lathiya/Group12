"""Itinerary versions (IMP-610; §5.2 snap-1, §5.8, §6.6.5 API-24 ``version_id`` and API-36 to
API-38; IMD-18, IMD-23; Amendment A1 §5.5).

A version holds a ``snap-1`` snapshot: days and items with locks, notes and ``source_chunk_ids``,
the budget settings and the plan_revision, never costs, travel or findings. Reading a version
prices the snapshot with the budget engine and runs the validator on it, and writes nothing.
``snapshot_before_regeneration`` is the hook IMP-607 calls when a regeneration job starts.
API-36 to API-38 and version reads answer 404 while the 'versions' switch is off (IMD-11).
"""

from datetime import time, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.budget import engine
from app.core.config import get_settings
from app.core.errors import (
    Conflict,
    EndpointNotImplemented,
    GenerationInProgress,
    NotFound,
    StalePlan,
)
from app.core.flags import is_enabled
from app.db.models import AiGeneration, ItineraryDay, ItineraryItem, ItineraryVersion, Place
from app.itinerary import repository, service
from app.itinerary.schemas import (
    ItineraryOut,
    ItinerarySource,
    VersionCreateIn,
    VersionOut,
)
from app.trips import service as trips_service
from app.validation import validator
from app.validation.schemas import Finding

NAME_TAKEN = "A version with this name already exists for this trip."


def _versions_enabled() -> None:
    if not is_enabled(get_settings(), "versions"):
        raise NotFound()  # IMD-11: a switched-off feature's routes answer 404


def version_out(row: ItineraryVersion) -> VersionOut:
    summary = row.validation_summary
    return VersionOut.model_validate(
        {
            "id": row.id,
            "version_no": row.version_no,
            "name": row.name,
            "reason": row.reason,
            "kind": "named" if row.name else "automatic",
            "plan_revision": row.plan_revision,
            "validation_summary": {
                key: summary.get(key, 0) for key in ("errors", "warnings", "infos")
            },
            "generation_id": row.generation_id,
            "created_at": row.created_at,
        }
    )


async def current_snapshot(
    session: AsyncSession, trip_id: UUID, plan_revision: int
) -> dict[str, Any]:
    """The stored plan as snap-1 (§5.2): no costs, travel or findings; citations as strings."""
    days = await repository.plan_days(session, trip_id)
    rows = await repository.plan_items(session, trip_id)
    items: dict[UUID, list[dict[str, Any]]] = {day.id: [] for day in days}
    for item, _, _ in rows:
        items[item.day_id].append(
            {
                "place_id": str(item.place_id),
                "position": item.position,
                "slot_type": item.slot_type,
                "start_time": item.start_time.strftime("%H:%M"),
                "duration_min": item.duration_min,
                "origin": item.origin,
                "note": item.note,
                "note_origin": item.note_origin,
                "is_locked": item.is_locked,
                "source_chunk_ids": [str(chunk_id) for chunk_id in item.source_chunk_ids],
            }
        )
    return {
        "schema": service.SNAPSHOT_SCHEMA,
        "plan_revision": plan_revision,
        "days": [
            {
                "day_number": day.day_number,
                "plan_date": day.plan_date.isoformat(),
                "theme": day.theme,
                "items": items[day.id],
            }
            for day in days
        ],
        "budget_settings": await repository.budget_settings_snapshot(session, trip_id),
    }


async def _summary_of_current(
    session: AsyncSession, trip_id: UUID, plan_revision: int
) -> dict[str, int]:
    """Counts of the stored warnings of the current revision (what a snapshot of it shows)."""
    findings = await service.stored_findings(session, trip_id, plan_revision)
    return {
        key: sum(finding.severity == severity for finding in findings)
        for severity, key in validator.SEVERITY_KEYS.items()
    }


async def snapshot_current(
    session: AsyncSession,
    trip_id: UUID,
    user_id: UUID,
    plan_revision: int,
    *,
    reason: str,
    name: str | None = None,
) -> ItineraryVersion:
    """Write a version of the stored plan; the caller holds the trip lock (version_no = max + 1)."""
    return await repository.insert_version(
        session,
        trip_id,
        reason=reason,
        name=name,
        plan_revision=plan_revision,
        snapshot=await current_snapshot(session, trip_id, plan_revision),
        validation_summary=await _summary_of_current(session, trip_id, plan_revision),
        generation_id=None,
        created_by=user_id,
    )


async def snapshot_before_regeneration(
    session: AsyncSession, user_id: UUID, trip_id: UUID
) -> ItineraryVersion:
    """IMP-607 calls this when a regeneration job starts (reason regeneration, always, also with
    the 'versions' switch off; FR-095 AC1). The caller has locked the trip and holds the plan."""
    trip = await repository.lock_trip(session, trip_id, user_id)
    if trip is None:
        raise NotFound()
    return await snapshot_current(
        session, trip_id, user_id, trip.plan_revision, reason="regeneration"
    )


async def list_versions(session: AsyncSession, user_id: UUID, trip_id: UUID) -> list[VersionOut]:
    """API-36: the trip's versions, newest first."""
    _versions_enabled()
    await trips_service.get_trip(session, user_id, trip_id)
    return [version_out(row) for row in await repository.list_versions(session, trip_id)]


async def _locked_for_change(
    session: AsyncSession, user_id: UUID, trip_id: UUID, plan_revision: int
) -> None:
    """§5.8: lock the trip; refuse while a generation runs (IMD-23), then check the revision."""
    trip = await repository.lock_trip(session, trip_id, user_id)
    if trip is None:
        raise NotFound()
    if await repository.generation_active(session, trip_id):
        raise GenerationInProgress()
    if plan_revision != trip.plan_revision:
        raise StalePlan()
    if not await repository.plan_days(session, trip_id):
        raise NotFound(service.NO_ITINERARY)


async def save_named(
    session: AsyncSession, user_id: UUID, trip_id: UUID, body: VersionCreateIn
) -> VersionOut:
    """API-37: save the current plan as a named version (reason manual, IMD-18)."""
    _versions_enabled()
    await _locked_for_change(session, user_id, trip_id, body.plan_revision)
    if await repository.version_name_taken(session, trip_id, body.name):
        raise Conflict(NAME_TAKEN)
    row = await snapshot_current(
        session, trip_id, user_id, body.plan_revision, reason="manual", name=body.name
    )
    return version_out(row)


async def restore(
    session: AsyncSession, user_id: UUID, trip_id: UUID, version_id: UUID, plan_revision: int
) -> ItineraryOut:
    """API-38: restore a version as the new current plan."""
    _versions_enabled()
    await _locked_for_change(session, user_id, trip_id, plan_revision)
    if await repository.version_for_trip(session, trip_id, version_id) is None:
        raise NotFound()
    raise EndpointNotImplemented()  # the restore transaction is the second part of IMP-610


async def read_version(
    session: AsyncSession, user_id: UUID, trip_id: UUID, version_id: UUID
) -> ItineraryOut:
    """API-24 with version_id: the snapshot priced and validated on read, nothing written
    (IMD-18). Travel is not stored in a snapshot, so a preview shows none; a restore
    recalculates it."""
    _versions_enabled()
    trip = await trips_service.get_trip(session, user_id, trip_id)
    version = await repository.version_for_trip(session, trip_id, version_id)
    if version is None:
        raise NotFound()
    prefs = await trips_service.get_preferences(session, user_id, trip_id)
    must_visit = set(prefs.must_visit_place_ids)
    snap_days = version.snapshot.get("days", [])
    place_ids = {UUID(item["place_id"]) for day in snap_days for item in day["items"]}
    places = {place.id: place for place in await repository.places_by_ids(session, place_ids)}
    currency = service.trip_currency(trip)

    # Transient rows, never added to the session.
    days: list[ItineraryDay] = []
    rows: list[tuple[ItineraryItem, Place, bool]] = []
    refs: dict[str, UUID] = {}
    for snap_day in sorted(snap_days, key=lambda day: day["day_number"]):
        day = ItineraryDay(
            id=uuid4(),
            trip_id=trip_id,
            day_number=snap_day["day_number"],
            plan_date=trip.start_date + timedelta(days=snap_day["day_number"] - 1),
            theme=snap_day.get("theme"),
        )
        days.append(day)
        for position, snap_item in enumerate(snap_day["items"], start=1):
            place = places.get(UUID(snap_item["place_id"]))
            if place is None:  # shortcut: a place removed from the data drops out of the preview
                continue
            cost = engine.item_cost(
                place, adults=trip.adults, children=trip.children, currency=currency
            )
            item = ItineraryItem(
                id=uuid4(),
                trip_id=trip_id,
                day_id=day.id,
                place_id=place.id,
                position=position,
                slot_type=snap_item["slot_type"],
                start_time=time.fromisoformat(snap_item["start_time"]),
                duration_min=snap_item["duration_min"],
                origin=snap_item["origin"],
                note=snap_item.get("note"),
                note_origin=snap_item.get("note_origin", "none"),
                is_locked=snap_item.get("is_locked", False),
                cost_min=None if cost.lo is None else engine.from_minor(cost.lo),
                cost_max=None if cost.hi is None else engine.from_minor(cost.hi),
                cost_currency=currency,
                cost_label=cost.label,
                # A1 §5.5: a snapshot without citations reads as an empty list.
                source_chunk_ids=[UUID(c) for c in snap_item.get("source_chunk_ids", [])],
            )
            refs[f"d{day.day_number}-i{position}"] = item.id
            rows.append((item, place, place.id in must_visit))

    planned = service.planned_days(days, rows)
    ctx = await service.validation_context(
        session, user_id, trip, [item.place_id for day in planned for item in day.items]
    )
    findings = [
        Finding(
            id=uuid4(),
            code=found.code,
            severity=found.severity,
            message=found.message,
            day_number=found.day_number,
            item_id=refs.get(found.item_ref) if found.item_ref else None,
            place_id=found.place_id,
            suggested_fix=found.suggested_fix,
        )
        for found in validator.validate(planned, ctx)
    ]
    generation = (
        await session.get(AiGeneration, version.generation_id)
        if version.generation_id
        else await repository.latest_completed_generation(session, trip_id)
    )
    out_days, totals = await service.plan_out(session, trip, days, rows, generation)
    return ItineraryOut(
        trip_id=trip.id,
        plan_revision=version.plan_revision,
        version_id=version.id,
        is_current=False,
        plan_stale=trip.plan_stale,
        source=None
        if generation is None
        else ItinerarySource.model_validate(
            {
                "generation_id": generation.id,
                "provider": generation.provider,
                "outcome": generation.outcome,
            }
        ),
        days=out_days,
        findings=findings,
        totals=totals,
    )
