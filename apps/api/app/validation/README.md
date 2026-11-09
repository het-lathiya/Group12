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

## MUST_VISIT_MISSING (error, §9.3.7, FR-034, FR-055)

Every place of `ctx.must_visit_ids` with no item on any day gives one `MUST_VISIT_MISSING`. The finding has `place_id` set and `item_ref` and `day_number` null, because the place has no item (IMD-42); the message names the place (from `ctx.places`, else its ID) and says it is not in the plan. Findings come in place-ID order.

Boundary cases:

- A must-visit place present on any day, once or more, gives no finding.
- A must-visit place that has an item counts as present even when it is no longer active; that item gets `UNKNOWN_PLACE` instead. A missing must-visit place that is no longer active is named by its ID.

## UNKNOWN_PLACE (error, §9.3.6, FR-055)

An item whose `place_id` is not an active place of the destination (`ctx.places`), or, when `ctx.shortlist_ids` is set (generation), not in the shortlist, gives `UNKNOWN_PLACE` on that item.

Boundary cases:

- With `shortlist_ids` None (edits, where no shortlist exists), any active place is valid.
- An active place outside the shortlist is unknown only in generation.
- This is the validator's finding only; dropping such items from a model answer is step 8 (`output_check.py`).

## OUTSIDE_TRIP_DATES (error, §9.3.6, FR-055)

num_days = end date − start date + 1. Every item on a day outside 1..num_days gives `OUTSIDE_TRIP_DATES`, one finding per item.

Boundary cases:

- Day 1 (the start date) and day num_days (the end date) are inside (TC-305); a one-day trip has day 1 only.
- A day number that a finding cannot hold (below 1 or above 14) gives `day_number` null; the day stays in `item_ref` and the message.
- Dropping such items from a model answer (IMD-126) is step 8, not the validator.
