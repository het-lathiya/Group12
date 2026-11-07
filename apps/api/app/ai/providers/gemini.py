"""Gemini adapter (specification §8.4, FR-041; IMP-301). The only importer of google-genai.

Uses the Interactions API (OD-14; docs/decisions/gemini-setup.md): ``_call_vendor`` holds the only
vendor call, with store=false, the io-1 wire schema, the lowest thinking level the model accepts
and no sampling parameter. One attempt per call: retries and the breaker are IMP-401, so the SDK's
own retries are switched off. Vendor error text is never read: it can echo the prompt (NFR-024).

``embed_texts`` (Amendment A1 §6.5, IMP-312) uses the models API instead, through
``_call_embed_vendor``, with the retries of §8.4 in the adapter. It leaves ``_last_state`` alone:
an embedding failure says nothing about generation (IMD-112). Texts and vectors are never logged.
"""

import asyncio
import json
import random
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, Final, Literal, cast

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

# The SDK exports its Interactions errors from no public module; the version is pinned for this.
from google.genai._gaos.lib.compat_errors import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
)
from google.genai._gaos.types.interactions.interaction import Interaction
from pydantic import ValidationError

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
from app.ai.prompts import registry
from app.ai.providers.base import check_embed_input, l2_normalised
from app.core.config import GEMINI_EMBEDDING_MODELS, GEMINI_TIME_ALLOWANCE_S, Settings
from app.schemas.ai import (
    EMBEDDING_DIMENSIONS,
    OUTPUT_MODELS,
    EditOperations,
    EmbeddingPurpose,
    EmbeddingResult,
    GenerationRequest,
    HealthStatus,
    ItineraryOutput,
    ModelMetadata,
    ModificationRequest,
    ProviderResult,
    UsageMetadata,
)

ADAPTER_VERSION: Final = "gemini-interactions-1"
API_STYLE: Final = "interactions"
# The SDK makes one retry even with attempts=0 and retries only the status codes listed here, so
# one no server sends leaves a single attempt.
NO_SDK_RETRY_STATUS: Final = 599
# gemini-setup.md: the models with "minimal"; every listed text model accepts "low".
MINIMAL_THINKING_MODELS: Final = frozenset({"gemini-3.5-flash-lite", "gemini-3.6-flash"})
# The generation blocked codes of the API errors page, and the card's jailbreak.
BLOCKED_CODES: Final = frozenset(
    {
        "safety",
        "jailbreak",
        "recitation",
        "language",
        "prohibited_content",
        "spii",
        "blocklist",
        "content_blocked",
    }
)
TRUNCATED_STATUSES: Final = frozenset({"incomplete", "requires_continuation"})
DROPPED_SCHEMA_KEYS: Final = frozenset({"$schema", "$id", "pattern"})
EMBEDDING_2: Final = GEMINI_EMBEDDING_MODELS[0]
EMBED_TASK_TYPES: Final[dict[EmbeddingPurpose, str]] = {
    "document": "RETRIEVAL_DOCUMENT",
    "query": "RETRIEVAL_QUERY",
}
RETRYABLE: Final = (ProviderTimeout, ProviderRateLimited, ProviderUnavailable)
BACKOFF_BASE_S: Final = 1.0
BACKOFF_JITTER: Final = 0.25

Health = Literal["ok", "degraded", "down"]


def _without_keys(node: Any) -> Any:
    if isinstance(node, dict):
        return {k: _without_keys(v) for k, v in node.items() if k not in DROPPED_SCHEMA_KEYS}
    if isinstance(node, list):
        return [_without_keys(item) for item in node]
    return node


def wire_schema(model: type[ItineraryOutput] = ItineraryOutput) -> dict[str, Any]:
    """The output schema as sent (§8.7): no $schema, $id or pattern; HH:MM stays in description."""
    schema: dict[str, Any] = _without_keys(model.model_json_schema())
    return schema


def thinking_level(model_id: str) -> str:
    return "minimal" if model_id in MINIMAL_THINKING_MODELS else "low"


def _error_code(body: object) -> str:
    """The snake_case error code of a vendor error body; its message is never read."""
    error = body.get("error") if isinstance(body, Mapping) else None
    code = error.get("code") if isinstance(error, Mapping) else None
    return code.lower() if isinstance(code, str) else ""


