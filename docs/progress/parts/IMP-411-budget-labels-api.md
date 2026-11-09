# IMP-411 · budget-labels-api

| Field | Value |
| --- | --- |
| Run | RUN-058 (grouped run, IMD-121), part 2 of 7 |
| Card | IMP-411 Transport allowance, stay budget and price source labels |
| Part | Transport allowance, stay budget, price source labels API (2 points) |
| Owner | Manal Patel |
| Status | PR_OPEN |
| Base commit | 16839a0 |
| Branch | feat/IMP-410-411-412-trips-budget-states |

## Starting point

API-34 was a 501 stub. `app/budget/repository.py` already existed with `upsert_settings` (IMP-308). Engine BF-05 and BF-06 were already built: a set allowance gives a `transport` or `accommodation` line labelled `traveller_input`, and a missing allowance gives a 0.00 line labelled `unavailable`. That label is on `CategoryCostLine` in `CostSummaryOut` (IMP-308, IMD-124 B2), so traveller input needs no fourth source label and no contract change. `SourceLabel` was defined in `app/places/vocabulary.py`, and `app/schemas/labels.py` did not exist.

## Changed files

- `apps/api/app/schemas/labels.py` (created): `SourceLabel` = exactly {curated, estimate, unavailable}, plus `SOURCE_LABELS`. This is now the only definition.
- `apps/api/app/places/vocabulary.py`: re-exports `SourceLabel` and `SOURCE_LABELS` from `app/schemas/labels.py` instead of defining them. The places module and its callers are unchanged. This file is not in the card's list, but it is needed to keep one definition.
- `apps/api/app/budget/repository.py`: adds `save_settings`, which upserts exactly the columns given, so a `null` clears an allowance. `upsert_settings` now calls it. `get_settings` reads with `populate_existing`, so a row saved earlier in the same transaction is read back as stored.
- `apps/api/app/budget/service.py`: `update_budget_settings` (API-34).
- `apps/api/app/budget/router.py`: API-34 now calls the service instead of answering 501.
- `apps/api/tests/unit/budget/test_allowances.py` (created): TC-223, TC-224, TC-232 and the patch body rules.
- `apps/api/tests/api/test_costs.py`: API-34 API tests. §6.6.6 puts TC-223 and TC-224 in this file.
- `apps/api/tests/authz/route_matrix.py`: API-34 is listed as `foreign`.
- `apps/api/tests/contract/test_openapi_contract.py`: the sample "declared route answers 501" test used API-34. It now uses API-12, which stays a stub until IMP-602.
- `docs/progress/parts/IMP-411-budget-labels-api.md`: this record.

`apps/api/app/budget/engine.py` is unchanged, because BF-05 and BF-06 already do what the card asks.

## Behaviour (API-34, §6.6.6)

- The body may contain any of `transport_allowance_per_day` and `stay_budget_per_night` (money ≥ 0, or `null` to clear) and `contingency_pct` (0 to 50).
- Only the fields sent are written. `contingency_pct: null` leaves the stored value unchanged, because that column has no "not set" state.
- A negative or out-of-range value, an unknown field, or `contingency_pct` while the `contingency` switch is off answers 422 `VALIDATION_ERROR`.
- Another user's trip answers 404 `NOT_FOUND`. An archived trip answers 409 `CONFLICT` (IMD-35).
- The response is 200 with the `CostSummaryOut` recalculated on read, including its `BUDGET_*` alerts.
- API-34 writes only `budget_settings`. It never writes `itinerary_warnings` and does not change `plan_revision`.

## IMD-130 overrides card step 3

Card step 3 says "curated carries checked_on date". IMD-130 (PD-IMP-309-1) decides that a curated price carries no date, while curated opening hours keep `hours_checked_on`. The label enum is therefore a plain value with no date. Prices in the API (`cost.label`, `CategoryCostLine.label`) have no date, and the hours date stays where it is (`hours_checked_on`).

## Commands

| Command | Result |
| --- | --- |
| `make test-unit ARGS='-k allowances or labels'` (run as `.venv/bin/pytest tests/unit -k 'allowances or labels'`) | `17 passed, 871 deselected, 1 warning in 1.98s` |
| `make test-unit` | `888 passed, 1 warning in 31.49s` |
| `make lint` | `All checks passed!` (ruff); ESLint `✖ 1 problem (0 errors, 1 warning)`, a warning that predates this run |
| `make typecheck` | `Success: no issues found in 111 source files` |
| `make imports` | `Contracts: 6 kept, 0 broken.` |
| `make test-web` | `Tests  119 passed (119)` |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` (API-34 was already declared with its final shape, so nothing was regenerated) |
| `.venv/bin/pytest tests/authz/test_route_inventory.py` | `7 passed, 1 error`: the error is the one case that needs PostgreSQL |
| `make test-contract` | `87 passed, 2 deselected, 1 warning in 5.94s` |

Not run: `make test-api ARGS='-k budget'` and `make test-authz`. This machine has no Docker and no PostgreSQL, so they rely on the CI `api` job.

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-072 AC1 (TC-223): saved inputs appear in the breakdown labelled traveller input | verified (unit); API not verified locally | `test_tc_223_allowances_enter_the_breakdown_as_traveller_input` passed; `test_tc_223_budget_settings_appear_as_traveller_input` runs in the CI `api` job |
| FR-072 AC2 (TC-224): with no input the lines are unavailable and the total says so | verified (unit); API not verified locally | `test_tc_224_*` unit tests passed; `test_tc_224_budget_settings_cleared_show_unavailable` runs in CI. The line label `unavailable` is how the response says so; `complete` keeps its item meaning |
| FR-076 AC2 (TC-232): no live or verified label can be produced | verified | `test_tc_232_labels_*` and `test_tc_232_cost_lines_cannot_be_labelled_live_or_verified` passed |
| Another user's PATCH returns 404 | not verified locally | `test_budget_settings_of_another_users_trip_are_not_found` and the API-34 row in `route_matrix.py`; CI `api` job |
| API-34 writes no itinerary_warnings | not verified locally | `test_budget_settings_write_no_warnings_and_keep_the_plan_revision`; CI `api` job |

## Proposed decisions

- **PD-IMP-411-1 (contingency_pct null):** `BudgetSettingsPatch` allows `contingency_pct: null`, but the column is NOT NULL with a default. `null` is treated as "leave unchanged". Proposed: §6 states this, or IMP-608 changes the field to a non-null integer.
- **PD-IMP-411-2 (archived trip):** API-34 answers 409 `CONFLICT` on an archived trip, following IMD-35 ("edit routes return 409"). §6.6.6 does not list it. Proposed: add the 409 to the API-34 row.
- **PD-IMP-411-3 (files):** `places/vocabulary.py` (re-export) and `tests/api/test_costs.py` (the §6.6.6 test file for TC-223 and TC-224) were changed but are not in the card's Files list. Proposed: add them.

## Blockers and open issues

None.
