# IMP-730 · whole-task part (E2E @live, switch-ON CI jobs, ON/OFF record, floor-journey fix)

- Card: IMP-730 (0 points, Amendment A2 §3.4, §12 Batch C3, §13.2 TC-486 and TC-490, §13.3 E2E-10)
- Run id: RUN-092 (Batch C3, Sprint 7, inserted under IMD-215)
- Owner: Krrish (Krrish Kamani)
- Status: PR_OPEN candidate on `feat/S7-C3-any-city-verify`
- Base commit: 818c1d8 (on `main`)
- Traces to: A2 §2 (d), §3.4; TC-372 (floor journey), TC-486, TC-490; ACC-23

## Floor-journey diagnosis (STEP 0 of RUN-092)

- **Evidence.** The E2E runs 45205546757 (RUN-091 dispatch, failed) and 45156156851 (main 667c0d8, attempt 1 failed, rerun passed). Artifacts were downloaded outside the repository. The traces and error contexts of `playwright-report/floor-journey` were read.
- **Locator that timed out.** The test is declared at `e2e/journey.spec.ts:86` and fails at line 274. The locator was `getByRole('region', { name: 'Day 1' }).getByRole('form', { name: 'Edit time of Fixture History House (sample)' }).getByLabel('Duration (minutes)')`. `locator.fill` waited until the 120 s test timeout. The page snapshot shows the item's "Edit time" button and no edit form.
- **Timeline from the trace (ms).** DELETE of the removed item at 10025 (64 ms). The following GET of the itinerary starts at 10092 and takes 98 ms, so it ends at about 10190. The spec presses Enter on "Edit time" at 10178.
- **Root cause.** `useItemEdit` (`apps/web/lib/api/queries.ts`) runs the removal's `after` callback first: the "Removed …" toast and the focus move. Only then does it `await refresh()`, the itinerary refetch. While the mutation is pending, `ItemEditor` disables every edit control (`disabled={busy}`, one edit at a time). The spec waited for the toast and the focus, then pressed Enter on the still-disabled Edit button. Playwright's `press` does not wait for a button to be enabled, so the key press did nothing and the form never opened. Whether the refetch ends before the press depends on CI timing. That is why it passed before and fails intermittently now. #295 changed nothing in this path: its `queries.ts` diff only adds any-city hooks, and the trip-form changes are earlier in the journey.
- **Owner and fix.** The cause is in the spec, so the fix is in this part. Before pressing, the spec now waits with `await expect(editTime).toBeEnabled()`, the same pattern the spec already uses for "Open latest" (line 320). It is a synchronization fix: no retry and no timeout was added. The product behaviour (controls disabled while an edit saves) is as designed (IMP-408).

## Changed files

- `apps/web/e2e/journey.spec.ts`: the `toBeEnabled` wait before the "Edit time" press, with a comment (the floor-journey fix).
- `apps/web/e2e/live-city.spec.ts` (created): E2E-10 `@live`, TC-486. It is skipped unless the Playwright run has `!any_city_mode` in both switch variables.
  - "Liveton (SAMPLE)": search → result → resolve → building or ready → the select shows "Liveton (SAMPLE) (Live data)", currency INR → trip → preferences → generate with MOCK → itinerary with the "Live data" badge, "Price unknown", "Hours unknown", the OpenStreetMap badge and the "Data sources" footer, including the per-page entry "Guide text from Wikivoyage (Liveton (SAMPLE)), …" (IMP-726 attribution-api part) → costs page with "Known costs only: N stops have no price".
  - "Tinyham (SAMPLE)": the not-enough-data message with "Bigtown (SAMPLE)" and its "Search Bigtown (SAMPLE)" button.
  - axe on each screen; screenshots at 360 and 1280 px.
- `apps/web/playwright.config.ts`: unchanged. The live job picks the file and the two width projects on the command line.
- `.github/workflows/ci.yml`: one added job, `any-city`.
- `.github/workflows/e2e.yml`: one added job, `live`.
- Existing jobs are unchanged in both workflows.
- `apps/api/tests/conftest.py`: the opt-in fixture `any_city_suite_on` (`ANY_CITY_SUITE_ON=1`). The default behaviour is unchanged.
- `docs/test-reports/any-city-switch.md` (created): the TC-490 ON/OFF record, the commands, the CI jobs and the screenshots artifact.

## Commands

| Command | Result line |
| --- | --- |
| `npx playwright test --list e2e/live-city.spec.ts` | Total: 8 tests in 1 file |
| `npx tsc --noEmit -p .`, `npx eslint e2e/live-city.spec.ts` | no output (exit 0) |
| TC-490 switch OFF (unit · contract · authz · api) | 1851 passed, 1 warning in 9.72s · 99 passed, 2 deselected, 1 warning in 19.85s · 87 passed, 14 skipped, 1 warning in 21.72s · 678 passed, 1 warning in 125.33s (0:02:05) |
| TC-490 switch ON, four §3.4 deselects (unit · contract · authz · api) | 1851 passed, 1 warning in 8.68s · 96 passed, 5 deselected, 1 warning in 20.05s · 2 failed, 84 passed, 14 skipped, 1 deselected, 1 warning in 25.23s · 678 passed, 1 warning in 138.70s (0:02:18) |
| switch ON authz with the two extra deselects | 84 passed, 14 skipped, 3 deselected, 1 warning in 21.55s |

The E2E specs (the journey with its fix, and `@live`) cannot run locally without starting the local API against the developer database. They run in the one E2E dispatch of RUN-092 (`repeat_each=3`). Its link and result are in the SYNC REPORT.

## Acceptance

- **TC-486 E2E-10 `@live`: not verified locally.** It is verified by the RUN-092 E2E dispatch (`live` job, 3 repeats at 360 and 1280 px); see the SYNC REPORT for the outcome.
- **TC-490 record: verified,** with the two extra switch-ON authz failures explained in `any-city-switch.md` (PD-730-1). Both are inventory or start-up-configuration tests, not product defects.
- **Floor journey fixed without a retry or timeout increase: verified by diagnosis.** The pass needs the RUN-092 dispatch (3 repeats).
- **Screenshots at 360 and 1280 px:** taken by the `@live` spec and uploaded as the artifact `live-city-screenshots` of the RUN-092 dispatch.

## Proposed decisions

- **PD-730-1:** add `tests/authz/test_ownership.py::test_tc_065_an_unlisted_route_fails_the_check` and `tests/authz/test_route_inventory.py::test_inventory_docs_companions_are_only_fastapi_doc_pages` to A2 §3.4's switch-ON deselect list. The first walks the OFF route set; the second builds a production app, which correctly refuses the FAKE provider with the switch ON.

## Open issues

- The `@live` spec accepts either "Building your city…" or "Ready…" as the first state, because a repeated run finds Liveton already imported in the shared stack.
- The `any-city` CI job is not a required check (branch protection lists six jobs).

## Blockers

none
