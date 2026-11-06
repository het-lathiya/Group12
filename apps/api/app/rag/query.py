"""The retrieval query text (Amendment A1 §6.7). Pure: no I/O and no framework imports.

Built from the trip's own data only, once per generation. ``notes_quoted`` is already redacted by
``request_builder.quote_notes`` (§8.6). The text is never logged or stored.
"""

from collections.abc import Sequence

from app.rag.constants import RAG_QUERY_MAX_CHARS


def build_query_text(
    *,
    destination: str,
    interests: Sequence[str],
    pace: str,
    budget_priority: str,
    transport: str,
    group_needs: Sequence[str],
    step_free: bool,
    notes_quoted: str | None,
) -> str:
    lines = [
        f"Destination: {destination}.",
        f"Interests: {', '.join(interests)}.",
        f"Pace: {pace}.",
        f"Budget priority: {budget_priority}.",
        f"Transport: {transport}.",
        f"Travelling with: {', '.join(group_needs) or 'adults only'}.",
        f"Step-free access needed: {'yes' if step_free else 'no'}.",
    ]
    if notes_quoted:
        lines.append(f"Notes: {notes_quoted}.")
    return "\n".join(lines)[:RAG_QUERY_MAX_CHARS]
