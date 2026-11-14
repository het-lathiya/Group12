# IMP-509 · whole-task part

- Run id: RUN-068
- Owner: Jeel (Jeel Fefar)
- Status: PR_OPEN pending integration (committed on `part/IMP-509-whole-task`; the lead integrates, regenerates OpenAPI and opens the pull request)
- Base commit: 26bac9d
- Traces to: US-029; FR-016; NFR-002, NFR-040; TC-092, TC-093, TC-094
- Card steps built: 1 to 5

## Changed files

- `apps/api/app/places/schemas.py` (modified): `PlaceSummary` gains `source_name: str | None = None` and `from_row(row, source_name=None)`. Additive: every other use of `PlaceSummary` (API-17 detail, API-21, alternatives, the shortlist) is unchanged and sends `null`; API-16 always sets it.
- `apps/api/app/places/repository.py` (modified): `search_places` joins `data_sources` and returns `(place, source name)` pairs; filters, ordering (name, then id) and paging are unchanged. Places the quality gate rejected are never loaded or are deactivated (§5.6), so the existing `is_active` filter keeps them out.
- `apps/api/app/places/service.py` (modified, not in the card's file list): three lines pass the source name into `PlaceSummary.from_row`. The router only calls the service, so the field cannot reach API-16 without this. The 404 for an inactive or unknown destination (IMD-127) is unchanged.
- `apps/api/app/places/router.py` (modified): docstring only. The limit (1 to 50, default 20), offset and 401 behaviour were already built in IMP-205.
- `apps/api/tests/api/test_places.py` (modified): `PLACE_FIELDS` now includes `source_name`. Five new `places_list` tests: TC-092 (three pages cover all 30 places once, ordered by name then id, empty page past the end), TC-093 (every item has its source name and a vocabulary verification status), TC-094 (Sampleton labels are estimate or unavailable, never curated), limit=51 answers 422 VALIDATION_ERROR and a missing token answers 401 UNAUTHENTICATED, and a test that results stay within one destination and inactive places are hidden.
- `apps/web/lib/api/queries.ts` (modified, appended block `// IMP-509`): `EXPLORE_PAGE_SIZE = 20` and `usePlacesPage(destinationId, offset)` (API-16, key `['places', destinationId, {limit, offset}]`).
- `apps/web/components/places/PlaceCard.tsx` (created): name, category and duration, tags, then the price (SourceBadge; an unavailable price is never shown as a value), hours (SourceBadge `kind="hours"`), verification status in words, and source name. SourceBadge is used without changes. `Place` is `PlaceSummary & { source_name?: string | null }`, so it compiles before and after the types are regenerated.
- `apps/web/app/(app)/trips/[tripId]/explore/page.tsx` (created): the trip (API-10) gives the destination; places come from API-16 20 at a time, shown as a PlaceCard grid with Previous and Next buttons and "Page N of M · T places". It has LoadingSkeleton (cards), EmptyState, ErrorState with retry, and a trip-not-found screen. A notice "Sample data; prices and hours are estimates unless marked Curated." shows when `destination.is_sample`. Otherwise "Prices and hours are estimates unless marked Curated." shows when a listed place has an estimate label or the status `estimated`.
- `apps/web/tests/unit/places/PlaceCard.test.tsx` (created): 10 cases, 3 for PlaceCard (source and verification, SourceBadge labels, unavailable price) and 7 for ExplorePage (sample banner, estimates notice, no notice, paging with destination_id and offset, empty, error with retry, not found).
- `docs/progress/parts/IMP-509-whole-task.md` (this record).

## Commands run

Run from the worktree, with Python tools run from `apps/api` with `PYTHONPATH=.`.

| Command | Result line |
| --- | --- |
| `.venv/bin/ruff check app tests` | `All checks passed!` |
| `.venv/bin/ruff format --check app tests` | `205 files already formatted` |
| `.venv/bin/mypy app` | `Success: no issues found in 118 source files` |
| `.venv/bin/lint-imports` | `Contracts: 6 kept, 0 broken.` |
| `.venv/bin/pytest tests/unit/places tests/unit/generation tests/unit/evaluation -q` | `266 passed in 2.25s` |
| `.venv/bin/pytest tests/api/test_places.py --collect-only -q -k places_list` | `5/23 tests collected (18 deselected) in 0.06s` |
| `.venv/bin/pytest tests/contract -q -k openapi` | `1 failed, 6 passed, 82 deselected, 1 warning in 1.55s` (`test_committed_contract_is_current`: expected until `make openapi` is run at integration) |
| `npx vitest run tests/unit/places` | `Tests  10 passed (10)` |
| `npx eslint <the four web files>` | exit 0, no output |
| `npx prettier --check <the four web files>` | `All matched files use Prettier code style!` |
| `npm run typecheck` | `✓ Types generated successfully`, `tsc --noEmit` exit 0 (passes without regeneration) |

## Not run

- `make test-api ARGS='-k places_list'` and the rest of `tests/api/test_places.py`: these need PostgreSQL, which this run does not have, so they are left for integration.
- `make openapi` and `make openapi-check`: the lead regenerates `contracts/openapi.v1.json` and `apps/web/lib/api/schema.d.ts` after integration.
- `make e2e`, `make check`, the explore-page screenshot (completion evidence): no dev server or stack in this run.

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-016 AC1 (TC-092): places listed in pages | verified (web); not verified (API, deferred) | `ExplorePage` paging test; API test `test_tc_092_places_list_…` written, not run |
| FR-016 AC2 (TC-093): source and verification status shown | verified (web); not verified (API, deferred) | PlaceCard tests; `test_tc_093_places_list_…` written, not run |
| FR-016 AC3 (TC-094): page states data is sample and estimated | verified (web) | ExplorePage sample-banner test; `test_tc_094_places_list_…` written, not run |
| limit=51 answers 422 VALIDATION_ERROR; places of another destination never appear | not verified (deferred) | `test_places_list_rejects_limit_51_and_needs_a_token`, `test_places_list_keeps_to_one_destination_and_hides_inactive_rows` |
| A request without a token answers 401 UNAUTHENTICATED | not verified (deferred) | `test_places_list_rejects_limit_51_and_needs_a_token` |

## Proposed decisions

- PD-IMP-509-1: §6.5 PlaceSummary gains an optional `source_name` (string or null), always set by API-16 and null elsewhere until a card fills it. The card asks for the source name in the summary, but the §6.5 table lists `source` only on the detail.
- PD-IMP-509-2: `apps/api/app/places/service.py` is added to the IMP-509 file list (three lines), because the router reaches the repository only through the service.

## Open issues

- The OpenAPI contract and the web types must be regenerated (`make openapi`) at integration. Until then `test_committed_contract_is_current` fails.
- §7.5.5 names a `SampleBanner` in `labels/` (MOD-F07). It is not on this card's file list, so the notice is written inline in the explore page and can move into `SampleBanner` when that component is built.
