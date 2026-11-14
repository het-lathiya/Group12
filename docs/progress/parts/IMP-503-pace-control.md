# IMP-503 · pace-control

- Run id: RUN-069
- Owner: Manasvi Rathore (Manasvi1704), 1 point
- Status: verified
- Base commit: 4c6c693
- Step: 4; FR-029, TC-129/130; IMD-175.

## Files changed

- apps/web/components/trips/PreferenceForm.tsx: clear pace guidance and field-error presentation; existing controlled selector and full preference save already include pace.
- apps/web/tests/unit/trips/TripWizard.test.tsx: resumed form changes balanced to busy and verifies API-14 PUT carries pace and no plan_stale field. The existing complete journey also verifies relaxed pace survives both preference and must-visit saves.
- This record.

## Commands and results

- `make test-web ARGS='TripWizard'`: `Test Files  1 passed (1)`; `Tests  15 passed (15)`.
- The new test waits for loaded preference controls and scopes Balanced to the pace group; no behavior assertions were removed.

## Acceptance

- Verified saved default, changed pace and API-14 body; no client stale-plan calculation.
- plan_stale is owned by the backend (IMD-175), with Batch A API tests; DB verification not repeated here because PostgreSQL is unavailable.

## Proposed decisions / open issues

- No new decisions, contract changes, migrations or dependencies.
- After-generation stale/regeneration journey awaits CI and IMP-607.
