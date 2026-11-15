# IMP-607 · regen-controls

- Run id: RUN-076b
- Owner: Krrish Kamani (2 points)
- Status: MERGED-READY for review; local gate passed, TC-376 browser execution awaits CI.
- Base commit: ce2c63d
- Files changed: apps/web/components/itinerary/DayColumn.tsx, apps/web/app/(app)/trips/[tripId]/itinerary/page.tsx, apps/web/lib/api/queries.ts (block // IMP-607), apps/web/components/generation/GenerationProgress.tsx, apps/web/tests/unit/itinerary/DayColumn.test.tsx, apps/web/tests/unit/itinerary/Regeneration.test.tsx, apps/web/e2e/itinerary-edit.spec.ts, .github/workflows/e2e.yml; this record.
- Commands: `make openapi` → `openapi: wrote openapi.v1.json`; no tracked contract changes because API-30/31 already declare the final shapes. Final make result lines are recorded below.
- Acceptance: verified by component tests for the controls and hooks. Tests cover keyboard day control, full-plan confirmation/cancellation, request revision/scope, disabled controls, progress and completion, invalidation of itinerary/costs/warnings/versions, and feature switch hiding. TC-376 regenerates a day and the whole plan, restoring each pre-regeneration version through Versions, at all configured browser widths.
- UI uses existing Button, ConfirmDialog, GenerationProgress, FallbackNotice, PrivacyNotice and ErrorState; no dependency added. Loading, focus, labels and touch targets follow docs/guides/ui-design.md.
- Files outside the run list: GenerationProgress.tsx → reuse its polling and retry states inline, invalidate derived views after completion; tests/unit/itinerary/Regeneration.test.tsx → exercise the page and real hooks beside DayColumn tests; .github/workflows/e2e.yml → the existing dispatch selected only journey/map paths, so explicitly run the required itinerary-edit file in the same dispatch.
- Screenshots: to be added by members.
- Blockers: none.
- Proposed decisions: none.
- Open issues: local E2E needs the unavailable Docker stack; the single CI dispatch supplies browser evidence.

## Card steps, acceptance criteria and test commands (verbatim)

**Implementation**

1. Implement API-30 POST /api/v1/trips/{trip_id}/itinerary/days/{day_number}/regenerate and API-31 POST /api/v1/trips/{trip_id}/itinerary/regenerate with body RegenerateIn (plan_revision, mode); both handled in app/generation/router.py (IMD-13), return 202 + GenerationOut and reuse the API-22 job protocol (one active job per trip, request-hash idempotency, caps).
2. Build the day-scoped gr-1 request: the day, its locked items as fixed constraints, neighbouring days' place ids as exclusions, remaining budget share; scope day with scope_day_number in ai_generations (IMD-17).
3. Save step for scope day: in one transaction verify plan_revision, replace only that day's unlocked items (the regeneration snapshot was already written when the job was started by API-30/API-31, always, IMD-18), recompute and revalidate the whole trip, bump plan_revision, write warnings and complete the generation; other days' rows untouched.
4. Full regeneration: same transaction pattern, locked items preserved, previous plan restorable through versions (reason regeneration).
5. On failure or stale revision the plan is unchanged and the generation ends failed (or 409 STALE_PLAN at start).
6. UI: "Regenerate day" in DayColumn and "Regenerate all" with ConfirmDialog; progress via GenerationProgress; outcome notice via FallbackNotice.
7. Guard both with the IMD-11 flag 'regeneration'.

**Interfaces**

- API: API-30, API-31, API-23, API-24 · Tables: ai_generations, itinerary_days, itinerary_items, itinerary_versions, itinerary_warnings, trips · Modules: MOD-B08, MOD-B06, MOD-F04 · Components: DayColumn, GenerationProgress, ConfirmDialog, FallbackNotice · Env: FEATURES_DISABLED · Other: gr-1 scope day

**Acceptance criteria**

- FR-067 AC1-AC2 hold (TC-213, TC-214); FR-068 AC1-AC2 hold (TC-215, TC-216).
- Rows of non-target days are byte-identical before and after a day regeneration (row hash comparison in the test).
- Locked items keep day and start_time (TC-313); restore of the pre-regeneration version works (TC-376, with IMP-610).
- With 'regeneration' disabled the routes return 404 and manual editing remains (TC-372).

**Tests**

- apps/api/tests/api/test_generations.py — TC-213, TC-214, TC-215, TC-216, TC-313 — `make test-api ARGS='-k regenerate'`
- apps/web/e2e/itinerary-edit.spec.ts — TC-376 — `make e2e ARGS='itinerary-edit'`


## Single integration fix

- Initial web result: `Tests  1 failed | 282 passed (283)`. The new notice assertion expected wording that FallbackNotice does not use; it now asserts the actual shared notice text. The final suite reports `Tests  283 passed (283)`.
- Added the shared loading icon to Regenerate all, kept it available for an existing empty plan, and made the confirmation describe a backup when Versions is switched off. Inline progress says "Plan ready." and clears after the saved plan refreshes.
- Verified: keyboard day activation and scope/revision payload; confirmation cancellation performs no write; confirmation starts full scope; active controls disable; progress polls; completion invalidates itinerary, costs, warnings and versions; FallbackNotice shows the outcome; regeneration-off hides both controls (TC-372).
- Not yet verified: TC-376 browser execution; the exact file is discovered in all four configured width projects and is wired into the branch's single E2E dispatch. Screenshots remain to be added by members.
- No dropped parts, blockers or proposed decisions. This is this owner's only integration fix commit.

## Final batch checks (RUN-076b)

Database: disposable PostgreSQL 16.15 with pgvector 0.6.0 on loopback port 55476, extracted under a task-owned temporary directory; no system installation. It was stopped and the cluster, packages and connection settings were removed after testing. Alembic: `0007 (head)` before and after; no migration added.

| Command | Exact result lines |
| --- | --- |
| `make lint` | `All checks passed!`; `232 files already formatted`; `✖ 1 problem (0 errors, 1 warning)` (existing client navigation warning); `All matched files use Prettier code style!` |
| `make typecheck` | `Success: no issues found in 123 source files`; `✓ Types generated successfully` |
| `make imports` | `Contracts: 6 kept, 0 broken.` |
| `make test` (all five suites) | `======================= 1185 passed, 1 warning in 19.39s =======================`; `================= 91 passed, 2 deselected, 1 warning in 20.98s =================`; `================== 564 passed, 1 warning in 195.46s (0:03:15) ==================`; `============================= 71 passed in 44.04s ==============================`; `      Tests  283 passed (283)` |
| `make test-api ARGS='-k regenerate'` | `================ 21 passed, 543 deselected, 1 warning in 16.64s ================` |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` |
| `make check` | `make check exit: 0`; all constituent checks passed. The final `make test` above also includes the subsequently added day-theme provenance regression. |
| `make e2e ARGS='itinerary-edit --list'` | `Total: 4 tests in 1 file` |
| `(cd apps/api && .venv/bin/alembic heads)` | `0007 (head)` |

Not run locally: `make e2e ARGS='itinerary-edit'` requires the local authentication stack, and Docker is unavailable in this WSL distro. Discovery is verified; TC-376 browser execution is not yet verified. The branch's one E2E dispatch includes this file. No live provider or recorded evaluation run was used.

## RUN-076c · restore-toast animation and axe timing (16 November 2026)

- Run id: RUN-076c; head before: 9d43947; branch: feat/S6-B-regenerate; existing PR #282. Preflight fetched/pulled cleanly, origin/main remains ce2c63d, and the PR is MERGEABLE with merge state CLEAN. The project virtual environment was already available.
- Commit owner, author and committer: Krrish Kamani <krrishkamani51@gmail.com>. This run makes one fix commit.
- Cause: animation-blend. In CI run 43750541683 the first 360 px scan passed; the second scan, after full regeneration and restoration, failed on the toast title. The outcome is the restore notification `Version ${version.version_no} restored`, emitted by versions/page.tsx's restore onSuccess. Regeneration itself shows an inline completion message.
- Colour source: components/ui/sonner.tsx maps --normal-text to --popover-foreground and --normal-bg to --popover. globals.css resolves these to **#1c1917 on #ffffff**, measured in Chromium from the actual tokens and installed Sonner CSS: **17.4883:1**. Providers renders the default Toaster; the toast has only cn-toast and no muted or opacity class override. Sonner's title inherits its colour.
- CI sampled **#8d8b8a on #fcfcfc = 3.3054:1**, below the unchanged 4.5:1 requirement. The installed Sonner CSS transitions transform/opacity over 400 ms. A read-only 360 px reproduction observed data-mounted=true while opacity was still 0 and two CSSTransitions were running; after settling, opacity was 1 with no running animations and the high-contrast token colours remained. This identifies the transient blend rather than a token-colour defect; Krrish owns the spec/helper fix.
- Change: TC-376 now waits for its specific restore toast to have data-mounted=true before navigating back. The shared e2e/axe.ts helper waits for mounted toast elements and for document.getAnimations() to contain no running animation before analysis. Every caller uses this same scan entry point, so the animation barrier belongs there. Existing critical/serious assertions, colour-contrast enablement, targets and all four viewport projects remain intact.
- Files changed: apps/web/e2e/itinerary-edit.spec.ts; apps/web/e2e/axe.ts; this record. Production toast/token files are unchanged.

| Command | Exact result lines |
| --- | --- |
| `make lint` | `All checks passed!`; `232 files already formatted`; `✖ 1 problem (0 errors, 1 warning)` (existing client navigation warning); `All matched files use Prettier code style!` |
| `make typecheck` | `Success: no issues found in 123 source files`; `✓ Types generated successfully` |
| `make test-web` | `Test Files  42 passed (42)`; `Tests  283 passed (283)` |
| `make e2e ARGS='itinerary-edit --list'` | `Total: 4 tests in 1 file` |
| Scratch 360 px Chromium diagnostic importing the actual shared helper with the real tokens/Sonner CSS | `axe scan 1 on blank: []`; `1 passed (2.0s)`; observed running enter transitions before the helper and opacity 1/no running animations afterwards |
| `git diff --check` | empty output |

- Not run locally: `make e2e ARGS='itinerary-edit'`; Docker and the local authentication stack are unavailable in this WSL distro. The CSS-only diagnostic is not TC-376 journey execution. TC-376 on the new commit at 360/768/1280/1920 remains not verified until the single new E2E dispatch completes; its URL/result is reported in the run's sync report.
- Status: local checks passed; one branch E2E dispatch follows the plain push. PR title/body are unchanged. No second fix is authorized if that run fails again.
- Blockers: none. Proposed decisions: none.
