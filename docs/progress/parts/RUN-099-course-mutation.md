# RUN-099 · IMD-221 · mutation testing

Owner: Manya (`Manya Rana`). Base: `77e52bac363b91b578e7636bcf6833b2e90fb5e4`.

Changed: scoped mutmut/Stryker setup, pinned development dependencies and lockfiles, optional Make
mutation targets, generated-output ignores, focused regression assertions, summary scripts and
`docs/course/08-mutation-testing.md` with raw evidence under `docs/test-reports/course/`.

Scope: API `app/trips/domain.py`, `app/budget/engine.py`, `app/routing/estimate.py`; only unit trip,
budget and routing suites, no database. Web `lib/auth/redirect.ts`, `lib/format.ts`, related Vitest
unit tests. Each tool invocation has a bounded timeout. CI required checks remain unchanged.

`uv add --dev mutmut==3.8.1` and `uv sync --extra dev` install mutmut with the existing API toolchain.
The previously locally excluded `uv.lock` is explicitly included as requested. Web uses the repository's
npm lockfile, not pnpm. Stryker core/runner are pinned to `10.1.1` and the coverage provider matches
Vitest `5.0.5`. These development tools implement the requested experiments, without a new runtime service.

## Commands and actual results

| Command | Exact result line / evidence |
| --- | --- |
| `scripts/run_course_mutation.sh '*'` after focused regressions | exit 0; `mutmut export-cicd-stats`: killed `569`, survived `28`, total `617`, no_tests `20`, timeout `0`; [raw API summary](../../test-reports/course/mutation-api-summary.txt) |
| `python3 scripts/course_mutation_summary.py api apps/api/mutants/app` | `API_TOTAL killed=569 survived=28 timeout=0 no_coverage=20 error=0 not_run=0 score=92.22%` |
| `timeout --signal=INT --kill-after=20s 15m npm run mutation --prefix apps/web` | exit 0; [raw web summary](../../test-reports/course/mutation-web-summary.txt) |
| `python3 scripts/course_mutation_summary.py web apps/web/reports/mutation/mutation.json` | `WEB_TOTAL killed=41 survived=1 timeout=0 no_coverage=2 error=0 not_run=0 score=93.18%` |
| `apps/api/.venv/bin/pytest apps/api/tests/unit/trips apps/api/tests/unit/budget apps/api/tests/unit/routing -q` | `185 passed in 0.76s` |
| `npm run test --prefix apps/web -- tests/unit/auth/redirect.test.ts tests/unit/lib/format.test.ts` | `Test Files  2 passed (2)`; `Tests  20 passed (20)` |
| `make lint` | exit 0; `All checks passed!`; `All matched files use Prettier code style!` |
| `apps/api/.venv/bin/ruff check scripts/course_coverage_summary.py scripts/course_mutation_summary.py` | `All checks passed!` |
| `apps/api/.venv/bin/ruff format --check scripts/course_coverage_summary.py scripts/course_mutation_summary.py` | `2 files already formatted` |
| `uv lock --check --project apps/api` | `Resolved 93 packages in 16ms` |
| `npm ci --prefix apps/web` | exit 0; `added 900 packages, and audited 901 packages in 26s`; `15 moderate severity vulnerabilities` (final PR audit remains the merge check) |
| `bash -n scripts/run_course_mutation.sh`; `make -n mutation`; `actionlint .github/workflows/course-reports.yml`; `git diff --check` | exit 0 |
| Course link/placeholder and summary/export validation | `Course document links and placeholders: PASS`; `Mutation summary matches official export; temporary fixture link removed: PASS` |

[PR #302](https://github.com/het-lathiya/Group12/pull/302) is the review/evidence destination.
Mutation results are local, not an Actions mutation run. Coverage remains the separately linked
[pre-mutation CI baseline](https://github.com/het-lathiya/Group12/actions/runs/46124142747).

## Verification and limits

Initial setup runs had fixture-layout/external-node-ID failures; those counts were rejected after
a direct mutant/control check. The corrected sandbox runs the actual selected unit tests. The
original source-import architecture test is checked in ordinary targeted pytest; instrumentation
imports are excluded only inside mutation execution. No source test is deleted or marked skipped.

The regression additions check a trimmed minimum-length title, a readable title error, group-price
labelling, relative redirect input, same-origin protocol-relative rejection and a valid slash-suffix
path. Inspected mutant diffs record the resulting kills and remaining survivors. Remaining no-coverage
and equivalent/uncertain survivors are included in the report denominator and limitations.

Acceptance: tools/configuration, bounded real executions, per-module counts/scores, survivor analysis,
quick regression changes and raw summaries verified. No production logic, contracts or migrations changed.
`make check`/full E2E: not run — operator fast mode; CI covers.
Database/staging/live-provider work: not run — pure unit scope; pending staging window 1 Dec.
