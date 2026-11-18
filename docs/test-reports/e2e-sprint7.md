# E2E regression suite, Sprint 7 (IMP-701)

Original gap list: RUN-081, 16 November 2026, base `a4c2a0b`. Final local evidence: RUN-081d, 18 November 2026, base `180c88a`, checked code head `b6051a8`, PR [#287](https://github.com/het-lathiya/Group12/pull/287). Owner: Krrish Kamani, whole task (3 points). Automated scenarios use the Supabase CLI local stack, the Sampleton seed and `AI_PROVIDER=MOCK`.

## 1. Gap list (written before any spec was changed)

State of `apps/web/e2e/` on `a4c2a0b`, before this run:

| Scenario | §13.4 spec file | State before IMP-701 | Covered by, after IMP-701 |
| --- | --- | --- | --- |
| E2E-01 Create or sign in to an account | `auth.spec.ts` | **Exists** (IMP-109): sign-up, duplicate notice, wrong password, sign-in, reload, sign-out, Back. Titles did not start with an ID. Not run by `e2e.yml` | `auth.spec.ts`, titles now start with `E2E-01` and the TC ID; run by the new CI step "Run the regression specs" |
| E2E-02 Create a trip | `trip-create.spec.ts` | **Partly exists** (IMP-212): wizard, end date before start date rejected, trip saved. Missing: the trip on `/dashboard` with status draft or ready. Not run by `e2e.yml` | `trip-create.spec.ts`, new step "See the trip on the dashboard as draft or ready"; run by the regression step |
| E2E-03 Generate an itinerary | `generate.spec.ts` | **Missing** (the file did not exist; the journey generates, but without a notice-to-itinerary check of its own) | `generate.spec.ts` (created) |
| E2E-04 Validate the itinerary and its costs | `validate-costs.spec.ts` | **Missing** | `validate-costs.spec.ts` (created) |
| E2E-05 Edit or remove an activity | `itinerary-edit.spec.ts` | **Partly exists**: the journey removes, retimes and moves by keyboard; `itinerary-edit.spec.ts` (IMP-607) covers regenerate and restore only. Missing: overlap finding, must-visit warning, lock, regenerate day 2 with a locked item, save version, change, restore, reload (card step 3) | `itinerary-edit.spec.ts`, new test `E2E-05 TC-376` |
| E2E-06 Save and reopen the trip | `reopen.spec.ts` | **Partly exists**: the journey reloads and uses Open latest. Missing: sign out and in again, second tab, 409 `STALE_PLAN` reload message | `reopen.spec.ts` (created) |
| E2E-07 Handle an AI provider failure | `provider-failure.spec.ts` | **Missing**, and no `provider-failure` project (IMD-33) | `provider-failure.spec.ts` (created), project `provider-failure`, two CI steps (timeout, quota) |
| E2E-08 Another user cannot access a private trip | `ownership.spec.ts` | **Missing** in the browser (the API half is the authz suite) | `ownership.spec.ts` (created) |
| TC-369 journey | `journey.spec.ts` | Exists (IMP-216, IMP-414) | unchanged apart from the title |
| TC-372 floor journey | `journey.spec.ts` | Runs only by the `features_disabled` dispatch input (IMP-699); no Playwright project | project `floor-journey` (present when both variables list the nine cut-list switches) |
| TC-373 360 px | all specs | Project `chromium-360` exists | reused |
| TC-374 keyboard only | `journey.spec.ts` | The journey is keyboard-driven (IMP-513) | plus `keyboard.spec.ts` (created): Tab and Enter only, axe after each page |
| TC-375 ownership | `ownership.spec.ts` | Missing | `ownership.spec.ts` |
| TC-376 regenerate, lock, version restore | `itinerary-edit.spec.ts` | Regenerate day and all, restore (IMP-607) | plus the card step 3 sequence |
| TC-432 extension switches | `extensions.spec.ts` | Missing | `extensions.spec.ts` (created), tag `@ext` |

Fixed waits: none were found (`grep -rn "waitForTimeout\|setTimeout(\|sleep" apps/web/e2e` finds only `test.setTimeout`). The new specs wait on GenerationProgress's terminal states (the itinerary opening after "Plan ready", `PausedAiNotice`, "Regeneration complete.") and on API-23's terminal status with `expect.poll`.

## 2. Failures of the first dispatch and their fixes (RUN-081b, RUN-081c)

| ID | Spec | Cause | Fix |
| --- | --- | --- | --- |
| F-E1 | `itinerary-edit.spec.ts`, `E2E-05 TC-376` | After the move, the must-visit item A (locked) and the moved, unlocked item B both start at 09:00. The spec retimed A to 09:00, its own start, so ItemEditor sent no PATCH and the step timed out waiting for one. | The step reads A and B by ID from a fresh API-24 read and retimes B onto A's start (A's start plus one minute when they are equal), which keeps the overlap. `retime()` checks that the editor receives a changed `HH:MM` value before it waits for the PATCH; the PATCH and its 200 stay asserted. |
| F-E2 | `validate-costs.spec.ts`, `E2E-04` | WarningsPanel renders the fix as one paragraph `Suggested fix: <text>`; the spec matched `<text>` alone, exactly, and found nothing. | The spec matches the whole paragraph `Suggested fix: <text>` exactly; the warning message stays an exact match. |
| F-E3 | `provider-failure.spec.ts`, both `E2E-07 TC-371` tests | The tests started API-22 for a trip that already had a plan and a saved version. API-22 answers 409 `CONFLICT` "This trip already has an itinerary. Regenerate it instead." (§6.4), which is correct product behaviour. | IMD-206: both tests start from a fresh trip with no itinerary and press "Generate with AI" on the generate page. Timeout: `completed`, outcome `fallback_rule_based`, `fallback_reason` `provider_timeout`, the FallbackNotice and a saved rule-based plan, then an edit saves. Quota: `failed`, `provider_quota_exhausted`, `next_action` `retry_rule_based`, `repair_attempts` 0, the paused-AI message with "Build a rule-based plan", and no itinerary saved (API-24 404). The rule-based build sends `mode: rule_based`; its generation has model `rule_based_planner_v1`, so it made no further provider call (ACC-03, ACC-17), and it completes `fallback_rule_based` with the FallbackNotice. A non-202 answer fails with its body in the message. No product code changed. |

