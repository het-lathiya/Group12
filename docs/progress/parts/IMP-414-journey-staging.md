# IMP-414 · journey-staging

| Field | Value |
| --- | --- |
| Run | RUN-063 (grouped run), part 2 of 2 |
| Card | IMP-414 End-to-end journey test on staging |
| Part | E2E journey test on staging (3 points) |
| Owner | Krrish Kamani |
| Status | PR_OPEN (TC-369 passes after the IMP-408 fix of RUN-063b; TC-370 and the Gemini run follow in a staging window) |
| Base commit | ee905c7 |
| Branch | feat/IMP-414-journey |

## Changed files

- `apps/web/e2e/journey.spec.ts`: the journey now signs up (local) or signs in with the staging account (when `E2E_STAGING_EMAIL` and `E2E_STAGING_PASSWORD` are set), resets the account's trips through the API, creates a SAMPLE trip with the wizard and generates. It waits for `completed`: 30 s locally, 180 s on staging, because Gemini is slower. It then removes the first item of a day with two or more items through the ItemEditor confirm dialog (API-27; the toast `Removed <place>` is a soft check, see blockers) and retimes the day's last item by 15 minutes (API-26). After a reload, and again after "Open latest" on the dashboard (API-09, IMP-410), API-24 must show the removed item gone, the new duration, the edit's `plan_revision` and the totals of the last edit's answer. The page must show the saved days. axe runs on the itinerary page (`e2e/axe.ts`). The checks are on roles and the texts the spec fixes, not on CSS. Locally, provider `MOCK` and outcome `model` are asserted. On staging the provider is whatever staging runs, and the provider, outcome and latency are printed for the report. The existing IMP-309 width checks and the "no Gemini host from the browser" check are kept.
- `.github/workflows/e2e.yml`: push to `main` and the nightly run are unchanged on the composed local stack. `workflow_dispatch` takes an input `base_url`. Empty runs the local job; set, it runs only the new `staging` job against that URL, with the secrets `E2E_STAGING_EMAIL` and `E2E_STAGING_PASSWORD`. The job runs one width with one worker, because all widths would share one account and one run's reset would delete another's trip. It uploads no Playwright report, because a trace records typed values, the password too. It never runs automatically and was not run.
- `docs/progress/parts/IMP-414-journey-staging.md`: this record.

## Commands

