"""API-33 and API-34 (§6.6.6; FR-071, FR-072, FR-076, IMD-05): the trip's costs, computed on read.

API-34 writes budget_settings only; itinerary_warnings and plan_revision are left as they are.

The engine runs in ``itinerary.service.cost_summary``, which API-24's totals share. This module
turns its minor units into the declared ``CostSummaryOut``.
"""

from typing import Final
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy.ext.asyncio import AsyncSession

from app.budget import engine, repository
from app.budget.schemas import (
    AmountRange,
    BudgetSettingsOut,
    BudgetSettingsPatch,
    BudgetStatus,
    CategoryCostLine,
    Contingency,
    CostSummaryOut,
    DayCostLine,
    PerTraveller,
)
from app.core.config import get_settings
from app.core.errors import Conflict, ValidationFailed
from app.core.flags import is_enabled
from app.itinerary import service as itinerary_service
from app.schemas.common import ErrorDetail
from app.trips import service as trips_service
from app.validation.schemas import Finding

BUDGET_ALERTS: Final = frozenset({"BUDGET_NEAR", "BUDGET_EXCEEDED"})


def _alert(trip_id: UUID, alert: engine.Alert) -> Finding:
    """Alerts are not stored, so the ID is derived: the same alert keeps the same ID."""
    return Finding(
        id=uuid5(NAMESPACE_URL, f"{trip_id}/{alert.code}"),
        code=alert.code,
        severity=alert.severity,
        message=alert.message,
        day_number=None,
        item_id=None,
        place_id=None,
        suggested_fix=None,
    )


async def get_costs(session: AsyncSession, user_id: UUID, trip_id: UUID) -> CostSummaryOut:
    trip = await trips_service.get_trip(session, user_id, trip_id)
    settings = await repository.get_settings(session, trip_id)
    summary, pct = await itinerary_service.cost_summary(session, trip)
    money = engine.from_minor
    alerts_on = is_enabled(get_settings(), "budget_alerts")
    stored_pct = settings.contingency_pct if settings else itinerary_service.DEFAULT_CONTINGENCY_PCT
    return CostSummaryOut(
        currency=itinerary_service.trip_currency(trip),
        estimate=AmountRange(min=money(summary.estimate_lo), max=money(summary.estimate_hi)),
        contingency=Contingency(pct=pct, amount=money(summary.contingency)),
        planning_total=money(summary.planning_total),
        per_traveller=PerTraveller(
            travellers=summary.travellers,
            largest_share=money(summary.largest_share),
            label="average",
        ),
        budget=BudgetStatus(
            amount=trip.budget.amount if trip.budget else None,
            status=summary.status,
            ratio_pct=summary.ratio_pct,
            excess=None if summary.excess is None else money(summary.excess),
        ),
        by_day=[
            DayCostLine(
                day_number=line.day_number,
                min=money(line.lo),
                max=money(line.hi),
                contingency_share=money(line.contingency_share),
            )
            for line in summary.by_day
        ],
        by_category=[
            CategoryCostLine(
                category=line.category, min=money(line.lo), max=money(line.hi), label=line.label
            )
            for line in summary.by_category
        ],
        alerts=[
            _alert(trip_id, alert)
            for alert in summary.alerts
            if alerts_on and alert.code in BUDGET_ALERTS
        ],
        complete=summary.complete,
        incomplete_items=summary.incomplete_items,
        settings=BudgetSettingsOut(
            transport_allowance_per_day=settings.transport_allowance_per_day if settings else None,
            stay_budget_per_night=settings.stay_budget_per_night if settings else None,
            contingency_pct=int(stored_pct),
        ),
    )


async def update_budget_settings(
    session: AsyncSession, user_id: UUID, trip_id: UUID, body: BudgetSettingsPatch
) -> CostSummaryOut:
    """API-34: save the fields sent (an allowance sent as null is cleared), return the costs."""
    trip = await trips_service.get_trip(session, user_id, trip_id)  # 404 for another user's
    if trip.status == "archived":
        raise Conflict("This trip is archived. Restore it before changing it.")
    values = {name: getattr(body, name) for name in body.model_fields_set}  # Decimals, not strings
    if values.get("contingency_pct", 0) is None:
        del values["contingency_pct"]  # the column has no "not set": null leaves it unchanged
    if "contingency_pct" in values and not is_enabled(get_settings(), "contingency"):
        raise ValidationFailed(
            details=[ErrorDetail(field="contingency_pct", message="The contingency buffer is off.")]
        )
    await repository.save_settings(session, trip_id, values)
    return await get_costs(session, user_id, trip_id)
