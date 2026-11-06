"""The retrieval query text (Amendment A1 §6.7; IMP-315)."""

from typing import Any

from app.rag.constants import RAG_QUERY_MAX_CHARS
from app.rag.query import build_query_text

TRIP: dict[str, Any] = {
    "destination": "Sampleton",
    "interests": ["museum", "food"],
    "pace": "relaxed",
    "budget_priority": "saving",
    "transport": "walking",
    "group_needs": [],
    "step_free": False,
    "notes_quoted": None,
}


def test_the_text_has_the_lines_of_section_6_7_in_order() -> None:
    assert build_query_text(**TRIP | {"notes_quoted": "Quiet mornings"}).splitlines() == [
        "Destination: Sampleton.",
        "Interests: museum, food.",
        "Pace: relaxed.",
        "Budget priority: saving.",
        "Transport: walking.",
        "Travelling with: adults only.",
        "Step-free access needed: no.",
        "Notes: Quiet mornings.",
    ]


def test_group_needs_step_free_and_no_notes() -> None:
    lines = build_query_text(
        **TRIP | {"group_needs": ["seniors", "toddlers"], "step_free": True}
    ).splitlines()
    assert "Travelling with: seniors, toddlers." in lines
    assert "Step-free access needed: yes." in lines
    assert not any(line.startswith("Notes:") for line in lines)


def test_the_text_is_cut_and_deterministic() -> None:
    long = TRIP | {"notes_quoted": "river " * 400}
    assert len(build_query_text(**long)) == RAG_QUERY_MAX_CHARS
    assert build_query_text(**long) == build_query_text(**long)
