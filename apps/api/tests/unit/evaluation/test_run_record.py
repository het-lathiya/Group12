"""Evaluation run records (FR-120: TC-287, TC-390; IMP-514). No database, no network."""

import json
from pathlib import Path
from typing import Any

import pytest

from app.ai.prompts import registry
from app.ai.providers.mock import MockProvider
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


def test_run_record_prompt_version_v3_drives_every_request_imd_195(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent: list[Any] = []
    real = MockProvider.generate_itinerary

    async def spy(self: MockProvider, request: Any) -> Any:
        sent.append(request)
        return await real(self, request)

    monkeypatch.setattr(MockProvider, "generate_itinerary", spy)
    out = tmp_path / "v3"
    argv = ["--dataset", "trips/v1", "--provider", "MOCK", "--repeats", "1", "--out", str(out)]
    assert run.main([*argv, "--prompt-version", "v3"]) == 0
    record = json.loads((out / "run.json").read_text(encoding="utf-8"))
    v3 = registry.load("itinerary_generate", "v3")
    assert (record["prompt_version"], record["prompt_version_overridden"]) == ("v3", True)
    assert record["prompt_sha256"] == dict(v3.sha256)
    assert (record["input_schema_version"], record["output_schema_version"]) == ("gr-2", "io-2")
    assert len(sent) == 15
    assert all(r.prompt_version == "v3" and r.input_schema_version == "gr-2" for r in sent)
    assert record["failures"] == []


def test_run_record_default_keeps_the_version_the_requests_name(tmp_path: Path) -> None:
    record = mock_run(tmp_path)
    v1 = registry.load("itinerary_generate", "v1")
    assert (record["prompt_version"], record["prompt_version_overridden"]) == ("v1", False)
    assert record["prompt_sha256"] == dict(v1.sha256)
    assert (record["input_schema_version"], record["output_schema_version"]) == ("gr-1", "io-1")


def test_run_record_an_unknown_prompt_version_is_a_cli_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = ["--dataset", "trips/v1", "--provider", "MOCK", "--out", str(tmp_path)]
    with pytest.raises(SystemExit) as exit_info:
        run.main([*argv, "--prompt-version", "v9"])
    assert exit_info.value.code == 2
    assert "--prompt-version: invalid choice: 'v9'" in capsys.readouterr().err
    assert not any(tmp_path.iterdir())


def test_run_record_prompt_version_is_refused_for_the_retrieval_suite(
    capsys: pytest.CaptureFixture[str],
) -> None:
    argv = ["--dataset", "retrieval/v1", "--suite", "retrieval", "--provider", "MOCK"]
    with pytest.raises(SystemExit) as exit_info:
        run.main([*argv, "--prompt-version", "v3"])
    assert exit_info.value.code == 2
    assert "generation suite only" in capsys.readouterr().err


def test_run_record_retrieval_report_quotes_the_record_prompt_version() -> None:
    row = dict.fromkeys(
        (
            "queries",
            "recall_at_6",
            "place_hit_rate_vector",
            "place_hit_rate_lexical",
            "citation_validity",
            "grounding_rate",
        ),
        0,
    )
    record = {
        "run_id": "r",
        "dataset_version": "v1",
        "dataset_sha256": "0" * 64,
        "provider": "MOCK",
        "embedding_model_id": None,
        "git_commit": "c",
        "prompt_template_id": "itinerary_generate",
        "prompt_version": "v2",
        "metrics": {"overall": row, "by_destination": {}},
    }
    text = run.report(record)
    assert (
        "Prompt itinerary_generate v2 (from the run record). MOCK does not read the prompt" in text
    )
