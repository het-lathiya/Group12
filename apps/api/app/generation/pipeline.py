"""Generation pipeline (§8.2 steps 1 to 11; IMP-305).

mark_running -> retrieval (A1 §6.7, never fails the job) -> build the request from the ranked
shortlist (steps 2 to 5) -> input limit -> record
the settings -> provider.generate_itinerary (steps 6, 7) -> mark_validating -> steps 8 and 9 -> save
the plan and complete the record in one transaction (step 11). Each status change is its own short
transaction, and none stays open across the provider call (§5.8). Step 8 is
``app.validation.output_check`` (IMP-306); step 9 is ``recalculate`` (IMP-308). Trip
completeness (step 1) is checked by API-22 before the row exists.

Step 10 (IMP-502, §8.13): ``assess`` runs steps 8 and 9 on an answer, applies the deterministic
repair of ``app.validation.repair`` and validates again. A usable answer with no error left is
saved (``model``, or ``model_repaired`` after a fix). Otherwise ``repair_call`` makes the one
model repair call: the same request (so the same passages) with ``repair_context`` holding the
answer and its findings, inside its own 25 s and never more than the job has left, with no
transport retry. Its answer goes through ``assess`` again: usable is ``model_repaired``; not usable
is the rule-based plan with ``unresolved_validation``; a failed or impossible repair call is the
rule-based plan with ``invalid_output`` (quota and configuration errors end ``failed``, IMD-44).
An invalid answer is never retried blindly.

The rule-based plan (``fallback_planner``, IMP-402) runs for mode rule_based (no retrieval and no
provider call) and after a transient provider error or an answer that cannot be saved; it goes
through steps 8 to 11 like a model answer and completes ``fallback_rule_based`` with the cause in
``validation_summary.provider_failure`` and failure_reason null (§8.3, IMD-22). Quota and
configuration errors end ``failed`` with no fallback (IMD-44).

After step 9 the merged validator (``app.validation.validator``, IMP-404) runs on the plan that is
saved, model or rule-based (IMP-406): its findings are saved as the plan's warnings and counted in
both summaries. A MUST_VISIT_MISSING finding names the place, the reason (filter conflict, closed
every day, no room) and a fix; a must-visit place is never dropped silently (FR-034). Pace limits
reach the validator for DAY_TOO_LONG (IMP-309).

Step 7 is skipped while the provider's circuit breaker is open (IMP-401): opened by transient
errors it gives the rule-based plan with that cause; opened by quota or auth it ends ``failed``
with ``provider_quota_exhausted`` or ``config_error``. Every provider failure, open breaker
included, is decided by the one table ``outcomes.resolve`` (IMP-403). The fallback uses what is
left of the job's 120 s (the 15 s reserve of §8.2 and any unused time); an unexpected error in
it, as anywhere in the job, ends ``failed`` / ``internal`` through the job runner, and a failed
generation writes nothing to the itinerary tables. Each generation's provider result is
recorded on the breaker once, after the adapter's retries; retrieval's embeddings never are.
An answer of GEMINI_FALLBACK_MODEL_ID records the configured model's failure on the breaker and
that model's ID on the record (IMD-222).

IMD-223: after an initial Gemini transient/quota failure, the optional Groq provider runs once
within step 7's remaining allowance. It uses the same validation and one repair call. Its errors
end in the labelled rule-based plan, including quota/configuration errors. Groq off preserves the
existing Gemini outcomes. Embeddings still use Gemini, with lexical fallback (IMD-112).

Never logged: the request built for the provider, its raw output, notes or prompt text (FR-125).
"""

import asyncio
import logging
import time
from collections import Counter
from collections.abc import Callable, Sequence
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field, replace
from typing import Any, Final
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import factory, limits
from app.ai.errors import (
    InvalidOutputKind,
    ProviderError,
    ProviderInvalidOutput,
    ProviderQuotaExhausted,
    ProviderRateLimited,
    ProviderTimeout,
    ProviderUnavailable,
)
from app.ai.providers.base import ModelProvider
from app.budget import engine
from app.core.config import GEMINI_TIME_ALLOWANCE_S, REPAIR_TIME_ALLOWANCE_S, get_settings
from app.core.errors import StalePlan
from app.generation import (
    fallback_planner,
    outcomes,
    records,
    repository,
    request_builder,
    retrieval,
    schedule,
)
from app.generation.records import CompletedOutcome, FailureReason, TokenUsage
from app.itinerary import service as itinerary_service
from app.itinerary.schemas import PlannedDay, PlannedItem
from app.places import repository as places_repository
from app.places import service as places_service
from app.routing.cache import RouteCacheRepository
from app.routing.client import get_client
from app.routing.service import RoutingService
from app.schemas.ai import (
    GenerationRequest,
    ItineraryOutput,
    ModelMetadata,
    ProviderResult,
    RepairContext,
    Scope,
    UsageMetadata,
)
from app.trips import service as trips_service
from app.validation import output_check, repair
from app.validation.rules import Finding, ValidationContext
from app.validation.validator import validate

