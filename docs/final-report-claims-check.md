# Final report claims check

**Draft — RUN-087, 22 November 2026; manual review by Junaid pending**

| Item | Value |
| --- | --- |
| Checks | [final-report.md](final-report.md) (draft of 22 November 2026, `main` at `4fe514c`) |
| Card | IMP-804 (US-148 AC1); test TC-397; NFR-041 |
| Reviewer | Junaid (manual review, no automated command) — **pending** |
| Prepared by | Malhar (data and architecture chapters); the AI chapter rows are added by Manya's part |

## Purpose

TC-397 and NFR-041 require that every numeric claim in the final report and the slides links to a recorded run, test report or other record, and that a claim without one is removed. This file lists every numeric claim of [final-report.md](final-report.md) with its source and the value found in that source when it was checked on 22 November 2026.

Rules used:

- A **numeric claim** is any count, percentage, duration, size or result figure in the report text, including numbers written as words. Identifiers are not claims: requirement, task, test, decision and gate IDs (FR-, IMP-, TC-, IMD-, SG-), migration numbers, commit IDs, CI run IDs, product and version numbers (PostgreSQL 16, prompt v2) and calendar dates.
- Every number comes only from a file in `eval/results/`, `eval/reports/` or `docs/test-reports/`, or from a CI run link (the strict source rule of RUN-087). A number with no such source was removed from the report or reworded so that the prose carries no digit or number word for it; such numbers are listed under "Claims removed while drafting".
- Each value was opened in its source (JSON, CSV, Markdown or CI log) and compared. A CI value was read with `gh run view <id> --log` (read only).
- Claims removed while drafting because no source was found are listed at the end.

## Claims of the data and architecture chapters (sections 1 to 4 and 6 to 10)

