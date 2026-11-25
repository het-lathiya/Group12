# IMP-804 · report-data-architecture part

- Run id: RUN-087
- Owner: Malhar (Malhar Mer; card lead; part "Final report: data and architecture chapters", 1 point)
- Status: PR_OPEN (draft; human completion and the claims-check review pending)
- Base commit: 4fe514cfa015f0b9ebd87c4a96c7daa04a4a2958 (`4fe514c`, `main`, the SG-7 release-candidate commit)
- Branch: chore/S7-D-gate-report (batch branch of RUN-087; card branch name `feat/IMP-804-<part>`)
- Traces to: US-148; NFR-041; TC-397; CHK-19
- Card steps built: 1 (data and architecture chapters, known limitations, cut-list decisions, account-deletion procedure, Stage 2 position, pending items) and 2 (claims check of these chapters), drafted from repository artefacts under step 4. Step 3 (presentation) belongs to Jeel's part; the AI chapter belongs to Manya's part.

## Changed files

- `docs/final-report.md` (created): sections 1 to 4 and 6 to 10; section 5 (AI) holds only the line "see AI chapter (Manya)"
- `docs/final-report-claims-check.md` (created): 33 claim rows for the data and architecture chapters (rows 1 to 33), the claims removed, a placeholder for the AI chapter rows and the presentation outline
- `docs/progress/parts/IMP-804-report-data-architecture.md` (created)

## Sources used

`docs/srs.md`, `docs/architecture.md`, `docs/api.md`, `docs/test-plan.md`, `docs/guides/deployment-guide.md`, `docs/guides/user-guide.md`, `docs/guides/aws-setup.md`, `docs/guides/rag-corpus.md`, `docs/progress/gates.md` (SG-3 to SG-8), `docs/progress/sprint-6.md`, `docs/progress/deferred.md`, `docs/decisions/cut-list-checkpoint.md`, `docs/test-reports/` (all files), `eval/reports/final-baseline.md`, `docs/stage2/README.md`, `docs/stage2/migration-gate-criteria.md`, `docs/spec/DECISION_REGISTER.md` (IMD-46, IMD-47, IMD-65, IMD-99 to IMD-105, IMD-115, IMD-137, IMD-167, IMD-200, IMD-201, IMD-213), `docs/spec/AMENDMENT_A1_AWS_RAG.md`, the data quality reports under `data/`, the part records of IMP-219, IMP-608, IMP-705, IMP-706 and IMP-707, and the CI runs below.

## Commands run

All read only, 22 November 2026, in the main checkout at `4fe514c`.

| Command | Result line (quoted exactly) |
| --- | --- |
| `gh run view 45037634091 --json conclusion,headSha,event,workflowName,jobs` | `"conclusion":"success"`, `"headSha":"4fe514cfa015f0b9ebd87c4a96c7daa04a4a2958"`, `"event":"push"`, `"workflowName":"CI"`; jobs audit, lint-types, unit, api, guards success, attribution skipped |
| `gh run view 45037634091 --log` (summary lines) | `1215 passed, 1 warning in 13.52s`; `91 passed, 2 deselected, 1 warning in 18.14s`; `590 passed, 1 warning in 214.57s (0:03:34)`; `87 passed, 14 skipped, 1 warning in 44.23s`; `Tests 288 passed (288)`; `TOTAL 8065 632 92%`; `445 commits scanned.`; `no leaks found` |
| `gh run view 45037634127 --json …` and `--log` (step result lines) | `"conclusion":"success"`, head `4fe514c…`; journey `4 passed (40.8s)`; map `8 passed (20.2s)`; itinerary-edit `8 passed (51.6s)`; regression `12 passed (23.8s)`, `9 skipped`; floor `1 passed (14.7s)`; timeout `1 passed (6.9s)`; quota `1 passed (7.4s)` |
| `gh run view 44733049430 --json …` and `--log` | `"conclusion":"success"`, `"headSha":"964327f83c73e90f1309e0ecb3e7db82cda471c8"`, `"workflowName":"Deploy staging"`; `5 passed in 1.66s` |
| `gh run view 43807026528 --json …` and `--log` | E2E, workflow_dispatch, success, `4c4375e`; `4 passed (34.0s)`, `8 passed (18.2s)` |
| `gh run view 43431854989 --json …` | E2E, workflow_dispatch, success, `f741fd6` |
| `python3` count of operations in `contracts/openapi.v1.json` | `36` |
| `find data/places/* data/guides/* data/fixtures/sampleton -type f` | `data/guides/ahmedabad: 16 files` (15 guides and `quality_report.md`); `data/fixtures/sampleton/guides/`: 3 files |

