# IMP-610 · version-snapshots

- Run id: RUN-075
- Owner: Jeel Fefar, 6 points
- Status: implemented; PR not opened (batch run, the lead integrates)
- Base commit: a6307c3
- Steps: 1, 3 (API-36 list, API-37 save, API-38 route shell), 4, 5; FR-095 AC1 (TC-256), IMD-18, IMD-23, Amendment A1 §5.5.

## Files changed

- apps/api/app/itinerary/versions.py (created): snap-1 snapshot of the stored plan (days, items with locks, notes, origin and `source_chunk_ids`, budget settings, plan_revision; no costs, travel or findings); `snapshot_before_regeneration` (reason regeneration, written also with the switch off) for IMP-607; API-36 list; API-37 named save (reason manual, 409 CONFLICT on a duplicate name, 409 GENERATION_IN_PROGRESS before 409 STALE_PLAN); API-38 shell (switch, ownership, generation, revision and version checks, then 501 until restore-retention); API-24 `version_id` read (snapshot priced by the budget engine and validated on read, nothing written; a snapshot without citations reads as empty). Switch `versions` off: API-36 to API-38 and version reads answer 404.
- apps/api/app/itinerary/router.py: API-36 to API-38 call versions.py; API-24 with `version_id` goes to `versions.read_version`.
- apps/api/app/itinerary/service.py: `get_itinerary` no longer takes `version_id` (its interim 501 is gone); uses the version row `insert_version` now returns.
- apps/api/app/itinerary/repository.py (needed for the SQL, not in the card's list): `insert_version` takes `name` and returns the row; `list_versions`, `version_name_taken`, `places_by_ids`.
- The pipeline save step (reason generation or fallback) and every edit (reason edit, edits.py) already wrote versions before this part; no change was needed in generation/pipeline.py or itinerary/edits.py.
- apps/web/lib/api/queries.ts (appended block `// IMP-610 versions`): `useVersions`, `useSaveVersion`, `useRestoreVersion` (restore invalidates versions, itinerary, costs, summary, trip).
- apps/web/components/versions/VersionList.tsx (created), apps/web/app/(app)/trips/[tripId]/versions/page.tsx (created; notFound while `versions` is off; EmptyState with a link to generate when there is no plan).
- apps/api/tests/api/test_versions.py (created), apps/web/tests/unit/versions/VersionList.test.tsx (created).
- apps/api/tests/api/test_itinerary.py: removed `test_reading_a_stored_version_is_not_built_yet`, which asserted the interim 501 this part replaces; version reads are covered in test_versions.py.
- apps/api/tests/authz/route_matrix.py and test_ownership.py (appended blocks `# IMP-610 versions`): API-36, API-37, API-38 rows; API-38's version_id is A's newest version, looked up as A through API-36.

## Commands and results

Database: a throwaway local PostgreSQL 16.2 + pgvector on 127.0.0.1:55432 (database travel_test_i), with PYTHONPATH set to the worktree's apps/api.

- `make test-api ARGS='-k versions -q'`: `17 passed, 461 deselected, 1 warning in 8.20s`
- `make test-api ARGS='-q -p no:warnings'`: `478 passed in 155.58s (0:02:35)`
- `make test-authz ARGS='-q -p no:warnings'`: `53 passed in 26.33s`
- `make test-web ARGS='tests/unit/versions'`: `Tests  4 passed (4)` (1.8 s wall time)
- `make lint`: `All checks passed!`; web `✖ 1 problem (0 errors, 1 warning)` (an existing warning outside this part); `All matched files use Prettier code style!`
- `make typecheck`: `Success: no issues found in 123 source files`; `✓ Types generated successfully`
- `make imports`: `Contracts: 6 kept, 0 broken.`
- `make openapi-check`: `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date`
- Not run: `make e2e` (no Docker on this machine).

## Acceptance

- TC-256 (FR-095 AC1): verified for the hook; `test_tc_256_regeneration_hook_stores_a_snap_1_snapshot_of_the_current_plan` and the switch-off case. Calling it when a regeneration starts is IMP-607.
- A duplicate version name returns 409 CONFLICT: verified, `test_versions_a_duplicate_name_is_409_conflict`.
- API-37 and API-38 return 409 GENERATION_IN_PROGRESS while a job is active: verified, `test_versions_save_and_restore_are_refused_while_a_generation_is_active`.
- API-24 `version_id` recomputes on read and writes nothing: verified, `test_reading_a_version_prices_and_validates_the_snapshot_and_writes_nothing`; foreign version 404 verified.
- With 'versions' disabled the routes answer 404 and the current plan reads (TC-372 API half): verified, `test_versions_switch_off_hides_the_routes_and_version_reads`. The E2E floor journey is not verified (no Docker).
- TC-257, TC-318, TC-319, named versions never pruned, stale screen after a restore gets 409: restore-retention part.
- Versions page screenshot after a restore: not verified (needs the restore part and a running stack).

## Blockers, proposed decisions, open issues

- A version preview shows no travel lines: snap-1 holds no travel (§5.2) and a read must write nothing, so routing (which writes the route cache) is not called; a restore recalculates travel.
- The versions tab link in the trip navigation is for the lead (shared navigation).

## Integration wiring (RUN-075, same owner)

- `apps/web/components/shell/AppShell.tsx`: "Versions" trip tab to `/trips/<tripId>/versions`, left out of the navigation when the `versions` switch is off (IMD-11).
- `tests/unit/shell/AppShell.test.tsx`: the open-trip case also checks the Versions link.
