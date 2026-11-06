"""Prompt size control (§8.6; FR-039, IMP-303).

Tokens are estimated at 4 characters each, the conservative default of §8.6, until the live key
lets the provider's token counter replace it. ``enforce_input_limit`` cuts the shortlist by rank;
the pipeline records the count as ``truncated_count`` in generation_settings (IMP-305).
"""

import math
from typing import Final

from app.ai.errors import ProviderBadRequest
from app.ai.prompts import registry
from app.schemas.ai import GenerationRequest, ShortlistPlace

CHARS_PER_TOKEN: Final = 4
FOOD_CATEGORY: Final = "food"


def estimate_tokens(request: GenerationRequest) -> int:
    """The estimated size of the rendered prompt, system and user text together."""
    system_text, user_text = registry.render(
        request.prompt_template_id, request.prompt_version, request
    )
    return math.ceil((len(system_text) + len(user_text)) / CHARS_PER_TOKEN)


def _droppable(request: GenerationRequest) -> list[ShortlistPlace]:
    """The shortlist entries that may go, lowest-ranked first."""
    kept = {*request.must_visit_place_ids, *(item.place_id for item in request.locked_items)}
    days = 1 if request.scope.kind == "day" else request.trip.num_days
    food_needed = days * len(request.limits.meal_slots)
    droppable = []
    # Best first, so the food places the meal slots need are the best-ranked ones.
    for place in request.shortlist:
        if place.place_id in kept:
            food_needed -= place.category == FOOD_CATEGORY
    for place in request.shortlist:
        if place.place_id in kept:
            continue
        if place.category == FOOD_CATEGORY and food_needed > 0:
            food_needed -= 1
            continue
        droppable.append(place)
    return droppable[::-1]


def enforce_input_limit(
    request: GenerationRequest, max_tokens: int | None
) -> tuple[GenerationRequest, int]:
    """The request cut to the limit, and the number of places removed (§8.6, FR-039 AC1).

    Must-visit places, locked places and enough food places for the meal slots always stay. If the
    prompt cannot fit even so, AI_MAX_INPUT_TOKENS is too low for this trip: ProviderBadRequest.
    """
    if max_tokens is None or estimate_tokens(request) <= max_tokens:
        return request, 0
    removed: set[object] = set()
    trimmed = request
    for place in _droppable(request):
        removed.add(place.place_id)
        trimmed = request.model_copy(
            update={
                "shortlist": [p for p in request.shortlist if p.place_id not in removed],
                "day_hints": [
                    hint.model_copy(
                        update={"place_ids": [i for i in hint.place_ids if i not in removed]}
                    )
                    for hint in request.day_hints
                ],
            }
        )
        if estimate_tokens(trimmed) <= max_tokens:
            return trimmed, len(removed)
    raise ProviderBadRequest("the prompt does not fit AI_MAX_INPUT_TOKENS")
