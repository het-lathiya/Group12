"""Adapters of the provider contract suite (§8.19; IMP-512; FR-040 AC3, NFR-043).

Every adapter in ``ADAPTERS`` runs the same tests through the ``adapter`` fixture. An entry builds
a working provider and one that fails with a given shared error. A new adapter (for example the
Stage 2 FINETUNED_MODEL) joins the suite by adding one entry here (docs/guides/adding-a-provider.md).

``gemini_recorded`` is the real Gemini adapter replaying provider_recordings/gemini/ through respx
over a fake HTTP transport: no key, no network. Only tests marked ``live`` reach Gemini.
``groq_recorded`` replays synthetic chat-completion recordings through the real Groq httpx adapter.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest
import respx
from fixtures.ai import DoubleProvider
from fixtures.groq import Calls

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
from app.ai.providers.groq import GroqProvider
from app.ai.providers.mock import MockProvider
from app.core.config import Settings

RECORDINGS = Path(__file__).resolve().parents[1] / "fixtures" / "provider_recordings" / "gemini"

GeminiAnswer = httpx.Response | Exception


def recording(name: str) -> httpx.Response:
    """One recorded Gemini answer (``{"http_status", "headers", "body"}``, no key, SAMPLE data)."""
    data = json.loads((RECORDINGS / f"{name}.json").read_text(encoding="utf-8"))
    return httpx.Response(data["http_status"], json=data["body"], headers=data["headers"])


def gemini_replay(answer: GeminiAnswer | None = None) -> GeminiProvider:
    """GeminiProvider whose every request gets ``answer`` (default ``ok.json``) from respx."""
    router = respx.MockRouter(assert_all_called=False)
    route = router.route()
    if isinstance(answer, Exception):
        route.mock(side_effect=answer)
    else:
        route.mock(return_value=answer or recording("ok"))
    settings = Settings(gemini_api_key="contract-key-not-real", gemini_model_id="contract-model")
    client = httpx.AsyncClient(transport=httpx.MockTransport(router.async_handler))
    return GeminiProvider(settings, http_client=client)


# The answer that makes the Gemini adapter raise each shared error. A timeout has no HTTP answer
# to record, so it stays an exception.
GEMINI_FAILURES: dict[type[ProviderError], Callable[[], GeminiAnswer]] = {
    ProviderTimeout: lambda: httpx.ReadTimeout("slow"),
    ProviderRateLimited: lambda: recording("rate_limited_429"),
    ProviderUnavailable: lambda: recording("unavailable_503"),
    ProviderQuotaExhausted: lambda: recording("quota_429"),
    ProviderInvalidOutput: lambda: recording("malformed"),
    ProviderAuthError: lambda: recording("permission_denied_403"),
    ProviderBadRequest: lambda: recording("model_not_found_404"),
}


def groq_recording(name: str) -> httpx.Response:
    data = json.loads((RECORDINGS.parent / "groq" / f"{name}.json").read_text(encoding="utf-8"))
    return httpx.Response(data["http_status"], json=data["body"], headers=data["headers"])


def groq_replay(answer: GeminiAnswer | None = None) -> GroqProvider:
    """Recorded Groq answers through its real httpx adapter, with no network or real waits."""
    return Calls(answer if answer is not None else groq_recording("ok")).provider()


GROQ_FAILURES: dict[type[ProviderError], Callable[[], GeminiAnswer]] = {
    ProviderTimeout: lambda: httpx.ReadTimeout("slow"),
    ProviderRateLimited: lambda: groq_recording("rate_limited_429"),
    ProviderUnavailable: lambda: groq_recording("unavailable_503"),
    ProviderQuotaExhausted: lambda: groq_recording("quota_402"),
    ProviderInvalidOutput: lambda: groq_recording("malformed"),
    ProviderAuthError: lambda: groq_recording("permission_denied_403"),
    ProviderBadRequest: lambda: groq_recording("model_not_found_404"),
}


@dataclass(frozen=True)
class Adapter:
    build: Callable[[], ModelProvider]
    failing: Callable[[ProviderError], ModelProvider]


ADAPTERS: dict[str, Adapter] = {
    # The in-test double stays registered, so the suite keeps checking its own expectations.
    "double": Adapter(build=DoubleProvider, failing=lambda error: DoubleProvider(error)),
    "mock": Adapter(
        build=lambda: MockProvider("ok", app_env="test"),
        failing=lambda error: MockProvider("ok", app_env="test", raise_error=error),
    ),
    "gemini_recorded": Adapter(
        build=gemini_replay,
        failing=lambda error: gemini_replay(GEMINI_FAILURES[type(error)]()),
    ),
    "groq_recorded": Adapter(
        build=groq_replay,
        failing=lambda error: groq_replay(GROQ_FAILURES[type(error)]()),
    ),
}


@pytest.fixture(params=sorted(ADAPTERS), ids=str)
def adapter(request: pytest.FixtureRequest) -> Adapter:
    return ADAPTERS[request.param]


@pytest.fixture
def gemini() -> Callable[[GeminiAnswer | None], GeminiProvider]:
    """Build the Gemini adapter over a given answer (default the ``ok`` recording)."""
    return gemini_replay
