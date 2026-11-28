# Mutation testing

RUN-099 · IMD-221 · owner: Manya. These are **local, bounded experiments**, not CI mutation runs.
[PR #302](https://github.com/het-lathiya/Group12/pull/302) contains the setup, regression tests and
raw evidence. The application source is unchanged from `77e52ba`; the final results include the
unit-test additions in this part. [The coverage run](https://github.com/het-lathiya/Group12/actions/runs/46124142747)
is a separate pre-mutation baseline and does not execute mutation testing.

## Tools and deliberately limited scope

The API uses `mutmut==3.8.1`, added with `uv add --dev mutmut==3.8.1`. The pinned dependency group
and `uv.lock` install with `uv sync --locked --extra dev`; the existing optional development extra
still supplies pytest and the quality tools. Web uses pinned `@stryker-mutator/core` and
`@stryker-mutator/vitest-runner` at `10.1.1`, with the project's Vitest `5.0.5`; npm's existing
`package-lock.json` is retained. No pnpm lockfile is used by this repository.

[Mutmut documentation](https://mutmut.readthedocs.io/en/latest/) describes function mutation and
selected-test execution. [Stryker's Vitest runner](https://stryker-mutator.io/docs/stryker-js/vitest-runner/)
uses related tests, and [its configuration](https://stryker-mutator.io/docs/stryker-js/configuration/)
controls the scope and reports. These tools change operators, constants, conditions and statements,
then rerun tests. A killed mutant is a detected change, a survivor exposes a gap or equivalent
behavior, and no coverage means no associated test reached it. Neither score proves correctness.

| Layer | Real module | Why this module | Test scope |
| --- | --- | --- | --- |
| API validation | `app/trips/domain.py` | Trip validation actually lives here under the specification's domain layout: dates, travellers, budget and errors; also exposes stale-plan helpers | `tests/unit/trips/` |
| API budget | `app/budget/engine.py` | Decimal/minor-unit arithmetic, group/child prices, allowances, totals and labels | `tests/unit/budget/` |
| API routing | `app/routing/estimate.py` | Deterministic distance, rounding and fallback buffers with no provider call | `tests/unit/routing/` |
| Web | `lib/auth/redirect.ts` | Same-site redirect guard and URL handling | `tests/unit/auth/redirect.test.ts` |
| Web | `lib/format.ts` | Date-only UTC rendering | `tests/unit/lib/format.test.ts` |

API configuration copies `app/` for imports but `only_mutate` allows just the listed modules.
Only the selected unit directories run; no API/authz/database suite is collected. The source-import
architecture test in `test_estimate.py` is excluded inside the instrumented sandbox because the
injected trampoline itself imports mutmut. It runs against the original source in the targeted
pytest validation below. No test is deleted, weakened or marked skipped.

`run_course_mutation.sh` temporarily links `apps/data` to the existing SAMPLE fixtures because
mutmut adds a sandbox directory level. It refuses to replace an existing path and removes the
link on exit. Tests remain inside the sandbox so their node IDs resolve during selected execution.
Initial setup attempts hit fixture-path and external-test-node-ID failures; their apparent kill
counts were rejected after a direct mutant/control check. Only the corrected runs below count.

## Reproduction and time limit

From the repository root:

```sh
make mutation-api
make mutation-web
# Or run both sequentially:
make mutation
```

Each tool command is wrapped in `timeout --signal=INT --kill-after=20s 15m`; installation is
separate from that runtime budget. The API wrapper limits worker concurrency; Stryker uses its
Vitest runner with per-test coverage and related-file selection. The targets accept `ARGS`.
The commands used for the recorded corrected API runs were
`scripts/run_course_mutation.sh` and, after the regression changes,
`scripts/run_course_mutation.sh '*'` (explicitly rechecks cached mutants).
Web ran `timeout --signal=INT --kill-after=20s 15m npm run mutation --prefix apps/web`.
Both final tool commands exited successfully before the limit; neither hit the overall deadline.
A deadline exit would leave unfinished mutants as **not run**, separately from per-mutant timeouts.

## Results from real output

API modules (paths relative to `apps/api/app/`):

| Module | Killed | Survived | Timeout | No coverage | Error | Not run | Score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| budget/engine.py | 364 | 5 | 0 | 0 | 0 | 0 | 98.64% |
| routing/estimate.py | 58 | 1 | 0 | 0 | 0 | 0 | 98.31% |
| trips/domain.py | 147 | 22 | 0 | 20 | 0 | 0 | 77.78% |
| TOTAL | 569 | 28 | 0 | 20 | 0 | 0 | 92.22% |

Web modules (paths relative to `apps/web/`):

| Module | Killed | Survived | Timeout | No coverage | Error | Not run | Score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| lib/auth/redirect.ts | 23 | 1 | 0 | 2 | 0 | 0 | 88.46% |
| lib/format.ts | 18 | 0 | 0 | 0 | 0 | 0 | 100.00% |
| TOTAL | 41 | 1 | 0 | 2 | 0 | 0 | 93.18% |

Exact calculated result lines:

```text
API_TOTAL killed=569 survived=28 timeout=0 no_coverage=20 error=0 not_run=0 score=92.22%
WEB_TOTAL killed=41 survived=1 timeout=0 no_coverage=2 error=0 not_run=0 score=93.18%
```

Raw local evidence: [API summary](../test-reports/course/mutation-api-summary.txt),
[official API export](../test-reports/course/mutation-api-stats.json),
[web summary](../test-reports/course/mutation-web-summary.txt),
[inspected mutant diffs](../test-reports/course/mutation-survivor-diffs.txt).
Each summary records the command, tool version, successful exit and scoped result lines;
these are linked local experiments, not fabricated Actions runs.

Counts come from mutmut's per-file `.py.meta` results and `export-cicd-stats`, and Stryker's
JSON/terminal report. `scripts/course_mutation_summary.py` calculates the table from those files;
no numbers are inferred from source size. Score here is detected mutants (killed plus timeout)
divided by all scoped mutants, including no-coverage mutants. Error/unfinished runs get no score.
The final runs have no error or unfinished results. Mutmut's `no tests` is labelled “no coverage”
for this table, not counted as killed or silently removed from the denominator.

The raw API summary preserves the corrected initial and final counts. The web summary preserves
both original terminal tables. The initial web score and subsequent improvement are not line
coverage percentages. The mutmut experiment covers function-body mutations, not every possible
change to module constants, type declarations or data-model defaults.

## Surviving mutants inspected and regression tests

These examples were survivors in the first valid experiments; the result column records the
final state. IDs are tool-local; retain the module and operator when comparing later runs.

| Mutant | Why it survived / what it changes | Targeted action and final result |
| --- | --- | --- |
| API `app.trips.domain.x_validate_title__mutmut_3` (and related `_4`) | Changes the lower comparison so a minimum-length trimmed title is rejected. Earlier tests exercised empty/long and ordinary valid titles, leaving that lower valid boundary unasserted | `test_one_character_title_after_trimming_is_allowed` supplies `" x "`; both boundary mutants are now killed. Existing invalid-title cases now also require a non-empty message, killing the null-message mutant `_7` |
| API `app.budget.engine.x_item_cost__mutmut_16` | Group prices still returned correct numeric amounts while the price label became null; the group-price test asserted amounts alone | `test_tc_297_a_group_price_is_counted_once` now also checks the curated label; this mutant is killed. This protects a user-visible label without changing the pricing formula |
| Web redirect mutant `11`, plus method mutant `12` | An empty prefix test admitted relative text that normalized to the same default path used by the old test; replacing `startsWith("//")` with `endsWith("//")` also escaped existing cases | Added a non-root relative path and a same-origin protocol-relative input to rejected cases, plus an allowed path ending in slashes. Both mutants are now killed |

The remaining web survivor, mutant `22`, removes the final origin-mismatch guard. Earlier checks
already require a single leading slash and reject backslashes/control characters, so a real URL
constructed from those accepted inputs keeps the fixed origin. This appears equivalent under
that input contract; it stays reported as survived. The catch body and origin-rejection body
remain no coverage. No artificial URL mock or ignored-mutant directive is used to inflate the score.

Remaining API survivors and no-test mutants are listed in the raw evidence. In particular,
`_plan_values`/`plan_affected` have no associated tests in the selected unit scope. The surviving
routing clamp mutation is not declared equivalent: antipodal/floating-rounding boundaries need
more investigation. Budget and validation survivors also need review of label/error paths and
arithmetic edges; these experiments do not claim the full-coverage target is met.

## Validation

| Command | Exact result / purpose |
| --- | --- |
| `apps/api/.venv/bin/pytest apps/api/tests/unit/trips apps/api/tests/unit/budget apps/api/tests/unit/routing -q` | `185 passed in 0.76s`, including the original source-import architecture test |
| `npm run test --prefix apps/web -- tests/unit/auth/redirect.test.ts tests/unit/lib/format.test.ts` | `Test Files  2 passed (2)`; `Tests  20 passed (20)` |
| `make lint` | exit 0; `All checks passed!`; `All matched files use Prettier code style!` |
| `apps/api/.venv/bin/ruff check scripts/course_mutation_summary.py scripts/course_coverage_summary.py` | `All checks passed!` |
| `bash -n scripts/run_course_mutation.sh` / `make -n mutation` | exit 0; wrapper syntax and target expansion verified |
| `uv lock --check --project apps/api` | `Resolved 93 packages in 16ms` |
| `npm ci --prefix apps/web` | exit 0; existing npm installer accepts the updated lockfile |

The direct API mutant/control check used the instrumented sandbox: the unmodified control passed,
while the `half_up` division mutant caused the child-free cost assertion to fail. The known title
boundary survivor was also exercised directly during setup validation; this exposed the invalid
external-node-ID configuration before it could be reported as a high score.

No production logic, contract, migration or required check was changed. Tool output, mutation
sandboxes and reports are ignored by git/lint/format as generated artifacts; only raw summaries
are copied under `docs/test-reports/course/`.

Local `make check` and full E2E: **not run — operator fast mode; CI covers**.
Database, live providers and staging: **not run — outside the pure mutation scope; pending staging window 1 Dec**.
