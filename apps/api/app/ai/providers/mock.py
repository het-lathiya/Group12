"""Mock adapter (specification §8.4, FR-042, IMD-27; SAMPLE output, never a real plan).

The default provider in ``local`` and ``test``. It makes no network call and imports no HTTP
client or vendor SDK. ``generate_itinerary`` builds io-1 only from the gr-1 request:

- ``ok``: each requested day (``trip.num_days``, or the one day of a ``day`` scope) takes, in
  shortlist order, every remaining candidate that fits: the day starts at ``limits.day_start``,
  each next item after the fallback travel estimate plus its buffer (as step 9 recalculates it),
  at most ``limits.max_items_per_day`` items and ``limits.max_active_minutes_per_day`` active
  minutes, ending by ``limits.day_end`` and inside the day's ``hours_summary`` hours when it has
  any; a candidate that fits no day is left out, and when none fits the plain spread is used.
  With a lunch slot in ``limits.meal_slots`` (IMD-189) a food place is planned only as the day's
  meal: once the clock is in the lunch window (12:00 to 14:00) the first remaining food place
  that fits and starts by 14:00 becomes a ``meal`` item (a must-visit food place may come at any
  time and is then the meal); a day that runs through the window without one ends its theme with
  "No food place found nearby", as the rule-based planner does;
- ``flawed`` and ``unknown_place`` start from the plain spread: the candidates in order, at most
  ``limits.max_items_per_day`` per day, first days first, the first item at 09:00 and each next
  one at the previous start + ``typical_duration_min`` + 30 minutes;
- ``duration_min`` is the candidate's typical duration;
- themes and notes are written into io-1's model-text fields and start with ``SAMPLE``;
- for a gr-2 request the answer is io-2 and an item cites the place passage of its place, if any.

The same request gives an identical output. Scenarios (IMD-27) come from the constructor in tests
or from ``MOCK_PROVIDER_SCENARIO`` (validated by ``app.core.config``); they are honoured when
``APP_ENV`` is local, test or staging and ignored (treated as ``ok``) in production. Unit tests may
pass ``raise_error=<ProviderError>`` to reach the other error kinds.

``embed_texts`` is the hashed bag-of-words of Amendment A1 §6.5 (``mock-embed-v1``): texts that share
words are similar. Scenarios do not affect it; unit tests pass ``embed_error=<ProviderError>``.
"""

import hashlib
import re
import time
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Final, Literal, get_args

from app.ai.errors import (
    ProviderBadRequest,
    ProviderConfigError,
    ProviderError,
    ProviderInvalidOutput,
    ProviderQuotaExhausted,
    ProviderRateLimited,
    ProviderTimeout,
)
from app.ai.providers.base import check_embed_input, l2_normalised
from app.core.config import AppEnv, MockScenario, get_settings
from app.routing.estimate import BUFFER_MIN, estimate
from app.schemas.ai import (
    EMBEDDING_DIMENSIONS,
    EditOperations,
    EmbeddingPurpose,
    EmbeddingResult,
    GenerationRequest,
    GroundedGenerationRequest,
    GroundedItineraryOutput,
    HealthStatus,
    ItineraryDayOutput,
    ItineraryItemOutput,
    ItineraryOutput,
    ModelMetadata,
    ModificationRequest,
    ProviderResult,
    ShortlistPlace,
    UsageMetadata,
)

MODEL_ID: Final = "mock-v1"
ADAPTER_VERSION: Final = "mock-1"
EMBED_MODEL_ID: Final = "mock-embed-v1"
EMBED_MIN_TOKEN: Final = 3
_ALPHANUMERIC_RUN: Final = re.compile(r"[^\W_]+")
SCENARIOS: Final[tuple[MockScenario, ...]] = get_args(MockScenario)
SCENARIO_ENVIRONMENTS: Final[frozenset[AppEnv]] = frozenset({"local", "test", "staging"})

DAY_START_MIN: Final = 9 * 60
GAP_MIN: Final = 30
LAST_START_MIN: Final = 23 * 60 + 59
THEME_MAX: Final = 80
# The lunch window and day note of the rule-based planner (IMP-606), repeated because the mock
# imports no planning module; a unit test keeps them equal to presets.MEAL_WINDOWS.
LUNCH_FROM: Final = 12 * 60
LUNCH_TO: Final = 14 * 60
NO_FOOD_NOTE: Final = "No food place found nearby"
FOOD: Final = "food"
WEEKDAYS: Final = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")  # ISO weekdays 1 to 7
# One part of the request builder's hours_summary, for example "Fri 09:00-17:00" or "Mon closed".
_HOURS_PART: Final = re.compile(r"(\w{3}) (?:closed|(\d\d:\d\d)-(\d\d:\d\d))")
# Namespace of the deterministic out-of-shortlist ID of the unknown_place scenario.
_UNKNOWN_PLACE_NAMESPACE: Final = uuid.UUID("5a3e1c00-0000-4000-8000-00000000a207")


