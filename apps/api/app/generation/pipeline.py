"""Generation pipeline (§8.2 steps 1 to 11; IMP-305).

mark_running -> retrieval (A1 §6.7, never fails the job) -> build the request from the ranked
shortlist (steps 2 to 5) -> input limit -> record
the settings -> provider.generate_itinerary (steps 6, 7) -> mark_validating -> steps 8 and 9 -> save
the plan and complete the record in one transaction (step 11). Each status change is its own short
transaction, and none stays open across the provider call (§5.8). Step 8 is
``app.validation.output_check`` (IMP-306); step 9 is ``recalculate`` (IMP-308). Output
that cannot be saved goes through ``end_invalid_output``; repair is IMP-502, which sends the same
request and so the same passages. Trip completeness (step 1) is checked by API-22 before the row
exists.

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
with ``provider_quota_exhausted`` or ``config_error``. Each generation's provider result is
recorded on the breaker once, after the adapter's retries; retrieval's embeddings never are.

Never logged: the request built for the provider, its raw output, notes or prompt text (FR-125).
"""

import logging
import time
from collections import Counter
from collections.abc import Callable, Sequence
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, replace
from typing import Any, Final, Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import factory, limits
from app.ai.errors import ProviderError, ProviderInvalidOutput
from app.ai.providers.base import ModelProvider
from app.budget import engine
from app.core.config import get_settings
from app.generation import fallback_planner, repository, request_builder, retrieval, schedule
from app.generation.records import FailureReason, TokenUsage
from app.itinerary import service as itinerary_service
from app.itinerary.schemas import PlannedDay, PlannedItem
from app.places import repository as places_repository
from app.places import service as places_service
from app.routing.cache import RouteCacheRepository
from app.routing.client import get_client
from app.routing.service import RoutingService
from app.schemas.ai import GenerationRequest, ItineraryOutput, ModelMetadata
from app.trips import service as trips_service
from app.validation import output_check
from app.validation.rules import Finding, ValidationContext
from app.validation.validator import validate

logger = logging.getLogger(__name__)

Sessions = Callable[[], AbstractAsyncContextManager[AsyncSession]]

SEVERITY_KEYS: Final = {"error": "errors", "warning": "warnings", "info": "infos"}


@dataclass
class Job:
    """One generation run: its row, its transactions and its clock."""

    generation_id: UUID
    sessions: Sessions
    trip_id: UUID
    user_id: UUID
    started: float
    validating: bool = False

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


async def end_invalid_output(
    job: Job,
    request: GenerationRequest,
    answer_summary: dict[str, Any],
    *,
    usage: TokenUsage | None,
    metadata: ModelMetadata,
) -> None:
    """The one route for an answer that cannot be saved; it is never retried blindly.

    The rule-based plan replaces it (fallback_reason invalid_output, IMD-22) until IMP-502 adds
    the repair call in front of this route. ``answer_summary`` is step 8 of the refused answer.
    """
    kind = answer_summary.get("kind") or "place check"
    logger.warning("generation %s invalid output: %s", job.generation_id, kind)
    await run_fallback(
        job,
        request,
        "invalid_output",
        answer_summary=answer_summary,
        usage=usage,
        metadata=metadata,
    )


