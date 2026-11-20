# Accessibility check on real devices, Sprint 7 (IMP-703)

Card: IMP-703 Accessibility check on real devices and fixes (HUMAN, 3 points, lead Krrish; issue #149). Traces to US-126; FR-114, FR-115; NFR-025, NFR-026; TC-373, TC-374, TC-382, TC-383.

**State of this report: prepared, not yet filled.** The sheet below (sections 2 to 5) is an empty template. Junaid runs the device and screen-reader sessions and Krrish records them (card step 1). Only the members enter devices, testers, dates, consent, step results and findings, and only what they observed (card step 2: "do not record findings that were not observed"). Section 6 holds the automated checks of RUN-083 and RUN-083b.

## 1. How to use this sheet

1. Fill section 2 (session details) before the session starts, one block per device or screen reader.
2. Walk the core journey of section 3 on each of the three set-ups and mark each step `pass`, `fail` or `not reached`, with a finding ID for every `fail`.
3. Add one row in section 4 per observed finding. Use the severity scale below.
4. After triage (card steps 3 and 5), update the status, owner, fix pull request and regression test of each finding. Every severity 1 and 2 finding is fixed with a regression test, or has an owner and a documented workaround (card acceptance criterion 2).

**Severity scale** (IMPLEMENTATION_SPEC §13, IMD-41): 1 = journey blocked or data exposed; 2 = a feature of the journey fails without a workaround; 3 = a feature fails with a workaround; 4 = cosmetic. Severity 1 and 2 defects block a gate.

**WCAG criterion:** the success criterion number and name if known (for example `1.4.3 Contrast (Minimum)`); leave `unknown` otherwise.

## 2. Session details (to be filled by the members)

### 2.1 Testers and consent

| Field | Value |
| --- | --- |
| Session lead (runs the sessions) | |
| Recorder | |
| Other testers (name, role) | |
| Consent recorded for each tester (yes / no, how and where it is kept) | |
| Environment tested (staging URL or local stack; commit) | |
| AI provider of that environment (GEMINI or MOCK) | |

### 2.2 Devices and screen reader

| Set-up | Device model | OS and version | Browser and version | Assistive technology and version (if used) | Tester | Date (YYYY-MM-DD) | Start and end time |
| --- | --- | --- | --- | --- | --- | --- | --- |
| iOS phone | | | | | | | |
| Android phone | | | | | | | |
| Desktop screen reader | (computer model) | | | (screen reader name and version) | | | |

## 3. Core journey steps (card IMP-703 step 1)

The core journey of card step 1 is: sign in, create trip, generate, edit, costs, summary. Mark each step per set-up with `pass`, `fail (F-NN)` or `not reached`.

| Step | Page | What the tester does | iOS phone | Android phone | Desktop screen reader |
| --- | --- | --- | --- | --- | --- |
| J1 Sign in | `/sign-in` | Sign in with the test account (or sign up first at `/sign-up`) and reach the dashboard | | | |
| J2 Create trip | `/trips/new` | Complete the trip wizard and save the trip | | | |
| J3 Generate | `/trips/{tripId}/generate` | Start generation, follow the progress and reach the itinerary | | | |
| J4 Edit | `/trips/{tripId}/itinerary` | Change the plan: move an item (move controls), change a time, remove an item; read the warnings | | | |
| J5 Costs | `/trips/{tripId}/costs` | Open the costs page and read the estimate, breakdown and any budget alert | | | |
| J6 Summary | `/trips/{tripId}/summary` | Open the trip summary | | | |

Notes per step (optional, observed facts only):

| Step | Set-up | Note |
| --- | --- | --- |
| | | |

## 4. Findings (to be filled by the members)

Only observed findings are recorded. IDs run F-01, F-02, and so on.

| ID | Set-up (device / screen reader) | Journey step | Page | Component | WCAG criterion | Severity (1-4) | Reproduction steps | Expected | Observed | Status (open / fixed / workaround) | Owner | Fix PR | Regression test |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| | | | | | | | | | | | | | |

Workarounds for open severity 1 and 2 findings (card acceptance criterion 2):

| Finding ID | Workaround | Owner | Due date |
| --- | --- | --- | --- |
| | | | |

## 5. Sign-off (to be filled by the members)

| Field | Value |
| --- | --- |
| All three set-ups completed (yes / no, which not and why) | |
| Open severity 1 or 2 findings (IDs, or none) | |
| Signed off by (name, date) | |

## 6. Automated checks

Card step 4: the axe scans in the keyboard and 360 px journeys (IMP-701) and the Vitest accessibility assertions; TC-383 and NFR-025 require no critical axe violations in CI.

### 6.1 Playwright journeys with axe (RUN-083, 19 November 2026, base `f75aa94`)

Set-up, as in `.github/workflows/e2e.yml`: the Supabase CLI local stack (started by the lead), `make db-migrate` (0001 to 0007) and `make seed` (Sampleton: `seed sampleton: places inserted 30, updated 0, unchanged 0, deactivated 0`), the API on port 8000 with `APP_ENV=test`, `AI_PROVIDER=MOCK`, `DB_AUTH_STUB=false`, and the production build of the web app (`npm run build`, exit 0) served from its standalone output on port 3000, with `BASE_URL=http://localhost:3000`. Each run had its own Playwright output folder outside the repository.

| Command | Result lines (quoted exactly) | axe results |
| --- | --- | --- |
| `make e2e ARGS='journey --output /tmp/e2e-journey'` | `Running 4 tests using 2 workers`; `4 failed`; each test: `Error: browserType.launch: Executable doesn't exist at /opt/pw-browsers/chromium_headless_shell-1248/chrome-headless-shell-linux64/chrome-headless-shell` | **not run**: no browser started, so no axe scan ran (0 `axe scan` lines in the output) |
| `make e2e ARGS='keyboard --output /tmp/e2e-keyboard'` | `Running 4 tests using 2 workers`; `4 failed`; same `Executable doesn't exist` error | **not run**: no axe scan ran (0 `axe scan` lines) |

Reason: the installed `@playwright/test` is 1.64.1, which needs Chromium headless shell build 1248; the container has only build 1243 under `/opt/pw-browsers` (`chromium-1243`, `chromium_headless_shell-1243`). Installing browsers was not allowed in this run. The axe results of TC-374 (`keyboard.spec.ts`, `expectNoSeriousA11y` after each page) and TC-383 (`journey.spec.ts`, `checkA11y`) therefore still have to come from an E2E run with a matching browser: the E2E workflow (`e2e.yml`, push to `main` or dispatch on the branch) or a member's local run. Record its run URL and its `axe serious` / `critical axe violations` lines here:

| Source (CI run URL or local run, date, commit) | Spec and project | Critical violations (quoted) | Serious violations (quoted) |
| --- | --- | --- | --- |
| Local run RUN-083b, 20 November 2026, `fddc7d1` (web code as on `main` `964327f`; see 6.1b) | `journey.spec.ts`, chromium-360, -768, -1280, -1920 | none: no `critical axe violations` line; every `axe scan` line ends `[]` | none: no `axe serious` line |
| Local run RUN-083b, 20 November 2026, `fddc7d1` | `keyboard.spec.ts`, chromium-360, -768, -1280, -1920 | none: no `critical axe violations` line; every `axe scan` line ends `[]` | none: no `axe serious` line |

### 6.1b Playwright journeys with axe (RUN-083b, 20 November 2026, branch `feat/S7-B2-eval-finish` at `fddc7d1`)

Set-up as in 6.1, on macOS: the Supabase CLI local stack, `make db-migrate` (0001 to 0007), `make seed` (`seed sampleton: places inserted 30, updated 0, unchanged 0, deactivated 0`), the API on port 8000 with `APP_ENV=test`, `AI_PROVIDER=MOCK`, `DB_AUTH_STUB=false` (`/health`: `{"status":"ok","version":"dev","environment":"test","provider":"MOCK"}`), and the production build of the web app served from its standalone output on port 3000, with `BASE_URL=http://localhost:3000`. `make setup ARGS=--with-browsers` installed Chromium build 1248, which `@playwright/test` 1.64.1 needs. The branch changes no web code. Each run had its own output folder outside the repository (`/Users/nidhi/S7B2-e2e/journey`, `/Users/nidhi/S7B2-e2e/keyboard`).

| Command | Result lines (quoted exactly) | axe results |
| --- | --- | --- |
| `make e2e ARGS='journey --output /Users/nidhi/S7B2-e2e/journey'` | `Running 4 tests using 4 workers`; `4 passed (31.6s)` | 40 `axe scan` lines (10 per project), each ending `[]`: `axe scan 1 on /sign-up: []`, `axe scan 2 on /dashboard: []`, `axe scan 3` to `6 on /trips/new: []`, `axe scan 7 on /trips/<trip>/generate: []`, `axe scan 8` and `9 on /trips/<trip>/itinerary: []`, `axe scan 10 on /trips/<trip>/costs: []`; no `axe serious` line |
| `make e2e ARGS='keyboard --output /Users/nidhi/S7B2-e2e/keyboard'` | `Running 4 tests using 4 workers`; `4 passed (10.8s)` | 20 `axe scan` lines (5 per project), each ending `[]`: `axe scan 1 on /sign-in: []`, `axe scan 2 on /dashboard: []`, `axe scan 3 on /trips/<trip>/itinerary: []`, `axe scan 4 on /trips/<trip>/costs: []`, `axe scan 5 on /trips/<trip>/versions: []`; no `axe serious` line |

`<trip>` stands for the trip ID each test created. This is a local run; the CI evidence of TC-383 comes from the `e2e.yml` dispatch on the branch, recorded in the pull request.

### 6.2 Vitest accessibility assertions (RUN-083)

| Command | Result lines (quoted exactly) |
| --- | --- |
| `make test-web` | `Test Files  43 passed (43)`; `Tests  288 passed (288)` |

The suite includes the axe-core assertions of `apps/web/tests/axe.ts` (`axeViolations`, colour contrast off because jsdom has no layout), used by `tests/unit/itinerary/ItemSources.test.tsx`, `tests/unit/profile/ProfileForm.test.tsx`, `tests/unit/trips/TripWizard.test.tsx` and `tests/unit/trips/dashboard.test.tsx`.

### 6.3 Fixes from automated checks

None in RUN-083: no axe scan ran, so no violation was found or fixed.

None in RUN-083b: the journey and keyboard scans found no serious or critical violation, so no IMD-206 fix was needed.
