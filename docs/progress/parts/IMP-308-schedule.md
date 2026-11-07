# IMP-308 · schedule part

- Run id: RUN-049 (grouped, IMD-121, with IMP-315)
- Owner: Het (het-lathiya)
- Status: merged in PR #252
- Base commit: e5f5e7a
- Branch: feat/IMP-315-308-wave4
- Reviewer: Kirtan (kirtan-S111)
- Traces to: US-051; FR-033; TC-139
- Card steps built: 1

## Changed files

- `apps/api/app/generation/schedule.py` (created): `recalculate(days, places, routing, pace, *, mode)`.
- `apps/api/app/generation/pipeline.py`: step 9 `recalculate` calls it in its own transaction, before the save.
- `apps/api/app/itinerary/schemas.py`, `repository.py`, `service.py`: `PlannedDay` and `PlannedItem`, which the save stores, travel columns included. The `snap-1` snapshot still leaves travel out (§5.2).
- `apps/api/app/schemas/ai.py`: `ShortlistPlace.id`, a property, so the exported gr-1 schema is unchanged.
- Tests: `tests/unit/generation/test_schedule.py` (created); `tests/api/test_generations.py`, `test_itinerary.py`, `tests/unit/generation/test_pipeline.py`, `tests/unit/validation/test_injection_cases.py`, `test_output_check.py`, `tests/fixtures/pipeline.py` (the save now takes the planned days).

## Commands and results

| Command | Result |
| --- | --- |
| `make test-unit ARGS='-k schedule'` | `8 passed, 699 deselected, 1 warning` |
| `make test-unit` | `707 passed, 1 warning` |
| `make test-api` (`TEST_DATABASE_URL` on `pgvector/pgvector:pg16`) | `311 passed, 1 warning` |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` |
| `make check` (the two commits of this run in the tree, `TEST_DATABASE_URL` on `pgvector/pgvector:pg16`) | exit 0: unit `707 passed, 1 warning`; contract `87 passed, 2 deselected, 1 warning`; api `311 passed, 1 warning`; authz `29 passed`; web `Tests  88 passed (88)` |
| `make e2e ARGS='journey'` (steps of `.github/workflows/e2e.yml`; web on port 3100 because another server held 3000) | `4 passed (10.4s)` |

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| Stored times equal the backend calculation; model values are ignored (FR-033 AC1, TC-139, times) | verified | `test_tc_139_model_times_and_durations_are_replaced_by_the_calculation`, and `test_tc_139_saved_times_are_the_recalculation_and_not_the_models` on a real database with injected model times |
| Stored totals equal the backend calculation (FR-033 AC1, totals) | not verified | The budget-costs part: item costs are still null |
| Times and costs come from recalculation, never from model fields (open criterion of IMP-305-pipeline) | verified for times; costs not verified | As above; the costs half stays with the budget-costs part |

## Blockers

None for this part.

## Proposed decisions

- **PD-IMP-308-1: durations come from the place.** The card's objective says durations are computed from stored data and §8.1 says "backend recalculates", but step 1 gives no rule. `duration_min` is the place's `typical_duration_min`, so no saved time or duration is a model value. If the team wants the model's `duration_min` kept, it is one line in `schedule.py`.
- **PD-IMP-308-2: `pace` has no rule.** The card's signature has `pace` but no step reads it, and it has no travel mode, which the rule needs. `recalculate` keeps `pace` and adds keyword `mode`, from `transport_pref`. The team can drop `pace` or give it a rule.
- **PD-IMP-308-3: §9.3.3 and the card differ on the first item.** §9.3.3 says item 1 keeps its `start_time`; the card and this run's prompt say 09:00. Built as the card says.

## Open issues

- A day that runs past midnight stops at 23:59 (`time` cannot hold more). The findings of IMP-404 are to report such a day.
- `RoutingService.travel` runs one leg at a time, at most 8 seconds each when OpenRouteService hangs. A long trip during an outage can use a large part of the job's time budget. To be measured at SG-3.
- `route_cache` writes and any ORS call happen in one transaction of their own, separate from the save; a routing call is not a model provider call, but §5.8 does not name it either.
