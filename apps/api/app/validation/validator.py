"""validate(plan, ctx): every rule of ``app.validation.rules.RULES`` in their fixed order (IMP-404).

Every finding leaves with a suggested fix (FR-056, IMP-405): a rule's own, more specific fix wins;
otherwise the catalogue's for its code. ``summary`` counts findings for validation_summary.
Pure: the caller loads the plan and the context; nothing here does I/O.
"""

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Final

from app.schemas.ai import FindingCode
from app.validation.rules import RULES, Finding, PlanDay, ValidationContext

# One suggested action per §8.12 code (FR-056 AC1).
SUGGESTED_FIXES: Final[Mapping[FindingCode, str]] = {
    "OVERLAP": "Move the later item to after the earlier one ends plus travel, or swap the two.",
    "TRANSFER_TOO_SHORT": "Start the later item later, or shorten the visit before it.",
    "CLOSED_ON_DAY": "Move this item to a day when the place is open.",
    "OUTSIDE_HOURS": "Move this item into the place's opening hours.",
    "HOURS_UNVERIFIED": "Check opening times before the visit.",
    "DAY_TOO_LONG": "Move or remove an item, or choose a slower pace.",
    "BUDGET_EXCEEDED": "Remove or replace a costly item, or raise the budget.",
    "BUDGET_NEAR": "Keep an eye on extra spending; the plan is close to the budget.",
    "MUST_VISIT_MISSING": "Add it to a day with room, or remove it from the must-visit list.",
    "UNKNOWN_PLACE": "Remove this item or replace it with an active place.",
    "OUTSIDE_TRIP_DATES": "Move this item to a day of the trip or change the trip dates.",
    "COST_INCOMPLETE": "Treat the total as a lower bound; some prices are unknown.",
    "ESTIMATE_USED": "Check the estimated price before you go.",
}

SEVERITY_KEYS: Final = {"error": "errors", "warning": "warnings", "info": "infos"}


def validate(plan: Sequence[PlanDay], ctx: ValidationContext) -> list[Finding]:
    return [
        found
        if found.suggested_fix
        else found.model_copy(update={"suggested_fix": SUGGESTED_FIXES[found.code]})
        for rule in RULES
        for found in rule(plan, ctx)
    ]


def summary(findings: Sequence[Finding]) -> dict[str, int]:
    """{errors, warnings, infos}: the counts of validation_summary (§6.5)."""
    counts = Counter(SEVERITY_KEYS[found.severity] for found in findings)
    return {key: counts[key] for key in SEVERITY_KEYS.values()}
