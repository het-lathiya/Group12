"""D3: paced embedding with a 429 backoff, a budget, a re-embed queue (live-local 2026-11-28).

Offline: the repository calls are replaced by an in-memory store, the provider by the MOCK adapter
with a scripted 429, and ``asyncio.sleep`` by a recorder, so no test waits.
"""

import uuid
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from typing import Any

import pytest

from app.ai.errors import ProviderRateLimited
from app.ai.providers.mock import MockProvider
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
