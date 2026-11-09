"""The circuit breaker (§8.4, FR-047; IMP-401: TC-010, TC-174, TC-175; IMD-44, A1 IMD-112).

The breaker runs on a fake clock, so cool-downs pass without waiting. TC-174 and TC-175 run the
pipeline with the stand-ins of ``fixtures.pipeline`` and MOCK errors (IMD-27).
"""

import asyncio
from typing import Any

import httpx
import pytest
from fixtures.ai import sample_request
from fixtures.pipeline import Journal

from app.ai import factory
from app.ai.breaker import (
    FAILURES_TO_OPEN,
    QUOTA_COOL_DOWN_S,
    TRANSIENT_COOL_DOWN_S,
    CircuitBreaker,
)
from app.ai.errors import (
    ProviderAuthError,
    ProviderBadRequest,
    ProviderError,
    ProviderQuotaExhausted,
    ProviderRateLimited,
    ProviderTimeout,
    ProviderUnavailable,
)
from app.ai.providers.gemini import GeminiProvider
from app.ai.providers.mock import MockProvider
from app.core.config import Settings
from app.schemas.ai import GenerationRequest


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def opened_by(error: ProviderError, times: int = 1) -> tuple[CircuitBreaker, Clock]:
    clock = Clock()
    breaker = CircuitBreaker(clock)
    for _ in range(times):
        breaker.record_failure(error)
    return breaker, clock


# ---------- State machine (TC-010) ----------


def test_breaker_starts_closed() -> None:
    assert CircuitBreaker().state == "closed"


@pytest.mark.parametrize(
    "error",
    [ProviderTimeout(), ProviderRateLimited(), ProviderUnavailable()],
    ids=["timeout", "rate_limited", "unavailable"],
)
def test_breaker_tc_010_opens_after_five_consecutive_transient_failures(
    error: ProviderError,
) -> None:
    breaker, _ = opened_by(error, FAILURES_TO_OPEN - 1)
    assert breaker.state == "closed"

    breaker.record_failure(error)

    assert (breaker.state, breaker.open_reason) == ("open", error.failure_reason)


def test_breaker_a_success_resets_the_count() -> None:
    breaker, _ = opened_by(ProviderUnavailable(), FAILURES_TO_OPEN - 1)

    breaker.record_success()
    breaker.record_failure(ProviderUnavailable())

    assert breaker.state == "closed"


def test_breaker_tc_010_recovers_through_half_open() -> None:
    breaker, clock = opened_by(ProviderUnavailable(), FAILURES_TO_OPEN)

    clock.now += TRANSIENT_COOL_DOWN_S - 1
    assert breaker.state == "open"
    clock.now += 1
    assert breaker.state == "half_open"

    breaker.record_success()  # the probe succeeded
    assert (breaker.state, breaker.open_reason) == ("closed", None)


def test_breaker_tc_010_a_failed_probe_opens_it_again_at_once() -> None:
    breaker, clock = opened_by(ProviderTimeout(), FAILURES_TO_OPEN)
    clock.now += TRANSIENT_COOL_DOWN_S

    breaker.record_failure(ProviderTimeout())

    assert breaker.state == "open"
    clock.now += TRANSIENT_COOL_DOWN_S
    assert breaker.state == "half_open"


def test_breaker_one_quota_error_opens_it_for_fifteen_minutes() -> None:
    breaker, clock = opened_by(ProviderQuotaExhausted())

    assert (breaker.state, breaker.open_reason) == ("open", "provider_quota_exhausted")
    clock.now += QUOTA_COOL_DOWN_S - 1
    assert breaker.state == "open"
    clock.now += 1
    assert breaker.state == "half_open"


def test_breaker_an_auth_error_keeps_it_open_until_restart() -> None:
    breaker, clock = opened_by(ProviderAuthError())

    clock.now += 10 * 24 * 3600
    assert (breaker.state, breaker.open_reason) == ("open", "config_error")


def test_breaker_a_bad_request_neither_counts_nor_resets() -> None:
    breaker, _ = opened_by(ProviderUnavailable(), FAILURES_TO_OPEN - 1)

    breaker.record_failure(ProviderBadRequest())
    assert breaker.state == "closed"
    breaker.record_failure(ProviderUnavailable())
    assert breaker.state == "open"


def test_breaker_the_factory_holds_one_breaker_per_provider() -> None:
    first, second = MockProvider("ok", app_env="test"), MockProvider("ok", app_env="test")

    assert factory.breaker_for(first) is factory.breaker_for(first)
    assert factory.breaker_for(first) is not factory.breaker_for(second)


# ---------- Health (API-02) ----------


def gemini_with(breaker: CircuitBreaker) -> GeminiProvider:
    settings = Settings(gemini_api_key="unit-test-gemini-key-not-real", gemini_model_id="m")
    return GeminiProvider(settings, breaker=breaker)


