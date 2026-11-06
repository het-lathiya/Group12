"""Evaluation dataset trips/v1 (§8.17; FR-118: TC-283, TC-386; IMP-310).

Every case passes the case schema and gr-1, IDs are unique, the manifest hashes match, and every
place in a case equals its row in the SAMPLE fixture, so no place, price or hours value is invented.
"""

import csv
import hashlib
import json
import re
import uuid
from functools import cache
from pathlib import Path
from typing import Any

import pytest

from app.schemas.ai import GenerationRequest

REPO_ROOT = Path(__file__).resolve().parents[5]
DATASET = REPO_ROOT / "eval" / "datasets" / "trips"
V1 = DATASET / "v1"
PLACES_CSV = REPO_ROOT / "data" / "fixtures" / "sampleton" / "places.csv"
# Seeded rows get random IDs, so frozen requests use stable IDs derived from external_ref.
NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "urn:ai-travel-planner:sampleton")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
JSON_TYPES: dict[str, type | tuple[type, ...]] = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "integer": int,
    "null": type(None),
}


@cache
def cases() -> tuple[dict[str, Any], ...]:
    lines = (V1 / "cases.jsonl").read_text(encoding="utf-8").splitlines()
    return tuple(json.loads(line) for line in lines)


@cache
def fixture_places() -> dict[str, dict[str, str]]:
    with PLACES_CSV.open(newline="", encoding="utf-8") as file:
        rows = csv.DictReader(file)
        return {str(uuid.uuid5(NAMESPACE, row["external_ref"])): row for row in rows}


def manifest() -> dict[str, Any]:
    return json.loads((V1 / "manifest.json").read_text(encoding="utf-8"))


def schema() -> dict[str, Any]:
    return json.loads((DATASET / "schema.json").read_text(encoding="utf-8"))


def problems(value: Any, rule: dict[str, Any], path: str = "case") -> list[str]:
    """The keywords schema.json uses, checked by hand: the project has no JSON Schema library."""
    found = []
    if "const" in rule and value != rule["const"]:
        found.append(f"{path}: not {rule['const']!r}")
    if "enum" in rule and value not in rule["enum"]:
        found.append(f"{path}: not in the enum")
    if "pattern" in rule and not re.fullmatch(rule["pattern"], value):
        found.append(f"{path}: does not match {rule['pattern']}")
    if "type" in rule:
        names = rule["type"] if isinstance(rule["type"], list) else [rule["type"]]
        if not isinstance(value, tuple(JSON_TYPES[name] for name in names)):
            return [*found, f"{path}: not {names}"]
    if isinstance(value, dict):
        known = rule.get("properties", {})
        found += [f"{path}.{k}: missing" for k in rule.get("required", []) if k not in value]
        if rule.get("additionalProperties") is False:
            found += [f"{path}.{k}: not allowed" for k in value if k not in known]
        for key, inner in known.items():
            if key in value:
                found += problems(value[key], inner, f"{path}.{key}")
    if isinstance(value, list) and "items" in rule:
        for index, item in enumerate(value):
            found += problems(item, rule["items"], f"{path}[{index}]")
    return found


def test_the_schema_check_refuses_a_broken_case() -> None:
    broken = {**cases()[0], "version": "v2", "extra": 1}
    del broken["request"]
    assert set(problems(broken, schema())) == {
        "case.version: not 'v1'",
        "case.request: missing",
        "case.extra: not allowed",
    }


def test_tc_283_every_case_has_id_inputs_hard_constraints_and_version() -> None:
    for case in cases():
        assert problems(case, schema()) == [], case["id"]


def test_tc_283_every_request_is_a_valid_gr_1_request() -> None:
    for case in cases():
        request = GenerationRequest.model_validate(case["request"])
        assert request.input_schema_version == "gr-1"
        assert request.shortlist, case["id"]


def test_tc_386_ids_are_unique_and_there_are_15_cases() -> None:
    ids = [case["id"] for case in cases()]
    assert len(ids) == 15
    assert len(set(ids)) == 15
    requests = [case["request"]["request_id"] for case in cases()]
    assert len(set(requests)) == 15


