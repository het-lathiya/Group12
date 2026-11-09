# FIX SG-3 · playwright-axe

| Field | Value |
| --- | --- |
| Run | RUN-058 (grouped run, IMD-121), part 7 of 7 |
| Fix | Axe checks in the Playwright specs (NFR-025) |
| Owner | Krrish Kamani |
| Status | PR_OPEN |
| Base commit | 16839a0 |
| Branch | feat/IMP-410-411-412-trips-budget-states |

## Changed files

- `apps/web/e2e/axe.ts` (created): `checkA11y(page)` runs axe on the current page with `@axe-core/playwright`.
  - A "critical" violation fails the test (NFR-025).
  - "Serious" violations are printed in the test output and added as an `axe-serious` test annotation.
  - It uses the same axe-core rule set as `tests/axe.ts`, with the layout rules on, because a browser has a layout.
- `apps/web/tests/axe.ts`: the rules that need a layout (`color-contrast`) are now the shared constant `LAYOUT_RULES`. The unit helper still turns them off for jsdom, so its behaviour is unchanged.
- `apps/web/e2e/smoke.spec.ts`, `auth.spec.ts`, `trip-create.spec.ts`, `journey.spec.ts`: one `checkA11y` per page. The pages are `/`, `/dashboard` and `/sign-in` (smoke), `/sign-up` (auth), `/trips/new` and `/trips/{id}/generate` (trip-create), and `/trips/{id}/itinerary` (journey). Each check is added after the page is shown. No journey step was changed (IMP-414 extends them).
- `apps/web/package.json`, `apps/web/package-lock.json`: **adds the devDependency `@axe-core/playwright` `^4.14.0`** (lockfile updated). It was not a dependency before. Version 4.14.0 was released on 15 October 2026, its only dependency is `axe-core ~4.14.0` (already used, `^4.14.0`), and its peer is `playwright-core`. It is needed because the run prompt asks for this package when it is missing.
- `docs/progress/parts/FIX-SG3-playwright-axe.md`: this record.

## Commands

| Command | Result |
| --- | --- |
| `npx playwright test --list` | `Total: 40 tests in 4 files` (the specs compile with the helper) |
| `make lint` | `All checks passed!`; ESLint `✖ 1 problem (0 errors, 1 warning)`, a warning that predates this run; `All matched files use Prettier code style!` |
| `make typecheck` | `Success: no issues found in 111 source files` |
| `make test-web` | `Tests  145 passed (145)` |
| `npm install` | `13 vulnerabilities (2 low, 11 moderate)`: all predate this run (eslint, shadcn and ts-morph chains); none comes from `@axe-core/playwright` or `axe-core` |

Not run: `make e2e`, because it needs the composed local stack (Supabase and the API), and this machine has no Docker. The critical and serious results per page are therefore not recorded yet; the e2e workflow or the operator's local run produces them.

## Acceptance

| Criterion | Status | How |
| --- | --- | --- |
| Critical axe violations fail an e2e test (NFR-025) | not verified (needs `make e2e`) | `expect(critical).toEqual([])` in `e2e/axe.ts` |
| Serious violations are listed in the test output | not verified (needs `make e2e`) | `console.log` and the `axe-serious` annotation in `e2e/axe.ts` |
| Called once per page in the existing specs, journey steps unchanged | verified | the diff of the four specs adds only `checkA11y(page)` lines and the import |

## Proposed decisions, blockers and open issues

- Open issue: the first e2e run may report serious contrast violations that jsdom never checked. They are listed, not failed, as the run asked.
