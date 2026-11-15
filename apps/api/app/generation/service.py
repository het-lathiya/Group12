"""Generation service (MOD-B06): start a generation (API-22) and read its status (API-23).

Create rules of §6.4, in order: trip owned and not archived; trip complete; no current itinerary;
for mode ai only, the AI notice acknowledged (IMD-24). Mode rule_based (IMP-402) stores the
configured provider name with model_id rule_based_planner_v1, which is how the job and API-23 know
the mode and why it never counts against the AI caps (IMD-43). The daily caps
(IMP-511) are added by their card. ``request_hash`` covers {trip_id, scope, day_number, mode,
plan_revision}: the same request while one is active returns that generation, a different one is
refused with GENERATION_IN_PROGRESS.
"""

import asyncio
import math
from datetime import UTC, datetime, timedelta
from typing import Final
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.factory import GENERATE_TEMPLATE_ID
from app.ai.prompts import registry
from app.ai.providers.base import ModelProvider
from app.auth import service as auth_service
from app.core.config import get_settings
from app.core.errors import (
    Conflict,
    GenerationInProgress,
    InvalidEdit,
    NotFound,
    QuotaReached,
    StalePlan,
    ValidationFailed,
)
from app.core.flags import is_enabled
from app.db.models import AiGeneration
from app.generation import fallback_planner, jobs, outcomes, records, repository
from app.generation.schemas import GenerationOut, GenerationStartIn, RegenerateIn
from app.itinerary import service as itinerary_service
from app.itinerary import versions
from app.schemas.common import ErrorDetail
from app.trips import preference_mapping
from app.trips import service as trips_service
from app.validation.schemas import ValidationSummary

RULE_BASED_MODEL_ID: Final = fallback_planner.MODEL_ID
TIMED_OUT_MESSAGE: Final = "Generation timed out."
_quota_lock = asyncio.Lock()  # IMD-12: one process; serialise count + insert across trips.


def utc_day(now: datetime) -> tuple[datetime, datetime]:
    start = now.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)


async def check_daily_cap(session: AsyncSession, user_id: UUID, now: datetime) -> None:
    start, reset = utc_day(now)
    user_count, global_count = await repository.daily_usage(session, user_id, start, reset)
    settings = get_settings()
    scope = (
        "global"
        if global_count >= settings.ai_daily_generations_global
        else ("user" if user_count >= settings.ai_daily_generations_per_user else None)
    )
    if scope:
        raise QuotaReached(
            "AI generation is paused for today. Build a rule-based plan or try again after the reset.",
            details=[
                ErrorDetail(field="scope", message=scope),
                ErrorDetail(field="reset_at", message=reset.isoformat().replace("+00:00", "Z")),
                ErrorDetail(field="mode", message="rule_based"),
            ],
            retry_after_s=max(1, math.ceil((reset - now).total_seconds())),
        )


async def start_generation(
    session: AsyncSession,
    user_id: UUID,
    trip_id: UUID,
    body: GenerationStartIn,
    provider: ModelProvider,
    submit: jobs.Submit,
) -> tuple[GenerationOut, bool]:
    """Returns the generation and whether it is new (202) rather than already active (200)."""
    return await _start(session, user_id, trip_id, body, provider, submit)


async def start_regeneration(
    session: AsyncSession,
    user_id: UUID,
    trip_id: UUID,
    body: RegenerateIn,
    provider: ModelProvider,
    submit: jobs.Submit,
    *,
    day_number: int | None = None,
) -> tuple[GenerationOut, bool]:
    """API-30/31 share API-22's job, idempotency and quota protocol (IMP-607)."""
    if not is_enabled(get_settings(), "regeneration"):
        raise NotFound()
    return await _start(session, user_id, trip_id, body, provider, submit, day_number=day_number)


