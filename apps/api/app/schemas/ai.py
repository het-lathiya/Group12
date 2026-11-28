"""Shared AI contracts (specification §8.3, §8.6, §8.7; IMD-06).

``GenerationRequest`` (gr-1) is what the backend sends a provider and ``ItineraryOutput`` (io-1) is
the only answer it accepts. ``GroundedGenerationRequest`` (gr-2) and ``GroundedItineraryOutput``
(io-2) add retrieved passages and citations beside them (Amendment A1 §6.8); the active template's
meta.json selects the pair. All four are exported to ``contracts/ai/*.schema.json`` by
``make openapi`` (``app.schemas.ai_export``). The model only chooses shortlisted place IDs, their
order and times and short notes (§8.1): no output has a field for prices, opening hours, travel
times or totals, and every model rejects fields it does not declare.

``ProviderResult``, ``UsageMetadata``, ``HealthStatus`` and ``ModelMetadata`` are the provider
result types of §8.3; ``ModificationRequest`` and ``EditOperations`` are R2 placeholders that only
exist so the ModelProvider interface is complete.
"""

from datetime import date, datetime
from typing import Annotated, Final, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, model_validator

INPUT_SCHEMA_VERSION: Final = "gr-1"
OUTPUT_SCHEMA_VERSION: Final = "io-1"
GROUNDED_INPUT_SCHEMA_VERSION: Final = "gr-2"
GROUNDED_OUTPUT_SCHEMA_VERSION: Final = "io-2"

# Limits of §8.6 and §8.7; the item limits match the itinerary_items CHECKs of migration 0004.
MAX_TRIP_DAYS = 14
MAX_ITEMS_PER_DAY = 12
MIN_DURATION_MIN = 15
MAX_DURATION_MIN = 480
MAX_MUST_VISIT = 10  # IMD-40 (Provisional)
MAX_ASSUMPTIONS = 20
# Amendment A1 §6.5.
EMBEDDING_DIMENSIONS = 768
MAX_EMBED_TEXTS = 32
MAX_EMBED_TEXT_CHARS = 2000
# Amendment A1 §6.8.
MAX_CONTEXT_PASSAGES = 12
MAX_PASSAGE_TITLE_CHARS = 120
MAX_PASSAGE_TEXT_CHARS = 1200
MAX_SOURCE_IDS = 3

HHMM = Annotated[
    str,
    Field(
        pattern=r"^([01]\d|2[0-3]):[0-5]\d$",
        description="24-hour time HH:MM in the destination time zone",
    ),
]
# Money is a decimal string with two places (IMD-05), never a float.
Money = Annotated[
    str, Field(pattern=r"^\d{1,10}\.\d{2}$", description="Amount as a two-decimal string")
]
CurrencyCode = Annotated[str, Field(pattern=r"^[A-Z]{3}$", description="ISO 4217 code")]
DayNumber = Annotated[int, Field(ge=1, le=MAX_TRIP_DAYS)]
DurationMin = Annotated[int, Field(ge=MIN_DURATION_MIN, le=MAX_DURATION_MIN)]

# Vocabularies: the CHECK lists of migrations 0002 to 0004 and IMD-40.
PlaceCategory = Literal[
    "sight",
    "museum",
    "nature",
    "food",
    "shopping",
    "entertainment",
    "religious",
    "activity",
    "stay",
]
Interest = Literal[
    "sight", "museum", "nature", "food", "shopping", "entertainment", "religious", "activity"
]
GroupNeed = Literal["children", "older_adults", "reduced_mobility"]
Pace = Literal["relaxed", "balanced", "busy"]
BudgetPriority = Literal["saving", "balanced", "comfort"]
TransportPref = Literal["walking", "local_transport", "car"]
AccommodationType = Literal["budget", "mid_range", "premium", "any"]
PriceLabel = Literal["estimate", "curated", "unavailable"]
SlotType = Literal["activity", "meal", "rest"]
FindingCode = Literal[
    "OVERLAP",
    "TRANSFER_TOO_SHORT",
    "CLOSED_ON_DAY",
    "OUTSIDE_HOURS",
    "HOURS_UNVERIFIED",
    "DAY_TOO_LONG",
    "BUDGET_EXCEEDED",
    "BUDGET_NEAR",
    "MUST_VISIT_MISSING",
    "UNKNOWN_PLACE",
    "OUTSIDE_TRIP_DATES",
    "COST_INCOMPLETE",
    "ESTIMATE_USED",
]
Severity = Literal["error", "warning", "info"]
ProviderName = Literal["GEMINI", "GROQ", "MOCK", "FINETUNED_MODEL"]


