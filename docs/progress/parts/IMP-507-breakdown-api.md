# IMP-507 · breakdown-api

| Field | Value |
| --- | --- |
| Run | RUN-068 (Sprint 5 batch A), part 1 of 2 |
| Card | IMP-507 Daily and category cost breakdown; estimate labels on every screen |
| Part | Daily and category cost breakdown API (3 points), steps 1 and 2 |
| Owner | Manal Patel |
| Status | PR_OPEN (lead integrates) |
| Base commit | 26bac9d |
| Branch | part/IMP-507-breakdown-api |

## Starting point

Steps 1 and 2 were already built by IMP-308 (`docs/progress/parts/IMP-308-budget-costs.md`):

- `budget/engine.py` `compute_costs` already does BF-12 in integer minor units: `by_day` holds the items of each day plus `t` and `s` (for d ≤ N), with an even contingency share per day (ruling B1). `by_category` holds activities, food and other, then transport, accommodation and contingency (ruling B5).
- `CostSummaryOut` (API-33) already declares `by_day[]` and `by_category[]` with the §6.5 shapes. `budget/service.py` already turns them into IMD-05 money strings.

So this part adds no engine, router or schema change. It adds the card's test file, which proves FR-073 AC1 on the fixtures. No API field changed, and no contract regeneration is needed.

## Changed files

- `apps/api/tests/unit/budget/test_breakdown.py` (created)
  - TC-225: on a fixture trip, the day table (max + contingency_share) and the category table (max) each add up to `planning_total`. This is checked after conversion to the API-33 `DayCostLine` and `CategoryCostLine` JSON strings.
  - TC-300: the same sums, plus contingency equals the sum of the shares and the contingency row, for both SAMPLE itineraries (`two_day_walking`, `five_day_local_transport`) priced from `data/fixtures/sampleton/places.csv` with `item_cost`. Each runs under four input sets: no allowances and 0 %; allowances and 10 %; an uneven 7 % split; 50 %.
  - Low estimates add up to `estimate_lo`.
  - Moving an item to another day moves its cost between day rows and keeps the total. This is the engine half of FR-073 AC2.
- `docs/progress/parts/IMP-507-breakdown-api.md`: this record.

## Commands

| Command | Result |
| --- | --- |
| `PYTHONPATH=. .venv/bin/pytest -q tests/unit/budget -k breakdown` (= `make test-unit ARGS='-k breakdown'`) | `12 passed, 63 deselected in 0.17s` |
| `PYTHONPATH=. .venv/bin/pytest -q tests/unit/budget` | `75 passed in 0.09s` |
| `.venv/bin/ruff check app tests` | `All checks passed!` |
| `.venv/bin/ruff format --check app tests` | `206 files already formatted` |
| `PYTHONPATH=. .venv/bin/mypy app` | `Success: no issues found in 118 source files` |
| `PYTHONPATH=. .venv/bin/lint-imports` | `Contracts: 6 kept, 0 broken.` |

Not run: `make test-api ARGS='-k costs'` (TC-226, `tests/api/test_costs.py`). It needs PostgreSQL and is deferred to integration. It is also not in this part's file list.

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-073 AC1: day and category sums equal the trip total (TC-225) | verified | `test_tc_225_…` |
| Category and day sums equal the trip total for all fixtures (TC-300) | verified | `test_tc_300_…` (8 parametrised cases and 2 more) |
| FR-073 AC2: after an edit the breakdown updates (TC-226) | not verified | API test deferred to integration; costs are computed on read (API-33), and the engine half is shown by `test_tc_300_an_edit_that_moves_an_item…` |
| Existing API-33 fields unchanged | verified | no change to `schemas.py`, `router.py` or `service.py` |
| FR-117 / TC-282 / TC-385 (labels, CostBreakdown) | not verified | steps 3 to 5, Manasvi's part |

## Proposed decisions

- **PD-IMP-507-1 (day row label):** card step 2 says by_day and by_category each carry "low, high, label". §6.5 (which wins) defines by_day as `{day_number, min, max, contingency_share}` with no label, and the contingency is a per-day share rather than a separate day row. Proposed: keep the §6.5 shape, which the built API already returns, and correct the card wording. If a day label is wanted, it would be an additive field (weakest label of the day's items) and needs a spec change first.

## Blockers and open issues

- none
