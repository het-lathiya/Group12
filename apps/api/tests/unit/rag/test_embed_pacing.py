"""D3: paced embedding with a 429 backoff, a budget, a re-embed queue (live-local 2026-11-28).

Offline: the repository calls are replaced by an in-memory store, the provider by the MOCK adapter
with a scripted 429, and ``asyncio.sleep`` by a recorder, so no test waits.
"""

import logging
import uuid
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest

from app.ai.errors import (
    ProviderError,
    ProviderQuotaExhausted,
    ProviderRateLimited,
    ProviderUnavailable,
)
from app.ai.providers.mock import MockProvider
from app.places import live_jobs
from app.rag import service as rag_service
from app.rag.constants import RAG_EMBED_BATCH
from app.schemas.ai import EmbeddingResult

pytestmark = pytest.mark.asyncio

DESTINATION = uuid.uuid4()


class Store:
    """Chunks by id, ``None`` until embedded; stands in for ``app.rag.repository``."""

    def __init__(self, count: int) -> None:
        self.vectors: dict[uuid.UUID, Sequence[float] | None] = {
            uuid.uuid4(): None for _ in range(count)
        }

    async def pending_chunks(self, session: Any, model_id: str, ids: Any, **_: Any) -> list[Any]:
        return [(cid, f"text {cid}", "title") for cid, v in self.vectors.items() if v is None]

    async def store_embeddings(self, session: Any, ids: Any, vectors: Any, model_id: str) -> None:
        self.vectors.update(zip(ids, vectors, strict=True))

    async def destinations_with_unembedded_chunks(self, session: Any) -> list[uuid.UUID]:
        return [DESTINATION] if self.missing else []

    @property
    def missing(self) -> int:
        return sum(v is None for v in self.vectors.values())


class RateLimitedOn(MockProvider):
    """Answers 429 on the listed call numbers (1-based), else as the MOCK adapter."""

    def __init__(self, *limited: int) -> None:
        super().__init__("ok", app_env="test")
        self.limited = set(limited)
        self.calls = 0

    async def embed_texts(self, texts: Any, purpose: Any, titles: Any = None) -> EmbeddingResult:
        self.calls += 1
        if self.calls in self.limited:
            raise ProviderRateLimited("mock 429", retry_after_s=None)
        return await super().embed_texts(texts, purpose, titles)


@asynccontextmanager
async def no_session() -> AsyncIterator[Any]:
    yield None


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch) -> Store:
    store = Store(3 * RAG_EMBED_BATCH)
    for name in ("pending_chunks", "store_embeddings", "destinations_with_unembedded_chunks"):
        monkeypatch.setattr(rag_service.repository, name, getattr(store, name))
    return store