def _retry_after_s(headers: httpx.Headers) -> float | None:
    try:
        return float(headers["retry-after"])
    except (KeyError, ValueError):
        return None


def map_status_error(status: int, code: str, headers: httpx.Headers) -> ProviderError:
    """The shared error of an HTTP failure (§8.4). The code is read before the status."""
    if code in BLOCKED_CODES:
        return ProviderInvalidOutput("blocked")
    if status == 402 or code == "quota_exceeded":
        return ProviderQuotaExhausted("Gemini quota exhausted")
    if status == 429:
        return ProviderRateLimited("Gemini rate limit", retry_after_s=_retry_after_s(headers))
    if status in (401, 403):
        return ProviderAuthError("Gemini refused the key")
    if status in (408, 504):
        return ProviderTimeout("Gemini deadline exceeded")
    if status >= 500:
        return ProviderUnavailable(f"Gemini unavailable: HTTP {status}")
    return ProviderBadRequest(f"Gemini refused the request: HTTP {status}")


def _models_api_code(error: genai_errors.APIError) -> str:
    """The code ``map_status_error`` reads, from a models API error. Its message is never read.

    That API answers RESOURCE_EXHAUSTED for both limits; a per-day quota ID marks the daily quota.
    Unverified without a key (PD-IMP-312-2).
    """
    body = error.details if isinstance(error.details, Mapping) else {}
    details = body.get("error", {}).get("details") if isinstance(body.get("error"), Mapping) else []
    for detail in details if isinstance(details, list) else []:
        violations = detail.get("violations") if isinstance(detail, Mapping) else None
        for violation in violations if isinstance(violations, list) else []:
            if isinstance(violation, Mapping) and "PerDay" in str(violation.get("quotaId")):
                return "quota_exceeded"
    return (error.status or "").lower()


def _embed_text(model_id: str, text: str, purpose: EmbeddingPurpose, title: str | None) -> str:
    """A1 §6.5: gemini-embedding-2 takes no task type, so the purpose goes in a prefix."""
    if model_id != EMBEDDING_2:
        return text
    if purpose == "query":
        return f"task: search result | query: {text}"
    return f"title: {title or 'none'} | text: {text}"


def _embed_vector(embedding: types.ContentEmbedding) -> list[float]:
    values = embedding.values or []
    if len(values) != EMBEDDING_DIMENSIONS or not any(values):
        raise ProviderInvalidOutput("schema_violation")
    return l2_normalised(values)


def _usage(interaction: Interaction) -> UsageMetadata:
    usage = interaction.usage
    if usage is None:
        return UsageMetadata(
            input_tokens=None, output_tokens=None, thinking_tokens=None, total_tokens=None
        )
    return UsageMetadata(
        input_tokens=usage.total_input_tokens,
        output_tokens=usage.total_output_tokens,
        thinking_tokens=usage.total_thought_tokens,
        total_tokens=usage.total_tokens,
    )


def parse_output(
    interaction: Interaction, model: type[ItineraryOutput] = ItineraryOutput
) -> ItineraryOutput:
    """The answer of a finished interaction, or the invalid-output kind saying why not (§8.4)."""
    codes = {(error.code or "").lower() for error in interaction.errors or []}
    if codes & BLOCKED_CODES:
        raise ProviderInvalidOutput("blocked")
    if interaction.status in TRUNCATED_STATUSES:
        raise ProviderInvalidOutput("truncated")
    if interaction.status != "completed":
        raise ProviderUnavailable(f"Gemini interaction ended {interaction.status}")
    text = interaction.output_text
    if not text or not text.strip():
        raise ProviderInvalidOutput("empty")
    try:
        data = json.loads(text)
    except ValueError:
        raise ProviderInvalidOutput("malformed_json") from None
    try:
        return model.model_validate(data)
    except ValidationError:
        raise ProviderInvalidOutput("schema_violation") from None


