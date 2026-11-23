# IMP-721 · orm-tests part (ORM model, MIGRATION_HEAD, migration tests)

- Card: IMP-721 Migration 0008: live destination columns (Amendment A2 §4, §12; 0 points)
- Part: ORM model, `MIGRATION_HEAD`, migration tests
- Run id: RUN-089 (Batch C1a, Sprint 7, inserted under IMD-215)
- Owner: Jeel (Jeel Fefar)
- Status: PR_OPEN candidate on `feat/S7-C1a-any-city-foundation`
- Base commit: 08587c0 (on `main`)
- Traces to: IMD-210, IMD-216; A2 §4.1, §4.2, §3.3; TC-463

## Changed files

- `apps/api/app/db/models/places.py`: `Destination` gains the twelve 0008 columns (`data_tier` with server default `'curated'`; `import_requested_by` as a foreign key to `profiles.id` `on delete set null`; the rest nullable).
- `apps/api/app/core/health.py`: `MIGRATION_HEAD = "0008"`.
- `apps/api/tests/api/test_live_destinations_schema.py` (create): a valid live row is accepted; existing (Sampleton) rows read `curated` with null live fields; the CHECKs reject a live row without `external_ref`, a curated row with an import status, a live SAMPLE row, a failed row without a reason, a reason without a failure and ten out-of-range values; the unique index rejects a duplicate `(provider, external_ref)`; `import_requested_by` is set null when the profile is deleted; the three indexes exist; the newest revision is `0008` and equals `MIGRATION_HEAD`.
- `docs/progress/parts/IMP-721-orm-tests.md` (this record).

`apps/api/tests/api/test_schema_drift.py` is not changed.

## Commands

| Command | Result line |
| --- | --- |
| `make db-up && make test-api ARGS='-k "live_destinations_schema or drift"'` | `58 passed, 555 deselected, 1 warning in 1.52s` |
| `make test-api` (whole API suite, includes `test_health.py` with the new head) | `613 passed, 1 warning in 114.36s (0:01:54)` |

## Acceptance

- TC-463: the CHECKs and the unique index reject the invalid rows of IMP-721 step 5, and existing rows read `curated`: **verified** (`test_live_destinations_schema.py`, 23 tests passed).
- `test_schema_drift.py` passes unchanged: **verified** (35 passed; file not in the diff).
- Readiness reports the new head: **verified** (`test_health.py` compares `MIGRATION_HEAD` with the head of `migrations/versions`, passed in the API run).

## Open issues

none

## Proposed decisions

none

## Blockers

none
