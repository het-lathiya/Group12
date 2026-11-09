"""Must-visit places and explicit constraints in the pipeline (FR-034; IMP-406: TC-142, TC-186).

The pipeline stand-ins of ``fixtures.pipeline`` (no database); tests/api/test_generations.py runs
the same cases against a real one (TC-141 to TC-144).
"""

import pytest
from fixtures.ai import FORT, sample_request
from fixtures.pipeline import Journal

from app.ai.providers.mock import MockProvider
from app.generation import fallback_planner, retrieval


def test_must_visit_a_place_the_model_left_out_is_saved_as_must_visit_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    journal = Journal(monkeypatch, sample_request())

    journal.run(MockProvider("flawed", app_env="test"))  # leaves FORT out (IMD-27)

    assert journal.completed["outcome"] == "model"  # MUST_VISIT_MISSING does not block (§8.12)
    [missing] = [f for f in journal.findings if f.code == "MUST_VISIT_MISSING"]
    assert (str(missing.place_id), missing.item_ref, missing.severity) == (FORT, None, "error")
    assert "Example Fort" in missing.message
    assert retrieval.NO_ROOM[0] in missing.message
    assert missing.suggested_fix == retrieval.NO_ROOM[1]
    assert journal.completed["validation_summary"]["errors"] == 1


def test_must_visit_the_reason_of_a_filter_conflict_is_named(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    journal = Journal(monkeypatch, sample_request())
    journal.reasons = {FORT: retrieval.MUST_VISIT_REASONS[retrieval.NOTE_CLOSED]}

    journal.run(MockProvider("flawed", app_env="test"))

    [missing] = [f for f in journal.findings if f.code == "MUST_VISIT_MISSING"]
    assert "It is closed on every day of the trip." in missing.message
    assert missing.suggested_fix.startswith("Change the trip dates")


def test_must_visit_a_plan_holding_every_must_visit_place_has_no_finding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    journal = Journal(monkeypatch, sample_request())

    journal.run(MockProvider("ok", app_env="test"))

    assert FORT in journal.saved_ids()
    assert journal.findings == []
    assert journal.completed["validation_summary"]["errors"] == 0


def test_must_visit_the_rule_based_plan_is_validated_too(monkeypatch: pytest.MonkeyPatch) -> None:
    request = sample_request()
    too_long = [
        place.model_copy(update={"typical_duration_min": 480})
        if str(place.place_id) == FORT
        else place
        for place in request.shortlist
    ]
    tight = request.limits.model_copy(update={"max_active_minutes_per_day": 300})
    journal = Journal(
        monkeypatch, request.model_copy(update={"shortlist": too_long, "limits": tight})
    )
    journal.model_id = fallback_planner.MODEL_ID

    journal.run(MockProvider("ok", app_env="test"))

    assert journal.fell_back(None)
    assert [f.code for f in journal.findings] == ["MUST_VISIT_MISSING"]


def test_must_visit_ai_text_only_in_theme_and_note(monkeypatch: pytest.MonkeyPatch) -> None:
    journal = Journal(monkeypatch, sample_request())

    journal.run(MockProvider("ok", app_env="test"))

    assert journal.saved is not None
    for day in journal.saved:
        assert day.theme.startswith("SAMPLE")
        for item in day.items:
            assert item.note.startswith("SAMPLE")
            # Facts are the backend's: start times from step 9, travel from routing.
            assert item.travel_source in (None, "routing_api")
