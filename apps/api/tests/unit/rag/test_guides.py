"""TC-448: the guide file format and quality gate (Amendment A1 §6.3, IMD-111)."""

from datetime import date
from pathlib import Path

import pytest

from app.rag.guides import Guide, GuideFinding, check_guide, check_sources

TODAY = date(2026, 11, 6)
FILE = "guides/example/walking.md"
BODY = "## Walking\n\n" + "The old quarter is compact and easy to explore on foot. " * 8
SAMPLES = Path(__file__).resolve().parents[5] / "data" / "fixtures" / "sampleton" / "guides"
FIELDS = {
    "title": "Getting around",
    "source_name": "Wikivoyage",
    "source_type": "other",
    "url": "https://en.wikivoyage.org/wiki/Example",
    "licence": "CC BY-SA 4.0",
    "attribution_text": "Adapted from Wikivoyage, CC BY-SA 4.0.",
    "retrieved_on": "2026-11-01",
    "curated_by": "A Member",
}


def text(body: str = BODY, **changes: str | None) -> str:
    fields = {**FIELDS, **changes}
    lines = [f"{key}: {value}" for key, value in fields.items() if value is not None]
    return "\n".join(["---", *lines, "---", "", body])


def rules(content: str, **options: bool) -> list[str]:
    return [finding.rule for finding in check_guide(FILE, content, today=TODAY, **options)[1]]


def passed(content: str = "", file: str = FILE) -> Guide:
    guide, findings = check_guide(file, content or text(), today=TODAY)
    assert findings == []
    assert guide is not None
    return guide


def test_tc_448_a_good_guide_passes_with_every_field_read() -> None:
    guide = passed()

    assert guide.title == "Getting around"
    assert guide.url == FIELDS["url"]
    assert guide.retrieved_on == date(2026, 11, 1)
    assert guide.body.startswith("## Walking")


@pytest.mark.parametrize(
    ("change", "rule"),
    [
        ({"title": None}, "title_invalid"),
        ({"title": "x" * 121}, "title_invalid"),
        ({"source_name": None}, "source_name_invalid"),
        ({"source_type": "osm_import"}, "source_type_invalid"),
        ({"url": None}, "url_missing"),
        ({"url": "http://example.org/page"}, "url_not_https"),
        ({"licence": None}, "licence_missing"),
        ({"attribution_text": None}, "attribution_missing"),
        ({"retrieved_on": None}, "retrieved_on_invalid"),
        ({"retrieved_on": "01-11-2026"}, "retrieved_on_invalid"),
        ({"retrieved_on": "2026-11-07"}, "retrieved_on_invalid"),
        ({"curated_by": None}, "curated_by_missing"),
    ],
)
def test_tc_448_a_missing_or_invalid_field_is_an_error(
    change: dict[str, str | None], rule: str
) -> None:
    guide, findings = check_guide(FILE, text(**change), today=TODAY)

    assert guide is None
    assert rule in [finding.rule for finding in findings]
    assert {finding.severity for finding in findings} == {"error"}


def test_tc_448_a_curated_manual_guide_needs_no_url_and_a_licence_may_need_no_attribution() -> None:
    guide = passed(
        text(
            source_type="curated_manual",
            url=None,
            licence="Team-written summary",
            attribution_text=None,
        )
    )

    assert guide.url is None
    assert guide.attribution_text is None


@pytest.mark.parametrize("body", ["## Short\n\nToo short.", "## Long\n\n" + "word " * 1300])
def test_tc_448_a_body_outside_the_limits_is_an_error(body: str) -> None:
    assert rules(text(body)) == ["body_length"]


@pytest.mark.parametrize(
    "content",
    ["no front matter here", "---\ntitle: never closed\n", "---\n---\n"],
)
def test_tc_448_broken_front_matter_is_an_error(content: str) -> None:
    assert check_guide(FILE, content, today=TODAY)[0] is None


@pytest.mark.parametrize(
    "line", ["  nested: value", "no colon here", "unknown_field: value", "title: twice"]
)
def test_tc_448_only_flat_known_keys_are_allowed_and_the_finding_has_its_line(line: str) -> None:
    content = text().replace("---\n\n", f"{line}\n---\n\n", 1)

    _, findings = check_guide(FILE, content, today=TODAY)

    assert GuideFinding(FILE, 10, "error", "front_matter_line") in findings