logger = logging.getLogger(__name__)

Sessions = Callable[[], AbstractAsyncContextManager[AsyncSession]]

SEVERITY_KEYS: Final = {"error": "errors", "warning": "warnings", "info": "infos"}
# §8.12: a plan with one of these left is not usable.
BLOCKING: Final = frozenset({"UNKNOWN_PLACE", "OUTSIDE_TRIP_DATES", "OVERLAP", "CLOSED_ON_DAY"})
# §8.14: the job's 120 s (jobs.PIPELINE_TIMEOUT_S; jobs imports this module) less the 15 s kept
# for the fallback and the save; the repair call never runs into them.
REPAIR_DEADLINE_S: Final = 120 - 15
FALLBACK_CAUSES: Final = {
    "provider_rate_limited": ProviderRateLimited,
    "provider_unavailable": ProviderUnavailable,
}
GROQ_TRIGGERS: Final = (
    ProviderUnavailable,
    ProviderRateLimited,
    ProviderQuotaExhausted,
    ProviderTimeout,
)


@dataclass
class Job:
    """One generation run: its row, its transactions and its clock."""

    generation_id: UUID
    sessions: Sessions
    trip_id: UUID
    user_id: UUID
    started: float
    validating: bool = False
    scope: Scope = field(default_factory=lambda: Scope(kind="full", day_number=None))
    request_hash: str | None = None
    rule_based: bool = False

    def elapsed_ms(self) -> int:
        return round((time.perf_counter() - self.started) * 1000)

    async def mark_validating(self) -> None:
        """running -> validating once; a fallback after step 8 is already validating."""
        if not self.validating:
            async with self.sessions() as session:
                await repository.mark_validating(session, self.generation_id)
            self.validating = True

    async def active_ids(self, request: GenerationRequest) -> set[str]:
        # Read again: a place can go inactive while the provider is answering.
        async with self.sessions() as session:
            active = await places_service.active_place_names(
                session, request.trip.destination_id, [p.place_id for p in request.shortlist]
            )
        return {str(id_) for id_ in active}

    async def fail(
        self,
        reason: FailureReason,
        *,
        usage: TokenUsage | None = None,
        validation_summary: dict[str, Any] | None = None,
    ) -> None:
        async with self.sessions() as session:
            await repository.fail(
                session,
                self.generation_id,
                reason,
                usage=usage,
                latency_ms=self.elapsed_ms(),
                validation_summary=validation_summary,
            )


@dataclass(frozen=True)
class Assessed:
    """An answer after steps 8 and 9 and the deterministic repair of step 10."""

    output: ItineraryOutput | None  # None: nothing could be read or nothing is left
    plan: list[PlannedDay]
    findings: list[Finding]  # step 9's on the repaired plan, or step 8's when no plan is left
    step8: dict[str, Any]  # output_check.summary of the answer
    fixes: int  # deterministic repairs, step 8's drops included

    @property
    def usable(self) -> bool:
        """§8.12: at least one item and none of BLOCKING left."""
        return (
            self.output is not None
            and any(day.items for day in self.plan)
            and not any(finding.code in BLOCKING for finding in self.findings)
        )

    @property
    def errors_remain(self) -> bool:
        return self.output is None or any(f.severity == "error" for f in self.findings)


def unreadable(kind: InvalidOutputKind) -> Assessed:
    return Assessed(None, [], [], output_check.summary(kind=kind), 0)


async def evaluate(
    job: Job, request: GenerationRequest, output: ItineraryOutput
) -> tuple[list[PlannedDay], list[Finding]]:
    """Step 9: the recalculated plan and the merged validator's findings on it."""
    async with job.sessions() as session:
        plan = await recalculate(session, output, request, job.trip_id, job.user_id)
        findings = await plan_findings(session, request, plan, job.trip_id, job.user_id)
    return plan, findings


