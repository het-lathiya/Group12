"""Stand-ins for running ``app.generation.pipeline`` with no database (IMP-305, IMP-306)."""

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest

from app.ai.providers.base import ModelProvider
from app.ai.providers.gemini import GeminiProvider
from app.core.config import Settings
from app.generation import pipeline
from app.schemas.ai import GenerationRequest, ItineraryOutput

RECORDINGS = Path(__file__).resolve().parent / "provider_recordings" / "gemini"
MODEL = "gemini-3.5-flash-lite"


def recorded_gemini(name: str = "ok") -> GeminiProvider:
    data = json.loads((RECORDINGS / f"{name}.json").read_text(encoding="utf-8"))
    answer = httpx.Response(data["http_status"], json=data["body"], headers=data["headers"])
    settings = Settings(gemini_api_key="not-a-real-key", gemini_model_id=MODEL)
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: answer))
    return GeminiProvider(settings, http_client=client)


class Journal:
    """Stands in for the repository, builder and save, and notes what the pipeline did."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, request: GenerationRequest) -> None:
        self.steps: list[str] = []
        self.settings: dict[str, Any] = {}
        self.saved: ItineraryOutput | None = None
        self.completed: dict[str, Any] = {}
        self.failed: str | None = None
        self.failed_with: dict[str, Any] = {}
        self.inactive: set[UUID] = set()
        self.transactions = 0
        self.open = 0

        async def mark_running(session: object, generation_id: UUID) -> Any:
            self.steps.append("running")
            return type(
                "Row",
                (),
                {
                    "trip_id": uuid4(),
                    "user_id": uuid4(),
                    "prompt_template_id": "itinerary_generate",
                    "prompt_version": "v1",
                },
            )

        async def build(session: object, **kwargs: Any) -> GenerationRequest:
            self.steps.append("build")
            return request

        async def record_settings(
            session: object, generation_id: UUID, settings: dict[str, Any]
        ) -> None:
            self.steps.append("settings")
            self.settings = settings

        async def mark_validating(session: object, generation_id: UUID) -> None:
            self.steps.append("validating")

        async def save(session: object, *args: Any, **kwargs: Any) -> None:
            self.steps.append("save")
            self.saved = args[2]

        async def complete(session: object, generation_id: UUID, **kwargs: Any) -> None:
            self.steps.append("complete")
            self.completed = kwargs

        async def fail(session: object, generation_id: UUID, reason: str, **kwargs: Any) -> None:
            self.steps.append("failed")
            self.failed = reason
            self.failed_with = kwargs

        async def active_place_names(
            session: object, destination_id: UUID, place_ids: list[UUID]
        ) -> dict[UUID, str]:
            return {place_id: "" for place_id in place_ids if place_id not in self.inactive}

        repository = pipeline.repository
        monkeypatch.setattr(repository, "mark_running", mark_running)
        monkeypatch.setattr(repository, "record_settings", record_settings)
        monkeypatch.setattr(repository, "mark_validating", mark_validating)
        monkeypatch.setattr(repository, "complete", complete)
        monkeypatch.setattr(repository, "fail", fail)
        monkeypatch.setattr(pipeline.request_builder, "build", build)
        monkeypatch.setattr(pipeline.itinerary_service, "save_generated_plan", save)
        monkeypatch.setattr(pipeline.places_service, "active_place_names", active_place_names)

    @asynccontextmanager
    async def sessions(self) -> AsyncIterator[Any]:
        self.transactions += 1
        self.open += 1
        yield object()
        self.open -= 1

    def run(self, provider: ModelProvider) -> None:
        asyncio.run(pipeline.run(uuid4(), provider, self.sessions))
