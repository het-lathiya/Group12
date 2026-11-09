# FIX IMD-126 · outside-trip-drop part

- Run id: RUN-057 (grouped, IMD-121, with IMP-401, IMP-402 and IMP-406)
- Owner: Manya (manyarana)
- Status: PR open
- Base commit: 16839a0
- Branch: feat/IMP-401-402-406-generation-reliability
- Reviewer: Manasvi (Manasvi1704)
- Traces to: IMD-126; §8.11 step 2; FR-032
- Scope: items on days outside 1..trip days are dropped with OUTSIDE_TRIP_DATES instead of failing the whole answer

## Changed files

- `apps/api/app/validation/output_check.py`:
  - `apply_limits` checks the trip limits (day count, a day twice, items per day) on days 1..trip days only and returns the answer unchanged; days past the trip no longer make a `schema_violation`. An answer whose days are all outside the trip passes to `check_output`, which drops every item.
  - `OutputCheckResult.usable` is now "at least one item and no UNKNOWN_PLACE": an OUTSIDE_TRIP_DATES item has been dropped, so it no longer remains (§8.12).
  - `check_output` is unchanged: one OUTSIDE_TRIP_DATES finding (error) per dropped item, named `d<day>-i<position>`, counted in `rejected_items`; UNKNOWN_PLACE and duplicate handling are unchanged. `summary` records the counts as IMP-306 does (`errors` includes the OUTSIDE_TRIP_DATES findings).
- `apps/api/app/generation/pipeline.py`: not changed by this part; the pipeline already saves `check_output`'s remaining answer when it is usable.
- `apps/api/tests/unit/validation/test_output_check.py`: TC-137 now also asserts the answer stays usable; new tests for a day past the trip (no schema violation, the rest kept), an answer with only outside days (not usable), UNKNOWN_PLACE still unusable, and the pipeline saving the answer without the outside day. The "more days than the trip" case of `test_tc_023_trip_limits_are_a_schema_violation` was removed: IMD-126 makes it a drop, which the new test asserts.

## Commands and results

| Command | Result |
| --- | --- |
| `make test-unit ARGS='-k output_check'` | `34 passed, 946 deselected, 1 warning` |
| `make test-unit` | `980 passed, 1 warning` |
| `make test-web` | `Tests  119 passed (119)` |
| `make lint` | exit 0 |
| `make typecheck` | `Success: no issues found in 112 source files` |
| `make imports` | `Contracts: 6 kept, 0 broken.` |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` |
| `make test-api ARGS='-k generation'` | not run to a result: no PostgreSQL or Docker on this machine (connection refused on port 5432). Evidence comes from the CI `api` job; no API test asserts OUTSIDE_TRIP_DATES |

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| Items on days outside 1..trip days are dropped with OUTSIDE_TRIP_DATES, not failing the answer (IMD-126, §8.11 step 2) | verified | `test_output_check_imd_126_a_day_past_the_trip_is_dropped_not_a_schema_violation`, `test_tc_137_items_on_a_day_outside_the_trip_are_rejected`, `test_output_check_imd_126_the_pipeline_saves_the_answer_without_the_outside_day` |
| UNKNOWN_PLACE and duplicate handling unchanged | verified | `test_tc_138_an_invented_place_id_is_dropped_with_unknown_place`, `test_output_check_unknown_place_still_makes_the_answer_unusable`, `test_the_second_occurrence_of_a_place_is_rejected_and_the_plan_stays_usable` |
| Counts recorded in validation_summary as IMP-306 does | verified | the pipeline test asserts `errors` 1 and `rejected_items` 1 on the completed record |

## Blockers

none

## Proposed decisions

none

## Open issues

- The dropped item's OUTSIDE_TRIP_DATES finding is counted in `validation_summary` but not saved as an `itinerary_warnings` row: the item has no row for `item_id`, and IMD-42 gives a `place_id` only to MUST_VISIT_MISSING. If the team wants it shown on the plan, a decision on how to reference it is needed.
