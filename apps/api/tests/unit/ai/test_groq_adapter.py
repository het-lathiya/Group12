"""Groq transport mapping and bounded retries (IMD-223, FR-040..FR-046), never live."""

import asyncio
import json

import httpx
import pytest
from fixtures.ai import sample_request
from fixtures.groq import MODEL, Calls, completion
from pydantic import SecretStr

from app.ai import factory
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
from app.ai.providers.groq import GroqProvider
from app.ai.providers.mock import MockProvider
from app.core.config import ConfigError, Settings, check_settings
from app.schemas.ai import RepairContext


def test_success_reports_actual_model_usage_and_shared_interface() -> None:
    calls = Calls()
    provider = calls.provider(ai_max_output_tokens=2048)
    assert isinstance(provider, ModelProvider)
    result = asyncio.run(provider.generate_itinerary(sample_request()))
    assert result.output.unknown_place_ids(sample_request()) == []
    assert result.model_id == MODEL
    assert result.provider_request_id == "sample-completion"
    assert result.usage.model_dump() == {
        "input_tokens": 120,
        "output_tokens": 40,
        "thinking_tokens": 10,
        "total_tokens": 160,
    }
    body = json.loads(calls.requests[0].content)
    assert str(calls.requests[0].url) == "https://api.groq.com/openai/v1/chat/completions"
    assert body["max_completion_tokens"] == 2048
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["strict"] is True
    assert len(calls.requests) == 1


@pytest.mark.parametrize(
    ("answer", "error"),
    [
        (httpx.Response(429, headers={"retry-after": "2"}), ProviderRateLimited),
        (httpx.Response(500), ProviderUnavailable),
        (httpx.Response(503), ProviderUnavailable),
        (httpx.Response(504), ProviderUnavailable),
        (httpx.ConnectError("sensitive transport text"), ProviderUnavailable),
        (httpx.ReadTimeout("sensitive transport text"), ProviderTimeout),
        (httpx.Response(401), ProviderAuthError),
        (httpx.Response(403), ProviderAuthError),
        (httpx.Response(402), ProviderQuotaExhausted),
        (httpx.Response(400), ProviderBadRequest),
        (httpx.Response(404), ProviderBadRequest),
    ],
)
def test_transport_errors_are_shared_and_retry_at_most_once(
    answer: httpx.Response | Exception, error: type[ProviderError]
) -> None:
    calls = Calls(answer)
    with pytest.raises(error) as raised:
        asyncio.run(calls.provider().generate_itinerary(sample_request()))
    assert len(calls.requests) == (2 if raised.value.retryable else 1)
    assert "sensitive" not in str(raised.value)
    assert raised.value.__cause__ is None
    if error is ProviderRateLimited:
        assert raised.value.retry_after_s == 2
        assert calls.delays == [2]


@pytest.mark.parametrize(
    ("body", "kind"),
    [
        (completion("{"), "malformed_json"),
        (completion("{}"), "schema_violation"),
        (completion(""), "empty"),
        (completion(choices=[]), "empty"),
        (completion(choices=[{"finish_reason": "length"}]), "truncated"),
        (completion(choices=[{"finish_reason": "content_filter"}]), "blocked"),
        (completion(usage={"prompt_tokens": -1}), "schema_violation"),
    ],
)
def test_invalid_output_is_never_blindly_retried(body: dict, kind: str) -> None:
    calls = Calls(httpx.Response(200, json=body))
    with pytest.raises(ProviderInvalidOutput) as raised:
        asyncio.run(calls.provider().generate_itinerary(sample_request()))
    assert raised.value.kind == kind
    assert len(calls.requests) == 1


def test_bad_response_envelope_is_invalid_json() -> None:
    calls = Calls(httpx.Response(200, text="<html>unusable</html>"))
    with pytest.raises(ProviderInvalidOutput, match="malformed_json"):
        asyncio.run(calls.provider().generate_itinerary(sample_request()))
    assert len(calls.requests) == 1


def test_retry_after_cannot_outlive_the_allowance() -> None:
    calls = Calls(httpx.Response(429, headers={"retry-after": "120"}))
    with pytest.raises(ProviderRateLimited):
        asyncio.run(calls.provider().generate_itinerary(sample_request()))
    assert len(calls.requests) == 1
    assert calls.delays == []


def test_repair_has_one_attempt_and_a_25_second_timeout() -> None:
    calls = Calls(httpx.Response(503))
    request = sample_request().model_copy(
        update={"repair_context": RepairContext(invalid_output="", findings=[])}
    )
    with pytest.raises(ProviderUnavailable):
        asyncio.run(calls.provider().generate_itinerary(request))
    assert len(calls.requests) == 1
    assert calls.requests[0].extensions["timeout"]["read"] <= 25


@pytest.mark.parametrize(
    ("key", "model"), [("", MODEL), ("fake-not-real", ""), ("", ""), ("<key>", MODEL)]
)
def test_optional_provider_is_off_if_either_setting_is_missing(key: str, model: str) -> None:
    assert factory.get_groq_provider(Settings(groq_api_key=key, groq_model_id=model)) is None


def test_factory_caches_groq_and_keeps_gemini_embeddings() -> None:
    settings = Settings(
        ai_provider="GROQ",
        groq_api_key="fake-not-real",
        groq_model_id=MODEL,
        gemini_embedding_model_id="gemini-embedding-2",
    )
    provider = factory.get_provider(settings)
    assert factory.get_provider(settings) is provider
    assert provider.embedding_model_id == "gemini-embedding-2"
    assert provider.get_model_metadata().provider == "GROQ"
    assert asyncio.run(provider.health_check()).status == "ok"


def test_embedding_delegation_leaves_generation_transport_alone() -> None:
    embeddings = MockProvider("ok", app_env="test")
    provider = GroqProvider(Settings(), embeddings=embeddings)
    result = asyncio.run(provider.embed_texts(["query"], "query"))
    assert result.model_id == embeddings.embedding_model_id


def test_absent_usage_stays_null() -> None:
    result = asyncio.run(
        Calls(httpx.Response(200, json=completion(usage=None)))
        .provider()
        .generate_itinerary(sample_request())
    )
    assert set(result.usage.model_dump().values()) == {None}


def test_missing_direct_provider_settings_fail_without_a_network_call() -> None:
    assert asyncio.run(GroqProvider(Settings()).health_check()).status == "down"
    with pytest.raises(ProviderAuthError, match="GROQ_API_KEY"):
        asyncio.run(GroqProvider(Settings()).generate_itinerary(sample_request()))
    with pytest.raises(ProviderBadRequest, match="GROQ_MODEL_ID"):
        asyncio.run(
            GroqProvider(Settings(groq_api_key=SecretStr("fake-not-real"))).generate_itinerary(
                sample_request()
            )
        )


def test_deployed_direct_groq_checks_name_only(clean_settings_env: pytest.MonkeyPatch) -> None:
    settings = Settings(
        app_env="production", ai_provider="GROQ", database_url="postgresql://local/test"
    )
    with pytest.raises(ConfigError) as raised:
        check_settings(settings, {})
    assert "GROQ_API_KEY" in str(raised.value)
    assert "GROQ_MODEL_ID" in str(raised.value)
