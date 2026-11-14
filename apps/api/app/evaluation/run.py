"""Offline evaluation harness: python -m app.evaluation.run (MOD-B15, FR-119; IMP-413).

Each frozen gr-1 request of the dataset goes through the production functions of steps 7 to 9:
``provider.generate_itinerary``, ``output_check.apply_limits`` and ``check_output`` (step 8),
``schedule.recalculate`` with the distance estimate instead of the route cache (no database, no
network), the budget engine and ``validator.validate``. Step 10 (repair, IMP-502) is not built yet.
The provider comes from ``--provider`` on a copy of the settings, so the application default
(``AI_PROVIDER``) never changes. GEMINI runs are manual and refused without ``GEMINI_API_KEY``.

Writes ``<out>/run.json`` (the record), ``<out>/scores.json`` and ``<out>/raw/<case>_<repeat>.json``.
Exit codes: 0 done, 1 dataset unreadable or not matching its manifest, 2 provider not available.

``--suite retrieval`` (IMP-318, Amendment A1 §6.14) needs a migrated, seeded and indexed database.
For each labelled query it builds the trip in memory, runs ``rag.service.retrieve`` and the ranking
in vector mode and with no vector result (lexical), then the grounded pipeline of steps 5 to 9 on
the vector shortlist; nothing is saved. Exit 1 also for a label that does not resolve.
"""

import argparse
import asyncio
import json
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Final
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from app.ai.errors import ProviderError, ProviderInvalidOutput
from app.ai.factory import get_provider
from app.ai.limits import enforce_input_limit
from app.ai.providers.base import ModelProvider
from app.budget import engine
from app.core.config import Settings, get_settings
from app.db.session import transaction
from app.evaluation import manifest, metrics, retrieval_metrics
from app.generation import grouping, request_builder, retrieval, schedule
from app.itinerary.schemas import PlannedDay
from app.places import service as places_service
from app.places.schemas import Destination, PlaceSummary
from app.rag import service as rag_service
from app.routing.estimate import TravelEstimate, TravelMode
from app.routing.service import RoutablePlace, travel_time
from app.schemas.ai import GenerationRequest, ShortlistPlace
from app.trips.schemas import PreferencesOut, TripDestination, TripOut, TripStatus
from app.validation import output_check
from app.validation.rules import ValidationContext
from app.validation.validator import validate

REPO_ROOT: Final = Path(__file__).resolve().parents[4]
DATASETS: Final = REPO_ROOT / "eval" / "datasets"
RESULTS: Final = REPO_ROOT / "eval" / "results"
REPORTS: Final = REPO_ROOT / "eval" / "reports"
METRICS_FILE: Final = REPO_ROOT / "eval" / "metrics_v1.md"
PROVIDERS: Final = ("MOCK", "GEMINI", "RULE_BASED")
NO_RULE_BASED: Final = "rule-based planner not available (IMP-402)"
NO_GEMINI_KEY: Final = "GEMINI_API_KEY is not set; GEMINI runs are manual and need the key"
# §8.12: a plan with one of these left is not usable.
BLOCKING: Final = frozenset({"UNKNOWN_PLACE", "OUTSIDE_TRIP_DATES", "OVERLAP", "CLOSED_ON_DAY"})
SUITES: Final = ("generation", "retrieval")
# Retrieval suite: the queries carry preferences only, so every query plans the same trip frame.
GROUNDED_PROMPT: Final = ("itinerary_generate", "v2")
TRIP_START: Final = date(2027, 3, 1)
TRIP_DAYS: Final = 2
TRIP_ADULTS: Final = 2
CONTINGENCY_PCT: Final = 10.0
GUIDE_K: Final = 6
PLACE_TOP: Final = 12
FRAME_TIME: Final = datetime(2026, 1, 1, tzinfo=UTC)


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
    request = _grouped(GenerationRequest.model_validate(case["request"]))
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
        "daily_travel_min": [],
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
        daily_travel_min=[sum(i.travel_from_prev_min or 0 for i in day.items) for day in plan],
    )
    return score, raw


