"""Trip routes API-07, API-08, API-10 to API-15 (specification §6.6.2; FR-005,
FR-007 to FR-010, FR-013), and the saved places API-19 to API-21 (§6.6.3; FR-020, IMP-605).

API-12 and API-13 (IMP-602) sit behind the trip_management switch (IMD-11).

Mounted under /api/v1, whose router requires CurrentUser (IMP-108); the user comes from the token.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from app.auth.deps import CurrentUser, DbSession
from app.itinerary import service as itinerary_service
from app.places.schemas import PlaceSummary
from app.schemas.common import Page
from app.trips import service
from app.trips.schemas import PreferencesIn, PreferencesOut, TripIn, TripOut, TripPatch

router = APIRouter(prefix="/trips", tags=["trips"])


@router.post(
    "",
    response_model=TripOut,
    status_code=status.HTTP_201_CREATED,
    summary="API-07 Create a draft trip",
)
async def create_trip(body: TripIn, user: CurrentUser, session: DbSession) -> TripOut:
    return await service.create_trip(session, user.user_id, body)


@router.get("", response_model=Page[TripOut], summary="API-08 List my trips")
async def list_trips(
    user: CurrentUser,
    session: DbSession,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    include_archived: bool = False,
) -> Page[TripOut]:
    return await service.list_trips(
        session, user.user_id, limit=limit, offset=offset, include_archived=include_archived
    )


@router.get("/{trip_id}", response_model=TripOut, summary="API-10 Read one of my trips")
async def get_trip(trip_id: UUID, user: CurrentUser, session: DbSession) -> TripOut:
    return await service.get_trip(session, user.user_id, trip_id)


@router.patch("/{trip_id}", response_model=TripOut, summary="API-11 Update one of my trips")
async def update_trip(
    trip_id: UUID, body: TripPatch, user: CurrentUser, session: DbSession
) -> TripOut:
    return await service.update_trip(session, user.user_id, trip_id, body)


@router.delete(
    "/{trip_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="API-12 Delete one of my trips",
)
async def delete_trip(trip_id: UUID, user: CurrentUser, session: DbSession) -> None:
    await service.delete_trip(session, user.user_id, trip_id)


@router.post(
    "/{trip_id}/duplicate",
    response_model=TripOut,
    status_code=status.HTTP_201_CREATED,
    summary="API-13 Duplicate one of my trips",
)
async def duplicate_trip(trip_id: UUID, user: CurrentUser, session: DbSession) -> TripOut:
    return await service.duplicate_trip(
        session, user.user_id, trip_id, copy_plan=itinerary_service.copy_plan
    )


@router.put(
    "/{trip_id}/preferences",
    response_model=PreferencesOut,
    summary="API-14 Save my trip's preferences and must-visit places",
)
async def save_preferences(
    trip_id: UUID, body: PreferencesIn, user: CurrentUser, session: DbSession
) -> PreferencesOut:
    return await service.save_preferences(session, user.user_id, trip_id, body)


@router.get(
    "/{trip_id}/preferences",
    response_model=PreferencesOut,
    summary="API-15 Read my trip's preferences",
)
async def get_preferences(trip_id: UUID, user: CurrentUser, session: DbSession) -> PreferencesOut:
    return await service.get_preferences(session, user.user_id, trip_id)


# IMP-605 saved places (API-19 to API-21; FR-020), switch `wishlist` (IMD-11).


@router.put(
    "/{trip_id}/saved-places/{place_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="API-19 Save a place to my trip",
)
async def save_place(trip_id: UUID, place_id: UUID, user: CurrentUser, session: DbSession) -> None:
    await service.save_place(session, user.user_id, trip_id, place_id)


@router.delete(
    "/{trip_id}/saved-places/{place_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="API-20 Remove a saved place from my trip",
)
async def unsave_place(
    trip_id: UUID, place_id: UUID, user: CurrentUser, session: DbSession
) -> None:
    await service.unsave_place(session, user.user_id, trip_id, place_id)


@router.get(
    "/{trip_id}/saved-places",
    response_model=list[PlaceSummary],
    summary="API-21 List my trip's saved places",
)
async def list_saved_places(
    trip_id: UUID, user: CurrentUser, session: DbSession
) -> list[PlaceSummary]:
    return await service.list_saved_places(session, user.user_id, trip_id)
