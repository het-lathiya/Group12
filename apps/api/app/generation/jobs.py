"""In-process generation jobs (IMD-12; §6.4, §8.2): asyncio tasks, at most two at a time, each
under a 120-second overall timeout, and the stale-job reaper.

The job runner classifies only the timeout and unexpected errors (``internal``); provider errors
are classified by the pipeline. A timed-out or reaped row is marked with
``validation_summary.timed_out`` so API-23 shows "Generation timed out." (IMD-22). A timeout that
fires after the plan's commit changes nothing: the row stays completed with its plan.
"""

import asyncio
import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated, Final
from uuid import UUID

from fastapi import Depends

from app.ai.providers.base import ModelProvider
from app.db.session import transaction
from app.generation import pipeline, records, repository
from app.generation.pipeline import Sessions

logger = logging.getLogger(__name__)

MAX_CONCURRENT_JOBS: Final = 2
PIPELINE_TIMEOUT_S: Final = 120
STALE_AFTER: Final = timedelta(seconds=150)
REAPER_INTERVAL_S: Final = 60
TIMED_OUT: Final = {"timed_out": True}

_slots = asyncio.Semaphore(MAX_CONCURRENT_JOBS)
_tasks: set[asyncio.Task[None]] = set()  # strong references, so a running task is not collected


async def run(
    generation_id: UUID, provider: ModelProvider, sessions: Sessions = transaction
) -> None:
    async with _slots:
        try:
            async with asyncio.timeout(PIPELINE_TIMEOUT_S):
                await pipeline.run(generation_id, provider, sessions)
        except TimeoutError:
            if await _fail_internal(generation_id, sessions, TIMED_OUT):
                logger.error(
                    "generation %s timed out after %d s", generation_id, PIPELINE_TIMEOUT_S
                )
        except Exception:
            logger.exception("generation %s failed with an unexpected error", generation_id)
            await _fail_internal(generation_id, sessions, None)


async def _fail_internal(
    generation_id: UUID, sessions: Sessions, validation_summary: dict[str, bool] | None
) -> bool:
    """Fail the row; False when it had already ended, which leaves it as it is."""
    async with sessions() as session:
        try:
            await repository.fail(
                session, generation_id, "internal", validation_summary=validation_summary
            )
        except records.IllegalTransitionError as exc:
            logger.info("generation %s had already ended %s", generation_id, exc.current)
            return False
    return True


def submit(generation_id: UUID, provider: ModelProvider) -> None:
    """Start the job; call it only after the queued row is committed (§6.4)."""
    task = asyncio.create_task(run(generation_id, provider))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


Submit = Callable[[UUID, ModelProvider], None]


def get_submit() -> Submit:
    """FastAPI dependency; tests override it to run the job themselves."""
    return submit


SubmitDep = Annotated[Submit, Depends(get_submit)]


async def reap_forever() -> None:
    """At start-up and every 60 s: fail active rows older than 150 s (§6.4)."""
    next_purge = 0.0
    while True:
        try:
            async with transaction() as session:
                count = await repository.fail_stale(
                    session, STALE_AFTER, validation_summary=TIMED_OUT
                )
            if count:
                logger.warning("reaper failed %d stale generations", count)
            if time.monotonic() >= next_purge:
                async with transaction() as session:
                    purged = await repository.purge_expired(session, datetime.now(UTC))
                next_purge = time.monotonic() + 86400
                if purged:
                    logger.info("purged %d expired generation records", purged)
        except Exception:  # the loop must survive a database outage; the next round retries
            logger.exception("generation reaper round failed")
        await asyncio.sleep(REAPER_INTERVAL_S)
