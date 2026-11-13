# IMP-414 · journey-fixtures-report

| Field | Value |
| --- | --- |
| Run | RUN-063 (grouped run), part 1 of 2 |
| Card | IMP-414 End-to-end journey test on staging |
| Part | Journey test fixtures, test report (2 points) |
| Owner | Mohammad Junaid Kureshi |
| Status | TESTS_FAILING (the journey fails on one product bug in IMP-408; this part's fixtures worked in CI) |
| Base commit | ee905c7 |
| Branch | feat/IMP-414-journey |

## Changed files

- `apps/web/e2e/fixtures/users.ts`: `stagingAccount()` reads the pre-created staging account from `E2E_STAGING_EMAIL` and `E2E_STAGING_PASSWORD` (null when neither is set, an error when only one is). The service-role admin client is now built on first use, so a staging run, which creates no user, needs no service-role key.
- `apps/web/e2e/fixtures/trips.ts` (created): `TestTrips` takes the API base and bearer token from a request the signed-in page sent, then deletes every trip of the account through the API (API-08 with `include_archived=true`, API-12 per trip), never by database access. The `trips` fixture deletes the staging account's trips after the run. A local account is removed by the `users` fixture, and its trips go with it (`on delete cascade` from `auth.users` through `profiles`). The token stays in memory and is never printed.
- `docs/test-reports/journey-sprint4.md` (created): the three sections, the CI result filled in, both staging sections "not run yet — staging window, IMD-137".
- `docs/secrets.md`: a row for the new CI secrets `E2E_STAGING_EMAIL` and `E2E_STAGING_PASSWORD` (Kirtan creates the account and both secrets).
- `docs/progress/parts/IMP-414-journey-fixtures-report.md`: this record.

## Commands

| Command | Result |
| --- | --- |
| `make lint` | `All checks passed!`; ESLint `✖ 1 problem (0 errors, 1 warning)` (a warning from before this run); `All matched files use Prettier code style!` |
| `make typecheck` | `Success: no issues found in 118 source files`; web `tsc --noEmit` clean |
| `make imports` | `Contracts: 6 kept, 0 broken.` |
| `make test` (API suites against a throwaway local PostgreSQL 16 with pgvector on port 55432) | `1040 passed, 1 warning`; `87 passed, 2 deselected, 1 warning`; `425 passed, 1 warning`; `41 passed`; web `Tests  186 passed (186)` |
| E2E workflow on the branch, [https://github.com/het-lathiya/Group12/actions/runs/43427715979](https://github.com/het-lathiya/Group12/actions/runs/43427715979) | `4 failed` (only the soft check of the removal toast, a product bug; see the staging part); every width signed up, reset (API-08 answered, 0 trips), ran the whole journey and deleted its account in teardown without error |

Not run: `make e2e` locally, because this machine has no Docker for the local Supabase stack. The CI run above is the evidence.

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| Test data is created through the app and removed after the run (card criterion 3), local stack | verified (local stack in CI) | The journey signs up through the UI, resets the account's trips through API-08 before the run, and the `users` fixture deletes each account afterwards (cascade). In the CI run above: the reset ran at every width, and the `users` teardown deleted each account with no error. There was no separate count query in CI |
| The same on staging, through API-12 | not verified | Staging window (IMD-137); API-12 is still a 501 stub (see blockers) |
| The report exists with the CI result | verified | `docs/test-reports/journey-sprint4.md`, section "Local stack in CI (MOCK)" |

## Blockers

- API-12 (`DELETE /api/v1/trips/{trip_id}`) answers 501 `NOT_IMPLEMENTED` on `main`; IMP-602 (Sprint 6) builds it. Until then the staging reset fails as soon as the staging account owns a trip, so the staging job's first run passes and later runs fail at the reset with "API-12 answered 501". The local run is not affected, because a new account has no trips and is deleted with its trips.

## Proposed decisions

- **PD-IMP-414-1 (staging trip reset):** either bring API-12 (soft delete, IMP-602 step 3) forward before the IMP-414 staging window, or accept for the Sprint 4 window that the staging account's trips are deleted by hand through the app's API by Kirtan. Proposed: bring API-12 forward.
- **PD-IMP-414-2 (new CI secrets):** `E2E_STAGING_EMAIL` and `E2E_STAGING_PASSWORD`, GitHub Actions secrets for a pre-created, confirmed staging account; registered in `docs/secrets.md`. Kirtan creates both before the staging window.

## Open issues

- The staging and Gemini sections of the report are filled in after the staging window.