def _grouped(request: GenerationRequest) -> GenerationRequest:
    """A frozen request without day_hints gets them from the grouping, as the request builder
    gives them in production (IMP-503), so the scores are of grouped plans."""
    if request.day_hints:
        return request
    hints = grouping.group_days(
        request.shortlist,
        request.must_visit_place_ids,
        request.trip.num_days,
        request.limits.max_items_per_day,
    )
    return request.model_copy(update={"day_hints": hints})


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


class LabelError(Exception):
    """A label of the retrieval dataset names nothing that exists."""


def load_queries(folder: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """The manifest and queries of a retrieval dataset, after checking the hash of queries.jsonl."""
    try:
        dataset = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        path = folder / "queries.jsonl"
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, ValueError) as exc:
        raise manifest.DatasetError(f"cannot read dataset {folder}: {exc}") from None
    if dataset.get("files", {}).get("queries.jsonl") != manifest.sha256(path):
        raise manifest.DatasetError(f"{path} does not match the hash in its manifest")
    return dataset, [json.loads(line) for line in lines if line.strip()]


def guide_key_errors(queries: list[dict[str, Any]], data_root: Path) -> list[str]:
    """Each guide label that is not ``guide:<destination>/<stem>`` with an existing file."""
    errors = []
    for number, query in enumerate(queries, 1):
        slug = query["destination"]
        folder = data_root / "fixtures" / slug / "guides"
        if not folder.is_dir():
            folder = data_root / "guides" / slug
        for key in query["relevant_guide_doc_keys"]:
            stem = key.removeprefix(f"guide:{slug}/")
            if stem == key or not (folder / f"{stem}.md").is_file():
                errors.append(f"query {number}: guide {key}")
    return errors


def _frame(
    number: int, destination: Destination, query: dict[str, Any]
) -> tuple[TripOut, PreferencesOut]:
    """The in-memory trip and preferences of one query; the ID is stable across runs."""
    trip = TripOut(
        id=uuid5(NAMESPACE_URL, f"eval:retrieval/v1:{number}"),
        title=f"retrieval evaluation query {number}",
        destination_id=destination.id,
        start_date=TRIP_START,
        end_date=TRIP_START + timedelta(days=TRIP_DAYS - 1),
        num_days=TRIP_DAYS,
        adults=TRIP_ADULTS,
        children=0,
        group_needs=[],
        budget=None,
        status=TripStatus.DRAFT,
        plan_revision=0,
        plan_stale=False,
        has_itinerary=False,
        destination=TripDestination(
            id=destination.id,
            name=destination.name,
            timezone=destination.timezone,
            currency=destination.currency,
            is_sample=destination.is_sample,
        ),
        created_at=FRAME_TIME,
        updated_at=FRAME_TIME,
    )
    prefs = PreferencesOut(
        interests=query["interests"],
        pace=query["pace"],
        budget_priority=query["budget_priority"],
        transport_pref=query["transport_pref"],
        accommodation_type=query["accommodation_type"],
        step_free_required=query["step_free_required"],
        notes=query["notes"],
        must_visit_place_ids=[],
        must_visit_places=[],
        effects=[],
        saved=True,
    )
    return trip, prefs


async def _resolve_places(query: dict[str, Any], number: int) -> set[UUID]:
    refs = [(ref["source_name"], ref["external_ref"]) for ref in query["relevant_place_refs"]]
    async with transaction() as session:
        found = await places_service.active_places_by_refs(session, query["destination"], refs)
    missing = [
        f"query {number}: place {source}/{ref}"
        for source, ref in refs
        if (source, ref) not in found
    ]
    if missing:
        raise LabelError("; ".join(missing))
    return {place.id for place in found.values()}


