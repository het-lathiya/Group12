# IMP-701 · whole-task

| Field | Value |
| --- | --- |
| Run | RUN-081 |
| Card | IMP-701 End-to-end regression suite for all primary scenarios |
| Part | Whole task (3 points) |
| Owner | Krrish |
| Status | PARTIAL (specs, projects and workflow written and statically checked; no E2E run on this machine, evidence is the CI dispatch of the PR head) |
| Base commit | a4c2a0b |
| Branch | wt/S7A-e (PR branch `feat/IMP-701-e2e-regression`, opened by the operator) |

## Changed files

- `docs/test-reports/e2e-sprint7.md` (created): the E2E-01 to E2E-08 gap list, written first; the three `--repeat-each=3` runs marked not run; the CI dispatch section.
- `apps/web/e2e/generate.spec.ts` (created; the card says "modify", but the file did not exist): E2E-03.
- `apps/web/e2e/validate-costs.spec.ts` (created): E2E-04.
- `apps/web/e2e/reopen.spec.ts` (created): E2E-06, TC-217.
- `apps/web/e2e/provider-failure.spec.ts` (created): E2E-07, TC-371, project `provider-failure` only.
- `apps/web/e2e/ownership.spec.ts` (created): E2E-08, TC-375.
- `apps/web/e2e/keyboard.spec.ts` (created): TC-374, Tab and Enter only, axe after each page.
- `apps/web/e2e/extensions.spec.ts` (created): TC-432, tag `@ext`.
- `apps/web/e2e/itinerary-edit.spec.ts` (modified; the card says "create", but it exists from IMP-607): new test `E2E-05 TC-376` for card step 3; the IMP-607 test is unchanged.
- `apps/web/e2e/auth.spec.ts`, `trip-create.spec.ts`, `journey.spec.ts` (modified): titles start with the E2E or TC ID; `trip-create.spec.ts` gains the dashboard check of E2E-02.
- `apps/web/e2e/fixtures/trips.ts` (modified): shared steps `signIn`, `signOut`, `plannedTrip`, `readItinerary`, `finishedGeneration`, `daysFromNow` (API set-up with the page's own token, as `itinerary-edit.spec.ts` did). Users still come only from `fixtures/users.ts`; no second user helper. `fixtures/users.ts` needed no change.
- `apps/web/e2e/axe.ts` (modified): `expectNoSeriousA11y`, the journey's serious-violation scan, shared by the new specs.
- `apps/web/playwright.config.ts` (modified): `retries: 0`, `trace: "retain-on-failure"` (on-first-retry never fires without retries), width projects ignore `provider-failure.spec.ts`, project `provider-failure` (base URL `PROVIDER_FAILURE_BASE_URL`, default `http://localhost:3001`), project `floor-journey`.
- `.github/workflows/e2e.yml` (modified): see "Workflow" below.
- `.github/pull_request_template.md` (modified): checkbox "E2E specs touched by this change pass locally (make e2e)".
- `docs/progress/parts/IMP-701-whole-task.md`: this record.

## How the card steps were met

- **Step 2, titles and steps.** Every new test title starts with its E2E or TC ID, and every user action is a `test.step("<user action>")`, so a failure names the step (US-141 AC2).
- **Step 3 (TC-376).** A move reflows the day's times, so a reorder alone never overlaps (API test `test_edits_a_move_shifts_the_following_start_times_and_renumbers`). The spec moves day 1's second item up by keyboard and then retimes the other item onto its start, which gives `OVERLAP` (PR-06 saves it). Then it removes the must-visit item (`MUST_VISIT_MISSING`), changes a duration, locks a day 2 item, regenerates day 2 (the locked item keeps its place and start), saves a named version, changes the plan, restores the version and reloads.
- **Step 4 (E2E-07).** The MOCK scenario is fixed per API process (`MOCK_PROVIDER_SCENARIO`, `app/core/config.py`). The spec reads the same variable and skips the test of the other scenario, with that reason. Timeout: FallbackNotice text, `fallback_rule_based` with `provider_timeout`, earlier versions and trip details unchanged, and an edit saves. Quota: PausedAiNotice ("Today's AI planning limit is reached") with "Build a rule-based plan", `failed` with `provider_quota_exhausted`, `next_action` `retry_rule_based`, `repair_attempts` 0. The plan revision, versions and trip stay unchanged. The rule-based build sends `mode: rule_based`, ends `fallback_rule_based` and an edit saves. "No further provider call" is shown in the browser only as mode `rule_based`, which makes no provider call by design (pipeline step 2). The breaker that refuses a second AI call is proven by the API tests.
- **Step 4, E2E-04 without `flawed`.** The shared CI API runs scenario `ok`, so `validate-costs.spec.ts` makes the flaws itself: a budget equal to the planning total gives `BUDGET_NEAR` (IMD-29), and a retime onto the previous start gives `OVERLAP`. The missing must-visit place of the `flawed` scenario is covered by E2E-05 (removal gives `MUST_VISIT_MISSING`).
- **Step 5.** `floor-journey` runs `journey.spec.ts` at 1280 px. It exists only when both `FEATURES_DISABLED` and `NEXT_PUBLIC_FEATURES_DISABLED` list the nine cut-list switches (`versions, trip_management, contingency, budget_alerts, wishlist, alternatives, regeneration, locks, meal_slots`, from `FEATURE_NAMES` in `lib/flags.ts`, the IMP-699 order). The servers read those variables, not the specs. In CI the floor journey stays the existing `features_disabled` dispatch input (IMP-699). With that input, `make e2e ARGS='journey'` also runs `floor-journey`. The 360 px project is the existing `chromium-360` (TC-373). The keyboard-only journey is `keyboard.spec.ts`, and the journey itself stays keyboard-driven.
- **Step 6.** No fixed waits existed. The new specs wait on GenerationProgress's terminal states and on API-23 with `expect.poll`.
- **Step 7.** Triggers are unchanged: push to `main` and `workflow_dispatch` (`base_url`, `features_disabled`). **The nightly cron of the card stays off by IMD-185** (E2E on every push to main and by dispatch on each pull request; there is no nightly or pull_request trigger). The HTML report is uploaded as before, with one report folder per step.
- **Step 9.** The nine extensions are cut and not built (IMD-65). One test per extension skips with `cut by IMD-65 (switch off)`. One test that is not skipped opens `/dashboard`, `/trips/new`, the itinerary and the costs page once their data has rendered. It checks that no extension button or link is shown, and that `/trips/[tripId]/today` and `/packing` answer 404. No extension is enabled.

## Workflow (`.github/workflows/e2e.yml`)

- `timeout-minutes` goes from 30 to 50 (a second web build and two provider-failure runs).
- The web app on 3000 now runs from a copy (`$RUNNER_TEMP/web-3000`), so the second build can reuse `.next`.
- New step **Run the regression specs**: `auth trip-create generate validate-costs reopen ownership keyboard extensions --project=chromium-1280`, report `playwright-report/regression`. It uses one width because the local stack allows 30 sign-ins and sign-ups per 5 minutes (`supabase/config.toml`): journey 4 plus map 8 plus itinerary-edit 8 plus regression 13.
- New step **Build and start the provider-failure web app on 3001**: `NEXT_PUBLIC_API_BASE_URL=http://localhost:8001/api/v1` (inlined at build time), served from `$RUNNER_TEMP/web-3001`.
- New steps **Run provider failure with a timeout** and **… with quota exhausted**: each starts its own API on 8001 with `MOCK_PROVIDER_SCENARIO` and `ALLOWED_ORIGINS=http://localhost:3001`, runs `make e2e ARGS='--project=provider-failure'` with the same scenario, and stops that API on exit (trap), pass or fail. Reports go to `playwright-report/provider-failure-timeout` and `-quota`. The extra server logs go into the uploaded artefact.
- All new steps are skipped on the floor run (`features_disabled` set), which runs the journey and the map specs, as at SG-6.
- `runs-on` stays `ubuntu-24.04`; the staging job is unchanged.

## Commands

| Command | Result |
| --- | --- |
| `cd apps/web && npx tsc --noEmit` | exit 0, no output |
| `npx eslint e2e playwright.config.ts` | exit 0, no output |
| `npx prettier --check e2e playwright.config.ts ../../.github/workflows/e2e.yml` | `All matched files use Prettier code style!` |
| `npx playwright test --list` | `Total: 118 tests in 13 files` (chromium-360 29, chromium-768 29, chromium-1280 29, chromium-1920 29, provider-failure 2) |
| `npx playwright test --list --grep @ext` | `Total: 40 tests in 1 file` (10 per width project) |
| `npx playwright test --list --project=provider-failure` | `Total: 2 tests in 1 file` |
| `FEATURES_DISABLED=<nine> NEXT_PUBLIC_FEATURES_DISABLED=<nine> npx playwright test --list --project=floor-journey` | `Total: 1 test in 1 file` |
| `make lint` | `All checks passed!`; `232 files already formatted`; ESLint `✖ 1 problem (0 errors, 1 warning)` (the existing warning in `lib/api/client.ts`); `All matched files use Prettier code style!` |
| `make typecheck` (web part) | `✓ Types generated successfully`, `tsc --noEmit` clean |

`.github/pull_request_template.md` was already not Prettier-formatted before this change. The repository's `format:check` covers only `apps/web`.

### Broken-assertion demo (local only, not committed)

The real suite cannot run here, so the reporter's behaviour was shown with a throwaway spec and config, outside the commit and without a web server. The test was titled `E2E-04: deliberately broken assertion (local demo, not committed)`, and its second `test.step` expects text that is absent. Command: `npx playwright test -c .imp701-demo/demo.config.ts` (retries 0, list and HTML reporters). The run ended with exit code 1, and the output lines were:

```text
  ✘  1 [chromium-1280] › .imp701-demo/demo.spec.ts:3:5 › E2E-04: deliberately broken assertion (local demo, not committed) (1.2s)
  1) [chromium-1280] › .imp701-demo/demo.spec.ts:3:5 › E2E-04: deliberately broken assertion (local demo, not committed) › See the planning total from the API
    Error: expect(locator).toBeVisible() failed
  1 failed
```

The failure names the test with its ID and the user step. The temporary files and their report were deleted. The suite's own run is the CI dispatch of the PR head.

### Not run

- `make e2e` (any spec), the three `--repeat-each=3` runs and `make e2e ARGS='--grep @ext'`: this machine has no Docker, so the Supabase local stack cannot start. Evidence = the CI dispatch of the PR head (one run).
- `make test` and `make check`: no API, web-unit or schema change in this part. The web unit tests are unaffected, because only `e2e/`, the Playwright config and CI files changed.

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| `make e2e` passes three consecutive times with MOCK and no retries configured | not verified | `retries: 0` is set (verified in the config). The three local runs were not run (no Docker) and are marked not run in `docs/test-reports/e2e-sprint7.md` |
| Specs exist and pass for E2E-01 to E2E-08 and TC-369, TC-371 to TC-376 | specs exist: verified (`--list`); pass: not verified locally, pending CI dispatch | `npx playwright test --list` lists every spec and title |
| A broken assertion fails CI and the report shows the test name and the failing user step | verified locally with a throwaway spec (above); CI not verified (pending dispatch) | Demo output above |
| Floor journey passes with all nine cut-list features disabled (TC-372) | not verified in this run | Project `floor-journey` listed with the nine switches set. CI evidence is the `features_disabled` dispatch (passed at SG-6, run 43807026528, before this change) |
| No spec needs a Gemini key, a hosted Supabase project or network beyond the local stack | verified by reading | Specs use MOCK, the local stack (the `users` fixture refuses non-local hosts) and the API. Map tiles are aborted in the edit specs |
| `--grep @ext` passes for enabled extensions and skips disabled ones with the reason | not verified locally, pending CI dispatch | 9 skips with `cut by IMD-65 (switch off)` plus 1 absence test per project, listed |

## Blockers

- No Docker on the operator machine, so no local E2E run. Evidence comes from one CI dispatch of the PR head (IMD-185; IMD-193 for a CI-only failure).

## Proposed decisions

- **PD-IMP-701-1 (nightly cron):** the card's nightly cron (step 7) stays off by IMD-185. The proposal is to record that IMP-701's acceptance is met by push-to-main runs plus the PR dispatch.
- **PD-IMP-701-2 (local sign-in limit):** if the CI run hits the local stack's limit of 30 sign-ins per 5 minutes (HTTP 429 on `/auth/v1/token`), raise `[auth.rate_limit] sign_in_sign_ups` in `supabase/config.toml` for the local stack only, rather than cutting widths further. Until then, the regression step runs at one width.

## Open issues

- **Versions page for a foreign trip (E2E-08):** `/trips/[tripId]/versions` reads API-24 first, and its 404 shows the no-plan state "No itinerary yet" with a "Generate a plan" link instead of the not-found state. The page shows no data of A's trip, and every API answer is 404. `ownership.spec.ts` accepts either heading and records this here. The fix would be in the versions page (IMP-610 owner).
- E2E-03's "progress passes through the statuses" is checked as the progress panel appearing and the itinerary opening. MOCK finishes in under a second, so the intermediate statuses are not asserted (that would be flaky).
- `trip-create.spec.ts` keeps its fixed dates (2026-12-04 to 2026-12-06). They are still in the future, but they will need `daysFromNow` before December 2026.

## RUN-081c follow-up (fixes of the first dispatch's failures)

| Field | Value |
| --- | --- |
| Run | RUN-081c (continues RUN-081b, which stopped on the IMP-506 lock-toggle name) |
| Owner | Krrish Kamani |
| Status | PR_OPEN pending: specs fixed and statically checked; the E2E evidence comes from the lead's integration runs |
| Base commit | 62eb1fc |

### Changed files

- `apps/web/e2e/itinerary-edit.spec.ts`: F-E1, the retime step reads A and B by ID from a fresh API-24 read and retimes the moved, unlocked item B to a different start inside A's interval; `retime()` refuses an unchanged value before it waits for the PATCH. The lock toggle is found by its new name `Locked <place>` (IMP-506, committed separately before this commit).
- `apps/web/e2e/validate-costs.spec.ts`: F-E2, matches the whole paragraph `Suggested fix: <text>`.
- `apps/web/e2e/provider-failure.spec.ts`: F-E3 under IMD-206, both TC-371 tests start from a fresh trip with no itinerary and press "Generate with AI" (API-22); a non-202 answer fails with its body. No API-31 regeneration case is kept.
- `apps/web/e2e/ownership.spec.ts`: the versions page of another user's trip must show "Trip not found" (IMP-610 fix 10f3324, the open issue below is closed).
- `apps/web/playwright.config.ts`: `FLOOR_BASE_URL` adds the `floor-journey` project against a separately built floor stack; retries stay 0.
- `.github/workflows/e2e.yml`: `repeat_each` dispatch input (default 1, validated), passed as `--repeat-each` to every local-stack run; a floor-journey step on API 8002 and web 3002 with the nine cut-list switches off; its logs in the artefact. Triggers stay push to `main` and `workflow_dispatch`; `ubuntu-24.04`.
- `docs/test-reports/e2e-sprint7.md`: sections 4 (F-E1 to F-E3) and 5 (result placeholders for the lead).
- `docs/progress/parts/IMP-701-whole-task.md`: this section.

### What each provider-failure assertion rests on

- Timeout outcome `fallback_rule_based`: `apps/api/app/generation/records.py:22` (`CompletedOutcome`), set by `pipeline.py:432`. `fallback_reason` `provider_timeout`: `pipeline.py:423` stores the cause, `service.py:215` returns it; MOCK `timeout` raises `ProviderTimeout` (`app/ai/providers/mock.py:363`).
- Quota `failed` / `provider_quota_exhausted`: `records.py:28`, `outcomes.py:12` and `NO_FALLBACK` (`outcomes.py:30`); `next_action` `retry_rule_based`: `outcomes.py:70` through `service.py:214`; `repair_attempts`: `schemas.py:51`, no repair call before a quota failure (IMD-44). Paused message: `GenerationProgress.tsx:200` shows `PausedAiNotice` (role status, "Build a rule-based plan"). Nothing saved: API-24 answers 404 `NOT_FOUND` with no itinerary (`app/itinerary/service.py:431`).
- Rule-based option: `service.py:167` stores `model_id` `rule_based_planner_v1` (`fallback_planner.py:33`) for mode rule_based, `service.py:209` returns `mode` rule_based, and the pipeline makes no model call for it (`pipeline.py:631`); it completes `fallback_rule_based` (`pipeline.py:432`), so the itinerary page shows the FallbackNotice (`FallbackNotice.tsx:15`, `itinerary/page.tsx:446`).

### Commands

| Command | Result | Wall time |
| --- | --- | --- |
| `make test-web ARGS='tests/unit/itinerary/LockToggle.test.tsx tests/unit/itinerary'` (IMP-506 commit) | `Test Files  12 passed (12)`, `Tests  82 passed (82)` | 7.8 s |
| `make lint` | exit 0: `All checks passed!`, `234 files already formatted`, `All matched files use Prettier code style!` | 9.6 s |
| `npm run typecheck --prefix apps/web` | exit 0: `✓ Types generated successfully`, `tsc --noEmit` clean | 2.9 s |

Not run in RUN-081c: `make e2e` (any spec). The lead runs every E2E invocation after integration, each with its own `--output` outside the repository.

### Acceptance criteria (RUN-081c)

| Criterion | Status | How |
| --- | --- | --- |
| F-E1 retime sends a PATCH and keeps the overlap (TC-376) | not verified, pending lead runs | RUN-081b showed the retime step passing on the same change; the full spec is pending |
| F-E2 suggested fix shown (E2E-04) | not verified, pending lead runs | RUN-081b showed the warning assertions passing at every width |
| TC-371 timeout and quota from a fresh trip (ACC-03, ACC-17) | not verified, pending lead runs | Assertions checked against the API code listed above; lint and typecheck pass |
| TC-383 lock toggle name contains its label | verified (unit); E2E not verified, pending lead runs | `LockToggle.test.tsx` passes |
| `make e2e` passes three consecutive times, no retries | not verified, pending lead runs | `retries: 0` in the config; `repeat_each` input added |
| Triggers push to main and workflow_dispatch only; ubuntu-24.04 | verified | Read `.github/workflows/e2e.yml` |

### Blockers

- None for this part. The 360 px CostBreakdown scroll regions (IMP-507) are fixed in a separate commit of the integration branch; `validate-costs` at 360 px depends on it.

### Proposed decisions

- None.
