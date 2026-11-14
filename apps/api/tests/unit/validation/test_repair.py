"""Bounded repair (§8.13, FR-057; IMP-502: TC-190, TC-313, and TC-011, TC-191, TC-192 without a
database). The pure deterministic repair first, then step 10 of the pipeline on the stand-ins of
``fixtures.pipeline``; tests/api/test_generations.py runs the same routes against PostgreSQL.
"""

from typing import Any

import pytest
from fixtures.ai import FORT, MARKET, THALI, sample_request
from fixtures.pipeline import Journal

from app.ai.errors import ProviderQuotaExhausted
from app.ai.prompts import registry
from app.ai.providers.mock import MockProvider
from app.core.config import MockScenario
from app.generation import pipeline
from app.schemas.ai import (
    GenerationRequest,
    GroundedItineraryOutput,
    ItineraryOutput,
    LockedItem,
    PlanFinding,
    RepairContext,
    UsageMetadata,
)
from app.validation import repair
from app.validation.repair import RepairScope

EXTRA = "00000000-0000-4000-8000-000000000009"  # not in the shortlist


def scope(**changes: Any) -> RepairScope:
    values: dict[str, Any] = {
        "day_numbers": range(1, 3),
        "max_items_per_day": 5,
        "max_active_minutes_per_day": 480,
        "day_start": "09:00",
        "shortlist": sample_request().shortlist,  # FORT, MARKET, THALI in rank order
        "must_visit_ids": [],
        **changes,
    }
    return RepairScope(**values)


def answer(*days: tuple[int, list[tuple[str, str, int]]]) -> ItineraryOutput:
    return ItineraryOutput.model_validate(
        {
            "days": [
                {
                    "day_number": number,
                    "theme": f"Day {number}",
                    "items": [
                        {
                            "place_id": place_id,
                            "start_time": start,
                            "duration_min": duration,
                            "slot_type": "activity",
                            "note": "kept",
                        }
                        for place_id, start, duration in items
                    ],
                }
                for number, items in days
            ],
            "assumptions": [],
        }
    )


def finding(code: str, item_ref: str | None = None, severity: str = "error") -> PlanFinding:
    day = int(item_ref[1:].split("-")[0]) if item_ref else None
    return PlanFinding.model_validate(
        {
            "code": code,
            "severity": severity,
            "day_number": day,
            "item_ref": item_ref,
            "message": "x",
        }
    )


def layout(output: ItineraryOutput | None) -> list[tuple[int, list[tuple[str, str]]]]:
    assert output is not None
    return [
        (day.day_number, [(item.place_id, item.start_time) for item in day.items])
        for day in output.days
    ]


# ---------- TC-190: the forward shift, with no model call ----------


def test_repair_tc_190_an_overlap_is_shifted_to_previous_end_plus_travel_and_buffer() -> None:
    overlapping = answer((1, [(FORT, "09:00", 120), (THALI, "10:00", 60)]))

    result = repair.repair(overlapping, [], scope(), {THALI: 15})

    assert layout(result.output) == [(1, [(FORT, "09:00"), (THALI, "11:15")])]
    assert result.fixes == 1
    assert result.output is not None
    assert [item.duration_min for item in result.output.days[0].items] == [120, 60]


def test_repair_an_item_already_late_enough_keeps_its_own_start() -> None:
    later = answer((1, [(FORT, "09:00", 120), (THALI, "13:00", 60)]))

    result = repair.repair(later, [], scope(), {THALI: 15})

    assert layout(result.output) == layout(later)
    assert result.fixes == 0


def test_repair_terminates_and_a_second_pass_finds_nothing_to_fix() -> None:
    flawed = answer((1, [(FORT, "09:00", 120), (THALI, "09:30", 60), (MARKET, "09:45", 60)]))

    first = repair.repair(flawed, [finding("OVERLAP", "d1-i2")], scope(), {THALI: 15})
    assert first.output is not None
    second = repair.repair(first.output, [], scope(), {THALI: 15})

    assert first.fixes == 2  # both later items shifted
    assert second.fixes == 0
    assert layout(second.output) == layout(first.output)


# ---------- TC-313 (repair part): locked items and must-visit places ----------


