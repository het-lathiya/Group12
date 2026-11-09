"""Gemini embeddings over a fake transport (Amendment A1 §6.5; IMP-312: TC-444, TC-445).

The real SDK parses every answer; nothing reaches the network. The error bodies follow the
documented Google API error shape and are format fixtures, not live recordings.
"""

import asyncio
import json
import logging
import math
from typing import Any

import httpx
import pytest

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
from app.ai.providers import gemini as adapter
from app.ai.providers.gemini import GeminiProvider
from app.core.config import Settings

KEY = "unit-test-gemini-key-not-real"
VENDOR_TEXT = "Sample vendor text"
TEXT = "A secret traveller sentence"


def vendor_error(
    code: int, status: str, details: list[dict[str, Any]] | None = None, **headers: str
) -> httpx.Response:
    error = {"code": code, "message": VENDOR_TEXT, "status": status, "details": details or []}
    return httpx.Response(code, json={"error": error}, headers=headers)


def per_day_quota() -> httpx.Response:
    violation = {"quotaId": "EmbedContentRequestsPerDayPerProjectPerModel"}
    return vendor_error(429, "RESOURCE_EXHAUSTED", [{"violations": [violation]}])


def ok(count: int = 1) -> httpx.Response:
    return httpx.Response(200, json={"embeddings": [{"values": [3.0, 4.0] + [0.0] * 766}] * count})


class Replay:
    """Answers each request with the next answer, repeating the last, and counts the requests."""

    def __init__(self, *answers: httpx.Response | Exception) -> None:
        self.answers = list(answers)
        self.count = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.count += 1
        answer = self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]
        if isinstance(answer, Exception):
            raise answer
        return answer


def provider(replay: Replay, **overrides: Any) -> GeminiProvider:
    values: dict[str, Any] = {
        "gemini_api_key": KEY,
        "gemini_model_id": "model-x",
        "gemini_embedding_model_id": "gemini-embedding-2",
    }
    client = httpx.AsyncClient(transport=httpx.MockTransport(replay))
    return GeminiProvider(Settings(**(values | overrides)), http_client=client)


@pytest.fixture
def sleeps(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    delays: list[float] = []

    async def no_wait(delay: float) -> None:
        delays.append(delay)

    monkeypatch.setattr(adapter.asyncio, "sleep", no_wait)
    return delays


def embed(gemini: GeminiProvider) -> list[float]:
    return asyncio.run(gemini.embed_texts([TEXT], "query")).vectors[0]


def test_tc_444_gemini_embeddings_are_normalised_in_code() -> None:
    vector = embed(provider(Replay(ok())))

    assert vector[:2] == [0.6, 0.8]
    assert math.isclose(sum(value * value for value in vector), 1.0)


def test_tc_444_a_zero_vector_is_refused() -> None:
    zero = httpx.Response(200, json={"embeddings": [{"values": [0.0] * 768}]})
    with pytest.raises(ProviderInvalidOutput) as raised:
        embed(provider(Replay(zero)))
    assert raised.value.kind == "schema_violation"


def test_tc_444_a_body_that_is_not_json_is_invalid_output() -> None:
    with pytest.raises(ProviderInvalidOutput) as raised:
        embed(provider(Replay(httpx.Response(200, text="not json"))))
    assert raised.value.kind == "malformed_json"


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        (per_day_quota, ProviderQuotaExhausted),
        (lambda: vendor_error(429, "RESOURCE_EXHAUSTED"), ProviderRateLimited),
        (lambda: vendor_error(402, "FAILED_PRECONDITION"), ProviderQuotaExhausted),
        (lambda: vendor_error(403, "PERMISSION_DENIED"), ProviderAuthError),
        (lambda: vendor_error(400, "INVALID_ARGUMENT"), ProviderBadRequest),
        (lambda: vendor_error(503, "UNAVAILABLE"), ProviderUnavailable),
        (lambda: vendor_error(504, "DEADLINE_EXCEEDED"), ProviderTimeout),
        (lambda: httpx.ReadTimeout("slow"), ProviderTimeout),
        (lambda: httpx.ConnectError("down"), ProviderUnavailable),
    ],
    ids=[
        "quota",
        "rate",
        "payment",
        "forbidden",
        "bad_request",
        "unavailable",
        "deadline",
        "read_timeout",
        "connection",
    ],
)
def test_tc_445_embedding_errors_map_to_the_shared_types(
    answer: Any, expected: type[ProviderError], sleeps: list[float]
) -> None:
    with pytest.raises(expected) as raised:
        embed(provider(Replay(answer())))
    assert VENDOR_TEXT not in str(raised.value)
    assert raised.value.__cause__ is None