RUN-081c also changed the lock toggle's accessible name so it contains its visible label (`Locked <place>` or `Lock <place>`, TC-383, IMP-506); `itinerary-edit.spec.ts` looks it up by the new name. The workflow gains a `repeat_each` dispatch input (default 1, checked to be a positive integer), passed to every local-stack `make e2e`, and a floor-journey step on its own stack (API 8002, web 3002, the nine cut-list switches off). Triggers stay push to `main` and `workflow_dispatch`; `runs-on` stays `ubuntu-24.04`; retries stay 0. Each Playwright invocation can take its own `--output=<folder outside the repository>`, so sequential local runs do not delete each other's artefacts.

## 3. RUN-081c integration evidence (historical)

RUN-081 originally could not start Docker; that limitation ended before these local integration runs. Results below are read from `/home/hetlathiya/S7A-081c-evidence/` and `/home/hetlathiya/S7A-081c-state.md`. Each Playwright invocation has its own output directory outside the repository. Selector commands below also received that output path and `--workers=2` through the local runner.

| Selector command | Exact result lines | Wall time | Log |
| --- | --- | --- | --- |
| `make e2e ARGS='itinerary-edit'` | `8 passed (1.1m)` | 65.61 s | `t-itinerary-edit.log` |
| `make e2e ARGS='validate-costs'` | `4 passed (15.9s)` | 17.24 s | `t-validate-costs.log` |
| `make e2e ARGS='journey'` | `5 passed (1.1m)` | 65.83 s | `t-journey.log` |
| `make e2e ARGS='ownership'` | `4 passed (14.0s)` | 15.00 s | `t-ownership.log` |
| `make e2e ARGS='--grep @ext'` | `36 skipped`; `4 passed (9.1s)` | 10.06 s | `t-ext.log` |
| `make e2e ARGS='provider-failure --project=provider-failure'`, timeout before its spec fix | `1 failed`; `1 skipped` | 4.80 s | `t-provider-timeout.log` |
| Same selector, timeout after `180c88a` | `1 skipped`; `1 passed (8.7s)` | 9.68 s | `t2-provider-timeout.log` |
| Same selector, quota after `180c88a` | `1 skipped`; `1 passed (8.2s)` | 9.01 s | `t2-provider-quota.log` |