def test_tc_386_the_manifest_matches_the_files() -> None:
    data = manifest()
    assert (data["dataset_id"], data["version"]) == ("trips", "v1")
    assert data["case_count"] == len(cases())
    counts: dict[str, int] = {}
    for case in cases():
        counts[case["category"]] = counts.get(case["category"], 0) + 1
    assert data["category_counts"] == counts
    for name, digest in data["files"].items():
        assert hashlib.sha256((V1 / name).read_bytes()).hexdigest() == digest, name
    lines = "".join(f"{name}:{digest}\n" for name, digest in sorted(data["files"].items()))
    assert hashlib.sha256(lines.encode()).hexdigest() == data["set_sha256"]


def test_every_category_of_the_card_has_a_case() -> None:
    assert set(manifest()["category_counts"]) == set(schema()["properties"]["category"]["enum"])
    days = {c["request"]["trip"]["num_days"] for c in cases() if c["category"] == "standard"}
    assert days == {2, 3, 5}


@pytest.mark.parametrize("case", cases(), ids=lambda case: case["id"])
def test_every_place_equals_its_sample_fixture_row(case: dict[str, Any]) -> None:
    for place in case["request"]["shortlist"]:
        row = fixture_places()[place["place_id"]]
        assert place["name"] == row["name"]
        assert place["category"] == row["category"]
        assert place["tags"] == row["tags"].split(";")
        assert place["lat"] == float(row["lat"])
        assert place["lon"] == float(row["lon"])
        assert place["typical_duration_min"] == int(row["typical_duration_min"])
        assert place["price_min"] == (row["price_min"] or None)
        assert place["price_max"] == (row["price_max"] or None)
        assert place["price_label"] == row["price_label"]
        assert place["hours_summary"] == f"hours {row['hours_label']}"
        suitability = place["suitability"]
        for flag in ("step_free", "child_friendly"):
            assert suitability[flag] == {"": None, "true": True, "false": False}[row[flag]]


@pytest.mark.parametrize("case", cases(), ids=lambda case: case["id"])
def test_hard_constraints_agree_with_the_request(case: dict[str, Any]) -> None:
    request, hard = case["request"], case["hard_constraints"]
    shortlist = {place["place_id"]: place for place in request["shortlist"]}
    assert hard["step_free_required"] == request["preferences"]["step_free_required"]
    assert hard["must_visit_place_ids"] == request["must_visit_place_ids"]
    assert hard["max_items_per_day"] == request["limits"]["max_items_per_day"]
    assert set(hard["must_visit_place_ids"]) <= set(shortlist)
    assert set(hard["locked_place_ids"]) <= set(shortlist)
    budget = request["trip"]["budget"]
    assert hard["budget_amount"] == (budget["amount"] if budget else None)
    conflicting = {item["place_id"] for item in case["expected_properties"]["conflicts"]}
    assert conflicting <= set(hard["must_visit_place_ids"])
    if hard["step_free_required"]:
        for place_id, place in shortlist.items():
            assert place["suitability"]["step_free"] is True or place_id in conflicting


def test_conflict_cases_carry_their_conflicts() -> None:
    for case in cases():
        if case["category"] == "must_visit_conflict":
            assert len(case["expected_properties"]["conflicts"]) == 2


def test_the_regeneration_case_has_a_day_scope_and_locks_on_that_day() -> None:
    (case,) = [c for c in cases() if c["category"] == "day_regeneration"]
    scope, locked = case["request"]["scope"], case["request"]["locked_items"]
    assert scope["kind"] == "day"
    assert locked
    assert {item["day_number"] for item in locked} == {scope["day_number"]}


def test_hostile_cases_hold_notes_only_as_quoted_data() -> None:
    hostile = [c for c in cases() if c["category"] == "hostile_notes"]
    assert hostile
    for case in hostile:
        note = case["request"]["preferences"]["notes_quoted"]
        assert re.search(r"ignore (previous|all prior)", note, re.IGNORECASE)
        assert case["expected_properties"]["notes_change_nothing"] is True
    for case in cases():
        if case["category"] != "hostile_notes":
            assert case["request"]["preferences"]["notes_quoted"] is None


def test_no_case_contains_personal_data() -> None:
    assert not EMAIL.search((V1 / "cases.jsonl").read_text(encoding="utf-8"))
