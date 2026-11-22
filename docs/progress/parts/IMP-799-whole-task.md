# IMP-799 · whole-task part

- Run id: RUN-087
- Owner: Kirtan
- Status: PR_OPEN
- Base commit: 4fe514c
- Branch: chore/S7-D-gate-report
- Points: 2 (pending until the gate passes)
- Traces to: NFR-041, NFR-048; CHK-03 to CHK-05, CHK-13, CHK-20 to CHK-22

## Scope

SG-7 gate record, **provisional**: the criteria do not all hold, so the gate is recorded as "not passed yet" with reasons, owners and due dates, and no tag is created (card step 6). Documentation only. No `.env` file was read; no staging URL, AWS, database or Gemini call was made; no workflow was dispatched. Read-only GitHub commands only (`gh run view`, `gh run list`, `gh pr view`, `gh issue list`).

## Changed files

- `docs/progress/gates.md` (modified): the SG-7 stub replaced by the gate entry
- `docs/progress/sprint-7.md` (created; the card says "modify", but the file did not exist)
- `docs/acceptance/rc1.md` (created)
- `docs/test-reports/defects.md` (created; the card says "modify", but the file did not exist)
- `docs/progress/parts/IMP-799-whole-task.md` (created): this record

## Commands run

| Command | Result line (quoted exactly) |
| --- | --- |
| `make check` (this branch, local) | exit 0 on branch commit `f6715c1` (22 Nov 2026): `All checks passed!`, `All matched files use Prettier code style!`, `Success: no issues found in 123 source files`, `Contracts: 6 kept, 0 broken.`, `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date`, unit `1219 passed, 1 warning in 7.97s`, contract `91 passed, 2 deselected, 1 warning in 18.45s`, api `590 passed, 1 warning in 114.68s (0:01:54)`, authz `87 passed, 14 skipped, 1 warning in 22.60s`, web `Tests  288 passed (288)` |
| `make e2e ARGS='smoke'` (this branch, local) | `12 passed (16.9s)` (exit 0, local Supabase stack, MOCK provider, branch commit `f6715c1`; the first attempt gave `12 failed` because the Next.js dev server stopped at start-up to print an upgrade notice, and the unchanged retry passed) |
| `gh run view 45037634091 --json jobs,headSha,conclusion,event` | `4fe514cfa015f0b9ebd87c4a96c7daa04a4a2958 completed success push`; jobs `audit`, `lint-types`, `unit`, `api`, `guards` success, `attribution` skipped |
| `gh run view 45037634091 --log` (summary lines) | `1215 passed, 1 warning in 13.52s`; `91 passed, 2 deselected, 1 warning in 18.14s`; `Test Files  43 passed (43)`; `Tests  288 passed (288)`; `590 passed, 1 warning in 214.57s (0:03:34)`; `87 passed, 14 skipped, 1 warning in 44.23s`; `445 commits scanned.`; `no leaks found` |
| `gh run view 45037634127 --log` (summary lines) | `4 passed (40.8s)`; `8 passed (20.2s)`; `8 passed (51.6s)`; `9 skipped` / `12 passed (23.8s)`; `1 passed (14.7s)`; `1 skipped` / `1 passed (6.9s)`; `1 skipped` / `1 passed (7.4s)` |
| `gh run list --workflow deploy-staging.yml --limit 5` | latest `completed success Deploy staging ... 44733049430 ... 2026-11-20T12:06:42Z` (commit `964327f`, not the candidate) |
| `gh run list --workflow live-smoke.yml --limit 5` | `HTTP 404: workflow live-smoke.yml not found on the default branch` |
| `git tag` | `contract-v1` (no `v1.0-rc1`) |
| `gh issue list --state open --label bug --limit 50` | no output |
| `git grep -n "EndpointNotImplemented\|status_code=501\|HTTP_501" apps/api/app` | `apps/api/app/core/errors.py:105:class EndpointNotImplemented(DomainError):`, `apps/api/app/core/errors.py:128:    EndpointNotImplemented,` (defined, raised nowhere) |
| Python count over `contracts/openapi.v1.json` | `36` operations, `0` declaring 501 |
| `git grep -n FEATURES_DISABLED -- infra .github .env.example apps/api/app/core/config.py docs/guides apps/web/lib/flags.ts` | no file lists an extension switch; staging and production read `STAGING_FEATURES_DISABLED` / `PRODUCTION_FEATURES_DISABLED` |
| `git diff --stat 6993197..4fe514c -- apps/` | no output |
| `ls apps/api/tests/unit/evaluation/`; `grep -rn "TC-388\|TC-389" apps/api/tests` | no `test_metrics.py`; no match |
| `gh pr view <287, 289, 290, 291> --json reviewDecision,reviews,mergedBy,statusCheckRollup` | no review on any; see the audit in gates.md |

