# IMP-602 · dashboard

- Run id: RUN-075
- Owner: Manasvi Rathore, 2 points
- Status: implemented; component tests pass locally
- Base commit: a6307c3
- Steps: the dashboard half of step 6; FR-012 AC1–AC3 (TC-082 to TC-084, web side), FR-015 actions through TripActionsMenu (trip-actions-api part).

## Files changed

- apps/web/app/(app)/dashboard/page.tsx: the drafts-only list is replaced by "All trips", with one TripCard per trip from API-08. A "Show archived" checkbox sends `include_archived=true` (FR-012 AC3). With no trips, the EmptyState offers "Create your first trip". New trip, Open latest (FR-014) and the no-drafts line are unchanged.
- apps/web/components/trips/TripCard.tsx (new): title, destination, dates, a status badge (Draft, Ready, Archived) and TripActionsMenu. The next step depends on the trip: Open itinerary when it has a plan, Continue draft for a draft, Generate plan for a ready trip without a plan. An archived trip without a plan has no next step until it is restored.
- apps/web/lib/api/queries.ts: one appended block, `// IMP-602 dashboard`, with `useTripList(includeArchived)`. It keeps the previous list on screen while the filter changes.
- apps/web/tests/unit/trips/dashboard.test.tsx: one appended describe block with TC-082, TC-083 and TC-084. The existing TC-086, TC-087, TC-088 and §7.5.3 cases are unchanged and still pass.
- This record.
- Delete and archive confirmation reuse the existing ConfirmDialog, through TripActionsMenu; the EmptyState is the existing component.

## Commands and results

- `make test-web ARGS='tests/unit/trips'`: `Tests  33 passed (33)`, `Duration  6.01s`
- `make lint`: `All checks passed!`, `All matched files use Prettier code style!`. The one existing ESLint warning (AppShell navigation) is not from this part.
- `make typecheck`: `Success: no issues found in 122 source files`; tsc exit 0

## Not run

- `make e2e`: Docker is not available on this machine. TC-372 (dashboard lists and creates with `trip_management` off) is covered at component level only: the menu renders nothing when the switch is off (TripActionsMenu test).

## Acceptance

- FR-012 AC1 (TC-082): verified by a component test. The card shows the title, the destination, the dates, the Ready status, the Open itinerary link and the actions menu.
- FR-012 AC2 (TC-083): verified. With no trips, the page links "Create your first trip" to /trips/new.
- FR-012 AC3 (TC-084): verified. An archived trip is hidden by default; Show archived requests `include_archived=true` and shows it with the Archived badge.
- Screenshot of the dashboard: not taken (no local stack). The member adds it.

## Proposed decisions / open issues

- None. No new dependencies or contract shapes.
