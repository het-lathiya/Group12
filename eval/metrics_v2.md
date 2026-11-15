# Evaluation metrics, version v2

Computed by `apps/api/app/evaluation/metrics.py` (`METRICS_VERSION = "v2"`) for every provider with the same code; `compute` takes no provider argument (FR-119 AC2). Each run record (`eval/results/<run_id>/run.json`) holds the SHA-256 of this file, so a changed definition shows up as a new hash. A change to a definition is a new version (`metrics_v3.md`), never an edit of this file once a run has used it. v2 is v1 (`metrics_v1.md`, unchanged) plus the count `no_duplicate_places` (IMD-181).

## Attempts

The harness runs every case of the dataset `--repeats` times (default 3). One attempt is one case and one repeat, scored by the production code of pipeline steps 7 to 9:

1. `provider.generate_itinerary` on the frozen gr-1 request (step 7).
2. `output_check.apply_limits` and `output_check.check_output` (step 8, §8.11).
3. `generation.schedule.recalculate` with the §9.3.5 distance estimate as the routing (no route cache, no OpenRouteService), the budget engine `budget.engine` (BF-01 to BF-12) and `validation.validator.validate` (step 9, §8.12).

Step 10 (repair, IMP-502) and the rule-based fallback (IMP-402) are not built yet, so an attempt is scored on the provider's answer alone.

`scores.json` holds one row per attempt: the error kind when there was no answer, `schema_valid`, `place_ids_valid`, `usable`, `no_duplicate_places`, `duplicate_places`, `invalid_ids`, `rejected_items`, the findings counted by code (from step 8, the validator and the budget engine), the budget status, latency and token counts.

## Counts (k of n attempts)

Only rules that the specification states exactly:

| Name | An attempt counts when | Source |
| --- | --- | --- |
| `schema_valid` | the answer was parsed and validated as io-1 together with the trip limits (no `malformed_json`, `schema_violation`, `empty`, `blocked` or `truncated`, and no other provider error) | §8.11 step 1 |
| `place_ids_valid` | the answer was schema-valid and step 8 found no place ID outside the shortlist (`invalid_ids = 0`) | §8.11 step 3 |
| `usable` | the scored plan has at least one day with items and no `UNKNOWN_PLACE`, `OUTSIDE_TRIP_DATES`, `OVERLAP` or `CLOSED_ON_DAY` finding | §8.12 |
| `no_duplicate_places` | the answer was schema-valid and no place appears more than once on the trip's days, meal stops included (`duplicate_places = 0`, the number of items whose place came earlier in the plan) | IMD-181 |

## Numbered metrics 1 to 13

The numbered metrics are those of blueprint §21.4. The blueprint is not in the repository (PD-IMP-310-1), so v1 gives no definition that it cannot copy (PD-IMP-413-3):

| Metric | v1 |
| --- | --- |
| 1 to 6, 10, 11, 13 | not computed in v1: blueprint §21.4 is not in the repository |
| 7, 9 | not computed in v1 (IMP-413 card) |
| 8 | Release 2 (§8.17) |
| 12 | null: no dated price table exists (§8.16) |

Each is written to the run record with `value: null` and this status.

## Supplementary metric (IMD-169)

`avg_daily_travel_min` is the mean over every planned day of all attempts of that day's summed travel minutes (`daily_travel_min`), rounded to one decimal place; it is null when there are no planned days. It is computed by `apps/api/app/evaluation/metrics.py`. This supplements v1; the three v1 counts above are unchanged (IMD-144), and v2 adds only `no_duplicate_places`.
