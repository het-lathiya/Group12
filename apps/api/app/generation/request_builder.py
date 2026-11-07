"""Build the GenerationRequest of a trip (§8.6, A1 §6.8; FR-026, IMP-303, IMP-316).

``build_generation_request`` holds the allow-list: only the fields named here reach the provider.
Never sent: e-mail, name, user ID or trip title. A place description reaches the model only inside
a place passage (A1 §6.8). ``build`` reads the rows, takes its shortlist from
``retrieval.ranked_shortlist`` (IMP-305), and ``ground`` adds the passages when the template's
meta.json names gr-2. ``quote_notes`` is the only way notes enter the request.
"""

import re
import uuid
from collections.abc import Callable, Iterable, Sequence
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Final, Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.prompts import registry
from app.ai.providers.base import ModelProvider
from app.core.logging import redact_text
from app.db.models import PlaceOpeningHours
from app.generation import records, repository, retrieval
from app.places.schemas import PlaceSummary
from app.rag.constants import RAG_MAX_PASSAGES, RAG_TOP_K_PLACE
from app.rag.mmr import RetrievedChunk
from app.rag.service import RetrievalResult
from app.schemas.ai import (
    GROUNDED_INPUT_SCHEMA_VERSION,
    MAX_PASSAGE_TEXT_CHARS,
    MAX_PASSAGE_TITLE_CHARS,
    Budget,
    ContextPassage,
    GenerationRequest,
    GroundedGenerationRequest,
    Limits,
    LockedItem,
    Preferences,
    RetrievalInfo,
    Scope,
    ShortlistPlace,
    Suitability,
    Travellers,
    TripContext,
)
from app.trips import preference_mapping
from app.trips import service as trips_service
from app.trips.schemas import PreferencesOut, TripOut

DAY_START: Final = "09:00"
DAY_END: Final = "19:00"
MEAL_SLOTS: Final = ["lunch"]
NOTES_MAX: Final = 500
PHONE_MIN_DIGITS: Final = 9  # a date such as 2027-01-12 has 8 digits and is left alone
REDACTED: Final = "[redacted]"
WEEKDAY_NAMES: Final = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")  # ISO weekdays 1 to 7
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_PHONE = re.compile(r"(?<![\w.])\+?\(?\d[\d ().-]{6,}\d(?!\w)")


def _redact_phone(match: re.Match[str]) -> str:
    digits = sum(char.isdigit() for char in match.group())
    return REDACTED if digits >= PHONE_MIN_DIGITS else match.group()


def quote_notes(notes: str | None) -> str | None:
    """Control characters removed, e-mail addresses and phone numbers replaced by [redacted]
    (best effort), cut to 500 characters (§8.6)."""
    if not notes:
        return None
    return _PHONE.sub(_redact_phone, redact_text(_CONTROL.sub("", notes)))[:NOTES_MAX] or None


@dataclass(frozen=True)
class RequestSettings:
    prompt_template_id: str
    prompt_version: str
    contingency_pct: float
    scope: Scope = field(default_factory=lambda: Scope(kind="full", day_number=None))


def hours_summary(hours: Iterable[PlaceOpeningHours], weekdays: Sequence[int]) -> str:
    """The stored hours on the trip's weekdays, for example "Tue 09:00-17:00; Wed closed" (§8.6);
    empty when none is stored."""
    rows = list(hours)
    parts = []
    for weekday in weekdays:
        name = WEEKDAY_NAMES[weekday - 1]
        for row in (r for r in rows if r.weekday == weekday):
            if row.is_closed:
                parts.append(f"{name} closed")
            elif row.open_time is not None and row.close_time is not None:
                parts.append(f"{name} {row.open_time:%H:%M}-{row.close_time:%H:%M}")
    return "; ".join(parts)


def shortlist_place(place: PlaceSummary, hours: str = "") -> ShortlistPlace:
    """Only the place fields gr-1 needs; description and URLs stay out (§8.6)."""
    return ShortlistPlace(
        place_id=place.id,
        name=place.name,
        category=place.category.value,
        tags=[tag.value for tag in place.tags],
        lat=place.lat,
        lon=place.lon,
        typical_duration_min=place.typical_duration_min,
        price_min=f"{place.price.min:.2f}" if place.price else None,
        price_max=(
            f"{place.price.max:.2f}" if place.price and place.price.max is not None else None
        ),
        price_label=place.price_label.value,
        hours_summary=hours or f"hours {place.hours_label.value}",
        suitability=Suitability(
            step_free=place.suitability.step_free,
            child_friendly=place.suitability.child_friendly,
        ),
    )