async def _start(
    session: AsyncSession,
    user_id: UUID,
    trip_id: UUID,
    body: GenerationStartIn | RegenerateIn,
    provider: ModelProvider,
    submit: jobs.Submit,
    *,
    day_number: int | None = None,
) -> tuple[GenerationOut, bool]:
    await repository.lock_trip(session, trip_id, user_id)  # serialises concurrent starts
    trip = await trips_service.get_trip(session, user_id, trip_id)  # NotFound if not the caller's
    if trip.status == "archived":
        raise Conflict("This trip is archived. Restore it before generating a plan.")
    # Title, destination, dates and adults are NOT NULL and checked on save (FR-008); only the
    # preferences row can be missing (IMD-25).
    if not (await trips_service.get_preferences(session, user_id, trip_id)).saved:
        raise ValidationFailed(
            details=[ErrorDetail(field="preferences", message="Save the trip's preferences.")]
        )
    regenerating = isinstance(body, RegenerateIn)
    if isinstance(body, RegenerateIn):
        if not trip.has_itinerary:
            raise Conflict("This trip has no itinerary to regenerate.")
        if body.plan_revision != trip.plan_revision:
            raise StalePlan()
        if day_number is not None and not 1 <= day_number <= trip.num_days:
            raise InvalidEdit("The day is outside this trip.")
    elif trip.has_itinerary:
        raise Conflict("This trip already has an itinerary. Regenerate it instead.")
    if body.mode == "ai" and not await auth_service.ai_notice_acknowledged(session, user_id):
        raise ValidationFailed(
            details=[ErrorDetail(field="ai_notice", message="Acknowledge the AI notice first.")]
        )

    request_hash = records.request_hash(
        {
            "trip_id": str(trip_id),
            "scope": "day" if day_number is not None else "full",
            "day_number": day_number,
            "mode": body.mode,
            "plan_revision": trip.plan_revision,
        }
    )
    active = await repository.find_active_for_trip(session, trip_id)
    if active is not None:
        if active.request_hash != request_hash:
            # IMD-119: the generate page resumes polling this id (§7.5.6).
            raise GenerationInProgress(
                details=[ErrorDetail(field="generation_id", message=str(active.id))]
            )
        return await _to_out(session, active), False

    async with _quota_lock:
        if body.mode == "ai":
            await check_daily_cap(session, user_id, datetime.now(UTC))
        metadata = provider.get_model_metadata()
        template = registry.load(GENERATE_TEMPLATE_ID)
        generation_id = await repository.create_queued(
            session,
            trip_id=trip_id,
            user_id=user_id,
            provider=metadata.provider,
            model_id=RULE_BASED_MODEL_ID if body.mode == "rule_based" else metadata.model_id,
            prompt_template_id=template.template_id,
            prompt_version=template.version,
            input_schema_version=template.meta.input_schema_version,
            output_schema_version=template.meta.output_schema_version,
            mapping_version=preference_mapping.MAPPING_VERSION,
            scope="day" if day_number is not None else "full",
            scope_day_number=day_number,
            request_hash=request_hash,
        )
        if regenerating:
            await versions.snapshot_before_regeneration(session, user_id, trip_id)
        row = await repository.get_for_user(session, generation_id, user_id)
        out = await _to_out(session, row)
        await session.commit()  # the job reads the row in its own transaction (§6.4)
    submit(generation_id, provider)
    return out, True


async def get_generation(
    session: AsyncSession, user_id: UUID, generation_id: UUID
) -> GenerationOut:
    row = await repository.get_for_user(session, generation_id, user_id)
    # Reaping refreshes this same row object in the session.
    await repository.fail_stale(
        session, jobs.STALE_AFTER, generation_id=generation_id, validation_summary=jobs.TIMED_OUT
    )
    return await _to_out(session, row)


async def _to_out(session: AsyncSession, row: AiGeneration) -> GenerationOut:
    summary = row.validation_summary or {}
    message, next_action = outcomes.MESSAGES.get(row.failure_reason or "", (None, None))
    if summary.get("timed_out"):
        message = TIMED_OUT_MESSAGE
    saved = await itinerary_service.saved_plan_for_generation(session, row.id)
    return GenerationOut.model_validate(
        {
            "id": row.id,
            "trip_id": row.trip_id,
            "scope": row.scope,
            "day_number": row.scope_day_number,
            "mode": "rule_based" if row.model_id == RULE_BASED_MODEL_ID else "ai",
            "status": row.status,
            "outcome": row.outcome,
            "failure_reason": row.failure_reason,
            "failure_message": message,
            "next_action": next_action,
            "fallback_reason": summary.get("provider_failure"),
            "provider": row.provider,
            "model_id": row.model_id,
            "prompt_version": row.prompt_version,
            "repair_attempts": row.repair_attempts,
            "deterministic_repairs": row.deterministic_repairs,
            "validation_summary": ValidationSummary(
                errors=summary.get("errors", 0),
                warnings=summary.get("warnings", 0),
                infos=summary.get("infos", 0),
            ),
            "latency_ms": row.latency_ms,
            "itinerary_version_id": saved.version_id if saved else None,
            "plan_revision": saved.plan_revision if saved else None,
            "created_at": row.created_at,
            "completed_at": row.completed_at,
            "retrieval_mode": row.retrieval_mode,
            "embedding_model_id": row.embedding_model_id,
            "retrieval_ms": row.retrieval_ms,
        }
    )
