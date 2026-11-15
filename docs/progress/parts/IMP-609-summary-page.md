# IMP-609 · summary-page

- Run id: RUN-075
- Owner: Krrish Kamani, 2 points
- Status: implemented; PR not opened (batch run, the lead integrates)
- Base commit: a6307c3 (on top of the summary-api part)
- Steps: 2, 3 (screen half), 4 (rendered page); FR-094 AC1-AC2 (TC-254, TC-255), NFR-040.

## Files changed

- apps/web/components/versions/PrintLayout.tsx (created): renders API-35 only: trip header, one section per day (time range, place, hours SourceBadge, cost with SourceBadge or Unavailable, travel line with its source label, AI-written badge on AI themes and notes, day estimate), trip total with Estimate labels, a separate Unresolved warnings section and the closing statement "Prices and hours are estimates unless marked Curated." In print only the summary is visible (a print stylesheet scoped to `[data-print-root]`, so the shared shell is not edited) and every day after the first starts a page (`print:break-before-page`).
- apps/web/app/(app)/trips/[tripId]/summary/page.tsx (created): Print button calls `window.print()` (no server-side PDF); EmptyState with a link to generate when API-35 answers 404; loading and error states.
- apps/web/lib/api/queries.ts (appended block `// IMP-609 summary`): `useSummary` (key `['summary', tripId]`, which edits, trip updates and restores already invalidate).
- apps/web/tests/unit/versions/PrintLayout.test.tsx (created).
- No generated types were missing: `TripSummaryOut` and API-35 are in schema.d.ts.

## Commands and results

- `make test-web ARGS='tests/unit/versions'`: `Tests  9 passed (9)` (2.2 s wall time, load average 0.72)
- `make lint`: `All checks passed!`; web `✖ 1 problem (0 errors, 1 warning)` (an existing warning outside this part); `All matched files use Prettier code style!`
- `make typecheck`: `Success: no issues found in 123 source files`; `✓ Types generated successfully`
- `make imports`: `Contracts: 6 kept, 0 broken.`
- Not run: `make e2e` (no Docker on this machine).

## Acceptance

- FR-094 AC1 (TC-254) on the page: verified, `TC-254: every day lists times, places, travel and labelled costs from the API`.
- FR-094 AC2 (TC-255) on the page: verified, `TC-255: unresolved warnings appear in their own section`.
- Every price, hour and travel time carries its label; AI-written themes carry the badge: verified in the TC-254 case.
- Print preview with no navigation and one day per page section: page-break classes verified by `starts each day after the first on a new printed page`; the manual print-preview check with a screenshot is not verified (no browser run here).
- Empty itinerary shows EmptyState with a generate link; Print calls window.print(): verified by the two page cases.

## Blockers, proposed decisions, open issues

- See PD-RUN-075-I3 (summary-api record): the closing statement is page text, and checked-on dates are not in the API-35 shape, so the summary shows hours labels without dates.
- The summary tab link in the trip navigation is for the lead (shared navigation).