@pytest.fixture
def waits(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    recorded: list[float] = []

    async def sleep(seconds: float) -> None:
        recorded.append(seconds)

    monkeypatch.setattr(rag_service.asyncio, "sleep", sleep)
    return recorded


async def test_d3_429_on_batch_two_backs_off_and_embeds_everything(
    store: Store, waits: list[float]
) -> None:
    provider = RateLimitedOn(2)
    report = await rag_service.embed_destinations(
        [DESTINATION], provider=provider, sessions=no_session
    )
    assert (report.embedded, report.queued, report.provider_failed) == (
        len(store.vectors),
        0,
        False,
    )
    assert store.missing == 0
    assert provider.calls == 4  # three batches and the one retried
    pace, backoff = rag_service.RAG_EMBED_PACE_S, rag_service.RAG_EMBED_BACKOFF_S
    assert waits == [pace, backoff, pace]


async def test_d3_backoff_doubles_while_429_repeats(store: Store, waits: list[float]) -> None:
    await rag_service.embed_destinations(
        [DESTINATION], provider=RateLimitedOn(1, 2), sessions=no_session
    )
    backoff = rag_service.RAG_EMBED_BACKOFF_S
    assert waits[:2] == [backoff, 2 * backoff]
    assert store.missing == 0


async def test_d3_budget_spent_queues_the_rest_and_re_embed_completes(
    store: Store, waits: list[float], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Every call after the first answers 429: the backoff would pass the budget, so the run stops.
    monkeypatch.setattr(rag_service, "RAG_EMBED_BACKOFF_S", 60.0)
    report = await rag_service.embed_destinations(
        [DESTINATION], provider=RateLimitedOn(*range(2, 10)), sessions=no_session, budget_s=30.0
    )
    assert report.provider_failed
    assert (report.embedded, report.queued) == (RAG_EMBED_BATCH, 2 * RAG_EMBED_BATCH)
    assert store.missing == 2 * RAG_EMBED_BATCH

    later = await rag_service.embed_queued(provider=RateLimitedOn(), sessions=no_session)
    assert (later.embedded, later.queued, later.provider_failed) == (2 * RAG_EMBED_BATCH, 0, False)
    assert store.missing == 0
    assert (
        await rag_service.embed_queued(provider=RateLimitedOn(1), sessions=no_session)
    ).embedded == 0


async def test_d3_no_budget_left_makes_no_call_and_queues_everything(
    store: Store, waits: list[float]
) -> None:
    provider = RateLimitedOn()
    report = await rag_service.embed_destinations(
        [DESTINATION], provider=provider, sessions=no_session, budget_s=0.0
    )
    assert (provider.calls, report.embedded, report.queued) == (0, 0, len(store.vectors))
    assert not report.provider_failed
    assert report.exit_code == rag_service.EXIT_PROVIDER  # a re-run resumes


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self.now = now
        self.elapsed = 0.0

    def advance(self, seconds: float) -> None:
        self.now += timedelta(seconds=seconds)
        self.elapsed += seconds

    def monotonic(self) -> float:
        return self.elapsed

    async def sleep(self, seconds: float) -> None:
        self.advance(seconds)


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> FakeClock:
    clock = FakeClock(datetime(2026, 11, 28, 23, 50, tzinfo=UTC))
    monkeypatch.setattr(rag_service, "_utc_now", lambda: clock.now)
    # Replace the service's time reference, leaving asyncio/pytest's own clock untouched.
    monkeypatch.setattr(rag_service, "time", clock)
    monkeypatch.setattr(rag_service.asyncio, "sleep", clock.sleep)
    return clock


class FailingEmbedder(MockProvider):
    def __init__(self, error: ProviderError, *, fail_from: int = 2) -> None:
        super().__init__("ok", app_env="test")
        self.error: ProviderError | None = error
        self.fail_from = fail_from
        self.calls = 0

    async def embed_texts(self, texts: Any, purpose: Any, titles: Any = None) -> EmbeddingResult:
        self.calls += 1
        if self.calls >= self.fail_from and self.error is not None:
            raise self.error
        return await super().embed_texts(texts, purpose, titles)


@pytest.mark.parametrize(
    "start",
    [
        datetime(2026, 11, 28, 23, 50, tzinfo=UTC),
        datetime(2026, 12, 31, 23, 50, tzinfo=UTC),
        datetime(2026, 11, 29, 5, 20, tzinfo=timezone(timedelta(hours=5, minutes=30))),
    ],
)
async def test_n3_import_quota_pauses_minute_rounds_once_until_utc_midnight_and_resumes(
    store: Store,
    clock: FakeClock,
    start: datetime,
    caplog: pytest.LogCaptureFixture,
) -> None:
    clock.now = start
    caplog.set_level(logging.INFO, logger="app.places.live_jobs")
    provider = FailingEmbedder(ProviderQuotaExhausted("SAMPLE quota"))
    report = await rag_service.embed_destinations(
        [DESTINATION], provider=provider, sessions=no_session
    )
    midnight = (start.astimezone(UTC) + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    assert report.paused_until == midnight
    assert (report.embedded, report.queued, provider.calls) == (RAG_EMBED_BATCH, 64, 2)
    warnings = list(caplog.records)
    assert len(warnings) == 1
    assert "provider_quota_exhausted" in warnings[0].message
    assert "paused until" in warnings[0].message

    for _ in range(9):
        clock.advance(60)
        queued = await live_jobs.reembed_queued(sessions=no_session, embedder=provider)
        assert queued == 64
    assert provider.calls == 2
    assert caplog.records == warnings
    assert store.missing == 64

    # A fresh instance of the same provider/model also observes the pause.
    replacement = FailingEmbedder(ProviderQuotaExhausted(), fail_from=1)
    assert (await rag_service.embed_queued(provider=replacement, sessions=no_session)).queued == 64
    assert replacement.calls == 0

    clock.now = midnight - timedelta(microseconds=1)
    await rag_service.embed_queued(provider=provider, sessions=no_session)
    assert provider.calls == 2
    clock.advance(0.000001)
    provider.error = None
    assert await live_jobs.reembed_queued(sessions=no_session, embedder=provider) == 0
    assert provider.calls == 4
    assert store.missing == 0
    assert len([r for r in caplog.records if r.levelname == "WARNING"]) == 1


async def test_n3_repeated_429s_exceeding_the_budget_pause_until_midnight(
    store: Store, clock: FakeClock, caplog: pytest.LogCaptureFixture
) -> None:
    provider = FailingEmbedder(ProviderRateLimited("SAMPLE repeated 429"))
    report = await rag_service.embed_queued(provider=provider, sessions=no_session)
    assert report.paused_until == datetime(2026, 11, 29, tzinfo=UTC)
    assert report.provider_failed
    assert (report.embedded, report.queued, provider.calls) == (32, 64, 5)
    assert clock.elapsed == 72  # pacing 2 + retry waits 10, 20, 40; 80 exceeds the budget
    for _ in range(5):
        clock.advance(60)
        assert await live_jobs.reembed_queued(sessions=no_session, embedder=provider) == 64
    assert provider.calls == 5
    assert len(caplog.records) == 1
    clock.now = report.paused_until
    provider.error = None
    resumed = await rag_service.embed_queued(provider=provider, sessions=no_session)
    assert (resumed.embedded, resumed.queued, resumed.paused_until) == (64, 0, None)
    assert store.missing == 0


@pytest.mark.parametrize("error_type", [ProviderQuotaExhausted, ProviderRateLimited])
@pytest.mark.parametrize("retry_after", [120, 3600])
async def test_n3_retry_after_controls_resume_even_across_midnight(
    store: Store,
    clock: FakeClock,
    error_type: type[ProviderQuotaExhausted] | type[ProviderRateLimited],
    retry_after: int,
    caplog: pytest.LogCaptureFixture,
) -> None:
    provider = FailingEmbedder(error_type(retry_after_s=retry_after), fail_from=1)
    until = clock.now + timedelta(seconds=retry_after)
    report = await rag_service.embed_queued(provider=provider, sessions=no_session)
    assert report.paused_until == until
    assert report.queued == len(store.vectors)
    clock.advance(retry_after - 1)
    await live_jobs.reembed_queued(sessions=no_session, embedder=provider)
    assert provider.calls == 1
    assert len(caplog.records) == 1
    clock.advance(1)
    provider.error = None
    resumed = await rag_service.embed_queued(provider=provider, sessions=no_session)
    assert resumed.queued == 0
    assert resumed.embedded == len(store.vectors)
    assert store.missing == 0


async def test_n3_an_outage_does_not_pause_until_midnight(store: Store, clock: FakeClock) -> None:
    provider = FailingEmbedder(ProviderUnavailable("SAMPLE outage"), fail_from=1)
    report = await rag_service.embed_queued(provider=provider, sessions=no_session)
    assert report.provider_failed
    assert report.paused_until is None
    provider.error = None
    clock.advance(60)
    resumed = await rag_service.embed_queued(provider=provider, sessions=no_session)
    assert resumed.queued == 0
    assert store.missing == 0