async def run_fallback(
    job: Job,
    request: GenerationRequest,
    provider_failure: FailureReason | None,
    *,
    answer_summary: dict[str, Any] | None = None,
    usage: TokenUsage | None = None,
    metadata: ModelMetadata | None = None,
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
    await save(
        job,
        request,
        checked.output,
        outcome="fallback_rule_based",
        usage=usage,
        validation_summary=validation_summary,
        metadata=metadata,
    )


async def save(
    job: Job,
    request: GenerationRequest,
    output: ItineraryOutput,
    *,
    outcome: Literal["model", "fallback_rule_based"],
    usage: TokenUsage | None,
    validation_summary: dict[str, Any],
    metadata: ModelMetadata | None,
) -> None:
    """Steps 9 and 11: recalculate and validate, then save the plan, its warnings and the record
    together. The record's counts add the plan's findings to step 8's."""
    async with job.sessions() as session:
        plan = await recalculate(session, output, request, job.trip_id, job.user_id)
        findings = await plan_findings(session, request, plan, job.trip_id, job.user_id)
    counts = Counter(SEVERITY_KEYS[finding.severity] for finding in findings)
    plan_summary = {key: counts[key] for key in SEVERITY_KEYS.values()}
    validation_summary = {
        **validation_summary,
        **{key: validation_summary.get(key, 0) + plan_summary[key] for key in plan_summary},
    }
    async with job.sessions() as session:
        await itinerary_service.save_generated_plan(
            session,
            job.trip_id,
            job.user_id,
            plan,
            job.generation_id,
            validation_summary=plan_summary,
            origin=outcome,
            findings=findings,
        )
        await repository.complete(
            session,
            job.generation_id,
            outcome=outcome,
            usage=usage,
            latency_ms=job.elapsed_ms(),
            validation_summary=validation_summary,
            adapter_version=metadata.adapter_version if metadata else None,
            model_version=metadata.model_version if metadata else None,
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
    limits = request.limits
    ctx = ValidationContext(
        start_date=request.trip.start_date,
        end_date=request.trip.end_date,
        places={str(place_id): name for place_id, name in names.items()},
        must_visit_ids=frozenset(must_visit),
        shortlist_ids=frozenset(request.shortlist_ids()),
        pace_limits=(limits.max_items_per_day, limits.max_active_minutes_per_day),
    )
    findings = validate(plan, ctx)
    if not any(finding.code == "MUST_VISIT_MISSING" for finding in findings):
        return findings
    trip = await trips_service.get_trip(session, user_id, trip_id)
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
        job = Job(generation_id, sessions, row.trip_id, row.user_id, started)
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
        )
    if rule_based:
        await run_fallback(job, request, None)
        return

    metadata = provider.get_model_metadata()
    breaker = factory.breaker_for(provider)
    if breaker.state == "open" and breaker.open_reason is not None:
        logger.warning("generation %s skips the provider: breaker open", generation_id)
        if breaker.open_reason in ("provider_quota_exhausted", "config_error"):
            await job.fail(breaker.open_reason)  # IMD-44: no fallback
        else:
            await run_fallback(job, request, breaker.open_reason, metadata=metadata)
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
        await end_invalid_output(
            job, request, output_check.summary(kind=exc.kind), usage=None, metadata=metadata
        )
        return
    except ProviderError as exc:
        breaker.record_failure(exc)
        logger.warning("generation %s provider error %s", generation_id, exc.failure_reason)
        if exc.retryable:  # the adapter's retries are spent (§8.3): the rule-based plan
            await run_fallback(job, request, exc.failure_reason, metadata=metadata)
        else:  # quota and configuration errors keep their cause (IMD-44)
            await job.fail(exc.failure_reason)
        return

    breaker.record_success()
    await job.mark_validating()
    active = await job.active_ids(request)
    try:
        answer = output_check.apply_limits(
            result.output,
            trip_days=request.trip.num_days,
            max_items_per_day=request.limits.max_items_per_day,
        )
    except ProviderInvalidOutput as exc:
        await end_invalid_output(
            job, request, output_check.summary(kind=exc.kind), usage=result.usage, metadata=metadata
        )
        return

    checked = output_check.check_output(
        answer, active, request.trip.num_days, request.passage_ids()
    )
    if not checked.usable:
        await end_invalid_output(
            job, request, output_check.summary(checked), usage=result.usage, metadata=metadata
        )
        return

    await save(
        job,
        request,
        checked.output,
        outcome="model",
        usage=result.usage,
        validation_summary=output_check.summary(checked),
        metadata=metadata,
    )
