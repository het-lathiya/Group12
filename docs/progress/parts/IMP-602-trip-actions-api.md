# IMP-602 · trip-actions-api

- Run id: RUN-075
- Owner: Manal Patel, 6 points (card lead)
- Status: implemented; API, authz and component tests pass locally
- Base commit: a6307c3
- Steps: 1–5, 7 and the menu half of step 6; FR-012, FR-015; TC-082 to TC-084, TC-089 to TC-091, TC-345, TC-346, TC-372; IMD-11, IMD-31, IMD-35; Amendment A1 §6.10.

## Files changed

- apps/api/app/trips/router.py: API-12 and API-13 are built (no longer 501 stubs); API-13 passes `itinerary.service.copy_plan` to the service.
- apps/api/app/trips/service.py: `ensure_not_archived` (IMD-35 guard, 409 CONFLICT), the `trip_management` switch on API-11 `status`, API-12 and API-13 (404 when off), `delete_trip`, `duplicate_trip`, `purge_deleted_trips` (30 days).
- apps/api/app/trips/repository.py: `soft_delete`, `insert_copy`, `copy_preferences_and_places`, `purge_deleted`.
- apps/api/app/itinerary/service.py: one block at the end, `# IMP-602 duplicate`, with `copy_plan`. It copies days, items (with `is_locked` and `source_chunk_ids`) and the current revision's warnings, then sets the copy to plan_revision 1. Nothing else in itinerary/ changed.
- apps/api/app/generation/jobs.py: the daily purge in `reap_forever` also deletes trips soft-deleted more than 30 days ago (IMD-31).
- apps/web/components/trips/TripActionsMenu.tsx (new): Rename (dialog), Duplicate, Archive (ConfirmDialog) or Restore, and Delete (destructive ConfirmDialog). It is hidden when `trip_management` is off.
- apps/web/lib/api/queries.ts: one appended block, `// IMP-602 trip actions`, with `useDeleteTrip` and `useDuplicateTrip`. Rename, archive and restore use the existing `useUpdateTrip`.
- apps/api/tests/api/test_trips.py: new tests for TC-082, TC-083, TC-084, TC-089, TC-090, TC-091, rename, foreign 404, archived duplicate and delete, the switch, and the purge.
- apps/api/tests/authz/route_matrix.py: one appended block, `# IMP-602 trip actions`, with API-11 archive, API-12 and API-13 as foreign routes.
- apps/api/tests/contract/test_openapi_contract.py: the 501-envelope test used the API-12 stub, which is now built. It now uses the API-31 stub instead (IMP-607, not in this batch). Same assertion.
- apps/web/tests/unit/trips/TripActionsMenu.test.tsx (new); this record.

## Commands and results

The database was a throwaway local PostgreSQL 16.2 + pgvector on 127.0.0.1:55432 (database travel_test_t). `PYTHONPATH=apps/api` was set so that pytest imports the worktree's code and not the shared venv's editable install.

- `make test-api ARGS='-k "dashboard or duplicate or archive or delete"'`: `22 passed, 456 deselected, 1 warning in 6.66s`
- `make test-api ARGS='-k purge'`: `2 passed, 476 deselected, 1 warning in 1.76s`
- `make test-api` (full API suite): `478 passed, 1 warning in 149.42s (0:02:29)`
- `make test-authz`: `53 passed in 26.40s`
- `make test-contract`: `91 passed, 2 deselected, 1 warning in 20.73s`
- `make test-web ARGS='tests/unit/trips/TripActionsMenu.test.tsx'`: `Tests  7 passed (7)`, `Duration  2.07s`
- `make lint`: `All checks passed!`, `All matched files use Prettier code style!`. The one existing ESLint warning (AppShell navigation) is not from this part; exit 0.
- `make typecheck`: `Success: no issues found in 122 source files`; tsc clean
- `make imports`: `Contracts: 6 kept, 0 broken.`
- `make openapi-check`: `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date`. The API-12 and API-13 shapes were already declared (IMD-37), so there is no drift.

## Not run

- `make e2e`: Docker is not available on this machine.

## Acceptance

- FR-012 AC1–AC3 (TC-082 to TC-084): verified by `test_tc_082_*`, `test_tc_083_*` and `test_tc_084_*` (title, destination, dates and status are listed; an empty page; archived trips appear only with `include_archived=true`).
- FR-015 AC1 (TC-089): verified by `test_tc_089_*`. The source's rows in every plan table are byte-identical before and after. Days, items, `is_locked`, `source_chunk_ids` (A1 §6.10), preferences, trip_places, budget settings and the warning (remapped to the copied item) are copied. The copy gets plan_revision 1; no generation is copied.
- FR-015 AC2 (TC-090): verified by `test_tc_090_*`. The response is 204. The trip is hidden from API-08 and API-10, a second delete returns 404, and the rows stay until the purge.
- FR-015 AC3 (TC-091): verified for the trips module's own routes (API-11 changes, API-14), which return 409 while the trip is archived. Restoring gives `ready` when the trip has days. Archived trips can still be duplicated and deleted. The itinerary edit routes are not guarded yet: see the wiring below.
- TC-345, TC-346: verified. The authz suite runs API-11 archive, API-12 and API-13 as user B and gets 404 with A unchanged, and the control calls reach A. `test_duplicate_and_delete_of_another_users_trip_are_404` also covers this.
- TC-372 (API side): verified by `test_trip_management_off_*`. With the switch off, archive, delete and duplicate return 404, while list, create and wizard title edits still work. Web: the menu renders nothing (component test).
- IMD-31 purge: verified by `test_purge_removes_*`. A trip deleted 31 days ago is purged with its children; trips deleted 29 days ago, or not deleted, are kept.
- Screenshot: not taken here (no local stack). The member adds it.

## Wiring for the lead (IMD-35 guard in other modules, not edited here)

- apps/api/app/itinerary/edits.py, `apply_edit`, after `if trip_row is None: raise NotFound()` (line 147): add `trips_service.ensure_not_archived(trip_row.status)`. This covers API-25, API-26, API-27, API-29 and move.
- apps/api/app/itinerary/service.py, `revalidate`, after `if trip_row is None: raise NotFound()` (line 377): add `trips_service.ensure_not_archived(trip_row.status)` (API-32 writes warnings).
- generation/service.py:77 and budget/service.py:109 already return 409 with their own `Conflict`. They could call the shared guard; this is optional.
- API-19 and API-20 (places, IMP-605) should call the guard when they are built.

## Proposed decisions / open issues

- PD-RUN-075-T1: the status of a duplicated trip. §6.6.2 API-13 says the copy is `status draft`, while §5 says "draft or ready". Built: `ready` when the source has preferences, else `draft`, following IMD-25 (a draft becomes ready when its preferences are saved). Otherwise a copied plan would need its preferences saved again before it could be generated. The decision register should confirm this.
- The card's step 1 names a `status` filter; §6.6.2 API-08 names `include_archived`. The specification wins, so the existing `include_archived` is kept and no new query parameter is added.
- On API-11, the switch guards only `status` (archive and restore). Title edits stay available because the wizard (IMP-410, IMP-510) edits the title through the same route. The menu hides Rename when the switch is off.
- No new endpoints, tables, environment variables, error codes or dependencies.