| Command | Result |
| --- | --- |
| `actionlint .github/workflows/e2e.yml` | exit 0 |
| `make lint` | `All checks passed!`; ESLint `✖ 1 problem (0 errors, 1 warning)` (a warning from before this run); `All matched files use Prettier code style!` |
| `make typecheck` | `Success: no issues found in 118 source files`; web `tsc --noEmit` clean |
| `make imports` | `Contracts: 6 kept, 0 broken.` |
| `make test` (API suites against a throwaway local PostgreSQL 16 with pgvector on port 55432) | `1040 passed, 1 warning`; `87 passed, 2 deselected, 1 warning`; `425 passed, 1 warning`; `41 passed`; web `Tests  186 passed (186)` |
| E2E workflow on the branch (`gh workflow run e2e.yml --ref feat/IMP-414-journey`), [https://github.com/het-lathiya/Group12/actions/runs/43427715979](https://github.com/het-lathiya/Group12/actions/runs/43427715979) attempt 2 | `Running 4 tests using 1 worker` … `4 failed`, each on `Expect "soft toBeVisible" getByText('Removed Sample Maritime Museum (sample)')` (journey.spec.ts:209); no other failing check. `generation: provider MOCK, outcome model, 2138 to 2253 ms to completed` |
| Attempt 1 of the same run | stack start failed on the runner: `failed to bind host port for 0.0.0.0:54324 … address already in use` |
| Earlier runs [43423666996](https://github.com/het-lathiya/Group12/actions/runs/43423666996), [43426753451](https://github.com/het-lathiya/Group12/actions/runs/43426753451) | `4 failed`: first a test bug, the DELETE URL carries `?plan_revision=` (IMD-26) and is now matched by pathname; then the same missing toast |

Not run: `make e2e ARGS='journey'` locally, because this machine has no Docker for the local Supabase stack. The staging job was not run, because staging is off (IMD-137).

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| TC-369: the journey passes with MOCK on the local stack in CI | not verified (fails on a product bug) CI run above: every step passes at every width except the removal toast |
| TC-370: the journey passes on staging with MOCK; the Gemini run is recorded with its date | not verified: staging window | The manual `staging` job is ready; it needs a staging window, the two secrets and API-12 (see the fixtures part's blockers) |

## Blockers

- **Product bug, IMP-408 item-editor (owner Manasvi):** after a removal is confirmed and API-27 answers 200, the toast `Removed <place>` (with its Undo action) never appears, and focus does not move to the next card. `ItemEditor.confirmRemove` passes `onSuccess` to `remove.mutate(...)`. `useItemEdit`'s own `onSuccess` (`apps/web/lib/api/queries.ts`) writes the changed day into the cache before that runs, so the removed card's `ItemEditor` unmounts, and TanStack Query v5 skips per-call callbacks once the calling component has unmounted. The unit test `tests/unit/itinerary/ItemEditor.test.tsx` misses it because the card stays on screen there. A likely fix is to show the toast and move focus from a callback that does not depend on the unmounted card, for example `mutateAsync` or the mutation's `onSuccess` in the hook. This run does not change product code (stop condition). The journey keeps the check as `expect.soft`, so it still fails on the bug and still runs the steps after it.
- The staging reset depends on API-12, which is a 501 stub until IMP-602; see PD-IMP-414-1 in `IMP-414-journey-fixtures-report.md`.

## Proposed decisions

- **PD-IMP-414-3 (staging switch):** the staging differences (sign in instead of sign up, a 180 s wait for `completed`) switch on the presence of the staging account secrets, not a separate flag. The AI provider is not chosen by the test.

## Open issues

- The staging job's first run, in the next staging window, records its result in `docs/test-reports/journey-sprint4.md`.

## Fix RUN-063b

| Field | Value |
| --- | --- |
| Run | RUN-063b |
| Owner | Krrish Kamani |
| Status | PR_OPEN |
| Base commit | ee905c7 |

The IMP-408 blocker above is fixed in this PR by Manasvi's commit `fix(web): IMP-408 removal toast and focus survive the card unmount` (see the "Fix RUN-063b" section of `IMP-408-item-editor.md`).

**Change.** `apps/web/e2e/journey.spec.ts`: the toast check `Removed <place>` is a hard `expect` again, and a new check confirms that focus is on the day's next card (`#item-<id>`) after the removal. Nothing else in the journey changed.

**Commands**

| Command | Result |
| --- | --- |
| `make lint` | `All checks passed!`; ESLint `✖ 1 problem (0 errors, 1 warning)` (a warning from before this run); `All matched files use Prettier code style!` |
| `make typecheck` | `Success: no issues found in 118 source files` |
| `make imports` | `Contracts: 6 kept, 0 broken.` |
| `make test` (API suites against a throwaway local PostgreSQL 16 with pgvector) | `1040 passed, 1 warning`; `87 passed, 2 deselected, 1 warning`; `425 passed, 1 warning`; `41 passed`; web `Tests  187 passed (187)` |
| E2E workflow on the branch, [https://github.com/het-lathiya/Group12/actions/runs/43431854989](https://github.com/het-lathiya/Group12/actions/runs/43431854989) (head `f741fd6`) | `Running 4 tests using 1 worker` … `4 passed (36.7s)`; no retry; `generation: provider MOCK, outcome model, 2097 to 2135 ms to completed` |

**Acceptance (replaces the TC-369 row above)**

| Criterion | Status | How |
| --- | --- | --- |
| TC-369: the journey passes with MOCK on the local stack in CI | verified | E2E run above: all four widths pass, with the hard toast and focus checks |
| TC-370: the journey on staging with MOCK; the Gemini run recorded | not verified: staging window | unchanged; the job needs a fresh staging account with no trips and the secrets `E2E_STAGING_EMAIL` and `E2E_STAGING_PASSWORD` (IMD-163, IMD-164) |
