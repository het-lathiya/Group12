# IMP-707 · test-plan part

- Run id: RUN-083
- Owner: Mohammad Junaid Kureshi (part "Test plan", 1 point, issue #156)
- Status: PR_OPEN (commit on the batch branch; the pull request is opened by the operator)
- Base commit: `f75aa94`
- Branch: `S7B/docs-core` (batch branch of RUN-083; one commit for this part)

## Card text used (TASK_REGISTER.md, IMP-707)

The test-plan half of implementation step 2 (quoted): "docs/test-plan.md summarises §13 with links to test reports."

Card step 5 applies to every part (drafting rule, summarised): draft from the repository and the specification only; run every documented command locally before writing it; mark commands that could not be run "not verified".

Acceptance criteria of the card (quoted):

- Each required document exists in docs/ with owner and version (US-145 AC1)
- The architecture document matches the deployed system or lists the differences (US-145 AC2)
- A member outside the platform squad completed README setup (time recorded) and a clean deployment answered /health (US-146 AC2, CHK-18)
- A new member created a trip and an itinerary from the user guide without help (US-146 AC1)
- make openapi-check is green, so docs/api.md points to a current contract

## Changed files

- `docs/test-plan.md` (created)
- `docs/progress/parts/IMP-707-test-plan.md` (created)

## What the document contains

Summary of specification §13: rules, test levels and suites with their locations, file counts and commands; the latest counts of this run; critical tests; the E2E scenarios with their spec files and Playwright projects; the regression policy; test data; the CI workflows as built; links to every report in `docs/test-reports/`, `docs/progress/gates.md` and `eval/reports/`; nine differences between §13 and the built set-up; the commands run and those marked not verified.

## Commands run

All in this run, Linux container, proxy variables unset, `PYTHONPATH=/home/user/wt-S7B-docs-core/apps/api`, no database.

| Command | Result line (quoted exactly) |
| --- | --- |
| `make test-unit` | `1210 passed, 1 warning in 20.91s` (exit 0) |
| `make test-contract` | `91 passed, 2 deselected, 1 warning in 20.26s` (exit 0) |
| `make test-web` | `Tests  288 passed (288)` (exit 0) |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` (exit 0) |
| `make lint` | `All checks passed!` … `All matched files use Prettier code style!` (exit 0) |
| `make typecheck` | `Success: no issues found in 123 source files` (exit 0) |
| `make imports` | `Contracts: 6 kept, 0 broken.` (exit 0) |
| `find apps/api/tests/<suite> -name 'test_*.py' \| wc -l`, `find apps/web/tests/unit -name '*.test.ts*' \| wc -l`, `ls apps/web/e2e/*.spec.ts \| wc -l` | unit 53, contract 2, api 24, authz 4, smoke 1; web 43; e2e 13 |

Counts of this run from the integration lead (base `f75aa94`, compose test database), quoted in `docs/test-plan.md` §3 as the latest counts: `make test-unit` → `1210 passed, 1 warning in 19.46s`; `make test-contract` → `91 passed, 2 deselected, 1 warning in 20.46s`; `make test-api` → `590 passed, 1 warning in 276.11s (0:04:36)`; `make test-authz` → `87 passed, 14 skipped, 1 warning in 55.38s`; `make test-web` → `Tests  288 passed (288)`.

## Not run

| Command | Reason |
| --- | --- |
| `make test-api`, `make test-authz`, `make check`, `make test`, `make db-migrate` (by this agent) | Need the database; the run rules leave the shared database to the lead, whose counts are quoted |
| `make e2e` | Needs Docker and the Supabase CLI local stack; the latest E2E evidence is linked (`docs/test-reports/e2e-sprint7.md`), not re-run |
| `make smoke URL=<api url>`, `make live-smoke` | Need a deployed URL or a provider key; staging is off between windows (IMD-137) |
| `make eval PROVIDER=MOCK DATASET=trips/v1`, `make eval DATASET=retrieval/v1 ARGS='--suite retrieval'` | Write run files into `eval/`; not needed for a documents-only part |
| The narrowed `ARGS='-k …'` commands of §13.3 | Their tests are inside the full suites that ran |

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| Each required document exists in docs/ with owner and version (US-145 AC1), for `docs/test-plan.md` | verified | Header table: owner Mohammad Junaid Kureshi, version 1.0 (draft for SG-7), 19 November 2026 |
| Step 2 (test-plan half): `docs/test-plan.md` summarises §13 with links to test reports | verified | Sections 1 to 7 follow §13.1 to §13.7; section 8 links all four files of `docs/test-reports/` (README excepted), `docs/progress/gates.md` and `eval/reports/` |
| Suites and their latest counts from this run stated | verified | Section 3 quotes the five counts given for RUN-083 exactly; E2E is stated as separate evidence |
| Step 5: commands run locally first, else "not verified" | verified | Section 10 of `docs/test-plan.md` |
| The architecture document matches the deployed system or lists the differences (US-145 AC2) | not verified (other part) | Part architecture-api (Manal) |
| A member outside the platform squad completed README setup (time recorded) and a clean deployment answered /health (US-146 AC2, CHK-18) | not verified | HUMAN step 6 of the card |
| A new member created a trip and an itinerary from the user guide without help (US-146 AC1) | not verified | User-guide part (Jeel), HUMAN |
| make openapi-check is green, so docs/api.md points to a current contract | verified (command) | `make openapi-check` exit 0 in this run |

## Blockers

- none for this part.

## Proposed decisions

- PD-IMP-707-4: update the specification §13 opening ("No test has been run yet"), §13.6 (`tests/fixtures/factories.py`) and §13.7 (e2e triggers, CI jobs, test database image) to the built set-up listed in `docs/test-plan.md` §9 (T-01 to T-06).

## Open issues

- When IMP-705 (final evaluation and cost report) and the staging items (TC-352, TC-433, TC-434, TC-436, staging journey, smoke) are recorded, `docs/test-plan.md` §8 should link them; the SG-7 gate can update it.
