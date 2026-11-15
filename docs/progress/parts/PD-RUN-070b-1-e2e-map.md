# PD-RUN-070b-1 · e2e-map

- Run id: RUN-071
- Owner: Kirtan
- Status: PR_OPEN-pending (the lead integrates and dispatches the E2E workflow)
- Base commit: aec7caa
- Scope: `.github/workflows/e2e.yml` ran only `make e2e ARGS='journey'`, so `apps/web/e2e/map.spec.ts` (tag `@map`, IMD-173, TC-240) did not run in CI. The MOCK `e2e` job now runs it as well. No application code, spec, contract, test or dependency changed.

## Files changed

- .github/workflows/e2e.yml (`e2e` job only; the `staging` job, triggers, permissions, env and secrets are unchanged):
  - New step "Run the map specs" after "Run the journey": `make e2e ARGS='map'` with `BASE_URL: http://localhost:3000`. `if: ${{ !cancelled() }}` makes it run when the journey step failed, so both specs report.
  - `PLAYWRIGHT_HTML_REPORT` is set per step (`playwright-report/journey`, `playwright-report/map`). The CI reporter in `apps/web/playwright.config.ts` is `["html", { open: "never" }]` with no `outputFolder`, so both runs would write to `apps/web/playwright-report/` and the second would empty the first. Playwright 1.64.1 reads `PLAYWRIGHT_HTML_REPORT` (resolved against the working directory, which `make e2e` sets to `apps/web`), so the config is untouched.
  - The upload step is unchanged: its path `apps/web/playwright-report/` already covers both subfolders. `test-results/` is cleared at the start of each run, but the HTML report copies its attachments and traces into its own folder, so the report does not depend on it and it is not uploaded.
- docs/progress/parts/PD-RUN-070b-1-e2e-map.md: this record.

## Commands and results

- `python3 -c 'import yaml,sys; yaml.safe_load(open(sys.argv[1]))' .github/workflows/e2e.yml`: parses, exit 0.
- `actionlint .github/workflows/e2e.yml`: no output, exit 0.
- `apps/web/node_modules/.bin/prettier --check .github/workflows/e2e.yml` (main checkout's binary): `Code style issues found in the above file.` The only difference is one blank line at the end of the file, which the unmodified file at aec7caa has too (the same check on `git show aec7caa:.github/workflows/e2e.yml` gives the same warning). Not changed here; the repository's `format:check` runs inside `apps/web` and does not cover `.github/`.
- Not run: `make e2e` (needs the local Supabase stack, API and web app), PostgreSQL tests, live calls.

## Acceptance

- The map spec runs in the MOCK E2E job after the journey step, and also when the journey step failed: implemented, YAML valid and actionlint clean; not verified by a CI run (pending the lead's `workflow_dispatch` of E2E on the integrated branch).
- The artifact covers both specs: the journey and map reports are in separate folders under `apps/web/playwright-report/`, which the unchanged upload step contains: implemented; not verified by a CI run (the artifact contents are to be checked on the dispatched run).
- Journey step, triggers, secrets and the staging job unchanged: verified by the diff (only the two `env` lines and the new step differ).

## Blockers

- none

## Proposed decisions

- none

## Open issues

- The `map` filter is a regular expression on the spec path; today only `e2e/map.spec.ts` matches. A future spec whose path contains "map" would also run in this step.
- If the dispatched run shows the map specs failing for a reason in `map.spec.ts`, that is outside this part.

## RUN-071c

- Run id: RUN-071c
- Owner: Kirtan
- Decision: IMD-183 (Actions minutes guardrail)
- Trigger change: `.github/workflows/e2e.yml` no longer runs on `push` to `main` or on the nightly `schedule` (`30 20 * * *`). Only `workflow_dispatch` remains, with its `base_url` input unchanged; E2E is dispatched by hand on a pull request's branch before merge. The header comment says so. The `e2e` and `staging` jobs, their `if:` conditions (`!inputs.base_url` and `inputs.base_url`, neither refers to the push or schedule event), `permissions`, `env` and `concurrency` are unchanged.
- Command: `apps/api/.venv/bin/python -c "import yaml,sys;d=yaml.safe_load(open('.github/workflows/e2e.yml'));print(list(d[True].keys()) if True in d else list(d['on'].keys()))"`
- Result: `['workflow_dispatch']`

## RUN-072

- Run id: RUN-072
- Owner: Kirtan (chaudhari kirtan sandipbhai), 0 points
- Part: ci-edited
- Status: implemented; local workflow checks passed; runtime PR-edit acceptance remains not verified
- Base commit: a72d07a
- Decisions: IMD-183, IMD-184; related card IMP-102
- Files changed: `.github/workflows/ci.yml` and this record only.

The `pull_request` trigger keeps `edited` because attribution checks the PR body. The five jobs `lint-types`, `unit`, `guards`, `audit` and `api` each have `if: github.event.action != 'edited'`, so an edit runs only `attribution`. The header documents the Actions minutes guardrail and that PR titles and bodies are final at creation. The six job names, push-to-main trigger, other PR events, concurrency, attribution condition and every step are unchanged.

Commands and exact results:

- `python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml'))"`: no output, exit 0.
- Parsed YAML comparison with the preceding commit, removing only the five new conditions: `CI: five edited-event guards verified; six jobs, triggers, concurrency and steps otherwise unchanged`.
- `actionlint .github/workflows/ci.yml`: no output, exit 0.
- `git diff --check`: no output, exit 0.

Acceptance: the YAML and all five conditions are verified locally. "A PR edit runs only attribution" remains **not verified at runtime** until an actual PR edit occurs; none is allowed in this run. No workflow is dispatched for this check. The one final push and one E2E dispatch follow all three parts and local integration checks; their result is recorded in the final pull request. No contract, migration or dependency changed.

Blockers: none. Proposed decisions: none; IMD-184 authorizes this change.

## RUN-073

- Run id: RUN-073
- Owner: Kirtan (chaudhari kirtan sandipbhai)
- Date: 15 November 2026
- Status: implemented; local workflow checks passed; the push-to-main trigger remains not verified at runtime
- Base commit: 43a4240
- Decision: IMD-185 (lifts IMD-183's one-push and one-E2E limit: E2E runs by dispatch on each pull request before merge and on every push to `main`; nightly stays off)
- Files changed: `.github/workflows/e2e.yml` and this record only.

The `push` trigger with `branches: [main]` is restored under `on:` in the shape it had before IMD-183 removed it. `workflow_dispatch` and its `base_url` input are unchanged, and no `schedule` is added. The header comment cites IMD-185. The `e2e` and `staging` jobs, `permissions`, `env` and `concurrency` are unchanged. On a push, `inputs.base_url` is empty, so `e2e` (`!inputs.base_url`) runs and `staging` (`inputs.base_url`) does not; the staging job stays dispatch-only.

Commands and exact results:

- `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/e2e.yml'))"`: no output, exit 0.
- `python3 -c "import yaml;d=yaml.safe_load(open('.github/workflows/e2e.yml'));print(list(d[True].keys()))"`: `['push', 'workflow_dispatch']`.
- `actionlint .github/workflows/e2e.yml`: no output, exit 0.
- `git diff --check`: no output, exit 0.
- Not run: `make e2e`, PostgreSQL tests, live calls; no workflow is dispatched and nothing is pushed in this run.

Acceptance: the trigger list and YAML are verified locally. "E2E runs on every push to main" is **not verified** yet: it can be observed only after this change is merged to `main`. No contract, migration or dependency changed.

Blockers: none. Proposed decisions: none; IMD-185 authorizes this change.
