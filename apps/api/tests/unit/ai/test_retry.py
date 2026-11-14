"""Bounded retries in the Gemini adapter (§8.4, §8.14; FR-047; IMP-401: TC-009, TC-016 to TC-018).

The recordings of provider_recordings/gemini go through the real SDK over a fake transport. The
adapter gets a fake clock and a fake sleep, so no test waits for real (IMD-27): the clock moves
only when a test says an attempt took time.
"""

import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from fixtures.ai import sample_request

from app.ai.errors import (
    ProviderAuthError,
    ProviderBadRequest,
    ProviderError,
    ProviderInvalidOutput,
    ProviderQuotaExhausted,
    ProviderRateLimited,
    ProviderTimeout,
    ProviderUnavailable,
)
from app.ai.providers.gemini import MAX_ATTEMPTS, GeminiProvider, wire_schema
from app.core.config import GEMINI_TIME_ALLOWANCE_S, REPAIR_TIME_ALLOWANCE_S, Settings
from app.schemas.ai import ItineraryOutput, RepairContext

RECORDINGS = Path(__file__).resolve().parents[2] / "fixtures" / "provider_recordings" / "gemini"
KEY = "unit-test-gemini-key-not-real"
MODEL = "gemini-3.5-flash-lite"


def recording(name: str) -> httpx.Response:
    data = json.loads((RECORDINGS / f"{name}.json").read_text(encoding="utf-8"))
    return httpx.Response(data["http_status"], json=data["body"], headers=data["headers"])


def status(code: int, error_code: str) -> httpx.Response:
    return httpx.Response(code, json={"error": {"code": error_code, "message": "vendor text"}})


class Answers:
    """A fake transport giving its answers in order, the last one again after that."""

    def __init__(self, *answers: httpx.Response | Exception) -> None:
        self.answers = list(answers)
        self.count = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        answer = self.answers[min(self.count, len(self.answers) - 1)]
        self.count += 1
        if isinstance(answer, Exception):
            raise answer
        return answer


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    async def sleep(self, delay: float) -> None:
        self.sleeps.append(delay)
        self.now += delay


def adapter(answers: Answers, clock: FakeClock, **overrides: Any) -> GeminiProvider:
    values: dict[str, Any] = {"gemini_api_key": KEY, "gemini_model_id": MODEL, **overrides}
    client = httpx.AsyncClient(transport=httpx.MockTransport(answers))
    return GeminiProvider(Settings(**values), http_client=client, clock=clock, sleep=clock.sleep)


def timed(gemini: GeminiProvider, clock: FakeClock, took_s: float) -> list[float]:
    """Each attempt takes ``took_s`` on the fake clock; returns the timeout each attempt got."""
    real = gemini._call_vendor
    timeouts: list[float] = []

    async def call(system: str, user: str, schema: dict[str, Any], timeout_s: float) -> Any:
        timeouts.append(timeout_s)
        clock.now += took_s
        return await real(system, user, schema, timeout_s)

    gemini._call_vendor = call  # type: ignore[method-assign]  # spy on the one vendor call
    return timeouts


def generate(gemini: GeminiProvider) -> Any:
    return asyncio.run(gemini.generate_itinerary(sample_request()))


# TC-009: only transient errors are retried


@pytest.mark.parametrize(
    "first",
    [recording("unavailable_503"), status(500, "internal"), httpx.ReadTimeout("slow")],
    ids=["503", "500", "timeout"],
)
def test_retry_tc_009_a_transient_error_is_retried_once_then_succeeds(first: Any) -> None:
    clock, answers = FakeClock(), Answers(first, recording("ok"))

    result = generate(adapter(answers, clock))

    assert result.output.days
    assert answers.count == 2
    assert len(clock.sleeps) == 1
    assert 0.75 <= clock.sleeps[0] <= 1.25  # 1 s with ±25 % jitter


@pytest.mark.parametrize(
    ("answer", "error"),
    [
        (recording("quota_429"), ProviderQuotaExhausted),
        (status(403, "permission_denied"), ProviderAuthError),
        (status(400, "invalid_request"), ProviderBadRequest),
        (recording("malformed"), ProviderInvalidOutput),
        (recording("blocked"), ProviderInvalidOutput),
    ],
    ids=["quota", "auth", "bad_request", "malformed", "blocked"],
)
def test_retry_tc_009_tc_017_other_errors_are_never_retried(
    answer: httpx.Response, error: type[ProviderError]
) -> None:
    clock, answers = FakeClock(), Answers(answer, recording("ok"))

    with pytest.raises(error):
        generate(adapter(answers, clock))

    assert answers.count == 1
    assert clock.sleeps == []


