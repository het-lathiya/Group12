# IMP-504 · add-place-api part

- Run id: RUN-068 (Sprint 5 batch A)
- Owner: Het (het-lathiya)
- Status: committed on the part branch, not pushed (the lead integrates)
- Base commit: 26bac9d
- Branch: part/IMP-504-add-place-api
- Traces to: US-071, US-074; FR-062, FR-069; NFR-003, NFR-008; IMD-23, IMD-152
- Card steps built: 1 to 4 (backend). Steps 5 to 7 (PlacePicker, `client.ts`, `EDIT_UNDO_ENABLED`) are Malhar's part.

## Changed files

- `apps/api/app/itinerary/edits.py`:
  - `add_item(session, user_id, trip_id, body)` turns the API-25 body into the IMP-407 `Add` operation and runs `apply_edit`.
  - Without `start_time` the place goes after the day's last item at previous end + travel + buffer (FR-062 AC1), with `origin user` and the place's typical duration.
  - With `start_time` but no `position`, the item is inserted in start-time order instead of being appended out of order.
  - IMD-152 (PD-IMP-407-2), decided as below: `_day` gives a trip day without a row its `itinerary_days` row on the first add or move. A day outside 1..num_days is still 422 INVALID_EDIT. `apply_edit` builds its response from the day rows after the operation, so the new day appears in `changed_days` and in the snapshot.
- `apps/api/app/itinerary/router.py`: API-25 is wired to `edits.add_item` (it answered 501 before).
- `apps/api/tests/api/test_edits.py`: TC-202, TC-203 (a duplicate place at a clashing time is kept as a second item, reported as OVERLAP, with no merge), INVALID_EDIT for day num_days+1 and for an unknown place, the empty-day row (IMD-152), TC-217 (a second tab's add, retime and remove on the old revision all answer 409 STALE_PLAN, and both the rows and API-24 are identical before and after), active generation 409, and a foreign trip 404.
- `apps/api/tests/authz/route_matrix.py`: an API-25 entry. This file is not in the card's list. The TC-065 walk fails for any built owned route that is not in the matrix, and CLAUDE.md §9 requires an authorization test for every new owned route.
- `apps/api/app/itinerary/schemas.py`: unchanged. `ItemAddIn` and `EditResultOut` are already contract v1, so no regeneration is needed. The exported OpenAPI was diffed against `contracts/`, with no difference.

Step 4 (revision check on every edit route) already holds in the shared `apply_edit`, as IMP-407 built it: lock the trip, then 409 GENERATION_IN_PROGRESS, then 409 STALE_PLAN, before anything is written. API-25 to API-27, and API-29 in IMP-505, all go through it.

## Commands and results

Python tools were run from the worktree's `apps/api` with `PYTHONPATH=.` (and `app.__file__` was checked to point into the worktree).

| Command | Result |
| --- | --- |
| `.venv/bin/ruff check app tests` | `All checks passed!` |
| `.venv/bin/ruff format --check app tests` | `205 files already formatted` |
| `.venv/bin/mypy app` | `Success: no issues found in 118 source files` |
| `.venv/bin/lint-imports` | `Contracts: 6 kept, 0 broken.` |
| `pytest -q tests/authz/test_ownership.py -k tc_065` | `2 passed, 32 deselected in 0.23s` |
| `pytest -q tests/contract/test_openapi_contract.py` | `7 passed, 1 warning in 0.76s` |
| `pytest -q --collect-only tests/api/test_edits.py -k "add_place or stale"` | `11/37 tests collected (26 deselected) in 0.03s` |
| `python -m app.openapi_export` diffed with `contracts/` | no difference |

Not run: `make test-api ARGS='-k "add_place or stale"'` and `make test-authz` (no PostgreSQL in this run, as the run prompt says). Deferred to integration.

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-062 AC1 / TC-202: inserted at a feasible time, day revalidated | not verified (deferred to integration) | `test_tc_202_add_place_route_inserts_at_a_feasible_time_and_revalidates` written and collected |
| FR-062 AC2 / TC-203: conflict reported and addition kept | not verified (deferred to integration) | `test_tc_203_add_place_route_keeps_a_conflicting_addition_and_reports_it`; undo (cancel) is Malhar's step 6 |
| FR-069 AC1 / TC-217: second tab gets 409 STALE_PLAN, rows identical | not verified (deferred to integration) | `test_tc_217_stale_edit_from_a_second_client_is_refused_and_rows_stay_identical` |
| Day 0 or num_days+1 returns 422 INVALID_EDIT | not verified; num_days+1 returns INVALID_EDIT, day 0 returns 422 VALIDATION_ERROR | `test_add_place_route_refuses_a_day_outside_the_trip_or_an_unknown_place`; see PD-IMP-504-2 |
| The page never computes times or totals | not applicable to this part | Malhar's screen part |

## Blockers

none

## Proposed decisions

- **PD-IMP-504-1 (resolves PD-IMP-407-2 under IMD-152): an edit creates the missing day row.** An add or move that names a trip day (1..num_days) without an `itinerary_days` row creates that row (`plan_date` = start_date + day − 1, no theme) in the same edit transaction. The save step is left unchanged. Reasons: it is local to the edit transaction, needs no change to the generation save or to existing plans, and API-24 already lists only days with rows. A day outside the trip stays 422 INVALID_EDIT.
- **PD-IMP-504-2: day 0 answers VALIDATION_ERROR, not INVALID_EDIT.** `ItemAddIn.day_number` is `DayNumber` (`ge=1`) in contract v1, so request validation answers day 0 with 422 VALIDATION_ERROR before the edit runs. The card's criterion names INVALID_EDIT. Proposal: amend the criterion so day 0 gives 422 VALIDATION_ERROR (still a 422 that changes nothing), and keep the contract. The alternative is to drop the bound from `ItemAddIn`, which is a contract change.

## Open issues

- The IMD-152 test assumes the 10-day SAMPLE rule-based plan leaves at least one day without a row, as IMP-407 observed (8 rows for 10 days). If a later seed fills every day, that test needs another way to get an empty day.
- `route_matrix.py` (authz) was edited outside the card's file list (see Changed files).
