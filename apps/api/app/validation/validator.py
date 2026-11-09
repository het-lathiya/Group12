"""validate(plan, ctx): every rule of ``app.validation.rules.RULES`` in their fixed order (IMP-404).

Pure: the caller loads the plan and the context; nothing here does I/O.
"""

from collections.abc import Sequence

from app.validation.rules import RULES, Finding, PlanDay, ValidationContext


def validate(plan: Sequence[PlanDay], ctx: ValidationContext) -> list[Finding]:
    return [found for rule in RULES for found in rule(plan, ctx)]