def _hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _minutes(hhmm: str) -> int:
    hours, minutes = hhmm.split(":")
    return int(hours) * 60 + int(minutes)


def _day_numbers(request: GenerationRequest) -> list[int]:
    if request.scope.kind == "day" and request.scope.day_number is not None:
        return [request.scope.day_number]
    return list(range(1, request.trip.num_days + 1))


def _build_days(
    request: GenerationRequest, candidates: list[ShortlistPlace]
) -> list[ItineraryDayOutput]:
    """Candidates in order over the days, at most the pace item limit per day (§8.4 timing)."""
    per_day = request.limits.max_items_per_day
    remaining = list(candidates)
    days: list[ItineraryDayOutput] = []
    for day_number in _day_numbers(request):
        items: list[ItineraryItemOutput] = []
        start = DAY_START_MIN
        while remaining and len(items) < per_day and start <= LAST_START_MIN:
            place = remaining.pop(0)
            items.append(
                ItineraryItemOutput(
                    place_id=str(place.place_id),
                    start_time=_hhmm(start),
                    duration_min=place.typical_duration_min,
                    slot_type="meal" if place.category == "food" else "activity",
                    note=f"SAMPLE note from the mock provider: visit {place.name}."[:200],
                )
            )
            start += place.typical_duration_min + GAP_MIN
        if items:
            first = next(p.name for p in candidates if str(p.place_id) == items[0].place_id)
            theme = f"SAMPLE day {day_number}: {first}"[:THEME_MAX]
            days.append(ItineraryDayOutput(day_number=day_number, theme=theme, items=items))
    return days


def _windows(summary: str, weekday: str) -> list[tuple[int, int]] | None:
    """Opening intervals of ``weekday`` in minutes (overnight past 1440); [] when closed, None
    when the summary has no stored hours for that day (nothing to fit)."""
    parts = [m for m in map(_HOURS_PART.fullmatch, summary.split("; ")) if m and m[1] == weekday]
    if not parts:
        return None
    windows = []
    for part in (m for m in parts if m[2] and m[3]):
        opened, closed = _minutes(part[2]), _minutes(part[3])
        windows.append((opened, closed + 1440 if closed <= opened else closed))
    return windows


def _fit(
    request: GenerationRequest,
    place: ShortlistPlace,
    previous: ShortlistPlace | None,
    clock: int,
    active: int,
    weekday: str,
) -> tuple[int, int, int] | None:
    """(start, end, active minutes after it) when ``place`` fits next on the day, else None."""
    limits = request.limits
    travel = 0
    if previous is not None:
        mode = request.preferences.transport_pref
        travel = estimate(previous.lat, previous.lon, place.lat, place.lon, mode).minutes
    start = clock + (travel + BUFFER_MIN["fallback_estimate"] if previous else 0)
    end = start + place.typical_duration_min
    spent = active + travel + place.typical_duration_min
    windows = _windows(place.hours_summary, weekday)
    if (
        end > _minutes(limits.day_end)
        or spent > limits.max_active_minutes_per_day
        or (windows is not None and not any(o <= start and end <= c for o, c in windows))
    ):
        return None
    return start, end, spent