async def assess(job: Job, request: GenerationRequest, answer: ItineraryOutput) -> Assessed:
    """Steps 8 and 9, then the deterministic repair and step 9 again if it changed anything."""
    if request.scope.kind == "day" and any(
        day.day_number != request.scope.day_number for day in answer.days
    ):
        return unreadable("schema_violation")
    try:
        answer = output_check.apply_limits(
            answer,
            trip_days=request.trip.num_days,
            max_items_per_day=request.limits.max_items_per_day,
        )
    except ProviderInvalidOutput as exc:
        return unreadable(exc.kind)
    active = await job.active_ids(request)
    if not request.limits.meal_slots:  # no meal slot requested, or the switch is off (IMD-11)
        answer = output_check.without_meals(answer)
    food = {str(place.place_id) for place in request.shortlist if place.category == "food"}
    checked = output_check.check_output(
        answer, active, request.trip.num_days, request.passage_ids(), food
    )
    step8 = output_check.summary(checked)
    dropped = len(checked.findings)  # step 8 dropped each unknown place and day outside the trip
    if not checked.output.days:
        return Assessed(None, [], checked.findings, step8, dropped)
    plan, findings = await evaluate(job, request, checked.output)
    scope = repair.scope_for(request)
    # Only a must-visit place that lacked room is inserted; one with a filter conflict or closed
    # every day stays MUST_VISIT_MISSING with its reason (FR-034).
    conflicted = {
        str(f.place_id)
        for f in findings
        if f.code == "MUST_VISIT_MISSING" and f.suggested_fix != retrieval.NO_ROOM[1]
    }
    scope = replace(scope, must_visit_ids=[p for p in scope.must_visit_ids if p not in conflicted])
    repaired = repair.repair(
        repair.retimed(checked.output, plan), findings, scope, repair.travel_gaps(plan)
    )
    if repaired.output is None:
        return Assessed(None, [], findings, step8, dropped + repaired.fixes)
    if repaired.fixes:
        plan, findings = await evaluate(job, request, repaired.output)
    return Assessed(repaired.output, plan, findings, step8, dropped + repaired.fixes)


def add_usage(first: TokenUsage | None, second: TokenUsage | None) -> UsageMetadata | None:
    """Both calls' reported counts; a count neither call reported stays null (FR-038 AC2)."""
    if first is None and second is None:
        return None

    def total(name: str) -> int | None:
        counts = [getattr(u, name) for u in (first, second) if u and getattr(u, name) is not None]
        return sum(counts) if counts else None

    return UsageMetadata(
        input_tokens=total("input_tokens"),
        output_tokens=total("output_tokens"),
        thinking_tokens=total("thinking_tokens"),
    )


async def finish(
    job: Job,
    request: GenerationRequest,
    provider: ModelProvider,
    first: Assessed,
    *,
    usage: TokenUsage | None,
    metadata: ModelMetadata,
) -> None:
    """Step 10's decision on the first answer: save it, or make the one repair call."""
    if first.usable and not first.errors_remain:
        await save(
            job,
            first.plan,
            first.findings,
            outcome="model_repaired" if first.fixes else "model",
            usage=usage,
            validation_summary=first.step8,
            metadata=metadata,
            deterministic_repairs=first.fixes,
        )
        return
    await repair_call(job, request, provider, first, usage=usage, metadata=metadata)


async def end_invalid_output(
    job: Job,
    request: GenerationRequest,
    answer_summary: dict[str, Any],
    *,
    provider: ModelProvider,
    usage: TokenUsage | None,
    metadata: ModelMetadata,
) -> None:
    """The one route for an answer the adapter could not read: the repair call, never a blind
    retry (TC-011). ``answer_summary`` is step 8 of the refused answer."""
    kind = answer_summary.get("kind") or "place check"
    logger.warning("generation %s invalid output: %s", job.generation_id, kind)
    first = Assessed(None, [], [], answer_summary, 0)
    await repair_call(job, request, provider, first, usage=usage, metadata=metadata)


