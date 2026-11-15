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
from app.itinerary.schemas import PlannedDay
from app.rag.service import RetrievalResult
from app.routing.estimate import TravelEstimate, TravelMode
from app.schemas.ai import GenerationRequest

RECORDINGS = Path(__file__).resolve().parent / "provider_recordings" / "gemini"
MODEL = "gemini-3.5-flash-lite"


def recorded_gemini(name: str = "ok") -> GeminiProvider:
    data = json.loads((RECORDINGS / f"{name}.json").read_text(encoding="utf-8"))
    answer = httpx.Response(data["http_status"], json=data["body"], headers=data["headers"])
    settings = Settings(gemini_api_key="not-a-real-key", gemini_model_id=MODEL)
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: answer))
    return GeminiProvider(settings, http_client=client)


class FixedRouting:
    """Ten minutes and 800 metres between any two places, from the routing service."""

    async def travel(self, origin: Any, target: Any, mode: TravelMode | str) -> TravelEstimate:
        return TravelEstimate(10, 800, TravelMode(mode), "routing_api")


class Journal:
    """Stands in for the repository, builder and save, and notes what the pipeline did."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, request: GenerationRequest) -> None:
        self.steps: list[str] = []
        self.settings: dict[str, Any] = {}
        self.retrieval: dict[str, Any] = {}
        self.saved: list[PlannedDay] | None = None
        self.findings: list[Any] = []  # the warnings saved with the plan
        self.reasons: dict[str, tuple[str, str]] = {}  # must_visit_reasons; empty means no room
        self.completed: dict[str, Any] = {}
        self.failed: str | None = None
        self.failed_with: dict[str, Any] = {}
        self.inactive: set[UUID] = set()
        self.model_id = "mock-v1"  # rule_based_planner_v1 runs the job as mode rule_based
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
                    "model_id": self.model_id,
                    "scope": request.scope.kind,
                    "scope_day_number": request.scope.day_number,
                    "request_hash": None,
                },
            )

        async def retrieve(*args: Any) -> RetrievalResult:
            return RetrievalResult("lexical_fallback", None, {}, {}, [], 0)

        async def build(session: object, **kwargs: Any) -> GenerationRequest:
            self.steps.append("build")
            return request

        async def record_settings(
            session: object, generation_id: UUID, settings: dict[str, Any]
        ) -> None:
            self.steps.append("settings")
            self.settings = settings

        async def record_retrieval(session: object, generation_id: UUID, **kwargs: Any) -> None:
            self.steps.append("retrieval")
            self.retrieval = kwargs

        async def mark_validating(session: object, generation_id: UUID) -> None:
            self.steps.append("validating")

        async def mark_repairing(session: object, generation_id: UUID) -> None:
            self.steps.append("repairing")

        async def save(session: object, *args: Any, **kwargs: Any) -> None:
            self.steps.append("save")
            self.saved = args[2]
            self.findings = list(kwargs.get("findings", []))

        async def reasons(*args: Any) -> dict[str, tuple[str, str]]:
            return self.reasons

        async def validation_hours(*args: Any) -> tuple[str, None]:
            return "UTC", None  # This stand-in has no database hours; boundaries have pure tests.

        async def nothing(*args: Any) -> None:
            return None

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
            names = {place.place_id: place.name for place in request.shortlist}
            return {
                place_id: names.get(place_id, "")
                for place_id in place_ids
                if place_id not in self.inactive
            }

        repository = pipeline.repository
        monkeypatch.setattr(repository, "mark_running", mark_running)
        monkeypatch.setattr(repository, "record_settings", record_settings)
        monkeypatch.setattr(repository, "record_retrieval", record_retrieval)
        monkeypatch.setattr(repository, "mark_validating", mark_validating)
        monkeypatch.setattr(repository, "mark_repairing", mark_repairing)
        monkeypatch.setattr(repository, "complete", complete)
        monkeypatch.setattr(repository, "fail", fail)

        async def add_costs(session: object, days: list[PlannedDay], *ids: UUID) -> Any:
            return days

        monkeypatch.setattr(pipeline, "routing_for", lambda session: FixedRouting())
        monkeypatch.setattr(pipeline, "add_costs", add_costs)
        monkeypatch.setattr(pipeline.request_builder, "retrieve", retrieve)
        monkeypatch.setattr(pipeline.request_builder, "build", build)
        monkeypatch.setattr(pipeline.itinerary_service, "save_generated_plan", save)
        monkeypatch.setattr(pipeline.itinerary_service, "validation_hours", validation_hours)
        monkeypatch.setattr(pipeline.itinerary_service, "validation_cost_inputs", nothing)
        monkeypatch.setattr(pipeline.places_service, "active_place_names", active_place_names)
        monkeypatch.setattr(pipeline.retrieval, "must_visit_reasons", reasons)
        monkeypatch.setattr(pipeline.trips_service, "get_trip", nothing)
        monkeypatch.setattr(pipeline.trips_service, "get_preferences", nothing)

    @asynccontextmanager
    async def sessions(self) -> AsyncIterator[Any]:
        self.transactions += 1
        self.open += 1
        yield object()
        self.open -= 1

    def fell_back(self, cause: str | None) -> bool:
        """The rule-based plan was saved instead of the answer, with ``cause`` recorded."""
        summary = self.completed.get("validation_summary", {})
        return (
            self.completed.get("outcome") == "fallback_rule_based"
            and summary.get("provider_failure") == cause
            and self.saved is not None
            and all(item.note == "" for day in self.saved for item in day.items)
        )

    def saved_ids(self) -> set[str]:
        return {item.place_id for day in self.saved or [] for item in day.items}

    def run(self, provider: ModelProvider) -> None:
        asyncio.run(pipeline.run(uuid4(), provider, self.sessions))