## Not run

| Command | Reason |
| --- | --- |
| `make check` | This part changes only Markdown documents; the run rules allow no history-writing git command and the lead runs the checks before the commit |
| Any staging, AWS or Gemini command (`make smoke`, the account-deletion procedure, `make live-smoke`) | Not allowed in this run (no live calls); the staging results are pending (Kirtan) |

## Acceptance criteria

| Criterion | Status (verified / not verified) | How |
| --- | --- | --- |
| Every numeric claim in the report and slides appears in the claims check with a linked record (US-148 AC1, TC-397) | verified (draft) for sections 1 to 4 and 6 to 10 / review by Junaid pending | Each number was opened in its source (JSON, Markdown or CI log) and entered with its checked value in `docs/final-report-claims-check.md`. Under the strict source rule of RUN-087 only `eval/results/`, `eval/reports/`, `docs/test-reports/` and CI run links count as sources; every other number (requirement coverage, operation and table counts, extension and switch counts, guide counts, the place minimum, audit counts, the course length) was removed or reworded and is listed under "Claims removed while drafting". AI chapter rows: Manya's part. Slides: Jeel's part. TC-397 is a manual review by Junaid, not yet done |
| The presentation fits the time slot in rehearsal and states the Stage 2 position honestly (US-148 AC2) | n/a to this part | Presentation part (Jeel); rehearsal timing pending |
| Known limitations and what was not built are stated (CHK-19) | verified (draft) | `docs/final-report.md` §2 (delivered, cut list from SG-4 and IMD-167, extensions cut by IMD-65, IMD-46 exclusions, T1, R2, PP and Stage 2 not built) and §7 (known limitations); human completion by Malhar pending |
| Card step 1: manual account-deletion procedure and Stage 2 position included | verified (draft) | §8 from `docs/guides/deployment-guide.md` §9 (A1 §5.1, IMD-101), marked not run on AWS; §9 from `docs/stage2/README.md` (Proposed, conditional and not done) |

## Blockers

- none for this draft. The report cannot be final until the staging results (Kirtan) and the human activities (Junaid, Krrish) are recorded or explicitly left pending at SG-7.

## Proposed decisions

- none.

## Open issues

- Follow-up of the coordinator in RUN-087: the strict source rule was applied after the first draft; 14 rows were removed from the claims check and the report prose reworded so that no unsourced number remains.

- `docs/stage2/migration-gate-criteria.md` "Current reference values" still says the final Gemini run was "not measured: no key in the run environment", although `eval/results/20261120T165222Z-gemini` now exists (IMP-706 owner, Manya).
- The difference lists of `docs/srs.md` §11 and `docs/architecture.md` §11 describe `main` at `f75aa94`; SRS D-18 (no IMP-705 or IMP-706 record) is out of date. The SG-7 gate should update them.
- `docs/guides/aws-setup.md` §14 (monthly cost estimate) is still "TO BE FILLED BY KIRTAN", so the report gives no cost figure for AWS.
- The last Deploy staging run is for `964327f`, not the candidate `4fe514c`.

## Update of RUN-096 (batch H, 25 November 2026; this file existed and is modified)

- Owner: Malhar. Branch `fix/RUN-096-batch-h`. Base commit: 5fa8e6d (on `main`). Status: PR_OPEN candidate. 0 points in this run.
- Changed files: `docs/final-report.md` header, sections 3, 4.1, 4.2 and 7 (two data tiers, migration `0008`, the live-data module, the switch state of IMD-220, limitations of live cities); `docs/final-report-claims-check.md` row 33a, "pending Junaid review"; this record.
- Already in the report and unchanged: the SG-4 cut-list decisions (section 2.2), the manual account-deletion procedure (section 8), the Stage 2 position (section 9, CHK-19). Section 5 (Manya) and section 11 (any-city, #297) are linked, not rewritten.
- Commands: `gh run view 45664284226 --log`: `Contracts: 7 kept, 0 broken.` (job `lint-types`, head `5fa8e6d`). `gh run list --workflow deploy-staging.yml`: the last run is still 44733049430 (`964327f`), so section 4.3 stands. The run checks on the branch head are in the SYNC REPORT of RUN-096.
- Acceptance: the chapters state the switch state as pending (**verified**); every new number has a row (**verified**); staging and production results **not verified** — pending (Kirtan); claims review pending (Junaid).
- Proposed decisions: none. Blockers: none.
- Open issues: section 11 still calls PD-AC-2 proposed and names v4's Gemini run as pending; IMD-220 and the IMP-732 report have settled both. Sections 6 and 10 still describe the candidate `4fe514c`.
