# IMP-608 · alerts-contingency

| Field | Value |
| --- | --- |
| Run | RUN-075 (Sprint 6 batch A), part 1 of 2 |
| Card | IMP-608 Budget alerts and contingency buffer |
| Part | Budget alerts and contingency buffer (2 points), steps 1, 2, 3 and 5 |
| Owner | Manal Patel |
| Status | PR_OPEN (lead integrates) |
| Base commit | a6307c3 |
| Branch | part/b |

## Starting point

Steps 1, 2, 3 and 5 were already built by IMP-308, IMP-411 and IMP-501:

- `budget/engine.py`: BF-08 `C = half_up(S_hi · p, 100)`, BF-09 `P = S_hi + C`, BF-11 `_status` with `BUDGET_NEAR_PCT = 90` (IMD-29). Exactly on budget counts as near. `BUDGET_EXCEEDED` names the excess, and `BUDGET_NEAR` names `ratio_pct`.
- `itinerary.service.validation_cost_inputs` reads `p` from `budget_settings.contingency_pct` (default 10). It passes `p = 0` when the `contingency` switch is off. API-33 and the validator rules (`validation/rules.py`) both call `engine.compute_costs`, so there is one implementation.
- `budget/service.get_costs` returns `alerts[]` (BUDGET_NEAR and BUDGET_EXCEEDED only) unless `budget_alerts` is off. The validator finding is not switched (TC-372).
- `BudgetSettingsPatch.contingency_pct` is `Field(ge=0, le=50)`, so a value outside the range gets 422. API-34 refuses a contingency value while the switch is off.

So this part adds no engine, router or service change, and no API field changes. "The estimate states that no buffer is included" is carried by `contingency: {pct: 0, amount: "0.00"}`. The BudgetAlert part (Krrish) turns that into the stated sentence. This part adds the card's test file.

## Changed files

- `apps/api/tests/unit/budget/test_alerts_contingency.py` (created): TC-227, TC-228 (including the buffer pushing P over B), threshold boundaries 89.99/90/100/100.01 percent, stable alert IDs and the alert-code filter in `budget/service`, TC-229, TC-230, TC-298 (the tables add up with an uneven 7 percent buffer), and contingency_pct 0..50 accepted, -1 and 51 refused.
- `docs/progress/parts/IMP-608-alerts-contingency.md`: this record.

## Commands

The API commands ran from the worktree root with `PYTHONPATH=$PWD/apps/api`. The database was a throwaway local PostgreSQL 16 + pgvector on 127.0.0.1:55432 (`travel_test_b`).

| Command | Result |
| --- | --- |
| `make test-unit ARGS='-k "alerts or contingency"'` | `20 passed, 1145 deselected, 1 warning in 1.48s` |
| `make test-unit` (all unit) | `1165 passed, 1 warning in 19.74s` |
| `make test-api ARGS='-k costs'` | `20 passed, 446 deselected, 1 warning in 10.05s` |
| `ruff check .` | `All checks passed!` |
| `ruff format --check .` | `229 files already formatted` |
| `mypy app` | `Success: no issues found in 122 source files` |
| `lint-imports --config .importlinter` | `Contracts: 6 kept, 0 broken.` |

Not run: `make e2e` (no Docker on this machine).

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-074 AC1: 92 percent of budget → near (TC-227) | verified | `test_tc_227_…` |
| FR-074 AC2: above budget → over, with the excess (TC-228) | verified | `test_tc_228_…` (two cases) |
| FR-075 AC1: a 10 percent buffer is 10 percent of the estimate (TC-229) | verified | `test_tc_229_…` |
| FR-075 AC2: no buffer → zero line (TC-230) | verified | `test_tc_230_…`; the switch-off API case is `tests/api/test_costs.py::test_the_disabled_switches_drop_the_contingency_and_the_alerts` |
| The contingency applies to S_hi, and the category and day sums equal the planning total (TC-298, TC-300) | verified | `test_tc_298_…`; TC-300 in `test_breakdown.py` (IMP-507) |
| With both switches off, the costs page still shows the estimate and the validator budget warning (TC-372) | verified (API half) | the API test above shows the estimate with `alerts == []`. The validator rules are not switched. The page half belongs to the BudgetAlert part and E2E (not run) |

## Proposed decisions

- none

## Blockers and open issues

- none
