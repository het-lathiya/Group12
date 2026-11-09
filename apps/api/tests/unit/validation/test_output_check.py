"""Step 8: io-1 limits, the place-ID check and the route of invalid output (§8.11; IMP-306)."""

import json
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from fixtures.ai import FORT, MARKET, SAMPLE_OUTPUT, THALI, sample_request
from fixtures.pipeline import Journal, recorded_gemini

from app.ai.errors import ProviderInvalidOutput
from app.ai.providers.mock import MockProvider
from app.generation import pipeline
from app.schemas.ai import GroundedItineraryOutput, ItineraryOutput
from app.validation import output_check
from app.validation.output_check import OutputCheckResult, apply_limits, check_output, summary

CONTRACT = Path(__file__).resolve().parents[5] / "contracts" / "ai" / "io-1.schema.json"
SHORTLIST = {FORT, MARKET, THALI}
INVENTED = "00000000-0000-4000-8000-000000009999"


def item(place_id: str, start: str = "09:00") -> dict[str, Any]:
    return {
        "place_id": place_id,
        "start_time": start,
        "duration_min": 60,
        "slot_type": "activity",
        "note": "",
    }


def plan(*days: tuple[int, list[str]]) -> ItineraryOutput:
    return ItineraryOutput.model_validate(
        {
            "days": [
                {"day_number": number, "theme": "", "items": [item(place) for place in places]}
                for number, places in days
            ],
            "summary": None,
            "assumptions": [],
        }
    )


def test_tc_138_an_invented_place_id_is_dropped_with_unknown_place() -> None:
    result = check_output(plan((1, [FORT, INVENTED])), SHORTLIST, 2)

    assert result.output.place_ids() == [FORT]
    assert not result.usable
    assert (result.invalid_ids, result.rejected_items) == (1, 1)
    [finding] = result.findings
    assert (finding.code, finding.severity, finding.item_ref) == (
        "UNKNOWN_PLACE",
        "error",
        "d1-i2",
    )
    assert INVENTED not in finding.message


def test_an_inactive_place_is_unknown_because_it_is_not_in_the_active_ids() -> None:
    result = check_output(plan((1, [FORT, THALI])), {FORT}, 1)

    assert [finding.code for finding in result.findings] == ["UNKNOWN_PLACE"]


def test_tc_137_items_on_a_day_outside_the_trip_are_rejected() -> None:
    result = check_output(plan((1, [FORT]), (3, [MARKET, THALI])), SHORTLIST, 2)

    assert [day.day_number for day in result.output.days] == [1]
    assert [(f.code, f.item_ref) for f in result.findings] == [
        ("OUTSIDE_TRIP_DATES", "d3-i1"),
        ("OUTSIDE_TRIP_DATES", "d3-i2"),
    ]
    assert (result.invalid_ids, result.rejected_items) == (0, 2)
    assert result.usable  # IMD-126: dropped, not a reason to refuse the answer


def test_output_check_imd_126_a_day_past_the_trip_is_dropped_not_a_schema_violation() -> None:
    answer = plan((1, [FORT]), (2, [MARKET]), (3, [THALI]))

    limited = apply_limits(answer, trip_days=2, max_items_per_day=5)
    result = check_output(limited, SHORTLIST, 2)

    assert limited == answer
    assert result.output.place_ids() == [FORT, MARKET]
    assert result.usable
    assert summary(result)["errors"] == 1
    assert summary(result)["rejected_items"] == 1


def test_output_check_an_answer_with_only_days_outside_the_trip_is_not_usable() -> None:
    answer = plan((3, [FORT]))

    result = check_output(apply_limits(answer, trip_days=2, max_items_per_day=5), SHORTLIST, 2)

    assert result.output.days == []
    assert not result.usable


def test_output_check_unknown_place_still_makes_the_answer_unusable() -> None:
    result = check_output(plan((1, [FORT]), (3, [MARKET]), (2, [INVENTED])), SHORTLIST, 2)

    assert [f.code for f in result.findings] == ["OUTSIDE_TRIP_DATES", "UNKNOWN_PLACE"]
    assert not result.usable


def test_the_second_occurrence_of_a_place_is_rejected_and_the_plan_stays_usable() -> None:
    result = check_output(plan((1, [FORT, THALI, FORT]), (2, [THALI])), SHORTLIST, 2)

    assert result.output.place_ids() == [FORT, THALI]
    assert [day.day_number for day in result.output.days] == [1]
    assert result.rejected_items == 2
    assert result.findings == []
    assert result.usable