def test_breaker_health_is_down_while_open_and_degraded_while_half_open() -> None:
    breaker, clock = opened_by(ProviderUnavailable(), FAILURES_TO_OPEN)
    gemini = gemini_with(breaker)

    assert asyncio.run(gemini.health_check()).status == "down"
    clock.now += TRANSIENT_COOL_DOWN_S
    assert asyncio.run(gemini.health_check()).status == "degraded"
    breaker.record_success()
    assert asyncio.run(gemini.health_check()).status == "ok"


def test_breaker_the_factory_gives_the_gemini_adapter_its_own_breaker() -> None:
    settings = Settings(
        ai_provider="GEMINI", gemini_api_key="unit-test-gemini-key-not-real", gemini_model_id="m"
    )
    factory.reset_provider_cache()
    try:
        gemini = factory.get_provider(settings)
        for _ in range(FAILURES_TO_OPEN):
            factory.breaker_for(gemini).record_failure(ProviderUnavailable())

        assert asyncio.run(gemini.health_check()).status == "down"
    finally:
        factory.reset_provider_cache()


# ---------- The pipeline (TC-174, TC-175) ----------


class Counting(MockProvider):
    def __init__(self, error: ProviderError | None = None) -> None:
        super().__init__("ok", app_env="test", raise_error=error)
        self.generate_calls = 0
        self.embed_calls = 0

    async def generate_itinerary(self, request: GenerationRequest) -> Any:
        self.generate_calls += 1
        return await super().generate_itinerary(request)

    async def embed_texts(self, *args: Any, **kwargs: Any) -> Any:
        self.embed_calls += 1
        return await super().embed_texts(*args, **kwargs)


def test_breaker_tc_174_five_transient_failures_then_the_fallback_without_a_provider_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = Counting(ProviderUnavailable())
    for _ in range(FAILURES_TO_OPEN):
        journal = Journal(monkeypatch, sample_request())
        journal.run(provider)
        assert journal.fell_back("provider_unavailable")  # each one after its retries
    assert factory.breaker_for(provider).state == "open"
    provider.raise_error = None  # the service is back, but the breaker is still open

    journal = Journal(monkeypatch, sample_request())
    journal.run(provider)

    assert provider.generate_calls == FAILURES_TO_OPEN
    assert journal.fell_back("provider_unavailable")
    assert "settings" not in journal.steps  # step 7 was skipped


def test_breaker_tc_175_a_quota_breaker_fails_the_next_generation_without_a_provider_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = Counting(ProviderQuotaExhausted())
    journal = Journal(monkeypatch, sample_request())
    journal.run(provider)
    assert journal.failed == "provider_quota_exhausted"
    provider.raise_error = None

    journal = Journal(monkeypatch, sample_request())
    journal.run(provider)

    assert provider.generate_calls == 1
    assert journal.failed == "provider_quota_exhausted"  # IMD-44: no rule-based plan
    assert journal.saved is None


def test_breaker_an_auth_breaker_fails_with_config_error(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = Counting(ProviderAuthError())
    Journal(monkeypatch, sample_request()).run(provider)

    journal = Journal(monkeypatch, sample_request())
    journal.run(provider)

    assert provider.generate_calls == 1
    assert journal.failed == "config_error"


def test_breaker_a_half_open_probe_that_succeeds_saves_the_model_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = Counting()
    clock = Clock()
    breaker = CircuitBreaker(clock)
    monkeypatch.setitem(factory._breakers, provider, breaker)
    for _ in range(FAILURES_TO_OPEN):
        breaker.record_failure(ProviderUnavailable())
    clock.now += TRANSIENT_COOL_DOWN_S

    journal = Journal(monkeypatch, sample_request())
    journal.run(provider)

    assert provider.generate_calls == 1
    assert journal.completed["outcome"] == "model"
    assert breaker.state == "closed"


def test_breaker_rule_based_mode_runs_while_open(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = Counting(ProviderQuotaExhausted())
    Journal(monkeypatch, sample_request()).run(provider)

    journal = Journal(monkeypatch, sample_request())
    journal.model_id = "rule_based_planner_v1"
    journal.run(provider)

    assert journal.fell_back(None)  # the page's "Build a plan without AI" still works


def test_breaker_embedding_calls_are_neither_counted_nor_blocked() -> None:
    clock = Clock()
    breaker = CircuitBreaker(clock)
    for _ in range(FAILURES_TO_OPEN):
        breaker.record_failure(ProviderUnavailable())
    calls = 0

    def answer(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"embeddings": [{"values": [0.6, 0.8] + [0.0] * 766}]})

    settings = Settings(
        gemini_api_key="unit-test-gemini-key-not-real",
        gemini_model_id="m",
        gemini_embedding_model_id="gemini-embedding-2",
    )
    client = httpx.AsyncClient(transport=httpx.MockTransport(answer))
    gemini = GeminiProvider(settings, http_client=client, breaker=breaker)

    result = asyncio.run(gemini.embed_texts(["a query"], "query"))

    assert calls == 1  # an open breaker does not block embeddings
    assert result.vectors
    assert breaker.state == "open"  # and an embedding success does not close it
