"""GEMINI_FALLBACK_MODEL_ID: one call with a second model after a 429 or 503 (IMD-222, PD-GEM-2).

Recordings of provider_recordings/gemini go through the real SDK over a fake transport that notes
the model of each call; a fake clock and sleep keep the retries instant (IMD-27). No live call.
"""

import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from fixtures.ai import sample_request
from fixtures.pipeline import Journal

from app.ai import factory
from app.ai.errors import ProviderQuotaExhausted, ProviderRateLimited, ProviderUnavailable
from app.ai.providers.gemini import GeminiProvider
from app.core.config import Settings
from app.schemas.ai import RepairContext

RECORDINGS = Path(__file__).resolve().parents[2] / "fixtures" / "provider_recordings" / "gemini"
MODEL = "gemini-3.5-flash-lite"
FALLBACK = "gemini-3.6-flash"


def recording(name: str) -> httpx.Response:
    data = json.loads((RECORDINGS / f"{name}.json").read_text(encoding="utf-8"))
    return httpx.Response(data["http_status"], json=data["body"], headers=data["headers"])


class Calls:
    """A fake transport: the answers in order (the last one again), and the model of each call."""

    def __init__(self, *answers: httpx.Response) -> None:
        self.answers = list(answers)
        self.models: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.models.append(json.loads(request.content)["model"])
        return self.answers[min(len(self.models) - 1, len(self.answers) - 1)]


def gemini(calls: Calls, fallback: str = FALLBACK) -> GeminiProvider:
    now = [1000.0]

    async def sleep(delay: float) -> None:
        now[0] += delay

    settings = Settings(
        gemini_api_key="unit-test-gemini-key-not-real",
        gemini_model_id=MODEL,
        gemini_fallback_model_id=fallback,
    )
    client = httpx.AsyncClient(transport=httpx.MockTransport(calls))
    return GeminiProvider(settings, http_client=client, clock=lambda: now[0], sleep=sleep)


def generate(provider: GeminiProvider, **update: Any) -> Any:
    return asyncio.run(provider.generate_itinerary(sample_request().model_copy(update=update)))


@pytest.mark.parametrize(
    ("primary", "cause"),
    [("unavailable_503", "provider_unavailable"), ("rate_limited_429", "provider_rate_limited")],
    ids=["503", "429"],
)
def test_fallback_answers_once_after_the_retries_of_a_503_or_429(primary: str, cause: str) -> None:
    calls = Calls(recording(primary), recording(primary), recording("ok"))

    result = generate(gemini(calls))

    assert calls.models == [MODEL, MODEL, FALLBACK]
    assert result.output.days
    assert result.model_id == FALLBACK
    assert result.fallback_from == cause


@pytest.mark.parametrize("fallback", ["", MODEL], ids=["unset", "same_as_primary"])
def test_no_second_model_call_when_the_fallback_is_off(fallback: str) -> None:
    calls = Calls(recording("unavailable_503"))

    with pytest.raises(ProviderUnavailable):
        generate(gemini(calls, fallback))

    assert calls.models == [MODEL, MODEL]


def test_a_failing_fallback_is_called_once_and_the_first_error_stands() -> None:
    calls = Calls(
        recording("rate_limited_429"), recording("rate_limited_429"), recording("quota_429")
    )

    with pytest.raises(ProviderRateLimited):
        generate(gemini(calls))

    assert calls.models == [MODEL, MODEL, FALLBACK]


def test_an_unusable_fallback_answer_keeps_the_first_error() -> None:
    calls = Calls(
        recording("unavailable_503"), recording("unavailable_503"), recording("malformed")
    )

    with pytest.raises(ProviderUnavailable):
        generate(gemini(calls))

    assert calls.models.count(FALLBACK) == 1


def test_quota_and_repair_calls_never_use_the_fallback() -> None:
    quota = Calls(recording("quota_429"), recording("ok"))
    with pytest.raises(ProviderQuotaExhausted):
        generate(gemini(quota))
    assert quota.models == [MODEL]

    repair = Calls(recording("unavailable_503"), recording("ok"))
    context = RepairContext(invalid_output="{}", findings=[])
    with pytest.raises(ProviderUnavailable):
        generate(gemini(repair), repair_context=context)
    assert repair.models == [MODEL]


def test_a_primary_answer_names_no_fallback() -> None:
    result = generate(gemini(Calls(recording("ok"))))

    assert (result.model_id, result.fallback_from) == (None, None)


# The pipeline: the record names the model used; the breaker counts the primary failure.


def test_pipeline_records_the_fallback_model_and_keeps_the_primary_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    journal = Journal(monkeypatch, sample_request())
    provider = gemini(
        Calls(recording("unavailable_503"), recording("unavailable_503"), recording("ok"))
    )
    breaker = factory.breaker_for(provider)
    for _ in range(4):
        breaker.record_failure(ProviderUnavailable())

    journal.run(provider)

    assert journal.completed["outcome"] == "model"
    assert journal.recorded_model == FALLBACK
    assert breaker.state == "open"  # the fifth primary failure, not reset by the fallback answer


def test_pipeline_both_models_failing_ends_in_the_labelled_rule_based_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    journal = Journal(monkeypatch, sample_request())
    calls = Calls(recording("unavailable_503"))

    journal.run(gemini(calls))

    assert calls.models == [MODEL, MODEL, FALLBACK]
    assert journal.fell_back("provider_unavailable")
    assert journal.recorded_model is None