@pytest.mark.parametrize("max_retries", [1, 3, 10])
def test_retry_no_path_makes_more_than_two_attempts(max_retries: int) -> None:
    clock, answers = FakeClock(), Answers(recording("unavailable_503"))

    with pytest.raises(ProviderUnavailable):
        generate(adapter(answers, clock, gemini_max_retries=max_retries))

    assert answers.count == MAX_ATTEMPTS == 2


def test_retry_gemini_max_retries_0_makes_one_attempt() -> None:
    clock, answers = FakeClock(), Answers(recording("unavailable_503"), recording("ok"))

    with pytest.raises(ProviderUnavailable):
        generate(adapter(answers, clock, gemini_max_retries=0))

    assert answers.count == 1


# TC-016: a 429 rate limit uses bounded backoff


def test_retry_tc_016_a_rate_limit_waits_for_retry_after() -> None:
    clock, answers = FakeClock(), Answers(recording("rate_limited_429"), recording("ok"))

    generate(adapter(answers, clock))

    assert answers.count == 2
    assert clock.sleeps == [7]  # the recording's retry-after, longer than the 1 s backoff


def test_retry_tc_016_a_retry_after_past_the_allowance_is_not_waited_for() -> None:
    clock, answers = FakeClock(), Answers(recording("rate_limited_429"), recording("ok"))
    gemini = adapter(answers, clock)
    timed(gemini, clock, took_s=GEMINI_TIME_ALLOWANCE_S - 5)  # 5 s left, retry-after is 7 s

    with pytest.raises(ProviderRateLimited):
        generate(gemini)

    assert answers.count == 1
    assert clock.sleeps == []


# TC-018: the timeout is enforced inside the 70 s allowance


def test_retry_tc_018_each_attempt_gets_at_most_the_time_left() -> None:
    clock, answers = FakeClock(), Answers(recording("unavailable_503"), recording("ok"))
    gemini = adapter(answers, clock, gemini_timeout_s=35)
    timeouts = timed(gemini, clock, took_s=40)

    generate(gemini)

    assert timeouts[0] == 35
    assert timeouts[1] == pytest.approx(GEMINI_TIME_ALLOWANCE_S - 40 - clock.sleeps[0])
    assert sum(timeouts) <= GEMINI_TIME_ALLOWANCE_S


def test_retry_tc_018_no_attempt_starts_once_the_allowance_is_spent() -> None:
    clock, answers = FakeClock(), Answers(httpx.ReadTimeout("slow"), recording("ok"))
    gemini = adapter(answers, clock)
    timed(gemini, clock, took_s=GEMINI_TIME_ALLOWANCE_S - 0.5)

    with pytest.raises(ProviderTimeout):
        generate(gemini)

    assert answers.count == 1
    assert clock.now - 1000.0 <= GEMINI_TIME_ALLOWANCE_S


def test_retry_tc_018_a_slow_answer_becomes_a_provider_timeout_per_attempt() -> None:
    async def never(request: httpx.Request) -> httpx.Response:
        await asyncio.Event().wait()  # never answers; the attempt's timeout ends it
        raise AssertionError("unreachable")

    clock = FakeClock()
    client = httpx.AsyncClient(transport=httpx.MockTransport(never))
    settings = Settings(gemini_api_key=KEY, gemini_model_id=MODEL, gemini_timeout_s=0.01)
    gemini = GeminiProvider(settings, http_client=client, clock=clock, sleep=clock.sleep)
    timeouts = timed(gemini, clock, took_s=0)

    with pytest.raises(ProviderTimeout):
        generate(gemini)

    assert timeouts == [0.01, 0.01]  # a timeout is transient: one retry, then the fallback


# IMP-502 (§8.13): the repair call makes one attempt inside its own 25 s


def test_retry_the_repair_call_is_one_attempt_of_at_most_25_s_with_the_wire_schema() -> None:
    clock, answers = FakeClock(), Answers(recording("unavailable_503"), recording("ok"))
    gemini = adapter(answers, clock, gemini_timeout_s=35)
    timeouts = timed(gemini, clock, took_s=1)
    schemas: list[dict[str, Any]] = []
    spied = gemini._call_vendor

    async def call(system: str, user: str, schema: dict[str, Any], timeout_s: float) -> Any:
        schemas.append(schema)
        return await spied(system, user, schema, timeout_s)

    gemini._call_vendor = call  # type: ignore[method-assign]  # spy on the one vendor call
    context = RepairContext(invalid_output="", findings=[])
    request = sample_request().model_copy(update={"repair_context": context})

    with pytest.raises(ProviderUnavailable):
        asyncio.run(gemini.generate_itinerary(request))

    assert answers.count == 1  # no transport retry
    assert clock.sleeps == []
    assert timeouts == [REPAIR_TIME_ALLOWANCE_S]
    assert schemas == [wire_schema(ItineraryOutput)]
