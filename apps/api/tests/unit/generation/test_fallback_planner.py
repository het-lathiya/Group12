"""The rule-based fallback planner and its pipeline paths (§8.15, FR-036; IMP-402: TC-146).

The planner is pure, so most cases call it directly. The pipeline cases use the stand-ins of
``fixtures.pipeline`` (no database); tests/api/test_generations.py covers TC-145 and TC-331 with a
real one. The SAMPLE trips are the 15 cases of eval/datasets/trips/v1.
"""

import ast
import asyncio
import json
from pathlib import Path
from typing import Any

import pytest
from fixtures.ai import FORT, sample_request
from fixtures.pipeline import Journal

from app.ai.errors import ProviderQuotaExhausted, ProviderUnavailable
from app.ai.providers.mock import MockProvider
from app.generation import fallback_planner, schedule
from app.generation.fallback_planner import (
    LUNCH_FROM,
    LUNCH_TO,
    MODEL_ID,
    NoPlanError,
    plan_rule_based,
)
from app.routing.estimate import TravelEstimate, estimate
from app.schemas.ai import GenerationRequest, ItineraryOutput
from app.validation.rules import ValidationContext
from app.validation.validator import validate

CASES = Path(__file__).resolve().parents[5] / "eval" / "datasets" / "trips" / "v1" / "cases.jsonl"
PLANNER_SOURCE = Path(fallback_planner.__file__)


def sample_trips() -> list[tuple[str, GenerationRequest]]:
    lines = CASES.read_text(encoding="utf-8").splitlines()
    cases = [json.loads(line) for line in lines]
    return [(c["id"], GenerationRequest.model_validate(c["request"])) for c in cases]


class EstimatedRouting:
    """Step 9 with the distance estimate only, as when no route is cached."""

    async def travel(self, origin: Any, target: Any, mode: str) -> TravelEstimate:
        return estimate(origin.lat, origin.lon, target.lat, target.lon, mode)


def findings(request: GenerationRequest, output: ItineraryOutput) -> list[Any]:
    """The merged validator on the recalculated plan, as the pipeline runs it."""
    places = {str(place.place_id): place for place in request.shortlist}
    plan = asyncio.run(
        schedule.recalculate(
            output.days,
            places,
            EstimatedRouting(),
            request.preferences.pace,
            mode=request.preferences.transport_pref,
        )
    )
    ctx = ValidationContext(
        start_date=request.trip.start_date,
        end_date=request.trip.end_date,
        places={place_id: place.name for place_id, place in places.items()},
        must_visit_ids=frozenset(str(i) for i in request.must_visit_place_ids),
        shortlist_ids=frozenset(request.shortlist_ids()),
    )
    return validate(plan, ctx)


def minutes(hhmm: str) -> int:
    return int(hhmm[:2]) * 60 + int(hhmm[3:])


# ---------- The planner (pure) ----------


@pytest.mark.parametrize(("case_id", "request_"), sample_trips(), ids=lambda v: str(v)[:12])
def test_fallback_tc_146_two_runs_give_identical_plans(
    case_id: str, request_: GenerationRequest
) -> None:
    first = plan_rule_based(request_).model_dump_json()
    fresh = GenerationRequest.model_validate(request_.model_dump())

    assert plan_rule_based(fresh).model_dump_json() == first


@pytest.mark.parametrize(("case_id", "request_"), sample_trips(), ids=lambda v: str(v)[:12])
def test_fallback_plans_have_no_error_finding_on_the_sample_trips(
    case_id: str, request_: GenerationRequest
) -> None:
    output = plan_rule_based(request_)

    assert [f.code for f in findings(request_, output) if f.severity == "error"] == []


@pytest.mark.parametrize(("case_id", "request_"), sample_trips(), ids=lambda v: str(v)[:12])
def test_fallback_plans_keep_to_the_shortlist_days_and_pace(
    case_id: str, request_: GenerationRequest
) -> None:
    output = plan_rule_based(request_)
    limits = request_.limits
    days = [day.day_number for day in output.days]

    assert set(output.place_ids()) <= request_.shortlist_ids()
    assert len(output.place_ids()) == len(set(output.place_ids()))
    assert all(1 <= day <= request_.trip.num_days for day in days)
    for day in output.days:
        assert len(day.items) <= limits.max_items_per_day
        assert minutes(day.items[0].start_time) == minutes(limits.day_start)
        last = day.items[-1]
        assert minutes(last.start_time) + last.duration_min <= minutes(limits.day_end)
        assert sum(item.duration_min for item in day.items) <= limits.max_active_minutes_per_day
        meals = [item for item in day.items if item.slot_type == "meal"]
        assert len(meals) <= 1


