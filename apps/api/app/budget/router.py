"""Cost routes API-33 and API-34 (specification §6.6.6; FR-071 to FR-075).

API-33 is built by IMP-308, API-34 by IMP-411.
"""

from uuid import UUID

from fastapi import APIRouter

from app.auth.deps import CurrentUser, DbSession
from app.budget import service
from app.budget.schemas import BudgetSettingsPatch, CostSummaryOut

router = APIRouter(prefix="/trips/{trip_id}", tags=["costs"])


@router.get("/costs", response_model=CostSummaryOut, summary="API-33 Read my trip's costs")
async def get_costs(trip_id: UUID, user: CurrentUser, session: DbSession) -> CostSummaryOut:
    return await service.get_costs(session, user.user_id, trip_id)


@router.patch(
    "/budget-settings",
    response_model=CostSummaryOut,
    summary="API-34 Update my trip's budget settings",
)
async def update_budget_settings(
    trip_id: UUID, body: BudgetSettingsPatch, user: CurrentUser, session: DbSession
) -> CostSummaryOut:
    return await service.update_budget_settings(session, user.user_id, trip_id, body)
