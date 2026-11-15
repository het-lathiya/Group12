# IMP-610 · restore-retention

- Run id: RUN-075
- Owner: Malhar Mer, 2 points
- Status: implemented; PR not opened (batch run, the lead integrates)
- Base commit: a6307c3 (on top of the version-snapshots part)
- Steps: 2, the restore half of 3; FR-095 AC2 (TC-257, TC-318), TC-319, IMD-18, IMD-23, Amendment A1 §5.5.

## Files changed

- apps/api/app/itinerary/versions.py: `restore` (API-38) in the request's one transaction: lock the trip, 409 GENERATION_IN_PROGRESS before 409 STALE_PLAN, 404 for a version of another trip, write a `restore` version of the current plan (the replaced plan stays in history), then rebuild through the edit core and answer API-24's current `ItineraryOut`. Every snapshot write ends with retention.
- apps/api/app/itinerary/service.py: `retain_versions` (IMD-18): past 20 versions per trip the oldest automatic versions are deleted; named versions and the newest version never are. With the switch `versions` off only two automatic versions stay (the current plan's version and one backup copy of the previous plan). Called after the generation save.
- apps/api/app/itinerary/edits.py (not in the part's file list; reused instead of copying the recalculation): a `Restore(snapshot)` operation that replaces days and items from snap-1 (locks, notes, origins and `source_chunk_ids` come back; dates follow the trip's start date; prices from the budget engine) and recalculates positions and travel on every day without moving start times; `apply_edit` takes `reason` (default `edit`, restore passes `restore`) and calls `retain_versions` after its version write. So a restore validates the whole plan, saves the new revision's warnings, bumps plan_revision once and writes a `restore` version of the result.
- apps/api/app/itinerary/repository.py (SQL for the above): `version_heads`, `delete_versions`, `delete_days`.
- apps/api/tests/api/test_versions.py: restore and retention cases.

## Commands and results

Database: a throwaway local PostgreSQL 16.2 + pgvector on 127.0.0.1:55432 (database travel_test_i), with PYTHONPATH set to the worktree's apps/api.

- `make test-api ARGS='-k versions -q -p no:warnings'`: `23 passed, 461 deselected in 11.77s`
- `make test-api ARGS='-q -p no:warnings'`: `484 passed in 158.17s (0:02:38)`
- `make test-authz ARGS='-q -p no:warnings'`: `53 passed in 30.74s`
- API `ruff check .`: `All checks passed!`; `ruff format --check .`: `230 files already formatted`; `mypy app`: `Success: no issues found in 123 source files`; `make imports`: `Contracts: 6 kept, 0 broken.` (no web files changed in this part)
- Not run: `make e2e` (no Docker on this machine).

## Acceptance

- TC-257 (FR-095 AC2, restored version becomes current): verified, `test_tc_257_tc_318_restore_makes_the_version_current_and_keeps_the_replaced_plan` (same places, times and locks as the version, recalculated totals, plan_revision + 1, API-24 answers the same plan, `version_id` is the new restore version).
- TC-318 (the replaced plan stays in history): verified in the same test; the pre-restore `restore` version reads back as the replaced plan through API-24 `version_id`.
- TC-319 (the limit removes only the oldest automatic version): verified, `test_tc_319_the_limit_removes_only_the_oldest_automatic_version`; named versions are never pruned, also past 20.
- A stale screen editing after a restore gets 409 STALE_PLAN: verified, `test_restore_a_stale_screen_editing_after_a_restore_gets_409_stale_plan` (edit and a repeated restore, nothing written).
- Restore brings back citations, locks and notes (A1 §5.5): verified, `test_restore_brings_back_locks_notes_and_citations`.
- Switch off keeps one backup copy: verified, `test_retention_with_the_switch_off_keeps_one_backup_copy`.
- 409 GENERATION_IN_PROGRESS for restore: verified by the version-snapshots part's test, now against the real restore.

## Blockers, proposed decisions, open issues

- PD-RUN-075-I1: §5.8 names one `restore` version (of the replaced plan); the card says "snapshot current … write a restore version". Both are written: the replaced plan (old revision) and the restored result (new revision), so the current plan always has a version (`ItineraryOut.version_id`, API-09). The team may prefer only the first.
- PD-RUN-075-I2: IMD-18 and the card say "one backup copy" with the switch off; read here as two automatic versions (current plus one backup), counting automatic versions only.
- A place that no longer exists in the data is skipped by a restore and by a preview (shortcut comment in code); places are not hard-deleted today.