@pytest.mark.parametrize(("case_id", "request_"), sample_trips(), ids=lambda v: str(v)[:12])
def test_fallback_meals_start_in_the_lunch_window_unless_must_visit(
    case_id: str, request_: GenerationRequest
) -> None:
    must = {str(i) for i in request_.must_visit_place_ids}
    for day in plan_rule_based(request_).days:
        for item in day.items:
            if item.slot_type == "meal" and item.place_id not in must:
                assert LUNCH_FROM <= minutes(item.start_time) <= LUNCH_TO


def test_fallback_text_comes_from_templates_and_items_have_no_note() -> None:
    output = plan_rule_based(sample_request())

    assert output.days[0].theme == "Day 1 around Example Fort"
    assert all(item.note == "" for day in output.days for item in day.items)  # IMD-131
    assert output.summary == fallback_planner.SUMMARY


def test_fallback_puts_a_must_visit_place_first() -> None:
    request = sample_request()
    reordered = request.model_copy(update={"shortlist": list(reversed(request.shortlist))})

    output = plan_rule_based(reordered)

    assert output.days[0].items[0].place_id == FORT


def test_fallback_leaves_out_a_must_visit_place_that_cannot_fit_and_the_validator_reports_it() -> (
    None
):
    request = sample_request()
    too_long = [
        place.model_copy(update={"typical_duration_min": 480})
        if str(place.place_id) == FORT
        else place
        for place in request.shortlist
    ]
    tight = request.model_copy(
        update={
            "shortlist": too_long,
            "limits": request.limits.model_copy(update={"max_active_minutes_per_day": 300}),
        }
    )

    output = plan_rule_based(tight)

    assert FORT not in output.place_ids()
    missing = [f for f in findings(tight, output) if f.code == "MUST_VISIT_MISSING"]
    assert [str(f.place_id) for f in missing] == [FORT]


def test_fallback_with_no_place_that_fits_raises() -> None:
    request = sample_request()

    with pytest.raises(NoPlanError):
        plan_rule_based(request.model_copy(update={"shortlist": []}))


def test_fallback_shares_no_code_with_the_mock_provider() -> None:
    tree = ast.parse(PLANNER_SOURCE.read_text(encoding="utf-8"))
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }

    assert not any("mock" in name or "providers" in name for name in imported)


# ---------- Pipeline paths (stand-ins, no database) ----------


def test_fallback_after_an_unavailable_provider_saves_the_labelled_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    journal = Journal(monkeypatch, sample_request())

    journal.run(MockProvider("ok", app_env="test", raise_error=ProviderUnavailable()))

    assert journal.fell_back("provider_unavailable")
    assert journal.failed is None
    assert journal.completed["adapter_version"] == "mock-1"  # an AI attempt was made (IMD-43)


def test_fallback_mode_rule_based_makes_no_model_call(monkeypatch: pytest.MonkeyPatch) -> None:
    journal = Journal(monkeypatch, sample_request())
    journal.model_id = MODEL_ID
    calls: list[str] = []

    class Counting(MockProvider):
        async def generate_itinerary(self, request: GenerationRequest) -> Any:
            calls.append("generate")
            return await super().generate_itinerary(request)

        async def embed_texts(self, *args: Any, **kwargs: Any) -> Any:
            calls.append("embed")
            return await super().embed_texts(*args, **kwargs)

    journal.run(Counting("ok", app_env="test"))

    assert calls == []
    assert "retrieval" not in journal.steps
    assert journal.fell_back(None)
    assert journal.completed["adapter_version"] is None
    assert journal.saved_ids() <= sample_request().shortlist_ids()


def test_fallback_is_not_used_for_quota_exhaustion(monkeypatch: pytest.MonkeyPatch) -> None:
    journal = Journal(monkeypatch, sample_request())

    journal.run(MockProvider("ok", app_env="test", raise_error=ProviderQuotaExhausted()))

    assert journal.failed == "provider_quota_exhausted"  # IMD-44
    assert journal.saved is None


def test_fallback_that_cannot_place_anything_ends_unresolved_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    journal = Journal(monkeypatch, sample_request())
    journal.inactive = {place.place_id for place in sample_request().shortlist}

    journal.run(MockProvider("ok", app_env="test"))

    assert journal.failed == "unresolved_validation"
    assert journal.saved is None
