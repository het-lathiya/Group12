"""Scripted io-2 response for the guide-citation regression; no provider calls."""

from app.ai.prompts import registry
from app.ai.providers.mock import MockProvider
from app.schemas.ai import (
    GenerationRequest,
    GroundedGenerationRequest,
    GroundedItineraryOutput,
    ItineraryOutput,
    ProviderResult,
)


class GuideCitationMock(MockProvider):
    """Quote one supplied guide in the first note, with invalid citations beside its UUID."""

    def __init__(self) -> None:
        super().__init__("ok", app_env="test")
        self.requests: list[GroundedGenerationRequest] = []
        self.prompts: list[tuple[str, str]] = []
        self.outputs: list[GroundedItineraryOutput] = []

    async def generate_itinerary(
        self, request: GenerationRequest
    ) -> ProviderResult[ItineraryOutput]:
        assert isinstance(request, GroundedGenerationRequest)
        assert request.prompt_version == "v2"
        self.requests.append(request)
        self.prompts.append(
            registry.render(request.prompt_template_id, request.prompt_version, request)
        )
        guide = next(p for p in request.context_passages if p.kind == "guide")
        result = await super().generate_itinerary(request)
        data = result.output.model_dump()
        item = data["days"][0]["items"][0]
        item["note"] = f"SAMPLE guide note: {guide.text}"[:200]
        # A document key and duplicate must be removed without losing the valid chunk UUID.
        item["source_ids"] = [
            str(guide.passage_id),
            "guide:another-city/foreign",
            str(guide.passage_id),
        ]
        output = GroundedItineraryOutput.model_validate(data)
        self.outputs.append(output)
        return result.model_copy(update={"output": output})
