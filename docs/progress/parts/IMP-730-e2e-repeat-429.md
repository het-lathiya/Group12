# IMP-730 · e2e-repeat-429 part (E2E repeat runs and the API rate limit)

- Card: IMP-730 (0 points, Amendment A2 §12 Batch C3), follow-up
- Part: e2e-repeat-429
- Run id: RUN-093 (batch F, Sprint 7, any-city follow-up)
- Owner: Krrish (Krrish Kamani)
- Status: PR_OPEN candidate on `fix/IMP-730-run-093-followups`
- Base commit: 445080f (on `main`)
- Traces to: IMD-203 (pattern), IMD-12 / IMP-511 (limiter), TC-376 (E2E-05), IMD-219

## Cause (reproduced before the change)

- **Symptom.** E2E dispatch 45228887894 ran with `repeat_each=3`. Its `e2e` job's "Run itinerary editing and restore" step failed 5 of 24 tests in `e2e/itinerary-edit.spec.ts:270` (E2E-05 TC-376), at 768, 1280 and 1920 px. Each failure was `expect(response.status()).toBe(200)` receiving **429**. The failing steps were "Remove the must-visit item", "Create and generate a trip…", "Regenerate day 2…" and "Change the duration…".
- **Limiter.** `app/core/rate_limit.py` `expensive_request` is used by the generation, itinerary, places and live routers. It checks two sliding one-minute windows, `user:<id>` and `address:<client host>`, each against `RATE_LIMIT_PER_MIN` (Settings default 60).
- **Why repeats hit it.** Every test already signs in as its own user (`users.create(...)` uses a unique email), so the per-user window is not what runs out. Playwright runs fully parallel, here 4 widths × 3 repeats × 2 tests, and every browser reaches the local API from one address (127.0.0.1). Together the tests passed 60 expensive requests a minute in the shared **address** window.
  - A scratch check shows this: with a limit of 60, distinct users from one address are limited after 60 calls; with a limit of 1000, 200 calls pass.
  - So the prompt's alternative, a distinct user per repeat, would not help.
- **IMD-203 fits.** It raised the local and CI stack's sign-in limit (Supabase `config.toml`) for repeated runs, with no effect on hosted environments. The same pattern applied to the API limiter is an E2E-stack environment value.

## Fix

- `.github/workflows/e2e.yml`: `RATE_LIMIT_PER_MIN: "1000"` in the workflow-level `env`, with a comment.
  - It reaches every API that the `e2e` and `live` jobs start (ports 8000, 8001 and 8002).
  - The `staging` job starts no API, so the value has no effect there.
- What does not change:
  - the Settings default (60, `app/core/config.py`) and `.env.example`;
  - the staging template value (`docs/guides/deployment-guide.md`: 60);
  - the limiter code;
  - the contract and the schema;
  - any spec assertion, including the floor journey's `toBeEnabled` wait.
- No E2E spec expects a 429 (`grep -rn '429\|RATE_LIMITED' apps/web/e2e/` prints nothing).
- `docs/test-reports/any-city-switch.md` is updated in three places:
  - the switch-ON authz deselect command now holds the two IMD-219 tests;
  - the PD-730-1 paragraph now reads as agreed (IMD-219);
  - a "Repeat runs (RUN-093)" note is added.
  The recorded RUN-092 result lines are kept. No workflow carries a deselect list: the `any-city` CI job runs `-m any_city` only. So no workflow deselect was changed.

## Changed files

- `.github/workflows/e2e.yml`
- `docs/test-reports/any-city-switch.md`
- `docs/progress/parts/IMP-730-e2e-repeat-429.md` (this record)

## Commands

| Command | Result line |
| --- | --- |
| `gh run view 45228887894 --log-failed` | `5 failed` · `19 passed (2.3m)`; `Expected: 200` `Received: 429` at `itinerary-edit.spec.ts:347` |
| scratch `SlidingWindowLimiter` check (not committed) | `distinct users, one address: limited after 60` · `limit 1000: no 429 in 200` |
| scratch `Settings()` with `RATE_LIMIT_PER_MIN=1000`, then without | `env read: 1000` · `default: 60` |
| `yaml.safe_load(e2e.yml)` | `1000 ['e2e', 'live', 'staging']` |
| `ANY_CITY_SUITE_ON=1 make test-authz ARGS='--deselect …` (the three authz deselects of A2 §3.4 and IMD-219)`'` | 88 passed, 14 skipped, 3 deselected, 1 warning in 25.75s |
| `make check` on the head | see the SYNC REPORT of RUN-093 |

## Acceptance

- **E2E repeat runs no longer depend on the shared 60-a-minute window: verified locally** by the limiter and Settings checks above.
- **No production default, Settings default, contract or schema change: verified** (`git diff --stat`; `make openapi-check`).
- **The `repeat_each` run on CI: NOT verified.** The operator must dispatch the E2E workflow with `repeat_each` on the PR head.
- **`make e2e ARGS='itinerary-edit'` locally: not run.** Starting the local API and stack would migrate the developer database, as in RUN-092. The change is a workflow environment value, and only a CI dispatch exercises it.

## Proposed decisions

none. The fix applies IMD-203's existing pattern to the API limiter in the E2E stack only.

## Open issues

- The RUN-093 prompt called the 429 "per-user". It comes from the per-address window, as explained above.
- A local `make e2e` with many workers can still reach 60 a minute unless `RATE_LIMIT_PER_MIN` is set in the developer's own `apps/api/.env`. The E2E README could mention this; that is not done here.

## Blockers

none
