"""Versioned prompts and unchanged io-1/io-2 with Groq's adapter-only schema conversion."""

import asyncio
import json
from typing import Any

import pytest
from fixtures.ai import sample_request
from fixtures.groq import Calls

from app.ai.prompts import registry
from app.ai.providers.groq import wire_schema
from app.schemas.ai import GroundedGenerationRequest, GroundedItineraryOutput, ItineraryOutput


@pytest.mark.parametrize("version", ["v1", "v2", "v3", "v4"])
def test_the_same_versioned_prompt_and_output_contract_are_used(version: str) -> None:
    request = sample_request().model_copy(update={"prompt_version": version})
    if version != "v1":
        request = GroundedGenerationRequest.model_validate(
            {
                **request.model_dump(exclude={"input_schema_version"}),
                "context_passages": [],
                "retrieval": {"mode": "lexical_fallback", "embedding_model_id": None},
            }
        )
    calls = Calls()
    result = asyncio.run(calls.provider().generate_itinerary(request))
    system, user = registry.load("itinerary_generate", version).prompt(request)
    body = json.loads(calls.requests[0].content)
    assert body["messages"] == [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    expected = ItineraryOutput if version == "v1" else GroundedItineraryOutput
    assert isinstance(result.output, expected)
    assert result.output.unknown_place_ids(request) == []


@pytest.mark.parametrize("model", [ItineraryOutput, GroundedItineraryOutput])
def test_strict_conversion_preserves_the_original_schema_and_its_limits(
    model: type[ItineraryOutput],
) -> None:
    original = model.model_json_schema()
    wire = wire_schema(model)
    assert model.model_json_schema() == original
    assert wire["required"] == list(wire["properties"])
    assert "default" not in wire["properties"]["summary"]
    assert {"type": "null"} in wire["properties"]["summary"]["anyOf"]

    def check(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node["additionalProperties"] is False
                assert node["required"] == list(node["properties"])
            for value in node.values():
                check(value)
        elif isinstance(node, list):
            for value in node:
                check(value)

    check(wire)
    item = next(value for name, value in wire["$defs"].items() if name.endswith("ItemOutput"))
    assert item["properties"]["duration_min"]["minimum"] == 15
    assert item["properties"]["duration_min"]["maximum"] == 480
    assert item["properties"]["note"]["maxLength"] == 200
    assert item["properties"]["start_time"]["pattern"]


def test_json_object_mode_for_a_model_without_json_schema_support() -> None:
    calls = Calls()
    asyncio.run(
        calls.provider(groq_model_id="llama-3.3-70b-versatile").generate_itinerary(sample_request())
    )
    assert json.loads(calls.requests[0].content)["response_format"] == {"type": "json_object"}


def test_best_effort_mode_is_selected_for_the_documented_non_strict_model() -> None:
    calls = Calls()
    asyncio.run(
        calls.provider(groq_model_id="openai/gpt-oss-safeguard-20b").generate_itinerary(
            sample_request()
        )
    )
    format_ = json.loads(calls.requests[0].content)["response_format"]
    assert format_["type"] == "json_schema"
    assert format_["json_schema"]["strict"] is False
