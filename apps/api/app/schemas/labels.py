"""Source labels (§6.1 Labels, §7.8; FR-076, IMP-411).

Every price and opening-hours value carries exactly one of these labels. Nothing in the MVP is
labelled live or verified, and the enum makes that impossible to serialise. A curated price has
no date (IMD-130); curated opening hours keep their ``hours_checked_on`` date.

Cost breakdown lines built from the traveller's own figures use the separate line label
``traveller_input`` (budget/schemas.py ``CategoryCostLine``, IMP-308); it is not a source label.
"""

from enum import StrEnum


class SourceLabel(StrEnum):
    """price_label and hours_label (§6.1 Labels)."""

    CURATED = "curated"
    ESTIMATE = "estimate"
    UNAVAILABLE = "unavailable"


SOURCE_LABELS: frozenset[str] = frozenset(label.value for label in SourceLabel)
