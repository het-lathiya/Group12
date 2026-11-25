# IMP-729 · live-attribution-coverage part (attribution on every screen showing live places)

- Card: IMP-729 (0 points, Amendment A2 §12); follow-up of the any-city readiness audit
- Part: PD-733-G6, read as A2 §10 ("every screen showing them carries the §9.3 attribution"), as the run prompt decides
- Run id: RUN-096 (batch H, Sprint 7 close)
- Owner: Krrish (Krrish Kamani)
- Status: PR_OPEN candidate on `fix/RUN-096-batch-h`
- Base commit: 5fa8e6d (on `main`)
- Traces to: A2 §9.2, §9.3, §10; IMD-220 (c); TC-484

## Screens checked

Found by searching the web code for every component that renders a place name.

| Screen | Shows live places | Attribution |
| --- | --- | --- |
| Explore, itinerary (with its dialogs and map), costs | yes | already there (IMP-729) |
| Summary (`/trips/[tripId]/summary`, printable) | yes | **added**, inside the printed part |
| Trip form, Must-visit places and Review steps (`/trips/new`, `/trips/[tripId]/edit`) | yes | **added**, from the third step on |
| Trip form, Details step | the city name only | search line "Search by Nominatim · © OpenStreetMap contributors" as before |
| Dashboard, versions, generate, profile, landing | no place data (the dashboard shows the trip's city name only) | none |

## Changed files

- `apps/web/app/(app)/trips/[tripId]/summary/page.tsx`, `apps/web/components/versions/PrintLayout.tsx` (a `footer` inside the printed part)
- `apps/web/components/trips/TripWizard.tsx`
- `apps/web/tests/unit/labels/LiveAttribution.screens.test.tsx` (created)
- `docs/progress/parts/IMP-729-live-attribution-coverage.md` (this record)

The texts come from API-79 through the existing `LiveAttribution`; no text was written or changed. With the switch OFF there is no API-79 request.

## Commands

| Command | Result line |
| --- | --- |
| `npx vitest run tests/unit/labels tests/unit/versions tests/unit/trips` | `Test Files  14 passed (14)`, `Tests  130 passed (130)` |
| `make e2e ARGS="--grep @live --project=chromium-360 --project=chromium-1280"` (local stack, throwaway database, MOCK, fake live data) | `4 passed (12.2s)` |
| temporary Playwright spec over the three new screens, removed afterwards | `2 passed (8.3s)`; every axe scan `[]`; no horizontal overflow at 360 and 1280 px |

`npm run build` for that local E2E compiled and wrote the output that was served (its BUILD_ID is of this run), then exited 1 with a Next.js security upgrade notice (next 16.4.3). No dependency was changed. The CI web build decides.

The run checks on the branch head are in the SYNC REPORT of RUN-096.

## Acceptance

- **Every screen showing live places carries the §9.3 attribution: verified** by the search above, the component tests and the local browser run.
- **Curated and SAMPLE screens, and the switch OFF, unchanged: verified** (component tests for both screens).
- **Axe and keyboard: verified** (component tests; axe also in the browser).
- **Screenshots at 360 and 1280 px:** taken locally for the summary, places and review screens. They are not committed, and the command line cannot attach images to the pull request, so they are handed to the operator.

## Proposed decisions

none

## Open issues

- A printed summary shows the attribution text but not the link addresses. The OSM guidance on writing the URL out is not verified (`IMP-723-throttle-isolation.md`).
- The summary still says "Unavailable" where the other live pages say "Price unknown" and "Hours unknown", and has no tier badge. A2 §9.2 lists explore, itinerary and costs for those, so they were left.

## Blockers

none
