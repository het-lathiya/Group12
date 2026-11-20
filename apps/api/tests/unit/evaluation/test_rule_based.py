"""RULE_BASED in the evaluation harness (IMD-213, PD-IMP-705-1; TC-393)."""

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from app.evaluation import manifest, metrics, run
from app.generation import fallback_planner


def sample_cases() -> list[dict[str, Any]]:
    """trips/v1: the frozen SAMPLE (Sampleton) requests."""
    return manifest.load_dataset(run.DATASETS / "trips" / "v1")[1]


@pytest.fixture
def no_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_: object, **__: object) -> None:
        raise AssertionError("RULE_BASED must not build or call a provider")

    monkeypatch.setattr(run, "get_provider", refuse)


def test_the_rule_based_planner_answers_every_sample_case_with_the_production_planner() -> None:
    planner = run.RuleBasedPlanner()
    for case in sample_cases():
        score, raw = asyncio.run(run.score_case(planner, case, 1))
        assert score["error"] is None, case["id"]
        assert score["schema_valid"], case["id"]
        assert score["place_ids_valid"], case["id"]
        assert raw["summary"] == fallback_planner.SUMMARY
        assert raw["days"], case["id"]
        assert (score["input_tokens"], score["output_tokens"]) == (None, None)


def test_rule_based_run_writes_a_complete_record_without_a_provider_call(
    tmp_path: Path, no_provider: None
) -> None:
    code = run.main(
        [
            "--dataset",
            "trips/v1",
            "--provider",
            "RULE_BASED",
            "--repeats",
            "1",
            "--out",
            str(tmp_path),
        ]
    )
    assert code == 0
    record = json.loads((tmp_path / "run.json").read_text())
    assert record["provider"] == "RULE_BASED"
    assert record["model_id"] == "rule-based"
    assert record["prompt_version"] == "not applicable"
    assert record["prompt_version_overridden"] is False
    assert record["prompt_sha256"] == {}
    assert record["dataset_version"] == "v1"
    assert record["git_commit"]
    assert record["generation_settings"] == {}
    assert (record["input_schema_version"], record["output_schema_version"]) == ("gr-1", "io-1")
    assert all(record.get(field) is not None for field in manifest.REQUIRED_FIELDS)
    assert record["metrics"]["attempts"] == 15
    assert record["failures"] == []
    scores = json.loads((tmp_path / "scores.json").read_text())
    assert len(scores) == 15
    assert len(list((tmp_path / "raw").iterdir())) == 15


def test_the_rule_based_scores_use_the_same_metric_code(tmp_path: Path, no_provider: None) -> None:
    assert (
        run.main(
            [
                "--dataset",
                "trips/v1",
                "--provider",
                "RULE_BASED",
                "--repeats",
                "1",
                "--out",
                str(tmp_path),
            ]
        )
        == 0
    )
    record = json.loads((tmp_path / "run.json").read_text())
    scores = json.loads((tmp_path / "scores.json").read_text())
    assert record["metrics"] == metrics.compute(scores)


def test_a_request_with_no_fitting_place_is_scored_as_a_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def no_plan(_: object) -> None:
        raise fallback_planner.NoPlanError()

    monkeypatch.setattr(fallback_planner, "plan_rule_based", no_plan)
    score, raw = asyncio.run(run.score_case(run.RuleBasedPlanner(), sample_cases()[0], 1))
    assert score["error"] == "no_plan"
    assert (score["schema_valid"], score["usable"]) == (False, False)
    assert raw == {"error": "no_plan"}


def test_prompt_version_is_refused_for_rule_based(no_provider: None) -> None:
    with pytest.raises(SystemExit):
        run.main(["--dataset", "trips/v1", "--provider", "RULE_BASED", "--prompt-version", "v2"])