def test_repair_tc_313_a_locked_item_is_never_shifted() -> None:
    locked = answer((1, [(FORT, "09:00", 120), (THALI, "10:00", 60)]))

    result = repair.repair(locked, [], scope(locked=frozenset({(1, THALI)})), {THALI: 15})

    assert layout(result.output) == layout(locked)
    assert result.fixes == 0


def test_repair_tc_313_a_locked_or_must_visit_item_is_never_moved_or_dropped() -> None:
    full = answer((1, [(FORT, "09:00", 60), (THALI, "11:00", 60)]))
    findings = [finding("CLOSED_ON_DAY", "d1-i1"), finding("CLOSED_ON_DAY", "d1-i2")]
    tight = scope(day_numbers=range(1, 2), must_visit_ids=[FORT], locked=frozenset({(1, THALI)}))

    result = repair.repair(full, findings, tight, {})

    assert layout(result.output) == layout(full)
    assert result.fixes == 0


def test_repair_overlap_against_a_locked_item_moves_the_unlocked_one() -> None:
    clash = answer((1, [(MARKET, "09:00", 60), (THALI, "09:30", 60)]))
    locked = scope(locked=frozenset({(1, THALI)}))

    result = repair.repair(clash, [finding("OVERLAP", "d1-i2")], locked, {})

    assert layout(result.output) == [(1, [(THALI, "09:30")]), (2, [(MARKET, "09:00")])]
    assert result.fixes == 1


# ---------- The cheapest fix per code ----------


def test_repair_an_unknown_place_is_dropped() -> None:
    unknown = answer((1, [(FORT, "09:00", 60), (EXTRA, "10:30", 60)]))

    result = repair.repair(unknown, [finding("UNKNOWN_PLACE", "d1-i2")], scope(), {})

    assert layout(result.output) == [(1, [(FORT, "09:00")])]
    assert result.fixes == 1


def test_repair_a_place_closed_on_its_day_moves_to_the_day_with_most_room() -> None:
    closed = answer((1, [(FORT, "09:00", 120), (MARKET, "11:30", 60)]))

    result = repair.repair(closed, [finding("CLOSED_ON_DAY", "d1-i2")], scope(), {})

    assert layout(result.output) == [(1, [(FORT, "09:00")]), (2, [(MARKET, "09:00")])]
    assert result.fixes == 1


def test_repair_with_no_room_elsewhere_the_lowest_ranked_unlocked_item_is_dropped() -> None:
    closed = answer((1, [(FORT, "09:00", 120), (THALI, "11:30", 60)]))

    result = repair.repair(closed, [finding("CLOSED_ON_DAY", "d1-i2")], scope(day_numbers=[1]), {})

    assert layout(result.output) == [(1, [(FORT, "09:00")])]


def test_repair_outside_hours_swaps_with_the_next_item() -> None:
    early = answer((1, [(MARKET, "09:00", 60), (THALI, "10:15", 60)]))

    result = repair.repair(early, [finding("OUTSIDE_HOURS", "d1-i1")], scope(), {})

    assert layout(result.output) == [(1, [(THALI, "09:00"), (MARKET, "10:00")])]
    assert result.fixes == 1


def test_repair_never_acts_on_budget_or_other_non_error_findings() -> None:
    plan = answer((1, [(FORT, "09:00", 60), (MARKET, "10:15", 60)]))
    findings = [
        finding("BUDGET_EXCEEDED", severity="warning"),
        finding("DAY_TOO_LONG", severity="warning"),
        finding("BUDGET_NEAR", severity="info"),
    ]

    result = repair.repair(plan, findings, scope(), {})

    assert layout(result.output) == layout(plan)
    assert result.fixes == 0


def test_repair_a_missing_must_visit_place_goes_to_the_day_with_most_room() -> None:
    plan = answer((1, [(MARKET, "09:00", 60), (THALI, "10:15", 60)]))

    result = repair.repair(plan, [], scope(must_visit_ids=[FORT]), {})

    assert result.output is not None
    assert layout(result.output)[1] == (2, [(FORT, "09:00")])
    inserted = result.output.days[1].items[0]
    assert (inserted.duration_min, inserted.slot_type) == (120, "activity")  # the shortlist's
    assert result.fixes == 1


