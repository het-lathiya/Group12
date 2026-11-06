# IMP-216 · whole-task part

- Run id: RUN-043
- Owner: Kirtan (kirtan-S111)
- Status: **local and CI part done; the journey passes locally. The first e2e.yml run and the staging walk-through come after merge**
- Base commit: `dd2961b`
- Reviewer: Junaid (Junaid-Kureshi)
- Traces to: US-153; NFR-048; TC-369

## Changed files

- `apps/web/e2e/journey.spec.ts` (created, tag `@journey`). It signs a confirmed user in, creates a trip in Sampleton through the four wizard steps, and generates with MOCK. It then checks:
  - API-23 ends `completed` with provider `MOCK` and outcome `model`;
  - every place and start time of every day matches what API-24 returned, in order, through the day tabs below 768 px;
  - the same plan is still there after a reload;
  - the browser made no request to the Gemini host.

  Dates are relative to today, so the nightly run never reaches a fixed date.
- `.github/workflows/e2e.yml` (created). On push to `main`, nightly and by hand; never on pull requests, so the six required checks do not change. It starts the Supabase CLI local stack, migrates and seeds, starts the API with `AI_PROVIDER=MOCK`, builds and starts the web app from its standalone output, runs `make e2e ARGS='journey'` and uploads the Playwright report and the two server logs.
  - The stack's keys come from `supabase status -o env` inside the job and are masked. `make stack-up` runs with its output discarded, because `supabase start` prints the keys before they can be masked.
  - The CLI is pinned to 2.122.0, the version of the local runs.

No application code, contract, migration, `ci.yml` job, environment variable name or Make target changed.

## Preflight

`.github/workflows/e2e.yml` did not exist on `main`. The part records of IMP-112, IMP-213, IMP-215, IMP-217 and IMP-218 are all there.

## Commands run

