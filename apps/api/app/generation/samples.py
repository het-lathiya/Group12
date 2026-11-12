"""Saved sample itineraries (§8.15, FR-036 AC3; IMP-402, IMD-145).

Two io-1 itineraries per demo destination, built once by the rule-based planner from frozen SAMPLE
trips (scripts/build_sample_itineraries.py) and stored as JSON under
``data/fixtures/<slug>/sample_itineraries/`` or ``data/places/<slug>/sample_itineraries/``. Place
IDs change on every reseed, so each item names its place by ``{source_name, external_ref}``;
loading resolves them to the current active place IDs, parses io-1, recalculates the times
(step 9, distance estimate, no network) and runs ``validate()``. A reference that does not resolve
raises; an item is never dropped. Samples are labelled SAMPLE and built without AI.
"""

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Final, Literal

from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.generation import schedule
from app.itinerary.schemas import PlannedDay
from app.places import service as places_service
from app.places.schemas import PlaceSummary
from app.routing.estimate import TravelEstimate, TravelMode
from app.routing.service import RoutablePlace, travel_time
from app.schemas.ai import ItineraryOutput
from app.validation.rules import Finding, ValidationContext
from app.validation.validator import validate

REPO_ROOT: Final = Path(__file__).resolve().parents[4]
SAMPLE_ROOTS: Final = (REPO_ROOT / "data" / "fixtures", REPO_ROOT / "data" / "places")
SAMPLE_DIR: Final = "sample_itineraries"
SLUG: Final = re.compile(r"[a-z0-9][a-z0-9-]*")

Ref = tuple[str, str]


class SampleNotFoundError(Exception):
    """No saved sample of that name for that destination slug."""


class UnresolvedPlaceRefError(Exception):
    """A sample names a place that is missing or inactive in the database."""

    def __init__(self, slug: str, name: str, refs: list[Ref]) -> None:
        listed = ", ".join(f"{source}/{ref}" for source, ref in refs)
        super().__init__(f"sample {name!r} of {slug!r}: no active place for {listed}")
        self.refs = refs


class SampleTrip(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    start_date: date
    end_date: date
    pace: str
    transport_pref: str


class SampleFile(BaseModel):
    """The stored file: io-1 with ``place_ref`` where io-1 has ``place_id``."""

    model_config = ConfigDict(extra="forbid")

    label: Literal["SAMPLE"]
    origin: Literal["fallback_rule_based"]
    model_id: Literal["rule_based_planner_v1"]
    destination_slug: str
    trip: SampleTrip
    itinerary: dict[str, Any]


@dataclass(frozen=True)
class LoadedSample:
    name: str
    sample: SampleFile
    output: ItineraryOutput
    plan: list[PlannedDay]
    findings: list[Finding]


class _EstimatedRouting:
    """Step 9 with the labelled distance estimate only: samples are for the offline demo."""

    async def travel(
        self, origin: RoutablePlace, target: RoutablePlace, mode: TravelMode | str
    ) -> TravelEstimate:
        return await travel_time(origin, target, mode)


def _directory(slug: str) -> Path | None:
    if not SLUG.fullmatch(slug):
        return None
    return next((d for root in SAMPLE_ROOTS if (d := root / slug / SAMPLE_DIR).is_dir()), None)


def list_samples(destination_slug: str) -> list[str]:
    directory = _directory(destination_slug)
    return sorted(path.stem for path in directory.glob("*.json")) if directory else []


def _ref(item: dict[str, Any]) -> Ref:
    place_ref = item["place_ref"]
    return (place_ref["source_name"], place_ref["external_ref"])


async def load_sample(session: AsyncSession, destination_slug: str, name: str) -> LoadedSample:
    """Raises ``SampleNotFoundError`` or ``UnresolvedPlaceRefError``; returns every finding."""
    directory = _directory(destination_slug)
    if directory is None or name not in list_samples(destination_slug):
        raise SampleNotFoundError(f"no sample {name!r} for {destination_slug!r}")
    raw = json.loads((directory / f"{name}.json").read_text(encoding="utf-8"))
    sample = SampleFile.model_validate(raw)
    days = sample.itinerary["days"]
    refs = [_ref(item) for day in days for item in day["items"]]

    places = await places_service.active_places_by_refs(session, destination_slug, refs)
    missing = [ref for ref in dict.fromkeys(refs) if ref not in places]
    if missing:
        raise UnresolvedPlaceRefError(destination_slug, name, missing)

    resolved_days = [
        {
            **day,
            "items": [
                {"place_id": str(places[_ref(item)].id)}
                | {key: value for key, value in item.items() if key != "place_ref"}
                for item in day["items"]
            ],
        }
        for day in days
    ]
    output = ItineraryOutput.model_validate({**sample.itinerary, "days": resolved_days})
    by_id: dict[str, PlaceSummary] = {str(place.id): place for place in places.values()}
    plan = await schedule.recalculate(
        output.days,
        by_id,
        _EstimatedRouting(),
        sample.trip.pace,
        mode=sample.trip.transport_pref,
    )
    ctx = ValidationContext(
        start_date=sample.trip.start_date,
        end_date=sample.trip.end_date,
        places={place_id: place.name for place_id, place in by_id.items()},
    )
    return LoadedSample(name, sample, output, plan, validate(plan, ctx))
