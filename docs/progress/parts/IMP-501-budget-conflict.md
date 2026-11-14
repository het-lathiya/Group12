# IMP-501 · budget-conflict

- Run id: RUN-069
- Owner: Manal Patel (manalPatel2557), 2 points
- Status: implemented; database integration awaiting CI
- Base commit: 4c6c693
- Steps: 4–5, budget half of 6–7; FR-054, TC-184/185/304.

## Files changed

- apps/api/app/validation/rules.py: BF-11 findings from the pure engine, COST_INCOMPLETE at trip level and ESTIMATE_USED per estimated item.
- apps/api/tests/unit/validation/test_day_length_budget.py: 89/90/100/101 percent, absent/zero budget, incomplete and estimate labels, repair never drops items for budget findings (even with error severity).
- Minimal integration files outside the listed scope: itinerary/service.py shares CostInputs between existing totals and validation; generation/pipeline.py loads that same input frame; tests/fixtures/pipeline.py provides the database-free input stub; test_rules_references.py expands the exact registration assertion.
- app/budget/engine.py already defines BUDGET_NEAR_PCT = 90 and BF-11; reused unchanged. validator.py already dispatches the shared rules tuple.

## Commands and results

- `make test-unit ARGS='-k "day_length or budget"'`: `98 passed, 1036 deselected, 1 warning in 1.50s`.
- `make test-unit ARGS='-k "pipeline or findings or references"'`: `25 passed, 1109 deselected, 1 warning in 1.37s`.
- `make typecheck`: `Success: no issues found in 121 source files`; `✓ Types generated successfully` (exit 0).
- `ruff check` after import ordering: no remaining errors.

## Acceptance

- Verified FR-054/TC-184/185/304: no finding at 89%, near at 90% and 100%, exceeded at 101%; excess is a two-decimal money string and currency; absent/zero budgets emit no budget finding.
- Verified COST_INCOMPLETE trip warning and ESTIMATE_USED item info; no totals arithmetic outside the pure engine.
- Verified repair input with all budget codes leaves every item intact.
- Generation/edit/API-32 use the shared rule; DB-backed evidence not verified because PostgreSQL is unavailable.

## Proposed decisions / open issues

- No new decisions, external contract changes or migrations.
- IMD-124 B6 still applies: there is no category estimate dataset. ESTIMATE_USED is covered for estimated input and does not invent estimate data.
- API integration awaits CI.

## Integration fix (RUN-069, I-6)

- CI run 43570568677: `5 failed, 459 passed, 1 warning in 259.54s (0:04:19)`. The API fixture revealed that known SAMPLE prices labelled estimate were being mistaken for BF-04 category substitutions. This incorrectly added COST_INCOMPLETE/ESTIMATE_USED despite every numeric price being present.
- Fixed only rules.py, this part's day_length_budget test and this record: category substitutions require explicit internal category_estimate_refs; IMD-124 B6 still supplies none in production because no category-estimate data exists. Known estimated prices keep their Estimate label and do not become missing costs. No column or API field is needed.
- Added a regression for a known estimated price and kept the explicit category-substitution case, unavailable costs, exact budget thresholds and no-dropping repair tests.
- `make test-unit ARGS='-k "day_length or budget"'`: `99 passed, 1041 deselected, 1 warning in 1.47s`.
- The remaining old no-hours-finding API assertions are updated in hours-checks; database rerun awaits CI. This is this part's one integration fix.