async def repair_call(
    job: Job,
    request: GenerationRequest,
    provider: ModelProvider,
    first: Assessed,
    *,
    usage: TokenUsage | None,
    metadata: ModelMetadata,
) -> None:
    """The one model repair call (§8.13): repair_attempts 1, status repairing, then revalidate."""
    allowance = min(REPAIR_TIME_ALLOWANCE_S, REPAIR_DEADLINE_S - job.elapsed_ms() / 1000)
    if allowance <= 0:
        logger.warning("generation %s has no time left for the repair call", job.generation_id)
        await run_fallback(
            job,
            request,
            outcomes.INVALID_OUTPUT.reason,
            answer_summary=first.step8,
            usage=usage,
            metadata=metadata,
            deterministic_repairs=first.fixes,
        )
        return
    async with job.sessions() as session:
        await repository.mark_repairing(session, job.generation_id)
    context = RepairContext(
        invalid_output=first.output.model_dump_json() if first.output else "",
        findings=first.findings,
    )
    attempts = {"deterministic_repairs": first.fixes, "repair_attempts": 1}
    try:
        async with asyncio.timeout(allowance):
            result = await provider.generate_itinerary(
                request.model_copy(update={"repair_context": context})
            )
    except (ProviderError, TimeoutError) as exc:
        outcome = outcomes.resolve(exc) if isinstance(exc, ProviderError) else None
        logger.warning("generation %s repair call failed", job.generation_id)
        if outcome is not None and outcome.kind == "failed" and provider.name != "GROQ":
            await job.fail(outcome.reason, usage=usage)
            return
        step8 = first.step8
        if isinstance(exc, ProviderInvalidOutput):
            step8 = output_check.summary(kind=exc.kind)
        await run_fallback(
            job,
            request,
            outcomes.INVALID_OUTPUT.reason,
            answer_summary=step8,
            usage=usage,
            metadata=metadata,
            **attempts,
        )
        return

    used_model = result.model_id or provider.get_model_metadata().model_id
    if used_model != metadata.model_id:
        metadata = metadata.model_copy(update={"model_id": used_model})
        async with job.sessions() as session:
            await repository.record_model(session, job.generation_id, used_model)
    usage = add_usage(usage, result.usage)
    second = await assess(job, request, result.output)
    attempts["deterministic_repairs"] += second.fixes
    if second.usable:
        await save(
            job,
            second.plan,
            second.findings,
            outcome="model_repaired",
            usage=usage,
            validation_summary=second.step8,
            metadata=metadata,
            **attempts,
        )
        return
    # An answer step 8 could not read is a failed repair call; a readable one is unresolved.
    cause = outcomes.INVALID_OUTPUT if second.step8["kind"] else outcomes.UNRESOLVED
    await run_fallback(
        job,
        request,
        cause.reason,
        answer_summary=second.step8,
        usage=usage,
        metadata=metadata,
        **attempts,
    )


async def end_with(
    job: Job, request: GenerationRequest, outcome: outcomes.Outcome, metadata: ModelMetadata
) -> None:
    """The outcome table's verdict (``outcomes.resolve``): the labelled rule-based plan, or failed
    with nothing written to the itinerary tables (FR-037 AC3)."""
    if outcome.kind == "failed":
        await job.fail(outcome.reason)
    else:
        await run_fallback(job, request, outcome.reason, metadata=metadata)


async def run_fallback(
    job: Job,
    request: GenerationRequest,
    provider_failure: FailureReason | None,
    *,
    answer_summary: dict[str, Any] | None = None,
    usage: TokenUsage | None = None,
    metadata: ModelMetadata | None = None,
    deterministic_repairs: int = 0,
    repair_attempts: int = 0,
) -> None:
    """The rule-based plan through steps 8 to 11; ``provider_failure`` is None for mode rule_based.

    The summary keeps the refused answer's step-8 counts; errors, warnings and infos are the saved
    plan's. Only if this plan is unusable too does the generation end failed /
    unresolved_validation (§6.4).
    """
    await job.mark_validating()
    active = await job.active_ids(request)
    # Only places still active, so step 8 has nothing to reject in the rule-based plan.
    shortlist = [place for place in request.shortlist if str(place.place_id) in active]
    try:
        output = fallback_planner.plan_rule_based(
            request.model_copy(update={"shortlist": shortlist})
        )
    except fallback_planner.NoPlanError:
        await job.fail("unresolved_validation", usage=usage)
        return
    checked = output_check.check_output(output, active, request.trip.num_days)
    counts = output_check.summary(checked)
    validation_summary = {**counts, **(answer_summary or {})}
    validation_summary.update({key: counts[key] for key in SEVERITY_KEYS.values()})
    if provider_failure is not None:
        validation_summary["provider_failure"] = provider_failure
    if not checked.usable:
        await job.fail("unresolved_validation", usage=usage, validation_summary=validation_summary)
        return
    plan, findings = await evaluate(job, request, checked.output)
    await save(
        job,
        plan,
        findings,
        outcome="fallback_rule_based",
        usage=usage,
        validation_summary=validation_summary,
        metadata=metadata,
        deterministic_repairs=deterministic_repairs,
        repair_attempts=repair_attempts,
    )


