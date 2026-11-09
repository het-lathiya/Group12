"""Offline evaluation harness: python -m app.evaluation.run (MOD-B15, FR-119; IMP-413).

Each frozen gr-1 request of the dataset goes through the production functions of steps 7 to 9:
``provider.generate_itinerary``, ``output_check.apply_limits`` and ``check_output`` (step 8),
``schedule.recalculate`` with the distance estimate instead of the route cache (no database, no
network), the budget engine and ``validator.validate``. Step 10 (repair, IMP-502) is not built yet.
The provider comes from ``--provider`` on a copy of the settings, so the application default
(``AI_PROVIDER``) never changes. GEMINI runs are manual and refused without ``GEMINI_API_KEY``.

Writes ``<out>/run.json`` (the record), ``<out>/scores.json`` and ``<out>/raw/<case>_<repeat>.json``.
Exit codes: 0 done, 1 dataset unreadable or not matching its manifest, 2 provider not available.
"""

import argparse
import asyncio
import json
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Final
from uuid import uuid4

from app.ai.errors import ProviderError, ProviderInvalidOutput
from app.ai.factory import get_provider
from app.ai.providers.base import ModelProvider
from app.budget import engine
from app.core.config import Settings, get_settings
from app.evaluation import manifest, metrics
from app.generation import schedule
from app.itinerary.schemas import PlannedDay
from app.routing.estimate import TravelEstimate, TravelMode
from app.routing.service import RoutablePlace, travel_time
from app.schemas.ai import GenerationRequest, ShortlistPlace
from app.validation import output_check
from app.validation.rules import ValidationContext
from app.validation.validator import validate

REPO_ROOT: Final = Path(__file__).resolve().parents[4]
DATASETS: Final = REPO_ROOT / "eval" / "datasets"
RESULTS: Final = REPO_ROOT / "eval" / "results"
METRICS_FILE: Final = REPO_ROOT / "eval" / "metrics_v1.md"
PROVIDERS: Final = ("MOCK", "GEMINI", "RULE_BASED")
NO_RULE_BASED: Final = "rule-based planner not available (IMP-402)"
NO_GEMINI_KEY: Final = "GEMINI_API_KEY is not set; GEMINI runs are manual and need the key"
# §8.12: a plan with one of these left is not usable.
BLOCKING: Final = frozenset({"UNKNOWN_PLACE", "OUTSIDE_TRIP_DATES", "OVERLAP", "CLOSED_ON_DAY"})


class EstimateRouting:
    """Step 9 routing without the route cache or OpenRouteService: the §9.3.5 distance estimate."""

    async def travel(
        self, origin: RoutablePlace, target: RoutablePlace, mode: TravelMode | str
    ) -> TravelEstimate:
        return await travel_time(origin, target, mode)


@dataclass(frozen=True)
class PricedShortlistPlace:
    """A shortlist place as the budget engine reads it; gr-1 prices are in the trip currency."""

    price_min: Decimal | None
    price_max: Decimal | None
    price_currency: str | None
    price_label: str
    tags: list[str]


async def score_case(
    provider: ModelProvider, case: dict[str, Any], repeat: int
) -> tuple[dict[str, Any], dict[str, Any]]:
    """(score, raw output) of one attempt."""
    request = GenerationRequest.model_validate(case["request"])
    score: dict[str, Any] = {
        "case_id": case["id"],
        "repeat": repeat,
        "category": case["category"],
        "error": None,
        "schema_valid": False,
        "place_ids_valid": False,
        "usable": False,
        "invalid_ids": 0,
        "rejected_items": 0,
        "findings": {},
        "budget_status": None,
        "latency_ms": None,
        "input_tokens": None,
        "output_tokens": None,
    }
    try:
        result = await provider.generate_itinerary(request)
        score.update(
            latency_ms=result.latency_ms,
            input_tokens=result.usage.input_tokens,
            output_tokens=result.usage.output_tokens,
        )
        answer = output_check.apply_limits(
            result.output,
            trip_days=request.trip.num_days,
            max_items_per_day=request.limits.max_items_per_day,
        )
    except ProviderInvalidOutput as exc:
        score["error"] = exc.kind
        return score, {"error": exc.kind}
    except ProviderError as exc:
        score["error"] = exc.failure_reason
        return score, {"error": exc.failure_reason}
    raw = result.output.model_dump(mode="json")
    score["schema_valid"] = True

    checked = output_check.check_output(answer, request.shortlist_ids(), request.trip.num_days)
    places = {str(place.place_id): place for place in request.shortlist}
    plan = await schedule.recalculate(
        checked.output.days,
        places,
        EstimateRouting(),
        request.preferences.pace,
        mode=request.preferences.transport_pref,
    )
    ctx = ValidationContext(
        start_date=request.trip.start_date,
        end_date=request.trip.end_date,
        places={place_id: place.name for place_id, place in places.items()},
        must_visit_ids=frozenset(str(p) for p in request.must_visit_place_ids),
        shortlist_ids=frozenset(places),
    )
    codes = Counter(f.code for f in [*checked.findings, *validate(plan, ctx)])
    summary = _costs(request, places, plan)
    codes.update(alert.code for alert in summary.alerts)
    score.update(
        place_ids_valid=checked.invalid_ids == 0,
        usable=bool(plan) and not BLOCKING & set(codes),
        invalid_ids=checked.invalid_ids,
        rejected_items=checked.rejected_items,
        findings=dict(sorted(codes.items())),
        budget_status=summary.status,
    )
    return score, raw


