"""The ModelProvider interface (specification §8.3, FR-040, IMD-06).

Code outside ``app/ai/`` uses a provider only through this module, ``app.ai.errors``,
``app.ai.factory`` (IMP-207) and ``app.ai.limits`` (IMP-305); it never imports an adapter or a
vendor SDK (§4.4, NFR-031). The
types of the interface are defined in ``app.schemas.ai`` and re-exported here.
"""

import math
from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from app.ai.errors import ProviderBadRequest
from app.schemas.ai import (
    MAX_EMBED_TEXT_CHARS,
    MAX_EMBED_TEXTS,
    EditOperations,
    EmbeddingPurpose,
    EmbeddingResult,
    GenerationRequest,
    HealthStatus,
    ItineraryOutput,
    ModelMetadata,
    ModificationRequest,
    ProviderName,
    ProviderResult,
    UsageMetadata,
)

__all__ = [
    "EditOperations",
    "EmbeddingPurpose",
    "EmbeddingResult",
    "GenerationRequest",
    "HealthStatus",
    "ItineraryOutput",
    "ModelMetadata",
    "ModelProvider",
    "ModificationRequest",
    "ProviderName",
    "ProviderResult",
    "UsageMetadata",
    "check_embed_input",
    "l2_normalised",
]


def check_embed_input(texts: Sequence[str], titles: Sequence[str | None] | None) -> None:
    """A1 §6.5: 1 to 32 texts of at most 2,000 characters; titles, if any, match them one to one."""
    if not 1 <= len(texts) <= MAX_EMBED_TEXTS:
        raise ProviderBadRequest(f"embed_texts takes 1 to {MAX_EMBED_TEXTS} texts")
    if any(len(text) > MAX_EMBED_TEXT_CHARS for text in texts):
        raise ProviderBadRequest(f"embed_texts takes at most {MAX_EMBED_TEXT_CHARS} characters")
    if titles is not None and len(titles) != len(texts):
        raise ProviderBadRequest("embed_texts needs one title per text")


def l2_normalised(vector: Sequence[float]) -> list[float]:
    """The vector scaled to unit length; the caller handles the zero vector."""
    length = math.sqrt(sum(value * value for value in vector))
    return [value / length for value in vector]


@runtime_checkable
class ModelProvider(Protocol):
    """One model provider: GEMINI, MOCK or FINETUNED_MODEL (Stage 2).

    Every operation raises only ``app.ai.errors.ProviderError`` subclasses. The assistive EXT
    operations of §8.20 are added by their own cards.
    """

    @property
    def name(self) -> ProviderName:
        """GEMINI, MOCK or FINETUNED_MODEL; an adapter sets it as a class attribute.

        Read-only in the interface, so an adapter may declare its own single literal.
        """
        ...

    async def generate_itinerary(
        self, request: GenerationRequest
    ) -> ProviderResult[ItineraryOutput]:
        """Propose an itinerary (io-1) for a gr-1 request."""
        ...

    async def modify_itinerary(
        self, request: ModificationRequest
    ) -> ProviderResult[EditOperations]:
        """R2. In the MVP an adapter may raise ``ProviderBadRequest("not enabled")``."""
        ...

    async def embed_texts(
        self,
        texts: Sequence[str],
        purpose: EmbeddingPurpose,
        titles: Sequence[str | None] | None = None,
    ) -> EmbeddingResult:
        """Embed texts for retrieval (A1 §6.5); never touches the generation breaker (IMD-112)."""
        ...

    async def health_check(self) -> HealthStatus:
        """Cheap status check; never raises and makes no generation call."""
        ...

    def get_model_metadata(self) -> ModelMetadata:
        """Provider, model and adapter identity; never raises."""
        ...