async def save(
    job: Job,
    plan: list[PlannedDay],
    findings: list[Finding],
    *,
    outcome: CompletedOutcome,
    usage: TokenUsage | None,
    validation_summary: dict[str, Any],
    metadata: ModelMetadata | None,
    deterministic_repairs: int = 0,
    repair_attempts: int = 0,
) -> None:
    """Step 11: save the plan of step 9, its warnings and the record together. The record's
    counts add the plan's findings to step 8's."""
    repairs = {"deterministic_repairs": deterministic_repairs, "repair_attempts": repair_attempts}
    async with job.sessions() as session:
        trip = None
        if job.request_hash is not None:
            trip = await trips_service.get_trip(session, job.user_id, job.trip_id)
            current_hash = records.request_hash(
                {
                    "trip_id": str(job.trip_id),
                    "scope": job.scope.kind,
                    "day_number": job.scope.day_number,
                    "mode": "rule_based" if job.rule_based else "ai",
                    "plan_revision": trip.plan_revision,
                }
            )
            if current_hash != job.request_hash:
                raise StalePlan()
        if trip is not None and trip.has_itinerary:
            _, findings = await itinerary_service.save_regenerated_plan(
                session,
                job.trip_id,
                job.user_id,
                plan,
                job.generation_id,
                base_revision=trip.plan_revision,
                scope_day_number=job.scope.day_number,
                origin="fallback_rule_based" if outcome == "fallback_rule_based" else "model",
                blocking_codes=BLOCKING,
                repairs=repairs,
            )
        else:
            counts = Counter(SEVERITY_KEYS[finding.severity] for finding in findings)
            await itinerary_service.save_generated_plan(
                session,
                job.trip_id,
                job.user_id,
                plan,
                job.generation_id,
                validation_summary={
                    **{key: counts[key] for key in SEVERITY_KEYS.values()},
                    **repairs,
                },
                origin="fallback_rule_based" if outcome == "fallback_rule_based" else "model",
                findings=findings,
                base_revision=trip.plan_revision if trip else None,
            )
        counts = Counter(SEVERITY_KEYS[finding.severity] for finding in findings)
        validation_summary = {
            **validation_summary,
            **{key: validation_summary.get(key, 0) + counts[key] for key in SEVERITY_KEYS.values()},
        }
        await repository.complete(
            session,
            job.generation_id,
            outcome=outcome,
            usage=usage,
            latency_ms=job.elapsed_ms(),
            validation_summary=validation_summary,
            adapter_version=metadata.adapter_version if metadata else None,
            model_version=metadata.model_version if metadata else None,
            **repairs,
        )
    logger.info("generation %s completed %s in %d ms", job.generation_id, outcome, job.elapsed_ms())


async def plan_findings(
    session: AsyncSession,
    request: GenerationRequest,
    plan: Sequence[PlannedDay],
    trip_id: UUID,
    user_id: UUID,
) -> list[Finding]:
    """The merged validator on the recalculated plan; MUST_VISIT_MISSING gets its reason."""
    must_visit = [str(place_id) for place_id in request.must_visit_place_ids]
    ids = {*request.shortlist_ids(), *must_visit}
    names = await places_service.active_place_names(
        session, request.trip.destination_id, [UUID(place_id) for place_id in sorted(ids)]
    )
    timezone, hours = await itinerary_service.validation_hours(session, request.trip.destination_id)
    trip = await trips_service.get_trip(session, user_id, trip_id)
    ctx = ValidationContext(
        start_date=request.trip.start_date,
        end_date=request.trip.end_date,
        places={str(place_id): name for place_id, name in names.items()},
        must_visit_ids=frozenset(must_visit),
        shortlist_ids=frozenset(request.shortlist_ids()),
        pace=request.preferences.pace,
        timezone=timezone,
        opening_hours=hours,
        cost_inputs=await itinerary_service.validation_cost_inputs(session, trip),
    )
    findings = validate(plan, ctx)
    if not any(finding.code == "MUST_VISIT_MISSING" for finding in findings):
        return findings
    prefs = await trips_service.get_preferences(session, user_id, trip_id)
    reasons = await retrieval.must_visit_reasons(session, trip, prefs)

    def with_reason(finding: Finding) -> Finding:
        if finding.code != "MUST_VISIT_MISSING":
            return finding
        reason, fix = reasons.get(str(finding.place_id), retrieval.NO_ROOM)
        message = f"{finding.message} {reason}"[:500]
        return finding.model_copy(update={"message": message, "suggested_fix": fix})

    return [with_reason(finding) for finding in findings]


