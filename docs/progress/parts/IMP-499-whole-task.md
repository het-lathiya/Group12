# IMP-499 · whole-task part

- Run id: RUN-064 (grouped: RUN-064 decision-record by Nidhi, then this part)
- Owner: Kirtan (kirtan-S111)
- Status: PR open
- Gate commit and base commit: ec6973a (`origin/main` at preflight, as expected)
- Branch: feat/IMP-499-sg4-gate
- Traces to: SG-4 (blueprint Gate 3); IMP-401 to IMP-414, IMP-318; IMD-33, IMD-44, IMD-47, IMD-65, IMD-137
- Card steps: 1, 3, 4, 5 and 6 in full; step 2 (staging) recorded from the operator's evidence only, as the run prompt says. This run made no staging, AWS or Gemini call

## Preflight

| Check | Result |
| --- | --- |
| `git fetch origin`; `git status --porcelain --untracked-files=no` | clean; `git rev-parse --short origin/main` → `ec6973a` |
| Part records on `main` for IMP-401 to IMP-414 and IMP-318 | all present (25 part records; RUN-059 records also present) |
| `gh run list --branch main -L 10` on `ec6973a` | CI 43439545525 success; E2E 43439545599 success; E2E 43537426722 (schedule) success; Deploy staging 43440282256 success |
| `git config core.hooksPath .githooks` | set |

## Changed files

- `docs/progress/sprint-4.md` (created; the card says "modify", but the file did not exist on `main`): one line per part, with owner, points, run, pull request, merged date, status, acceptance and record; the fix runs RUN-059, RUN-063b and RUN-067; open issues.
- `docs/progress/gates.md`: the SG-4 section (status, scope, operator staging evidence, criteria table, checks, working-agreement audit, gaps, open items).
- `docs/decisions/cut-list-checkpoint.md` (created): the rule, the search for point values, why C cannot be computed, the stories not complete, the bound, PD-IMP-499-1.
- `docs/progress/parts/IMP-499-whole-task.md`: this record.

No product code, contract, migration, environment variable or `FEATURES_DISABLED` value changed.

## Commands and results

The API suites ran against a throwaway local PostgreSQL 16.2 with pgvector (pip `pgserver` in the scratch directory, port 55432), which was stopped at the end.

| Command | Result |
| --- | --- |
| `make test-api ARGS='-k generation_failures'` (TC-148, TC-308) | `30 passed, 395 deselected, 1 warning in 8.99s` |
| `make check` | exit 0. ruff `All checks passed!`; ESLint `✖ 1 problem (0 errors, 1 warning)` (from before this run); Prettier `All matched files use Prettier code style!`; mypy `Success: no issues found in 118 source files`; `Contracts: 6 kept, 0 broken.`; `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date`; unit `1040 passed, 1 warning in 16.79s`; contract `87 passed, 2 deselected, 1 warning in 13.46s`; api `425 passed, 1 warning in 112.14s (0:01:52)`; authz `41 passed in 17.82s`; web `Tests  190 passed (190)` |
| `make lint` (after writing these documents) | `All checks passed!`; `✖ 1 problem (0 errors, 1 warning)`; `All matched files use Prettier code style!` |
| Point search: `grep` over `docs/` for "story points", "203", "359 - 2C" and US-nnn with a point value; sum of the Sprint 1 to 4 card points in the task register | no per-story values; card points total 244 over 70 cards |
| `gh pr view <n> --json reviewDecision,reviews,mergedBy,statusCheckRollup` for #259 to #273 (merged) | 0 approvals; all six checks green on each merged head |

Not run:

- `make smoke URL=<staging api url>`: this run makes no staging call (run prompt).
- `make e2e ARGS='journey'` locally: no Docker on this machine. CI evidence: E2E 43431854989 (TC-369), and 43439545599 and 43537426722 on the gate commit.
- Card step 2 on staging (journey, `MOCK_PROVIDER_SCENARIO=timeout`, edit totals): staging window, Wed 18 November 2026 (IMD-137).

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| Sign-up to a saved, edited itinerary passes on staging (TC-369, IMP-414 evidence) | pass on the local stack in CI; not verifiable on staging | E2E 43431854989 `4 passed (36.7s)`; main E2E 43439545599 and 43537426722 on `ec6973a`. TC-370 on staging is an open item |
| A provider failure produces a labelled fallback plan (TC-148, IMP-403 evidence) | pass by API tests; not verifiable on staging | `make test-api ARGS='-k generation_failures'` in this run; IMP-403 part records. Staging timeout demo open; the operator's staging run shows only the config_error path (IMD-44) |
| Edits recalculate in one transaction (IMP-407 evidence) | pass by API tests; not verifiable on staging | TC-206, TC-207, TC-312 in the IMP-407 record, inside this run's `make test-api` (`425 passed`) |
| `make check` and the e2e job are green on `main` at the gate commit | pass | CI 43439545525, E2E 43439545599 and 43537426722 on `ec6973a`; local `make check` exit 0 |
| The checkpoint decision with its arithmetic is recorded; any cut is applied by flag, not by deleting code | pass with a gap | `docs/decisions/cut-list-checkpoint.md`; C not computable, PD-IMP-499-1 waits for the supervisor; no cut applied |

Gate status: **pass with listed gaps** (`docs/progress/gates.md`, SG-4).

## Blockers

None for this part. The staging criteria wait for the staging window (IMD-137), and C waits for per-story point values or the supervisor's confirmation of PD-IMP-499-1.

## Proposed decisions

- **PD-IMP-499-1:** no cut at SG-4. All Sprint 1 to 4 stories are complete except those listed (US-151 / IMP-114 interviews, BLOCKED to 19 November; FR-036 AC3 Ahmedabad samples, half of IMP-402; the staging-only evidence). C ≥ 180 unless the listed stories exceed 23 of the planned 203 points. The supervisor is asked to confirm.

## Open issues

- All gate open items, with owners and dates, are in `docs/progress/gates.md` (SG-4, "Open items"): 22 rows.
- The card's file list says `sprint-4.md (modify)`; the file was created here because it did not exist.
- Card points (244 for Sprints 1 to 4) and the rule's planned 203 story points do not reconcile from the repository. A later decision run could record the per-story values from the blueprint, so that the SG-6 freeze and later checks can compute C.
