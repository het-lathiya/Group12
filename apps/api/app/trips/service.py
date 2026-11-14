"""Trip service (MOD-B03): create, list, read and update the caller's trips (API-07, API-08,
API-10, API-11) and save and read their preferences and must-visit places (API-14, API-15).

Drafts (FR-013, IMP-410): API-07 stores a draft as soon as the wizard's Details step is left;
API-11 and API-14 save each later step. A draft becomes ready when its preferences are saved
(IMD-25), so preferences are required only for the move to ready.

The session is the request's single transaction (app.auth.deps.DbSession): API-07 inserts the trip
and its default budget_settings row in it, so both are saved or neither is.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.budget import repository as budget_repository
from app.core.errors import Conflict, NotFound, ValidationFailed
from app.db.models import Trip
from app.places import service as places_service
from app.schemas.common import ErrorDetail, Money, Page
from app.trips import domain, preference_mapping, repository
from app.trips.repository import TripRow
from app.trips.schemas import (
    MustVisitPlace,
    PreferenceEffect,
    PreferencesIn,
    PreferencesOut,
    TripDestination,
    TripIn,
    TripOut,
    TripPatch,
    TripStatus,
)


def _to_draft(body: TripIn) -> domain.TripDraft:
    return domain.TripDraft(
        title=body.title,
        destination_id=body.destination_id,
        start_date=body.start_date,
        end_date=body.end_date,
        adults=body.adults,
        children=body.children,
        group_needs=[need.value for need in body.group_needs],
        budget_amount=body.budget.amount if body.budget else None,
        budget_currency=body.budget.currency if body.budget else None,
    )


def _stored_draft(trip: Trip) -> domain.TripDraft:
    return domain.TripDraft(
        title=trip.title,
        destination_id=trip.destination_id,
        start_date=trip.start_date,
        end_date=trip.end_date,
        adults=trip.adults,
        children=trip.children,
        group_needs=list(trip.group_needs),
        budget_amount=trip.budget_amount,
        budget_currency=trip.budget_currency,
    )


def _to_out(row: TripRow) -> TripOut:
    trip, destination = row.trip, row.destination
    budget = None
    if trip.budget_amount is not None and trip.budget_currency is not None:
        budget = Money(amount=trip.budget_amount, currency=trip.budget_currency)
    return TripOut.model_validate(
        {
            "id": trip.id,
            "title": trip.title,
            "destination_id": trip.destination_id,
            "start_date": trip.start_date,
            "end_date": trip.end_date,
            "num_days": trip.num_days,
            "adults": trip.adults,
            "children": trip.children,
            "group_needs": trip.group_needs,
            "budget": budget,
            "status": trip.status,
            "plan_revision": trip.plan_revision,
            "plan_stale": trip.plan_stale,
            "has_itinerary": row.has_itinerary,
            "destination": TripDestination(
                id=destination.id,
                name=destination.name,
                timezone=destination.timezone,
                currency=destination.currency,
                is_sample=destination.is_sample,
            ),
            "created_at": trip.created_at,
            "updated_at": trip.updated_at,
        }
    )


async def _validate(session: AsyncSession, draft: domain.TripDraft) -> None:
    """The API-07 field rules, shared by API-11 (§6.6.2: the same validation as API-07)."""
    supported = [
        domain.SupportedDestination(id=d.id, name=d.name, currency=d.currency)
        for d in await repository.active_destinations(session)
    ]
    chosen = next((d for d in supported if d.id == draft.destination_id), None)
    errors = [
        *domain.validate_trip(draft),
        *domain.validate_destination(draft.destination_id, supported),
        *(domain.validate_budget_currency(draft.budget_currency, chosen) if chosen else []),
    ]
    if errors:
        raise ValidationFailed(
            details=[ErrorDetail(field=e.field, message=e.message) for e in errors]
        )


async def create_trip(session: AsyncSession, user_id: UUID, body: TripIn) -> TripOut:
    draft = _to_draft(body)
    await _validate(session, draft)
    trip_id = await repository.insert_trip(
        session,
        user_id,
        title=draft.title.strip(),
        destination_id=draft.destination_id,
        start_date=draft.start_date,
        end_date=draft.end_date,
        adults=draft.adults,
        children=draft.children,
        group_needs=list(draft.group_needs),
        budget_amount=draft.budget_amount,
        budget_currency=draft.budget_currency,
    )
    # Default settings (contingency 10 %, no allowances); no trip_preferences row (IMD-25).
    await budget_repository.upsert_settings(session, trip_id)
    return await get_trip(session, user_id, trip_id)


async def get_trip(session: AsyncSession, user_id: UUID, trip_id: UUID) -> TripOut:
    row = await repository.get_owned(session, user_id, trip_id)
    if row is None:
        # Missing, soft-deleted or another user's: the same 404 (FR-005 AC1).
        raise NotFound()
    return _to_out(row)


async def update_trip(
    session: AsyncSession, user_id: UUID, trip_id: UUID, body: TripPatch
) -> TripOut:
    """API-11: change the fields sent (a wizard step of a draft, FR-013), archive or restore."""
    row = await _owned(session, user_id, trip_id)
    trip = row.trip
    sent = body.model_fields_set
    changes = sent - {"status"}
    if trip.status == "archived" and changes:
        raise Conflict("This trip is archived. Restore it before changing it.")

    values: dict[str, object] = {}
    if changes:
        # A budget sent as null clears it; a budget left out keeps the stored one.
        if "budget" in sent:
            amount = body.budget.amount if body.budget else None
            currency = body.budget.currency if body.budget else None
        else:
            amount, currency = trip.budget_amount, trip.budget_currency
        draft = domain.TripDraft(
            title=body.title if body.title is not None else trip.title,
            destination_id=body.destination_id or trip.destination_id,
            start_date=body.start_date or trip.start_date,
            end_date=body.end_date or trip.end_date,
            adults=body.adults if body.adults is not None else trip.adults,
            children=body.children if body.children is not None else trip.children,
            group_needs=(
                [need.value for need in body.group_needs]
                if body.group_needs is not None
                else list(trip.group_needs)
            ),
            budget_amount=amount,
            budget_currency=currency,
        )
        await _validate(session, draft)
        values = {
            "title": draft.title.strip(),
            "destination_id": draft.destination_id,
            "start_date": draft.start_date,
            "end_date": draft.end_date,
            "adults": draft.adults,
            "children": draft.children,
            "group_needs": list(draft.group_needs),
            "budget_amount": draft.budget_amount,
            "budget_currency": draft.budget_currency,
        }
        # FR-011: dates, travellers, budget or destination changed; items outside new dates are
        # left for the validator to report as OUTSIDE_TRIP_DATES.
        if row.has_itinerary and domain.plan_affected(_stored_draft(trip), draft):
            values["plan_stale"] = True
    if body.status == TripStatus.ARCHIVED:
        values["status"] = "archived"
    elif body.status == TripStatus.READY and trip.status == "archived":
        # §5.4: a restored trip is ready if it has days, otherwise a draft again.
        values["status"] = "ready" if row.has_itinerary else "draft"
    if values:
        await repository.update_trip(session, trip_id, values)
    return await get_trip(session, user_id, trip_id)


async def list_trips(
    session: AsyncSession, user_id: UUID, *, limit: int, offset: int, include_archived: bool
) -> Page[TripOut]:
    rows, total = await repository.list_owned(
        session, user_id, limit=limit, offset=offset, include_archived=include_archived
    )
    return Page[TripOut](items=[_to_out(r) for r in rows], total=total, limit=limit, offset=offset)


async def _owned(session: AsyncSession, user_id: UUID, trip_id: UUID) -> TripRow:
    row = await repository.get_owned(session, user_id, trip_id)
    if row is None:
        raise NotFound()
    return row


async def get_preferences(session: AsyncSession, user_id: UUID, trip_id: UUID) -> PreferencesOut:
    """API-15: the stored preferences, or the defaults with saved false when none exist."""
    trip = (await _owned(session, user_id, trip_id)).trip
    stored = await repository.get_preferences(session, trip_id)
    place_ids = await repository.must_visit_place_ids(session, trip_id)
    names = await places_service.active_place_names(session, trip.destination_id, place_ids)
    # Ordered by place name; a must-visit place that was deactivated later keeps its id but has
    # no entry in must_visit_places.
    ordered = [*names, *(place_id for place_id in place_ids if place_id not in names)]
    defaults = preference_mapping.Preferences()
    return PreferencesOut.model_validate(
        {
            "interests": stored.interests if stored else list(defaults.interests),
            "pace": stored.pace if stored else defaults.pace,
            "budget_priority": stored.budget_priority if stored else defaults.budget_priority,
            "transport_pref": stored.transport_pref if stored else defaults.transport_pref,
            "accommodation_type": (
                stored.accommodation_type if stored else defaults.accommodation_type
            ),
            "step_free_required": (
                stored.step_free_required if stored else defaults.step_free_required
            ),
            "notes": stored.notes if stored else None,
            "must_visit_place_ids": ordered,
            "must_visit_places": [MustVisitPlace(id=pid, name=name) for pid, name in names.items()],
            "effects": [
                PreferenceEffect(field=name, effect=effect)
                for name, effect in preference_mapping.field_effects()
            ],
            "saved": stored is not None,
        }
    )


async def save_preferences(
    session: AsyncSession, user_id: UUID, trip_id: UUID, body: PreferencesIn
) -> PreferencesOut:
    """API-14 in the request's single transaction: preferences, must-visit set and trip state."""
    row = await _owned(session, user_id, trip_id)
    trip = row.trip
    if trip.status == "archived":
        raise Conflict("This trip is archived. Restore it before changing it.")

    wanted = list(body.must_visit_place_ids)
    found = await places_service.active_place_names(session, trip.destination_id, wanted)
    errors = [
        ErrorDetail(
            field=f"must_visit_place_ids.{index}",
            message=f"Place {place_id} is not an active place of this trip's destination.",
        )
        for index, place_id in enumerate(wanted)
        if place_id not in found
    ]
    if errors:
        raise ValidationFailed(details=errors)

    values = {
        "interests": [interest.value for interest in body.interests],
        "pace": body.pace.value,
        "budget_priority": body.budget_priority.value,
        "transport_pref": body.transport_pref.value,
        "accommodation_type": body.accommodation_type.value,
        "step_free_required": body.step_free_required,
        "notes": body.notes,
    }
    stored = await repository.get_preferences(session, trip_id)
    # FR-011: only a real change flags the plan; the edit page resending the same values does not.
    changed = (
        stored is None
        or any(getattr(stored, name) != value for name, value in values.items())
        or set(await repository.must_visit_place_ids(session, trip_id)) != set(wanted)
    )
    await repository.upsert_preferences(session, trip_id, values)
    await repository.replace_must_visit(session, trip_id, wanted)
    await repository.mark_preferences_saved(
        session,
        trip_id,
        make_ready=trip.status == "draft",
        make_stale=row.has_itinerary and changed,
    )
    return await get_preferences(session, user_id, trip_id)