The initial timeout spec failure was `provider-failure.spec.ts:73`: `postDataJSON()` returned null. Fix `180c88a` reads the generation mode from the 202 response body; timeout and quota then pass. This used RUN-081c's single fix round.

| Full run at `180c88a` | Exact full result lines | Full wall time | Quota follow-up result | Quota wall time | Combined wall time recorded in checkpoint |
| --- | --- | --- | --- | --- | --- |
| 1 (`full1.log`) | `3 failed`; `37 skipped`; `79 passed (4.1m)` | 246.67 s | `1 skipped`; `1 passed (8.2s)` | 9.63 s | 259 s |
| 2 (`full2.log`) | `3 failed`; `37 skipped`; `79 passed (4.0m)` | 238.74 s | `1 skipped`; `1 passed (8.8s)` | 10.38 s | 249 s |
| 3 (`full3.log`) | `3 failed`; `37 skipped`; `79 passed (4.3m)` | 259.47 s | `1 skipped`; `1 passed (8.4s)` | 9.51 s | 269 s |

All three full invocations failed on the same AppShell defect: `smoke.spec.ts:87` `/dashboard fits the viewport` at 360 px (`Profile` clipped) and 768 px, plus `auth.spec.ts:147` TC-054/TC-056 at 768 px (`scrollWidth` 894 > 768). The navigation came from `main` (`a4c2a0b`), after the Sprint 6 Explore (`428b68c`), Summary (`3769bab`) and Versions (`b991141`) additions. These are deterministic failures, not flaky tests. A layout change exceeded IMD-206's attribute-level scope, so RUN-081c stopped without pushing. IMD-207 authorizes the AppShell layout repair and a fresh three-run round. RUN-081c `make check` had passed (wall 426.76 s; web `Tests  286 passed (286)`), but did not satisfy the three-green-E2E criterion.

## 4. RUN-081d reproduction and final local results

IMD-207 is `21ba8d5` (Nidhi). AppShell fix `b6051a8` (Manasvi, original part commit `c038433`) wraps the desktop navigation, fits all phone tabs with at least 44 px targets, and hides the trip-needed hints at narrow widths. Tabs, routes, order and behavior stay intact. The main web build came from the final M2 tree, identical to integrated `b6051a8`; provider/floor builds came from the integrated checkout.

Evidence directory: `/home/hetlathiya/S7A-081d-evidence/`. For every row below, `make e2e` used `--workers=2 --output=/home/hetlathiya/S7A-081d-evidence/<label>-results`; the corresponding log is `<label>.log`. Run summaries and elapsed times are also recorded in `<label>.result.json`, `M-status.md` and `state.json`.

| Phase / selector | Label | Exact result lines | Wall time |
| --- | --- | --- | --- |
| M2 before fix, `smoke` | `m-before-smoke` | `2 failed`; `10 passed (10.9s)` | 12.21 s |
| M2 before fix, `auth` | `m-before-auth` | `1 failed`; `19 passed (13.4s)` | 14.30 s |
| M2 first candidate, `smoke` | `m-after-smoke` | `12 passed (9.9s)` | 11.04 s |
| M2 first candidate, `auth` | `m-after-auth` | `20 passed (14.7s)` | 15.50 s |
| M2 final source, `smoke` | `m-final-smoke` | `12 passed (10.0s)` | 10.88 s |
| M2 final source, `auth` | `m-final-auth` | `20 passed (16.3s)` | 17.18 s |
| Integrated head, `smoke` | `lead-smoke` | `12 passed (10.5s)` | 11.52 s |
| Integrated head, `auth` | `lead-auth` | `20 passed (14.3s)` | 15.20 s |