class GeminiProvider:
    name: Literal["GEMINI"] = "GEMINI"

    def __init__(self, settings: Settings, http_client: httpx.AsyncClient | None = None) -> None:
        self._api_key = settings.gemini_api_key.get_secret_value()
        self._model_id = settings.gemini_model_id
        self.embedding_model_id = settings.gemini_embedding_model_id
        self._max_retries = settings.gemini_max_retries
        self._max_input_tokens = settings.ai_max_input_tokens
        self._max_output_tokens = settings.ai_max_output_tokens
        # shortcut: the whole allowance, not what is left of it; the retry loop of IMP-401 owns
        # that clock and must bound each attempt by the time left.
        self._timeout_s = min(settings.gemini_timeout_s, GEMINI_TIME_ALLOWANCE_S)
        self._http_client = http_client
        self._client: genai.Client | None = None
        self._last_state: Health = "ok"

    @property
    def generation_settings(self) -> dict[str, str | int | float | bool]:
        """The names and values actually sent (§8.4 settings record)."""
        sent: dict[str, str | int | float | bool] = {
            "api_style": API_STYLE,
            "thinking_level": thinking_level(self._model_id),
            "structured_output": True,
            "timeout_s": self._timeout_s,
        }
        if self._max_output_tokens is not None:
            sent["max_output_tokens"] = self._max_output_tokens
        return sent

    def _vendor_client(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(
                api_key=self._api_key,
                http_options=types.HttpOptions(
                    timeout=int(self._timeout_s * 1000),
                    retry_options=types.HttpRetryOptions(
                        attempts=0, http_status_codes=[NO_SDK_RETRY_STATUS]
                    ),
                    httpx_async_client=self._http_client,
                ),
            )
        return self._client

    async def _call_vendor(
        self, system_text: str, user_text: str, schema: dict[str, Any], timeout_s: float
    ) -> Interaction:
        """The only vendor call (§8.4). Raises shared errors only, with none of the vendor's text."""
        config: dict[str, Any] = {"thinking_level": thinking_level(self._model_id)}
        if self._max_output_tokens is not None:
            config["max_output_tokens"] = self._max_output_tokens
        try:
            async with asyncio.timeout(timeout_s):
                answer = await self._vendor_client().aio.interactions.create(
                    model=self._model_id,
                    system_instruction=system_text,
                    input=user_text,
                    store=False,
                    response_format={
                        "type": "text",
                        "mime_type": "application/json",
                        "schema": schema,
                    },
                    generation_config=config,
                    stream=False,
                    automatic_continuation=False,
                )
            return cast(Interaction, answer)  # stream=False: the SDK's union also lists a stream
        except (TimeoutError, APITimeoutError):
            raise ProviderTimeout("Gemini timed out") from None
        except APIStatusError as exc:
            raise map_status_error(
                exc.response.status_code, _error_code(exc.body), exc.response.headers
            ) from None
        except APIConnectionError:
            raise ProviderUnavailable("Gemini connection failed") from None
        except APIError:  # the body of a 200 answer that is not an Interaction
            raise ProviderInvalidOutput("malformed_json") from None

    async def generate_itinerary(
        self, request: GenerationRequest
    ) -> ProviderResult[ItineraryOutput]:
        if not self._api_key:
            raise ProviderAuthError("GEMINI_API_KEY is not set")
        if not self._model_id:
            raise ProviderBadRequest("GEMINI_MODEL_ID is not set")
        try:
            template = registry.load(request.prompt_template_id, request.prompt_version)
            system_text, user_text = template.prompt(request)
        except (registry.PromptTemplateNotFound, registry.PromptRenderError):
            raise ProviderBadRequest("the prompt template cannot be rendered") from None
        output_model = OUTPUT_MODELS[template.meta.output_schema_version]

        started = time.perf_counter()
        try:
            interaction = await self._call_vendor(
                system_text, user_text, wire_schema(output_model), self._timeout_s
            )
            output = parse_output(interaction, output_model)
        except ProviderAuthError:
            self._last_state = "down"
            raise
        except (ProviderInvalidOutput, ProviderBadRequest):
            self._last_state = "ok"  # the service answered
            raise
        except ProviderError:
            self._last_state = "degraded"
            raise
        self._last_state = "ok"
        return ProviderResult[ItineraryOutput](
            output=output,
            usage=_usage(interaction),
            finish_reason=interaction.status,
            latency_ms=round((time.perf_counter() - started) * 1000),
            provider_request_id=interaction.id or None,
        )

    async def modify_itinerary(
        self, request: ModificationRequest
    ) -> ProviderResult[EditOperations]:
        raise ProviderBadRequest("modify_itinerary not enabled in the MVP")

    async def _call_embed_vendor(
        self,
        contents: list[types.Content],
        config: types.EmbedContentConfig,
        timeout_s: float,
    ) -> types.EmbedContentResponse:
        """The only embedding call (A1 §6.5). Raises shared errors only, with no vendor text."""
        try:
            async with asyncio.timeout(timeout_s):
                return await self._vendor_client().aio.models.embed_content(
                    model=self.embedding_model_id,
                    contents=cast(types.ContentListUnion, contents),
                    config=config,
                )
        except (TimeoutError, httpx.TimeoutException):
            raise ProviderTimeout("Gemini embedding timed out") from None
        except genai_errors.APIError as exc:
            raise map_status_error(
                exc.code,
                _models_api_code(exc),
                httpx.Headers(getattr(exc.response, "headers", None) or {}),
            ) from None
        except httpx.TransportError:
            raise ProviderUnavailable("Gemini connection failed") from None
        except ValueError:  # the body of a 200 answer that is not an embedding response
            raise ProviderInvalidOutput("malformed_json") from None

    async def _embed_with_retries(
        self, contents: list[types.Content], config: types.EmbedContentConfig
    ) -> types.EmbedContentResponse:
        """§8.4: transient errors only, backoff 1, 2, 4 s with ±25 % jitter, within the allowance."""
        deadline = time.monotonic() + GEMINI_TIME_ALLOWANCE_S
        attempt = 0
        while True:
            left = deadline - time.monotonic()
            try:
                return await self._call_embed_vendor(contents, config, min(self._timeout_s, left))
            except RETRYABLE as exc:
                backoff = BACKOFF_BASE_S * 2**attempt
                delay = backoff * random.uniform(1 - BACKOFF_JITTER, 1 + BACKOFF_JITTER)  # noqa: S311
                if isinstance(exc, ProviderRateLimited) and exc.retry_after_s is not None:
                    delay = max(delay, exc.retry_after_s)
                if attempt >= self._max_retries or delay >= deadline - time.monotonic():
                    raise
            attempt += 1
            await asyncio.sleep(delay)

    async def embed_texts(
        self,
        texts: Sequence[str],
        purpose: EmbeddingPurpose,
        titles: Sequence[str | None] | None = None,
    ) -> EmbeddingResult:
        check_embed_input(texts, titles)
        if not self._api_key:
            raise ProviderAuthError("GEMINI_API_KEY is not set")
        if self.embedding_model_id not in GEMINI_EMBEDDING_MODELS:
            raise ProviderBadRequest("GEMINI_EMBEDDING_MODEL_ID is not set or not supported")
        model_id = self.embedding_model_id
        started = time.perf_counter()
        # One Content per text: gemini-embedding-2 merges the parts of one content into one vector.
        contents = [
            types.Content(
                parts=[types.Part(text=_embed_text(model_id, text, purpose, title))],
            )
            for text, title in zip(texts, titles or [None] * len(texts), strict=True)
        ]
        config = types.EmbedContentConfig(
            output_dimensionality=EMBEDDING_DIMENSIONS,
            task_type=None if model_id == EMBEDDING_2 else EMBED_TASK_TYPES[purpose],
        )
        response = await self._embed_with_retries(contents, config)
        embeddings = response.embeddings or []
        if len(embeddings) != len(texts):
            raise ProviderInvalidOutput("schema_violation")
        return EmbeddingResult(
            vectors=[_embed_vector(embedding) for embedding in embeddings],
            model_id=model_id,
            usage=UsageMetadata(),  # the Gemini API reports no embedding token counts
            latency_ms=round((time.perf_counter() - started) * 1000),
        )

    async def health_check(self) -> HealthStatus:
        """From the configuration and the last call; never a generation call."""
        status: Health = self._last_state
        detail = None if status == "ok" else f"last Gemini call: {status}"
        if not self._api_key or not self._model_id:
            status, detail = "down", "GEMINI_API_KEY or GEMINI_MODEL_ID is not set"
        return HealthStatus(status=status, detail=detail, checked_at=datetime.now(UTC))

    def get_model_metadata(self) -> ModelMetadata:
        return ModelMetadata(
            provider=self.name,
            model_id=self._model_id,
            adapter_version=ADAPTER_VERSION,
            supports_structured_output=True,
            max_input_tokens=self._max_input_tokens,
            max_output_tokens=self._max_output_tokens,
        )
