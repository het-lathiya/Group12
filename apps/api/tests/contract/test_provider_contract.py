"""Provider contract suite (§8.19; IMP-110, IMP-207, IMP-301, IMP-512; FR-040 AC1-AC3, NFR-043).

Every adapter must pass the same tests: the ``adapter`` fixture of conftest.py runs each shared test
for ``double``, ``mock`` and ``gemini_recorded`` (the Gemini adapter replaying
provider_recordings/gemini/ with respx). No key and no network: only tests marked ``live`` reach
Gemini, through make live-smoke. A new adapter joins by adding one entry to conftest.ADAPTERS
(docs/guides/adding-a-provider.md).
"""

import ast
import asyncio
import inspect
import json
import math
import socket
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
from fixtures.ai import SAMPLE_OUTPUT, sample_request

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


OPERATIONS = (
    "generate_itinerary",
    "modify_itinerary",
    "embed_texts",
    "health_check",
    "get_model_metadata",
)

# The conftest's Adapter (build, failing) and the gemini fixture's builder; conftest modules are
# not imported.
Adapter = Any
Gemini = Callable[..., GeminiProvider]


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


def test_tc_006_health_check_is_cheap_and_opens_no_connection(
    adapter: Adapter, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("health_check opened a network connection")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)
    provider = adapter.build()

    assert asyncio.run(provider.health_check()).status in ("ok", "degraded", "down")
    assert "generate_itinerary" not in getattr(provider, "calls", [])


def test_tc_006_gemini_health_check_sends_no_request() -> None:
    seen: list[httpx.Request] = []
    provider = embed_gemini(httpx.Response(200, json={}), seen)

    asyncio.run(provider.health_check())

    assert seen == []


def test_tc_007_metadata_names_the_provider_model_and_adapter(adapter: Adapter) -> None:
    provider = adapter.build()
    metadata = provider.get_model_metadata()

    assert metadata.provider == provider.name
    assert metadata.model_id
    assert metadata.adapter_version


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
def test_tc_005_failures_surface_as_the_shared_error_types(
    adapter: Adapter, error: ProviderError
) -> None:
    with pytest.raises(type(error)) as raised:
        asyncio.run(adapter.failing(error).generate_itinerary(sample_request()))
    assert raised.value.failure_reason == error.failure_reason


async def interface_only_caller(provider: ModelProvider) -> list[str]:
    """A caller written against ModelProvider only, as the generation service is."""
    health = await provider.health_check()
    metadata = provider.get_model_metadata()
    result = await provider.generate_itinerary(sample_request())
    output = ItineraryOutput.model_validate(result.output.model_dump())
    return [health.status, metadata.provider, *output.place_ids()]


def test_tc_157_tc_008_the_same_caller_runs_unchanged_on_every_adapter(adapter: Adapter) -> None:
    provider = adapter.build()
    request = sample_request()
    status, name, *place_ids = asyncio.run(interface_only_caller(provider))

    assert status in ("ok", "degraded", "down")
    assert name == provider.name
    assert place_ids
    assert set(place_ids) <= request.shortlist_ids()
    # A failing provider reaches the same caller as the shared type, never a vendor error.
    with pytest.raises(ProviderTimeout):
        asyncio.run(interface_only_caller(adapter.failing(ProviderTimeout())))


APP = Path(__file__).resolve().parents[2] / "app"
CONCRETE_ADAPTERS = (
    "app.ai.providers.gemini",
    "app.ai.providers.mock",
    "app.ai.providers.finetuned",
)


