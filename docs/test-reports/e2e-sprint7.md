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
