# IMP-504 · place-picker

- Run id: RUN-069
- Owner: Malhar Mer (Malhar1112-v), 2 points
- Status: implemented and component verified; screenshots/E2E awaiting local stack and CI
- Base commit: 4c6c693
- Steps: 5–7; FR-062, FR-069; IMD-157, IMD-170.

## Files changed

- apps/web/components/itinerary/PlacePicker.tsx: accessible dialog, destination search through API-16, trip-day selection, add through API-25 and Undo through API-27 with the returned revision.
- apps/web/app/(app)/trips/[tripId]/itinerary/page.tsx: mounts picker for saved plans, including empty saved days, and loads trip metadata for all day choices.
- apps/web/lib/api/client.ts: exact shared stale-plan wording.
- apps/web/lib/api/queries.ts: EDIT_UNDO_ENABLED = true; server-response merge includes newly created day rows; shared edits refresh costs/summary/versions; stale requests refetch and show Reload.
- apps/web/tests/unit/itinerary/PlacePicker.test.tsx; this record.
- Minimal extra test file: ItemEditor.test.tsx now requires Undo to be present in both removal cases, matching IMD-157 activation. No test weakened.

## Commands and results

- `make test-web ARGS='PlacePicker'`: `Test Files  1 passed (1)`; `Tests  2 passed (2)`.
- `make test-web ARGS='itinerary'`: `Test Files  8 passed (8)`; `Tests  64 passed (64)`.
- `make typecheck`: `Success: no issues found in 122 source files`; `✓ Types generated successfully` (exit 0).
- Initial Undo test exposed jsdom's missing pointer capture; use a direct click event for the toast action, leaving all API/cache assertions intact.

## Acceptance

- Verified FR-062: search/add body carries the revision and chosen day; server totals render unchanged, new day rows enter the cache; Undo deletes the returned item with the returned revision.
- Verified FR-069: stale edit preserves the cached revision, invalidates API-24 and shows exactly “This plan changed since you opened it” with Reload.
- Verified removal undo now visible through existing component integration cases.
- No client times, travel or prices are calculated. UI only enumerates day choices and formats server data.
- TC-217 database conflict evidence remains Batch A/API CI; screenshot: local stack — member to add.

## Proposed decisions / open issues

- No new decisions, packages, migrations or contract shapes.
- Live-stack screenshots and E2E remain unverified here.
