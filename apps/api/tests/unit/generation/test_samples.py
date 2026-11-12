"""Saved sample itineraries, file side (§8.15, FR-036 AC3; IMP-402: TC-147 sample half, IMD-145).

The database side (load, validate, reseed) is tests/api/test_samples.py.
"""

import asyncio
import csv
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from app.generation import fallback_planner, samples

REPO_ROOT = Path(__file__).resolve().parents[5]
BUILDER = REPO_ROOT / "scripts" / "build_sample_itineraries.py"
SAMPLETON = REPO_ROOT / "data" / "fixtures" / "sampleton"
NAMES = ["five_day_local_transport", "two_day_walking"]
NO_SESSION: Any = None  # these cases end before any query


def builder() -> ModuleType:
    spec = importlib.util.spec_from_file_location("build_sample_itineraries", BUILDER)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stored(name: str) -> dict[str, Any]:
    path = SAMPLETON / "sample_itineraries" / f"{name}.json"
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def items(data: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for day in data["itinerary"]["days"] for item in day["items"]]


def test_sample_two_saved_samples_for_sampleton() -> None:
    assert samples.list_samples("sampleton") == NAMES


@pytest.mark.parametrize("slug", ["no-such-place", "../fixtures/sampleton", "Sampleton", ""])
def test_sample_unknown_or_unsafe_slug_has_none(slug: str) -> None:
    assert samples.list_samples(slug) == []


@pytest.mark.parametrize("name", NAMES)
def test_sample_files_are_the_rule_based_planners_output(name: str) -> None:
    module = builder()

    assert json.loads(module.render(module.SAMPLES[name])) == stored(name)


@pytest.mark.parametrize("name", NAMES)
def test_sample_files_are_labelled_sample_and_carry_no_ai_text(name: str) -> None:
    sample = samples.SampleFile.model_validate(stored(name))

    assert (sample.label, sample.origin, sample.model_id) == (
        "SAMPLE",
        "fallback_rule_based",
        fallback_planner.MODEL_ID,
    )
    assert sample.itinerary["summary"] == fallback_planner.SUMMARY
    assert all(item["note"] == "" for item in items(stored(name)))  # IMD-131: no note at all


@pytest.mark.parametrize("name", NAMES)
def test_sample_places_are_referenced_by_fixture_refs_not_ids(name: str) -> None:
    with (SAMPLETON / "places.csv").open(newline="", encoding="utf-8") as file:
        fixture = {(r["source_name"], r["external_ref"]) for r in csv.DictReader(file)}

    for item in items(stored(name)):
        assert "place_id" not in item
        assert (item["place_ref"]["source_name"], item["place_ref"]["external_ref"]) in fixture


def test_sample_two_samples_have_different_lengths() -> None:
    lengths = {len(stored(name)["itinerary"]["days"]) for name in NAMES}

    assert len(lengths) == 2


def test_sample_unresolved_ref_raises_and_names_it(monkeypatch: pytest.MonkeyPatch) -> None:
    async def nothing_active(*_: Any) -> dict[Any, Any]:
        return {}

    monkeypatch.setattr(samples.places_service, "active_places_by_refs", nothing_active)

    with pytest.raises(samples.UnresolvedPlaceRefError, match="sample-006"):
        asyncio.run(samples.load_sample(NO_SESSION, "sampleton", "two_day_walking"))


def test_sample_unknown_name_raises() -> None:
    with pytest.raises(samples.SampleNotFoundError):
        asyncio.run(samples.load_sample(NO_SESSION, "sampleton", "../places"))