async def score_query(
    provider: ModelProvider,
    settings: Settings,
    number: int,
    query: dict[str, Any],
    destinations: dict[str, Destination],
) -> dict[str, Any]:
    destination = destinations.get(query["destination"])
    if destination is None:
        raise LabelError(f"query {number}: destination {query['destination']}")
    relevant_places = await _resolve_places(query, number)
    trip, prefs = _frame(number, destination, query)
    notes = request_builder.quote_notes(prefs.notes)
    retrieved = await retrieval.semantic_retrieval(trip, prefs, notes, provider, transaction)
    async with transaction() as session:
        ranked = {
            mode: await retrieval.ranked_shortlist(
                session,
                trip,
                prefs,
                [],
                meal_slots_per_day=len(request_builder.MEAL_SLOTS),
                retrieved=result,
            )
            for mode, result in (("vector", retrieved), ("lexical", None))
        }
        keys = await rag_service.document_keys(
            session, [c.document_id for c in retrieved.guide_passages]
        )
    selected = [keys[chunk.document_id] for chunk in retrieved.guide_passages]
    saved, supplied, items = await _grounded_plan(
        provider, settings, trip, prefs, ranked["vector"], retrieved
    )
    return {
        "query": number,
        "destination": query["destination"],
        "retrieval_mode": retrieved.mode,
        "recall_at_6": retrieval_metrics.recall_at_k(
            selected, query["relevant_guide_doc_keys"], GUIDE_K
        ),
        "place_hit_rate_vector": retrieval_metrics.place_hit_rate(
            [c.place.id for c in ranked["vector"]], relevant_places, PLACE_TOP
        ),
        "place_hit_rate_lexical": retrieval_metrics.place_hit_rate(
            [c.place.id for c in ranked["lexical"]], relevant_places, PLACE_TOP
        ),
        "citations_saved": len(saved),
        "citation_validity": retrieval_metrics.citation_validity(saved, supplied),
        "notes": sum(1 for note, _ in items if note.strip()),
        "grounding_rate": retrieval_metrics.grounding_rate(items),
    }


async def _grounded_plan(
    provider: ModelProvider,
    settings: Settings,
    trip: TripOut,
    prefs: PreferencesOut,
    shortlist: list[retrieval.Candidate],
    retrieved: rag_service.RetrievalResult,
) -> tuple[list[str], set[str], list[tuple[str, list[str]]]]:
    """Steps 5 to 9 as ``request_builder.build`` and ``pipeline.run`` do them, without saving:
    (saved citations, supplied passage IDs, (note, citations) per planned item)."""
    weekdays = [(trip.start_date + timedelta(days=d)).isoweekday() for d in range(trip.num_days)]
    request = request_builder.build_generation_request(
        trip,
        prefs,
        [],
        [],
        [
            request_builder.shortlist_place(
                PlaceSummary.from_row(c.place), request_builder.hours_summary(c.hours, weekdays)
            )
            for c in shortlist
        ],
        request_builder.RequestSettings(*GROUNDED_PROMPT, contingency_pct=CONTINGENCY_PCT),
    )
    grounded, _ = enforce_input_limit(
        request_builder.ground(request, retrieved),
        settings.ai_max_input_tokens,
        request_builder.passage_similarities(retrieved),
    )
    supplied = grounded.passage_ids()
    result = await provider.generate_itinerary(grounded)
    answer = output_check.apply_limits(
        result.output, trip_days=trip.num_days, max_items_per_day=grounded.limits.max_items_per_day
    )
    checked = output_check.check_output(answer, grounded.shortlist_ids(), trip.num_days, supplied)
    plan = await schedule.recalculate(
        checked.output.days,
        {str(place.place_id): place for place in grounded.shortlist},
        EstimateRouting(),
        grounded.preferences.pace,
        mode=grounded.preferences.transport_pref,
    )
    items = [(item.note, list(item.source_chunk_ids)) for day in plan for item in day.items]
    return [chunk_id for _, sources in items for chunk_id in sources], supplied, items


def summarise(scores: list[dict[str, Any]]) -> dict[str, Any]:
    """Means over the queries, per destination and overall; pooled counts for the citations."""

    def block(rows: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "queries": len(rows),
            **{
                name: retrieval_metrics.mean(row[name] for row in rows)
                for name in (
                    "recall_at_6",
                    "place_hit_rate_vector",
                    "place_hit_rate_lexical",
                    "grounding_rate",
                )
            },
            "citations_saved": sum(row["citations_saved"] for row in rows),
            "citation_validity": retrieval_metrics.mean(row["citation_validity"] for row in rows),
            "vector_mode_queries": sum(row["retrieval_mode"] == "vector" for row in rows),
        }

    slugs = sorted({row["destination"] for row in scores})
    return {
        "overall": block(scores),
        "by_destination": {
            slug: block([r for r in scores if r["destination"] == slug]) for slug in slugs
        },
        "per_query": scores,
    }


