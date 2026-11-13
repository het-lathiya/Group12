# Journey test report, Sprint 4 (IMP-414)

The journey of `apps/web/e2e/journey.spec.ts` (tag `@journey`; TC-369, TC-370): sign up (local) or sign in (staging), create a SAMPLE trip in Sampleton, generate, wait for `completed`, remove one item (API-27, after the confirm dialog) and retime another (API-26), reload, open latest (API-09), and check that both edits, `plan_revision` and the server totals of the last edit's answer persist. axe runs on the itinerary page.

Test data is created through the app only. Before the run the account's trips are deleted through the API (API-08, API-12). After the run a local account is deleted with everything it owns; on staging the account's trips are deleted through the API again.

## Local stack in CI (MOCK)

| Field | Value |
| --- | --- |
| Date | 2026-11-13 |
| Commit | `f741fd6` (branch `feat/IMP-414-journey`, with the IMP-408 removal fix) |
| Base URL | `http://localhost:3000` (Supabase CLI local stack, API with `AI_PROVIDER=MOCK`) |
| CI run | [43431854989](https://github.com/het-lathiya/Group12/actions/runs/43431854989) (manual run on the branch) |
| Duration | job 6 min 18 s; journey step `4 passed (36.7s)`, 6.9 to 7.6 s per test |
| Outcome | **Passed** at all four widths with no retry: sign-up, trip reset, wizard, generation, removal with the toast `Removed <place>` and focus on the next card, retime, reload, Open latest, the edits, `plan_revision` and the totals of the last edit's answer, axe, and no horizontal scroll |
| Generation latency | 2097 to 2135 ms from the first-generation notice to `completed` (provider `MOCK`, outcome `model`) |
| Warnings | none printed; no critical axe violation |
| Notes | Four widths (360, 768, 1280, 1920 px), one new account each, each deleted in teardown. Earlier runs on the branch failed: [43423666996](https://github.com/het-lathiya/Group12/actions/runs/43423666996) on a test bug (the DELETE URL carries `?plan_revision=`); [43426753451](https://github.com/het-lathiya/Group12/actions/runs/43426753451) and [43427715979](https://github.com/het-lathiya/Group12/actions/runs/43427715979) on the missing removal toast, an IMP-408 bug fixed in RUN-063b. |

## Staging with MOCK

Not run yet — staging window, IMD-137.

| Field | Value |
| --- | --- |
| Date | |
| Commit | |
| Base URL | |
| Outcome | |
| Generation latency | |
| Warnings | |
| Notes | Run with `gh workflow run e2e.yml --ref main -f base_url=<staging web URL>` while staging runs `AI_PROVIDER=MOCK`. Needs the secrets `E2E_STAGING_EMAIL` and `E2E_STAGING_PASSWORD`, and API-12 (IMP-602) for the trip reset. |

## Staging with Gemini

Not run yet — staging window, IMD-137.

| Field | Value |
| --- | --- |
| Date | |
| Commit | |
| Base URL | |
| Outcome | |
| Generation latency | |
| Warnings | |
| Notes | The same staging job while staging runs `AI_PROVIDER=GEMINI`. The job log prints `generation: provider …, outcome …, … ms to completed`. |