@pytest.mark.parametrize(
    ("line", "rule"),
    [
        ("A thali costs ₹250 here.", "currency_amount"),
        ("Entry is 50 INR.", "currency_amount"),
        ("Tickets are Rs 40.", "currency_amount"),
        ("About USD 10 a day.", "currency_amount"),
        ("Around €5 for a coffee.", "currency_amount"),
        ("It runs 10:00 to 17:30 each week.", "clock_time_range"),
        ("Gates work 09:00-18:00.", "clock_time_range"),
        ("The museum is open daily.", "hours_or_travel_phrase"),
        ("Check the Opening Hours first.", "hours_or_travel_phrase"),
        ("It is closed on Mondays.", "hours_or_travel_phrase"),
        ("It is 20 minutes by bus.", "hours_or_travel_phrase"),
    ],
)
def test_tc_448_content_patterns_warn_and_fail_only_with_strict(line: str, rule: str) -> None:
    content = text(f"{BODY}\n\n{line}")

    guide, findings = check_guide(FILE, content, today=TODAY)
    assert guide is not None
    assert [(finding.rule, finding.severity) for finding in findings] == [(rule, "warning")]

    guide, findings = check_guide(FILE, content, today=TODAY, strict=True)
    assert guide is None
    assert [(finding.rule, finding.severity) for finding in findings] == [(rule, "error")]


def test_tc_448_a_content_finding_names_its_line_and_never_quotes_the_guide() -> None:
    content = text(f"{BODY}\n\nIt costs ₹250.")
    line = content.splitlines().index("It costs ₹250.") + 1

    _, [finding] = check_guide(FILE, content, today=TODAY)

    assert (finding.file, finding.line) == (FILE, line)
    assert "250" not in str(finding)


@pytest.mark.parametrize(
    "line", ["The tram opened in 1920.", "Route 7 follows the river.", "NH 8 runs north."]
)
def test_ordinary_numbers_are_not_flagged(line: str) -> None:
    assert rules(text(f"{BODY}\n\n{line}")) == []


def test_tc_448_two_pages_of_one_source_with_different_urls_pass() -> None:
    first = passed(text(url="https://en.wikivoyage.org/wiki/One"), "one.md")
    second = passed(text(url="https://en.wikivoyage.org/wiki/Two"), "two.md")

    kept, findings = check_sources(
        [first, second], {"Wikivoyage": ("CC BY-SA 4.0", FIELDS["attribution_text"])}
    )

    assert kept == [first, second]
    assert findings == []


def test_tc_448_a_different_licence_for_a_stored_source_fails() -> None:
    guide = passed()

    kept, [finding] = check_sources([guide], {"Wikivoyage": ("CC0", None)})

    assert kept == []
    assert (finding.rule, finding.severity, finding.line) == ("source_terms", "error", 6)


def test_tc_448_a_different_attribution_between_two_guides_fails_the_second() -> None:
    first = passed(file="one.md")
    second = passed(text(attribution_text="Something else."), "two.md")

    kept, findings = check_sources([first, second], {})

    assert kept == [first]
    assert [finding.file for finding in findings] == ["two.md"]


def sample_text(**changes: str | None) -> str:
    return text(
        **{
            "title": "SAMPLE walking",
            "source_name": "SAMPLE guides",
            "source_type": "curated_manual",
            "url": None,
            "licence": "synthetic test data",
            "attribution_text": None,
            **changes,
        }
    )


def test_a_sample_guide_passes_only_where_samples_are_allowed() -> None:
    allowed = check_guide(
        FILE, sample_text(), today=TODAY, sample_fixture=True, sample_allowed=True
    )
    refused = check_guide(FILE, sample_text(), today=TODAY, sample_fixture=True)

    assert allowed[0] is not None
    assert refused[0] is None
    assert [finding.rule for finding in refused[1]] == ["sample_not_allowed"]


def test_a_guide_labelled_sample_is_refused_outside_the_fixture_too() -> None:
    assert "sample_not_allowed" in rules(sample_text())


@pytest.mark.parametrize(
    ("change", "rule"),
    [
        ({"title": "Walking"}, "sample_label_missing"),
        ({"source_name": "Guides"}, "sample_label_missing"),
        ({"source_type": "other", "url": "https://example.org/a"}, "sample_source_invalid"),
        ({"licence": "CC0"}, "sample_source_invalid"),
    ],
)
def test_a_sample_fixture_guide_must_be_labelled_as_one(
    change: dict[str, str | None], rule: str
) -> None:
    found = rules(sample_text(**change), sample_fixture=True, sample_allowed=True)

    assert found == [rule]


@pytest.mark.parametrize("path", sorted(SAMPLES.glob("*.md")), ids=lambda path: path.stem)
def test_the_three_sample_guides_pass_the_strict_gate(path: Path) -> None:
    guide, findings = check_guide(
        path.name,
        path.read_text(encoding="utf-8"),
        today=TODAY,
        strict=True,
        sample_fixture=True,
        sample_allowed=True,
    )

    assert findings == []
    assert guide is not None
    assert guide.url is None


def test_there_are_exactly_three_sample_guides() -> None:
    assert sorted(path.stem for path in SAMPLES.glob("*.md")) == [
        "food-culture",
        "getting-around",
        "local-customs",
    ]
