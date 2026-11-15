"""Itinerary, edit and version routes API-09, API-24 to API-29 and API-35 to API-38
(specification §6.6.5; IMD-18, IMD-23).

API-09 and API-24 to API-29 are built (IMP-211, IMP-309, IMP-408, IMP-504, IMP-505; API-28 and
API-29 answer 404 while the 'alternatives' switch is off, IMD-11). API-35 is IMP-609: its costs are
API-33's answer from the budget service, passed to the itinerary service's projection.
API-36 to API-38 and API-24 with version_id are IMP-610 (app/itinerary/versions.py, switch
'versions').
API-30 and API-31 live in generation/router.py and API-32 in validation/router.py (IMD-13).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.auth.deps import CurrentUser, DbSession
from app.budget import service as budget_service
from app.core.rate_limit import expensive_request
from app.itinerary import edits, service, versions
from app.itinerary.schemas import (
    AlternativesOut,
    EditResultOut,
    ItemAddIn,
    ItemPatchIn,
    ItineraryOut,
    LatestItineraryOut,
    PlanRevisionIn,
    ReplaceIn,
    TripSummaryOut,
    VersionCreateIn,
    VersionOut,
)

router = APIRouter(tags=["itinerary"])


@router.get(
    "/itineraries/latest",
    response_model=LatestItineraryOut,
    summary="API-09 Find my most recently changed itinerary",
)
async def latest_itinerary(user: CurrentUser, session: DbSession) -> LatestItineraryOut:
    return await service.latest_itinerary(session, user.user_id)


@router.get(
    "/trips/{trip_id}/itinerary",
    response_model=ItineraryOut,
    summary="API-24 Read my trip's itinerary",
)
async def get_itinerary(
    trip_id: UUID, user: CurrentUser, session: DbSession, version_id: UUID | None = None
) -> ItineraryOut:
    if version_id is not None:
        return await versions.read_version(session, user.user_id, trip_id, version_id)
    return await service.get_itinerary(session, user.user_id, trip_id)


@router.post(
    "/trips/{trip_id}/itinerary/items",
    response_model=EditResultOut,
    dependencies=[Depends(expensive_request)],
    summary="API-25 Add a place to a day",
)
async def add_item(
    trip_id: UUID, body: ItemAddIn, user: CurrentUser, session: DbSession
) -> EditResultOut:
    return await edits.add_item(session, user.user_id, trip_id, body)


@router.patch(
    "/itinerary/items/{item_id}",
    response_model=EditResultOut,
    dependencies=[Depends(expensive_request)],
    summary="API-26 Move, retime, lock or unlock an item",
)
async def update_item(
    item_id: UUID, body: ItemPatchIn, user: CurrentUser, session: DbSession
) -> EditResultOut:
    return await edits.patch_item(session, user.user_id, item_id, body)


@router.delete(
    "/itinerary/items/{item_id}",
    response_model=EditResultOut,
    dependencies=[Depends(expensive_request)],
    summary="API-27 Remove an item",
)
async def delete_item(
    item_id: UUID, plan_revision: int, user: CurrentUser, session: DbSession
) -> EditResultOut:
    return await edits.remove_item(session, user.user_id, item_id, plan_revision)


@router.get(
    "/itinerary/items/{item_id}/alternatives",
    response_model=AlternativesOut,
    dependencies=[Depends(expensive_request)],
    summary="API-28 List alternatives for an item",
)
async def list_alternatives(
    item_id: UUID, user: CurrentUser, session: DbSession
) -> AlternativesOut:
    return await edits.alternatives(session, user.user_id, item_id)


@router.post(
    "/itinerary/items/{item_id}/replace",
    response_model=EditResultOut,
    dependencies=[Depends(expensive_request)],
    summary="API-29 Replace an item with an alternative",
)
async def replace_item(
    item_id: UUID, body: ReplaceIn, user: CurrentUser, session: DbSession
) -> EditResultOut:
    return await edits.replace_item(session, user.user_id, item_id, body)


@router.get(
    "/trips/{trip_id}/summary",
    response_model=TripSummaryOut,
    summary="API-35 Read my trip's printable summary",
)
async def trip_summary(trip_id: UUID, user: CurrentUser, session: DbSession) -> TripSummaryOut:
    costs = await budget_service.get_costs(session, user.user_id, trip_id)
    return await service.trip_summary(session, user.user_id, trip_id, costs)


@router.get(
    "/trips/{trip_id}/versions",
    response_model=list[VersionOut],
    summary="API-36 List my trip's saved versions",
)
async def list_versions(trip_id: UUID, user: CurrentUser, session: DbSession) -> list[VersionOut]:
    return await versions.list_versions(session, user.user_id, trip_id)


@router.post(
    "/trips/{trip_id}/versions",
    response_model=VersionOut,
    status_code=status.HTTP_201_CREATED,
    summary="API-37 Save a named version",
)
async def create_version(
    trip_id: UUID, body: VersionCreateIn, user: CurrentUser, session: DbSession
) -> VersionOut:
    return await versions.save_named(session, user.user_id, trip_id, body)


@router.post(
    "/trips/{trip_id}/versions/{version_id}/restore",
    response_model=ItineraryOut,
    summary="API-38 Restore a saved version",
)
async def restore_version(
    trip_id: UUID, version_id: UUID, body: PlanRevisionIn, user: CurrentUser, session: DbSession
) -> ItineraryOut:
    return await versions.restore(session, user.user_id, trip_id, version_id, body.plan_revision)