The before-fix failures reproduce `smoke.spec.ts:87` at 360/768 px and `auth.spec.ts:147` at 768 px. The 360 px assertion at `smoke.spec.ts:53` receives `["Profile"]`; the 768 px assertions at `smoke.spec.ts:32` and `auth.spec.ts:24` receive 894 for a 768 px viewport.

A separate, unchanged open-trip browser check first found deterministic Summary-label clipping at 360 px (`1 failed`, `3 passed (20.0s)`, wall 20.81 s, `m-layout.log`). M2 refined widths before committing. Its final run, `m-layout-final.log`, reports `4 passed (24.9s)` (wall 25.92 s): at 360, 768, 1280 and 1920 px all seven tabs are visible and unclipped, document width fits the viewport, targets are at least 44 px, Profile is reached by Tab, keyboard order and visible focus rings hold, and serious/critical axe findings are empty. This pre-commit iteration is not a full-run failure or a flake.

`make test-web ARGS='tests/unit/shell/AppShell.test.tsx'` passes on final M2 source: `Test Files  1 passed (1)`, `Tests  7 passed (7)`, `Duration  1.83s`; typecheck and scoped Prettier also pass. The tests cover every trip-tab accessible name and order in both navs, and the hints' `sr-only hidden lg:inline` classes.

`make check` runs once on the integrated code head and exits 0, wall **401.43 s** (`check.log`):

```text
All checks passed!
234 files already formatted
All matched files use Prettier code style!
Success: no issues found in 123 source files
Contracts: 6 kept, 0 broken.
openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date
======================= 1210 passed, 1 warning in 19.85s =======================
================= 91 passed, 2 deselected, 1 warning in 20.52s =================
================== 590 passed, 1 warning in 250.28s (0:04:10) ==================
================== 87 passed, 14 skipped, 1 warning in 50.41s ==================
 Test Files  43 passed (43)
      Tests  288 passed (288)
```

### Three consecutive full runs

Code head `b6051a8` is unchanged for all three runs; retries are 0. Each full invocation includes the four width projects (360, 768, 1280, 1920), keyboard checks, provider timeout and `floor-journey`. The main stack is API 8000/web 3000, provider stack API 8001/web 3001, floor stack API 8002/web 3002. The provider API is switched to quota for its follow-up after each full run, then back to timeout before the next full run; this changes the MOCK scenario, not code.

| Run | Exact command | Exact result lines | Wall time |
| --- | --- | --- | --- |
| 1 | `make e2e ARGS='--workers=2 --output=/home/hetlathiya/S7A-081d-evidence/full1-results'` | `37 skipped`; `82 passed (3.9m)` | 237.09 s |
| 2 | `make e2e ARGS='--workers=2 --output=/home/hetlathiya/S7A-081d-evidence/full2-results'` | `37 skipped`; `82 passed (4.1m)` | 247.23 s |
| 3 | `make e2e ARGS='--workers=2 --output=/home/hetlathiya/S7A-081d-evidence/full3-results'` | `37 skipped`; `82 passed (4.1m)` | 248.37 s |

Each log starts `Running 119 tests using 2 workers`. The 37 skips are 36 cut-extension cases (nine at each width, IMD-65) and the quota scenario while the provider API runs timeout. The complementary quota invocations use `MOCK_PROVIDER_SCENARIO=quota`:

| After full run | Exact command | Exact result lines | Wall time | Full + quota + scenario-switch wall time |
| --- | --- | --- | --- | --- |
| 1 | `make e2e ARGS='provider-failure --project=provider-failure --workers=2 --output=/home/hetlathiya/S7A-081d-evidence/full1-quota-results'` | `1 skipped`; `1 passed (8.2s)` | 9.21 s | 248.22 s |
| 2 | `make e2e ARGS='provider-failure --project=provider-failure --workers=2 --output=/home/hetlathiya/S7A-081d-evidence/full2-quota-results'` | `1 skipped`; `1 passed (8.4s)` | 9.27 s | 259.91 s |
| 3 | `make e2e ARGS='provider-failure --project=provider-failure --workers=2 --output=/home/hetlathiya/S7A-081d-evidence/full3-quota-results'` | `1 skipped`; `1 passed (8.3s)` | 9.07 s | 259.36 s |

All six invocations exit 0. Timeout and quota both start from a fresh trip and cover the saved rule-based plan/fallback notice and paused-AI/rule-based option respectively. No full-run fix round was needed.

**Flaky-test list: empty.** Observed failing/flaky full runs: **0 of 3**. The earlier RUN-081c AppShell failures and the M2 pre-commit Summary-clipping finding were deterministic and are fixed before this three-run sequence.

## 5. IMP-701 acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| `make e2e` passes locally three consecutive times with MOCK and no retries | verified | RUN-081d full runs 1–3 at `b6051a8`: each `37 skipped`, `82 passed`; provider quota follow-up passes after each. No code changes between runs; `retries: 0`; IMD-203 permits three separate full invocations. |
| Specs exist and pass for E2E-01 to E2E-08 and TC-369, TC-371, TC-372, TC-373, TC-374, TC-375, TC-376 | verified locally | All three full logs include auth, trip creation, generation, costs, editing/lock/regenerate/restore, reopen/stale-plan, ownership, keyboard and the separate floor project; the provider timeout passes in each full run and quota in each follow-up. |
| A deliberately broken assertion makes CI fail and the report names the test and failing user step | local reporter behavior verified; CI portion not verified | The RUN-081 local demo in the part record exits 1, reports `1 failed`, and names `E2E-04: deliberately broken assertion (local demo, not committed)` and `See the planning total from the API`. No deliberately broken assertion was dispatched to CI. |
| Floor journey passes with all nine cut-list features disabled (TC-372) | verified locally | `[floor-journey]` passes in full runs 1–3 against API 8002/web 3002 built with all nine switches disabled; `FLOOR_BASE_URL` includes this project in each full invocation. |
| No spec needs a Gemini key, hosted Supabase project or network beyond the local stack | verified locally and by inspection | All three runs use MOCK and the CLI local stack; `fixtures/users.ts` refuses non-local hosts. Map tests abort remote tiles or serve a local style, and edit specs abort tiles. No provider or hosted-project credential is required. |
| `make e2e ARGS='--grep @ext'` passes for enabled extensions and skips disabled ones with a reason | verified for the current cut-list configuration | RUN-081c targeted `@ext`: `36 skipped`, `4 passed (9.1s)`; each RUN-081d full run also passes the four absence/404 checks and skips the nine cut extensions at each of four widths with the IMD-65 reason. There are no enabled extensions. |

## 6. CI dispatch and remaining verification

At this evidence commit, RUN-081d's push and E2E dispatch have not occurred: integration order requires K3 evidence first. Therefore no RUN-081d dispatch URL or CI result exists yet, and no CI pass is claimed. After integration, the lead dispatches `gh workflow run e2e.yml --ref feat/S7-A-e2e-security -f repeat_each=3` once and records its actual run URL/result in the RUN-081d SYNC REPORT and checkpoint. A CI-only failure is reported under IMD-193; this run does not re-dispatch or merge.

The workflow keeps push-to-main and `workflow_dispatch` triggers, `ubuntu-24.04`, retries 0, a validated positive `repeat_each` input and uploaded HTML reports. The nightly cron stays off under IMD-185/IMD-202. CI execution on the pushed head, the deliberately broken assertion in CI, live/staging checks and manual device/screen-reader checks are not verified by these local MOCK runs.