def test_repair_a_must_visit_place_with_no_room_stays_missing() -> None:
    plan = answer((1, [(MARKET, "09:00", 60)]), (2, [(THALI, "09:00", 60)]))

    result = repair.repair(plan, [], scope(max_items_per_day=1, must_visit_ids=[FORT]), {})

    assert layout(result.output) == layout(plan)
    assert result.fixes == 0


def test_repair_keeps_the_io_2_answer_and_its_citations() -> None:
    grounded = GroundedItineraryOutput.model_validate(
        {
            "days": [
                {
                    "day_number": 1,
                    "theme": "",
                    "items": [
                        {
                            "place_id": MARKET,
                            "start_time": "09:00",
                            "duration_min": 60,
                            "slot_type": "activity",
                            "note": "",
                            "source_ids": ["p1"],
                        }
                    ],
                }
            ],
            "assumptions": [],
        }
    )

    result = repair.repair(grounded, [], scope(must_visit_ids=[FORT]), {})

    assert isinstance(result.output, GroundedItineraryOutput)
    assert [item.source_ids for day in result.output.days for item in day.items] == [["p1"], []]


def test_repair_scope_for_a_request_reads_its_limits_must_visit_and_locks() -> None:
    request = sample_request()
    lock = LockedItem.model_validate(
        {"day_number": 2, "place_id": MARKET, "start_time": "10:00", "duration_min": 60}
    )

    made = repair.scope_for(request.model_copy(update={"locked_items": [lock]}))

    assert list(made.day_numbers) == [1, 2]
    assert made.must_visit_ids == [FORT]
    assert made.locked == frozenset({(2, MARKET)})
    assert made.max_items_per_day == 5


# ---------- Step 10 in the pipeline: TC-011, TC-191, TC-192, call counts ----------


class Logged(MockProvider):
    """The mock with a call log: the request of every generate_itinerary call."""

    def __init__(self, scenario: MockScenario, **kwargs: Any) -> None:
        super().__init__(scenario, app_env="test", **kwargs)
        self.calls: list[GenerationRequest] = []

    async def generate_itinerary(self, request: GenerationRequest) -> Any:
        self.calls.append(request)
        return await super().generate_itinerary(request)


def one_item_a_day() -> GenerationRequest:
    request = sample_request()
    limits = request.limits.model_copy(update={"max_items_per_day": 1})
    return request.model_copy(update={"limits": limits})


def test_repair_tc_011_invalid_json_gets_one_repair_call_then_the_rule_based_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    journal = Journal(monkeypatch, sample_request())
    provider = Logged("invalid_json")

    journal.run(provider)

    assert len(provider.calls) == 2  # 1 generate + 1 repair, never a blind retry
    assert provider.calls[0].repair_context is None
    context = provider.calls[1].repair_context
    assert context is not None
    assert (context.invalid_output, context.findings) == ("", [])
    assert journal.steps.index("validating") < journal.steps.index("repairing")
    assert journal.fell_back("invalid_output")
    assert journal.completed["repair_attempts"] == 1
    assert journal.completed["validation_summary"]["kind"] == "malformed_json"


def test_repair_an_unknown_place_is_repaired_without_a_model_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    journal = Journal(monkeypatch, sample_request())
    provider = Logged("unknown_place")

    journal.run(provider)

    assert len(provider.calls) == 1
    assert journal.completed["outcome"] == "model_repaired"
    assert (journal.completed["deterministic_repairs"], journal.completed["repair_attempts"]) == (
        1,
        0,
    )
    assert journal.saved_ids() <= sample_request().shortlist_ids()
    assert "repairing" not in journal.steps


def test_repair_tc_190_tc_191_flawed_overlap_and_must_visit_fixed_without_a_model_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    journal = Journal(monkeypatch, sample_request())
    provider = Logged("flawed")  # day 1 overlaps and FORT, a must-visit place, is left out

    journal.run(provider)

    assert len(provider.calls) == 1
    assert journal.completed["outcome"] == "model_repaired"
    assert journal.completed["deterministic_repairs"] == 2  # one shift, one insertion
    assert journal.completed["repair_attempts"] == 0
    assert FORT in journal.saved_ids()
    assert journal.findings == []


