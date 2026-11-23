# IMP-721 · migration-sql part (migration SQL, down file and Alembic revision)

- Card: IMP-721 Migration 0008: live destination columns (Amendment A2 §4, §12; 0 points)
- Part: migration SQL, down file and Alembic revision (lead)
- Run id: RUN-089 (Batch C1a, Sprint 7, inserted under IMD-215)
- Owner: Malhar (Malhar Mer)
- Status: PR_OPEN candidate on `feat/S7-C1a-any-city-foundation`
- Base commit: 08587c0 (on `main`)
- Traces to: IMD-210, IMD-215, IMD-216; A2 §4.1, §4.2, §3.3; TC-463

## Changed files

- `apps/api/migrations/sql/0008_live_destinations.sql` (create): the twelve columns of A2 §4.1 on `public.destinations`, all nullable except `data_tier` (not null, default `'curated'`); column CHECKs for every enumerated or ranged value (`data_tier`, `provider`, `external_ref` format `^[NWR][0-9]{1,12}$`, `import_status`, `import_failure_reason`, `places_found >= 0`, `places_usable >= 0`, `nearby_city` 1 to 120 characters); `import_requested_by` references `public.profiles(id)` (the table `trips.user_id` references) `on delete set null`; constraints `ck_destinations_tier`, `ck_destinations_failure` and `ck_destinations_nearby_city` ("set only with `insufficient_data`", the rule column of §4.1); indexes `ux_destinations_provider_ref` (unique, partial), `ix_destinations_import_active` (partial) and `ix_destinations_import_requester` (partial). No new table, no column on `places`, no change to `data_sources` and no RLS or grant statement.
- `apps/api/migrations/sql/down/0008_live_destinations.down.sql` (create): drops the three indexes, the three named constraints and the twelve columns.
- `apps/api/migrations/versions/0008_live_destinations.py` (create): `revision = "0008"`, `down_revision = "0007"`, same shape as 0007.
- `docs/progress/parts/IMP-721-migration-sql.md` (this record).

## Commands

| Command | Result line |
| --- | --- |
| `(cd apps/api && .venv/bin/alembic heads)` | `0008 (head)` |
| `DATABASE_URL=<compose test db> (cd apps/api && alembic upgrade head && alembic downgrade base && alembic upgrade head && alembic heads)` | `Running downgrade 0008 -> 0007 …` … `Running upgrade 0007 -> 0008 …` then `0008 (head)` |
| `make db-up && make test-api ARGS='-k "live_destinations_schema or drift"'` | `58 passed, 555 deselected, 1 warning in 1.52s` |
| `make test-api` (whole API suite on the branch) | `613 passed, 1 warning in 114.36s (0:01:54)` |

The round trip ran against the compose test database (`localhost:5432/travel_test`, set through `DATABASE_URL` in the shell) so that `downgrade base` never touched a developer database. The CI round-trip job link is added when CI runs on the pull request.

## Acceptance

- The round trip passes and `alembic heads` prints one head, `0008 (head)`: **verified** (commands above).
- `test_schema_drift.py` passes unchanged: **verified** (35 drift tests in the 58 above; the file is not in this branch's diff).
- Every existing test passes: **verified** for the API suite (613 passed); the whole `make check` result is in the SYNC REPORT.
- Only nullable or defaulted columns; constraints and indexes as §4.1; no new table, no RLS change: **verified** by reading the SQL and by the schema tests of the ORM part (`IMP-721-orm-tests.md`).

## Open issues

- `ck_destinations_nearby_city` is a named constraint for the §4.1 rule "set only with `insufficient_data`"; §4.1 lists it in the rule column rather than under "Constraints". Recorded so the reviewer can check the reading.

## Proposed decisions

none

## Blockers

none
