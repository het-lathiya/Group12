# IMP-513 · whole-task part

- Run id: RUN-070
- Owner: Krrish (Krrish Kamani)
- Status: committed on `part/513`, not pushed; E2E deferred to integration and CI
- Base commit: 15475eb (built on PD-RUN-069-1, 628f716: MOCK default proposal and the journey's outcome assertion `model`, `deterministic_repairs` 0, kept)
- Traces to: US-123; FR-115; NFR-025; IMD-157, IMD-168
- Card steps built: 1 to 5 (step 3 in part, see PD-IMP-513-1)

## What was already in place (checked, not changed)

- `apps/web/components/shell/AppShell.tsx`: skip link first in the Tab order, focusing `<main id="main-content" tabIndex=-1>`; landmarks and labelled navigation (TC-278 unit cases). Step 1 needed no change.
- `apps/web/components/generation/GenerationProgress.tsx`: status changes in a polite live region, not the elapsed counter. Step 4 needed no change.
- `apps/web/components/itinerary/StalePlanBanner.tsx`: already `role="status"` (a polite live region), so it was not touched.
- `apps/web/components/itinerary/WarningsPanel.tsx`: grouped by severity (named regions "Errors", "Warnings", "Infos") then day (`h3`), with a polite live region for the counts. Not changed (PD-IMP-513-1).
- dnd-kit pointer and keyboard sensors and the Up, Down and day-select move controls (IMP-409).

## Changed files

- `apps/web/components/itinerary/MoveControls.tsx`:
  - Defect fixed: a button move to another day lost its announcement and its focus move. The item's MoveControls unmounts when the item leaves its day, and TanStack Query then skips the per-call `onSuccess` (the same cause as RUN-063b). MoveDndContext, which stays mounted, now provides its move function through a context, and MoveControls uses it (its own hook only outside MoveDndContext). The new DayColumn cases fail on the old file.
  - After a move, when the item's controls are not on screen (below 768 px the new day is a closed tab), focus goes to that day's tab. Focusing the tab opens it (Radix automatic activation).
  - The day button's visible text is now "Move" (was "Move to day"), so it is part of the accessible name "Move <place> to day N". This fixes the serious axe finding `label-content-name-mismatch` that CI reported on the itinerary page (E2E run 43584016895).
- `apps/web/components/itinerary/DayColumn.tsx`: the day heading reads "Day N, <date>" (a screen-reader-only comma). The section stays the region "Day N", and items stay in an ordered list with the time first.
- `apps/web/tests/unit/itinerary/DayColumn.test.tsx`: heading name updated, and four new cases run through the real hooks (`useItinerary`, the edit mutations), MoveDndContext and DayColumn, as the page renders them, with a 50 ms re-read like the RUN-063b case:
  - removing the last item by keyboard moves focus to the previous card;
  - removing the only item moves focus to the day heading;
  - TC-280: a move to another day is announced in the polite live region, and focus lands on the item's controls in the new day;
  - below 768 px (day tabs): the move is announced, and focus goes to the new day's tab, which is selected and shows the item.
- `apps/web/e2e/journey.spec.ts`:
  - `scan(page)` reuses `checkA11y` (`e2e/axe.ts`) and also fails on serious findings, which checkA11y only records as an `axe-serious` annotation. The thresholds are not weakened.
  - Scans run on sign-up (or sign-in on staging), the dashboard, wizard steps 1 to 4, the first-generation notice, the itinerary (after the first read and after the keyboard move) and costs.
  - Every button and link of the journey is now activated with Enter on the focused control, not a click.
  - TC-279: on a fresh dashboard the first Tab reaches the skip link, which is visible; Enter focuses `main`.
  - TC-374 and TC-280: an item is moved to another day by keyboard (choose the day in the select, Tab to Move, Enter). The test checks the polite announcement, then focus: the item's Move button in its new day, or below 768 px (the chromium-360 project) the new day's tab, which is selected. The item is visible there.
  - Costs is reached through the main navigation by keyboard.
- `docs/guides/keyboard-map.md` (created): the focus order, skip link and keys for the core pages, and the focus target of each edit.

## Commands and results

| Command | Result |
| --- | --- |
| `npx vitest run tests/unit/itinerary/DayColumn.test.tsx` (`make test-web ARGS='DayColumn'`) | `Tests  11 passed (11)` |
| The same file with `MoveControls.tsx` at HEAD (before the fix) | `Tests  2 failed \| 9 passed (11)` (the two move cases) |
| `npx vitest run tests/unit/itinerary tests/unit/shell tests/unit/generation` | `Test Files  16 passed (16)`, `Tests  110 passed (110)` |
| `npx prettier --check` on the four changed code files | `All matched files use Prettier code style!` |
| `npx eslint` on the four changed code files | exit 0, no output |
| `npm run typecheck` | exit 0 (`next typegen && tsc --noEmit`, no errors) |

Not run:

- `make e2e ARGS='journey'`: there is no local stack on this machine. Deferred to integration and CI.
- `make check`: needs PostgreSQL. Only this part's web tests, lint and typecheck were run.

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-115 AC1 / TC-279: every step of the core journey is reachable by keyboard, including the skip link | not verified (E2E deferred) | journey.spec.ts activates every control with Enter and checks the skip link and `main` focus; it has not run yet |
| FR-115 AC2 / TC-280: days, times and warnings are read in order; moves are announced politely | verified (unit) for the day heading "Day N, <date>", time-first ordered items, and the move announcement; warnings' severity headings not built (PD-IMP-513-1) | DayColumn cases "shows the day number and date…", "TC-196…" and "TC-280: announces a move…"; WarningsPanel's existing cases cover the severity groups and the live region |
| TC-374: keyboard-only journey | not verified (E2E deferred) | journey.spec.ts; the controls are activated with Enter after a programmatic focus. Full Tab traversal is checked only for the skip link and the select-to-Move step |
| TC-383: no serious or critical axe findings on each core page | not verified (E2E deferred) | `scan()` on 9 page states in journey.spec.ts. The known serious finding (`label-content-name-mismatch`, Move to day) is fixed. The other pages were never scanned before, see PD-IMP-513-2 |
| Focus fallback after a removal: previous card, else the day heading | verified | DayColumn cases "after removing the last item…" and "after removing the only item…", through the real hook path (IMD-157: Undo on, unchanged) |
| Below 768 px: after a keyboard move to another day, focus goes to a sensible target and the move is announced | verified (unit); E2E not verified (deferred) | DayColumn case "below 768 px…"; the chromium-360 project of journey.spec.ts checks the same on the page |
| TC-382: manual screen-reader pass | IMP-703, not claimed | |

## Blockers

none

## Proposed decisions

- PD-IMP-513-1: WarningsPanel severity headings. Card step 3 asks for the severity groups to have headings. The groups are named regions ("Errors", "Warnings", "Infos") with the day as `h3`. Visible severity `h3` headings with the days as `h4` would break `tests/unit/itinerary/WarningsPanel.test.tsx` ("groups by severity…" expects only day headings at level 3), which is outside this part's files. Proposal: a follow-up changes WarningsPanel and that test together.
- PD-IMP-513-2: axe serious findings. journey.spec.ts now fails on serious findings (card step 5), and pages other than the itinerary are scanned for the first time. If CI reports serious findings in files outside IMP-513 (for example the LockToggle name "Unlock <place>" against the visible "Locked" in `ItineraryItemCard.tsx`, or the map list buttons in `MapListFallback.tsx`), they need fixes there; the threshold is not to be lowered. Also proposed: move the serious threshold into `checkA11y` (`e2e/axe.ts`, outside this part) so every spec applies it.
- PD-IMP-513-3: removal focus order. As built (IMP-408, RUN-063b), focus goes to the next card, else the previous card, else the day heading. The run prompt describes "the previous card, or the day heading when the removed item was first". The tests cover the built order. Proposal: confirm the built order (next, previous, heading) as the rule, as `docs/guides/keyboard-map.md` states it.

## Open issues

- The E2E additions are untested until the journey runs in CI. Watch for the new skip-link and keyboard-move steps and the new scans in the first run.
- Focus after a move to another day below 768 px finds the target tab by its text "Day N". That text comes from the itinerary page's tab labels.

## RUN-070b

Owner: Krrish. Base commit: 640fc89.

- PD-IMP-513-1 resolved. `WarningsPanel.tsx`: each severity group now has a visible heading (Errors / Warnings / Infos) at level 3, labelling its section; the day heading moved from `h3` to `h4`. The outline is page `h1`, "Plan checks" `h2`, severity `h3`, day `h4`, with no skipped level. The polite live region for the counts is unchanged. `WarningsPanel.test.tsx` now expects the three level-3 headings in order and the day headings at level 4; no assertion was removed.
- Journey focus failure (E2E run 43586860101, all projects): step "Day to move X to" select, Tab, "Move X to day N" button focused, `e2e/journey.spec.ts`, itinerary page. Cause: the test. Playwright's `selectOption` does not move keyboard focus to the select, so Tab started elsewhere. `MoveControls.tsx` keeps the same `select` mounted on change (controlled state only), so the component was not at fault. Fix: `await daySelect.focus()` before `selectOption`; the Tab-lands-on-Move assertion and the announcement and focus assertions after the move are unchanged.
- Other findings, not fixed here: 3 serious `label-content-name-mismatch` nodes on the itinerary page (MapListFallback stop buttons) are owned by Manasvi in a parallel part. `/dashboard` `color-contrast` (1 node, first attempts only, target not captured) is outside this part and has no owner yet.
- Commands (from `apps/web`):
  - `npx vitest run tests/unit/itinerary/WarningsPanel.test.tsx`: `Tests  9 passed (9)`
  - `npx eslint` on the three changed files: no output (clean)
  - `npx prettier --check` on the three changed files: `All matched files use Prettier code style!`
  - `npm run typecheck`: `tsc --noEmit` finished with no errors
- Acceptance: TC-280 warnings read in order with severity headings: verified (unit). Journey focus step: fixed in the test, E2E deferred to the lead's new E2E run. Axe scans: not verified (deferred).

## RUN-071

Owner: Krrish. Part: PD-RUN-070b-2 (axe-targets). Base commit: aec7caa. File changed: `apps/web/e2e/axe.ts` (plus this record).

- `checkA11y` now writes every violation of any impact on every scan, before the `expect`, pass or fail: rule id, impact, page URL, and for each node its target selectors and `failureSummary`. The same list goes to the console and to the test as a JSON attachment named `axe-<scan number>-<pathname>`, so several scans in one test do not collide. A scan with no violations attaches an empty list.
- Unchanged: the serious annotation and console summary, the critical-only `expect(..., "critical axe violations (NFR-025)").toEqual([])`, `LAYOUT_RULES`, and which pages are scanned. No rule was excluded and no threshold changed.
- Commands (from `apps/web`):
  - `npx eslint e2e/axe.ts`: no output (exit 0)
  - `npx prettier --check e2e/axe.ts`: `All matched files use Prettier code style!`
  - `npm run typecheck`: `next typegen && tsc --noEmit` finished with no errors (exit 0)
- Acceptance: targets logged and attached on every attempt: not verified in CI (code path only; proof pending the lead's E2E dispatch). Threshold unchanged: verified by diff (the `expect` and the serious block are untouched apart from reusing the hoisted `where`).

## RUN-071 contrast

Owner: Krrish. Part: U3 (contrast fix, completes TC-383). Base commit: a106239. Files changed: `apps/web/app/(app)/dashboard/page.tsx`, `apps/web/tests/unit/trips/dashboard.test.tsx` (plus this record).

- Finding (E2E run 43590291645, first attempt, chromium-360, from the axe target log added in PD-RUN-070b-2): rule `color-contrast`, impact serious, page `/dashboard`, target `.border-border`, "insufficient color contrast of 3.33 (foreground #8b8988, background #fafaf9, 14px, normal weight)". The retry scan of the same page passed, and run 43589661503 passed every `/dashboard` scan.
- Element: the "Open latest" Button in `dashboard/page.tsx`. With no latest itinerary it is the outline variant (`border-border`), the only outline Button on the page. It is `disabled={latest.isPending}`.
- Cause: the shared Button has `disabled:opacity-50` and `transition-all`. When the latest-itinerary query settles, the button is enabled and its opacity animates 0.5 to 1. axe scanned during that fade. #8b8988 is the 50% blend of the foreground token (#1C1917) over #FAFAF9, and its ratio computes to 3.33, matching the report. It is a transient state, not a token problem.
- Fix: `className="transition-colors"` on that Button. `cn` (the `cn` package, `apps/web/lib/utils.ts`) drops `transition-all` when `transition-colors` follows (checked by running `cn("... transition-all ... disabled:opacity-50 ...", "transition-colors")`: result has `transition-colors`, no `transition-all`). Opacity now changes at once and colour changes still ease. `components/ui/button.tsx` is not edited. No rule, element or threshold was excluded; the scan and E2E files are untouched.
- Contrast after: settled label is the foreground token #1C1917 (inherited from `body`) on the background token #FAFAF9, 16.74:1 (WCAG formula, node calculation). AA needs 4.5:1.
- Test: `tests/unit/trips/dashboard.test.tsx`, TC-088 test now also asserts the enabled "Open latest" button has `transition-colors` and not `transition-all`. Checked to fail with the dashboard change reverted (`Tests  1 failed | 6 passed (7)`) and pass with it.
- Commands (from `apps/web`):
  - `npx vitest run tests/unit/trips/dashboard.test.tsx`: `Tests  7 passed (7)`
  - `npx eslint "app/(app)/dashboard/page.tsx" tests/unit/trips/dashboard.test.tsx`: no output (exit 0)
  - `npx prettier --check` on the same two files: `All matched files use Prettier code style!`
  - `npm run typecheck`: `next typegen && tsc --noEmit` finished with no errors
- Acceptance: TC-383 contrast on `/dashboard`: verified by cause analysis, the computed ratios and the unit assertion; not verified in CI (needs the lead's next E2E run). Threshold unchanged.
- Open issue (outside this part): the same transient shows on `/trips/new` (run 43590291645, chromium-1280): `color-contrast`, the TripWizard Back button, #797877 on #fcfcfc, 4.29:1 (computes to 4.29), in `apps/web/components/trips/TripWizard.tsx`. It needs the same treatment or the shared fix below.
- Proposed decision: in a follow-up that owns `components/ui/button.tsx`, replace `transition-all` with colour and shadow transitions (no opacity), so every disabled-to-enabled Button is free of the fade. That would also remove the need for the per-button class added here.

## RUN-071b button (PD-RUN-071-1, shared Button animates colours only, owner Manasvi)

Owner: Manasvi (Manasvi Rathore). Part: button-transition. Base commit: 7ea14f1 (the map-worker commit of this run; the part has no dependency on it). Files changed: `apps/web/components/ui/button.tsx`, `apps/web/tests/unit/ui/button.test.tsx` (new), plus this record. `components/ui/button.tsx` is the IMP-104 file.

- Resolves: `/trips/new`, the TripWizard "Back" button (`components/trips/TripWizard.tsx`, shared `Button`, outline variant, `disabled={step === 0 || saving}`): `color-contrast`, #797877 on #fcfcfc, 4.29:1 (computes to 4.29:1), E2E run 43590291645, chromium-1280. It is the same transient as the dashboard "Open latest" finding in RUN-071 contrast.
- General cause: the shared Button base classes had `transition-all` together with `disabled:opacity-50`. When a disabled Button is enabled, opacity animates 0.5 to 1 over the 150 ms default, and a contrast scan during the fade reads a half-transparent label (50% of #1C1917 over #FCFCFC is 3.33:1; the reported #797877 is a later frame of the same fade). Every disabled-to-enabled Button on every page had this; the per-button `transition-colors` on the dashboard fixed one instance only.
- Fix: in the base classes `transition-all` became `transition-colors` (colour, background, border, outline, fill and stroke colours; 150 ms; no opacity, no transform, no box-shadow). Sizes, variants and tokens are unchanged. Side effects, both intended: the focus ring (`ring-3`, a box-shadow) now appears at once instead of easing in, and the 1 px press (`active:translate-y-px`) snaps. Colours still ease on hover.
- WCAG: a disabled control is an "inactive user interface component", exempt from 1.4.3 (and axe skips disabled elements), so `disabled:opacity-50` stays. Enabled and settled, text colour on its background (WCAG formula, run in node from the tokens in `globals.css`): default #FFFFFF on #0F766E 5.47:1 (hover #115E59 7.58:1); outline and ghost #1C1917 on #FAFAF9 16.74:1 (hover #F5F5F4 16.03:1); secondary #134E4A on #F0FDFA 9.09:1 (hover 8.23:1); destructive #B91C1C on 10% tint over #FAFAF9 5.24:1 (over a white card 5.46:1); link #0F766E on #FAFAF9 5.24:1. All pass 4.5:1. The enabled and disabled states use the same text colours (only opacity differs), so no colour fade crosses a low-contrast frame when a Button is enabled.
- Open issue (hover only, not scanned by axe, tokens not changed here): the destructive variant hovered (`hover:bg-destructive/20`) computes to 4.40:1 over the page background #FAFAF9 (4.57:1 over a white card), an alpha blend in sRGB that approximates Tailwind's colour mix. Proposed decision PD-RUN-071b-1: lower the hover tint to `/15` or darken the label in a follow-up that owns the tokens; the rule "do not change variants or tokens" kept this part from doing it.
- Redundant class: `apps/web/app/(app)/dashboard/page.tsx` still carries `className="transition-colors"` (and its comment) on "Open latest" from RUN-071; it is now redundant and harmless (`cn` merges it), and was left because the file is outside this part. `tests/unit/trips/dashboard.test.tsx` still passes.
- Test: `tests/unit/ui/button.test.tsx`: for each of the six variants a rendered Button has `transition-colors` and none of `transition-all`, `transition-opacity`, `transition`; a disabled Button keeps `disabled:opacity-50` and the colour-only class. Checked to fail with the old class (`Tests  7 failed (7)` with `button.tsx` stashed) and pass with the fix.
- Commands (from `apps/web`):
  - `npx vitest run tests/unit/ui tests/unit/trips/dashboard.test.tsx`: `Test Files  2 passed (2)` / `Tests  14 passed (14)`
  - `npx eslint components/ui/button.tsx tests/unit/ui`: no output (exit 0)
  - `npx prettier --check components/ui/button.tsx tests/unit/ui`: `All matched files use Prettier code style!`
  - `npm run typecheck`: `✓ Types generated successfully`, tsc exit 0
- Acceptance: TC-383 contrast of Buttons that become enabled (the `/trips/new` Back button and every other Button): verified by cause analysis, the computed settled ratios and the unit tests; not verified in CI (needs the lead's next E2E run, run id to be filled in). Axe threshold, scans and rules are unchanged.
