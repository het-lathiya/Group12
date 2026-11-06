"""Guide files: flat front matter, body and the quality gate (Amendment A1 §6.3, IMD-111). Pure.

``check_guide`` returns the guide, or None when it has an error, with its findings. Each finding
names a file, a line and a rule and never quotes the guide. The content patterns are warnings, and
errors with ``strict``.
"""

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from typing import Final, Literal

from app.rag.constants import GUIDE_MAX_CHARS, GUIDE_MIN_CHARS

FIELDS: Final = frozenset(
    {
        "title",
        "source_name",
        "source_type",
        "url",
        "licence",
        "attribution_text",
        "retrieved_on",
        "curated_by",
    }
)
SOURCE_TYPES: Final = frozenset({"official_site", "curated_manual", "other"})
NAME_MAX: Final = 120
SAMPLE_PREFIX: Final = "SAMPLE"
SAMPLE_LICENCE: Final = "synthetic test data"
_FENCE: Final = "---"
_CODES: Final = r"(?:Rs\.?|INR|USD|EUR|GBP|AED|AUD|CAD|CHF|CNY|JPY|SGD)"
_CONTENT_RULES: Final = (
    (
        "currency_amount",
        re.compile(rf"[₹$€£]\s?\d|\d\s?[₹$€£]|\b{_CODES}\s?\d|\d\s?{_CODES}(?!\w)", re.IGNORECASE),
    ),
    (
        "clock_time_range",
        re.compile(r"\b\d{1,2}:\d{2}\s*(?:-|\u2013|\u2014|to)\s*\d{1,2}:\d{2}\b", re.IGNORECASE),
    ),
    (
        "hours_or_travel_phrase",
        re.compile(r"open daily|opening hours|closed on|minutes by", re.IGNORECASE),
    ),
)

Severity = Literal["error", "warning"]


@dataclass(frozen=True)
class GuideFinding:
    file: str
    line: int
    severity: Severity
    rule: str


@dataclass(frozen=True)
class Guide:
    file: str
    title: str
    source_name: str
    source_type: str
    url: str | None
    licence: str
    attribution_text: str | None
    retrieved_on: date
    curated_by: str
    body: str
    licence_line: int


def _split(
    file: str, text: str
) -> tuple[dict[str, str], dict[str, int], str, int, list[GuideFinding]]:
    """Front matter values, their lines, the body and its first line, and the format errors."""
    lines = text.splitlines()
    closing = next(
        (number for number, line in enumerate(lines[1:], 1) if line.strip() == _FENCE), None
    )
    if not lines or lines[0].strip() != _FENCE or closing is None:
        return {}, {}, "", 1, [GuideFinding(file, 1, "error", "front_matter_missing")]

    values: dict[str, str] = {}
    where: dict[str, int] = {}
    findings: list[GuideFinding] = []
    for number, line in enumerate(lines[1:closing], 2):
        key, colon, value = line.partition(":")
        if not line.strip():
            continue
        if not colon or key != key.strip() or key not in FIELDS or key in values:
            findings.append(GuideFinding(file, number, "error", "front_matter_line"))
            continue
        values[key], where[key] = value.strip(), number
    rest = lines[closing + 1 :]
    blank = next((number for number, line in enumerate(rest) if line.strip()), len(rest))
    return values, where, "\n".join(rest[blank:]).strip(), closing + 2 + blank, findings


def _retrieved_on(value: str, today: date) -> date | None:
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed <= today and len(value) == len("YYYY-MM-DD") else None


def _field_rules(values: Mapping[str, str], today: date) -> list[tuple[str, str]]:
    """(field, rule) for every field that is missing or invalid."""
    problems: list[tuple[str, str]] = []
    for name in ("title", "source_name"):
        if not 1 <= len(values.get(name, "")) <= NAME_MAX:
            problems.append((name, f"{name}_invalid"))
    if values.get("source_type") not in SOURCE_TYPES:
        problems.append(("source_type", "source_type_invalid"))
    url = values.get("url", "")
    if url and not url.startswith("https://"):
        problems.append(("url", "url_not_https"))
    if not url and values.get("source_type") != "curated_manual":
        problems.append(("url", "url_missing"))
    licence = values.get("licence", "")
    if not licence:
        problems.append(("licence", "licence_missing"))
    if licence.upper().startswith("CC BY") and not values.get("attribution_text"):
        problems.append(("attribution_text", "attribution_missing"))
    if _retrieved_on(values.get("retrieved_on", ""), today) is None:
        problems.append(("retrieved_on", "retrieved_on_invalid"))
    if not values.get("curated_by"):
        problems.append(("curated_by", "curated_by_missing"))
    return problems


def _sample_rules(values: Mapping[str, str], sample_allowed: bool) -> list[tuple[str, str]]:
    """IMD-15: SAMPLE text is labelled as such and exists only in local and test."""
    problems: list[tuple[str, str]] = []
    if not sample_allowed:
        problems.append(("title", "sample_not_allowed"))
    for name in ("title", "source_name"):
        if not values.get(name, "").startswith(SAMPLE_PREFIX):
            problems.append((name, "sample_label_missing"))
    if values.get("source_type") != "curated_manual" or values.get("url"):
        problems.append(("source_type", "sample_source_invalid"))
    if values.get("licence") != SAMPLE_LICENCE:
        problems.append(("licence", "sample_source_invalid"))
    return problems


def check_guide(
    file: str,
    text: str,
    *,
    today: date,
    strict: bool = False,
    sample_fixture: bool = False,
    sample_allowed: bool = False,
) -> tuple[Guide | None, list[GuideFinding]]:
    values, where, body, body_line, findings = _split(file, text)
    if not values and findings:
        return None, findings

    problems = _field_rules(values, today)
    labelled = any(
        values.get(name, "").startswith(SAMPLE_PREFIX) for name in ("title", "source_name")
    )
    if sample_fixture or labelled:
        problems += _sample_rules(values, sample_allowed)
    findings += [GuideFinding(file, where.get(name, 1), "error", rule) for name, rule in problems]

    if not GUIDE_MIN_CHARS <= len(body) <= GUIDE_MAX_CHARS:
        findings.append(GuideFinding(file, body_line, "error", "body_length"))

    severity: Severity = "error" if strict else "warning"
    for number, line in enumerate(body.splitlines(), body_line):
        findings += [
            GuideFinding(file, number, severity, rule)
            for rule, pattern in _CONTENT_RULES
            if pattern.search(line)
        ]

    if any(finding.severity == "error" for finding in findings):
        return None, findings
    guide = Guide(
        file=file,
        title=values["title"],
        source_name=values["source_name"],
        source_type=values["source_type"],
        url=values.get("url") or None,
        licence=values["licence"],
        attribution_text=values.get("attribution_text") or None,
        retrieved_on=date.fromisoformat(values["retrieved_on"]),
        curated_by=values["curated_by"],
        body=body,
        licence_line=where["licence"],
    )
    return guide, findings


def check_sources(
    guides: Iterable[Guide], existing: Mapping[str, tuple[str, str | None]]
) -> tuple[list[Guide], list[GuideFinding]]:
    """One source name, one licence and attribution text; each page URL may differ (A1 §6.3)."""
    terms = dict(existing)
    kept: list[Guide] = []
    findings: list[GuideFinding] = []
    for guide in guides:
        wanted = (guide.licence, guide.attribution_text)
        if terms.setdefault(guide.source_name, wanted) == wanted:
            kept.append(guide)
        else:
            findings.append(GuideFinding(guide.file, guide.licence_line, "error", "source_terms"))
    return kept, findings