def routing_for(session: AsyncSession) -> schedule.Routing:
    return RoutingService(RouteCacheRepository(session), get_client())


async def accept_result(
    job: Job,
    request: GenerationRequest,
    provider: ModelProvider,
    result: ProviderResult[ItineraryOutput],
    metadata: ModelMetadata,
) -> None:
    """The shared validation and single repair path for either provider's candidate."""
    if result.model_id is not None:
        metadata = metadata.model_copy(update={"model_id": result.model_id})
        async with job.sessions() as session:
            await repository.record_model(session, job.generation_id, result.model_id)
    await job.mark_validating()
    first = await assess(job, request, result.output)
    await finish(job, request, provider, first, usage=result.usage, metadata=metadata)


async def try_groq(
    job: Job, request: GenerationRequest, provider_started: float, primary_metadata: ModelMetadata
) -> bool:
    """Try the optional second provider once, after Gemini's entire initial attempt failed.

    Its adapter may retry transport once. Both calls share step 7's original 70 s, preserving
    the repair and save reserves; there is never another provider switch during repair.
    """
    provider = factory.get_groq_provider()
    allowance = min(
        GEMINI_TIME_ALLOWANCE_S - (time.perf_counter() - provider_started),
        REPAIR_DEADLINE_S - job.elapsed_ms() / 1000,
    )
    if provider is None or allowance <= 0:
        return False
    metadata = provider.get_model_metadata()
    breaker = factory.breaker_for(provider)
    if breaker.state == "open" and breaker.open_reason is not None:
        # No Groq request was made; keep the identity of the last attempted provider.
        await run_fallback(job, request, breaker.open_reason, metadata=primary_metadata)
        return True
    async with job.sessions() as session:
        await repository.record_provider(
            session, job.generation_id, metadata, getattr(provider, "generation_settings", {})
        )
    try:
        async with asyncio.timeout(allowance):
            result = await provider.generate_itinerary(request)
    except ProviderInvalidOutput as exc:
        breaker.record_success()
        await job.mark_validating()
        await end_invalid_output(
            job,
            request,
            output_check.summary(kind=exc.kind),
            provider=provider,
            usage=None,
            metadata=metadata,
        )
    except (ProviderError, TimeoutError) as exc:
        failure = exc if isinstance(exc, ProviderError) else ProviderTimeout()
        breaker.record_failure(failure)
        await run_fallback(job, request, failure.failure_reason, metadata=metadata)
    else:
        breaker.record_success()
        await accept_result(job, request, provider, result, metadata)
    return True


async def add_costs(
    session: AsyncSession, days: Sequence[PlannedDay], trip_id: UUID, user_id: UUID
) -> list[PlannedDay]:
    """BF-01 to BF-04 from the ``places`` rows, so nothing the model wrote can become a price."""
    trip = await trips_service.get_trip(session, user_id, trip_id)
    currency = itinerary_service.trip_currency(trip)
    ids = {UUID(item.place_id) for day in days for item in day.items}
    rows = await places_repository.active_places_by_ids(session, trip.destination_id, list(ids))
    places = {str(row.id): row for row in rows}

    def priced(item: PlannedItem) -> PlannedItem:
        place = places.get(item.place_id)  # gone inactive since step 8: its price is unknown
        cost = engine.ITEM_UNAVAILABLE
        if place is not None:
            cost = engine.item_cost(
                place, adults=trip.adults, children=trip.children, currency=currency
            )
        return replace(
            item,
            cost_min=None if cost.lo is None else engine.from_minor(cost.lo),
            cost_max=None if cost.hi is None else engine.from_minor(cost.hi),
            cost_currency=currency,
            cost_label=cost.label,
        )

    return [replace(day, items=[priced(item) for item in day.items]) for day in days]


