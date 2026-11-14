# IMP-506 · lock-toggle

- Run id: RUN-069
- Owner: Krrish Kamani (Assassin-byte), 1 point
- Status: implemented and component verified
- Base commit: 4c6c693
- Steps: 5 and UI half of 6; FR-066, TC-211/212/313/372.

## Files changed

- apps/web/components/itinerary/ItineraryItemCard.tsx: native lock button with aria-pressed, visible lock icon and Locked text; read-only locked indicator; hidden with locks disabled. Shared mutation state prevents concurrent edits; server errors remain visible.
- apps/web/lib/api/queries.ts: API-26 hook in // IMP-506 block sends is_locked and plan_revision using shared cache refresh/stale handling.
- apps/web/tests/unit/itinerary/LockToggle.test.tsx; this record.

## Commands and results

- `make test-web ARGS='LockToggle'`: `Test Files  1 passed (1)`; `Tests  2 passed (2)`.
- `make typecheck`: `Success: no issues found in 122 source files`; `✓ Types generated successfully` (exit 0).

## Acceptance

- Verified keyboard Space locks and Enter unlocks; aria-pressed and visible text follow server responses; requests carry revisions 7 then 8.
- Verified locks disabled hides both control and indicator.
- Backend lock/repair evidence is lock-api; live floor/E2E remains CI evidence.
- Screenshot: local stack — member to add.

## Proposed decisions / open issues

- No new decisions, migrations, contract shapes or dependencies.
- Live-stack screenshot/E2E unverified here.
