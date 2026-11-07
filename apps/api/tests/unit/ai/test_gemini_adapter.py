"""Gemini adapter by replay (§8.4; FR-041: TC-013 to TC-015, TC-018 to TC-024, TC-030 to TC-032,
TC-159 to TC-161; IMP-301).

Each fixture in provider_recordings/gemini/ goes through the real SDK over a fake HTTP transport;
nothing reaches the network. The fixtures are format fixtures until a live recording replaces them.
"""

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any

import httpx
import pytest
from fixtures.ai import sample_request, sample_request_data

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
from app.ai.providers import gemini as adapter
from app.ai.providers.gemini import GeminiProvider
from app.core.config import Settings, load_settings
from app.generation import records
from app.schemas.ai import (
    GenerationRequest,
    GroundedGenerationRequest,
    GroundedItineraryOutput,
    ItineraryOutput,
)

RECORDINGS = Path(__file__).resolve().parents[2] / "fixtures" / "provider_recordings" / "gemini"
CONTRACTS = Path(__file__).resolve().parents[5] / "contracts" / "ai"
IO_1 = CONTRACTS / "io-1.schema.json"
KEY = "unit-test-gemini-key-not-real"
MODEL = "gemini-3.5-flash-lite"
VENDOR_TEXT = "Sample vendor text"


def recording(name: str) -> httpx.Response:
    data = json.loads((RECORDINGS / f"{name}.json").read_text(encoding="utf-8"))
    return httpx.Response(data["http_status"], json=data["body"], headers=data["headers"])


class Replay:
    """A fake transport that answers every request and keeps what it was sent."""

    def __init__(self, answer: httpx.Response | Exception) -> None:
        self.answer = answer
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer

    @property
    def body(self) -> dict[str, Any]:
        body: dict[str, Any] = json.loads(self.requests[-1].content)
        return body


def provider(replay: Replay, **overrides: Any) -> GeminiProvider:
    values: dict[str, Any] = {"gemini_api_key": KEY, "gemini_model_id": MODEL}
    client = httpx.AsyncClient(transport=httpx.MockTransport(replay))
    return GeminiProvider(Settings(**(values | overrides)), http_client=client)


def generate(gemini: GeminiProvider, request: GenerationRequest | None = None) -> Any:
    return asyncio.run(gemini.generate_itinerary(request or sample_request()))


def failure(name: str) -> ProviderError:
    with pytest.raises(ProviderError) as raised:
        generate(provider(Replay(recording(name))))
    assert VENDOR_TEXT not in str(raised.value)
    assert raised.value.__cause__ is None
    return raised.value