class StrictModel(BaseModel):
    """Base of every AI contract model: undeclared fields are rejected, never ignored."""

    model_config = ConfigDict(extra="forbid")


# ---------- gr-1: GenerationRequest (§8.6) ----------


class Travellers(StrictModel):
    adults: int = Field(ge=1, le=20)
    children: int = Field(ge=0, le=20)


class Budget(StrictModel):
    """Group total for the whole trip."""

    amount: Money
    currency: CurrencyCode


class TripContext(StrictModel):
    destination_id: UUID
    start_date: date
    end_date: date
    num_days: DayNumber
    travellers: Travellers
    group_needs: list[GroupNeed]
    budget: Budget | None
    contingency_pct: float = Field(ge=0, le=50)

    @model_validator(mode="after")
    def _dates_match_num_days(self) -> Self:
        if (self.end_date - self.start_date).days + 1 != self.num_days:
            raise ValueError("num_days must equal end_date - start_date + 1")
        return self


class Preferences(StrictModel):
    interests: list[Interest]
    pace: Pace
    budget_priority: BudgetPriority
    transport_pref: TransportPref
    accommodation_type: AccommodationType
    step_free_required: bool
    # The traveller's notes, cleaned and cut to 500 characters; data for the model, never instructions.
    notes_quoted: str | None = Field(max_length=500)


class Suitability(StrictModel):
    """Null means unknown."""

    step_free: bool | None
    child_friendly: bool | None


class ShortlistPlace(StrictModel):
    place_id: UUID
    name: str = Field(min_length=1, max_length=160)
    category: PlaceCategory
    tags: list[str]
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    typical_duration_min: DurationMin
    price_min: Money | None
    price_max: Money | None
    price_label: PriceLabel
    hours_summary: str
    suitability: Suitability

    @property
    def id(self) -> UUID:
        """So a shortlist place can be routed like a ``places`` row."""
        return self.place_id


class DayHint(StrictModel):
    day_number: DayNumber
    place_ids: list[UUID]


class Limits(StrictModel):
    max_items_per_day: int = Field(ge=1, le=MAX_ITEMS_PER_DAY)
    max_active_minutes_per_day: int = Field(gt=0)
    day_start: HHMM
    day_end: HHMM
    meal_slots: list[str]


class LockedItem(StrictModel):
    day_number: DayNumber
    place_id: UUID
    start_time: HHMM
    duration_min: DurationMin


class Scope(StrictModel):
    """`full` for API-22 and API-31; `day` with its day number for API-30."""

    kind: Literal["full", "day"]
    day_number: DayNumber | None

    @model_validator(mode="after")
    def _day_number_only_for_day_scope(self) -> Self:
        # Mirrors the ai_generations CHECK (scope = 'day') = (scope_day_number is not null).
        if (self.kind == "day") != (self.day_number is not None):
            raise ValueError("day_number is set exactly when kind is 'day'")
        return self


class PlanFinding(StrictModel):
    """A validator finding as the repair call sees it (§8.12, §8.18)."""

    code: FindingCode
    severity: Severity
    day_number: DayNumber | None
    item_ref: str | None = Field(default=None, description="Item as d<day>-i<position>")
    place_id: UUID | None = Field(default=None, description="Set only for MUST_VISIT_MISSING")
    message: str = Field(max_length=500)
    suggested_fix: str | None = Field(default=None, max_length=500)


class RepairContext(StrictModel):
    """Sent only on the one repair call of step 10 (§8.13)."""

    invalid_output: str
    findings: list[PlanFinding]


