# IMP-609 · summary-api

- Run id: RUN-075
- Owner: Het Lathiya, 1 point
- Status: implemented; PR not opened (batch run, the lead integrates)
- Base commit: a6307c3 (on top of the IMP-610 parts)
- Steps: 1, the API half of 3 and 4; FR-094 AC1-AC2 (TC-254, TC-255).

## Files changed

- apps/api/app/itinerary/service.py: `trip_summary` (API-35): a read-only projection of the current plan: the trip, the days exactly as API-24 builds them (times, travel with its source, costs with labels, places with `hours_label`, `theme_origin`/`note_origin` for the AI-written badge), the stored findings of the current revision as `unresolved_findings`, the costs and `generated_at`. 404 NOT_FOUND for an empty plan or a foreign trip.
- apps/api/app/itinerary/router.py: API-35 replaces its 501 stub; `costs` is API-33's answer from `budget.service.get_costs`, passed into the projection (itinerary.service cannot import budget.service: that module imports itinerary.service). No calculation in the router.
- apps/api/tests/api/test_itinerary.py: TC-254, TC-255, 404 cases.
- apps/api/tests/authz/route_matrix.py (appended block `# IMP-609 summary`): API-35 row.
- apps/api/app/itinerary/schemas.py: unchanged; `TripSummaryOut` already had the §6.6.5 shape.

## Commands and results

Database: a throwaway local PostgreSQL 16.2 + pgvector on 127.0.0.1:55432 (database travel_test_i); every API command ran with PYTHONPATH=<worktree>/apps/api.

- `make test-api ARGS='-k summary -q -p no:warnings'`: `5 passed, 482 deselected in 3.89s`
- `make test-api ARGS='tests/api/test_itinerary.py -q -p no:warnings'` (runs the whole tests/api folder): `487 passed in 178.97s (0:02:58)`
- `make test-authz ARGS='-q -p no:warnings'`: `55 passed in 30.02s`
- API `ruff check .`: `All checks passed!`; `ruff format --check .`: `230 files already formatted`; `mypy app`: `Success: no issues found in 123 source files`; `lint-imports`: `Contracts: 6 kept, 0 broken.`
- `make openapi-check`: `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date`
- Not run: `make e2e` (no Docker).

## Acceptance

- FR-094 AC1 (TC-254): verified, `test_tc_254_summary_lists_every_day_with_times_places_travel_and_labels` (days equal API-24's, costs equal API-33's, every time, cost label, hours label and travel source present, themes carry their origin).
- FR-094 AC2 (TC-255): verified, `test_tc_255_summary_shows_the_unresolved_warnings_of_the_current_plan` (the current revision's warning is listed, an older revision's is not).
- Labels on every price, hour and travel time: verified at API level in TC-254; the rendering is the summary-page part.

## Blockers, proposed decisions, open issues

- PD-RUN-075-I3: card step 1 lists a closing statement and checked-on dates in the API projection, but §6.6.5 API-35 is `{trip, days, unresolved_findings, costs, generated_at}` and `ItemPlace` has no `hours_checked_on`. To avoid a contract change in this batch, the response keeps the §6.6.5 shape; the fixed statement "Prices and hours are estimates unless marked Curated" is page text in PrintLayout. If the team wants it from the API, or wants checked-on dates on the summary, add `hours_checked_on` to `ItemPlace` (and a `statement` field) through a decision and `make openapi`.