async def evaluate_retrieval(
    provider: ModelProvider, settings: Settings, queries: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    async with transaction() as session:
        destinations = {d.slug: d for d in await places_service.list_destinations(session)}
    return [
        await score_query(provider, settings, number, query, destinations)
        for number, query in enumerate(queries, 1)
    ]


def report(record: dict[str, Any]) -> str:
    lines = [
        f"# Retrieval evaluation {record['run_id']}",
        "",
        f"Dataset {record['dataset_version']} (sha256 {record['dataset_sha256'][:12]}), provider "
        f"{record['provider']}, embedding model {record['embedding_model_id']}, commit {record['git_commit']}.",
        "",
        "| Scope | Queries | recall@6 | Place hit rate (vector) | Place hit rate (lexical) "
        "| Citation validity | Grounding rate |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    m = record["metrics"]
    for name, row in [("overall", m["overall"]), *m["by_destination"].items()]:
        lines.append(
            f"| {name} | {row['queries']} | {row['recall_at_6']} | {row['place_hit_rate_vector']} "
            f"| {row['place_hit_rate_lexical']} | {row['citation_validity']} | {row['grounding_rate']} |"
        )
    return "\n".join(lines) + "\n"


def main_retrieval(args: argparse.Namespace, settings: Settings) -> int:
    started = datetime.now(UTC)
    try:
        dataset, queries = load_queries(DATASETS / args.dataset)
    except manifest.DatasetError as exc:
        print(exc, file=sys.stderr)
        return 1
    errors = guide_key_errors(queries, rag_service.data_root())
    if errors:
        print("unresolved labels: " + "; ".join(errors), file=sys.stderr)
        return 1
    provider = get_provider(settings.model_copy(update={"ai_provider": args.provider}))
    try:
        scores = asyncio.run(evaluate_retrieval(provider, settings, queries))
    except LabelError as exc:
        print(f"unresolved labels: {exc}", file=sys.stderr)
        return 1
    run_id = f"{started:%Y%m%dT%H%M%SZ}-retrieval-{args.provider.lower()}"
    out: Path = args.out or RESULTS / run_id
    record = {
        "run_id": run_id,
        "suite": "retrieval",
        "dataset_version": dataset["dataset_version"],
        "dataset_sha256": dataset["files"]["queries.jsonl"],
        "provider": args.provider,
        "model_id": provider.get_model_metadata().model_id,
        "embedding_model_id": provider.embedding_model_id or None,
        "prompt_template_id": GROUNDED_PROMPT[0],
        "prompt_version": GROUNDED_PROMPT[1],
        "trip_frame": {
            "start_date": TRIP_START.isoformat(),
            "num_days": TRIP_DAYS,
            "adults": TRIP_ADULTS,
            "children": 0,
            "budget": None,
            "contingency_pct": CONTINGENCY_PCT,
        },
        "k": {"guide_recall": GUIDE_K, "place_top": PLACE_TOP},
        "git_commit": manifest.git_commit(),
        "started_at": started.isoformat(),
        "ended_at": datetime.now(UTC).isoformat(),
        "metrics": summarise(scores),
    }
    _write(out / "run.json", record)
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / f"{run_id}.md").write_text(report(record), encoding="utf-8")
    print(f"evaluation {run_id}: {len(scores)} queries, written to {out}")
    return 0


def main(argv: list[str] | None = None, settings: Settings | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.evaluation.run")
    parser.add_argument("--dataset", required=True, help="<id>/<version>, e.g. trips/v1")
    parser.add_argument("--suite", choices=SUITES, default="generation")
    parser.add_argument("--provider", required=True, choices=PROVIDERS)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--out", type=Path, help="default eval/results/<run_id>/")
    args = parser.parse_args(argv)
    if args.suite == "retrieval":
        settings = settings or get_settings()
        reason = unavailable(args.provider, settings)
        if reason:
            print(reason, file=sys.stderr)
            return 2
        return main_retrieval(args, settings)

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
