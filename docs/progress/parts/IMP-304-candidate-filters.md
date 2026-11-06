# IMP-304 · candidate-filters part

- Run id: RUN-045 (grouped, IMD-121, with IMP-304, IMP-307 and IMP-310)
- Owner: Malhar (Malhar1112-v)
- Status: PR_OPEN
- Base commit: 4f20bfc
- Branch: feat/IMP-304-307-310-wave1
- Reviewer: Manal (manalPatel2557)
- Traces to: US-046; FR-027; TC-123, TC-124, TC-125
- Card steps built: 1 and 2

## Changed files

- `apps/api/app/places/repository.py`: `candidates(session, destination_id)`, active places of an active destination with their opening hours, in one parameterised query. The labels are columns of `places`. The module has functions rather than a class, so the card's `PlaceRepository.candidates` is this function.
- `apps/api/app/generation/retrieval.py` (created):
  - `retrieve_candidates(session, trip, prefs, must_visit)` returns the filtered `Candidate` list.
  - `apply_filters` holds the filters without I/O.
  - `activity_budget` and `min_group_cost` give the two budget values.
- `apps/api/app/generation/repository.py`: `budget_settings(session, trip_id)`, read only.
- `apps/api/tests/api/test_retrieval.py` (created, 17 tests).

## Commands and results

| Command | Result line |
| --- | --- |
| `make test-api ARGS='-k retrieval'` | `17 passed, 233 deselected, 1 warning in 2.57s` |
| `make lint` | `All checks passed!` (ruff); `All matched files use Prettier code style!` |
| `make typecheck` | `Success: no issues found in 89 source files` |
| `make imports` | `Contracts: 5 kept, 0 broken.` |
| `make test` (via `make check`, `TEST_DATABASE_URL` = the §4.7 default on `pgvector/pgvector:pg16`) | unit `467 passed, 1 warning`; contract `35 passed, 1 warning`; api `250 passed, 1 warning`; authz `28 passed`; web `Tests  80 passed (80)` |
| `make check` | exit 0 (`openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date`) |

Not run: `make e2e` (no journey changes; nothing in the pipeline calls this code yet).

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| Step-free trips contain no non-step-free place (FR-027 AC1, TC-123) | verified | `test_tc_123_step_free_trips_hold_only_step_free_places` |
| A must-visit place failing a filter stays with a note (FR-027 AC2, TC-124) | verified | `test_tc_124_a_must_visit_place_failing_a_filter_stays_with_a_note`, and the excluded-category, closed and budget tests |
| Every candidate ID exists in places (FR-027 AC3, TC-125) | verified | `test_tc_125_every_candidate_id_exists_in_places` |
| Shortlist size and must-visit retention on SAMPLE | verified | Part `ranking`, `docs/progress/parts/IMP-304-ranking.md` |

## Blockers

None.

## Proposed decisions

- **PD-IMP-304-1: activity budget.** The specification uses this term without defining it, and blueprint §20.2 is not in the repository. It is derived from §9.3.1: the most activities and meals may cost with the planning total still within the budget, `B / (1 + p/100) - D·t - (D - 1)·s`, a missing line counting 0, never below 0. No budget means no budget filter.
- **PD-IMP-304-2: children filter.** The card lists four filters; pm-1 also holds the children rule (`child_friendly` false is removed, unknown kept). It runs after the excluded-category filter, as pm-1 is the only source of filters (IMD-29).
- **PD-IMP-304-3: stay in the query.** §8.9 puts `category ≠ stay` in the query. It is applied as a filter instead, so a must-visit stay place reaches the filters and keeps its conflict note (FR-027 AC2). No SAMPLE place is in that category.

## Open issues

- A price in another currency, or no price, never fails the budget filter (`min_group_cost` is None, §9.3.1 BF-04).
- `request_builder.py` still uses the first 40 places by name. Its docstring says ranking replaces this in IMP-304, but the file is not on this card; IMP-303 owns the file and takes the shortlist as an input.