| # | Claim (exact text as it appears) | Location (file + section) | Source (eval/, docs/test-reports/ path or CI run link) | Checked value |
| --- | --- | --- | --- | --- |
| 1 | "works with every cut-list switch off: the floor journey passed in E2E 43807026528 (16 November 2026, `4 passed (34.0s)`)" | final-report.md §2.2 | [E2E 43807026528](https://github.com/het-lathiya/Group12/actions/runs/43807026528) | workflow_dispatch on `4c4375e`, success, 2026-11-16; log shows both `FEATURES_DISABLED` variables with the nine switches; journey line `4 passed (34.0s)` |
| 2 | "the floor step of E2E 45037634127 on the candidate (`1 passed (14.7s)`)" (also §6.1 table "Floor journey, all cut-list switches off · `1 passed (14.7s)`") | final-report.md §2.2, §6.1 | [E2E 45037634127](https://github.com/het-lathiya/Group12/actions/runs/45037634127) | step "Run the floor journey with the nine cut-list switches disabled": `1 passed (14.7s)` |
| 3 | "**30** synthetic places" | final-report.md §3 | `eval/reports/final-baseline.md` "Candidate and conditions" (retrieval database) | "Sampleton 30 places" |
| 4 | "**103** places loaded" | final-report.md §3 | `eval/reports/final-baseline.md` "Candidate and conditions" | "Ahmedabad 103 places" |
| 5 | "the RAG index held **151** documents and **227** chunks, all embedded (`rag-index: documents=151 chunks=227 embedded=227 inactive=0 warnings=0 errors=0`)" | final-report.md §3 | `eval/reports/final-baseline.md` "Candidate and conditions" | `rag-index: documents=151 chunks=227 embedded=227 inactive=0 warnings=0 errors=0` |
| 6 | "report `Contracts: 6 kept, 0 broken.` on the candidate" (also §6.1 "Lint, types, import boundaries") | final-report.md §4.1, §6.1 | [CI 45037634091](https://github.com/het-lathiya/Group12/actions/runs/45037634091), job `lint-types`, step `make imports` | `Contracts: 6 kept, 0 broken.` |
| 7 | "`5 passed in 1.66s`" (last Deploy staging run, commit `964327f`) | final-report.md §4.3 | [Deploy staging 44733049430](https://github.com/het-lathiya/Group12/actions/runs/44733049430) | 2026-11-20, success, head `964327f`; steps "Run the release task", "Update the API service", "Update the web service", "Smoke test and CORS check" success; `5 passed in 1.66s` |
| 8 | "`1215 passed, 1 warning in 13.52s`" | final-report.md §6.1 | [CI 45037634091](https://github.com/het-lathiya/Group12/actions/runs/45037634091), job `unit`, `make test-unit` | `1215 passed, 1 warning in 13.52s` |
| 9 | "`91 passed, 2 deselected, 1 warning in 18.14s`" | final-report.md §6.1 | CI 45037634091, job `unit`, `make test-contract` | `91 passed, 2 deselected, 1 warning in 18.14s` |
| 10 | "`590 passed, 1 warning in 214.57s (0:03:34)`" | final-report.md §6.1 | CI 45037634091, job `api`, `make test-api` | `590 passed, 1 warning in 214.57s (0:03:34)` |
| 11 | "`87 passed, 14 skipped, 1 warning in 44.23s`" | final-report.md §6.1 | CI 45037634091, job `api`, `make test-authz` | `87 passed, 14 skipped, 1 warning in 44.23s` |
| 12 | "`Test Files  43 passed (43)`, `Tests  288 passed (288)`" | final-report.md §6.1 | CI 45037634091, job `unit`, `make test-web` | `Test Files 43 passed (43)`; `Tests 288 passed (288)` |
| 13 | "`Success: no issues found in 123 source files`" | final-report.md §6.1 | CI 45037634091, job `lint-types`, `make typecheck` | `Success: no issues found in 123 source files` |
| 14 | "`TOTAL … 92%` for `app`" | final-report.md §6.1 | CI 45037634091, job `api`, step "Coverage report for TC-334 (adds the unit suite)" | `TOTAL 8065 632 92%` |
| 15 | "npm audit `11 moderate severity vulnerabilities`, none critical" | final-report.md §6.1 | CI 45037634091, job `audit`, step "npm audit (critical findings fail)" | `11 moderate severity vulnerabilities`; step success |
| 16 | "gitleaks `445 commits scanned.`, `no leaks found`" | final-report.md §6.1 | CI 45037634091, job `guards`, step "Secret scan of the full history" | `445 commits scanned.`; `no leaks found` |
| 17 | "Journey (four widths) · `4 passed (40.8s)`" | final-report.md §6.1 | [E2E 45037634127](https://github.com/het-lathiya/Group12/actions/runs/45037634127), step "Run the journey"; widths from `docs/test-reports/e2e-sprint7.md` §4 (360, 768, 1280, 1920 px) | `4 passed (40.8s)` |
| 18 | "Map specs · `8 passed (20.2s)`" | final-report.md §6.1 | E2E 45037634127, step "Run the map specs" | `8 passed (20.2s)` |
| 19 | "Itinerary editing and restore · `8 passed (51.6s)`" | final-report.md §6.1 | E2E 45037634127, step "Run itinerary editing and restore" | `8 passed (51.6s)` |
| 20 | "Regression specs (E2E-01 to E2E-08 at 1280 px, keyboard, extensions) · `12 passed (23.8s)`, `9 skipped`" | final-report.md §6.1 | E2E 45037634127, step "Run the regression specs" (`--project=chromium-1280`) | `9 skipped`; `12 passed (23.8s)` |
| 21 | "Provider failure, timeout · `1 passed (6.9s)`, `1 skipped`" | final-report.md §6.1 | E2E 45037634127, step "Run provider failure with a timeout" | `1 skipped`; `1 passed (6.9s)` |
| 22 | "Provider failure, quota exhausted · `1 passed (7.4s)`, `1 skipped`" | final-report.md §6.1 | E2E 45037634127, step "Run provider failure with quota exhausted" | `1 skipped`; `1 passed (7.4s)` |
| 23 | "three consecutive local full runs on 18 November 2026 at code head `b6051a8`, retries 0" | final-report.md §6.2 | `docs/test-reports/e2e-sprint7.md` §4 "Three consecutive full runs" | three runs at `b6051a8`; "retries are 0" |
| 24 | "each `Running 119 tests using 2 workers`" | final-report.md §6.2 | `docs/test-reports/e2e-sprint7.md` §4 | "Each log starts `Running 119 tests using 2 workers`" |
| 25 | "ending `37 skipped`; `82 passed`" | final-report.md §6.2 | `docs/test-reports/e2e-sprint7.md` §4 table | runs 1 to 3: `37 skipped`; `82 passed (3.9m)` / `(4.1m)` / `(4.1m)` |
| 26 | "The **36** extension cases and the quota case account for the skips" | final-report.md §6.2 | `docs/test-reports/e2e-sprint7.md` §4 | "The 37 skips are 36 cut-extension cases (nine at each width, IMD-65) and the quota scenario" |
| 27 | "**0 of 3** full runs failed" | final-report.md §6.2 | `docs/test-reports/e2e-sprint7.md` §4 | "Observed failing/flaky full runs: 0 of 3" |
| 28 | "app shell overflow at 360 and 768 px" | final-report.md §6.2 | `docs/test-reports/e2e-sprint7.md` §3 and §4 | `smoke.spec.ts:87` at 360 px and 768 px; `auth.spec.ts:147` at 768 px |
| 29 | "the authorization suite then reported `87 passed, 14 skipped, 1 warning in 62.96s (0:01:02)`" | final-report.md §6.3 | `docs/test-reports/security-sprint7.md` "RUN-081b correction evidence" | `87 passed, 14 skipped, 1 warning in 62.96s (0:01:02)` |
| 30 | "Finding F-1 (…; severity 3)" and "No severity 1 or 2 defect was found" | final-report.md §6.3 | `docs/test-reports/security-sprint7.md` "Findings and defects" | F-1 severity "3 (low)"; "No severity-1 or severity-2 defect was found" |
| 31 | "journey `4 passed (31.6s)` with **40** axe scans" | final-report.md §6.4 | `docs/test-reports/accessibility-sprint7.md` §6.1b | `4 passed (31.6s)`; "40 `axe scan` lines (10 per project), each ending `[]`" |
| 32 | "keyboard `4 passed (10.8s)` with **20** scans, every scan `[]`" | final-report.md §6.4 | `docs/test-reports/accessibility-sprint7.md` §6.1b | `4 passed (10.8s)`; "20 `axe scan` lines (5 per project), each ending `[]`" |
| 33 | "43431854989, `4 passed (36.7s)` at four widths" | final-report.md §6.5 | `docs/test-reports/journey-sprint4.md`; [E2E 43431854989](https://github.com/het-lathiya/Group12/actions/runs/43431854989) | report: journey step `4 passed (36.7s)`, "Four widths (360, 768, 1280, 1920 px)"; run: workflow_dispatch on `f741fd6`, success |

## Claims removed while drafting

| Claim considered | Why it was left out |
| --- | --- |
| Number of AI generations that ended `config_error` in the SG-4 staging timing run | Recorded only as operator evidence quoted in `docs/progress/gates.md`, not in a run record, test report or CI run; the report states the outcome without a count |
| Service size (vCPU, memory), log retention days, the AWS budget amount and alert thresholds | Configuration values in `infra/aws/` and the guides, not results; not needed for the chapter and not verified against AWS |
| Card points of the plan and of the cut extensions | Not needed for the report's claims; the cut-list checkpoint itself says card points are not the rule's basis |
| Number of differences listed in the SRS, architecture document and user guide | Those lists describe `main` at `f75aa94` and are to be updated at SG-7; the report links them instead of counting them |
| Monthly AWS cost | No record: [aws-setup.md](guides/aws-setup.md) §14 is still "TO BE FILLED BY KIRTAN" |
| Staging journey, smoke and timing results on the candidate | Not run; pending (Kirtan) |
| Usability, interview, device and screen-reader results | Not run; pending (Junaid, Krrish) |
| Count of MVP and MVP-S requirements Done at SG-6, and the MVP / MVP-S split (`docs/progress/sprint-6.md`) | source not in eval/ , docs/test-reports/ or a CI run |
| Number of API operations in the contract (`docs/api.md`, `contracts/openapi.v1.json`) | source not in eval/ , docs/test-reports/ or a CI run |
| Number of extensions cut and number of cut-list switches (`docs/progress/deferred.md`, IMD-65) | source not in eval/ , docs/test-reports/ or a CI run |
| Sprint range of the cut-list rule (`docs/decisions/cut-list-checkpoint.md`) | source not in eval/ , docs/test-reports/ or a CI run |
| Number of trip inputs the Ahmedabad samples wait for (`docs/progress/deferred.md`) | source not in eval/ , docs/test-reports/ or a CI run |
| Number of synthetic SAMPLE guides (`data/fixtures/sampleton/guides/`) | source not in eval/ , docs/test-reports/ or a CI run |
| Minimum of usable Ahmedabad places (`data/places/ahmedabad/quality_report.md`) | source not in eval/ , docs/test-reports/ or a CI run |
| Number of Ahmedabad guides (`data/guides/ahmedabad/quality_report.md`) | source not in eval/ , docs/test-reports/ or a CI run |
| Number of tables in migrations 0001 to 0007 (`docs/srs.md`) | source not in eval/ , docs/test-reports/ or a CI run |
| Working-agreement audit counts of SG-3 to SG-6 (`docs/progress/gates.md`) | source not in eval/ , docs/test-reports/ or a CI run |
| Length of the course commitment and the sprint range of the Stage 2 position (`docs/stage2/README.md`) | source not in eval/ , docs/test-reports/ or a CI run |
| Count words such as "one transaction", "one hosted project" and "one per environment" (rules and configuration, not results) | source not in eval/ , docs/test-reports/ or a CI run |

## AI chapter (section 5)

To be added by the AI chapter part (Manya): one row per numeric claim of section 5, with its run record under `eval/results/<run>/`, its evaluation report or `docs/test-reports/cost-latency-report.md`.

## Presentation outline (docs/presentation/outline.md)

to be added by the presentation part

## Review

| Field | Value |
| --- | --- |
| Reviewer | Junaid |
| Date | pending |
| Result (every claim sourced: yes / no; rows changed) | pending |
