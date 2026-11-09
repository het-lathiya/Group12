# app/validation

MOD-B07. Two steps of the generation pipeline (§8.2) and the validator of every plan.

- `output_check.py`: step 8, the model's answer against its schema, the shortlist and the trip (§8.11, IMP-306).
- `rules.py`: the finding catalogue (13 codes and their severities, §8.12), `ValidationContext` and the rules, each a pure function `(plan, ctx) -> list[Finding]`.
- `validator.py`: `validate(plan, ctx)` runs `rules.RULES` in their fixed order and returns every finding.

A plan is the recalculated days of step 9 (`PlannedDay`, IMP-308) or any object with the same attributes: each day has `day_number` and `items`; each item has `place_id`, `start_time` (HH:MM), `duration_min`, `travel_from_prev_min` and `travel_source`. The travel time and its source come from the item, as step 9 stored them; the rules never route. An item is named `d<day>-i<position>`, positions counting from 1.

## OVERLAP (error, §9.3.4, FR-050)

For consecutive items i and j of one day, gap = start of j − (start of i + duration of i), in minutes. gap < 0 gives `OVERLAP` on j, and the message names both items and the minutes of overlap.

Boundary cases:

- gap = 0 (back-to-back) is not an overlap (TC-177). The transfer rule then decides whether there is time to travel.
- Items on different days are never compared, even at the same clock time (TC-306).
- Only neighbours by position are compared. An item placed after one that started later is reported against its neighbour, not against every item it crosses.

## TRANSFER_TOO_SHORT (warning, §9.3.5, FR-051)

need = `travel_from_prev_min` + buffer, where the buffer is 5 minutes after `routing_api` and 15 after `fallback_estimate` (`app.routing.estimate.BUFFER_MIN`). 0 ≤ gap < need gives `TRANSFER_TOO_SHORT` on j, and the message carries the shortfall need − gap.

Boundary cases:

- gap = need is enough; gap = need − 1 is one minute short.
- A 10-minute gap and a 30-minute transfer from routing is 25 minutes short; from the distance estimate it is 35 minutes short and the message says "(estimate)" (TC-178, TC-179).
- gap < 0 is an `OVERLAP` only, never also a short transfer.
- The first item of a day, and an item without stored travel (null minutes or source), are not checked.