def test_a_plan_with_nothing_left_is_not_usable() -> None:
    result = check_output(plan((1, [INVENTED])), SHORTLIST, 1)

    assert result.output.days == []
    assert not result.usable


def test_a_valid_answer_passes_unchanged() -> None:
    answer = ItineraryOutput.model_validate(SAMPLE_OUTPUT)

    result = check_output(apply_limits(answer, trip_days=2, max_items_per_day=5), SHORTLIST, 2)

    assert result.output == answer
    assert result.usable
    assert summary(result) == {
        "errors": 0,
        "warnings": 0,
        "infos": 0,
        "invalid_ids": 0,
        "rejected_items": 0,
        "unknown_source_ids": 0,
        "kind": None,
    }


@pytest.mark.parametrize(
    ("days", "trip_days", "max_items"),
    [
        (((1, [FORT]), (1, [MARKET])), 2, 5),
        (((1, [FORT, MARKET, THALI]),), 2, 2),
    ],
    ids=["a day twice", "over the pace maximum"],
)
def test_tc_023_trip_limits_are_a_schema_violation(
    days: tuple[tuple[int, list[str]], ...], trip_days: int, max_items: int
) -> None:
    with pytest.raises(ProviderInvalidOutput) as caught:
        apply_limits(plan(*days), trip_days=trip_days, max_items_per_day=max_items)

    assert caught.value.kind == "schema_violation"


def test_fewer_days_than_the_trip_is_allowed_when_the_places_run_out() -> None:
    answer = plan((1, [FORT]))

    assert apply_limits(answer, trip_days=3, max_items_per_day=5) == answer


@pytest.mark.parametrize(
    "change",
    [
        {"theme": "x" * 81},
        {"items": [{**item(FORT), "note": "x" * 201}]},
        {"items": [{**item(FORT), "start_time": "9:00"}]},
        {"items": [{**item(FORT), "duration_min": 14}]},
        {"items": [{**item(FORT), "duration_min": 481}]},
        {"items": [{**item(FORT), "price": "0.00"}]},
    ],
    ids=["theme", "note", "start_time", "short", "long", "extra field"],
)
def test_tc_023_field_limits_hold_at_the_model(change: dict[str, Any]) -> None:
    day = {"day_number": 1, "theme": "", "items": [item(FORT)], **change}

    with pytest.raises(ValueError, match="validation error"):
        ItineraryOutput.model_validate({"days": [day], "assumptions": []})


def test_the_summary_is_limited_to_500_characters() -> None:
    with pytest.raises(ValueError, match="validation error"):
        ItineraryOutput.model_validate({**SAMPLE_OUTPUT, "summary": "x" * 501})


def test_the_trip_limits_leave_the_exported_schema_unchanged() -> None:
    exported = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert exported["properties"] == ItineraryOutput.model_json_schema()["properties"]


@pytest.mark.parametrize(
    ("recording", "kind"),
    [("malformed", "malformed_json"), ("schema_violation", "schema_violation")],
)
def test_tc_136_tc_022_tc_023_bad_answers_are_classified_and_take_the_one_route(
    monkeypatch: pytest.MonkeyPatch, recording: str, kind: str
) -> None:
    journal = Journal(monkeypatch, sample_request())
    routed: list[str | None] = []
    real = pipeline.end_invalid_output

    async def spy(job: Any, request: Any, summary: dict[str, Any], **kw: Any) -> None:
        routed.append(summary["kind"])
        await real(job, request, summary, **kw)

    monkeypatch.setattr(pipeline, "end_invalid_output", spy)

    journal.run(recorded_gemini(recording))

    assert routed == [kind]
    assert journal.completed["validation_summary"]["kind"] == kind
    assert journal.fell_back("invalid_output")  # IMP-402: the answer itself is never saved


