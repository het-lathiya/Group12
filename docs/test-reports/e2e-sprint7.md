# E2E regression suite, Sprint 7 (IMP-701)

Written in RUN-081 (IMP-701 whole task, Krrish), 16 November 2026, on base `a4c2a0b`. Scenarios: specification §13.4 (E2E-01 to E2E-08) and the TC IDs of the card. Every automated scenario runs against the Supabase CLI local stack, `make seed` (Sampleton) and the API with `AI_PROVIDER=MOCK`.

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

## 2. Local runs (card step 6)

**Not run — no Docker on the operator machine; evidence = CI dispatch of the PR head (one run).** The local Supabase stack needs Docker, so `make e2e` (three runs with `--repeat-each=3`) could not run here. No pass is claimed.

| Run | Command | Result | Run time | Flaky tests |
| --- | --- | --- | --- | --- |
| 1 | `make e2e ARGS='--repeat-each=3'` | not run | not run | not run |
| 2 | `make e2e ARGS='--repeat-each=3'` | not run | not run | not run |
| 3 | `make e2e ARGS='--repeat-each=3'` | not run | not run | not run |

Flaky-test list: none known; the list stays open until the CI dispatch has run.

## 3. CI dispatch of the PR head

Not run yet. The E2E workflow is dispatched once on the pull request's branch (IMD-185); its result and the run link go here and into the part record. Retries are 0 in `playwright.config.ts`, so the run has no hidden retry.

## 4. Failures of the first dispatch and their fixes (RUN-081b, RUN-081c)

| ID | Spec | Cause | Fix |
| --- | --- | --- | --- |
| F-E1 | `itinerary-edit.spec.ts`, `E2E-05 TC-376` | After the move, the must-visit item A (locked) and the moved, unlocked item B both start at 09:00. The spec retimed A to 09:00, its own start, so ItemEditor sent no PATCH and the step timed out waiting for one. | The step reads A and B by ID from a fresh API-24 read and retimes B onto A's start (A's start plus one minute when they are equal), which keeps the overlap. `retime()` checks that the editor receives a changed `HH:MM` value before it waits for the PATCH; the PATCH and its 200 stay asserted. |
| F-E2 | `validate-costs.spec.ts`, `E2E-04` | WarningsPanel renders the fix as one paragraph `Suggested fix: <text>`; the spec matched `<text>` alone, exactly, and found nothing. | The spec matches the whole paragraph `Suggested fix: <text>` exactly; the warning message stays an exact match. |
| F-E3 | `provider-failure.spec.ts`, both `E2E-07 TC-371` tests | The tests started API-22 for a trip that already had a plan and a saved version. API-22 answers 409 `CONFLICT` "This trip already has an itinerary. Regenerate it instead." (§6.4), which is correct product behaviour. | IMD-206: both tests start from a fresh trip with no itinerary and press "Generate with AI" on the generate page. Timeout: `completed`, outcome `fallback_rule_based`, `fallback_reason` `provider_timeout`, the FallbackNotice and a saved rule-based plan, then an edit saves. Quota: `failed`, `provider_quota_exhausted`, `next_action` `retry_rule_based`, `repair_attempts` 0, the paused-AI message with "Build a rule-based plan", and no itinerary saved (API-24 404). The rule-based build sends `mode: rule_based`; its generation has model `rule_based_planner_v1`, so it made no further provider call (ACC-03, ACC-17), and it completes `fallback_rule_based` with the FallbackNotice. A non-202 answer fails with its body in the message. No product code changed. |

RUN-081c also changed the lock toggle's accessible name so it contains its visible label (`Locked <place>` or `Lock <place>`, TC-383, IMP-506); `itinerary-edit.spec.ts` looks it up by the new name. The workflow gains a `repeat_each` dispatch input (default 1, checked to be a positive integer), passed to every local-stack `make e2e`, and a floor-journey step on its own stack (API 8002, web 3002, the nine cut-list switches off). Triggers stay push to `main` and `workflow_dispatch`; `runs-on` stays `ubuntu-24.04`; retries stay 0. Each Playwright invocation can take its own `--output=<folder outside the repository>`, so sequential local runs do not delete each other's artefacts.

## 5. Results (to be filled from the lead's integration runs)

| Run | Command | Result | Run time | Flaky tests |
| --- | --- | --- | --- | --- |
| 1 | _PLACEHOLDER: to be filled from the lead's integration runs_ | _PLACEHOLDER_ | _PLACEHOLDER_ | _PLACEHOLDER_ |
| 2 | _PLACEHOLDER: to be filled from the lead's integration runs_ | _PLACEHOLDER_ | _PLACEHOLDER_ | _PLACEHOLDER_ |
| 3 | _PLACEHOLDER: to be filled from the lead's integration runs_ | _PLACEHOLDER_ | _PLACEHOLDER_ | _PLACEHOLDER_ |

Provider failure, timeout and quota: _PLACEHOLDER: to be filled from the lead's integration runs_.

CI dispatch run link and result: _PLACEHOLDER: to be filled from the lead's integration runs_.

Flaky-test list: _PLACEHOLDER: to be filled from the lead's integration runs_.
