# Journey test report, Sprint 4 (IMP-414)

The journey of `apps/web/e2e/journey.spec.ts` (tag `@journey`; TC-369, TC-370): sign up (local) or sign in (staging), create a SAMPLE trip in Sampleton, generate, wait for `completed`, remove one item (API-27, after the confirm dialog) and retime another (API-26), reload, open latest (API-09), and check that both edits, `plan_revision` and the server totals of the last edit's answer persist. axe runs on the itinerary page.

Test data is created through the app only. Before the run the account's trips are deleted through the API (API-08, API-12). After the run a local account is deleted with everything it owns; on staging the account's trips are deleted through the API again.

## Local stack in CI (MOCK)

| Field | Value |
| --- | --- |
| Date | 2026-11-13 |
| Commit | `5edbcd9` (the spec as committed in this PR; the later amend changed only the part records) (branch `feat/IMP-414-journey`) |
| Base URL | `http://localhost:3000` (Supabase CLI local stack, API with `AI_PROVIDER=MOCK`) |
| CI run | [43427715979](https://github.com/het-lathiya/Group12/actions/runs/43427715979) (manual run on the branch, attempt 2; attempt 1 failed to start the stack: port 54324 already in use on the runner) |
| Duration | job 6 min 21 s; journey step 1 min 58 s (`Running 4 tests using 1 worker`), about 12 to 15 s per test |
| Outcome | **Failed**: `4 failed` (each width failed, then failed its retry), all on one check. After API-27 answers 200, the toast `Removed <place>` never appears (product bug in IMP-408 item-editor, see notes). Every other step passed at every width: sign-up, trip reset, wizard, generation, removal saved, retime saved, reload, Open latest, the edits, `plan_revision` and the totals of the last edit's answer, axe, and no horizontal scroll. The check is soft, so these later steps ran |
| Generation latency | 2138 to 2253 ms from the first-generation notice to `completed` (provider `MOCK`, outcome `model`) |
| Warnings | none printed; no critical axe violation |
| Notes | Four widths (360, 768, 1280, 1920 px), one new account each; each account was deleted in teardown without error. The removal toast is missing because `ItemEditor` calls `remove.mutate(vars, { onSuccess })`, and the hook's own `onSuccess` first writes the changed day into the cache. That unmounts the removed card's `ItemEditor`, and TanStack Query does not run per-call callbacks after the calling component unmounts, so the toast, its Undo and the focus move never run. Earlier runs on the branch: [43423666996](https://github.com/het-lathiya/Group12/actions/runs/43423666996) and [43426753451](https://github.com/het-lathiya/Group12/actions/runs/43426753451) failed on test bugs fixed before this run (the DELETE URL carries `?plan_revision=`) and on the same toast. |

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
