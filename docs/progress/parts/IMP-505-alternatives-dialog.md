# IMP-505 · alternatives-dialog

- Run id: RUN-069
- Owner: Krrish Kamani (Assassin-byte), 2 points
- Status: implemented and component verified
- Base commit: 4c6c693
- Steps: 4 and UI half of 5; FR-065, TC-208/209/210/372.

## Files changed

- apps/web/components/itinerary/AlternativesDialog.tsx: labelled dialog with ranked place/price labels, server cost/time deltas and Apply; exact empty text “No alternative fits this slot”. Locked items and a disabled alternatives switch hide Replace.
- apps/web/components/itinerary/ItineraryItemCard.tsx: Replace action on editable unlocked items.
- apps/web/lib/api/queries.ts: API-28/29 hooks in // IMP-505 block, using shared server cache merge/stale handling.
- apps/web/tests/unit/itinerary/AlternativesDialog.test.tsx; this record.

## Commands and results

- `make test-web ARGS='AlternativesDialog'`: `Test Files  1 passed (1)`; `Tests  3 passed (3)`.
- `make typecheck`: `Success: no issues found in 122 source files`; `✓ Types generated successfully` (exit 0).

## Acceptance

- Verified displayed ranking/deltas/SourceBadge, Apply body with plan_revision, server totals replacing cache, exact empty state, disabled flag hiding action.
- API ranking/locked/stale cases are Batch A plus shared mutation behavior; database verification awaits CI.
- Screenshot: local stack — member to add. No client arithmetic or provider calls.

## Proposed decisions / open issues

- No new decisions, migrations, dependencies or contract shapes.
- Live-stack screenshot/E2E not verified here.
