"""Provider contract suite (§8.19; IMP-110 skeleton: TC-001, TC-158; NFR-043).

Every adapter must pass the same tests. Each entry of ``ADAPTERS`` builds a fresh provider, plus
one that raises a given shared error. The in-test double stays registered next to the MOCK adapter
(IMP-207), so the suite keeps checking its own expectations.

Adapters join by adding one entry:
- IMP-207: ``mock`` (``app.ai.providers.mock.MockProvider``, scenarios and ``raise_error``);
- IMP-301: ``gemini_recorded`` (the Gemini adapter behind a fake HTTP transport, no network);
- IMP-512: completes the suite for every adapter (failure scenarios per error type, live marker).
"""

import asyncio
import inspect
import json
import socket
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx
import pytest
from fixtures.ai import SAMPLE_OUTPUT, DoubleProvider, sample_request

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
from app.ai.providers.base import ModelProvider
from app.ai.providers.gemini import GeminiProvider
from app.ai.providers.mock import MockProvider
from app.core.config import MockScenario, Settings, get_settings
from app.schemas.ai import (
    HealthStatus,
    ItineraryOutput,
    ModelMetadata,
    ModificationRequest,
    ProviderResult,
)


@dataclass(frozen=True)
class Adapter:
    build: Callable[[], ModelProvider]
    failing: Callable[[ProviderError], ModelProvider]


USAGE = {
    "total_input_tokens": 120,
    "total_output_tokens": 40,
    "total_thought_tokens": 10,
    "total_tokens": 170,
}


def interaction(text: str = "", **overrides: Any) -> dict[str, Any]:
    """An Interactions answer in the documented shape."""
    return {
        "id": "sample-interaction",
        "status": "completed",
        "steps": [{"type": "model_output", "content": [{"type": "text", "text": text}]}],
        "usage": USAGE,
        **overrides,
    }


def vendor_error(status: int, code: str, **headers: str) -> httpx.Response:
    body = {"error": {"code": code, "message": "vendor text that must never surface"}}
    return httpx.Response(status, json=body, headers=headers)


def gemini(answer: httpx.Response | Exception | None = None) -> GeminiProvider:
    """GeminiProvider behind a fake transport: nothing leaves the process."""
    ok = httpx.Response(200, json=interaction(json.dumps(SAMPLE_OUTPUT)))

    def respond(request: httpx.Request) -> httpx.Response:
        if isinstance(answer, Exception):
            raise answer
        return answer or ok

    settings = Settings(gemini_api_key="contract-key-not-real", gemini_model_id="contract-model")
    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    return GeminiProvider(settings, http_client=client)


def gemini_failing(error: ProviderError) -> GeminiProvider:
    answers: dict[type[ProviderError], httpx.Response | Exception] = {
        ProviderTimeout: httpx.ReadTimeout("slow"),
        ProviderRateLimited: vendor_error(429, "rate_limit_exceeded", **{"retry-after": "1"}),
        ProviderUnavailable: vendor_error(503, "service_unavailable"),
        ProviderQuotaExhausted: vendor_error(429, "quota_exceeded"),
        ProviderInvalidOutput: httpx.Response(200, json=interaction("not json")),
        ProviderAuthError: vendor_error(403, "permission_denied"),
        ProviderBadRequest: vendor_error(404, "model_not_found"),
    }
    return gemini(answers[type(error)])


ADAPTERS: dict[str, Adapter] = {
    "double": Adapter(build=DoubleProvider, failing=lambda error: DoubleProvider(error)),
    "mock": Adapter(
        build=lambda: MockProvider("ok", app_env="test"),
        failing=lambda error: MockProvider("ok", app_env="test", raise_error=error),
    ),
    "gemini_recorded": Adapter(build=gemini, failing=gemini_failing),
}

OPERATIONS = ("generate_itinerary", "modify_itinerary", "health_check", "get_model_metadata")


@pytest.fixture(params=sorted(ADAPTERS), ids=str)
def adapter(request: pytest.FixtureRequest) -> Adapter:
    return ADAPTERS[request.param]


def test_tc_001_adapter_implements_the_model_provider_interface(adapter: Adapter) -> None:
    provider = adapter.build()
    assert isinstance(provider, ModelProvider)
    assert provider.name in ("GEMINI", "MOCK", "FINETUNED_MODEL")
    for name in OPERATIONS:
        operation = getattr(provider, name)
        expected = getattr(ModelProvider, name)
        assert inspect.iscoroutinefunction(operation) == inspect.iscoroutinefunction(expected)
        assert (
            list(inspect.signature(operation).parameters)
            == list(inspect.signature(expected).parameters)[1:]
        )


def test_tc_158_generate_itinerary_returns_a_valid_io_1_result(adapter: Adapter) -> None:
    request = sample_request()
    result = asyncio.run(adapter.build().generate_itinerary(request))

    assert isinstance(result, ProviderResult)
    output = ItineraryOutput.model_validate(result.output.model_dump())
    assert output.unknown_place_ids(request) == []
    assert result.latency_ms >= 0
    # Usage is reported or null, never estimated: no negative or invented values.
    for count in result.usage.model_dump().values():
        assert count is None or count >= 0


def test_health_check_and_metadata_shapes(adapter: Adapter) -> None:
    provider = adapter.build()
    health = asyncio.run(provider.health_check())
    metadata = provider.get_model_metadata()

    assert isinstance(health, HealthStatus)
    assert isinstance(metadata, ModelMetadata)
    assert metadata.provider == provider.name
    assert metadata.supports_structured_output is True
    assert metadata.is_tuned is False


