# IMP-507 · costs-page

- Run id: RUN-069
- Owner: Manasvi Rathore (Manasvi1704), 2 points
- Status: implemented and component verified; full live label review pending
- Base commit: 4c6c693
- Steps: 3–5; FR-073, FR-117, TC-225/226/282/300/385; IMD-130/172.

## Files changed

- apps/web/app/(app)/trips/[tripId]/costs/page.tsx: API-only summary, incomplete note, budget inputs and labelled breakdowns, loading/error/retry states.
- apps/web/components/costs/CostBreakdown.tsx: two accessible tables, exact §6.5 day/category shapes and contingency shares, server values only; unavailable category prices hidden.
- apps/web/components/labels/SourceBadge.tsx: Traveller input label for server allowance lines.
- apps/web/tests/unit/costs/CostBreakdown.test.tsx; docs/test-reports/label-review.md; this record.
- Minimal itinerary label addition: ItineraryItemCard.tsx now shows hours_label; ItineraryItemCard.test.tsx and labels/AiBadge.test.tsx explicitly require both curated price/hours badges. These tests changed because the review adds the second factual label.
- Explore already labels its values. Place-detail and summary screens/API implementations are absent (IMP-604/609), recorded as pending in label-review.md; no unrelated screens built.

## Commands and results

- `make test-web ARGS='CostBreakdown'`: `Test Files  1 passed (1)`; `Tests  2 passed (2)`.
- Initial full web run: one old assertion assumed one Curated badge; updated it to require both price and hours badges.
- `make test-web`: `Test Files  32 passed (32)`; `Tests  214 passed (214)`.
- `make typecheck`: `Success: no issues found in 122 source files`; `✓ Types generated successfully` (exit 0).
- `npm run lint --prefix apps/web`: `✖ 1 problem (0 errors, 1 warning)` (existing client navigation warning; exit 0).

## Acceptance

- Verified TC-282: table captions, row/column headers, exact money strings, source/Traveller input/unavailable labels.
- Verified TC-226 component path: an edit invalidates the shared costs query and both breakdown and planning total update without manual reload.
- TC-225/300 engine sums remain backend evidence; browser performs no sums, times or travel estimates.
- TC-385 source audit recorded for every requested screen; built screens have labels. Full live-stack review/screenshots, and future place-detail/summary screens, not verified.
- Screenshot: local stack — member to add.

## Proposed decisions / open issues

- No new decisions, contract shapes, migrations or packages.
- Place-detail (IMP-604), summary (IMP-609) and live visual review remain pending; no completion claim for absent screens.