def _costs(
    request: GenerationRequest, places: dict[str, ShortlistPlace], plan: list[PlannedDay]
) -> engine.CostSummary:
    """BF-01 to BF-12 with the production engine; no currency means every price is unavailable."""
    trip = request.trip
    currency = trip.budget.currency if trip.budget else ""
    items = []
    for day in plan:
        for item in day.items:
            place = places[item.place_id]
            cost = engine.item_cost(
                PricedShortlistPlace(
                    Decimal(place.price_min) if place.price_min else None,
                    Decimal(place.price_max) if place.price_max else None,
                    currency,
                    place.price_label,
                    place.tags,
                ),
                adults=trip.travellers.adults,
                children=trip.travellers.children,
                currency=currency,
            )
            items.append(
                engine.CostedItem(
                    uuid4(), day.day_number, place.category, cost.lo, cost.hi, cost.label
                )
            )
    inputs = engine.CostInputs(
        num_days=trip.num_days,
        adults=trip.travellers.adults,
        children=trip.travellers.children,
        currency=currency,
        budget=engine.to_minor(Decimal(trip.budget.amount)) if trip.budget else None,
        transport_per_day=None,  # traveller inputs, not in gr-1
        stay_per_night=None,
        contingency_pct=int(trip.contingency_pct),
    )
    return engine.compute_costs(items, inputs)


def unavailable(name: str, settings: Settings) -> str | None:
    """Why ``--provider`` cannot run here, or None."""
    if name == "RULE_BASED":
        return NO_RULE_BASED
    if name == "GEMINI" and not settings.gemini_api_key.get_secret_value():
        return NO_GEMINI_KEY
    return None


async def evaluate(
    provider: ModelProvider, cases: list[dict[str, Any]], repeats: int
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    scores, raw = [], {}
    for case in cases:
        for repeat in range(1, repeats + 1):
            score, output = await score_case(provider, case, repeat)
            scores.append(score)
            raw[f"{case['id']}_{repeat}"] = output
    return scores, raw


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None, settings: Settings | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.evaluation.run")
    parser.add_argument("--dataset", required=True, help="<id>/<version>, e.g. trips/v1")
    parser.add_argument("--provider", required=True, choices=PROVIDERS)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--out", type=Path, help="default eval/results/<run_id>/")
    args = parser.parse_args(argv)

    started = datetime.now(UTC)
    try:
        dataset, cases = manifest.load_dataset(DATASETS / args.dataset)
    except manifest.DatasetError as exc:
        print(exc, file=sys.stderr)
        return 1
    settings = settings or get_settings()
    reason = unavailable(args.provider, settings)
    if reason:
        print(reason, file=sys.stderr)
        return 2
    provider = get_provider(settings.model_copy(update={"ai_provider": args.provider}))

    scores, raw = asyncio.run(evaluate(provider, cases, args.repeats))
    run_id = f"{started:%Y%m%dT%H%M%SZ}-{args.provider.lower()}"
    out: Path = args.out or RESULTS / run_id
    first = cases[0]["request"]
    record = manifest.build(
        run_id=run_id,
        dataset=dataset,
        provider=args.provider,
        metadata=provider.get_model_metadata(),
        prompt=(first["prompt_template_id"], first["prompt_version"]),
        # PD-IMP-301-2: not on the protocol; the pipeline reads it the same way.
        settings_sent=getattr(provider, "generation_settings", {}),
        repeats=args.repeats,
        metrics_file=METRICS_FILE,
        started_at=started.isoformat(),
        ended_at=datetime.now(UTC).isoformat(),
        metrics=metrics.compute(scores),
    )
    _write(out / "run.json", record)
    _write(out / "scores.json", scores)
    for name, output in raw.items():
        _write(out / "raw" / f"{name}.json", output)
    print(f"evaluation {run_id}: {len(scores)} attempts, written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
