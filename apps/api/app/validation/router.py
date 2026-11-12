"""API-32, revalidate a trip's itinerary (§6.6.5; IMD-13 places it here, IMP-405).

The plan is read and its warnings written by the itinerary service, the tables' only writer (§3).
"""

from uuid import UUID

from fastapi import APIRouter

from app.auth.deps import CurrentUser, DbSession
from app.itinerary import service as itinerary_service
from app.itinerary.schemas import PlanRevisionIn, ValidateOut

router = APIRouter(tags=["itinerary"])


@router.post(
    "/trips/{trip_id}/itinerary/validate",
    response_model=ValidateOut,
    summary="API-32 Revalidate my trip's itinerary",
)
async def validate_itinerary(
    trip_id: UUID, body: PlanRevisionIn, user: CurrentUser, session: DbSession
) -> ValidateOut:
    return await itinerary_service.revalidate(session, user.user_id, trip_id, body.plan_revision)
