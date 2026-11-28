# RUN-099 · IMD-221 · unit, white-box and system testing

Owner: Junaid (`Mohammad Junaid Kureshi`). Base: `77e52bac363b91b578e7636bcf6833b2e90fb5e4`.

Changed: `docs/course/05-unit-testing.md`, `06-system-testing.md`,
`docs/test-reports/course/coverage-summary.txt`, `scripts/course_coverage_summary.py` and this record.

The reports describe the actual pytest/Vitest isolation and fixtures, selected statement/branch/path
examples, input partitions/boundaries with existing TC IDs, and operational acceptance GWT cases.
Missing ACC definitions and staging results remain missing; no local-stack result closes a staging gate.

Coverage evidence: [Course reports 46124142747](https://github.com/het-lathiya/Group12/actions/runs/46124142747),
measured commit `b3248cf`, conclusion `success`. Application/test source is unchanged from `77e52ba`.

| Command | Result |
| --- | --- |
| `gh run watch 46124142747 --exit-status --interval 15` | exit 0 |
| `gh run download 46124142747 -n coverage-api -n coverage-web -D <temp-dir>` | exit 0; downloaded outside the repository |
| `python3 scripts/course_coverage_summary.py <temp-dir> --run-url https://github.com/het-lathiya/Group12/actions/runs/46124142747 --commit b3248cffa380fffb88f1020dc20f7751b8903d5f` | `API_TOTAL lines=9212/9830 (93.71%); branches=1620/1938 (83.59%)`; `WEB_TOTAL lines=1542/1740 (88.62%); branches=1487/1759 (84.54%)` |
| `apps/api/.venv/bin/ruff check scripts/course_coverage_summary.py` | `All checks passed!` |
| `apps/api/.venv/bin/ruff format --check scripts/course_coverage_summary.py` | `1 file already formatted` |
| `git diff --quiet origin/main..b3248cf -- apps/api/app apps/web/app apps/web/components apps/web/lib apps/api/tests apps/web/tests` | exit 0 |

Exact pytest/Vitest result lines are preserved in the coverage summary; the existing baseline CI/E2E
logs were also downloaded for the system report. Every uncovered module is listed in the summary.
The coverage is a baseline before mutation regressions, not an unmeasured claim about the final head.

Acceptance: suite/fixture explanation, named white-box examples, measured per-package line/branch
tables, gap list and black-box/GWT cases verified against source and downloaded evidence.
Live/staging acceptance: not verified — pending staging window 1 Dec. Missing ACC source texts remain open.
No contracts or migrations changed. Local `make check`/E2E: not run — operator fast mode; CI covers.
