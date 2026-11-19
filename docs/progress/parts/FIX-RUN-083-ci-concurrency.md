# FIX RUN-083 · ci-concurrency part

- Run id: RUN-083 (batch run, agent F, part F2)
- Owner: Kirtan (chaudhari kirtan sandipbhai), integration lead
- Status: PR_OPEN (committed on the batch branch; the lead pushes and opens the pull request)
- Base commit: f75aa94
- Branch: S7B/fixes
- Points: 0 (CI fix)
- Traces to: IMP-102 (CI workflow); IMD-183, IMD-184 (a PR edit runs only attribution)

## Problem

`.github/workflows/ci.yml` used one concurrency group per pull request, `ci-<workflow>-<PR number or ref>`, with `cancel-in-progress` on for pull-request events. An `edited` event (a title or body change) runs only the `attribution` job, but it joined the same group, so it cancelled a code run (opened, synchronize, reopened) that was still in progress for the same pull request.

## Changed files

- `.github/workflows/ci.yml` (modified): the concurrency group gets a suffix, `edited` for an `edited` event and `code` for every other event, plus a one-line comment citing this fix:
  `group: ci-${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}-${{ github.event.action == 'edited' && 'edited' || 'code' }}`.
  `cancel-in-progress`, the triggers, the six job names (`api`, `attribution`, `audit`, `guards`, `lint-types`, `unit`) and the runner `ubuntu-24.04` are unchanged. A new push still cancels an older code run of the same pull request, and a new edit still cancels an older edit run.
- `docs/progress/parts/FIX-RUN-083-ci-concurrency.md` (created): this record.

## Commands run

| Command | Result line (quoted exactly) |
| --- | --- |
| `python3 -c "import yaml,sys; d=yaml.safe_load(open(sys.argv[1])); print('YAML OK', sorted(d['jobs']), ...)" .github/workflows/ci.yml` | `YAML OK ['api', 'attribution', 'audit', 'guards', 'lint-types', 'unit'] ...` (the parsed group is the new expression, `cancel-in-progress` is `${{ github.event_name == 'pull_request' }}`, triggers `['opened', 'synchronize', 'reopened', 'edited']`) |
| `git diff --stat` | `1 file changed, 2 insertions(+), 1 deletion(-)` (`.github/workflows/ci.yml`, before this record was added) |

## Not run

| Command | Reason |
| --- | --- |
| `actionlint` | Not installed in this container. |
| A real CI run with an edited event during a code run | Needs a pull request on GitHub; this run does not push or open pull requests. |

## Acceptance criteria

| Criterion | Status (verified / not verified) | How |
| --- | --- | --- |
| The group separates `edited` events from code events | verified | diff and the parsed YAML |
| `cancel-in-progress`, job names, triggers and runner unchanged | verified | the diff changes only the group line and adds one comment line |
| The YAML parses | verified | `yaml.safe_load` above |
| An edited event no longer cancels a code run on GitHub | not verified | needs a live pull request |

## Blockers

none

## Proposed decisions

none

## Open issues

none
