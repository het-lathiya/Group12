"""Build the saved SAMPLE itineraries of Sampleton (IMP-402, §8.15, IMD-145).

Each sample is the rule-based planner's io-1 answer to one frozen trip case of
eval/datasets/trips/v1, with every place_id replaced by the place's {source_name, external_ref}
from data/fixtures/sampleton/places.csv. Nothing is written by hand.

Run from the repository root:
  apps/api/.venv/bin/python scripts/build_sample_itineraries.py          # write the files
  apps/api/.venv/bin/python scripts/build_sample_itineraries.py --check  # exit 1 if stale
"""

import argparse
import csv
import json
import sys
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from app.generation.fallback_planner import MODEL_ID, plan_rule_based  # noqa: E402
from app.schemas.ai import GenerationRequest  # noqa: E402

CASES = ROOT / "eval" / "datasets" / "trips" / "v1" / "cases.jsonl"
SAMPLETON = ROOT / "data" / "fixtures" / "sampleton"
OUT = SAMPLETON / "sample_itineraries"
# The frozen cases use stable IDs derived from external_ref (tests/unit/evaluation/test_dataset.py).
NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "urn:ai-travel-planner:sampleton")
SAMPLES = {"two_day_walking": "trips-v1-001", "five_day_local_transport": "trips-v1-003"}


def build(case_id: str) -> dict[str, Any]:
    cases = [json.loads(line) for line in CASES.read_text(encoding="utf-8").splitlines()]
    case = next(c for c in cases if c["id"] == case_id)
    with (SAMPLETON / "places.csv").open(newline="", encoding="utf-8") as file:
        rows = {str(uuid.uuid5(NAMESPACE, r["external_ref"])): r for r in csv.DictReader(file)}
    request = GenerationRequest.model_validate(case["request"])
    shortlist = {str(place.place_id): place for place in request.shortlist}
    itinerary = plan_rule_based(request).model_dump(mode="json")
    for day in itinerary["days"]:
        items = []
        for item in day["items"]:
            place_id = item.pop("place_id")
            row = rows[place_id]  # KeyError: the case names a place that is not in the fixture
            if (row["name"], int(row["typical_duration_min"])) != (
                shortlist[place_id].name,
                shortlist[place_id].typical_duration_min,
            ):
                raise ValueError(f"{case_id}: {row['external_ref']} differs from places.csv")
            ref = {"source_name": row["source_name"], "external_ref": row["external_ref"]}
            items.append({"place_ref": ref, **item})
        day["items"] = items
    trip = request.trip
    return {
        "label": "SAMPLE",
        "origin": "fallback_rule_based",
        "model_id": MODEL_ID,
        "destination_slug": "sampleton",
        "trip": {
            "case_id": case_id,
            "start_date": trip.start_date.isoformat(),
            "end_date": trip.end_date.isoformat(),
            "pace": request.preferences.pace,
            "transport_pref": request.preferences.transport_pref,
        },
        "itinerary": itinerary,
    }


def render(case_id: str) -> str:
    return json.dumps(build(case_id), indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="compare instead of writing")
    check = parser.parse_args().check
    stale = []
    for name, case_id in SAMPLES.items():
        path, text = OUT / f"{name}.json", render(case_id)
        if check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(path.name)
        else:
            OUT.mkdir(exist_ok=True)
            path.write_text(text, encoding="utf-8")
    if stale:
        print(f"stale sample itineraries: {', '.join(stale)}", file=sys.stderr)
    return 1 if stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
