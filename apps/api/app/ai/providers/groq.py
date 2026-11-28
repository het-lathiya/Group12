"""Groq chat completions through httpx (IMD-223); no vendor SDK or prompt changes.

The wire schema alone adapts io-1/io-2 to Groq's strict subset. Pydantic and the pipeline still
enforce the original contracts. Two transport attempts at most, one on repair; the pipeline
also bounds a second-provider call by the generation allowance left after Gemini.
"""

import asyncio
import json
import math
import random
import time
from collections.abc import Awaitable, Callable, Sequence
from datetime import UTC, datetime
from typing import Any, Final, Literal

import httpx
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
from app.ai.limits import enforce_input_limit
from app.ai.prompts import registry
from app.ai.providers.base import ModelProvider, check_embed_input
from app.core.config import GEMINI_TIME_ALLOWANCE_S, REPAIR_TIME_ALLOWANCE_S, Settings
from app.schemas.ai import (
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

BASE_URL: Final = "https://api.groq.com/openai/v1"
ADAPTER_VERSION: Final = "groq-chat-1"
# Official supported-model lists checked 2026-11-28 (docs/decisions/accounts.md).
STRICT_MODELS: Final = frozenset(
    {"openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.8-27b", "meta-models/muse-spark-open"}
)
SCHEMA_MODELS: Final = STRICT_MODELS | {"openai/gpt-oss-safeguard-20b"}
RETRYABLE: Final = (ProviderTimeout, ProviderRateLimited, ProviderUnavailable)


def wire_schema(model: type[ItineraryOutput] = ItineraryOutput) -> dict[str, Any]:
    """Strict objects require every property; nullable fields retain their null union.

    Remove defaults, which are annotations rather than output constraints. All original value,
    length and count limits stay in this adapter's schema and in the unchanged output model.
    """

    def convert(node: Any, names: bool = False) -> Any:
        if isinstance(node, list):
            return [convert(item) for item in node]
        if not isinstance(node, dict):
            return node
        kept = {
            key: convert(value, not names and key in {"properties", "$defs"})
            for key, value in node.items()
            if names or key not in {"default", "$schema", "$id"}
        }
        if not names and kept.get("type") == "object":
            kept["additionalProperties"] = False
            kept["required"] = list(kept.get("properties", {}))
        return kept

    schema: dict[str, Any] = convert(model.model_json_schema())
    return schema


def response_format(model_id: str, model: type[ItineraryOutput]) -> dict[str, Any]:
    if model_id not in SCHEMA_MODELS:
        return {"type": "json_object"}
    return {
        "type": "json_schema",
        "json_schema": {
            "name": model.__name__,
            "strict": model_id in STRICT_MODELS,
            "schema": wire_schema(model),
        },
    }


def map_status_error(response: httpx.Response) -> ProviderError:
    """Classify by status and a safe code only; never expose the vendor's error message."""
    status = response.status_code
    try:
        data = response.json()
    except ValueError:
        data = None
    error = data.get("error") if isinstance(data, dict) else None
    code = error.get("code") if isinstance(error, dict) else None
    if status == 402:
        return ProviderQuotaExhausted("Groq quota exhausted")
    if status == 429:
        retry_after: float | None
        try:
            retry_after = float(response.headers["retry-after"])
            if not math.isfinite(retry_after) or retry_after < 0:
                retry_after = None
        except (KeyError, ValueError):
            retry_after = None
        return ProviderRateLimited("Groq rate limit", retry_after_s=retry_after)
    if status in (401, 403):
        return ProviderAuthError("Groq refused the key")
    if status == 408:
        return ProviderTimeout("Groq deadline exceeded")
    if status >= 500:
        return ProviderUnavailable(f"Groq unavailable: HTTP {status}")
    if isinstance(code, str) and code in {"json_validate_failed", "json_generation_failed"}:
        return ProviderInvalidOutput("schema_violation")
    if code == "content_policy_violation":
        return ProviderInvalidOutput("blocked")
    return ProviderBadRequest(f"Groq refused the request: HTTP {status}")


def parse_output(data: Any, model: type[ItineraryOutput]) -> tuple[ItineraryOutput, dict[str, Any]]:
    if not isinstance(data, dict):
        raise ProviderInvalidOutput("schema_violation")
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise ProviderInvalidOutput("empty")
    choice = choices[0]
    if choice.get("finish_reason") == "length":
        raise ProviderInvalidOutput("truncated")
    message = choice.get("message")
    if choice.get("finish_reason") == "content_filter" or (
        isinstance(message, dict) and message.get("refusal")
    ):
        raise ProviderInvalidOutput("blocked")
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise ProviderInvalidOutput("empty")
    try:
        output = json.loads(content)
    except ValueError:
        raise ProviderInvalidOutput("malformed_json") from None
    try:
        return model.model_validate(output), choice
    except ValidationError:
        raise ProviderInvalidOutput("schema_violation") from None


def _usage(data: dict[str, Any]) -> UsageMetadata:
    usage = data.get("usage")
    usage = usage if isinstance(usage, dict) else {}
    details = usage.get("completion_tokens_details")
    details = details if isinstance(details, dict) else {}
    try:
        return UsageMetadata(
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            thinking_tokens=details.get("reasoning_tokens"),
            total_tokens=usage.get("total_tokens"),
        )
    except ValidationError:
        raise ProviderInvalidOutput("schema_violation") from None


class GroqProvider:
    name: Literal["GROQ"] = "GROQ"

    def __init__(
        self,
        settings: Settings,
        http_client: httpx.AsyncClient | None = None,
        *,
        embeddings: ModelProvider | None = None,
        clock: Callable[[], float] | None = None,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        self._api_key = settings.groq_api_key.get_secret_value()
        self._model_id = settings.groq_model_id
        self.embedding_model_id = settings.gemini_embedding_model_id
        self._embeddings = embeddings
        self._http_client = http_client
        self._timeout_s = min(settings.gemini_timeout_s, GEMINI_TIME_ALLOWANCE_S)
        self._max_retries = min(settings.gemini_max_retries, 1)
        self._max_input_tokens = settings.ai_max_input_tokens
        self._max_output_tokens = settings.ai_max_output_tokens
        self._clock = clock or time.monotonic
        self._sleep = sleep or asyncio.sleep
        self._last_state: Literal["ok", "degraded", "down"] = "ok"

    @property
    def generation_settings(self) -> dict[str, str | int | float | bool]:
        sent: dict[str, str | int | float | bool] = {
            "api_style": "chat_completions",
            "structured_output": self._model_id in SCHEMA_MODELS,
            "timeout_s": self._timeout_s,
        }
        if self._max_output_tokens is not None:
            sent["max_output_tokens"] = self._max_output_tokens
        return sent

    async def _call_vendor(self, body: dict[str, Any], timeout_s: float) -> httpx.Response:
        async def post(client: httpx.AsyncClient) -> httpx.Response:
            return await client.post(
                f"{BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=body,
                timeout=timeout_s,
            )

        try:
            async with asyncio.timeout(timeout_s):
                if self._http_client is not None:
                    response = await post(self._http_client)
                else:
                    async with httpx.AsyncClient() as client:
                        response = await post(client)
        except (TimeoutError, httpx.TimeoutException):
            raise ProviderTimeout("Groq timed out") from None
        except httpx.TransportError:
            raise ProviderUnavailable("Groq connection failed") from None
        if response.is_error:
            raise map_status_error(response)
        return response

    async def generate_itinerary(
        self, request: GenerationRequest
    ) -> ProviderResult[ItineraryOutput]:
        if not self._api_key.strip():
            raise ProviderAuthError("GROQ_API_KEY is not set")
        if not self._model_id.strip():
            raise ProviderBadRequest("GROQ_MODEL_ID is not set")
        request, _ = enforce_input_limit(request, self._max_input_tokens)
        try:
            template = registry.load(request.prompt_template_id, request.prompt_version)
            system_text, user_text = template.prompt(request)
        except (registry.PromptTemplateNotFound, registry.PromptRenderError):
            raise ProviderBadRequest("the prompt template cannot be rendered") from None
        model = OUTPUT_MODELS[template.meta.output_schema_version]
        body: dict[str, Any] = {
            "model": self._model_id,
            "messages": [
                {"role": "system", "content": system_text},
                {"role": "user", "content": user_text},
            ],
            "response_format": response_format(self._model_id, model),
            "stream": False,
        }
        if self._max_output_tokens is not None:
            body["max_completion_tokens"] = self._max_output_tokens
        repair = request.repair_context is not None
        allowance = REPAIR_TIME_ALLOWANCE_S if repair else GEMINI_TIME_ALLOWANCE_S
        deadline = self._clock() + allowance
        started = time.perf_counter()
        attempts = 1 if repair else 1 + self._max_retries
        try:
            for attempt in range(attempts):
                left = deadline - self._clock()
                if left <= 0:
                    raise ProviderTimeout("Groq time allowance exhausted")
                try:
                    response = await self._call_vendor(body, min(self._timeout_s, left))
                    break
                except RETRYABLE as exc:
                    delay = 2**attempt * random.uniform(0.75, 1.25)  # noqa: S311
                    if isinstance(exc, ProviderRateLimited) and exc.retry_after_s is not None:
                        delay = max(delay, exc.retry_after_s)
                    if attempt + 1 == attempts or delay >= deadline - self._clock():
                        raise
                    await self._sleep(delay)
            try:
                data = response.json()
            except ValueError:
                raise ProviderInvalidOutput("malformed_json") from None
            output, choice = parse_output(data, model)
            result = ProviderResult[ItineraryOutput](
                output=output,
                usage=_usage(data),
                finish_reason=choice.get("finish_reason"),
                latency_ms=round((time.perf_counter() - started) * 1000),
                provider_request_id=data.get("id"),
                model_id=data.get("model") or self._model_id,
            )
        except ProviderAuthError:
            self._last_state = "down"
            raise
        except ProviderError:
            self._last_state = "degraded"
            raise
        except ValidationError:
            raise ProviderInvalidOutput("schema_violation") from None
        self._last_state = "ok"
        return result

    async def modify_itinerary(
        self, request: ModificationRequest
    ) -> ProviderResult[EditOperations]:
        raise ProviderBadRequest("modify_itinerary not enabled in the MVP")

    async def embed_texts(
        self,
        texts: Sequence[str],
        purpose: EmbeddingPurpose,
        titles: Sequence[str | None] | None = None,
    ) -> EmbeddingResult:
        check_embed_input(texts, titles)
        if self._embeddings is None:
            raise ProviderBadRequest("Gemini embeddings are not configured")
        return await self._embeddings.embed_texts(texts, purpose, titles)

    async def health_check(self) -> HealthStatus:
        configured = bool(self._api_key.strip() and self._model_id.strip())
        return HealthStatus(
            status=self._last_state if configured else "down",
            detail=None if configured else "GROQ_API_KEY or GROQ_MODEL_ID is not set",
            checked_at=datetime.now(UTC),
        )

    def get_model_metadata(self) -> ModelMetadata:
        return ModelMetadata(
            provider=self.name,
            model_id=self._model_id,
            adapter_version=ADAPTER_VERSION,
            supports_structured_output=True,  # JSON mode still goes through the same parser
            max_input_tokens=self._max_input_tokens,
            max_output_tokens=self._max_output_tokens,
        )
