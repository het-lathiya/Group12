# RUN-077 · journey flake (Open latest)

- Run id: RUN-077
- Owner: Krrish Kamani (0 points)
- Status: PR_READY (not pushed)
- Base commit: 0e15ae7
- Cause (spec timing; the app is correct): CI run 43752904069, chromium-1280 (the retry passed), failed at `apps/web/e2e/journey.spec.ts:315` with `Expected: ".../trips/<id>/itinerary"` and `Received: "http://localhost:3000/dashboard"`. The spec runs `page.goto("/dashboard")` and presses Enter on Open latest without waiting. `apps/web/app/(app)/dashboard/page.tsx:46` renders the button with `disabled={latest.isPending}` until API-09 (`useLatestItinerary`) answers on the fresh page load. Playwright's `locator.press` does not check that the element is enabled, so when the press landed before API-09 answered, Enter went to a disabled button and nothing happened. Disabling the button while the latest plan loads is intended (FR-014), and once it is enabled it navigates through `router.push` (`page.tsx:28`), so the app needs no change.
- Fix: the spec waits until the Open latest button is enabled (`await expect(openLatest).toBeEnabled()`) before pressing Enter. No retry and no timeout change; all viewport projects still run.
- Files changed: apps/web/e2e/journey.spec.ts; this record.
- Commands: `cd apps/web && npx eslint e2e/journey.spec.ts` → no output, exit 0; `npx prettier --check e2e/journey.spec.ts` → `All matched files use Prettier code style!`; `npx tsc --noEmit -p .` → no output, exit 0 (after `npx next typegen` generated the untracked `.next/types` that the worktree lacked; before that, only the existing `PageProps`/`LayoutProps` errors appeared, none in the spec).
- Not run: `make e2e ARGS='journey --repeat-each=5'`: no Docker or local Supabase auth stack on this machine.
- Acceptance:
  - Journey no longer presses Open latest while it is disabled: verified by reading the code (the wait comes before the press); not verified by repeated E2E runs (evidence missing until CI).
  - App behaviour unchanged: verified, because no app file was changed.
- Blockers: none.
- Proposed decisions: none.
- Open issues: the CI journey job should confirm the fix; other specs that `press()` controls disabled while loading may race the same way (not audited).