| Command | Result line |
| --- | --- |
| `make stack-up`, `make db-migrate`, `make seed` | `seed sampleton: places inserted 0, updated 0, unchanged 30, deactivated 0` |
| `make e2e ARGS='journey'`, run 1 | `4 passed (18.9s)` |
| `make e2e ARGS='journey'`, run 2 | `4 passed (18.2s)` |
| `make e2e ARGS='journey'`, run 3 | `4 passed (17.5s)` |
| The `run:` steps of `e2e.yml` from the YAML, locally, with `CI=true`, the production web build and `BASE_URL` | every step ok; `4 passed (6.2s)`; API log and web log with no error line |
| Mutation: API with `MOCK_PROVIDER_SCENARIO=timeout` | `4 failed` (`page.waitForResponse: Test timeout of 30000ms exceeded.`) |
| `select count(*) from auth.users where email like 'e2e-%@example.test'` after the runs | `0` |
| `api.log` of the local workflow run, searched for tokens and e-mail addresses | `tokens 0, emails 0` |
| `actionlint -no-color .github/workflows/*.yml` (shellcheck on `PATH`) | `actionlint exit=0` |
| `make lint` | `All matched files use Prettier code style!` |
| `make typecheck` | `Success: no issues found in 85 source files` |
| `make imports` | `Contracts: 4 kept, 0 broken.` |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` |
| `make test` | unit `385 passed, 1 warning in 9.75s`; contract `35 passed, 1 warning in 0.93s`; api `231 passed, 1 warning in 86.97s (0:01:26)`; authz `28 passed in 19.19s`; web `Tests  80 passed (80)` |

Each `4 passed` covers the four Playwright projects: 360, 768, 1280 and 1920 px. The stack's values were held in the shell environment only, and the local `.next` output, which inlines the anon key, was deleted afterwards.

Local set-up of each run: `make stack-up`; the API started by hand on port 8000 with `APP_ENV=test`, `AI_PROVIDER=MOCK`, `DB_AUTH_STUB=false` and `SUPABASE_JWKS_URL`; Playwright started the web dev server.

## Acceptance

| Criterion | Status | How |
| --- | --- | --- |
| `journey.spec.ts` passes locally with MOCK and no Gemini call (US-153 AC1, TC-369) | verified | Three runs, `4 passed` each, including 360 and 1280 px. Provider `MOCK` from API-23; the browser check covers the browser only, and the API runs the MOCK adapter with no key |
| `journey.spec.ts` passes in `e2e.yml` | not verified | The workflow runs only after merge; its first run is recorded at the gate. Its `run:` steps passed locally from the YAML, except `make setup` and the action steps |
| `e2e.yml` is valid | verified | `actionlint exit=0` |
| On staging the path runs from the browser and a generation record row exists (US-153 AC2) | not verified | Needs Kirtan's set-up; see the checklist below |
| Known gaps are listed for the gate review (US-153 AC3) | verified | The section below |

## Staging walk-through (after Kirtan's set-up; not verified)

Run it once `deploy-staging.yml` has deployed with `AI_PROVIDER=MOCK`, the template's current value. Record the results at IMP-299.

1. Open `STAGING_WEB_ORIGIN` and sign up or sign in with a test account. Record that sign-in works with the hosted project (web; JWKS token accepted by the API).
2. Create a trip through the four wizard steps. Note the trip ID.
3. Press **Generate with AI** and wait for the itinerary.
4. From the browser's network panel, record:
   - API-23: `status`, `provider` (`MOCK`), `outcome`, `model_id`, `latency_ms`;
   - API-24: the number of days and items, and `plan_revision`.
5. Reload the itinerary page and confirm that the same plan is shown.
6. Show that a generation record row exists. RDS is private (IMD-100), so API-23 is the evidence: it reads that row. Add the generation ID.
7. Write down what each layer did: web, API, database, provider interface, generation record row.
8. Delete the test account (`python -m app.db.admin delete-user`, one-off ECS task, IMD-101) and in Supabase Auth.

## Known gaps (US-153 AC3)

- **The skeleton's plan is thin.** No routing, costs, validator rules, repair, rule-based fallback or retrieval yet (IMP-303 onwards). A provider failure ends `failed` until IMP-403.
- **The itinerary is read-only** (edits from IMP-405 onwards).
- **Gemini is not exercised.** The journey proves the provider interface with MOCK only.
- **`e2e.yml` runs only the journey.** `auth`, `trip-create` and `smoke` stay manual, and `trip-create.spec.ts` keeps a fixed date (`2026-12-04`).
- **No accessibility scan** in the journey (no axe dependency yet; IMP-703).
- **Sign-up through the screen is not in this journey.** It signs in with a confirmed user, as the card says; `auth.spec.ts` covers sign-up.
- **Development server warning.** `next dev` reports `Could not validate that a segment in your UI has instant navigation` for `/trips/[tripId]/itinerary`. It does not fail the journey, and the production build does not show it. Owner: IMP-213.
- **CI retries once** (`retries: 1` in `playwright.config.ts`), so a flaky pass shows as `flaky` in the report rather than as a failure.
- **`supabase/config.toml` sets `major_version = 17`,** while the specification names PostgreSQL 16 for the local stack's role. The journey ran on that stack as configured.

## Blockers

None. The journey exposed no application defect.

## Proposed decisions

- **PD-IMP-216-1 (`make e2e` does not start the API):** card step 2 asks for that, but this run keeps the Make targets unchanged. `e2e.yml` starts the API itself, and local runs start it by hand. Proposed: update the card.
- **PD-IMP-216-2 (`docs/progress/sprint-2.md`):** the card lists this file and places the staging notes there. This run limits the change to the spec, the workflow and this record, so the checklist is here and the gate card compiles it.
- **PD-IMP-216-3 (web server in `e2e.yml`):** the card says "web dev server"; the run prompt says to build and start the web app. The workflow uses the production standalone build, which is nearer to what is deployed.
- **PD-IMP-216-4 (`docs/guides/local-setup.md`):** `SUPABASE_JWKS_URL` is needed for local tokens with CLI 2.122.0 (noted in IMP-212). It may be missing from the guide.
