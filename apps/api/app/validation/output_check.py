"""Step 8 of the pipeline: an answer against its schema, the shortlist and the trip (§8.11).

``apply_limits`` adds the limits that depend on the trip to the checks of the schema and classifies
a failure as ``ProviderInvalidOutput("schema_violation")``. ``check_output`` then rejects, item by
item, what the model may not choose, and removes citations of passages the request did not hold
(A1 §6.10): a citation never costs an item and has no finding code. ``summary`` gives the counts for
``ai_generations.validation_summary``. No text from the answer goes into a message or a count.
"""

from collections.abc import Set
from dataclasses import dataclass, field
from typing import Final

from pydantic import ValidationError

from app.ai.errors import InvalidOutputKind, ProviderInvalidOutput
from app.schemas.ai import MAX_SOURCE_IDS, GroundedItemOutput, ItineraryOutput, PlanFinding

UNKNOWN_PLACE_MESSAGE: Final = "This place is not in the shortlist of active places."
OUTSIDE_TRIP_MESSAGE: Final = "This day is outside the trip."


@dataclass(frozen=True)
class OutputCheckResult:
    output: ItineraryOutput  # what is left; days that lost every item are gone
    findings: list[PlanFinding] = field(default_factory=list)
    invalid_ids: int = 0
    rejected_items: int = 0
    unknown_source_ids: int = 0

    @property
    def usable(self) -> bool:
        """§8.12: at least one item and no UNKNOWN_PLACE or OUTSIDE_TRIP_DATES.

        A dropped duplicate has no finding code, so it leaves the plan usable.
        """
        return bool(self.output.days) and not self.findings


def apply_limits(
    output: ItineraryOutput, *, trip_days: int, max_items_per_day: int
) -> ItineraryOutput:
    context = {"trip_days": trip_days, "max_items_per_day": max_items_per_day}
    try:
        return type(output).model_validate(output.model_dump(), context=context)
    except ValidationError:
        raise ProviderInvalidOutput("schema_violation") from None


def _finding(code: str, message: str, day_number: int, position: int) -> PlanFinding:
    return PlanFinding.model_validate(
        {
            "code": code,
            "severity": "error",
            "day_number": day_number,
            "item_ref": f"d{day_number}-i{position}",
            "message": message,
        }
    )


def check_output(
    output: ItineraryOutput,
    shortlist_ids: Set[str],
    trip_days: int,
    passage_ids: Set[str] = frozenset(),
) -> OutputCheckResult:
    """Reject items on days outside the trip, unknown or inactive places and repeated places.

    ``shortlist_ids`` holds only places still active. The first occurrence of a place is kept. A
    kept item keeps at most three distinct citations from ``passage_ids``; the rest are counted.
    """
    findings: list[PlanFinding] = []
    seen: set[str] = set()
    days = []
    invalid_ids = rejected_items = unknown_source_ids = 0
    for day in output.days:
        kept = []
        for position, item in enumerate(day.items, start=1):
            if day.day_number > trip_days:
                findings.append(
                    _finding("OUTSIDE_TRIP_DATES", OUTSIDE_TRIP_MESSAGE, day.day_number, position)
                )
            elif item.place_id not in shortlist_ids:
                invalid_ids += 1
                findings.append(
                    _finding("UNKNOWN_PLACE", UNKNOWN_PLACE_MESSAGE, day.day_number, position)
                )
            elif item.place_id not in seen:
                seen.add(item.place_id)
                if isinstance(item, GroundedItemOutput):
                    cited = [i for i in dict.fromkeys(item.source_ids) if i in passage_ids]
                    cited = cited[:MAX_SOURCE_IDS]
                    unknown_source_ids += len(item.source_ids) - len(cited)
                    item = item.model_copy(update={"source_ids": cited})
                kept.append(item)
                continue
            rejected_items += 1
        if kept:
            days.append(day.model_copy(update={"items": kept}))
    return OutputCheckResult(
        output.model_copy(update={"days": days}),
        findings,
        invalid_ids,
        rejected_items,
        unknown_source_ids,
    )


def summary(
    result: OutputCheckResult | None = None, kind: InvalidOutputKind | None = None
) -> dict[str, object]:
    """The record of step 8; ``kind`` is set when the whole answer was refused."""
    return {
        "errors": len(result.findings) if result else 0,
        "warnings": 0,
        "infos": 0,
        "invalid_ids": result.invalid_ids if result else 0,
        "rejected_items": result.rejected_items if result else 0,
        "unknown_source_ids": result.unknown_source_ids if result else 0,
        "kind": kind,
    }
