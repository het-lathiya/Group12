"""Provider factory: the one active ModelProvider chosen by AI_PROVIDER (specification §8.4, FR-043).

This is the only module that imports concrete adapters (§4.4, ``.importlinter`` vendor-adapters).
Each adapter is imported inside its own branch, so a process loads only the adapter it uses. The
provider is built once per process from ``Settings``; keys are read only from ``Settings`` (the
environment), never from a file in the repository (TC-013), and no message holds a value.

- MOCK: ``MockProvider`` with MOCK_PROVIDER_SCENARIO and APP_ENV.
- GEMINI: ``GeminiProvider``. Without a key or model ID its health is ``down`` and generations end
  ``failed`` with ``config_error``, and the app keeps running (§8.4: a down provider never stops
  the app). A missing key already stops start-up in staging and production
  (``app.core.config.check_settings``).
- FINETUNED_MODEL: refused with ``ProviderBadRequest`` (IMD-92), "not enabled before Stage 2".

``startup_provider`` is the start-up step of ``app.main``: it checks that PROMPT_TEMPLATE_VERSION
names an existing ``itinerary_generate`` template, builds the provider, calls ``health_check`` once
and logs the metadata. ``get_model_provider`` is the FastAPI dependency the generation code uses.
"""

import logging
from functools import cache
from typing import Annotated, Final, get_args

from fastapi import Depends, Request

from app.ai.errors import ProviderBadRequest, ProviderConfigError
from app.ai.prompts import registry
from app.ai.providers.base import ModelProvider
from app.core.config import AiProvider, AppEnv, ConfigError, MockScenario, Settings, get_settings

logger = logging.getLogger(__name__)

GENERATE_TEMPLATE_ID: Final = "itinerary_generate"
FINETUNED_NOT_ENABLED: Final = (
    "AI_PROVIDER: the FINETUNED_MODEL adapter is not enabled before Stage 2"
)


_gemini_providers: dict[tuple[object, ...], ModelProvider] = {}


@cache
def _build(  # ai_provider is a str: a value that bypassed Settings is refused below
    ai_provider: str, app_env: AppEnv, scenario: MockScenario
) -> ModelProvider:
    if ai_provider == "MOCK":
        from app.ai.providers.mock import MockProvider

        return MockProvider(scenario, app_env=app_env)
    if ai_provider == "FINETUNED_MODEL":
        from app.ai.providers.finetuned import FineTunedProvider

        try:
            return FineTunedProvider()
        except ProviderBadRequest as exc:  # IMD-92: the Stage 1 stub refuses to be built
            raise ProviderBadRequest(FINETUNED_NOT_ENABLED) from exc
    allowed = ", ".join(get_args(AiProvider))
    raise ProviderConfigError(f"AI_PROVIDER must be one of {allowed}")


def get_provider(settings: Settings | None = None) -> ModelProvider:
    """The process's provider for these settings (built once, then reused)."""
    settings = settings or get_settings()
    if settings.ai_provider == "GEMINI":
        return _gemini(settings)
    return _build(settings.ai_provider, settings.app_env, settings.mock_provider_scenario)


def _gemini(settings: Settings) -> ModelProvider:
    # Settings is not hashable, so this cache is keyed by the values the adapter reads.
    key = (
        settings.gemini_api_key.get_secret_value(),
        settings.gemini_model_id,
        settings.gemini_embedding_model_id,
        settings.gemini_timeout_s,
        settings.gemini_max_retries,
        settings.ai_max_input_tokens,
        settings.ai_max_output_tokens,
    )
    if key not in _gemini_providers:
        from app.ai.providers.gemini import GeminiProvider

        _gemini_providers[key] = GeminiProvider(settings)
    return _gemini_providers[key]


def reset_provider_cache() -> None:
    """Forget the built providers (tests only)."""
    _build.cache_clear()
    _gemini_providers.clear()


async def startup_provider(settings: Settings) -> ModelProvider:
    """§8.4 start-up: template check, provider, one health check and the metadata in the log.

    Raises ``ConfigError`` naming the variable (never a value) when the process must not start.
    """
    version = settings.prompt_template_version
    try:
        registry.load(GENERATE_TEMPLATE_ID, version)
    except registry.PromptTemplateNotFound:
        raise ConfigError(
            [
                f"PROMPT_TEMPLATE_VERSION: no {GENERATE_TEMPLATE_ID} template for version "
                f"{version!r} in app/ai/prompts/templates"
            ]
        ) from None
    try:
        provider = get_provider(settings)
    except ProviderConfigError as exc:
        raise ConfigError([str(exc)]) from None

    health = await provider.health_check()
    metadata = provider.get_model_metadata()
    logger.info(
        "model provider %s model %s adapter %s health %s",
        metadata.provider,
        metadata.model_id,
        metadata.adapter_version,
        health.status,
    )
    if health.status != "ok":
        # A down provider never stops the app: generations end failed with config_error (§8.4).
        logger.warning(
            "model provider %s is %s: %s", metadata.provider, health.status, health.detail
        )
    return provider


def get_model_provider(request: Request) -> ModelProvider:
    """FastAPI dependency: the provider resolved at start-up (tests may override it)."""
    provider: ModelProvider | None = getattr(request.app.state, "model_provider", None)
    if provider is None:
        provider = get_provider(request.app.state.settings)
        request.app.state.model_provider = provider
    return provider


ModelProviderDep = Annotated[ModelProvider, Depends(get_model_provider)]
