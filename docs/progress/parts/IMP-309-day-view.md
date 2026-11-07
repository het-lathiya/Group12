# IMP-309 · day-view part

- Run id: RUN-050 (grouped, IMD-121, with the IMP-309 read-fields part and IMP-314)
- Owner: Manasvi (Manasvi1704)
- Status: PR_OPEN
- Base commit: 1681b41
- Branch: feat/IMP-309-314-itinerary-guides
- Reviewer: Kirtan (kirtan-S111)
- Traces to: US-068; FR-059; FR-035; NFR-002, NFR-025; TC-196
- Card steps built: 2 to 5, plus the two SG-2 items routed to IMP-309

## Changed files

- `apps/web/components/labels/SourceBadge.tsx`, `AiBadge.tsx` (created).
- `apps/web/components/generation/FallbackNotice.tsx` (created; §7.6 places it here, IMP-403 extends it).
- `apps/web/lib/format.ts` (created): `formatDayDate`, moved out of `DayColumn.tsx` so that `SourceBadge` can use it without an import cycle.
- `apps/web/components/itinerary/ItineraryItemCard.tsx`: time range, cost with its label, travel leg with its label, note with AiBadge.
- `apps/web/components/itinerary/DayColumn.tsx`: theme with AiBadge.
- `apps/web/app/(app)/trips/[tripId]/itinerary/page.tsx`: not-found screen, empty plan, FallbackNotice.
- `apps/web/lib/api/queries.ts`: `useTrip` (API-10), used only after API-24 answers 404.
- `apps/web/app/globals.css`: `--radius-md` 8 px, `--radius-xl` 12 px.
- `apps/web/e2e/journey.spec.ts`: no horizontal scroll at 375 and 1280 px; `UPDATE_SCREENSHOTS=1` writes the evidence.
- Tests: `tests/unit/itinerary/DayColumn.test.tsx`, `ItineraryItemCard.test.tsx`, `fixtures.ts` (IMP-213's "must not show" cases are replaced, because the card now shows those fields), `ItineraryPage.test.tsx` and `tests/unit/labels/SourceBadge.test.tsx` (created).
- `docs/progress/parts/IMP-309-day-view-screens/`: `itinerary-375.png`, `itinerary-1280.png`.

## SG-2 items routed here

- **Radius.** `rounded-xl` is now 12 px and `rounded-md` 8 px, so cards and dialogs match guide §5 and `rounded-md` is no longer larger than `rounded-lg`. The item card moved from `rounded-lg` to `rounded-xl`. Nothing in `apps/web` uses `rounded-2xl`.
- **Foreign trip.** The run prompt describes this as a plan with no items for a non-SAMPLE destination. SG-2 and the IMP-213 record describe a trip that is not the caller's. Both are covered, and the specification states both:
  - §7.5: a foreign or missing trip shows the not-found screen with a link to the dashboard. API-24 answers 404 for that and for a trip with no plan, so the page asks API-10 to tell them apart.
  - §7.5.7: a trip with nothing planned shows EmptyState "Nothing planned yet" with "Generate" and "Add a place". This now also covers a plan whose days are all empty, whatever the destination. "Add a place" is left out until API-25 is built (IMP-504).

## PR checklist

- [x] No component computes a total or a time in the browser. Checked by reading every changed component, and by the test "shows the time range as sent, not worked out from the duration", which sends an end time that does not match the duration. The only logic on values is `cost.min === cost.max`, a string comparison that chooses one amount or a range, and `formatDuration`, which writes a server value in the guide's words (IMP-213).

## Commands

The local stack as in `.github/workflows/e2e.yml`: `make stack-up`, `make db-migrate`, `make seed`, the API with `AI_PROVIDER=MOCK`, the standalone web build, with the stack's values exported into each command's environment only. `make stack-down` afterwards.

| Command | Result |
| --- | --- |
| `make test-web ARGS='DayColumn'` | `Test Files  1 passed (1)`, `Tests  7 passed (7)` |
| `make test-web ARGS='itinerary labels generat states'` | `Test Files  9 passed (9)`, `Tests  45 passed (45)` |
| `make e2e ARGS='journey'` (`BASE_URL=http://localhost:3000`) | `4 passed (8.0s)`. Run before two comment-only edits |
| `make check` | exit 0: unit `755 passed, 1 warning`; contract `87 passed, 2 deselected, 1 warning`; api `326 passed, 1 warning`; authz `31 passed`; web `Tests  105 passed (105)`. Run before two comment-only edits |

## Acceptance

| Criterion | Status | How |
| --- | --- | --- |
| FR-059 AC1, AC2, TC-196: items in time order; estimated costs carry "Estimate" | verified | `DayColumn.test.tsx`, "TC-196" |
| No component computes a total or a time in the browser | verified | PR checklist above |
| Owner-only | verified | read-fields part; not-found screen in `ItineraryPage.test.tsx` |
| Renders at 375 px and 1280 px without horizontal scroll | verified | `journey.spec.ts` assertion and the screenshots |

The bar across the middle of `itinerary-375.png` is the fixed bottom navigation, caught by the full-page capture.

## Blockers

None.

## Proposed decisions

- **PD-IMP-309-1 (no checked date in API-24).** §7.8 asks for "Curated, checked on <date>", but `ItemCost` has no date and contract v1 must not change here. `places` also holds only `hours_checked_on`, with no date for prices. `SourceBadge` takes `checkedOn` and writes the full text when given it; on the itinerary it shows "Curated". Proposed: decide whether API-24 gains a date, and which one, or whether "Curated" stands for prices.
- **PD-IMP-309-2 (label wording).** The card says "Curated, checked <date>"; §7.8 and guide §12 say "Curated, checked on <date>". §7.8 is followed. Proposed: correct the card.
- **PD-IMP-309-3 (query key).** The card says `["itinerary", tripId]`; §7.4 says `['itinerary', tripId, versionId or 'current']`, which `queryKeys` already uses. §7.4 is followed, and the card's key still works as the invalidation prefix. Proposed: correct the card.
- **PD-IMP-309-4 (Files list).** The card leaves out `FallbackNotice.tsx`, `lib/format.ts`, `globals.css` and `e2e/journey.spec.ts`. Proposed: add them.

## Open issues

- **Still to come on this page (§7.5.7):** warnings (IMP-405), cost strip (IMP-507), trip title in the header, and "Add a place" (IMP-504). `day_cost` and `totals` are in the response and are not shown yet.
- **Generate on an all-empty plan.** API-22 answers 409 when an itinerary exists (IMD-21), so the "Generate" link cannot help a plan whose days are all empty until regeneration exists (IMP-607). The planner does not save such a plan today.
- **Separator dots.** At 375 px a wrapped meta row can end in a "·".