def _fitted_days(request: GenerationRequest) -> list[ItineraryDayOutput]:
    """The ok plan: each day takes, in shortlist order, the remaining candidates that fit."""
    limits = request.limits
    lunch_slot = "lunch" in limits.meal_slots  # empty with the 'meal_slots' switch off (IMD-11)
    must = {str(place_id) for place_id in request.must_visit_place_ids}
    remaining = list(request.shortlist)
    days: list[ItineraryDayOutput] = []
    for day_number in _day_numbers(request):
        weekday = WEEKDAYS[(request.trip.start_date + timedelta(days=day_number - 1)).weekday()]
        items: list[ItineraryItemOutput] = []
        names: list[str] = []
        clock, active, previous, had_meal = _minutes(limits.day_start), 0, None, False
        # None closes the pass so that a lunch still due after the last candidate is tried.
        for place in [*remaining, None]:
            if len(items) >= limits.max_items_per_day:
                break
            if lunch_slot and not had_meal and LUNCH_FROM <= clock <= LUNCH_TO:
                had_meal = True  # planned now, or no food place fits and the day goes on
                meal = next(
                    (
                        (food, fit)
                        for food in remaining
                        if food.category == FOOD
                        and (fit := _fit(request, food, previous, clock, active, weekday))
                        and fit[0] <= LUNCH_TO
                    ),
                    None,
                )
                if meal is not None:
                    food, (start, clock, active) = meal
                    items.append(_item(food, start, "meal"))
                    names.append(food.name)
                    remaining.remove(food)
                    previous = food
                    if len(items) >= limits.max_items_per_day:
                        break
            if place is None or place not in remaining:
                continue
            is_food = place.category == FOOD
            if lunch_slot and is_food and (had_meal or str(place.place_id) not in must):
                continue  # a food place is the day's meal, not a stop on the way
            fit = _fit(request, place, previous, clock, active, weekday)
            if fit is None:
                continue
            had_meal = had_meal or (lunch_slot and is_food)
            items.append(_item(place, fit[0], "meal" if is_food else "activity"))
            names.append(place.name)
            remaining.remove(place)
            clock, active, previous = fit[1], fit[2], place
        if items:
            theme = f"SAMPLE day {day_number}: {names[0]}"
            meals = any(item.slot_type == "meal" for item in items)
            if lunch_slot and not meals and clock >= LUNCH_TO:  # the lunch slot stays empty
                suffix = f" · {NO_FOOD_NOTE}"
                theme = theme[: THEME_MAX - len(suffix)] + suffix
            days.append(
                ItineraryDayOutput(day_number=day_number, theme=theme[:THEME_MAX], items=items)
            )
    return days


def _item(
    place: ShortlistPlace, start: int, slot_type: Literal["activity", "meal"]
) -> ItineraryItemOutput:
    return ItineraryItemOutput(
        place_id=str(place.place_id),
        start_time=_hhmm(start),
        duration_min=place.typical_duration_min,
        slot_type=slot_type,
        note=f"SAMPLE note from the mock provider: visit {place.name}."[:200],
    )


def _output(days: list[ItineraryDayOutput]) -> ItineraryOutput:
    if not days:
        # io-1 needs at least one day with one item; an empty shortlist cannot give one.
        raise ProviderInvalidOutput("empty", "mock provider: the request has no candidates")
    return ItineraryOutput(
        days=days,
        summary="SAMPLE plan from the mock provider.",
        assumptions=["SAMPLE: travel times, prices and hours are calculated by the application."],
    )


def _flawed(request: GenerationRequest) -> ItineraryOutput:
    """Schema-valid io-1 with one must-visit place left out and one overlap on the first day.

    The left-out place is the first must-visit ID that is a candidate; the overlap moves the
    second item of the first day to start halfway through the first item. A request without a
    shortlisted must-visit place, or whose first day has one item, gets only the flaw it allows.
    """
    shortlisted = {str(place.place_id) for place in request.shortlist}
    missing = next((str(p) for p in request.must_visit_place_ids if str(p) in shortlisted), None)
    days = _build_days(request, [p for p in request.shortlist if str(p.place_id) != missing])
    if days and len(days[0].items) >= 2:
        first, second = days[0].items[0], days[0].items[1]
        overlap_start = _minutes(first.start_time) + first.duration_min // 2
        days[0].items[1] = second.model_copy(update={"start_time": _hhmm(overlap_start)})
    return _output(days)


def _unknown_place(request: GenerationRequest) -> ItineraryOutput:
    """The plain spread with its last item's place_id replaced by one outside the candidates."""
    output = _output(_build_days(request, list(request.shortlist)))
    shortlisted = request.shortlist_ids()
    unknown = uuid.uuid5(_UNKNOWN_PLACE_NAMESPACE, str(request.request_id))
    while str(unknown) in shortlisted:
        unknown = uuid.uuid5(_UNKNOWN_PLACE_NAMESPACE, str(unknown))
    last_day = output.days[-1]
    last_day.items[-1] = last_day.items[-1].model_copy(update={"place_id": str(unknown)})
    return output


def _cited(request: GroundedGenerationRequest, output: ItineraryOutput) -> ItineraryOutput:
    """io-2: each item cites the place passage of its own place, which is deterministic."""
    passages = {
        str(passage.place_id): str(passage.passage_id)
        for passage in request.context_passages
        if passage.kind == "place"
    }
    answer = output.model_dump()
    for day in answer["days"]:
        for item in day["items"]:
            passage_id = passages.get(item["place_id"])
            item["source_ids"] = [passage_id] if passage_id else []
    return GroundedItineraryOutput.model_validate(answer)