def build_generation_request(
    trip: TripOut,
    preferences: PreferencesOut,
    must_visit: Sequence[UUID],
    locked_items: Sequence[LockedItem],
    shortlist: Sequence[ShortlistPlace],
    settings: RequestSettings,
) -> GenerationRequest:
    """The gr-1 fields; ``shortlist`` is in rank order, best first. Nothing here reads a row."""
    max_items, max_minutes = preference_mapping.PACE_LIMITS[
        preference_mapping.Pace(preferences.pace)
    ]
    return GenerationRequest(
        request_id=uuid.uuid4(),
        trip=TripContext(
            destination_id=trip.destination_id,
            start_date=trip.start_date,
            end_date=trip.end_date,
            num_days=trip.num_days,
            travellers=Travellers(adults=trip.adults, children=trip.children),
            group_needs=[need.value for need in trip.group_needs],
            budget=(
                Budget(amount=f"{trip.budget.amount:.2f}", currency=trip.budget.currency)
                if trip.budget
                else None
            ),
            contingency_pct=settings.contingency_pct,
        ),
        preferences=Preferences(
            interests=[interest.value for interest in preferences.interests],
            pace=preferences.pace.value,
            budget_priority=preferences.budget_priority.value,
            transport_pref=preferences.transport_pref.value,
            accommodation_type=preferences.accommodation_type.value,
            step_free_required=preferences.step_free_required,
            notes_quoted=quote_notes(preferences.notes),
        ),
        must_visit_place_ids=list(must_visit),
        shortlist=list(shortlist),
        day_hints=[],
        limits=Limits(
            max_items_per_day=max_items,
            max_active_minutes_per_day=max_minutes,
            day_start=DAY_START,
            day_end=DAY_END,
            meal_slots=MEAL_SLOTS,
        ),
        locked_items=list(locked_items),
        scope=settings.scope,
        repair_context=None,
        prompt_template_id=settings.prompt_template_id,
        prompt_version=settings.prompt_version,
    )


def _passage(chunk: RetrievedChunk, kind: Literal["place", "guide"]) -> ContextPassage:
    return ContextPassage(
        passage_id=chunk.chunk_id,
        kind=kind,
        title=chunk.title[:MAX_PASSAGE_TITLE_CHARS],
        text=chunk.content[:MAX_PASSAGE_TEXT_CHARS],
        place_id=chunk.place_id,
    )


def ground(
    request: GenerationRequest, retrieved: RetrievalResult | None
) -> GroundedGenerationRequest:
    """gr-2: guide passages in MMR order, then the best chunks of the top places (A1 §6.7, §6.8)."""
    guides: Sequence[RetrievedChunk] = retrieved.guide_passages if retrieved else ()
    best = retrieved.place_best_chunk if retrieved else {}
    top = [place.place_id for place in request.shortlist[:RAG_TOP_K_PLACE]]
    places = sorted(
        (best[place_id] for place_id in top if place_id in best),
        key=lambda chunk: (-chunk.similarity, chunk.chunk_id),
    )
    return GroundedGenerationRequest.model_validate(
        {
            **request.model_dump(exclude={"input_schema_version"}),
            "context_passages": [
                *(_passage(chunk, "guide") for chunk in guides),
                *(_passage(chunk, "place") for chunk in places),
            ][:RAG_MAX_PASSAGES],
            "retrieval": RetrievalInfo(
                mode=retrieved.mode if retrieved else "lexical_fallback",
                embedding_model_id=retrieved.embedding_model_id if retrieved else None,
            ),
        }
    )


def passage_similarities(retrieved: RetrievalResult) -> dict[UUID, float]:
    """Passage ID to similarity, the order in which the size limit drops passages (A1 §6.8)."""
    chunks = (*retrieved.guide_passages, *retrieved.place_best_chunk.values())
    return {chunk.chunk_id: chunk.similarity for chunk in chunks}


def generation_request_hash(request: GenerationRequest) -> str:
    """SHA-256 of the canonical request. ``request_id`` is fresh per call and is left out, so the
    same trip state always gives the same hash."""
    return records.request_hash(request.model_dump(mode="json", exclude={"request_id"}))


async def retrieve(
    trip_id: UUID,
    user_id: UUID,
    provider: ModelProvider,
    sessions: Callable[[], AbstractAsyncContextManager[AsyncSession]],
) -> RetrievalResult:
    """Retrieval for ``build``, with the notes redacted as §8.6 says (A1 §6.7)."""
    async with sessions() as session:
        trip = await trips_service.get_trip(session, user_id, trip_id)
        prefs = await trips_service.get_preferences(session, user_id, trip_id)
    return await retrieval.semantic_retrieval(
        trip, prefs, quote_notes(prefs.notes), provider, sessions
    )


async def build(
    session: AsyncSession,
    *,
    trip_id: UUID,
    user_id: UUID,
    prompt_template_id: str,
    prompt_version: str,
    retrieved: RetrievalResult | None = None,
) -> GenerationRequest:
    trip = await trips_service.get_trip(session, user_id, trip_id)
    prefs = await trips_service.get_preferences(session, user_id, trip_id)
    candidates = await retrieval.ranked_shortlist(
        session,
        trip,
        prefs,
        prefs.must_visit_place_ids,
        meal_slots_per_day=len(MEAL_SLOTS),
        retrieved=retrieved,
    )
    dates = (trip.start_date + timedelta(days=offset) for offset in range(trip.num_days))
    weekdays = list(dict.fromkeys(day.isoweekday() for day in dates))
    request = build_generation_request(
        trip,
        prefs,
        prefs.must_visit_place_ids,
        [],
        [
            shortlist_place(
                PlaceSummary.from_row(candidate.place), hours_summary(candidate.hours, weekdays)
            )
            for candidate in candidates
        ],
        RequestSettings(
            prompt_template_id=prompt_template_id,
            prompt_version=prompt_version,
            contingency_pct=await repository.contingency_pct(session, trip_id),
        ),
    )
    meta = registry.load(prompt_template_id, prompt_version).meta
    grounded = meta.input_schema_version == GROUNDED_INPUT_SCHEMA_VERSION
    return ground(request, retrieved) if grounded else request