def test_tc_445_a_stuck_call_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    gemini = provider(Replay(ok()), gemini_timeout_s=0.01, gemini_max_retries=0)

    class Stuck:
        async def embed_content(self, **kwargs: object) -> None:
            await asyncio.Event().wait()

    class Client:
        class aio:  # noqa: N801 - the SDK's attribute name
            models = Stuck()

    monkeypatch.setattr(gemini, "_vendor_client", lambda: Client)
    with pytest.raises(ProviderTimeout):
        embed(gemini)


def test_a_transient_error_is_retried_up_to_gemini_max_retries(sleeps: list[float]) -> None:
    replay = Replay(vendor_error(503, "UNAVAILABLE"), ok())

    assert embed(provider(replay))
    assert replay.count == 2
    assert len(sleeps) == 1
    assert 0.75 <= sleeps[0] <= 1.25

    # §8.14 (IMP-401): never a third attempt, whatever GEMINI_MAX_RETRIES says.
    failing = Replay(vendor_error(503, "UNAVAILABLE"))
    with pytest.raises(ProviderUnavailable):
        embed(provider(failing, gemini_max_retries=2))
    assert failing.count == 2


def test_a_retry_honours_retry_after(sleeps: list[float]) -> None:
    limited = vendor_error(429, "RESOURCE_EXHAUSTED", **{"retry-after": "7"})

    assert embed(provider(Replay(limited, ok())))
    assert sleeps == [7]


@pytest.mark.parametrize(
    "answer",
    [per_day_quota, lambda: vendor_error(403, "PERMISSION_DENIED")],
    ids=["quota", "forbidden"],
)
def test_quota_and_auth_errors_are_not_retried(answer: Any, sleeps: list[float]) -> None:
    replay = Replay(answer())
    with pytest.raises(ProviderError):
        embed(provider(replay))
    assert replay.count == 1
    assert sleeps == []


@pytest.mark.parametrize(
    "answer",
    [per_day_quota, lambda: vendor_error(403, "PERMISSION_DENIED")],
    ids=["quota", "forbidden"],
)
def test_tc_445_embedding_failures_leave_the_generation_health_alone(
    answer: Any, sleeps: list[float]
) -> None:
    gemini = provider(Replay(answer()))
    with pytest.raises(ProviderError):
        embed(gemini)
    assert asyncio.run(gemini.health_check()).status == "ok"


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"gemini_api_key": ""}, ProviderAuthError),
        ({"gemini_embedding_model_id": ""}, ProviderBadRequest),
        ({"gemini_embedding_model_id": "text-embedding-004"}, ProviderBadRequest),
    ],
    ids=["no_key", "no_model", "unsupported_model"],
)
def test_embedding_without_its_configuration_sends_nothing(
    overrides: dict[str, str], expected: type[ProviderError]
) -> None:
    replay = Replay(ok())
    with pytest.raises(expected):
        embed(provider(replay, **overrides))
    assert replay.count == 0


def test_neither_text_nor_vectors_are_logged(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG):
        embed(provider(Replay(ok())))
    assert TEXT not in caplog.text
    assert json.dumps(0.6) not in caplog.text