def hashed_embedding(text: str) -> list[float]:
    """A1 §6.5: signed token hashes, summed and normalised; nothing to hash gives e0."""
    vector = [0.0] * EMBEDDING_DIMENSIONS
    for token in _ALPHANUMERIC_RUN.findall(text.lower()):
        if len(token) < EMBED_MIN_TOKEN:
            continue
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        vector[int(digest[:8], 16) % EMBEDDING_DIMENSIONS] += (
            1 if int(digest[8], 16) % 2 == 0 else -1
        )
    if not any(vector):
        return [1.0, *[0.0] * (EMBEDDING_DIMENSIONS - 1)]
    return l2_normalised(vector)


class MockProvider:
    name: Literal["MOCK"] = "MOCK"
    embedding_model_id: str = EMBED_MODEL_ID

    def __init__(
        self,
        scenario: MockScenario | None = None,
        *,
        app_env: AppEnv | None = None,
        raise_error: ProviderError | None = None,
        embed_error: ProviderError | None = None,
    ) -> None:
        """``scenario`` and ``app_env`` default to MOCK_PROVIDER_SCENARIO and APP_ENV."""
        if scenario is None or app_env is None:
            settings = get_settings()
            scenario = settings.mock_provider_scenario if scenario is None else scenario
            app_env = settings.app_env if app_env is None else app_env
        if scenario not in SCENARIOS:
            raise ProviderConfigError(
                f"mock provider: unknown scenario; allowed values are {', '.join(SCENARIOS)}"
            )
        self.requested_scenario: MockScenario = scenario
        self.app_env: AppEnv = app_env
        self.raise_error = raise_error
        self.embed_error = embed_error

    @property
    def scenario(self) -> MockScenario:
        """The scenario in effect: the requested one outside production, else ``ok``."""
        return self.requested_scenario if self.app_env in SCENARIO_ENVIRONMENTS else "ok"

    async def generate_itinerary(
        self, request: GenerationRequest
    ) -> ProviderResult[ItineraryOutput]:
        started = time.perf_counter()
        if self.raise_error is not None:
            raise self.raise_error
        match self.scenario:
            case "timeout":
                raise ProviderTimeout("mock provider: timeout scenario")
            case "rate_limited":
                raise ProviderRateLimited("mock provider: rate_limited scenario", retry_after_s=1)
            case "quota":
                raise ProviderQuotaExhausted("mock provider: quota scenario")
            case "invalid_json":
                raise ProviderInvalidOutput(
                    "malformed_json", "mock provider: invalid_json scenario"
                )
            case "flawed":
                output = _flawed(request)
            case "unknown_place":
                output = _unknown_place(request)
            case _:
                # Nothing fits (for example every visit outlasts the day): the plain spread.
                fitted = _fitted_days(request)
                output = _output(fitted or _build_days(request, list(request.shortlist)))
        if isinstance(request, GroundedGenerationRequest):
            output = _cited(request, output)
        return ProviderResult[ItineraryOutput](
            output=output,
            usage=UsageMetadata(),  # the mock reports no tokens: every count stays null
            finish_reason="stop",
            latency_ms=round((time.perf_counter() - started) * 1000),
            provider_request_id=None,
        )

    async def modify_itinerary(
        self, request: ModificationRequest
    ) -> ProviderResult[EditOperations]:
        raise ProviderBadRequest("modify_itinerary not enabled in the MVP")

    async def embed_texts(
        self,
        texts: Sequence[str],
        purpose: EmbeddingPurpose,
        titles: Sequence[str | None] | None = None,
    ) -> EmbeddingResult:
        started = time.perf_counter()
        check_embed_input(texts, titles)
        if self.embed_error is not None:
            raise self.embed_error
        return EmbeddingResult(
            vectors=[hashed_embedding(text) for text in texts],
            model_id=EMBED_MODEL_ID,
            usage=UsageMetadata(),
            latency_ms=round((time.perf_counter() - started) * 1000),
        )

    async def health_check(self) -> HealthStatus:
        """``down`` for a configuration error, as a provider with a refused key reports (§8.3)."""
        down = isinstance(self.raise_error, ProviderConfigError)
        return HealthStatus(
            status="down" if down else "ok", detail=None, checked_at=datetime.now(UTC)
        )

    def get_model_metadata(self) -> ModelMetadata:
        return ModelMetadata(
            provider=self.name,
            model_id=MODEL_ID,
            adapter_version=ADAPTER_VERSION,
            supports_structured_output=True,
            max_input_tokens=None,
            max_output_tokens=None,
        )


if TYPE_CHECKING:
    from app.ai.providers.base import ModelProvider

    def _conforms_to_model_provider(provider: MockProvider) -> ModelProvider:
        # mypy (make typecheck) fails here if the mock stops matching the interface.
        return provider
