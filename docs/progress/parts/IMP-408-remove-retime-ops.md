# IMP-408 · remove-retime-ops part

- Run id: RUN-062 (grouped with IMP-409; parts remove-retime-ops, move-op, item-editor, move-controls)
- Owner: Het (het-lathiya)
- Status: PR open
- Base commit: d7625c7
- Branch: feat/IMP-408-409-remove-retime-move
- Reviewers: Assassin-byte, manalPatel2557
- Traces to: US-070, US-072; FR-061, FR-063; NFR-003; IMD-23, IMD-26
- Card steps built: 1 to 3 (API-27 remove, API-26 retime, ownership through the item's trip)

## State on main before this part

- API-26 `PATCH /api/v1/itinerary/items/{item_id}` and API-27 `DELETE /api/v1/itinerary/items/{item_id}` were declared in `itinerary/router.py` as `raise EndpointNotImplemented()` stubs (501 NOT_IMPLEMENTED, IMD-37). Their shapes were already in contract v1: `ItemPatchIn` and `EditResultOut {plan_revision, changed_days, totals, findings}`.
- `migrations/sql/0004_ai_and_plan.sql` line 91: `unique (day_id, position) deferrable initially deferred`, so renumbering inside one transaction needs no temporary positions.

## Changed files

- `apps/api/app/itinerary/router.py`: API-26 and API-27 take `CurrentUser` and `DbSession` and call `edits.patch_item` and `edits.remove_item`. No rules or SQL in the router.
- `apps/api/app/itinerary/edits.py`: `patch_item` and `remove_item` translate the bodies into the IMP-407 `Retime` and `Remove` operations and call `apply_edit` unchanged (no new recalculation path; the PD-IMP-407-3 times rule applies). A private `_locate` finds the item's trip for the signed-in user. The operations themselves are unchanged.
- `apps/api/app/itinerary/repository.py` (not in the part's list): `item_location(session, item_id, user_id)` returns the item's trip and day only when the trip belongs to the user and is not deleted. The query belongs to the table owner's repository (CLAUDE.md §4).
- `apps/api/tests/api/test_edits.py`: route tests (below). `planned_trip` gained an optional `must_visit` argument for TC-201.
- `apps/api/tests/authz/route_matrix.py`: API-26 and API-27 rows (`foreign`); `Owned` gained `item_id` and `url()` fills `{item_id}`.
- `apps/api/tests/authz/test_ownership.py` (not in the part's list): the `owned` fixture sets `item_id` to A's first itinerary item, which the two new matrix rows need.

## Behaviour

- API-27 with `?plan_revision=N` (IMD-26) removes the item; positions renumber, travel and later times recompute, the plan is revalidated. Removing a must-visit item returns `MUST_VISIT_MISSING` in `findings` (FR-061 AC2).
- API-26 with `start_time` and/or `duration_min` is a retime. The traveller's values are kept; clashes come back as findings (for example OVERLAP), not as a refusal (PR-06, PD-IMP-407-3). FR-063 AC1 allows "shift or flag"; this flags.
- Duration outside 15 to 480 is refused by `ItemPatchIn` with 422 `VALIDATION_ERROR` in the §6.3 envelope (FR-063 AC2).
- Another user's item, or an item of a deleted trip: 404 `NOT_FOUND`. Stale revision: 409 `STALE_PLAN`. Active generation: 409 `GENERATION_IN_PROGRESS` (from the IMP-407 core, unchanged).
- A body with no change: 422 `INVALID_EDIT`.
- A body that sets `is_locked` keeps answering 501 `NOT_IMPLEMENTED`: lock and unlock are IMP-506 (Sprint 5). In this commit a body with `day_number` or `position` also answers 501; the move-op part wires it.

## Commands and results

PostgreSQL: a throwaway PostgreSQL 16.2 with pgvector (pip `pgserver`) on 127.0.0.1:55432 in a scratch directory outside the repository, `TEST_DATABASE_URL` set for the run, stopped afterwards.

| Command | Result |
| --- | --- |
| `make test-api ARGS="-k 'remove or retime'"` | `13 passed, 401 deselected, 1 warning` |
| `make test-authz` | `41 passed` |
| `make test-unit` | `1006 passed, 1 warning` |
| `make lint` | exit 0 (one existing ESLint warning in `apps/web/lib/api/client.ts`, not from this part) |
| `make typecheck` | `Success: no issues found in 116 source files` |
| `make imports` | `Contracts: 6 kept, 0 broken.` |
| `make openapi` | no diff |

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-061 AC1 (TC-200): a removal recomputes the day's times and totals | verified | `test_tc_200_remove_route_recomputes_the_day_and_totals`: positions dense, the new first item has no travel leg, response equals API-24 |
| FR-061 AC2 (TC-201): a removed must-visit item yields a warning | verified | `test_tc_201_remove_route_reports_a_removed_must_visit_place`: MUST_VISIT_MISSING naming the place |
| FR-063 AC1 (TC-204): following times shift or conflicts are flagged | verified | `test_tc_204_retime_route_saves_the_new_values_and_flags_the_conflict`: values saved, OVERLAP on the next item |
| FR-063 AC2 (TC-205): a duration outside limits is rejected | verified | `test_tc_205_retime_route_refuses_a_duration_outside_15_to_480` (14 and 481): 422 VALIDATION_ERROR, nothing written |
| A foreign item → 404 | verified | `test_retime_and_remove_routes_answer_another_users_item_with_not_found`; authz matrix rows API-26, API-27 |
| Response totals equal API-24 after the edit | verified | `assert_matches_itinerary` in TC-200 and TC-204 |
| Stale 409 / active generation 409, nothing changed | verified | `test_remove_and_retime_routes_refuse_a_stale_revision_or_an_active_generation` |

## Blockers

none

## Proposed decisions

none

## Open issues

- `is_locked` on API-26 answers 501 until IMP-506.
- Screenshots: not verified — taken on the local stack by the member after merge.