def test_repair_tc_191_tc_192_an_error_left_gets_one_call_and_stays_a_visible_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    journal = Journal(monkeypatch, one_item_a_day())  # no room anywhere for FORT
    provider = Logged("flawed")

    journal.run(provider)

    assert len(provider.calls) == 2
    context = provider.calls[1].repair_context
    assert context is not None
    assert [f.code for f in context.findings] == ["MUST_VISIT_MISSING"]
    assert ItineraryOutput.model_validate_json(context.invalid_output).place_ids() == [
        MARKET,
        THALI,
    ]
    # the repair call is the same request: same shortlist, template and passages
    assert provider.calls[1].model_copy(update={"repair_context": None}) == provider.calls[0]
    assert journal.completed["outcome"] == "model_repaired"
    assert journal.completed["repair_attempts"] == 1
    assert [f.code for f in journal.findings] == ["MUST_VISIT_MISSING"]  # FR-057 AC3


def test_repair_an_answer_still_unusable_after_the_call_is_unresolved_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    only_unknown = answer((1, [(EXTRA, "09:00", 60)]))

    class Unknown(Logged):
        async def generate_itinerary(self, request: GenerationRequest) -> Any:
            result = await super().generate_itinerary(request)
            return result.model_copy(update={"output": only_unknown})

    journal = Journal(monkeypatch, sample_request())
    provider = Unknown("ok")

    journal.run(provider)

    assert len(provider.calls) == 2
    assert journal.fell_back("unresolved_validation")
    assert journal.completed["repair_attempts"] == 1


def test_repair_a_quota_error_on_the_repair_call_ends_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class QuotaOnRepair(Logged):
        async def generate_itinerary(self, request: GenerationRequest) -> Any:
            if request.repair_context is not None:
                self.calls.append(request)
                raise ProviderQuotaExhausted()
            return await super().generate_itinerary(request)

    journal = Journal(monkeypatch, one_item_a_day())
    provider = QuotaOnRepair("flawed")

    journal.run(provider)

    assert len(provider.calls) == 2
    assert journal.failed == "provider_quota_exhausted"  # IMD-44: no fallback
    assert "save" not in journal.steps


def test_repair_with_no_time_left_no_call_is_made_and_the_rule_based_plan_is_saved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pipeline, "REPAIR_DEADLINE_S", 0)
    journal = Journal(monkeypatch, sample_request())
    provider = Logged("invalid_json")

    journal.run(provider)

    assert len(provider.calls) == 1
    assert journal.fell_back("invalid_output")
    assert journal.completed["repair_attempts"] == 0


def test_repair_the_call_gets_at_most_25_s_and_never_more_than_the_job_has_left(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    allowances: list[float | None] = []
    real = pipeline.asyncio.timeout

    def recorded(delay: float | None) -> Any:
        allowances.append(delay)
        return real(delay)

    monkeypatch.setattr(pipeline.asyncio, "timeout", recorded)
    monkeypatch.setattr(pipeline, "REPAIR_DEADLINE_S", 10)
    journal = Journal(monkeypatch, sample_request())

    journal.run(Logged("invalid_json"))

    [allowance] = allowances
    assert allowance is not None
    assert 0 < allowance <= 10


def test_repair_usage_adds_the_counts_both_calls_reported() -> None:
    first = UsageMetadata(input_tokens=100, output_tokens=20)
    second = UsageMetadata(input_tokens=150, output_tokens=None)

    total = pipeline.add_usage(first, second)

    assert total is not None
    assert (total.input_tokens, total.output_tokens, total.thinking_tokens) == (250, 20, None)
    assert pipeline.add_usage(None, None) is None


def test_repair_the_v1_template_appends_repair_txt_on_the_repair_call() -> None:
    request = sample_request()
    plain, _ = registry.render("itinerary_generate", "v1", request)
    context = RepairContext(invalid_output="", findings=[])

    system_text, _ = registry.render(
        "itinerary_generate", "v1", request.model_copy(update={"repair_context": context})
    )

    assert system_text.startswith(plain)
    assert "This is a repair call." in system_text