class GenerationRequest(StrictModel):
    """gr-1: built by the backend from database rows only; it never holds personal data (§8.6)."""

    input_schema_version: Literal["gr-1"] = INPUT_SCHEMA_VERSION
    request_id: UUID
    trip: TripContext
    preferences: Preferences
    must_visit_place_ids: list[UUID] = Field(max_length=MAX_MUST_VISIT)
    shortlist: list[ShortlistPlace]
    day_hints: list[DayHint]
    limits: Limits
    locked_items: list[LockedItem]
    scope: Scope
    repair_context: RepairContext | None
    prompt_template_id: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)

    def shortlist_ids(self) -> set[str]:
        """The closed list of place IDs an answer may use."""
        return {str(place.place_id) for place in self.shortlist}

    def passage_ids(self) -> set[str]:
        """The closed list of IDs an answer may cite; gr-1 sends no passages."""
        return set()


# ---------- gr-2: GroundedGenerationRequest (A1 §6.8) ----------


class ContextPassage(StrictModel):
    """A whole retrieved chunk, sent as quoted reference data, never as an instruction."""

    passage_id: UUID
    kind: Literal["place", "guide"]
    title: str = Field(max_length=MAX_PASSAGE_TITLE_CHARS)
    text: str = Field(max_length=MAX_PASSAGE_TEXT_CHARS)
    place_id: UUID | None


class RetrievalInfo(StrictModel):
    mode: Literal["vector", "lexical_fallback"]
    embedding_model_id: str | None


class GroundedGenerationRequest(GenerationRequest):
    """gr-2: gr-1 plus the retrieved passages, guide passages first (A1 §6.8)."""

    # Each schema version pins its own literal, so a gr-1 file can never validate as gr-2.
    input_schema_version: Literal["gr-2"] = GROUNDED_INPUT_SCHEMA_VERSION  # type: ignore[assignment]
    context_passages: list[ContextPassage] = Field(max_length=MAX_CONTEXT_PASSAGES)
    retrieval: RetrievalInfo

    def passage_ids(self) -> set[str]:
        return {str(passage.passage_id) for passage in self.context_passages}


# ---------- io-1: ItineraryOutput (§8.7) ----------
# Field order is part of the contract: the model follows it (days, summary, assumptions).


class ItineraryItemOutput(StrictModel):
    place_id: str = Field(min_length=1, description="A place_id from the request's shortlist")
    start_time: HHMM
    duration_min: DurationMin
    slot_type: SlotType
    note: str = Field(max_length=200)


class ItineraryDayOutput(StrictModel):
    day_number: DayNumber
    theme: str = Field(max_length=80)
    items: list[ItineraryItemOutput] = Field(min_length=1, max_length=MAX_ITEMS_PER_DAY)


class ItineraryOutput(StrictModel):
    """io-1: the model's proposal. Prices, hours, travel times and totals come from code (§8.1)."""

    days: list[ItineraryDayOutput] = Field(min_length=1, max_length=MAX_TRIP_DAYS)
    summary: str | None = Field(default=None, max_length=500)
    assumptions: list[str] = Field(max_length=MAX_ASSUMPTIONS)

    @model_validator(mode="after")
    def _fits_the_request(self, info: ValidationInfo) -> Self:
        """The limits that depend on the trip (IMP-306), given as validation context.

        Only ``app.validation.output_check`` passes the context, so an adapter's parse and the
        exported schema stay as they are. A day number past the trip is not refused here:
        ``check_output`` rejects its items with OUTSIDE_TRIP_DATES.
        """
        if not info.context:
            return self
        day_numbers = [day.day_number for day in self.days]
        if len(day_numbers) > info.context["trip_days"]:
            raise ValueError("more days than the trip has")
        if len(set(day_numbers)) != len(day_numbers):
            raise ValueError("a day number appears twice")
        if any(len(day.items) > info.context["max_items_per_day"] for day in self.days):
            raise ValueError("more items on a day than the pace allows")
        return self

    def place_ids(self) -> list[str]:
        return [item.place_id for day in self.days for item in day.items]

    def unknown_place_ids(self, request: GenerationRequest) -> list[str]:
        """IDs outside the request's shortlist, in answer order.

        Step 8 drops these items with an UNKNOWN_PLACE finding (§8.11); parsing does not reject
        them, so the repair step can see what the model did.
        """
        allowed = request.shortlist_ids()
        return [place_id for place_id in self.place_ids() if place_id not in allowed]


