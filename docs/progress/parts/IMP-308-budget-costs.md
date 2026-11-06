# IMP-308 · budget-costs part

- Run id: RUN-049.2 (grouped, IMD-121, with IMP-315 and the IMP-308 schedule part)
- Owner: Manal (manalPatel2557)
- Status: PR_OPEN
- Base commit: e5f5e7a
- Branch: feat/IMP-315-308-wave4
- Reviewer: Kirtan (kirtan-S111)
- Traces to: US-051, US-080; FR-033, FR-071; NFR-030; IMD-05, IMD-29; F-3; TC-140, TC-221, TC-222, TC-295, TC-296, TC-297, TC-299, TC-314, TC-316, TC-334
- Card steps built: 2 to 5

## Changed files

- `apps/api/app/budget/engine.py` (created): BF-01 to BF-12, pure, integers in minor units.
- `apps/api/app/budget/service.py` (created), `router.py`, `repository.py`: API-33 as declared. API-34 stays a 501 stub for IMP-411.
- `apps/api/app/budget/schemas.py`: F-3, a validator on `BudgetStatus`. The exported shape is unchanged.
- `apps/api/app/generation/pipeline.py`: `add_costs` in step 9 prices every item from its `places` row.
- `apps/api/app/itinerary/schemas.py`, `repository.py`, `service.py`: the save writes `cost_min`, `cost_max`, `cost_currency` and `cost_label`; `cost_summary` runs the engine; API-24's `totals` now come from it.
- `apps/api/.importlinter`: `app.budget.engine` in the pure-domain contract.
- Tests: `tests/unit/budget/test_engine.py`, `tests/api/test_costs.py` (created); `tests/authz/route_matrix.py` (API-33 joins the two-user suite); `tests/contract/test_openapi_contract.py` (its 501 example moves from API-33 to API-34); `tests/api/test_generations.py`, `test_itinerary.py`, `tests/unit/validation/test_injection_cases.py`, `tests/fixtures/pipeline.py` (items now carry costs).

## Operator rulings

Each is an operator ruling, to be entered in the decision register before SG-3.

| Ruling | Applied in | Test |
| --- | --- | --- |
| Operator ruling B1, to be entered in the decision register before SG-3: contingency split evenly across days, earlier days take the extra minor unit | `compute_costs`, `split` | `test_ruling_b1_*` |
| Operator ruling B2, to be entered in the decision register before SG-3: food to food, shopping and stay to other, the rest to activities; transport and accommodation from traveller inputs only | `cost_category`, `_input_line` | `test_ruling_b2_*` |
| Operator ruling B3, to be entered in the decision register before SG-3: a null `price_max` gives a_hi = a_lo | `item_cost` | `test_ruling_b3_*` |
| Operator ruling B4, to be entered in the decision register before SG-3: `ratio_pct` and `pct` are integers; the ratio rounds half-up once | `_status`, `_summary` | `test_ruling_b4_*` |
| Operator ruling B5, to be entered in the decision register before SG-3: the contingency row has min = max = C and label `estimate`, which the declared enum has | `compute_costs` | `test_ruling_b5_*` |
| Operator ruling B6, to be entered in the decision register before SG-3: a missing price is 0, listed and `COST_INCOMPLETE`; `ESTIMATE_USED` is not emitted | `compute_costs` | `test_tc_222_ruling_b6_*`, `test_tc_314_ruling_b6_*` |

TC-222, TC-295, TC-299, TC-314, TC-316 and TC-140 have no §13.3 row, so they are built from the card's acceptance wording: rounding (TC-295), remainder split (TC-296), group pricing (TC-297), missing prices (TC-299), category estimate (TC-314), zero price (TC-316), a missing cost flagged incomplete (TC-222) and stored totals against a model's own total (TC-140).

## Evidence: API-33 for the SAMPLE trip

From the test database: a three-day SAMPLE trip, 2 adults and 1 child, budget 150.00 GBP, transport 6.00 per day, stay 35.00 per night, generated with MOCK. Both tables add up to the planning total: 145.00 + 14.50 = 159.50.

```json
{
  "currency": "GBP",
  "estimate": {
    "min": "109.00",
    "max": "145.00"
  },
  "contingency": {
    "pct": 10,
    "amount": "14.50"
  },
  "planning_total": "159.50",
  "per_traveller": {
    "travellers": 3,
    "largest_share": "53.17",
    "label": "average"
  },
  "budget": {
    "amount": "150.00",
    "status": "exceeded",
    "ratio_pct": 106,
    "excess": "9.50"
  },
  "by_day": [
    {
      "day_number": 1,
      "min": "41.00",
      "max": "50.00",
      "contingency_share": "4.84"
    },
    {
      "day_number": 2,
      "min": "41.00",
      "max": "47.00",
      "contingency_share": "4.83"
    },
    {
      "day_number": 3,
      "min": "27.00",
      "max": "48.00",
      "contingency_share": "4.83"
    }
  ],
  "by_category": [
    {
      "category": "activities",
      "min": "0.00",
      "max": "15.00",
      "label": "estimate"
    },
    {
      "category": "food",
      "min": "21.00",
      "max": "42.00",
      "label": "estimate"
    },
    {
      "category": "other",
      "min": "0.00",
      "max": "0.00",
      "label": "estimate"
    },
    {
      "category": "transport",
      "min": "18.00",
      "max": "18.00",
      "label": "traveller_input"
    },
    {
      "category": "accommodation",
      "min": "70.00",
      "max": "70.00",
      "label": "traveller_input"
    },
    {
      "category": "contingency",
      "min": "14.50",
      "max": "14.50",
      "label": "estimate"
    }
  ],
  "alerts": [
    {
      "id": "df316a04-61b5-5956-8006-634e97038253",
      "code": "BUDGET_EXCEEDED",
      "severity": "warning",
      "message": "The plan is over your budget by 9.50 GBP.",
      "day_number": null,
      "item_id": null,
      "place_id": null,
      "suggested_fix": null
    }
  ],
  "complete": false,
  "incomplete_items": [
    "c4c7bce1-6b62-4953-9f45-13ebb83b92a0",
    "d4f9ef9a-1164-4319-863a-86260885e9f2"
  ],
  "settings": {
    "transport_allowance_per_day": "6.00",
    "stay_budget_per_night": "35.00",
    "contingency_pct": 10
  }
}
```