def test_an_item_past_the_pace_maximum_is_refused_before_saving(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = sample_request()
    tight = request.model_copy(
        update={"limits": request.limits.model_copy(update={"max_items_per_day": 1})}
    )
    journal = Journal(monkeypatch, tight)

    journal.run(recorded_gemini())

    assert journal.completed["validation_summary"]["kind"] == "schema_violation"
    assert journal.fell_back("invalid_output")


def test_a_place_gone_inactive_during_the_call_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    journal = Journal(monkeypatch, sample_request())
    journal.inactive = {UUID(THALI)}

    journal.run(MockProvider("ok", app_env="test"))

    assert journal.fell_back("invalid_output")
    assert journal.completed["validation_summary"]["invalid_ids"] == 1
    assert THALI not in journal.saved_ids()


def test_the_counts_reach_the_completed_record_when_a_duplicate_is_dropped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    journal = Journal(monkeypatch, sample_request())
    repeated = plan((1, [FORT, THALI, FORT]))
    monkeypatch.setattr(output_check, "apply_limits", lambda output, **limits: repeated)

    journal.run(MockProvider("ok", app_env="test"))

    assert journal.saved is not None
    assert [item.place_id for day in journal.saved for item in day.items] == [FORT, THALI]
    assert journal.completed["validation_summary"]["rejected_items"] == 1


# ---------- Citations (A1 §6.10; FR-138 AC2, TC-455) ----------

P1, P2, P3, P4 = (f"00000000-0000-4000-8000-00000000c00{n}" for n in range(1, 5))
PASSAGES = {P1, P2, P3, P4}


def cited(*source_ids: list[str]) -> GroundedItineraryOutput:
    """One day, one item per citation list, on the three shortlisted places."""
    places = [FORT, MARKET, THALI]
    items = [
        {**item(place), "source_ids": ids} for place, ids in zip(places, source_ids, strict=False)
    ]
    return GroundedItineraryOutput.model_validate(
        {"days": [{"day_number": 1, "theme": "", "items": items}], "assumptions": []}
    )


def citations(result: OutputCheckResult) -> list[list[str]]:
    assert isinstance(result.output, GroundedItineraryOutput)
    return [item.source_ids for day in result.output.days for item in day.items]


def test_output_check_tc_455_a_citation_outside_the_request_is_dropped_and_counted() -> None:
    result = check_output(cited([P1, "not-a-passage", INVENTED]), SHORTLIST, 2, PASSAGES)

    assert citations(result) == [[P1]]
    assert summary(result)["unknown_source_ids"] == 2


def test_output_check_tc_455_a_repeated_citation_is_dropped_and_counted() -> None:
    result = check_output(cited([P1, P1, P2]), SHORTLIST, 2, PASSAGES)

    assert citations(result) == [[P1, P2]]
    assert result.unknown_source_ids == 1


def test_output_check_tc_455_an_item_keeps_at_most_three_citations() -> None:
    result = check_output(cited([P1, P2, P3, P4]), SHORTLIST, 2, PASSAGES)

    assert citations(result) == [[P1, P2, P3]]
    assert result.unknown_source_ids == 1


def test_output_check_tc_455_an_item_is_never_dropped_for_a_citation() -> None:
    answer = cited(["bad-1", "bad-2"], [], [P1])

    result = check_output(answer, SHORTLIST, 2, PASSAGES)

    assert result.output.place_ids() == [FORT, MARKET, THALI]
    assert citations(result) == [[], [], [P1]]
    assert result.usable
    assert (result.findings, result.rejected_items) == ([], 0)
    assert summary(result)["unknown_source_ids"] == 2


def test_output_check_tc_455_a_request_without_passages_keeps_no_citation() -> None:
    result = check_output(cited([P1, P2]), SHORTLIST, 2)

    assert citations(result) == [[]]
    assert result.unknown_source_ids == 2


def test_output_check_limits_keep_the_io_2_answer_and_its_citations() -> None:
    answer = cited([P1, P2, P3, P4])

    checked = apply_limits(answer, trip_days=2, max_items_per_day=5)

    assert isinstance(checked, GroundedItineraryOutput)
    assert checked == answer


def test_output_check_a_refused_answer_counts_no_citation() -> None:
    assert summary(kind="malformed_json")["unknown_source_ids"] == 0


def test_output_check_imd_126_the_pipeline_saves_the_answer_without_the_outside_day(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    answer = plan((1, [FORT]), (3, [MARKET]))  # the sample trip has 2 days

    class Answers(MockProvider):
        async def generate_itinerary(self, request: Any) -> Any:
            result = await super().generate_itinerary(request)
            return result.model_copy(update={"output": answer})

    journal = Journal(monkeypatch, sample_request())

    journal.run(Answers("ok", app_env="test"))

    assert journal.completed["outcome"] == "model"
    assert journal.saved_ids() == {FORT}
    recorded = journal.completed["validation_summary"]
    assert (recorded["errors"], recorded["rejected_items"]) == (1, 1)
