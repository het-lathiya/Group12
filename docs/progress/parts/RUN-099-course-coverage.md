# RUN-099 · IMD-221 · coverage workflow

Owner: Kirtan (`chaudhari kirtan sandipbhai`). Base: `77e52bac363b91b578e7636bcf6833b2e90fb5e4`.

The optional Course reports workflow runs on manual dispatch or pull requests changing
`docs/course/**` or its own workflow. It copies the existing API job's PostgreSQL service,
auth stub, migrations and migration round trip. It measures the API, authorization, unit
and offline contract suites with branch coverage, and the web unit suites with V8 coverage.
The artifacts are `coverage-api` and `coverage-web`, including machine-readable coverage,
terminal output and HTML. Existing required workflows and checks are unchanged.

`@vitest/coverage-v8` matches the installed Vitest version; npm's existing lockfile is updated.
No pnpm lockfile is present in this repository. Report thresholds remain informational (TC-334,
NFR-030); this workflow adds no threshold or branch-protection change.

Validation:

- `actionlint .github/workflows/course-reports.yml`: exit 0, no findings.
- `npm run test --prefix apps/web -- tests/unit/lib/format.test.ts --coverage --coverage.include=lib/format.ts --coverage.reporter=text --coverage.reportsDirectory=/tmp/run-099-coverage-provider`:
  `Test Files  1 passed (1)`; `Tests  2 passed (2)`. This verifies the provider only;
  package coverage comes from the CI artifacts in the course coverage summary.
- `make lint`: exit 0; `All checks passed!`; `All matched files use Prettier code style!`.
- Workflow setup compared with the existing API job. CI artifact evidence is recorded
  by Junaid in the course coverage summary after the pull-request run.
Local `make check` and E2E: not run — operator fast mode; CI covers.
Smoke/live providers: not run — pending staging window 1 Dec.

Acceptance: artifact names and trigger paths verified in workflow source; downloadable
coverage evidence awaits the pull-request run. No contracts or migrations changed.
