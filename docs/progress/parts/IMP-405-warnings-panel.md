# IMP-405 · warnings-panel part

- Run id: RUN-060 (grouped, IMD-121, with IMP-407 and IMP-403)
- Owner: Manasvi (Manasvi1704)
- Status: PR open
- Base commit: 84d1973
- Branch: feat/IMP-403-405-407-failures-warnings-edits
- Reviewer: Kirtan (kirtan-S111)
- Traces to: US-065; FR-056; NFR-028; IMD-118
- Card steps built: 4 (steps 1, 2, 3 and 5 are the persist-warnings part)

## Reuse of PR #264

Built fresh, not cherry-picked. The closed PR #264 (`feat/IMP-405-warnings-panel`) has four commits authored `Manasvi1704 <166296173+Manasvi1704@users.noreply.github.com>`, which is not the identity in the run prompt (202301108@dau.ac.in). They also touch the itinerary page and `ItineraryItemCard.tsx`, not only the panel and its test. Both conditions of the reuse rule fail.

## Changed files

- `apps/web/components/itinerary/WarningsPanel.tsx` (created). A section titled "Plan checks" with the counts in its header ("2 errors · 1 warning · 1 info"; zero counts are left out).
  - Groups: Error, Warning, Info, then by day. Findings with no day (MUST_VISIT_MISSING) come first as "Whole trip", then "Day 1", "Day 2" and so on.
  - Each row shows a severity badge (text, icon and colour from the semantic tokens), the message, then "Suggested fix:" with the fix.
  - A row about an item has a "Go to item" text button. MUST_VISIT_MISSING has no item: its row shows the place name (from the trip's must-visit list) and no button.
  - Empty state: "No issues found" with a check icon.
  - The counts are announced in a polite live region.
  - Below 1280 px a Show/Hide button (`aria-expanded`, `aria-controls`) collapses the list. It starts collapsed when only info rows remain. From 1280 px (`xl`) the list is always shown and the toggle is hidden.
- `apps/web/app/(app)/trips/[tripId]/itinerary/page.tsx`:
  - Layout: the panel sits above the days below 1280 px, and beside them (320 px column, sticky) from 1280 px.
  - Place names come from API-15's `must_visit_places`.
  - `goToItem` opens the item's day tab (the day tabs are now controlled, because below 768 px the item may sit in a closed tab), then scrolls the card into view and moves focus to it.
- `apps/web/components/itinerary/ItineraryItemCard.tsx` (focus target only): the card has `id="item-<id>"`, `tabIndex={-1}`, `scroll-mt-24` and the guide's focus-visible ring. `itemCardId` is exported for the page.
- `apps/web/tests/unit/itinerary/WarningsPanel.test.tsx` (created): nine cases (header counts, group order, cause, badge and fix on every row, Go to item keyboard focus and callback, the must-visit place name with no button, empty, live region, collapsed when only info rows remain, open with errors).
- `apps/web/tests/unit/itinerary/ItineraryPage.test.tsx`: one case: the page shows the plan checks, and "Go to item" moves focus to the item's card.

No browser code computes a finding, a count from data other than the findings array, a time or a price; the panel shows API-24's findings as sent.

## Commands and results

| Command | Result |
| --- | --- |
| `make test-web ARGS='WarningsPanel'` (run as `npx vitest run WarningsPanel ItineraryPage`) | `Tests  17 passed (17)` |
| `make test-web` | `Tests  161 passed (161)`. In one of 11 runs, 1 test failed; it could not be reproduced in the other 10, including runs under load. See Open issues |
| `make lint` | `All checks passed!`; ESLint `✖ 1 problem (0 errors, 1 warning)`, a warning that predates this run (`window.location.assign`, not in these files); `All matched files use Prettier code style!` |
| `make typecheck` | `Success: no issues found in 116 source files`; `tsc --noEmit` clean |
| `make test-unit` | `1006 passed, 1 warning` |
| `make imports` | `Contracts: 6 kept, 0 broken.` |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` |

Not run: screenshots at 375 px and 1280 px for the MOCK `flawed` scenario, since no local stack runs here. They are added on staging after deploy.

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| WarningsPanel shows the cause and suggested fix for each finding | verified | `shows each cause with a text badge and the suggested fix` |
| WarningsPanel is keyboard reachable | verified | `Go to item is a keyboard-reachable button …`; Show/Hide is a native button; the page test shows focus moving to the item card |
| Grouped by severity, then day; empty state; polite announcement (DESIGN) | verified | `groups by severity …`, `says No issues found …`, `announces the counts …` |
| 1280 px beside the days, 375 px collapsible above (DESIGN) | not verified visually | Tailwind classes (`xl:grid-cols-[minmax(0,1fr)_320px]`, `xl:hidden` toggle) and the collapsed-state test. Visual check on staging |

## Blockers

none

## Proposed decisions

none

## Open issues

- One unexplained failure in one of 11 `make test-web` runs. It happened in the run right after `make lint` and `make typecheck`, and the failing test's name was not captured. Ten later runs, two of them alongside a parallel `make typecheck`, passed 161/161. CI should be watched for a flaky web test.
- Finding messages of the schedule rules name items as `d1-i2` (IMP-404 wording in `rules.py`), so the panel shows those references. Rewording the messages with place names belongs to the validator, not this part.
