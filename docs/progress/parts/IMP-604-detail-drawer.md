# IMP-604 · detail-drawer part (PlaceDetailDrawer with labelled facts)

- Run id: RUN-075
- Owner: Jeel (Jeel Fefar)
- Status: PR_OPEN pending integration (committed on `part/p`; the lead integrates and opens the pull request)
- Base commit: a6307c3
- Traces to: US-031; FR-018; NFR-002, NFR-040; TC-098 (UI), TC-099, TC-100
- Card steps built: 5 (drawer half)

## Changed files

- `apps/web/components/places/PlaceDetailDrawer.tsx` (created): a side drawer (the shared Dialog, placed at the right edge) that reads API-17 and shows the name, description, hours, price, verification status, address with coordinates, and source (name, linked when it has a URL, retrieval date, licence, attribution). Labels come from the existing SourceBadge: curated hours read "Curated, checked on <date>" and estimates read "Estimate". Missing hours read "Hours unavailable" with no time, and a missing price reads "Unavailable", never 0. It has loading (LoadingSkeleton) and error (ErrorState with retry) states. Nothing is computed or guessed in the browser. The booking link is not shown (PR-10 allows it only as a plain link; it can be added later).
- `apps/web/app/(app)/trips/[tripId]/explore/page.tsx`: each place has a "Details" button (`aria-label="Details of <name>"`) that opens the drawer.
- `apps/web/lib/api/queries.ts` (block `// IMP-604 detail drawer` appended): `usePlace(placeId)` (API-17, key `['place', placeId]`, §7.4). It uses the generated `PlaceOut` type and needs no regeneration.
- `apps/web/tests/unit/places/PlaceDetailDrawer.test.tsx` (created): curated hours with checked date and each day (TC-098 UI), "Hours unavailable" with no time (TC-099), "Estimate" on an estimated price and on estimated hours (TC-100), and a missing price shown as Unavailable.

## Commands run

| Command | Result line |
| --- | --- |
| `make test-web ARGS='PlaceDetailDrawer'` | `Tests  4 passed (4)` |
| `npx vitest run tests/unit/places` | `Tests  21 passed (21)` (2.9 s wall time) |
| `make lint` | ruff `All checks passed!`; ESLint `0 errors, 1 warning` (existing warning in lib/api/client.ts); `All matched files use Prettier code style!` |
| `make typecheck` | `Success: no issues found in 122 source files`; `tsc --noEmit` exit 0 |
| `make imports` | `Contracts: 6 kept, 0 broken.` |

## Not run

- `make e2e` and the detail-drawer screenshot: no Docker or dev server on this machine.

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-018 AC1 (TC-098): curated hours show "Curated, checked on <date>" | verified | drawer test 1 (API half in the search-api record) |
| FR-018 AC2 (TC-099): no hours shows "Hours unavailable" and no time | verified | drawer test 2 |
| FR-018 AC3 (TC-100): an estimated price carries "Estimate" | verified | drawer test 3 |
| A missing price shows "Unavailable", never 0 | verified | drawer test 4 |

## Blockers

None.

## Proposed decisions

None.

## Open issues

- DR-08 says hours older than a configured age show as unverified. No threshold is set, so this is not built.