def test_gemini_tc_013_the_key_comes_from_the_environment_and_never_surfaces(
    clean_settings_env: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    clean_settings_env.setenv("DATABASE_URL", "postgresql://u:p@localhost/x")
    clean_settings_env.setenv("GEMINI_API_KEY", KEY)
    clean_settings_env.setenv("GEMINI_MODEL_ID", MODEL)
    replay = Replay(recording("unavailable_503"))
    client = httpx.AsyncClient(transport=httpx.MockTransport(replay))
    gemini = GeminiProvider(load_settings(), http_client=client)
    with caplog.at_level(logging.DEBUG), pytest.raises(ProviderUnavailable) as raised:
        generate(gemini)
    assert replay.requests[-1].headers["x-goog-api-key"] == KEY
    health = asyncio.run(gemini.health_check())
    seen = [
        str(raised.value),
        caplog.text,
        str(gemini.generation_settings),
        gemini.get_model_metadata().model_dump_json(),
        health.model_dump_json(),
    ]
    assert not [text for text in seen if KEY in text]


def test_gemini_tc_014_the_request_carries_the_structured_output_configuration() -> None:
    replay = Replay(recording("ok"))
    generate(provider(replay))
    body = replay.body
    assert body["response_format"]["type"] == "text"
    assert body["response_format"]["mime_type"] == "application/json"
    assert body["response_format"]["schema"] == adapter.wire_schema()
    system_text, user_text = registry.render("itinerary_generate", "v1", sample_request())
    assert (body["system_instruction"], body["input"]) == (system_text, user_text)


def test_gemini_the_wire_schema_is_io_1_without_schema_id_and_pattern() -> None:
    contract = json.loads(IO_1.read_text(encoding="utf-8"))
    wire = adapter.wire_schema()
    text = json.dumps(wire)
    assert '"pattern"' not in text
    assert '"$schema"' not in text
    assert '"$id"' not in text
    assert "HH:MM" in text
    assert list(wire["properties"]) == ["days", "summary", "assumptions"]
    assert wire["properties"] == adapter._without_keys(contract)["properties"]


def test_gemini_tc_015_a_valid_answer_parses_to_io_1() -> None:
    result = generate(provider(Replay(recording("ok"))))
    assert [item.start_time for item in result.output.days[0].items] == ["09:30", "12:00"]
    assert result.output.unknown_place_ids(sample_request()) == []


def test_gemini_tc_018_no_answer_within_the_timeout_is_a_provider_timeout() -> None:
    async def never(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(5)
        return recording("ok")

    client = httpx.AsyncClient(transport=httpx.MockTransport(never))
    settings = Settings(gemini_api_key=KEY, gemini_model_id=MODEL, gemini_timeout_s=0.01)
    with pytest.raises(ProviderTimeout):
        generate(GeminiProvider(settings, http_client=client))


def test_gemini_tc_018_a_transport_timeout_is_a_provider_timeout() -> None:
    with pytest.raises(ProviderTimeout):
        generate(provider(Replay(httpx.ReadTimeout("slow"))))


def test_gemini_the_timeout_reaches_the_http_options_in_milliseconds() -> None:
    replay = Replay(recording("ok"))
    gemini = provider(replay, gemini_timeout_s=12)
    generate(gemini)
    assert replay.requests[-1].extensions["timeout"]["read"] == 12
    assert gemini.generation_settings["timeout_s"] == 12


@pytest.mark.parametrize("name", ["blocked", "blocked_status"])
def test_gemini_tc_019_a_safety_block_is_invalid_output_blocked(name: str) -> None:
    error = failure(name)
    assert isinstance(error, ProviderInvalidOutput)
    assert error.kind == "blocked"


@pytest.mark.parametrize(
    ("name", "kind"),
    [
        ("empty", "empty"),  # TC-020
        ("truncated", "truncated"),  # TC-021
        ("malformed", "malformed_json"),  # TC-022
        ("schema_violation", "schema_violation"),  # TC-023
    ],
)
def test_gemini_tc_020_to_023_each_invalid_output_kind(name: str, kind: str) -> None:
    error = failure(name)
    assert isinstance(error, ProviderInvalidOutput)
    assert error.kind == kind
    assert error.failure_reason == "invalid_output"


def test_gemini_an_answer_body_that_is_not_an_interaction_is_malformed() -> None:
    with pytest.raises(ProviderInvalidOutput) as raised:
        generate(provider(Replay(httpx.Response(200, text="<html>not json</html>"))))
    assert raised.value.kind == "malformed_json"


def test_gemini_a_failed_interaction_without_a_block_is_unavailable() -> None:
    answer = httpx.Response(200, json={"id": "i", "status": "failed"})
    with pytest.raises(ProviderUnavailable):
        generate(provider(Replay(answer)))


def test_gemini_tc_024_usage_is_mapped_from_the_response() -> None:
    usage = generate(provider(Replay(recording("ok")))).usage
    assert usage.model_dump() == {
        "input_tokens": 812,
        "output_tokens": 146,
        "thinking_tokens": 37,
        "total_tokens": 995,
    }


def test_gemini_tc_030_nothing_is_stored_at_the_provider() -> None:
    replay = Replay(recording("ok"))
    generate(provider(replay))
    assert replay.body["store"] is False


def test_gemini_tc_031_the_model_id_is_recorded_exactly_as_configured() -> None:
    replay = Replay(recording("ok"))
    gemini = provider(replay, gemini_model_id="Gemini-Exact_ID-1")
    generate(gemini)
    assert replay.body["model"] == "Gemini-Exact_ID-1"
    assert gemini.get_model_metadata().model_id == "Gemini-Exact_ID-1"


def test_gemini_tc_032_no_sampling_parameter_or_thinking_budget_is_sent() -> None:
    replay = Replay(recording("ok"))
    generate(provider(replay, ai_temperature=0.9, ai_max_output_tokens=2048))
    assert replay.body["generation_config"] == {
        "thinking_level": "minimal",
        "max_output_tokens": 2048,
    }


def test_gemini_no_output_limit_is_sent_when_none_is_configured() -> None:
    replay = Replay(recording("ok"))
    gemini = provider(replay)
    generate(gemini)
    assert replay.body["generation_config"] == {"thinking_level": "minimal"}
    assert "max_output_tokens" not in gemini.generation_settings


@pytest.mark.parametrize(
    ("model", "level"),
    [
        ("gemini-3.5-flash-lite", "minimal"),
        ("gemini-3.6-flash", "minimal"),
        ("gemini-3.8-flash", "low"),
        ("some-other-model", "low"),
    ],
)
def test_gemini_the_lowest_thinking_level_of_the_model(model: str, level: str) -> None:
    assert adapter.thinking_level(model) == level


def test_gemini_tc_159_a_valid_call_returns_a_candidate_and_usage() -> None:
    result = generate(provider(Replay(recording("ok"))))
    assert result.output.days
    assert result.usage.total_tokens == 995
    assert result.finish_reason == "completed"
    assert result.provider_request_id == "sample-interaction-id"
    assert result.latency_ms >= 0


def test_gemini_tc_160_a_429_is_a_rate_limit_with_retry_after() -> None:
    error = failure("rate_limited_429")
    assert isinstance(error, ProviderRateLimited)
    assert error.retry_after_s == 7


def test_gemini_a_429_of_daily_quota_is_quota_exhausted() -> None:
    assert isinstance(failure("quota_429"), ProviderQuotaExhausted)


def test_gemini_tc_161_a_blocked_or_empty_answer_names_its_reason() -> None:
    assert "blocked" in str(failure("blocked"))
    assert "empty" in str(failure("empty"))


@pytest.mark.parametrize("name", ["unavailable_503", "rate_limited_429", "quota_429"])
def test_gemini_the_sdk_makes_one_attempt_only(name: str) -> None:
    replay = Replay(recording(name))
    with pytest.raises(ProviderError):
        generate(provider(replay))
    assert len(replay.requests) == 1


def test_gemini_a_400_code_is_read_before_the_status() -> None:
    bad = httpx.Response(400, json={"error": {"code": "invalid_request", "message": VENDOR_TEXT}})
    with pytest.raises(ProviderBadRequest):
        generate(provider(Replay(bad)))
    with pytest.raises(ProviderInvalidOutput):
        generate(provider(Replay(recording("blocked"))))


def test_gemini_a_prompt_that_cannot_render_is_a_bad_request() -> None:
    data = {**sample_request_data(), "prompt_version": "v99"}
    replay = Replay(recording("ok"))
    with pytest.raises(ProviderBadRequest):
        generate(provider(replay), GenerationRequest.model_validate(data))
    assert replay.requests == []


def test_gemini_generation_settings_pass_the_record_allow_list() -> None:
    sent = provider(Replay(recording("ok")), ai_max_output_tokens=2048).generation_settings
    assert records.clean_generation_settings(sent) == sent
    assert sent == {
        "api_style": "interactions",
        "thinking_level": "minimal",
        "structured_output": True,
        "timeout_s": 35,
        "max_output_tokens": 2048,
    }


def test_gemini_health_needs_no_generation_call() -> None:
    replay = Replay(recording("ok"))
    assert asyncio.run(provider(replay).health_check()).status == "ok"
    assert asyncio.run(provider(replay, gemini_api_key="").health_check()).status == "down"
    assert asyncio.run(provider(replay, gemini_model_id="").health_check()).status == "down"
    assert replay.requests == []


def test_gemini_health_follows_the_last_call() -> None:
    replay = Replay(recording("unavailable_503"))
    gemini = provider(replay)
    with pytest.raises(ProviderUnavailable):
        generate(gemini)
    assert asyncio.run(gemini.health_check()).status == "degraded"
    replay.answer = recording("ok")
    generate(gemini)
    assert asyncio.run(gemini.health_check()).status == "ok"
    replay.answer = httpx.Response(403, json={"error": {"code": "permission_denied"}})
    with pytest.raises(ProviderAuthError):
        generate(gemini)
    assert asyncio.run(gemini.health_check()).status == "down"


# ---------- Template v2: gr-2 in, io-2 out (A1 §6.8) ----------


def grounded_request() -> GroundedGenerationRequest:
    return GroundedGenerationRequest.model_validate(
        {
            **sample_request().model_dump(exclude={"input_schema_version"}),
            "prompt_version": "v2",
            "context_passages": [],
            "retrieval": {"mode": "lexical_fallback", "embedding_model_id": None},
        }
    )


def test_template_v2_sends_the_io_2_wire_schema_and_parses_io_2() -> None:
    replay = Replay(recording("ok"))

    result = generate(provider(replay), grounded_request())

    assert isinstance(result.output, GroundedItineraryOutput)
    assert "source_ids" in json.dumps(replay.body)


def test_template_v1_keeps_the_io_1_wire_schema() -> None:
    replay = Replay(recording("ok"))

    result = generate(provider(replay))

    assert not isinstance(result.output, GroundedItineraryOutput)
    assert "source_ids" not in json.dumps(replay.body)


# ---------- Wire schema without serving limits (proposed D13) ----------

OUTPUTS = [("io-1", ItineraryOutput), ("io-2", GroundedItineraryOutput)]
SERVING_LIMITS = {
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "minItems",
    "maxItems",
    "minLength",
    "maxLength",
    "format",
    "multipleOf",
}


def schema_keywords(node: Any, names: bool = False) -> set[str]:
    """Every keyword at any depth; the keys under properties and $defs are names, not keywords."""
    if isinstance(node, list):
        return set().union(*(schema_keywords(item) for item in node))
    if not isinstance(node, dict):
        return set()
    found = set() if names else set(node)
    for key, value in node.items():
        found |= schema_keywords(value, not names and key in adapter.NAME_MAPS)
    return found


def schema_objects(schema: dict[str, Any]) -> dict[str, tuple[list[str], list[str]]]:
    """The property names and required fields of the root and of each definition."""
    nodes = {"": schema, **schema["$defs"]}
    return {k: (list(n["properties"]), n["required"]) for k, n in nodes.items()}


@pytest.mark.parametrize(("name", "model"), OUTPUTS)
def test_wire_schema_has_no_serving_limit_at_any_depth(
    name: str, model: type[ItineraryOutput]
) -> None:
    contract = json.loads((CONTRACTS / f"{name}.schema.json").read_text(encoding="utf-8"))
    assert schema_keywords(contract) & SERVING_LIMITS  # the walk does find them in the contract
    assert not schema_keywords(adapter.wire_schema(model)) & (
        SERVING_LIMITS | {"$schema", "$id", "pattern"}
    )


@pytest.mark.parametrize(("name", "model"), OUTPUTS)
def test_wire_schema_keeps_every_property_required_field_and_enum(
    name: str, model: type[ItineraryOutput]
) -> None:
    contract = json.loads((CONTRACTS / f"{name}.schema.json").read_text(encoding="utf-8"))
    wire = adapter.wire_schema(model)
    assert schema_objects(wire) == schema_objects(contract)
    assert schema_keywords(wire) >= {
        "type",
        "properties",
        "required",
        "additionalProperties",
        "enum",
        "items",
        "$defs",
        "$ref",
        "description",
    }
    assert "HH:MM" in json.dumps(wire)


def test_wire_schema_keeps_a_field_named_like_a_dropped_keyword() -> None:
    node = {"properties": {"format": {"type": "string", "maxLength": 3}}, "required": ["format"]}
    assert adapter._without_keys(node) == {
        "properties": {"format": {"type": "string", "description": "At most 3 characters."}},
        "required": ["format"],
    }


def test_wire_schema_is_what_the_request_carries() -> None:
    replay = Replay(recording("ok"))
    generate(provider(replay))
    assert replay.body["response_format"]["schema"] == adapter.wire_schema(ItineraryOutput)

    generate(provider(replay), grounded_request())
    assert replay.body["response_format"]["schema"] == adapter.wire_schema(GroundedItineraryOutput)


def limited_nodes(contract: Any, wire: Any, names: bool = False) -> Any:
    """Each contract node holding a limit, walked in step with its wire node."""
    if isinstance(contract, list):
        for pair in zip(contract, wire, strict=True):
            yield from limited_nodes(*pair)
    elif isinstance(contract, dict):
        if not names and set(contract) & (SERVING_LIMITS | {"pattern"}):
            yield contract, wire
        for key, value in contract.items():
            if key in wire and (names or key not in SERVING_LIMITS):
                yield from limited_nodes(value, wire[key], not names and key in adapter.NAME_MAPS)


@pytest.mark.parametrize(("name", "model"), OUTPUTS)
def test_wire_schema_every_node_that_lost_a_limit_states_it(
    name: str, model: type[ItineraryOutput]
) -> None:
    contract = json.loads((CONTRACTS / f"{name}.schema.json").read_text(encoding="utf-8"))
    nodes = list(limited_nodes(contract, adapter.wire_schema(model)))
    assert len(nodes) == (11 if name == "io-2" else 10)
    for before, after in nodes:
        for keyword in set(before) & SERVING_LIMITS:
            assert re.search(rf"\b{before[keyword]}\b", after["description"]), (keyword, after)
        if "pattern" in before:
            assert "HH:MM (24-hour)" in after["description"]
        if "description" in before:
            assert after["description"].startswith(before["description"])


@pytest.mark.parametrize(("name", "model"), OUTPUTS)
def test_wire_schema_states_each_limit_in_plain_words(
    name: str, model: type[ItineraryOutput]
) -> None:
    wire = adapter.wire_schema(model)
    defs = wire["$defs"].values()
    item = next(d for d in defs if "note" in d["properties"])["properties"]
    day = next(d for d in defs if "theme" in d["properties"])["properties"]
    described = {
        "duration": item["duration_min"],
        "note": item["note"],
        "theme": day["theme"],
        "summary": wire["properties"]["summary"]["anyOf"][0],
        "assumptions": wire["properties"]["assumptions"],
        "days": wire["properties"]["days"],
        "items": day["items"],
        "day_number": day["day_number"],
    }
    assert {key: node["description"] for key, node in described.items()} == {
        "duration": "Integer from 15 to 480.",
        "note": "At most 200 characters.",
        "theme": "At most 80 characters.",
        "summary": "At most 500 characters.",
        "assumptions": "At most 20 items.",
        "days": "From 1 to 14 items.",
        "items": "From 1 to 12 items.",
        "day_number": "Integer from 1 to 14.",
    }
    assert item["place_id"]["description"] == (
        "A place_id from the request's shortlist. At least 1 character."
    )
    assert item["start_time"]["description"] == (
        "24-hour time HH:MM in the destination time zone. Format: HH:MM (24-hour)."
    )
    if name == "io-2":
        assert item["source_ids"]["description"] == (
            "passage_id values of the request this note relies on. At most 3 items."
        )


@pytest.mark.parametrize(
    ("limits", "description"),
    [
        ({"type": "number", "minimum": 0, "maximum": 1.5}, "Number from 0 to 1.5."),
        ({"minimum": 0}, "At least 0."),
        ({"maximum": 9}, "At most 9."),
        ({"exclusiveMinimum": 0, "exclusiveMaximum": 5}, "Greater than 0. Less than 5."),
        ({"multipleOf": 5}, "Multiple of 5."),
        ({"minLength": 2, "maxLength": 4}, "From 2 to 4 characters."),
        ({"minLength": 2}, "At least 2 characters."),
        ({"maxLength": 1}, "At most 1 character."),
        ({"minItems": 1}, "At least 1 item."),
        ({"format": "date"}, "Format: date."),
        ({"pattern": "^[A-Z]{3}$"}, "Matches the pattern ^[A-Z]{3}$."),
        ({"pattern": adapter.HHMM_PATTERN}, "Format: HH:MM (24-hour)."),
        (
            {"maxLength": 3, "format": "date", "pattern": "^x$", "minimum": 1},
            "At least 1. At most 3 characters. Format: date. Matches the pattern ^x$.",
        ),
        ({"description": "Kept.", "maxItems": 2}, "Kept. At most 2 items."),
        ({"description": "Kept", "maxItems": 2}, "Kept. At most 2 items."),
    ],
)
def test_wire_schema_sentence_for_each_removed_keyword(
    limits: dict[str, Any], description: str
) -> None:
    assert adapter._without_keys(limits)["description"] == description


def test_wire_schema_a_node_without_limits_gets_no_description() -> None:
    assert adapter._without_keys({"type": "string"}) == {"type": "string"}


def answer_with(change: Any) -> httpx.Response:
    data = json.loads((RECORDINGS / "ok.json").read_text(encoding="utf-8"))
    content = data["body"]["steps"][0]["content"][0]
    answer = json.loads(content["text"])
    change(answer)
    content["text"] = json.dumps(answer)
    return httpx.Response(200, json=data["body"])


@pytest.mark.parametrize(
    "change",
    [
        pytest.param(lambda a: a["days"][0]["items"][0].update(duration_min=600), id="duration"),
        pytest.param(lambda a: a.update(assumptions=["An assumption."] * 21), id="assumptions"),
        pytest.param(lambda a: a["days"][0]["items"][0].update(note="n" * 300), id="note"),
        pytest.param(lambda a: a["days"][0].update(theme="t" * 81), id="theme"),
        pytest.param(lambda a: a.update(summary="s" * 501), id="summary"),
        pytest.param(lambda a: a["days"][0]["items"][0].update(start_time="25:00"), id="time"),
        pytest.param(lambda a: a["days"][0].update(day_number=0), id="day_number"),
        pytest.param(lambda a: a["days"][0].update(items=[]), id="no_items"),
        pytest.param(lambda a: a["days"][0].update(items=a["days"][0]["items"] * 7), id="items"),
        pytest.param(lambda a: a.update(days=a["days"] * 15), id="days"),
        pytest.param(lambda a: a.update(days=[]), id="no_days"),
    ],
)
@pytest.mark.parametrize("grounded", [False, True], ids=["io-1", "io-2"])
def test_wire_schema_a_removed_limit_is_still_rejected_after_parsing(
    change: Any, grounded: bool
) -> None:
    gemini = provider(Replay(answer_with(change)))
    with pytest.raises(ProviderInvalidOutput) as raised:
        generate(gemini, grounded_request() if grounded else None)
    assert raised.value.kind == "schema_violation"