## Commands and results

| Command | Result |
| --- | --- |
| `make test-unit ARGS='-k budget'` | `59 passed, 696 deselected, 1 warning` |
| `make test-api ARGS='-k costs'` | `12 passed, 311 deselected, 1 warning` |
| `pytest tests/unit/budget tests/api/test_costs.py --cov=app.budget` (TC-334; `pytest-cov` installed outside the repository, see Open issues) | `TOTAL                        259      7    97%` |
| `make test-authz` | `31 passed` |
| `make lint`, `make typecheck`, `make imports`, `make openapi-check` | `All checks passed!`; `Success: no issues found in 105 source files`; `Contracts: 6 kept, 0 broken.`; `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` |
| `make check` (all three parts in the tree, `TEST_DATABASE_URL` on `pgvector/pgvector:pg16`) | exit 0: unit `755 passed, 1 warning`; contract `87 passed, 2 deselected, 1 warning`; api `323 passed, 1 warning`; authz `31 passed`; web `Tests  88 passed (88)` |
| `make e2e ARGS='journey'` (steps of `.github/workflows/e2e.yml`; web on port 3100 because another server held 3000) | `4 passed (7.2s)`. Run before the last three test-only edits; no application code changed after it |

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-033 AC1 (TC-140): stored totals equal the backend calculation even when the model output carries its own total | verified | `test_tc_140_stored_totals_equal_the_calculation_when_the_model_writes_its_own`; io-1 has no total or price field and refuses one (`test_tc_140_a_total_or_price_field_is_refused_by_the_model_output_schema`), so a model can only carry a total in its text |
| FR-033 AC2 (recalculation after an edit) | not verified | Edits are IMP-407 |
| FR-071 AC1 (TC-221) | verified | `test_tc_221_*` |
| FR-071 AC2 (TC-222): flagged incomplete | verified for the flag | `test_tc_222_ruling_b6_*`. "The item uses a labelled estimate" cannot hold until estimate data exists (ruling B6) |
| Rounding, remainder split, group pricing, missing prices, zero price (TC-295, TC-296, TC-297, TC-299, TC-316) | verified | `test_engine.py` |
| Category estimate (TC-314) | verified as ruled by B6 | `test_tc_314_ruling_b6_*`: no estimate data, no `ESTIMATE_USED` |
| Blueprint §20.3 worked example: planning total 13,530, status near | not verified | The blueprint is not in the repository, as PD-IMP-304-1 and PD-IMP-310-1 found. `test_the_stated_figures_of_the_section_9_3_1_example` checks only the figures §9.3.1 states; no item inputs were invented |
| Statement coverage of app/budget at least 85 percent (TC-334, NFR-030) | verified | 97 percent |
| F-3: no excess unless exceeded | verified | `test_f_3_*` in both test files |
| Times and costs come from recalculation (open criterion of IMP-305-pipeline, costs half) | verified | `test_saved_items_carry_costs_from_the_places_rows` |

## Blockers

None.

## Proposed decisions

- **PD-IMP-308-4: `complete` looks at items only.** An unavailable transport or stay line does not make the total incomplete, or nearly every new trip would be. FR-072 AC2 ("the total says so") is IMP-411's to settle.
- **PD-IMP-308-5: category labels.** Nothing defines the label of a mixed category. It is `curated` when all items are, `unavailable` when all are, otherwise `estimate`; an empty category is `estimate`, because "unavailable" means unknown and these rows show 0.00.
- **PD-IMP-308-6: alert IDs.** `Finding.id` is required but alerts are computed and not stored, so the ID is derived from the trip and code, and stays the same between reads.

## Open issues

- `COST_INCOMPLETE` comes out of the engine, but it is not in `alerts` (declared as `BUDGET_NEAR` and `BUDGET_EXCEEDED`) and nothing writes it to `itinerary_warnings` yet. In API-33 it shows as `complete: false` with `incomplete_items`. The validator of IMP-404 and IMP-405 stores findings.
- `pytest-cov` is not a project dependency, so the coverage figure came from a copy installed outside the repository. CI does not measure TC-334 until a card adds it. In the report, `service.py` shows 71 percent and six missed lines inside `get_costs`; these lines ran (`test_costs.py` asserts their output), and the tracer most likely loses them after an `await` under the async driver.
- `contingency_pct` is `numeric(5,2)` in the database and an integer in the contract (ruling B4). Only whole values can be written today; a fractional one would be truncated.
- `app/budget/engine.py` and `retrieval.min_group_cost` both apply BF-01. They agree today, and the second could call the first in a later change.