## Not run

| Command | Reason |
| --- | --- |
| `make smoke URL=<staging API URL>` | candidate not deployed to staging; Kirtan staging window, due 26 Nov 2026 |
| live smoke against staging | needs Kirtan's staging window; operator dispatch only; `.github/workflows/live-smoke.yml` does not exist (PD-IMP-799-2) |
| ACC-01 to ACC-18 on staging | staging window |
| `git tag v1.0-rc1` | criteria do not all hold (card step 6) |
| `make e2e ARGS='--grep @ext'` with enabled switches | no extension is enabled (all cut, IMD-65); `extensions.spec.ts` ran in the CI E2E step "Run the regression specs" |

## Acceptance criteria

| Criterion | Status (verified / not verified) | How |
| --- | --- | --- |
| docs/progress/gates.md records SG-7 with date, commit SHA and each criterion as met or not met | verified | gates.md SG-7: 22 November 2026, `4fe514c`, 27 rows each met / not met / not verifiable / not applicable |
| ACC-01 to ACC-18 results recorded on staging (CHK-21) | not verified | not run on staging; `docs/acceptance/rc1.md` lists all 18 as pending with local and CI coverage as supporting evidence |
| no severity-1 defect open (CHK-22) | verified on the records to date | `docs/test-reports/defects.md`; staging, device and usability results pending |
| Final evaluation report and cost report exist (US-131) | verified | `eval/reports/final-baseline.md`, `docs/test-reports/cost-latency-report.md` |
| document set drafted (US-145, US-146) | verified (drafted); US-146 trials not verified | six documents of IMP-707 exist; step 6 trials pending |
| Tag v1.0-rc1 exists on a commit whose CI and staging smoke are green | not verified (not met) | `git tag` shows only `contract-v1`; staging smoke not run |
| No criterion is recorded as met without a linked artefact | verified | every met row in gates.md SG-7 links its artefact |
| Each extension is recorded as done (tests TC-399 to TC-432 passing) or switched off; the @ext E2E smoke passes for the enabled ones | verified as recorded (cut, off by decision); `FEATURES_DISABLED` listing not verified | gates.md SG-7 "Extension freeze"; repository configuration lists no extension switch; @ext not applicable |

## Blockers

- Staging: the candidate is not deployed; `make smoke`, live smoke, ACC-01 to ACC-18 and the staging security rows need Kirtan's staging window (due 26 Nov 2026).
- Human results: IMP-703 sessions, IMP-611 and IMP-704 usability sessions, IMP-707 step 6 trials (due 26 Nov 2026).

## Proposed decisions

- PD-IMP-799-1: source of the ACC-01 to ACC-18 scenario texts (not in the repository), or accept the E2E-01 to E2E-09 mapping in `rc1.md` for the staging re-run.
- PD-IMP-799-2: `.github/workflows/live-smoke.yml` does not exist and no card creates it; decide whether step 3 is met by an operator run of `make live-smoke` with the staging key, or a workflow is added.
- PD-IMP-799-3: list the nine extension switches in `STAGING_FEATURES_DISABLED` and `PRODUCTION_FEATURES_DISABLED` before the tag, or accept "not built, off by decision" (IMD-187) for card step 7.
- The proposed decisions of the Sprint 7 part records are copied in `docs/progress/sprint-7.md`, "Proposed decisions for team review".

## Open issues

- The IMP-707 records ask the gate to update `docs/srs.md` section 11, `docs/test-plan.md` §8 and the `docs/architecture.md` staging comparison; those files are outside this part and are left for their owners after the staging window.
- `docs/progress/deferred.md` is not updated by this run; the SG-7 open items are in gates.md.
