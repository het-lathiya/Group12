# RUN-077 · one-backup

- Run id: RUN-077
- Owner: Malhar Mer, 0 points (follow-up of IMP-610 restore-retention, IMD-191)
- Status: test added; no code change needed (the existing retention already keeps exactly one backup)
- Base commit: 0e15ae7
- Scope: IMD-191 (PD-RUN-075-I2): with 'versions' in FEATURES_DISABLED exactly one backup copy of the previous itinerary is kept for regeneration (blueprint §25.6 item 1); IMD-11, IMD-18.

## Files changed

- apps/api/tests/api/test_versions.py: `test_switch_off_keeps_exactly_one_backup_after_repeated_regenerations`. A named version is saved with the switch on, then the switch is turned off and the whole itinerary is regenerated three times through API-31 (mode rule_based, MOCK job path). It asserts: the named version remains; apart from the current plan's own version (API-24 `version_id`) exactly one automatic version remains, and it is the `regeneration` snapshot of the previous plan (plan_revision current - 1, no generation_id); API-38 restore of it answers 404.
- docs/progress/parts/RUN-077-one-backup.md: this record.

## Finding

The test passed on the first run, before any code change: 1 backup. `service.retain_versions` (called by every version write: `service.save_plan`, `service.save_regeneration`, `edits.apply_edit` and `versions.snapshot_current`, which `snapshot_before_regeneration`, `save_named` and `restore` use) keeps two automatic versions with the switch off: the current plan's version and one backup. The current plan's version cannot go (API-24 and API-23 report it as `version_id` and `itinerary_version_id`, and the newest version is never deleted), so two automatic rows is "one backup copy" in IMD-191's sense. PD-RUN-075-I2 counted those two rows, not two backups. So `apps/api/app/itinerary/versions.py` and `service.py` are unchanged.

## Commands and results

Database: a throwaway local PostgreSQL 16 + pgvector on 127.0.0.1:55432 (database travel_test_v).

- Before any code change: `pytest tests/api/test_versions.py -q -p no:warnings -k exactly_one_backup`: `1 passed, 19 deselected in 1.24s` (not red: one backup found)
- `pytest tests/api/test_versions.py -q -p no:warnings`: `20 passed in 11.13s`
- `make test-api ARGS='-q -p no:warnings'`: `565 passed in 214.42s (0:03:34)`
- `make test-authz ARGS='-q -p no:warnings'`: `71 passed in 40.18s`
- `pytest tests/unit -q -p no:warnings -k "itinerary or edit or version"`: `31 passed, 1154 deselected in 2.63s`
- `ruff check tests/api/test_versions.py`: `All checks passed!`; `ruff format --check tests/api/test_versions.py`: `1 file already formatted`
- Not run: `make e2e` (no Docker on this machine), `make check` in full (CI runs it).

## Acceptance

- With 'versions' off, exactly one backup remains after more than two regenerations: verified, the new test.
- Named versions are never deleted with the switch off: verified, the same test.
- Restore stays 404 with the switch off: verified, the same test and `test_versions_switch_off_hides_the_routes_and_version_reads`.

## Blockers, proposed decisions, open issues

- Blockers: none.
- PD-RUN-077-V1: close PD-RUN-075-I2 as "already met". "One backup copy" means one automatic version next to the current plan's own version. That is what the code does, so nothing changes.
- Open issue: an edit after a regeneration makes the replaced plan the backup, and the pre-regeneration snapshot is dropped. Either one is a copy of the previous itinerary, and with the switch off nothing can be restored.
