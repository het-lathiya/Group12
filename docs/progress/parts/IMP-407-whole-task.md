# IMP-407 · whole-task part

- Run id: RUN-060 (grouped, IMD-121, with IMP-405 and IMP-403)
- Owner: Het (het-lathiya)
- Status: PR open
- Base commit: 84d1973
- Branch: feat/IMP-403-405-407-failures-warnings-edits
- Reviewer: Kirtan (kirtan-S111)
- Traces to: US-073; FR-064; NFR-003, NFR-008; IMD-18, IMD-23; A1 §6.10 (IMD-110)
- Card steps built: 1 to 7 (the core and its schema; no routes, as the run prompt requires)

## Changed files

- `apps/api/app/itinerary/edits.py` (created): the operations `Move`, `Retime`, `Remove`, `Add`, `Lock` and `Replace` (`EditOperation`), and `apply_edit(session, user_id, trip_id, base_revision, op) -> EditResultOut`. It follows §5.8 in order:
  1. Lock the trip row (`SELECT … FOR UPDATE`, owner only, else 404).
  2. 409 GENERATION_IN_PROGRESS if a generation is queued, running, validating or repairing. This is checked before the revision (IMD-23).
  3. 409 STALE_PLAN on a revision mismatch.
  4. Apply the operation.
  5. Renumber positions.
  6. Recompute travel on the changed days (route cache, ORS, estimate) and shift later unlocked start times forward.
  7. Price added or replaced places with the budget engine.
  8. `validate()` the whole plan (IMP-404/IMP-405).
  9. plan_revision + 1.
  10. Save the new revision's warnings through part 1's `insert_warnings`.
  11. Write an automatic `itinerary_versions` row with reason `edit`, a snap-1 snapshot and its summary.
  12. Return `EditResultOut`.

  422 INVALID_EDIT covers: a day not in the plan, a position out of range, an unknown or inactive place (or one of another destination), an item not in the plan, and moving, retiming or replacing a locked item. Soft-rule breaks are saved and returned as findings (PR-06). Kept items keep their note and `source_chunk_ids`. A replaced item drops them, because they described the old place.
- `apps/api/app/itinerary/service.py`: `plan_out(session, trip, days, rows, generation)` is extracted from `get_itinerary` (API-24's response is unchanged), so the edit response's days and totals are built by the same code and the same budget engine.
- `apps/api/app/itinerary/repository.py`: `bump_revision` (plan_revision + 1 only; unlike `mark_plan_saved` it leaves `status` and `plan_stale` alone) and `generation_active`. This file is not in the card's list. The two queries belong to the table owner's repository (CLAUDE.md §4), and itinerary must not import generation, which already imports itinerary (§4 rule 6).
- `apps/api/app/itinerary/schemas.py`: unchanged. `EditResultOut {plan_revision, changed_days, totals, findings}` was already in contract v1 (§6.5); see the deviation note below.
- `apps/api/tests/api/test_edits.py` (created): TC-206 (all six operations, each answering recalculated totals and findings equal to API-24's, a new revision and an `edit` version), add follows the previous item and is priced, a move takes the displaced slot and shifts later items, a conflicting retime is saved with OVERLAP (PR-06), kept items keep citations in rows and snapshot, stale 409, active generation 409 even when also stale, seven impossible edits 422, a foreign trip 404, and TC-207/TC-312 (a fault in `validate`, `insert_warnings` or `insert_version` leaves every table as it was, and the plan stays editable).
- `apps/api/tests/api/test_edit_performance.py` (created): TC-330.

Deviation from the run prompt, as the specification wins: the prompt names the edit response `{plan_revision, day, totals, warnings}`. §6.5 and the existing contract define `EditResultOut {plan_revision, changed_days[], totals, findings[]}`, and this part returns that shape, so no contract change was needed.

Times rule (FR-060, card step 5):
- A retime keeps the traveller's values.
- A moved item takes the start time of the item it displaces, or follows the previous item when it is appended.
- An added item without a time follows the previous item.
- Later unlocked items on the edited day shift to `max(own start, previous end + travel + buffer)`. Locked items never move.

`schedule.recalculate` (IMP-308) is not called: it lives in `generation`, which imports `itinerary` (a cycle), and it replaces every start time and duration with the generation defaults, which would undo a retime.

## Commands and results

PostgreSQL: a throwaway PostgreSQL 16.2 with pgvector on 127.0.0.1:55432 (scratch directory, `TEST_DATABASE_URL` set for the run).

| Command | Result |
| --- | --- |
| `make test-api ARGS='-k edits'` | `12 passed, 361 deselected, 1 warning` |
| `make test-api ARGS='-k edit_performance'` (with `-s`) | `TC-330 edit_performance: 30 edits on a 10-day trip (27 items on 8 planned days): p50 63 ms, p95 79 ms (target p95 < 1500 ms)`; `1 passed, 373 deselected, 1 warning` |
| `make test-api` | `374 passed, 1 warning` |
| `make test-authz` | `37 passed` |
| `make test-unit` | `1006 passed, 1 warning` |
| `make test-web` | `Tests  151 passed (151)` |
| `make lint` | exit 0 |
| `make typecheck` | `Success: no issues found in 115 source files` (web `tsc` clean) |
| `make imports` | `Contracts: 6 kept, 0 broken.` |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` |

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-064 AC1 / TC-206: every edit response has recalculated totals | verified | `test_tc_206_every_edit_returns_recalculated_totals_findings_and_a_new_revision` (totals, findings and changed days equal API-24 after each of the six operations) |
| FR-064 AC2 / TC-207: a failing validation step leaves data consistent and is reported | verified | `test_tc_207_tc_312_...[validate]`: the error propagates (the route will answer 500 INTERNAL) and nothing is written |
| TC-312: an interrupted edit leaves consistent data | verified | `test_tc_207_tc_312_...[insert_warnings]`, `[insert_version]`: the revision is already bumped when the fault fires, and the rollback restores it |
| TC-330: 10-day fixture p95 < 1.5 s locally (recorded, not a gate) | verified (recorded) | p95 79 ms locally; the test's assertion is a loose 5 s |
| A stale base revision returns 409 STALE_PLAN and changes nothing | verified | `test_edits_a_stale_revision_is_refused_and_nothing_changes` |
| An active generation returns 409 GENERATION_IN_PROGRESS and changes nothing (IMD-23) | verified | `test_edits_an_active_generation_is_refused_before_the_revision_check` |
| Kept items keep source_chunk_ids (A1 §6.10) | verified | `test_edits_kept_items_keep_their_citations` |

## Blockers

none

## Proposed decisions

- **PD-IMP-407-1: travel lookups inside the lock.** §5.8 says a routing call is made before the transaction opens. The core looks travel up inside the locked transaction (route cache first, then ORS, then the estimate), marked `shortcut:` in `edits.py`. With ORS configured, an uncached pair holds the trip lock for one HTTP call. Proposal: keep it for the MVP and move the lookup in front of the lock if lock waits show up.
- **PD-IMP-407-2: days without items.** The rule-based save writes only days that have items (the 10-day SAMPLE trip gets 8 day rows). An edit naming a day with no row is refused as INVALID_EDIT ("not in the plan"), although it is inside the trip. IMP-504 (API-25) should decide whether the save writes every trip day or whether an edit creates the missing day row.

## Open issues

- With the versions switch off, §5.8 keeps only one backup copy. Pruning automatic versions is IMP-610, so every edit adds a version until then.
- Lock and unlock are core operations; the `locks` feature switch is enforced by the API-26 route (IMP-408/IMP-506).
