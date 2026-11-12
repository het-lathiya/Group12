# IMP-409 · move-op part

- Run id: RUN-062 (grouped with IMP-408; parts remove-retime-ops, move-op, item-editor, move-controls)
- Owner: Het (het-lathiya)
- Status: PR open
- Base commit: d7625c7
- Branch: feat/IMP-408-409-remove-retime-move
- Reviewers: Assassin-byte, manalPatel2557
- Traces to: US-069; FR-060; NFR-003
- Card steps built: 1 (move operation on API-26)

## Changed files

- `apps/api/app/itinerary/edits.py`: `patch_item` sends a body with `day_number` and/or `position` to the IMP-407 `Move` operation through `apply_edit`. Without `day_number` the item stays on its own day; without `position` it goes after the target day's last item (`Move.position` is now optional for this). Positions in both affected days are renumbered in the one transaction; the `(day_id, position)` unique constraint is deferrable initially deferred (0004), so no temporary positions are needed.
- `apps/api/tests/api/test_edits.py`: move route tests (below).

## Behaviour

- Times follow the IMP-407 FR-060 rule (PD-IMP-407-3): the moved item takes the displaced item's start time or follows the previous item when appended; later unlocked items shift forward.
- Conflicts after a move are saved and returned as findings; the move is not reverted (FR-060 AC3).
- Stale revision: 409 `STALE_PLAN`, nothing written. Day not in the plan or position past the end: 422 `INVALID_EDIT`.
- A body with move fields and retime fields together: §6 API-26 lists move and retime as separate behaviours and does not define a combined request, so it is refused with 422 `INVALID_EDIT` (PD-IMP-409-1).

## Commands and results

PostgreSQL: the same throwaway PostgreSQL 16.2 with pgvector (pip `pgserver`) on 127.0.0.1:55432 as the remove-retime-ops part, outside the repository, stopped afterwards.

| Command | Result |
| --- | --- |
| `make test-api ARGS="-k 'move'"` | `15 passed, 406 deselected, 1 warning` |
| `make test-api` | `421 passed, 1 warning in 139.21s (0:02:19)` |
| `make test-authz` | `41 passed` |
| `make test-unit` | `1006 passed, 1 warning` |
| `make lint` | exit 0 |
| `make typecheck` | `Success: no issues found in 116 source files` |
| `make imports` | `Contracts: 6 kept, 0 broken.` |
| `make openapi` | no diff |

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-060 AC3 / TC-199 (server side): a conflicting move is saved and reported | verified | `test_tc_199_move_route_saves_a_conflicting_move_and_reports_it`: every later item moved onto day 1, each 200, a new day-1 finding, the order persisted, response equals API-24 |
| A move across days keeps positions dense in both days | verified | `test_move_route_across_days_keeps_positions_dense_in_both_days` |
| Stale revision → 409 with nothing changed | verified | `test_move_route_refuses_a_stale_revision_and_changes_nothing` |
| Position-only and day-only moves | verified | `test_move_route_within_a_day_and_to_the_end_of_a_day` |
| Invalid moves → 422 INVALID_EDIT | verified | `test_move_route_refuses_an_invalid_move_with_invalid_edit` (combined body, day 9, position 99) |

## Blockers

none

## Proposed decisions

- PD-IMP-409-1: API-26 refuses a body that mixes move fields (`day_number`, `position`) with retime fields (`start_time`, `duration_min`) with 422 `INVALID_EDIT`, because §6 does not define the combined edit. The client sends them as two edits.

## Open issues

- Screenshots: not verified — taken on the local stack by the member after merge.
