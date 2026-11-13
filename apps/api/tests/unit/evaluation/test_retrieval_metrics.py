"""Retrieval metrics and the retrieval dataset (FR-140: TC-458; IMP-318)."""

import json
from pathlib import Path

import pytest

from app.evaluation import manifest, run
from app.evaluation.retrieval_metrics import (
    citation_validity,
    grounding_rate,
    mean,
    place_hit_rate,
    recall_at_k,
)

DATASET = run.DATASETS / "retrieval" / "v1"


def test_tc_458_recall_at_k_counts_documents_of_the_first_k_passages() -> None:
    selected = ["g:a", "g:a", "g:b", "g:c", "g:d", "g:e", "g:f", "g:z"]
    assert recall_at_k(selected, {"g:a", "g:f"}, k=6) == 0.5  # g:f is the seventh passage
    assert recall_at_k(selected, {"g:a", "g:z"}, k=8) == 1.0
    assert recall_at_k([], {"g:a"}) == 0.0


def test_tc_458_recall_with_k_larger_than_the_list_or_no_relevant_label() -> None:
    assert recall_at_k(["g:a"], ["g:a", "g:b", "g:c"], k=50) == 0.3333
    assert recall_at_k(["g:a"], []) is None


def test_tc_458_place_hit_rate_in_the_top_n() -> None:
    ranked = list(range(20))
    assert place_hit_rate(ranked, {3, 15}, top=12) == 0.5
    assert place_hit_rate(ranked[:2], {0, 1}, top=12) == 1.0
    assert place_hit_rate(ranked, set()) is None


def test_tc_458_citation_validity_is_the_share_of_saved_ids_that_were_supplied() -> None:
    assert citation_validity(["p1", "p2", "p1"], {"p1", "p2"}) == 1.0
    assert citation_validity(["p1", "x"], {"p1"}) == 0.5
    assert citation_validity([], {"p1"}) is None


def test_tc_458_grounding_rate_counts_only_written_notes() -> None:
    items = [("Note.", ["p1"]), ("Note.", []), ("", ["p2"]), ("  ", []), (None, [])]
    assert grounding_rate(items) == 0.5
    assert grounding_rate([("", [])]) is None


def test_mean_leaves_out_undefined_values() -> None:
    assert mean([1.0, None, 0.5]) == 0.75
    assert mean([None]) is None


def test_tc_458_the_labelled_dataset_matches_its_manifest_and_every_guide_label_resolves() -> None:
    dataset, queries = run.load_queries(DATASET)
    assert dataset["dataset_version"] == "retrieval/v1"
    assert len(queries) == dataset["query_count"]
    assert {r["name"] for r in dataset["reviewers"]} == {"Malhar Mer", "Krrish Kamani"}
    assert run.guide_key_errors(queries, run.REPO_ROOT / "data") == []
    for query in queries:
        assert query["relevant_place_refs"], "every query labels at least one place"
        assert all(
            {"source_name", "external_ref"} == set(ref) for ref in query["relevant_place_refs"]
        )


def test_an_unresolved_guide_label_is_an_error_that_names_it() -> None:
    queries = [
        {"destination": "sampleton", "relevant_guide_doc_keys": ["guide:sampleton/missing"]},
        {"destination": "sampleton", "relevant_guide_doc_keys": ["food-culture"]},
    ]
    assert run.guide_key_errors(queries, run.REPO_ROOT / "data") == [
        "query 1: guide guide:sampleton/missing",
        "query 2: guide food-culture",
    ]


def test_a_changed_queries_file_is_refused(tmp_path: Path) -> None:
    (tmp_path / "queries.jsonl").write_text('{"destination": "sampleton"}\n', encoding="utf-8")
    (tmp_path / "manifest.json").write_text(
        json.dumps({"files": {"queries.jsonl": "0" * 64}}), encoding="utf-8"
    )
    with pytest.raises(manifest.DatasetError, match="does not match"):
        run.load_queries(tmp_path)
