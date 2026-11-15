# IMP-604 · filter-bar part (PlaceFilterBar)

- Run id: RUN-075
- Owner: Manasvi (Manasvi Rathore)
- Status: PR_OPEN pending integration (committed on `part/p`; the lead integrates and opens the pull request)
- Base commit: a6307c3
- Traces to: US-030; FR-017; NFR-002, NFR-040; TC-096 (UI half)
- Card steps built: 5 (filter bar half), 3 (UI half: which filters to relax)

## Changed files

- `apps/web/components/places/PlaceFilterBar.tsx` (created): a `role="search"` form with search text (name or tag), maximum price in the destination currency (checked as a money amount before it is sent), maximum duration (select), Category chips and Interest chips (`ChipMultiSelect`, aria-pressed; the interest chips sit in a native `<details>`), and a step-free checkbox. Apply (or Enter) sends the filters and Clear removes them all. Every control is a native input, select or button, so the bar works by keyboard. Helpers: `filtersFromParams` (drops values the API would refuse), `filtersToParams`, `filtersToQuery` and `activeFilterNames`.
- `apps/web/app/(app)/trips/[tripId]/explore/page.tsx`: the applied filters are read from the URL query string (`useSearchParams`) and written with `router.replace`, so a reload keeps them. Applying filters goes back to the first page. With no match and active filters, the EmptyState reads "No places match these filters", then "Try relaxing these filters: …", with a Clear filters action.
- `apps/web/lib/api/queries.ts` (block `// IMP-604 filter bar` appended): `PlaceSearchQuery` and `useFilteredPlacesPage` (API-16, key `['places', destinationId, {filters, limit, offset}]`). The new query parameters are not in the generated types yet, so the query object is cast to the generated operation's query type (commented; the cast goes once `make openapi` has run).
- `apps/web/tests/unit/places/PlaceFilterBar.test.tsx` (created): URL round trip and clean-up of bad values, apply and clear, aria-pressed chips, a malformed price refused, and an explore page that sends the URL filters to API-16 and names the filters to relax (TC-096 UI half).
- `apps/web/tests/unit/places/PlaceCard.test.tsx`: the `next/navigation` mock also gives `useRouter` and `useSearchParams` (the page now calls them).

## Commands run

| Command | Result line |
| --- | --- |
| `npx vitest run tests/unit/places` | `Tests  17 passed (17)` (2.9 s wall time) |
| `make lint` | ruff `All checks passed!`; ESLint `0 errors, 1 warning` (existing warning in lib/api/client.ts); `All matched files use Prettier code style!` |
| `make typecheck` | `Success: no issues found in 122 source files`; `tsc --noEmit` exit 0 |

## Not run

- `make e2e` and the screenshot of filters with an empty result: no Docker or dev server on this machine.

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-017 AC2 (TC-096), UI half: the page explains which filters to relax | verified | `ExplorePage filters` test |
| Filter state survives a page reload (URL) | verified (component level) | the page reads its filters from `useSearchParams` and API-16 receives them (test); `filtersFromParams`/`filtersToParams` round trip |
| Keyboard operable | verified (by construction and test) | native controls and aria-pressed chips; submitting the form with Enter applies the filters (test) |

## Blockers

None.

## Proposed decisions

- None beyond PD-RUN-075-P1 (parameter names, in the search-api record).

## Open issues

- The bar has no "near a point" control. Distance ordering (FR-017 AC3) is in the API, but choosing a reference point (for example a map click or "near my hotel") needs a design decision.
- The trip tabs need an "Explore" link to `/trips/[tripId]/explore`. That is shared navigation, so it is left to the lead.
