# Release candidate 1 · acceptance record (IMP-799)

Card: IMP-799 Sprint 7 gate SG-7, step 4: "Re-run ACC-01 to ACC-18 on staging with the candidate (CHK-21) and record pass/fail per scenario in docs/acceptance/rc1.md; record the High-priority test execution summary (CHK-20)." Owner: Kirtan (gate owner). Run: RUN-087, 22 November 2026.

- Candidate commit: `4fe514c` (`4fe514cfa015f0b9ebd87c4a96c7daa04a4a2958`), `main` after #291. Tag `v1.0-rc1`: not created (see [gates.md, SG-7](../progress/gates.md#sg-7-end-of-week-7-release-candidate-and-extension-freeze-imp-799)).
- State of this record: **provisional**. The candidate is not deployed to staging (the last "Deploy staging" run, [44733049430](https://github.com/het-lathiya/Group12/actions/runs/44733049430), deployed `964327f` on 20 November 2026), so no scenario has a staging result. Every staging cell reads "pending (Kirtan staging window)", due 26 Nov 2026.
- The local and CI E2E columns are **supporting evidence only**. They ran with MOCK on the Supabase CLI local stack, not on staging, and they do not replace the staging re-run (CHK-21).

## Scenario names

The specification refers to ACC-01 to ACC-18 (IMP-799 card, §13.4 "Related" column, IMP-701, IMP-702 and IMP-705 cards) but does not hold their names or texts in the repository; `grep` of `docs/` finds no definition. The blueprint that defines them is not in the repository. Each row below therefore gives the ID and the specification's own cross-reference to it, quoted from §13.4 or the card that names it, instead of a scenario name. PD-IMP-799-1 ([sprint-7.md](../progress/sprint-7.md#proposed-decisions-for-team-review)) asks the team for the source of the texts. ACC-19 is defined in Amendment A1 §9 and is outside this range.

## Results

| ID | Scenario (cross-reference in the specification) | Staging result on the candidate | Local / CI coverage (spec and test title) | Supporting run |
| --- | --- | --- | --- | --- |
| ACC-01 | not named in the repository; related to E2E-02 "Create a trip" and E2E-03 "Generate an itinerary" (§13.4) | pending (Kirtan staging window) | `apps/web/e2e/trip-create.spec.ts` "E2E-02 TC-068 TC-071: a new trip is saved step by step, opens the generate page and is listed on the dashboard"; `apps/web/e2e/generate.spec.ts` "E2E-03: accept the notice, generate with MOCK and open a three-day itinerary"; `journey.spec.ts` (TC-369) | [E2E 45037634127](https://github.com/het-lathiya/Group12/actions/runs/45037634127): "Run the regression specs", "Run the journey" |
| ACC-02 | not named in the repository; related to E2E-03 "Generate an itinerary" (§13.4) | pending (Kirtan staging window) | `generate.spec.ts` "E2E-03: accept the notice, generate with MOCK and open a three-day itinerary" | E2E 45037634127: "Run the regression specs" |
| ACC-03 | not named in the repository; related to E2E-07 "Handle an AI provider failure" (§13.4) and the fallback path of IMP-799 step 3 | pending (Kirtan staging window) | `provider-failure.spec.ts` "E2E-07 TC-371: a provider timeout gives the labelled rule-based plan and saves it" | E2E 45037634127: "Run provider failure with a timeout" |
| ACC-04 | not named in the repository; no cross-reference in the specification | pending (Kirtan staging window) | no spec names ACC-04 | — |
| ACC-05 | not named in the repository; related to E2E-05 "Edit or remove an activity" (§13.4) | pending (Kirtan staging window) | `itinerary-edit.spec.ts` "E2E-05 TC-376: move, overlap, remove, retime, lock, regenerate day 2, save a version, change, restore and reload" | E2E 45037634127: "Run itinerary editing and restore" |
| ACC-06 | not named in the repository; related to E2E-04 "Validate the itinerary and its costs" (§13.4) | pending (Kirtan staging window) | `validate-costs.spec.ts` "E2E-04: an overlap and a near budget show with their fixes, and the costs match the API" | E2E 45037634127: "Run the regression specs" |
| ACC-07 | not named in the repository; related to E2E-04 "Validate the itinerary and its costs" (§13.4) | pending (Kirtan staging window) | `validate-costs.spec.ts` (same test as ACC-06) | E2E 45037634127: "Run the regression specs" |
| ACC-08 | not named in the repository; related to E2E-08 "Another user cannot access a private trip" (§13.4) | pending (Kirtan staging window) | `ownership.spec.ts` "E2E-08 TC-375: another user's itinerary, costs and versions URLs show nothing of the trip"; API half in `apps/api/tests/authz/` | E2E 45037634127: "Run the regression specs"; [CI 45037634091](https://github.com/het-lathiya/Group12/actions/runs/45037634091) job `api` (`make test-authz`) |
| ACC-09 | not named in the repository; no cross-reference in the specification | pending (Kirtan staging window) | no spec names ACC-09 | — |
| ACC-10 | not named in the repository; related to E2E-06 "Save and reopen the trip" (§13.4) | pending (Kirtan staging window) | `reopen.spec.ts` "E2E-06 TC-217: reopen the saved plan after signing in again, and a stale second tab must reload" | E2E 45037634127: "Run the regression specs" |
| ACC-11 | not named in the repository; no cross-reference in the specification | pending (Kirtan staging window) | no spec names ACC-11 | — |
| ACC-12 | not named in the repository; no cross-reference in the specification | pending (Kirtan staging window) | no spec names ACC-12 | — |
| ACC-13 | not named in the repository; no cross-reference in the specification | pending (Kirtan staging window) | no spec names ACC-13 | — |
| ACC-14 | not named in the repository; related to IMP-705 step 2: "Run make eval PROVIDER=MOCK DATASET=trips/v1 twice and confirm identical metrics (reproducibility, ACC-14)" | pending (Kirtan staging window) | not an E2E scenario; two MOCK evaluation runs with identical metrics ([final-baseline.md, Reproducibility](../../eval/reports/final-baseline.md#reproducibility-card-step-2-acc-14); runs `20261119T182737Z-mock` and `20261119T182745Z-mock`) | local runs of IMP-705 (RUN-083), no CI run |
| ACC-15 | not named in the repository; related to IMP-702 step 3 (injection: SQL strings stored as text, prompt-injection notes change nothing) | pending (Kirtan staging window) | `apps/api/tests/api/test_injection.py` (TC-349, TC-357; its docstring names ACC-15) | CI 45037634091 job `api` (`make test-api`) |
| ACC-16 | not named in the repository; related to E2E-05 "Edit or remove an activity" (§13.4) | pending (Kirtan staging window) | `itinerary-edit.spec.ts` (same test as ACC-05) | E2E 45037634127: "Run itinerary editing and restore" |
| ACC-17 | not named in the repository; related to E2E-07 "Handle an AI provider failure" (§13.4; quota case of IMP-701 step 4) | pending (Kirtan staging window) | `provider-failure.spec.ts` "E2E-07 TC-371: a provider quota pause offers the rule-based plan and changes nothing" | E2E 45037634127: "Run provider failure with quota exhausted" |
| ACC-18 | not named in the repository; related to E2E-06 "Save and reopen the trip" (§13.4) | pending (Kirtan staging window) | `reopen.spec.ts` (same test as ACC-10) | E2E 45037634127: "Run the regression specs" |

Staging summary: **0 of 18 run on staging; 18 pending** (Kirtan staging window, due 26 Nov 2026). When the re-run happens, each row gets the date, the tester, the provider (GEMINI or MOCK scenario), pass or fail and, for a failure, a defect in [defects.md](../test-reports/defects.md).

## High-priority test execution summary (CHK-20)

The repository does not tag tests by priority. The summary below is therefore suite-level: every suite of `make check` and every E2E step, which include the critical tests of specification §13.3. Lines are quoted exactly from the run logs (`gh run view <id> --log`, read-only).

### CI on the candidate: [CI 45037634091](https://github.com/het-lathiya/Group12/actions/runs/45037634091) (push, `4fe514c`, 22 November 2026, success)

| Job | Step | Result line |
| --- | --- | --- |
| `lint-types` | `make lint` | `All checks passed!` |
| `lint-types` | `make typecheck` | `Success: no issues found in 123 source files` |
| `lint-types` | `make imports` | `Contracts: 6 kept, 0 broken.` |
| `lint-types` | `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` |
| `unit` | `make test-unit` | `1215 passed, 1 warning in 13.52s` |
| `unit` | `make test-contract` | `91 passed, 2 deselected, 1 warning in 18.14s` |
| `unit` | `make test-web` | `Test Files  43 passed (43)`; `Tests  288 passed (288)` |
| `api` | `make test-api ARGS='--cov=app --cov-report='` | `590 passed, 1 warning in 214.57s (0:03:34)` |
| `api` | `make test-authz ARGS='--cov=app --cov-append --cov-report='` | `87 passed, 14 skipped, 1 warning in 44.23s` (the 14 skipped are the cut extension cases, IMD-65) |
| `guards` | Secret scan of the full history | `445 commits scanned.`; `no leaks found` |
| `audit` | pip-audit of the API dependencies | `No known vulnerabilities found` |
| `audit` | npm audit (critical findings fail) | `11 moderate severity vulnerabilities` (none critical; the step passed) |
| `attribution` | — | skipped on push |

### E2E on the candidate: [E2E 45037634127](https://github.com/het-lathiya/Group12/actions/runs/45037634127) (push, `4fe514c`, success; MOCK, local stack)

| Step (job `e2e`) | Result line |
| --- | --- |
| Run the journey | `Running 4 tests using 2 workers`; `4 passed (40.8s)` |
| Run the map specs | `Running 8 tests using 2 workers`; `8 passed (20.2s)` |
| Run itinerary editing and restore | `Running 8 tests using 2 workers`; `8 passed (51.6s)` |
| Run the regression specs (`auth trip-create generate validate-costs reopen ownership keyboard extensions`, 1280 px) | `Running 21 tests using 2 workers`; `9 skipped`; `12 passed (23.8s)` |
| Run the floor journey with the nine cut-list switches disabled | `Running 1 test using 1 worker`; `1 passed (14.7s)` |
| Run provider failure with a timeout | `Running 2 tests using 2 workers`; `1 skipped`; `1 passed (6.9s)` |
| Run provider failure with quota exhausted | `Running 2 tests using 2 workers`; `1 skipped`; `1 passed (7.4s)` |
| Job `staging` | skipped |

No step of either run reports a failed test.

### Local on this branch

| Command | Result line |
| --- | --- |
| `make check` | exit 0 on branch commit `f6715c1` (22 Nov 2026): `All checks passed!`, `All matched files use Prettier code style!`, `Success: no issues found in 123 source files`, `Contracts: 6 kept, 0 broken.`, `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date`, unit `1219 passed, 1 warning in 7.97s`, contract `91 passed, 2 deselected, 1 warning in 18.45s`, api `590 passed, 1 warning in 114.68s (0:01:54)`, authz `87 passed, 14 skipped, 1 warning in 22.60s`, web `Tests  288 passed (288)` |
| `make e2e ARGS='smoke'` | `12 passed (16.9s)` (exit 0, local Supabase stack, MOCK provider, branch commit `f6715c1`; the first attempt gave `12 failed` because the Next.js dev server stopped at start-up to print an upgrade notice, and the unchanged retry passed) |

### Not run

| Check | Reason |
| --- | --- |
| `make smoke URL=<staging API URL>` (E2E-09) | candidate not deployed to staging; Kirtan staging window, due 26 Nov 2026 |
| Live smoke against staging (Gemini) | needs Kirtan's staging window; operator dispatch only; `.github/workflows/live-smoke.yml` does not exist (PD-IMP-799-2) |
| TC-370 (LIVE variant of E2E-03 on staging) | staging window |
