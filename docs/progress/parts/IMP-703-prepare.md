# IMP-703 · prepare part

- Run id: RUN-083 (batch run, agent F, part F4; Sprint 7 Batch B, IMD-202 "IMP-703 (prepare only)")
- Owner: Krrish (Krrish Kamani), lead of IMP-703
- Status: PARTIAL (preparation done; E2E axe evidence recorded locally in RUN-083b; the device and screen-reader sessions are still open)
- Base commit: f75aa94
- Branch: S7B/fixes
- Points: 0 now (the card's 3 points are earned by the members' sessions)
- Issue: #149
- Traces to: US-126; FR-114, FR-115; NFR-025, NFR-026; TC-373, TC-374, TC-382, TC-383

## Scope of this part

Prepare only. The sheet template (card step 3: "generate the observation-sheet template") and the automated checks of card step 4. No device, tester, date, consent, step result or finding was entered: those are entered by the members (Junaid runs the sessions, Krrish records).

## Changed files

- `docs/test-reports/accessibility-sprint7.md` (created): how to use the sheet and the §13 severity scale (IMD-41); session details (testers, consent, environment); the devices table (one iOS phone and one Android phone with model, OS and browser; one desktop screen reader); the six core journey steps of card step 1 (sign in, create trip, generate, edit, costs, summary) with their pages; the findings table (page, component, WCAG criterion, severity 1-4, reproduction steps, expected, observed, status, owner, fix PR, regression test); workarounds; sign-off; and the "Automated checks" section with this run's results.
- `docs/progress/parts/IMP-703-prepare.md` (created): this record.

## Commands run

Set-up as in `.github/workflows/e2e.yml`: the local Supabase stack started by the lead (`supabase status` showed it running; its values were loaded into the environment without printing them), `APP_ENV=test`, `AI_PROVIDER=MOCK`, `DB_AUTH_STUB=false`, `DATABASE_URL` the stack database on 127.0.0.1:54322, `ALLOWED_ORIGINS=http://localhost:3000`, `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1`, empty `FEATURES_DISABLED`.

| Command | Result line (quoted exactly) |
| --- | --- |
| `make db-migrate` (stack database) | `INFO  [alembic.runtime.migration] Running upgrade 0006 -> 0007, 0007 RAG store: pgvector, rag_documents and rag_chunks, item citations and retrieval record (A1 §5.3).` (`alembic current`: `0007 (head)`) |
| `make seed` | `seed sampleton: places inserted 30, updated 0, unchanged 0, deactivated 0` |
| `uvicorn app.main:app --port 8000` then `curl http://localhost:8000/health` | `{"status":"ok","version":"dev","environment":"test","provider":"MOCK"}` |
| `npm run build` in `apps/web` of the worktree | `Error: Turbopack build failed with 1 error:` / `Error: Could not find the Next.js package (next/package.json)` (the worktree's `node_modules` is a symlink outside the project root, which Turbopack does not follow) |
| `npm run build` in a copy of the tracked `apps/web` files outside the repository (`/tmp/e2e-f4/web`, `node_modules` hard-linked), first attempt | `✓ Compiled successfully in 21.1s`, then exit 1 from a post-build upgrade notice of the Next.js CLI (no upgrade was run) |
| same build, retried | exit 0 (route table printed); served with `node server.js` from the standalone copy on port 3000, `curl http://localhost:3000/` → `200` |
| `make e2e ARGS='journey --output /tmp/e2e-journey'` (`BASE_URL=http://localhost:3000`) | `Running 4 tests using 2 workers`; `4 failed`; `Error: browserType.launch: Executable doesn't exist at /opt/pw-browsers/chromium_headless_shell-1248/chrome-headless-shell-linux64/chrome-headless-shell` |
| `make e2e ARGS='keyboard --output /tmp/e2e-keyboard'` (`BASE_URL=http://localhost:3000`) | `Running 4 tests using 2 workers`; `4 failed`; same `Executable doesn't exist` error |
| `make test-web` | `Test Files  43 passed (43)`; `Tests  288 passed (288)` |

The API and web servers started for this run were stopped at the end (ports 3000 and 8000 closed afterwards).

## RUN-083b automated checks (20 November 2026)

- Run id RUN-083b, branch `feat/S7-B2-eval-finish` at `fddc7d1` (no web code changed on the branch), local macOS run, set-up as above. `make setup ARGS=--with-browsers` installed Chromium build 1248 (matching `@playwright/test` 1.64.1).
- The web dev server and the first `npm run build` stopped on the same Next.js CLI upgrade notice as in RUN-083 (no upgrade was run); the retried build exited 0 and was served from its standalone output on port 3000.

| Command | Result line (quoted exactly) | axe |
| --- | --- | --- |
| `make e2e ARGS='journey --output /Users/nidhi/S7B2-e2e/journey'` (`BASE_URL=http://localhost:3000`) | `Running 4 tests using 4 workers`; `4 passed (31.6s)` | 40 `axe scan` lines, each ending `[]` (for example `axe scan 1 on /sign-up: []`, `axe scan 10 on /trips/<trip>/costs: []`); no `axe serious` line, no `critical axe violations` failure |
| `make e2e ARGS='keyboard --output /Users/nidhi/S7B2-e2e/keyboard'` (`BASE_URL=http://localhost:3000`) | `Running 4 tests using 4 workers`; `4 passed (10.8s)` | 20 `axe scan` lines, each ending `[]` (for example `axe scan 1 on /sign-in: []`, `axe scan 5 on /trips/<trip>/versions: []`); no `axe serious` line |

No serious or critical violation was found, so no IMD-206 fix was made. No device or screen-reader finding was entered.

## Not run

| Command | Reason |
| --- | --- |
| axe scans of `journey.spec.ts` (TC-383) and `keyboard.spec.ts` (TC-374) | No browser launched: `@playwright/test` 1.64.1 needs Chromium headless shell build 1248, and `/opt/pw-browsers` holds only build 1243. `playwright install` was not allowed in this run. No axe result exists from this run. |
| Device and screen-reader sessions (TC-382) | Human task: Junaid runs them, Krrish records. |

## Acceptance criteria (card IMP-703)

| Criterion | Status (verified / not verified) | How |
| --- | --- | --- |
| A report exists with the devices, screen reader, date, tester and every observed finding with severity (US-126 AC1) | not verified | the report file and its template exist; the members' entries are still empty |
| Every severity 1 and 2 finding is fixed with a regression test or has an owner and a documented workaround | not verified | no session has run, so no finding exists yet |
| The keyboard-only journey (TC-374) and axe scans (TC-383) report no critical violations in CI (US-126 AC2, NFR-025) | verified locally (RUN-083b); CI not verified in this record | local runs: journey `4 passed (31.6s)` and keyboard `4 passed (10.8s)`, every `axe scan` line `[]`, no serious or critical line; the CI evidence is the `e2e.yml` dispatch on `feat/S7-B2-eval-finish`, whose URL is in the pull request |
| The template was produced and no finding, result or device observation was entered by this run | verified | `docs/test-reports/accessibility-sprint7.md` sections 2 to 5 are empty tables; section 6 quotes only this run's command output |

## Blockers

- Resolved in RUN-083b: E2E axe evidence (local journey and keyboard runs with Chromium build 1248).
- The device and screen-reader sessions (members).

## Proposed decisions

none

## Open issues

- No axe fix commit was made in this run: no scan ran, so no serious or critical violation was found (IMD-206 fixes need an observed violation).
