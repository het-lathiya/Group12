"""Offline evaluation harness (FR-119: TC-285, TC-286, TC-387, TC-041; IMP-413)."""

import asyncio
import inspect
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import SecretStr

from app.ai.providers.mock import MockProvider
from app.core.config import get_settings
from app.evaluation import manifest, metrics, run
from app.schemas.ai import ItineraryOutput
from app.validation import output_check, validator

MANIFEST_FIELDS = {
    "run_id",
    "dataset_id",
    "dataset_version",
    "dataset_sha256",
    "provider",
    "model_id",
    "prompt_template_id",
    "prompt_version",
    "input_schema_version",
    "output_schema_version",
    "generation_settings",
    "git_commit",
    "started_at",
    "ended_at",
    "metrics",
}


def cases() -> list[dict[str, Any]]:
    return manifest.load_dataset(run.DATASETS / "trips" / "v1")[1]


def test_tc_285_tc_387_mock_dry_run_completes_offline_and_writes_the_record(
    tmp_path: Path,
) -> None:
    code = run.main(
        ["--dataset", "trips/v1", "--provider", "MOCK", "--repeats", "1", "--out", str(tmp_path)]
    )
    assert code == 0
    record = json.loads((tmp_path / "run.json").read_text())
    assert set(record) >= MANIFEST_FIELDS
    assert (record["provider"], record["model_id"], record["dataset_version"]) == (
        "MOCK",
        "mock-v1",
        "v1",
    )
    assert record["metrics"]["attempts"] == 15
    assert record["metrics"]["counts"]["schema_valid"] == {"k": 15, "n": 15}
    assert len(json.loads((tmp_path / "scores.json").read_text())) == 15
    assert len(list((tmp_path / "raw").iterdir())) == 15
    assert not any("key" in field or "secret" in field for field in record)


def test_tc_286_metric_definitions_take_no_provider_and_score_alike() -> None:
    assert list(inspect.signature(metrics.compute).parameters) == ["scores"]
    scores = [
        {"schema_valid": True, "place_ids_valid": True, "usable": False},
        {"schema_valid": False, "place_ids_valid": False, "usable": False},
    ]
    result = metrics.compute(scores)
    assert result["counts"]["schema_valid"] == {"k": 1, "n": 2}
    assert result["counts"]["usable"] == {"k": 0, "n": 2}
    assert set(result["numbered"]) == {str(n) for n in range(1, 14)}
    assert all(m["value"] is None for m in result["numbered"].values())


def test_tc_041_scoring_uses_the_production_validator_and_output_check() -> None:
    assert run.validate is validator.validate
    assert run.output_check is output_check
    case = next(c for c in cases() if c["request"]["must_visit_place_ids"])
    score, raw = asyncio.run(run.score_case(MockProvider("flawed", app_env="test"), case, 1))
    assert score["findings"].get("MUST_VISIT_MISSING") == 1
    # step 9 replaces the model's times (FR-033), so the mock's overlap is gone, as in production
    assert "OVERLAP" not in score["findings"]
    assert score["usable"] is True
    assert raw["days"]


def test_an_invalid_answer_is_scored_not_schema_valid() -> None:
    score, raw = asyncio.run(
        run.score_case(MockProvider("invalid_json", app_env="test"), cases()[0], 1)
    )
    assert score["error"] == "malformed_json"
    assert (score["schema_valid"], score["usable"]) == (False, False)
    assert raw == {"error": "malformed_json"}


def test_rule_based_exits_2_until_the_planner_exists(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = run.main(["--dataset", "trips/v1", "--provider", "RULE_BASED", "--out", str(tmp_path)])
    assert code == 2
    assert "rule-based planner not available (IMP-402)" in capsys.readouterr().err
    assert not (tmp_path / "run.json").exists()


def test_gemini_is_refused_without_a_key_and_never_built(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def no_provider(*_: object) -> None:
        raise AssertionError("no provider may be built")

    monkeypatch.setattr(run, "get_provider", no_provider)
    settings = get_settings().model_copy(update={"gemini_api_key": SecretStr("")})
    code = run.main(
        ["--dataset", "trips/v1", "--provider", "GEMINI", "--out", str(tmp_path)], settings
    )
    assert code == 2
    assert "GEMINI_API_KEY" in capsys.readouterr().err


def test_a_dataset_that_does_not_match_its_manifest_exits_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = tmp_path / "trips" / "v9"
    folder.mkdir(parents=True)
    (folder / "cases.jsonl").write_text("{}\n")
    (folder / "manifest.json").write_text(json.dumps({"files": {"cases.jsonl": "0" * 64}}))
    monkeypatch.setattr(run, "DATASETS", tmp_path)
    assert run.main(["--dataset", "trips/v9", "--provider", "MOCK"]) == 1
    assert run.main(["--dataset", "trips/missing", "--provider", "MOCK"]) == 1


def test_duplicate_places_count_a_repeated_place_and_meal_stops_imd_181() -> None:
    def answer(days: list[list[tuple[str, str]]]) -> ItineraryOutput:
        return ItineraryOutput.model_validate(
            {
                "days": [
                    {
                        "day_number": n,
                        "theme": "t",
                        "items": [
                            {
                                "place_id": place,
                                "start_time": "12:00",
                                "duration_min": 60,
                                "slot_type": slot,
                                "note": "",
                            }
                            for place, slot in items
                        ],
                    }
                    for n, items in enumerate(days, start=1)
                ],
                "summary": "s",
                "assumptions": [],
            }
        )

    a, b = "00000000-0000-4000-8000-000000000001", "00000000-0000-4000-8000-000000000005"
    assert run.duplicate_places(answer([[(a, "activity"), (b, "meal")]]), 1) == 0
    # The same food place as lunch on both days, and a sight twice on one day.
    repeated = answer([[(b, "meal"), (a, "activity"), (a, "activity")], [(b, "meal")]])
    assert run.duplicate_places(repeated, 2) == 2
    assert run.duplicate_places(repeated, 1) == 1  # a day outside the trip is not counted
    counts = metrics.compute(
        [{"no_duplicate_places": True}, {"no_duplicate_places": False}, {"schema_valid": False}]
    )["counts"]
    assert counts["no_duplicate_places"] == {"k": 1, "n": 3}
