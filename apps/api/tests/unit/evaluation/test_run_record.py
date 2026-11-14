"""Evaluation run records (FR-120: TC-287, TC-390; IMP-514). No database, no network."""

import json
from pathlib import Path
from typing import Any

import pytest

from app.evaluation import manifest, run


def mock_run(out: Path) -> dict[str, Any]:
    argv = ["--dataset", "trips/v1", "--provider", "MOCK", "--repeats", "1", "--out", str(out)]
    assert run.main(argv) == 0
    record: dict[str, Any] = json.loads((out / "run.json").read_text(encoding="utf-8"))
    return record


def test_run_record_tc_287_a_completed_run_has_every_field(tmp_path: Path) -> None:
    record = mock_run(tmp_path)
    assert all(record[name] is not None for name in manifest.REQUIRED_FIELDS)
    assert (record["dataset_id"], record["dataset_version"], record["case_count"]) == (
        "trips",
        "v1",
        15,
    )
    assert record["failures"] == []
    assert len(list((tmp_path / "raw").iterdir())) == 15  # one output per case and repeat
    text = (tmp_path / "run.json").read_text(encoding="utf-8").lower()
    assert "api_key" not in text
    assert "you are" not in text  # no prompt body


@pytest.mark.parametrize("name", manifest.REQUIRED_FIELDS)
def test_run_record_tc_390_an_incomplete_record_cannot_be_saved(tmp_path: Path, name: str) -> None:
    record = mock_run(tmp_path / "done")
    path = tmp_path / "again" / "run.json"
    for broken in ({k: v for k, v in record.items() if k != name}, record | {name: None}):
        with pytest.raises(manifest.IncompleteRecordError, match=name):
            manifest.write(path, broken)
        assert not path.exists()


def test_run_record_failures_list_each_errored_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = run.score_case

    async def failing(provider: Any, case: dict[str, Any], repeat: int) -> Any:
        score, raw = await real(provider, case, repeat)
        if case["id"] == "trips-v1-001":
            score["error"] = "timeout"
        return score, raw

    monkeypatch.setattr(run, "score_case", failing)
    record = mock_run(tmp_path)
    assert record["failures"] == [{"case_id": "trips-v1-001", "repeat": 1, "error": "timeout"}]


def test_run_record_an_incomplete_run_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(manifest, "git_commit", lambda: None)
    argv = ["--dataset", "trips/v1", "--provider", "MOCK", "--repeats", "1", "--out", str(tmp_path)]
    assert run.main(argv) == 3
    assert not any(tmp_path.iterdir())
