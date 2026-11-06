"""Generation pipeline (§8.2 steps 1 to 11; IMP-305).

mark_running -> retrieval (A1 §6.7, never fails the job) -> build the request from the ranked
shortlist (steps 2 to 5) -> input limit -> record
the settings -> provider.generate_itinerary (steps 6, 7) -> mark_validating -> steps 8 and 9 -> save
the plan and complete the record in one transaction (step 11). Each status change is its own short
transaction, and none stays open across the provider call (§5.8). Step 8 is
``app.validation.output_check`` (IMP-306); step 9 is a hook for the recalculation of IMP-308. Output
that cannot be saved goes through ``end_invalid_output``, where IMP-402 adds the fallback; repair is
IMP-502. Trip completeness (step 1) is checked by API-22 before the row exists.

Never logged: the request built for the provider, its raw output, notes or prompt text (FR-125).
"""

import logging
import time
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Final
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import limits
from app.ai.errors import InvalidOutputKind, ProviderError, ProviderInvalidOutput
from app.ai.providers.base import ModelProvider
from app.core.config import get_settings
from app.generation import repository, request_builder
from app.generation.records import TokenUsage
from app.itinerary import service as itinerary_service
from app.places import service as places_service
from app.schemas.ai import ItineraryOutput
from app.validation import output_check

logger = logging.getLogger(__name__)

Sessions = Callable[[], AbstractAsyncContextManager[AsyncSession]]

# The rules of step 9 arrive with IMP-308 and IMP-309, so the plan is saved with no findings.
NO_FINDINGS: Final = {"errors": 0, "warnings": 0, "infos": 0}


async def end_invalid_output(
    generation_id: UUID,
    sessions: Sessions,
    kind: InvalidOutputKind | None,
    validation_summary: dict[str, object],
    *,
    usage: TokenUsage | None,
    latency_ms: int,
) -> None:
    """The one route for an answer that cannot be saved; it is never retried blindly.

    shortcut: ends failed with invalid_output (PD-IMP-306-1); IMP-402 replaces this body with the
    rule-based fallback (fallback_reason invalid_output, failure_reason null, IMD-22).
    """
    logger.warning("generation %s invalid output: %s", generation_id, kind or "place check")
    async with sessions() as session:
        await repository.fail(
            session,
            generation_id,
            "invalid_output",
            usage=usage,
            latency_ms=latency_ms,
            validation_summary=validation_summary,
        )


def recalculate(output: ItineraryOutput) -> ItineraryOutput:
    """Step 9, the hook of IMP-308. Only what this returns is saved.

    shortcut: times pass through as the model gave them and costs stay null; IMP-308 recalculates
    them here.
    """
    return output


async def run(generation_id: UUID, provider: ModelProvider, sessions: Sessions) -> None:
    started = time.perf_counter()

    def elapsed_ms() -> int:
        return round((time.perf_counter() - started) * 1000)

    async with sessions() as session:
        row = await repository.mark_running(session, generation_id)
        trip_id, user_id = row.trip_id, row.user_id
        prompt_template_id, prompt_version = row.prompt_template_id, row.prompt_version

    # shortcut: kept in this function only; IMP-316 writes mode, model and ms to the record.
    retrieved = await request_builder.retrieve(trip_id, user_id, provider, sessions)
    logger.info(
        "generation %s retrieval %s in %d ms", generation_id, retrieved.mode, retrieved.retrieval_ms
    )

    async with sessions() as session:
        request = await request_builder.build(
            session,
            trip_id=trip_id,
            user_id=user_id,
            prompt_template_id=prompt_template_id,
            prompt_version=prompt_version,
            retrieved=retrieved,
        )

    try:
        request, truncated_count = limits.enforce_input_limit(
            request, get_settings().ai_max_input_tokens
        )
        # PD-IMP-301-2: not on the protocol until ProviderResult has the field; MOCK sends none.
        sent = getattr(provider, "generation_settings", {})
        async with sessions() as session:
            await repository.record_settings(
                session, generation_id, {**sent, "truncated_count": truncated_count}
            )
        result = await provider.generate_itinerary(request)
    except ProviderInvalidOutput as exc:
        await end_invalid_output(
            generation_id,
            sessions,
            exc.kind,
            output_check.summary(kind=exc.kind),
            usage=None,
            latency_ms=elapsed_ms(),
        )
        return
    except ProviderError as exc:
        logger.warning("generation %s provider error %s", generation_id, exc.failure_reason)
        async with sessions() as session:
            await repository.fail(
                session, generation_id, exc.failure_reason, latency_ms=elapsed_ms()
            )
        return

    async with sessions() as session:
        await repository.mark_validating(session, generation_id)
        # Read again: a place can go inactive while the provider is answering.
        active = await places_service.active_place_names(
            session, request.trip.destination_id, [p.place_id for p in request.shortlist]
        )

    try:
        answer = output_check.apply_limits(
            result.output,
            trip_days=request.trip.num_days,
            max_items_per_day=request.limits.max_items_per_day,
        )
    except ProviderInvalidOutput as exc:
        await end_invalid_output(
            generation_id,
            sessions,
            exc.kind,
            output_check.summary(kind=exc.kind),
            usage=result.usage,
            latency_ms=elapsed_ms(),
        )
        return

    checked = output_check.check_output(answer, {str(id_) for id_ in active}, request.trip.num_days)
    validation_summary = output_check.summary(checked)
    if not checked.usable:
        await end_invalid_output(
            generation_id,
            sessions,
            None,
            validation_summary,
            usage=result.usage,
            latency_ms=elapsed_ms(),
        )
        return

    plan = recalculate(checked.output)
    metadata = provider.get_model_metadata()
    async with sessions() as session:
        await itinerary_service.save_generated_plan(
            session, trip_id, user_id, plan, generation_id, validation_summary=NO_FINDINGS
        )
        await repository.complete(
            session,
            generation_id,
            outcome="model",
            usage=result.usage,
            latency_ms=elapsed_ms(),
            validation_summary=validation_summary,
            adapter_version=metadata.adapter_version,
            model_version=metadata.model_version,
        )
    logger.info("generation %s completed in %d ms", generation_id, elapsed_ms())