def imported_modules(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
            names.update(f"{node.module}.{alias.name}" for alias in node.names)
    return names


def test_tc_156_generation_imports_no_concrete_adapter_or_vendor_sdk() -> None:
    """FR-040 AC1, card step 3: generation reaches a provider only through factory and base.

    make imports enforces the same rule for every module (.importlinter, TC-002); this test names
    the generation module so a breach there fails make test-contract too.
    """
    files = sorted((APP / "generation").glob("*.py"))
    assert files
    for path in files:
        for name in imported_modules(path):
            assert not name.startswith(CONCRETE_ADAPTERS), f"{path.name} imports {name}"
            assert name.split(".")[0] != "google", f"{path.name} imports {name}"


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

OK_RECORDING = Path(__file__).resolve().parents[1] / "fixtures/provider_recordings/gemini/ok.json"


def test_tc_003_gemini_answers_through_the_interface_with_a_provider_result(
    gemini: Gemini,
) -> None:
    recorded = json.loads(OK_RECORDING.read_text(encoding="utf-8"))["body"]
    provider: ModelProvider = gemini()
    result = asyncio.run(provider.generate_itinerary(sample_request()))
    assert isinstance(result, ProviderResult)
    assert result.output.model_dump(mode="json") == json.loads(
        recorded["steps"][0]["content"][0]["text"]
    )
    assert result.finish_reason == "completed"
    assert result.provider_request_id == recorded["id"]


def test_tc_004_gemini_usage_is_mapped(gemini: Gemini) -> None:
    usage = asyncio.run(gemini().generate_itinerary(sample_request())).usage
    assert usage.model_dump() == {
        "input_tokens": 812,
        "output_tokens": 146,
        "thinking_tokens": 37,
        "total_tokens": 995,
    }


def test_tc_004_gemini_usage_stays_null_when_absent(gemini: Gemini) -> None:
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
    gemini: Gemini, answer: httpx.Response | Exception, expected: type[ProviderError]
) -> None:
    with pytest.raises(expected) as raised:
        asyncio.run(gemini(answer).generate_itinerary(sample_request()))
    assert "vendor text" not in str(raised.value)
    assert raised.value.__cause__ is None


# ---------- embed_texts (IMP-312; Amendment A1 §6.5): TC-444 ----------

EMBED_TEXTS = ["Old fort at sunrise", "Street food market"]
EMBED_MODEL = "gemini-embedding-2"


def embedding_answer(count: int, length: int = 768) -> httpx.Response:
    # A different direction per text, and not unit length, so order and normalising both show.
    embeddings = [{"values": [float(i + 2)] + [1.0] * (length - 1)} for i in range(count)]
    return httpx.Response(200, json={"embeddings": embeddings})