def test_modify_itinerary_is_not_enabled_in_the_mvp(adapter: Adapter) -> None:
    with pytest.raises(ProviderBadRequest):
        asyncio.run(adapter.build().modify_itinerary(ModificationRequest()))


@pytest.mark.parametrize(
    "error",
    [
        ProviderTimeout(),
        ProviderRateLimited(retry_after_s=1),
        ProviderUnavailable(),
        ProviderQuotaExhausted(),
        ProviderInvalidOutput("malformed_json"),
        ProviderAuthError(),
        ProviderBadRequest("model not found"),
    ],
    ids=lambda error: type(error).__name__,
)
def test_failures_surface_as_the_shared_error_types(adapter: Adapter, error: ProviderError) -> None:
    with pytest.raises(type(error)) as raised:
        asyncio.run(adapter.failing(error).generate_itinerary(sample_request()))
    assert raised.value.failure_reason == error.failure_reason


def test_tc_162_generate_itinerary_makes_no_network_call(
    adapter: Adapter, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("an adapter opened a network connection")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)
    result = asyncio.run(adapter.build().generate_itinerary(sample_request()))
    assert result.output.days


# MOCK_PROVIDER_SCENARIO (IMD-27): each failure scenario raises the matching shared error.
MOCK_FAILURE_SCENARIOS: dict[MockScenario, type[ProviderError]] = {
    "timeout": ProviderTimeout,
    "rate_limited": ProviderRateLimited,
    "quota": ProviderQuotaExhausted,
    "invalid_json": ProviderInvalidOutput,
}


@pytest.mark.parametrize("scenario", sorted(MOCK_FAILURE_SCENARIOS))
def test_tc_163_mock_failure_scenarios_raise_the_shared_error(scenario: MockScenario) -> None:
    expected = MOCK_FAILURE_SCENARIOS[scenario]
    provider = MockProvider(scenario, app_env="test")
    with pytest.raises(expected) as raised:
        asyncio.run(provider.generate_itinerary(sample_request()))
    assert raised.value.failure_reason == expected.failure_reason


# ---------- Gemini (IMP-301): TC-003, TC-004, TC-005, and the manual TC-029 ----------


def test_tc_003_gemini_answers_through_the_interface_with_a_provider_result() -> None:
    provider: ModelProvider = gemini()
    result = asyncio.run(provider.generate_itinerary(sample_request()))
    assert isinstance(result, ProviderResult)
    assert result.output == ItineraryOutput.model_validate(SAMPLE_OUTPUT)
    assert result.finish_reason == "completed"
    assert result.provider_request_id == "sample-interaction"


def test_tc_004_gemini_usage_is_mapped() -> None:
    usage = asyncio.run(gemini().generate_itinerary(sample_request())).usage
    assert usage.model_dump() == {
        "input_tokens": 120,
        "output_tokens": 40,
        "thinking_tokens": 10,
        "total_tokens": 170,
    }


def test_tc_004_gemini_usage_stays_null_when_absent() -> None:
    answer = httpx.Response(200, json=interaction(json.dumps(SAMPLE_OUTPUT), usage=None))
    usage = asyncio.run(gemini(answer).generate_itinerary(sample_request())).usage
    assert set(usage.model_dump().values()) == {None}


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        (httpx.ReadTimeout("slow"), ProviderTimeout),
        (vendor_error(504, "deadline_exceeded"), ProviderTimeout),
        (vendor_error(429, "rate_limit_exceeded"), ProviderRateLimited),
        (vendor_error(429, "too_many_requests"), ProviderRateLimited),
        (vendor_error(429, "quota_exceeded"), ProviderQuotaExhausted),
        (vendor_error(402, "payment_required"), ProviderQuotaExhausted),
        (vendor_error(500, "api_error"), ProviderUnavailable),
        (vendor_error(503, "service_unavailable"), ProviderUnavailable),
        (httpx.ConnectError("down"), ProviderUnavailable),
        (vendor_error(401, "authentication"), ProviderAuthError),
        (vendor_error(403, "permission_denied"), ProviderAuthError),
        (vendor_error(400, "invalid_request"), ProviderBadRequest),
        (vendor_error(404, "model_not_found"), ProviderBadRequest),
        (vendor_error(400, "safety"), ProviderInvalidOutput),
    ],
    ids=lambda value: getattr(value, "__name__", None),
)
def test_tc_005_gemini_failures_map_to_the_shared_types(
    answer: httpx.Response | Exception, expected: type[ProviderError]
) -> None:
    with pytest.raises(expected) as raised:
        asyncio.run(gemini(answer).generate_itinerary(sample_request()))
    assert "vendor text" not in str(raised.value)
    assert raised.value.__cause__ is None


@pytest.mark.live
def test_tc_029_gemini_live_smoke() -> None:
    """Manual, key holder only: make live-smoke. Never run by make test or CI (-m "not live")."""
    settings = get_settings()
    if not settings.gemini_api_key.get_secret_value() or not settings.gemini_model_id:
        pytest.skip("GEMINI_API_KEY and GEMINI_MODEL_ID are needed for the live smoke")
    result = asyncio.run(GeminiProvider(settings).generate_itinerary(sample_request()))
    assert result.output.days
    assert result.finish_reason == "completed"
