# IMP-604 · search-api part (Search and filter queries, place detail API, indexes)

- Run id: RUN-075
- Owner: Malhar (Malhar Mer)
- Status: PR_OPEN pending integration (committed on `part/p`; the lead integrates, regenerates OpenAPI and opens the pull request)
- Base commit: a6307c3
- Traces to: US-030, US-031; FR-017, FR-018; NFR-002, NFR-040; TC-095, TC-096, TC-097, TC-098
- Card steps built: 1, 2 (no index needed), 3 (API half), 4, 6 (already in place)

## Changed files

- `apps/api/app/places/router.py`: API-16 gains `interest` (repeatable tag), `price_max` (money, two decimals, in the destination currency), `duration_max_min` (15 to 480), `step_free` (true keeps confirmed step-free places; false is no filter), `near_lat`/`near_lon` and `max_distance_m` (1 to 100000). A query parameter outside the declared list answers 422 VALIDATION_ERROR naming it (`known_search_params`). API-17 is built (it was a 501 stub). The rate limit dependency (`expensive_request`, IMP-511) was already on API-16 (step 6).
- `apps/api/app/places/service.py` (not in the card's file list; the router reaches the repository only through it, as in IMP-509): filter validation (`near_lat` and `near_lon` together, `max_distance_m` needs both, else 422) and `get_place` (inactive or unknown place, or inactive destination, is 404).
- `apps/api/app/places/repository.py`: `PlaceFilters` and the filtered `search_places`. `q` matches the name or a tag, case-insensitively. A price filter keeps only priced places whose lowest price, in the destination's currency, is at most `price_max`; an unknown price never matches. Unknown step-free (NULL) is not step-free. Distance is the haversine formula in SQL (same radius as `routing/estimate.py`), and results are ordered by distance, then id, when a point is given. `active_place_detail` reads the place, its source and its hours.
- `apps/api/app/places/schemas.py`: `PlaceSummary.distance_m` (int or null, set only with a point; §6.5 lists it) and `PlaceOut.from_rows`. Hours are listed only when `hours_label` is not `unavailable` (FR-018 AC2); times are `HH:MM` destination local time as stored.
- `apps/api/tests/api/test_places.py`: `PLACE_FIELDS` gains `distance_m`. New tests: TC-095 (category plus price band), interest tag, duration and step-free filters, `q` on a tag, TC-096 (empty page, total 0), TC-097 (distance order, `max_distance_m`), 9 cases of unknown or bad parameters answering 422, TC-098 (curated hours with checked date, source, suitability), no guessed hours or price, and 404 for inactive, hidden-destination and unknown places.
- No migration: the filters run within one destination through `ix_places_dest_cat`, and the interest filter (`&&`) uses the GIN index `ix_places_tags` (step 2: an index only if needed).

## Commands run

Database: a throwaway local PostgreSQL 16 with pgvector (`travel_test_p` on 127.0.0.1:55432). `PYTHONPATH=apps/api` was set because the shared virtual environment's editable install otherwise imports `app` from the main checkout.

| Command | Result line |
| --- | --- |
| `make test-api ARGS='-k "filter or place_detail"'` | `23 passed, 460 deselected, 1 warning in 8.48s` |
| `.venv/bin/pytest tests/api/test_places.py -q` | `40 passed in 10.53s` |
| `.venv/bin/pytest tests/contract -q` | `1 failed, 90 passed, 2 skipped, 1 warning in 20.27s` (`test_committed_contract_is_current`: expected until `make openapi` at integration) |
| `.venv/bin/pytest tests/authz -q -k tc_065` | `2 passed, 45 deselected in 0.31s` |
| `make lint` | `All checks passed!` (ruff); ESLint `0 errors, 1 warning` (existing warning in lib/api/client.ts) |
| `make typecheck` | `Success: no issues found in 122 source files` |
| `make imports` | `Contracts: 6 kept, 0 broken.` |

## Not run

- `make openapi`: the lead regenerates the contract and web types once.
- `make e2e`: no Docker on this machine.

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-017 AC1 (TC-095): category and price band return only matching places | verified | `test_tc_095_filter_by_category_and_price_band_returns_only_matching_places` |
| FR-017 AC2 (TC-096), API half: no match is an empty page with total 0 | verified | `test_tc_096_filter_without_a_match_is_an_empty_page_with_total_0` (the UI hint is the filter-bar part) |
| FR-017 AC3 (TC-097): ordered by distance from a point | verified | `test_tc_097_filter_near_a_point_orders_by_distance` |
| FR-018 AC1 (TC-098), API half: curated hours with checked date, source with retrieval date | verified | `test_tc_098_place_detail_has_curated_hours_with_checked_date_and_its_source` |
| Missing hours are an empty list with `hours_label` unavailable; missing price is null with label unavailable, never 0 | verified | `test_place_detail_never_fills_missing_hours_or_prices` |
| Unknown params answer 422 | verified | `test_filter_rejects_unknown_or_bad_params_with_422` |
| Inactive place answers 404 | verified | `test_place_detail_of_an_inactive_or_unknown_place_is_404` |
| Rate limit on API-16 (step 6) | verified (already in place) | `Depends(expensive_request)` on the route since IMP-511; covered by that card's tests |

## Blockers

None.

## Proposed decisions

- PD-RUN-075-P1: The card's API-16 parameter names differ from §6.6.3. Built as the card says: `interest` (§6.6.3: `tag`), `duration_max_min` (§6.6.3: `max_duration_min`) and `max_distance_m` (not in §6.6.3). The §6.6.3 `child_friendly`, `indoor` and `trip_id` filters on API-16 are not in the card and are not built. The team chooses one set and the register follows it.
- PD-RUN-075-P2: The card says "unknown params -> 422"; §6.6.3 does not. Built: an undeclared query parameter answers 422 VALIDATION_ERROR with the parameter name as the detail field.
- PD-RUN-075-P3: Add `apps/api/app/places/service.py` to the IMP-604 file list.

## Open issues

- `contracts/openapi.v1.json` and `apps/web/lib/api/schema.d.ts` must be regenerated (`make openapi`).
- API-17's `trip_id` (`saved`, `must_visit`) is filled by the IMP-605 part in the same branch.
