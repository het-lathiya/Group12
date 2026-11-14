# IMP-510 · edit-page

- Run id: RUN-069
- Owner: Krrish Kamani (Assassin-byte), 1 point
- Status: implemented and component verified
- Base commit: 4c6c693
- Steps: 4–5; FR-011, TC-080/081; IMD-175.

## Files changed

- apps/web/app/(app)/trips/[tripId]/edit/page.tsx: reuses TripWizard in explicit edit mode, prefilling API-10 details and API-15 preferences.
- apps/web/components/itinerary/StalePlanBanner.tsx: renders only server plan_stale, with Regenerate linking to the generate page; respects the regeneration switch.
- apps/web/app/(app)/trips/[tripId]/itinerary/page.tsx: banner mount only for this part.
- apps/web/tests/unit/itinerary/StalePlanBanner.test.tsx; this record.
- Necessary minimal extra scope: TripWizard.tsx previously only created trips and locked existing details, so it gains editId, starts at Details, unlocks that form, and calls API-11. queries.ts adds useUpdateTrip in // IMP-510 block with the specified trip/itinerary/cost/summary invalidation; TripWizard.test.tsx verifies prefill/PATCH and no client stale flag. Without these changes reusing the existing wizard would silently skip saving edits.

## Commands and results

- `make test-web ARGS='StalePlanBanner TripWizard'`: `Test Files  2 passed (2)`; `Tests  17 passed (17)`.
- `make lint`: `All checks passed!`; `227 files already formatted`; `All matched files use Prettier code style!` (one existing navigation warning; exit 0).
- `make typecheck`: `Success: no issues found in 122 source files`; `✓ Types generated successfully` (exit 0).

## Acceptance

- Verified edit mode preloads the trip, enables the fields, PATCHes the same trip, then opens saved preferences; request has no plan_stale.
- Verified fresh plan hides banner; stale plan announces status and Regenerate links to /trips/<id>/generate.
- API-31 is IMP-607 and remains unimplemented; this part makes no call to it.
- Backend title-only/dates/ownership/cleared-on-generation evidence is Batch A and API CI; database unavailable locally.
- Screenshot: local stack — member to add.

## Proposed decisions / open issues

- No new decisions, migrations, dependencies or contract shapes.
- Live-stack screenshot/E2E not verified here; full regeneration behavior remains IMP-607.
