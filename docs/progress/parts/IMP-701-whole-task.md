# IMP-701 · whole-task

| Field | Value |
| --- | --- |
| Run | RUN-081 implementation; RUN-081b/RUN-081c fixes; RUN-081d final local evidence (18 November 2026) |
| Card | IMP-701 End-to-end regression suite for all primary scenarios |
| Part | Whole task (3 points, counted once) |
| Owner | Krrish Kamani |
| Status | Local acceptance verified except the CI broken-assertion demonstration; PR #287 remains unmerged and its RUN-081d dispatch has not occurred at this evidence commit |
| Base commit | 180c88a (RUN-081d); original implementation base a4c2a0b |
| Checked code head | b6051a8; three full E2E runs without code changes |
| Branch | wt/S7A-K-081d; integration branch feat/S7-A-e2e-security |
| PR | [#287](https://github.com/het-lathiya/Group12/pull/287) |

## This part's current change

Only `docs/test-reports/e2e-sprint7.md` and this part record change in K3. They record real RUN-081c and RUN-081d results, elapsed times, earlier deterministic failures, the empty flaky list and each acceptance criterion. No product code, contract or migration changes in K3. The complete command/result tables are in [the Sprint 7 E2E report](../../test-reports/e2e-sprint7.md).

## Historical implementation files (RUN-081 / RUN-081c)

- `docs/test-reports/e2e-sprint7.md` (created): the E2E-01 to E2E-08 gap list, written first; the original local-run limitation, now superseded by the recorded integration evidence; the CI dispatch section.
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

## How the card steps are met

- **Steps 1–2:** the report preserves the pre-implementation E2E-01..08 gap list. New spec titles identify the E2E/TC case and use `test.step` for user actions. The existing local `fixtures/users.ts` creates test users; no second user helper was added.
- **Step 3 (TC-376):** editing makes an overlap through a changed retime, removes a must-visit item, changes duration, locks a day 2 item, regenerates day 2 while preserving its place/time, saves a version, changes the plan, restores and reloads. F-E1 reads fresh item IDs after the move and refuses an unchanged retime before waiting for PATCH.
- **Step 4 (E2E-04):** with scenario `ok`, costs specs set the budget near the estimate and retime to create overlap; `Suggested fix: <text>` is matched as a whole paragraph (F-E2). Removal in E2E-05 covers the missing must-visit finding.
- **Step 4 (E2E-07, IMD-206):** timeout and quota start with a fresh trip without an itinerary. Timeout saves the labelled rule-based plan and then an edit. Quota gives `failed` / `provider_quota_exhausted`, `next_action: retry_rule_based`, no saved itinerary and no repair attempt; the explicit rule-based build uses `mode: rule_based`, completes `fallback_rule_based` and saves. A second generation on an existing itinerary is correctly a 409 and is not a precondition here. Fix `180c88a` reads generation mode from the 202 body, rather than nullable request JSON.
- **Step 5:** four width projects cover 360/768/1280/1920 px; `keyboard.spec.ts` uses Tab/Enter and axe scans; the separate `floor-journey` stack on API 8002/web 3002 disables `versions,trip_management,contingency,budget_alerts,wishlist,alternatives,regeneration,locks,meal_slots`. `FLOOR_BASE_URL` includes it alongside enabled-feature projects in each full local run.
- **Step 6 (IMD-203):** three separate full `make e2e` invocations pass consecutively on unchanged `b6051a8`, retries 0; quota passes after each. There are no fixed sleeps in the specs, and assertions wait for terminal states/API results. The flaky list is empty, 0 of 3 full runs failing or flaky.
- **Steps 7–8:** `e2e.yml` retains push-to-main and `workflow_dispatch`, `ubuntu-24.04`, uploaded HTML reports and retries 0; `repeat_each` is validated and passed to every local-stack invocation. The full workflow has a separate floor step plus provider timeout/quota steps. The nightly cron stays off by IMD-185/IMD-202. The PR template includes “E2E specs touched by this change pass locally (make e2e)”.
- **Step 9:** all nine extensions remain cut under IMD-65. At each width nine tests skip with the cut-list reason and one absence/404 test passes. No enabled extension exists to claim as exercised.

## RUN-081c results and stop (historical)

After integrating F-E1/F-E2/F-E3, the targeted suite reports `8 passed (1.1m)` for itinerary editing (65.61 s), `4 passed (15.9s)` for costs (17.24 s), `5 passed (1.1m)` for journey including floor (65.83 s), `4 passed (14.0s)` for ownership (15.00 s), and `36 skipped`, `4 passed (9.1s)` for `@ext` (10.06 s). The initial provider timeout reports `1 failed`, `1 skipped` (4.80 s): the request-body mode assertion at `provider-failure.spec.ts:73` reads null. Fix `180c88a` is the one RUN-081c fix round; afterward timeout reports `1 skipped`, `1 passed (8.7s)` (9.68 s), and quota `1 skipped`, `1 passed (8.2s)` (9.01 s).

| Full run at 180c88a | Exact result | Full wall | Quota result / wall | Combined wall |
| --- | --- | --- | --- | --- |
| 1 | `3 failed`; `37 skipped`; `79 passed (4.1m)` | 246.67 s | `1 skipped`; `1 passed (8.2s)` / 9.63 s | 259 s |
| 2 | `3 failed`; `37 skipped`; `79 passed (4.0m)` | 238.74 s | `1 skipped`; `1 passed (8.8s)` / 10.38 s | 249 s |
| 3 | `3 failed`; `37 skipped`; `79 passed (4.3m)` | 259.47 s | `1 skipped`; `1 passed (8.4s)` / 9.51 s | 269 s |

Every full run fails identically in `smoke.spec.ts:87` at 360 px (Profile clipped) and 768 px, plus `auth.spec.ts:147` TC-054/TC-056 at 768 px (page width 894 > 768). This is AppShell's main-origin navigation overflow after Explore/Summary/Versions were added (`428b68c`, `3769bab`, `b991141` on main `a4c2a0b`), not a flaky test. The used fix round and IMD-206's attribute-only boundary stopped RUN-081c without a push. Its `make check` had passed (426.76 s; web 286 tests), but its three E2E runs did not pass.

## RUN-081d final verification

IMD-207 (`21ba8d5`, Nidhi) authorizes the layout defect fix. Manasvi's M2 (`c038433`, integrated as `b6051a8`) keeps every tab, route and keyboard order, wraps the desktop nav, fits seven phone tabs with 44 px minimum targets and uses `sr-only hidden lg:inline` on hints.

Before fix: `smoke` reports `2 failed`, `10 passed (10.9s)` (wall 12.21 s); `auth` reports `1 failed`, `19 passed (13.4s)` (14.30 s), reproducing the same 360/768 failures. Final M2 source: `smoke` `12 passed (10.0s)` (10.88 s), `auth` `20 passed (16.3s)` (17.18 s). The unchanged external open-trip check reports `4 passed (24.9s)` (25.92 s): all seven links visible/unclipped at all four widths, page fits viewport, targets at least 44 px, Profile reached by Tab, existing keyboard order, visible focus rings, no serious/critical axe violations. The first candidate's deterministic Summary-label clipping at 360 px was repaired before the M2 commit and before these final runs. AppShell's final unit run is `Test Files  1 passed (1)`, `Tests  7 passed (7)`, duration 1.83 s; accessible names/order and narrow-width hint classes are asserted.

The integrated main web build's tree equals `b6051a8`; provider and floor builds use the integrated checkout. Each invocation writes outside the repository to its own output folder in `/home/hetlathiya/S7A-081d-evidence/`.

| Command / phase | Exact result lines | Wall time | Evidence log |
| --- | --- | --- | --- |
| `make check` (once) | exit 0; `All checks passed!`; `Success: no issues found in 123 source files`; `Contracts: 6 kept, 0 broken.`; `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date`; `1210 passed, 1 warning in 19.85s`; `91 passed, 2 deselected, 1 warning in 20.52s`; `590 passed, 1 warning in 250.28s (0:04:10)`; `87 passed, 14 skipped, 1 warning in 50.41s`; `Test Files  43 passed (43)`; `Tests  288 passed (288)` | 401.43 s | `check.log` |
| Integrated `make e2e ARGS='smoke'` | `12 passed (10.5s)` | 11.52 s | `lead-smoke.log` |
| Integrated `make e2e ARGS='auth'` | `20 passed (14.3s)` | 15.20 s | `lead-auth.log` |
| Full `make e2e`, run 1 | `37 skipped`; `82 passed (3.9m)` | 237.09 s | `full1.log` |
| Quota after run 1 | `1 skipped`; `1 passed (8.2s)` | 9.21 s | `full1-quota.log` |
| Full `make e2e`, run 2 | `37 skipped`; `82 passed (4.1m)` | 247.23 s | `full2.log` |
| Quota after run 2 | `1 skipped`; `1 passed (8.4s)` | 9.27 s | `full2-quota.log` |
| Full `make e2e`, run 3 | `37 skipped`; `82 passed (4.1m)` | 248.37 s | `full3.log` |
| Quota after run 3 | `1 skipped`; `1 passed (8.3s)` | 9.07 s | `full3-quota.log` |

All full/quota invocations exit 0 with workers 2, retries 0 and no code change between runs. Full logs each start `Running 119 tests using 2 workers`: 82 pass, 36 cut-extension skips and one complementary quota skip. Each quota follow-up skips timeout and passes quota. Combined full/quota/scenario-switch wall times: 248.22 s, 259.91 s, 259.36 s. No full-run fix round was used. **Flaky-test list: empty (0 of 3 full runs).**

## Acceptance criteria (current)

| Criterion | Status | How |
| --- | --- | --- |
| `make e2e` passes locally three consecutive times with MOCK and no retries | verified | RUN-081d full runs 1–3 at `b6051a8`: each `37 skipped`, `82 passed`; provider quota follow-up passes after each. No code changes between runs; `retries: 0`; IMD-203 permits three separate full invocations. |
| Specs exist and pass for E2E-01 to E2E-08 and TC-369, TC-371, TC-372, TC-373, TC-374, TC-375, TC-376 | verified locally | All three full logs include auth, trip creation, generation, costs, editing/lock/regenerate/restore, reopen/stale-plan, ownership, keyboard and the separate floor project; the provider timeout passes in each full run and quota in each follow-up. |
| A deliberately broken assertion makes CI fail and the report names the test and failing user step | local reporter behavior verified; CI portion not verified | The RUN-081 local demo in the part record exits 1, reports `1 failed`, and names `E2E-04: deliberately broken assertion (local demo, not committed)` and `See the planning total from the API`. No deliberately broken assertion was dispatched to CI. |
| Floor journey passes with all nine cut-list features disabled (TC-372) | verified locally | `[floor-journey]` passes in full runs 1–3 against API 8002/web 3002 built with all nine switches disabled; `FLOOR_BASE_URL` includes this project in each full invocation. |
| No spec needs a Gemini key, hosted Supabase project or network beyond the local stack | verified locally and by inspection | All three runs use MOCK and the CLI local stack; `fixtures/users.ts` refuses non-local hosts. Map tests abort remote tiles or serve a local style, and edit specs abort tiles. No provider or hosted-project credential is required. |
| `make e2e ARGS='--grep @ext'` passes for enabled extensions and skips disabled ones with a reason | verified for the current cut-list configuration | RUN-081c targeted `@ext`: `36 skipped`, `4 passed (9.1s)`; each RUN-081d full run also passes the four absence/404 checks and skips the nine cut extensions at each of four widths with the IMD-65 reason. There are no enabled extensions. |

## RUN-081 broken-assertion demo (historical, local only, not committed)

When the real suite could not run during RUN-081, the reporter's behaviour was shown with a throwaway spec and config, outside the commit and without a web server. The test was titled `E2E-04: deliberately broken assertion (local demo, not committed)`, and its second `test.step` expects text that is absent. Command: `npx playwright test -c .imp701-demo/demo.config.ts` (retries 0, list and HTML reporters). The run ended with exit code 1, and the output lines were:

```text
  ✘  1 [chromium-1280] › .imp701-demo/demo.spec.ts:3:5 › E2E-04: deliberately broken assertion (local demo, not committed) (1.2s)
  1) [chromium-1280] › .imp701-demo/demo.spec.ts:3:5 › E2E-04: deliberately broken assertion (local demo, not committed) › See the planning total from the API
    Error: expect(locator).toBeVisible() failed
  1 failed
```

The failure names the test with its ID and the user step. The temporary files and their report were deleted. This proves local reporter behavior only; the deliberately broken assertion has not been dispatched to CI.


## Provider-failure assertion basis (IMD-206)

- Timeout outcome `fallback_rule_based`: `apps/api/app/generation/records.py:22` (`CompletedOutcome`), set by `pipeline.py:432`. `fallback_reason` `provider_timeout`: `pipeline.py:423` stores the cause, `service.py:215` returns it; MOCK `timeout` raises `ProviderTimeout` (`app/ai/providers/mock.py:363`).
- Quota `failed` / `provider_quota_exhausted`: `records.py:28`, `outcomes.py:12` and `NO_FALLBACK` (`outcomes.py:30`); `next_action` `retry_rule_based`: `outcomes.py:70` through `service.py:214`; `repair_attempts`: `schemas.py:51`, no repair call before a quota failure (IMD-44). Paused message: `GenerationProgress.tsx:200` shows `PausedAiNotice` (role status, "Build a rule-based plan"). Nothing saved: API-24 answers 404 `NOT_FOUND` with no itinerary (`app/itinerary/service.py:431`).
- Rule-based option: `service.py:167` stores `model_id` `rule_based_planner_v1` (`fallback_planner.py:33`) for mode rule_based, `service.py:209` returns `mode` rule_based, and the pipeline makes no model call for it (`pipeline.py:631`); it completes `fallback_rule_based` (`pipeline.py:432`), so the itinerary page shows the FallbackNotice (`FallbackNotice.tsx:15`, `itinerary/page.tsx:446`).

## Remaining verification and blockers

No blocker remains for the local regression runs. At K3 commit time, the required lead push and one `e2e.yml` dispatch (`repeat_each=3`) follow integration of this evidence, so no RUN-081d CI URL/result exists yet. The lead records the actual URL/result in the RUN-081d SYNC REPORT and checkpoint. CI execution on the pushed head and a deliberately broken assertion in CI remain not verified; a local failure demo is not a CI demonstration. Live/staging and manual device/screen-reader verification are outside these MOCK results.

## Decisions and open issues

- PD-IMP-701-1 is resolved by IMD-202: nightly stays off under IMD-185.
- PD-IMP-701-2 is resolved by IMD-203: local/CI `sign_in_sign_ups` is 300; hosted configuration is unchanged.
- The foreign-trip versions-page issue is closed by Jeel's `10f3324`; `ownership.spec.ts` requires “Trip not found” and passes in the targeted RUN-081c and all three RUN-081d full runs.
- Intermediate MOCK progress statuses are not individually timed: the panel and terminal outcome are asserted to avoid timing-dependent checks.
- `trip-create.spec.ts` retains 4–6 December 2026 dates; conversion to relative dates is a later maintenance item, not part of this evidence-only commit.
- Proposed decisions: none. No contracts changed or migrations added.
