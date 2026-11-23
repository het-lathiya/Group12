# Final report claims check

**Draft — RUN-087, 22 November 2026; manual review by Junaid pending**

| Item | Value |
| --- | --- |
| Checks | [final-report.md](final-report.md) (draft of 22 November 2026, `main` at `4fe514c`) |
| Card | IMP-804 (US-148 AC1); test TC-397; NFR-041 |
| Reviewer | Junaid (manual review, no automated command) — **pending** |
| Prepared by | Malhar (data and architecture chapters); Manya (AI chapter rows); Jeel (presentation outline rows) |

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

Rows for the numeric claims of section 5 (Manya's part). Numbering continues from the data and architecture rows (last row 33). Under the strict source rule of RUN-087 every number comes only from `eval/results/`, `eval/reports/`, `docs/test-reports/` or a CI run link. Each value was opened in its run record (`run.json` or `scores.json`, parsed as JSON), in the evaluation or test report, or in the CI log, and compared on 22 November 2026.

| # | Claim (exact text as it appears) | Location (file + section) | Source (eval/, docs/test-reports/ path or CI run link) | Checked value |
| --- | --- | --- | --- | --- |
| 34 | "`Contracts: 6 kept, 0 broken.`" | final-report.md §5.2 | [CI 45037634091](https://github.com/het-lathiya/Group12/actions/runs/45037634091), job `lint-types`, `make imports` | `Contracts: 6 kept, 0 broken.` |
| 35 | "model `gemini-3.5-flash-lite`, adapter `gemini-interactions-1`, structured output, thinking level minimal" | final-report.md §5.2 | `eval/results/20261120T165222Z-gemini/run.json` (`model_id`, `adapter_version`, `generation_settings`) | `gemini-3.5-flash-lite`; `gemini-interactions-1`; `structured_output: true`, `thinking_level: minimal`, `api_style: interactions`, `timeout_s: 35.0` |
| 36 | "timeout `1 passed (6.9s)`, quota `1 passed (7.4s)`" | final-report.md §5.3 | [E2E 45037634127](https://github.com/het-lathiya/Group12/actions/runs/45037634127), steps "Run provider failure with a timeout" and "… with quota exhausted" | `1 passed (6.9s)`; `1 passed (7.4s)` |
| 37 | "usable outputs 44 / 45, 1 failure (`schema_violation`)" (baseline-1, v1) | final-report.md §5.4 | `eval/results/20261114T104200Z-gemini/run.json` | `usable` k 44, n 45; `failures` 1: `trips-v1-010`, repeat 2, `schema_violation` |
| 38 | "492 of the 557 item notes start with \"AI-written:\"" | final-report.md §5.4 | `eval/reports/baseline-1.md` (finding 1) | "492 of the 557 item notes start with \"AI-written:\"" |
| 39 | "88 items reuse a place already in the plan" | final-report.md §5.4 | `eval/reports/baseline-1.md` (finding 2) | "88 items reuse a place already in the same plan: 87 meal slots and 1 activity" |
| 40 | "Gemini usable 44 / 45 and 0 of 564 notes with \"AI-written\"" (v3) | final-report.md §5.4 | `eval/results/20261116T042246Z-gemini/run.json`; `eval/reports/RUN-079-prompt-v3.md` | `usable` k 44, n 45; report: "0 of 564" |
| 41 | "14 duplicate-place items in 3 attempts" (v3) | final-report.md §5.4 | `eval/results/20261116T042246Z-gemini/scores.json` (`duplicate_places`); `eval/reports/RUN-079-prompt-v3.md` | sum 14: `trips-v1-003` r2 (3), `trips-v1-007` r2 (1), `trips-v1-012` r2 (10) |
| 42 | "15 cases × 3 repeats = 45 attempts per run" | final-report.md §5.6 | `eval/results/20261119T182737Z-mock/run.json`, `…182745Z-mock`, `…155153Z-rule_based`, `…165222Z-gemini` (`case_count`, `repeats`, `metrics.attempts`) | `case_count` 15, `repeats` 3, `attempts` 45 in all four |
| 43 | MOCK run 1 column: "45 / 45" (completed, schema-valid, valid IDs, usable, no duplicates) and "126.7" | final-report.md §5.6 table | `eval/results/20261119T182737Z-mock/run.json` (`metrics`), `scores.json` | every count k 45, n 45; `avg_daily_travel_min` 126.7; `failures` [] |
| 44 | MOCK run 2 column: "45 / 45" and "126.7" | final-report.md §5.6 table | `eval/results/20261119T182745Z-mock/run.json` | every count k 45, n 45; `avg_daily_travel_min` 126.7; `failures` [] |
| 45 | Rule-based column: "45 / 45" and "86.2" | final-report.md §5.6 table | `eval/results/20261120T155153Z-rule_based/run.json` | every count k 45, n 45; `avg_daily_travel_min` 86.2; `failures` [] |
| 46 | Gemini column: "**23 / 45** (22 `provider_unavailable`)" | final-report.md §5.6 table and text | `eval/results/20261120T165222Z-gemini/run.json` (`failures`), `scores.json` (`error`) | 22 failures, all `provider_unavailable`; 23 rows with `error` null |
| 47 | Gemini column: "23 / 23 completed (23 / 45 in the record)" (schema-valid, valid IDs, usable) | final-report.md §5.6 table | `eval/results/20261120T165222Z-gemini/run.json` (`metrics.counts`), `scores.json` | `schema_valid`, `place_ids_valid`, `usable`: k 23, n 45; true in all 23 completed rows |
| 48 | Gemini column: "19 / 23 completed (19 / 45 in the record)" (no duplicates) | final-report.md §5.6 table | same | `no_duplicate_places` k 19, n 45 |
| 49 | Gemini column: "119.4 (completed attempts only)" | final-report.md §5.6 table; also "119.4 against 92.2" | `eval/results/20261120T165222Z-gemini/run.json` | `avg_daily_travel_min` 119.4 |
| 50 | "so 12 of the 15 cases are covered" and "Three cases (`trips-v1-002`, `003`, `012`) have no completed attempt" | final-report.md §5.6 | `eval/results/20261120T165222Z-gemini/scores.json` | 12 distinct `case_id` values among completed rows; `002`, `003`, `012` failed in all three repeats |
| 51 | "no invalid place ID, 8 duplicate-place items, all 8 rejected by the output check" | final-report.md §5.6 | `eval/results/20261120T165222Z-gemini/scores.json` | sum `invalid_ids` 0; sum `duplicate_places` 8; sum `rejected_items` 8 |
| 52 | "`COST_INCOMPLETE` 7 and `BUDGET_NEAR` 1" | final-report.md §5.6 | `eval/results/20261120T165222Z-gemini/scores.json` (`findings`) | `COST_INCOMPLETE` 7, `BUDGET_NEAR` 1 |
| 53 | "`COST_INCOMPLETE` in 15 of 45 attempts (five cases, every repeat)" (rule-based) | final-report.md §5.6 | `eval/results/20261120T155153Z-rule_based/scores.json`; `eval/reports/final-baseline.md` | 15 attempts; cases `003`, `007`, `012`, `014`, `015`, repeats 1 to 3 |
| 54 | "the `metrics` objects of the two records are identical and their raw outputs are identical" | final-report.md §5.6 | `eval/reports/final-baseline.md` "Reproducibility"; the two `run.json` files | `metrics` equal when parsed (checked again in this run); raw outputs: "`diff -r` printed nothing" (report) |
| 55 | "usable 44 / 45, average daily travel 92.2 minutes" (baseline-1) | final-report.md §5.6 | `eval/results/20261114T104200Z-gemini/run.json` | `usable` k 44, n 45; `avg_daily_travel_min` 92.2 |
| 56 | "45 attempts of 15 cases against 23 attempts of 12 cases" | final-report.md §5.6 | `eval/results/20261114T104200Z-gemini/run.json`; `eval/results/20261120T165222Z-gemini/scores.json` | 45 attempts, `case_count` 15; 23 completed rows over 12 cases |
| 57 | "The numbered metrics 1 to 13 are not computed" | final-report.md §5.6 | `metrics.numbered` in each `run.json` above | keys "1" to "13", every `value` null with a `status` reason |
| 58 | "`retrieval/v1`, 12 queries, 6 per destination" | final-report.md §5.6 | `eval/results/20261119T182831Z-retrieval-mock/run.json` (`metrics.overall.queries`, `metrics.by_destination`) | overall `queries` 12; ahmedabad 6, sampleton 6 |
| 59 | recall@6 "0.7083" / "0.7083" | final-report.md §5.6 retrieval table | `eval/results/20261113T114756Z-retrieval-mock/run.json`; `eval/results/20261119T182831Z-retrieval-mock/run.json` (`metrics.overall.recall_at_6`) | 0.7083; 0.7083 |
| 60 | Place hit rate, vector "0.6667" / "0.6667" | same table | same (`place_hit_rate_vector`) | 0.6667; 0.6667 |
| 61 | Place hit rate, lexical "0.7083" / "0.7083" | same table | same (`place_hit_rate_lexical`) | 0.7083; 0.7083 |
| 62 | Citation validity "1.0" / "1.0" | same table and text | same (`citation_validity`) | 1.0; 1.0 |
| 63 | Grounding rate "0.7571" / "**0.6392**"; "fell from 0.7571 to 0.6392" | same table and text | same (`grounding_rate`) | 0.7571; 0.6392 |
| 64 | Citations saved "68" / "47"; "from 68 to 47" | same table and text | same (`citations_saved`) | 68; 47 |
| 65 | Queries in vector mode "12 of 12" / "12 of 12" | same table | same (`vector_mode_queries`) | 12; 12 |
| 66 | "the top 12" (place hit rate) | same table | same (`k.place_top`) | 12 (`k`: `guide_recall` 6, `place_top` 12) |
| 67 | "recall@6 is 0.4167 for Ahmedabad and 1.0 for Sampleton" | final-report.md §5.6 | `eval/results/20261119T182831Z-retrieval-mock/run.json` (`metrics.by_destination`) | ahmedabad 0.4167; sampleton 1.0 |
| 68 | "the IMP-318 record quotes `embedded=189`, the final run's index printed `embedded=227`" | final-report.md §5.6 | `eval/reports/final-baseline.md` "Retrieval suite" and "Candidate and conditions" | `embedded=189` (IMP-318 part record, as quoted); `embedded=227` |
| 69 | "stopped at its first call with `Gemini unavailable: HTTP 503`" | final-report.md §5.6 | `eval/reports/final-baseline.md` run table; `docs/progress/parts/IMP-705-whole-task.md` RUN-083d | `app.ai.errors.ProviderUnavailable: Gemini unavailable: HTTP 503`; no record written |
| 70 | Gemini latency "1775 / 7471.6 / 19999 (median 6608, p95 12699)" | final-report.md §5.7 | `docs/test-reports/cost-latency-report.md`; `eval/results/20261120T165222Z-gemini/scores.json` (`latency_ms`, 23 values) | report: 1775 / 7471.6 / 19999, median 6608, p95 12699; recomputed in this run: min 1775, mean 7471.57, max 19999, median 6608, nearest-rank p95 12699 |
| 71 | "mean 3739.5 (1471 to 4984); 86008 in total" (input tokens) | final-report.md §5.7 | same files (`input_tokens`) | report values; recomputed: mean 3739.48, min 1471, max 4984, sum 86008 over 23 attempts |
| 72 | "mean 993.0 (314 to 1957); 22838 in total" (output tokens) | final-report.md §5.7 | same files (`output_tokens`) | report values; recomputed: mean 992.96, min 314, max 1957, sum 22838 |
| 73 | Rule-based latency "0 / 0.76 / 2" | final-report.md §5.7 | `docs/test-reports/cost-latency-report.md`; `eval/results/20261120T155153Z-rule_based/scores.json` | 0 / 0.76 / 2 (recomputed) |
| 74 | MOCK latency "0 / 0.36 / 1 and 0 / 0.33 / 1" | final-report.md §5.7 | `docs/test-reports/cost-latency-report.md`; the two MOCK `scores.json` files | 0 / 0.36 / 1; 0 / 0.33 / 1 (recomputed) |
| 75 | "the latency of the 22 failed Gemini attempts" (not measured) | final-report.md §5.7 | `docs/test-reports/cost-latency-report.md` "Not measured"; `scores.json` | 22 rows with `latency_ms` null |

Claims of section 5 removed or reworded so that the prose carries no number:

| Claim considered | Why it was left out |
| --- | --- |
| Number of finding codes (`docs/srs.md`) | source not in eval/ , docs/test-reports/ or a CI run |
| Maximum number of model repair calls (specification §8.13) | source not in eval/ , docs/test-reports/ or a CI run; reworded as "a single bounded model repair call" |
| Number of consecutive failures that opens the circuit breaker (`app/ai/breaker.py`, IMD-146), and the number of quota or authorization errors that opens it | source not in eval/ , docs/test-reports/ or a CI run |
| Number of synthetic SAMPLE guides (`data/fixtures/sampleton/guides/`) | source not in eval/ , docs/test-reports/ or a CI run |
| Maximum number of cited passage IDs per item (`MAX_SOURCE_IDS` in `app/schemas/ai.py`, A1 §6.10) | source not in eval/ , docs/test-reports/ or a CI run; the cap is named without its value |
| Per-attempt timeout and time allowances of the pipeline; embedding dimension and chunk sizes | specification rules and configuration constants, not results; not needed |
| Gemini retrieval figures; money cost of Gemini calls; staging generation figures | no record (HTTP 503 attempt wrote none; no dated price table; no staging record on the candidate) |

## Presentation outline (docs/presentation/outline.md)

Rows for the numeric claims of [presentation/outline.md](presentation/outline.md) (Jeel's part, draft of 22 November 2026). The outline takes every figure from [final-report.md](final-report.md), including section 5, under the same strict source rule; each row names the report section and the row of this file that holds the source record (rows 1 to 33 for sections 1 to 4 and 6 to 10, rows 34 to 75 for section 5). The checked value is the figure as the report states it, compared on 22 November 2026. Identifiers, migration numbers, version numbers, HTTP status codes, section and slide numbers and calendar dates are not claims, as above.

| # | Claim (exact text as it appears) | Location (file + section) | Source (eval/, docs/test-reports/ path or CI run link) | Checked value |
| --- | --- | --- | --- | --- |
| O1 | "floor journey `1 passed (14.7s)` on the candidate" | outline.md Slide 4 (on slide) | final-report.md §2.2, §6.1; row 2 ([E2E 45037634127](https://github.com/het-lathiya/Group12/actions/runs/45037634127)) | "`1 passed (14.7s)`" |
| O2 | "Ahmedabad with 103 curated places" | outline.md Slide 4 (on slide) | final-report.md §3; row 4 (`eval/reports/final-baseline.md`) | "**103** places loaded" |
| O3 | "final evaluation index of 151 documents and 227 chunks" | outline.md Slide 4 (on slide) | final-report.md §3; row 5 (`eval/reports/final-baseline.md`) | "**151** documents and **227** chunks, all embedded" |
| O4 | "`Contracts: 6 kept, 0 broken.`" | outline.md Slide 6 (on slide) | final-report.md §4.1, §5.2, §6.1; rows 6 and 34 ([CI 45037634091](https://github.com/het-lathiya/Group12/actions/runs/45037634091), job `lint-types`) | "`Contracts: 6 kept, 0 broken.`" |
| O5 | "15 cases × 3 repeats = 45 attempts per run" | outline.md Slide 7 (on slide) | final-report.md §5.6; row 42 (the four generation `run.json` files) | "15 cases × 3 repeats = 45 attempts per run" |
| O6 | "23 of 45 attempts completed (22 `provider_unavailable`)" | outline.md Slide 7 (on slide) | final-report.md §5.6; row 46 (`eval/results/20261120T165222Z-gemini/`) | "**23 / 45** (22 `provider_unavailable`)"; "Only 23 of the 45 attempts completed; 22 ended `provider_unavailable`" |
| O7 | "all 23 completed attempts usable" | outline.md Slide 7 (on slide) | final-report.md §5.6 table; row 47 (`eval/results/20261120T165222Z-gemini/`) | Usable "23 / 23 completed (23 / 45 in the record)" |
| O8 | "8 duplicate-place items, all rejected by the output check" | outline.md Slide 7 (on slide) | final-report.md §5.6; row 51 (`eval/results/20261120T165222Z-gemini/scores.json`) | "8 duplicate-place items, all 8 rejected by the output check" |
| O9 | "Rule-based planner 45 / 45 usable" | outline.md Slide 7 (on slide) | final-report.md §5.6 table; row 45 (`eval/results/20261120T155153Z-rule_based/run.json`) | Rule-based column "45 / 45" |
| O10 | "MOCK runs 45 / 45 and identical, so the harness is reproducible" | outline.md Slide 7 (on slide) | final-report.md §5.6; rows 43, 44 and 54 (the two MOCK `run.json` files; `eval/reports/final-baseline.md`) | "Both runs score 45 / 45 on every count; the `metrics` objects of the two records are identical and their raw outputs are identical, so the harness is reproducible" |
| O11 | "citation validity 1.0" | outline.md Slide 7 (on slide) | final-report.md §5.6 retrieval table; row 62 (`eval/results/20261119T182831Z-retrieval-mock/run.json`) | Citation validity "1.0" (final MOCK) |
| O12 | "grounding rate fell from 0.7571 to 0.6392, recorded but not investigated" | outline.md Slide 7 (on slide) | final-report.md §5.6; row 63 (the two retrieval `run.json` files) | "The grounding rate fell from 0.7571 to 0.6392 … This drop is recorded but not investigated." |
| O13 | "Gemini retrieval not possible (HTTP 503)" | outline.md Slide 7 (on slide) | final-report.md §5.6; row 69 (`eval/reports/final-baseline.md`) | "stopped at its first call with `Gemini unavailable: HTTP 503`" |
| O14 | "only 12 of the 15 cases have a completed attempt" and "the three uncovered cases" | outline.md Slide 7 (notes) | final-report.md §5.6; row 50 (`eval/results/20261120T165222Z-gemini/scores.json`) | "Three cases … have no completed attempt, so 12 of the 15 cases are covered"; "say nothing about the three uncovered cases" |
| O15 | "Gemini provider-call latency over the 23 completed attempts: mean 7471.6 ms (median 6608, p95 12699)" | outline.md Slide 7 (notes) | final-report.md §5.7; row 70 (`docs/test-reports/cost-latency-report.md`, `eval/results/20261120T165222Z-gemini/scores.json`) | "1775 / 7471.6 / 19999 (median 6608, p95 12699)" over "23 completed attempts" |
| O16 | "unit 1215 passed" | outline.md Slide 8 (on slide) | final-report.md §6.1; row 8 (CI 45037634091, job `unit`) | "`1215 passed, 1 warning in 13.52s`" |
| O17 | "provider and API contract 91 passed" | outline.md Slide 8 (on slide) | final-report.md §6.1; row 9 (CI 45037634091, job `unit`) | "`91 passed, 2 deselected, 1 warning in 18.14s`" |
| O18 | "API and database 590 passed" | outline.md Slide 8 (on slide) | final-report.md §6.1; row 10 (CI 45037634091, job `api`) | "`590 passed, 1 warning in 214.57s (0:03:34)`" |
| O19 | "authorization 87 passed (14 skipped)" | outline.md Slide 8 (on slide) | final-report.md §6.1; row 11 (CI 45037634091, job `api`) | "`87 passed, 14 skipped, 1 warning in 44.23s`" |
| O20 | "web components 288 passed" | outline.md Slide 8 (on slide) | final-report.md §6.1; row 12 (CI 45037634091, job `unit`) | "`Tests  288 passed (288)`" |
| O21 | "journey at four widths `4 passed (40.8s)`" | outline.md Slide 8 (on slide) | final-report.md §6.1; row 17 ([E2E 45037634127](https://github.com/het-lathiya/Group12/actions/runs/45037634127); widths from `docs/test-reports/e2e-sprint7.md`) | "Journey (four widths) · `4 passed (40.8s)`" |
| O22 | "three consecutive local full runs of 119 tests" | outline.md Slide 8 (on slide) | final-report.md §6.2; rows 23 and 24 (`docs/test-reports/e2e-sprint7.md` §4) | "three consecutive local full runs … each `Running 119 tests using 2 workers`" |
| O23 | "0 of 3 failed" | outline.md Slide 8 (on slide) | final-report.md §6.2; row 27 (`docs/test-reports/e2e-sprint7.md` §4) | "**0 of 3** full runs failed" |
| O24 | "finding F-1 (severity 3) fixed; no severity 1 or 2 defect" | outline.md Slide 8 (on slide) | final-report.md §6.3; row 30 (`docs/test-reports/security-sprint7.md`) | "Finding F-1 (…; severity 3) was fixed"; "No severity 1 or 2 defect was found" |
| O25 | "40 + 20 automated axe scans, no serious or critical violation" | outline.md Slide 8 (on slide) | final-report.md §6.4; rows 31 and 32 (`docs/test-reports/accessibility-sprint7.md` §6.1b) | "**40** axe scans"; "**20** scans, every scan `[]`"; "no serious or critical violation" |
| O26 | "Coverage 92% for `app`, reported but not enforced" | outline.md Slide 8 (on slide) | final-report.md §6.1; row 14 (CI 45037634091, job `api`) | "`TOTAL … 92%` for `app`; no threshold fails the build" |
| O27 | "`no leaks found` over `445 commits scanned.`" | outline.md Slide 8 (notes) | final-report.md §6.1; row 16 (CI 45037634091, job `guards`) | "gitleaks `445 commits scanned.`, `no leaks found`" |
| O28 | "Prompt v3 not active (14 duplicate-place items in 3 attempts)" | outline.md Slide 9 (on slide) | final-report.md §5.4; row 41 (`eval/results/20261116T042246Z-gemini/scores.json`, `eval/reports/RUN-079-prompt-v3.md`) | "14 duplicate-place items in 3 attempts, so the IMD-195 activation gate was **not met**" |

Numbers considered for the outline and left out, because the report no longer states them (removed under the strict source rule; see "Claims removed while drafting" above): the count and MVP / MVP-S split of requirements Done at SG-6; the number of API operations; the number of extensions and cut-list switches; the minimum of usable Ahmedabad places; the number of Ahmedabad guides; the number of tables; the maximum number of model repair calls; the maximum number of cited passage IDs; the working-agreement audit counts; the length of the course commitment and the sprint range of the Stage 2 position. Team point totals were not used (the report states none). No rehearsal timing, slot length, demo result or participant feedback exists to quote.

## Claims of the any-city chapter (section 11; RUN-092, 23 November 2026)

| # | Claim (exact text as it appears) | Location (file + section) | Source (eval/, docs/test-reports/ path or CI run link) | Checked value |
| --- | --- | --- | --- | --- |
| A1 | "usable plans in 24/24 MOCK attempts and 24/24 rule-based attempts" | final-report.md §11 | `eval/results/20261123T171053Z-mock/scores.json`, `eval/results/20261123T171053Z-rule_based/scores.json`; `eval/reports/live-v1-2026-11-23.md` | `usable` true in 24 of 24 entries in each file |
| A2 | "Every planned live place had an unknown price" | final-report.md §11 | `eval/reports/live-v1-2026-11-23.md` "Results" (unknown-price share) | "219 of 219" (MOCK), "216 of 216" (RULE_BASED) |
| A3 | "two inventory or start-up-configuration authz tests failed beyond the four that A2 §3.4 names" | final-report.md §11 | `docs/test-reports/any-city-switch.md` "Result lines" | switch ON authz "2 failed, 84 passed, 14 skipped, 1 deselected, 1 warning in 25.23s" |

"The four that A2 §3.4 names" counts the tests named in the amendment's own text (a specification reference, not a measured result).

## Review

| Field | Value |
| --- | --- |
| Reviewer | Junaid |
| Date | pending |
| Result (every claim sourced: yes / no; rows changed) | pending |