async def recalculate(
    session: AsyncSession,
    output: ItineraryOutput,
    request: GenerationRequest,
    trip_id: UUID,
    user_id: UUID,
) -> list[PlannedDay]:
    """Step 9. Only what this returns is saved, so no saved time or cost is a model value."""
    days = await schedule.recalculate(
        output.days,
        {str(place.place_id): place for place in request.shortlist},
        routing_for(session),
        request.preferences.pace,
        mode=request.preferences.transport_pref,
    )
    return await add_costs(session, days, trip_id, user_id)


async def run(generation_id: UUID, provider: ModelProvider, sessions: Sessions) -> None:
    started = time.perf_counter()
    async with sessions() as session:
        row = await repository.mark_running(session, generation_id)
        job = Job(
            generation_id,
            sessions,
            row.trip_id,
            row.user_id,
            started,
            scope=Scope(
                kind="day" if row.scope == "day" else "full", day_number=row.scope_day_number
            ),
            request_hash=row.request_hash,
            rule_based=row.model_id == fallback_planner.MODEL_ID,
        )
        prompt_template_id, prompt_version = row.prompt_template_id, row.prompt_version
        rule_based = row.model_id == fallback_planner.MODEL_ID  # IMD-43: set at insert

    retrieved = None
    if not rule_based:  # mode rule_based makes no model call, embeddings included (FR-036)
        retrieved = await request_builder.retrieve(job.trip_id, job.user_id, provider, sessions)
        logger.info(
            "generation %s retrieval %s in %d ms",
            generation_id,
            retrieved.mode,
            retrieved.retrieval_ms,
        )
        async with sessions() as session:
            await repository.record_retrieval(
                session,
                generation_id,
                mode=retrieved.mode,
                embedding_model_id=retrieved.embedding_model_id,
                retrieval_ms=retrieved.retrieval_ms,
            )

    async with sessions() as session:
        request = await request_builder.build(
            session,
            trip_id=job.trip_id,
            user_id=job.user_id,
            prompt_template_id=prompt_template_id,
            prompt_version=prompt_version,
            retrieved=retrieved,
            scope=job.scope,
        )
    if rule_based:
        await run_fallback(job, request, None)
        return

    metadata = provider.get_model_metadata()
    breaker = factory.breaker_for(provider)
    provider_started = time.perf_counter()
    if breaker.state == "open" and breaker.open_reason is not None:
        logger.warning("generation %s skips the provider: breaker open", generation_id)
        if (
            provider.name == "GEMINI"
            and breaker.open_reason != "config_error"
            and await try_groq(job, request, provider_started, metadata)
        ):
            return
        await end_with(job, request, outcomes.resolve_open_breaker(breaker.open_reason), metadata)
        return
    try:
        passages_built = len(request.passage_ids())
        request, truncated_count = limits.enforce_input_limit(
            request,
            get_settings().ai_max_input_tokens,
            request_builder.passage_similarities(retrieved) if retrieved else {},
        )
        passages_sent = len(request.passage_ids())
        # PD-IMP-301-2: not on the protocol until ProviderResult has the field; MOCK sends none.
        sent = getattr(provider, "generation_settings", {})
        async with sessions() as session:
            await repository.record_settings(
                session,
                generation_id,
                {
                    **sent,
                    "truncated_count": truncated_count,
                    "passages_sent": passages_sent,
                    "passages_dropped": passages_built - passages_sent,
                },
            )
        result = await provider.generate_itinerary(request)
    except ProviderInvalidOutput as exc:
        breaker.record_success()  # the service answered
        await job.mark_validating()
        await end_invalid_output(
            job,
            request,
            output_check.summary(kind=exc.kind),
            provider=provider,
            usage=None,
            metadata=metadata,
        )
        return
    except ProviderError as exc:
        breaker.record_failure(exc)
        logger.warning("generation %s provider error %s", generation_id, exc.failure_reason)
        if (
            provider.name == "GEMINI"
            and isinstance(exc, GROQ_TRIGGERS)
            and await try_groq(job, request, provider_started, metadata)
        ):
            return
        await end_with(job, request, outcomes.resolve(exc), metadata)
        return

    if result.fallback_from is None:
        breaker.record_success()
    else:  # IMD-222: the configured model failed; the fallback's answer must not close the breaker
        breaker.record_failure(FALLBACK_CAUSES[result.fallback_from]())
    await accept_result(job, request, provider, result, metadata)
