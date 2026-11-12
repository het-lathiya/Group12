"""How a generation ends after a provider failure (blueprint §19.2.2, §6.4, §8.3; IMP-403).

``resolve`` is the one outcome table, and the pipeline asks it what to do with any failure:

- timeout, rate limit or outage after the adapter's retries, or a breaker opened by them: the
  rule-based plan, with the cause in validation_summary.provider_failure and failure_reason
  null (IMD-22);
- an unusable answer (ProviderInvalidOutput, a step-8 refusal): the rule-based plan,
  invalid_output (``INVALID_OUTPUT``);
- still unusable after the repair call (IMP-502): the rule-based plan, unresolved_validation
  (``UNRESOLVED``);
- quota exhausted, or a breaker opened by quota: failed, provider_quota_exhausted, no fallback
  (IMD-44);
- an auth error or a bad request, or a breaker opened by auth: failed, config_error, no fallback;
- anything else: failed, internal (``INTERNAL``).

``MESSAGES`` maps a failure_reason to the user message and next action of API-23 (§6.4). The
text is fixed here, never taken from the error, so no vendor text reaches a response (NFR-024).
Pure: no I/O.
"""

from dataclasses import dataclass
from typing import Final, Literal

from app.ai.errors import ProviderError, ProviderFailureReason, ProviderInvalidOutput
from app.generation.records import FailureReason

NextAction = Literal["retry_rule_based", "edit_trip", "retry"]

NO_FALLBACK: Final[frozenset[str]] = frozenset({"provider_quota_exhausted", "config_error"})


@dataclass(frozen=True)
class Outcome:
    """``fallback``: build the rule-based plan with ``reason`` as its cause; ``failed``: end the
    generation failed with ``reason`` and write nothing to the itinerary tables."""

    kind: Literal["fallback", "failed"]
    reason: FailureReason


INVALID_OUTPUT: Final = Outcome("fallback", "invalid_output")
UNRESOLVED: Final = Outcome("fallback", "unresolved_validation")
INTERNAL: Final = Outcome("failed", "internal")


def resolve(error: BaseException) -> Outcome:
    if isinstance(error, ProviderInvalidOutput):
        return INVALID_OUTPUT
    if not isinstance(error, ProviderError):
        return INTERNAL
    if error.retryable:  # the adapter has spent its retries (§8.3)
        return Outcome("fallback", error.failure_reason)
    if error.failure_reason in NO_FALLBACK:
        return Outcome("failed", error.failure_reason)
    return INTERNAL


def resolve_open_breaker(open_reason: ProviderFailureReason) -> Outcome:
    """Step 7 skipped: a quota or auth breaker keeps its failed cause (IMD-44)."""
    return Outcome("failed" if open_reason in NO_FALLBACK else "fallback", open_reason)


# §6.4: failure_reason -> (failure_message, next_action).
MESSAGES: Final[dict[str, tuple[str, NextAction]]] = {
    "provider_timeout": ("The AI service did not return a usable plan.", "retry_rule_based"),
    "provider_rate_limited": ("The AI service did not return a usable plan.", "retry_rule_based"),
    "provider_unavailable": ("The AI service did not return a usable plan.", "retry_rule_based"),
    "invalid_output": ("The AI service did not return a usable plan.", "retry_rule_based"),
    "provider_quota_exhausted": ("AI generation is paused for today.", "retry_rule_based"),
    "unresolved_validation": (
        "No plan satisfied the checks; adjust the trip or must-visit places.",
        "edit_trip",
    ),
    "config_error": ("The AI service is not available right now.", "retry_rule_based"),
    "internal": ("Something went wrong on our side.", "retry"),
}