# ---------- io-2: GroundedItineraryOutput (A1 §6.8) ----------


class GroundedItemOutput(ItineraryItemOutput):
    # maxItems tells the model the limit but is not validated: an extra citation must never fail
    # the answer, so ``output_check`` cuts the list instead (A1 §6.10).
    source_ids: list[str] = Field(
        default_factory=list,
        description="passage_id values of the request this note relies on",
        json_schema_extra={"maxItems": MAX_SOURCE_IDS},
    )


class GroundedDayOutput(ItineraryDayOutput):
    # Narrows the field to the io-2 item; every other rule of io-1 stays.
    items: list[GroundedItemOutput] = Field(min_length=1, max_length=MAX_ITEMS_PER_DAY)  # type: ignore[assignment]


class GroundedItineraryOutput(ItineraryOutput):
    """io-2: io-1 plus the citations of each item. Field order stays as in io-1."""

    # Narrows the field to the io-2 day; every other rule of io-1 stays.
    days: list[GroundedDayOutput] = Field(min_length=1, max_length=MAX_TRIP_DAYS)  # type: ignore[assignment]


# The pairs meta.json may name (A1 §6.8): v1 uses gr-1 and io-1, v2 uses gr-2 and io-2.
OUTPUT_FOR_INPUT: Final[dict[str, str]] = {
    INPUT_SCHEMA_VERSION: OUTPUT_SCHEMA_VERSION,
    GROUNDED_INPUT_SCHEMA_VERSION: GROUNDED_OUTPUT_SCHEMA_VERSION,
}
OUTPUT_MODELS: Final[dict[str, type[ItineraryOutput]]] = {
    OUTPUT_SCHEMA_VERSION: ItineraryOutput,
    GROUNDED_OUTPUT_SCHEMA_VERSION: GroundedItineraryOutput,
}


# ---------- Provider result types (§8.3) ----------


class UsageMetadata(StrictModel):
    """Token counts as the provider reports them; null when not reported, never estimated."""

    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    thinking_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)


class ProviderResult[T](StrictModel):
    output: T
    usage: UsageMetadata
    finish_reason: str | None
    latency_ms: int = Field(ge=0)
    provider_request_id: str | None
    notes: list[str] = Field(default_factory=list)
    # IMD-222: set only when GEMINI_FALLBACK_MODEL_ID answered after the configured model failed.
    model_id: str | None = None
    fallback_from: Literal["provider_rate_limited", "provider_unavailable"] | None = None


EmbeddingPurpose = Literal["document", "query"]


class EmbeddingResult(StrictModel):
    """A1 §6.5: one 768-length, L2-normalised vector per text, in the order of the texts."""

    vectors: list[list[float]]
    model_id: str
    usage: UsageMetadata
    latency_ms: int = Field(ge=0)


class HealthStatus(StrictModel):
    """`health_check` never raises and makes no generation call."""

    status: Literal["ok", "degraded", "down"]
    detail: str | None
    checked_at: datetime


class ModelMetadata(StrictModel):
    provider: ProviderName
    model_id: str
    model_version: str | None = None  # null unless the response reports one
    adapter_version: str
    supports_structured_output: bool
    max_input_tokens: int | None
    max_output_tokens: int | None
    is_tuned: bool = False
    base_model: str | None = None
    training_run_id: str | None = None


# ---------- R2 placeholders (§8.3 modify_itinerary) ----------


class ModificationRequest(StrictModel):
    """R2: natural-language edits (blueprint). Its fields arrive with the R2 card."""


class EditOperations(StrictModel):
    """R2: the edits a model proposes for a ModificationRequest. Fields arrive with the R2 card."""
