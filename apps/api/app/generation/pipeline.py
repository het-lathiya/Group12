"""Generation pipeline (§8.2 steps 1 to 11; IMP-305).

mark_running -> build the request from the ranked shortlist (steps 2 to 5) -> input limit -> record
the settings -> provider.generate_itinerary (steps 6, 7) -> mark_validating -> steps 8 and 9 -> save
the plan and complete the record in one transaction (step 11). Each status change is its own short
transaction, and none stays open across the provider call (§5.8). Steps 8 and 9 are hooks: IMP-306
adds the validator rules and IMP-308 the recalculation; repair and the fallback are IMP-401 to
IMP-403. Trip completeness (step 1) is checked by API-22 before the row exists.

Never logged: the request built for the provider, its raw output, notes or prompt text (FR-125).
"""

import logging
import time
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Final
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import limits
from app.ai.errors import ProviderError
from app.ai.providers.base import ModelProvider
from app.core.config import get_settings
from app.generation import repository, request_builder
from app.itinerary import service as itinerary_service
from app.schemas.ai import GenerationRequest, ItineraryOutput

logger = logging.getLogger(__name__)

Sessions = Callable[[], AbstractAsyncContextManager[AsyncSession]]

# No validator rules run before IMP-306, so the plan is saved with no findings.
NO_FINDINGS: Final = {"errors": 0, "warnings": 0, "infos": 0}


def output_problem(output: ItineraryOutput, request: GenerationRequest) -> str | None:
    """Step 8: why an answer cannot be saved (schema, day numbers or place IDs), or None.

    The hook of IMP-306, which adds the other rules and the counts.
    """
    try:
        ItineraryOutput.model_validate(output.model_dump())
    except ValidationError:
        return "schema"
    day_numbers = [day.day_number for day in output.days]
    if len(set(day_numbers)) != len(day_numbers) or max(day_numbers) > request.trip.num_days:
        return "day_numbers"
    if output.unknown_place_ids(request):
        return "unknown_place_ids"
    return None


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
        request = await request_builder.build(
            session,
            trip_id=trip_id,
            user_id=user_id,
            prompt_template_id=row.prompt_template_id,
            prompt_version=row.prompt_version,
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
    except ProviderError as exc:
        logger.warning("generation %s provider error %s", generation_id, exc.failure_reason)
        async with sessions() as session:
            await repository.fail(
                session, generation_id, exc.failure_reason, latency_ms=elapsed_ms()
            )
        return

    async with sessions() as session:
        await repository.mark_validating(session, generation_id)

    problem = output_problem(result.output, request)
    if problem is not None:
        logger.warning("generation %s invalid output: %s", generation_id, problem)
        async with sessions() as session:
            await repository.fail(
                session,
                generation_id,
                "invalid_output",
                usage=result.usage,
                latency_ms=elapsed_ms(),
            )
        return

    plan = recalculate(result.output)
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
            validation_summary=NO_FINDINGS,
            adapter_version=metadata.adapter_version,
            model_version=metadata.model_version,
        )
    logger.info("generation %s completed in %d ms", generation_id, elapsed_ms())
