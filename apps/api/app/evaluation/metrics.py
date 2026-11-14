"""Versioned metric definitions of the evaluation harness (MOD-B15, FR-119; IMP-413).

One function scores every provider, and it takes no provider argument (FR-119 AC2, TC-286). The
definitions are written out in ``eval/metrics_v1.md``; its SHA-256 goes into each run record.

The numbered metrics 1 to 13 are those of blueprint §21.4, which is not in the repository
(PD-IMP-310-1, PD-IMP-413-3), so their definitions cannot be copied: every one is reported as not
computed in v1 rather than given an invented definition. The ``counts`` use only rules the
specification states exactly (§8.11, §8.12), each as k of n attempts.
"""

from collections.abc import Mapping, Sequence
from typing import Any, Final

METRICS_VERSION: Final = "v1"

BLUEPRINT_MISSING: Final = "not computed in v1: blueprint §21.4 is not in the repository"
NUMBERED: Final[Mapping[int, str]] = {
    **dict.fromkeys((1, 2, 3, 4, 5, 6, 10, 11, 13), BLUEPRINT_MISSING),
    7: "not computed in v1 (IMP-413 card)",
    8: "Release 2 (§8.17)",
    9: "not computed in v1 (IMP-413 card)",
    12: "null: no dated price table exists (§8.16)",
}

# name -> the per-attempt score field that must be True.
COUNTS: Final[Mapping[str, str]] = {
    "schema_valid": "schema_valid",  # §8.11 step 1: parsed and validated as io-1 with its limits
    "place_ids_valid": "place_ids_valid",  # §8.11 step 3: no UNKNOWN_PLACE
    "usable": "usable",  # §8.12: at least one item and no blocking finding
}


def compute(scores: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """The v1 metrics of a run from its per-attempt scores."""
    n = len(scores)
    days = [minutes for s in scores for minutes in s.get("daily_travel_min", [])]
    return {
        "metrics_version": METRICS_VERSION,
        "attempts": n,
        # FR-030 AC2: mean over every planned day of all attempts of its summed travel minutes.
        "avg_daily_travel_min": round(sum(days) / len(days), 1) if days else None,
        "counts": {
            name: {"k": sum(1 for s in scores if s[field] is True), "n": n}
            for name, field in COUNTS.items()
        },
        "numbered": {
            str(number): {"value": None, "status": NUMBERED[number]} for number in NUMBERED
        },
    }
