"""The pipeline's order of work, on the recorded Gemini answer (§8.2; IMP-305: TC-133, FR-031).

The repository, the request builder and the save are stand-ins, so this needs no database;
tests/api/test_generations.py runs the same steps against a real one.
"""

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
from fixtures.ai import sample_request

from app.ai.errors import ProviderBadRequest
from app.ai.providers.base import ModelProvider
from app.ai.providers.gemini import GeminiProvider
from app.ai.providers.mock import MockProvider
from app.core.config import Settings
from app.generation import pipeline
from app.schemas.ai import GenerationRequest, ItineraryOutput

RECORDINGS = Path(__file__).resolve().parents[2] / "fixtures" / "provider_recordings" / "gemini"
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

        repository = pipeline.repository
        monkeypatch.setattr(repository, "mark_running", mark_running)
        monkeypatch.setattr(repository, "record_settings", record_settings)
        monkeypatch.setattr(repository, "mark_validating", mark_validating)
        monkeypatch.setattr(repository, "complete", complete)
        monkeypatch.setattr(repository, "fail", fail)
        monkeypatch.setattr(pipeline.request_builder, "build", build)
        monkeypatch.setattr(pipeline.itinerary_service, "save_generated_plan", save)

    @asynccontextmanager
    async def sessions(self) -> AsyncIterator[Any]:
        self.transactions += 1
        self.open += 1
        yield object()
        self.open -= 1

    def run(self, provider: ModelProvider) -> None:
        asyncio.run(pipeline.run(uuid4(), provider, self.sessions))


class Spy(MockProvider):
    def __init__(self, journal: Journal) -> None:
        super().__init__("ok", app_env="test")
        self.journal = journal

    async def generate_itinerary(self, request: GenerationRequest) -> Any:
        assert self.journal.open == 0  # no transaction stays open across the call (§5.8)
        self.journal.steps.append("provider")
        return await super().generate_itinerary(request)


def test_tc_133_the_recorded_gemini_answer_goes_through_every_step(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    journal = Journal(monkeypatch, sample_request())

    journal.run(recorded_gemini())

    assert journal.steps == ["running", "build", "settings", "validating", "save", "complete"]
    assert journal.saved is not None
    assert journal.saved == ItineraryOutput.model_validate(journal.saved.model_dump())
    assert journal.completed["outcome"] == "model"
    assert journal.completed["usage"].input_tokens == 812
    assert journal.completed["adapter_version"] == "gemini-interactions-1"
    assert journal.settings["api_style"] == "interactions"
    assert journal.settings["truncated_count"] == 0


def test_pipeline_records_the_settings_before_the_provider_call_in_a_closed_transaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    journal = Journal(monkeypatch, sample_request())

    journal.run(Spy(journal))

    assert journal.steps.index("settings") < journal.steps.index("provider")
    assert journal.settings == {"truncated_count": 0}


def test_pipeline_records_how_many_places_the_input_limit_removed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = sample_request()
    journal = Journal(monkeypatch, request)
    trimmed = request.model_copy(update={"shortlist": request.shortlist[:2]})
    seen: list[int | None] = []

    def limit(given: GenerationRequest, max_tokens: int | None) -> tuple[GenerationRequest, int]:
        seen.append(max_tokens)
        return trimmed, 1

    monkeypatch.setattr(pipeline.limits, "enforce_input_limit", limit)
    monkeypatch.setattr(
        pipeline, "get_settings", lambda: type("S", (), {"ai_max_input_tokens": 500})
    )

    journal.run(MockProvider("ok", app_env="test"))

    assert seen == [500]
    assert journal.settings["truncated_count"] == 1
    assert journal.saved is not None
    assert set(journal.saved.place_ids()) <= trimmed.shortlist_ids()


def test_pipeline_ends_with_config_error_when_the_prompt_cannot_fit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    journal = Journal(monkeypatch, sample_request())

    def too_big(given: GenerationRequest, max_tokens: int | None) -> Any:
        raise ProviderBadRequest("the prompt does not fit AI_MAX_INPUT_TOKENS")

    monkeypatch.setattr(pipeline.limits, "enforce_input_limit", too_big)

    journal.run(Spy(journal))

    assert journal.failed == "config_error"
    assert "provider" not in journal.steps
    assert "save" not in journal.steps


def test_pipeline_rejects_an_id_outside_the_shortlist_before_saving(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    journal = Journal(monkeypatch, sample_request())

    journal.run(MockProvider("unknown_place", app_env="test"))

    assert journal.failed == "invalid_output"
    assert "save" not in journal.steps


def test_pipeline_saves_only_what_the_recalculation_hook_returns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    journal = Journal(monkeypatch, sample_request())
    replaced = ItineraryOutput.model_validate(
        {
            "days": [
                {
                    "day_number": 1,
                    "theme": "From the hook",
                    "items": [
                        {
                            "place_id": str(sample_request().shortlist[0].place_id),
                            "start_time": "10:00",
                            "duration_min": 60,
                            "slot_type": "activity",
                            "note": "",
                        }
                    ],
                }
            ],
            "summary": None,
            "assumptions": [],
        }
    )
    monkeypatch.setattr(pipeline, "recalculate", lambda output: replaced)

    journal.run(MockProvider("ok", app_env="test"))

    assert journal.saved == replaced