def embed_gemini(
    answer: httpx.Response, seen: list[httpx.Request], model: str = EMBED_MODEL
) -> GeminiProvider:
    def respond(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return answer

    settings = Settings(gemini_api_key="contract-key-not-real", gemini_embedding_model_id=model)
    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    return GeminiProvider(settings, http_client=client)


EMBED_ADAPTERS: dict[str, Callable[[], ModelProvider]] = {
    "mock": lambda: MockProvider("ok", app_env="test"),
    "gemini_fake": lambda: embed_gemini(embedding_answer(len(EMBED_TEXTS)), []),
}


@pytest.mark.parametrize("name", sorted(EMBED_ADAPTERS))
def test_tc_444_embed_returns_768_length_unit_vectors_in_text_order(name: str) -> None:
    result = asyncio.run(EMBED_ADAPTERS[name]().embed_texts(EMBED_TEXTS, "document"))

    assert len(result.vectors) == len(EMBED_TEXTS)
    assert result.vectors[0] != result.vectors[1]
    for vector in result.vectors:
        assert len(vector) == 768
        assert math.isclose(math.sqrt(sum(value * value for value in vector)), 1.0)
    assert result.model_id
    assert result.latency_ms >= 0


@pytest.mark.parametrize("name", sorted(EMBED_ADAPTERS))
@pytest.mark.parametrize(
    ("texts", "titles"),
    [([], None), (["a"] * 33, None), (["a" * 2001], None), (["a", "b"], ["only one"])],
    ids=["empty", "too_many", "too_long", "title_count"],
)
def test_embed_refuses_input_outside_the_limits(
    name: str, texts: list[str], titles: list[str | None] | None
) -> None:
    with pytest.raises(ProviderBadRequest):
        asyncio.run(EMBED_ADAPTERS[name]().embed_texts(texts, "document", titles))


def embed_requests(seen: list[httpx.Request]) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = json.loads(seen[-1].content)["requests"]
    return requests


def test_tc_444_embed_sends_one_content_per_text_with_the_embedding_2_prefixes() -> None:
    seen: list[httpx.Request] = []
    provider = embed_gemini(embedding_answer(2), seen)

    asyncio.run(provider.embed_texts(EMBED_TEXTS, "document", ["The Fort", None]))
    documents = embed_requests(seen)
    asyncio.run(provider.embed_texts(EMBED_TEXTS, "query"))
    queries = embed_requests(seen)

    assert seen[-1].url.path.endswith(f"/models/{EMBED_MODEL}:batchEmbedContents")
    assert [request["content"]["parts"] for request in documents] == [
        [{"text": "title: The Fort | text: Old fort at sunrise"}],
        [{"text": "title: none | text: Street food market"}],
    ]
    assert [request["content"]["parts"] for request in queries] == [
        [{"text": "task: search result | query: Old fort at sunrise"}],
        [{"text": "task: search result | query: Street food market"}],
    ]
    for request in [*documents, *queries]:
        assert request["outputDimensionality"] == 768
        assert "taskType" not in request


@pytest.mark.parametrize(
    ("purpose", "task_type"), [("document", "RETRIEVAL_DOCUMENT"), ("query", "RETRIEVAL_QUERY")]
)
def test_tc_444_embed_sets_the_task_type_and_no_prefix_for_embedding_001(
    purpose: Any, task_type: str
) -> None:
    seen: list[httpx.Request] = []
    provider = embed_gemini(embedding_answer(2), seen, "gemini-embedding-001")

    asyncio.run(provider.embed_texts(EMBED_TEXTS, purpose, ["The Fort", None]))

    requests = embed_requests(seen)
    assert [r["content"]["parts"] for r in requests] == [[{"text": t}] for t in EMBED_TEXTS]
    assert {r["taskType"] for r in requests} == {task_type}
    assert {r["outputDimensionality"] for r in requests} == {768}


@pytest.mark.parametrize(
    "answer",
    [embedding_answer(1), embedding_answer(3), embedding_answer(2, length=767)],
    ids=["fewer", "more", "wrong_length"],
)
def test_tc_444_embed_refuses_an_answer_of_the_wrong_shape(answer: httpx.Response) -> None:
    with pytest.raises(ProviderInvalidOutput) as raised:
        asyncio.run(embed_gemini(answer, []).embed_texts(EMBED_TEXTS, "document"))
    assert raised.value.kind == "schema_violation"


@pytest.mark.live
def test_tc_444_gemini_embed_live() -> None:
    """Manual, key holder only: make live-smoke. Never run by make test or CI (-m "not live")."""
    settings = get_settings()
    if not settings.gemini_api_key.get_secret_value() or not settings.gemini_embedding_model_id:
        pytest.skip("GEMINI_API_KEY and GEMINI_EMBEDDING_MODEL_ID are needed for the live test")
    result = asyncio.run(GeminiProvider(settings).embed_texts(EMBED_TEXTS, "document"))
    assert [len(vector) for vector in result.vectors] == [768, 768]


@pytest.mark.live
def test_tc_029_gemini_live_smoke() -> None:
    """Manual, key holder only: make live-smoke. Never run by make test or CI (-m "not live")."""
    settings = get_settings()
    if not settings.gemini_api_key.get_secret_value() or not settings.gemini_model_id:
        pytest.skip("GEMINI_API_KEY and GEMINI_MODEL_ID are needed for the live smoke")
    result = asyncio.run(GeminiProvider(settings).generate_itinerary(sample_request()))
    assert result.output.days
    assert result.finish_reason == "completed"
