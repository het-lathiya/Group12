# IMP-804 · report-ai-chapter part

- Run id: RUN-087
- Owner: Manya (Manya Rana; part "Final report: AI chapter", 1 point)
- Status: PR_OPEN (draft; human completion and the claims-check review pending)
- Base commit: 4fe514cfa015f0b9ebd87c4a96c7daa04a4a2958 (`4fe514c`, `main`, the SG-7 release-candidate commit)
- Branch: chore/S7-D-gate-report (batch branch of RUN-087; card branch name `feat/IMP-804-<part>`)
- Traces to: US-148; NFR-041; TC-397
- Card steps built: 1 (the AI chapter of `docs/final-report.md`) and 2 (claims check of that chapter), drafted from repository artefacts under step 4. The data and architecture chapters are Malhar's part; the presentation is Jeel's part.

## Changed files

- `docs/final-report.md` (modified): section 5 "AI: provider, prompts, retrieval and evaluation" replaces the placeholder line "see AI chapter (Manya)"
- `docs/final-report-claims-check.md` (modified): subsection "AI chapter (section 5)" with rows 34 to 75 replaces the placeholder of that subsection
- `docs/progress/parts/IMP-804-report-ai-chapter.md` (created)

## Sources used

`eval/reports/final-baseline.md`, `eval/reports/baseline-1.md`, `eval/reports/RUN-079-prompt-v3.md`, the run records `eval/results/20261119T182737Z-mock/`, `20261119T182745Z-mock/`, `20261120T155153Z-rule_based/`, `20261120T165222Z-gemini/`, `20261114T104200Z-gemini/`, `20261116T042246Z-gemini/`, `20261113T114756Z-retrieval-mock/` and `20261119T182831Z-retrieval-mock/`, `docs/test-reports/cost-latency-report.md`, `docs/test-reports/e2e-sprint7.md`, `docs/model-change-log.md`, `docs/architecture.md` §3.3, §6, §7 and §9, `docs/guides/rag-corpus.md`, `docs/stage2/` (README and migration-gate criteria), `docs/progress/parts/IMP-705-whole-task.md`, `docs/progress/parts/IMP-706-whole-task.md`, `docs/spec/IMPLEMENTATION_SPEC.md` §8.3, §8.4, §8.13, `docs/spec/DECISION_REGISTER.md` (IMD-105, IMD-146, IMD-200, IMD-213), `apps/api/app/ai/breaker.py`, `apps/api/app/schemas/ai.py`, `apps/api/app/evaluation/run.py`, and CI runs 45037634091 and 45037634127.

## Commands run

All read only, 22 November 2026, in the main checkout at `4fe514c`. No evaluation was run and no model was called.

| Command | Result line (quoted exactly) |
| --- | --- |
| `python3` read of `metrics`, `failures`, `case_count`, `repeats`, `model_id`, `prompt_version` in the six generation `run.json` files | MOCK runs: every count k 45 / n 45, `avg_daily_travel_min` 126.7; rule-based: k 45 / n 45, 86.2; GEMINI v2: `schema_valid` 23/45, `place_ids_valid` 23/45, `usable` 23/45, `no_duplicate_places` 19/45, 119.4, 22 failures `provider_unavailable`; baseline-1: 44/45, 92.2; v3: 44/45, 41/45, 112.2 |
| `python3` sums over `scores.json` of the GEMINI v2 run | `23 completed`; `cases covered 12`; `dup items 8 rejected 8 invalid 0`; `COST_INCOMPLETE: 7, BUDGET_NEAR: 1`; tokens in `1471 4984`, out `314 1957` |
| `python3` latency and token statistics (nearest-rank p95) | GEMINI: `1775 7471.565217391304 19999 6608 12699`; `3739.478260869565 86008 992.9565217391304 22838`; MOCK `0 0.36 1` and `0 0.33 1`; rule-based `0 0.76 2` |
| `python3` comparison of the two MOCK `run.json` files | `True ['ended_at', 'run_id', 'started_at']` (metrics equal; only those fields differ) |
| `python3` read of the two retrieval `run.json` files | IMP-318: grounding 0.7571, citations 68; final: grounding 0.6392, citations 47; recall@6 0.7083, vector 0.6667, lexical 0.7083, validity 1.0, 12 vector-mode queries in both |
| `grep -n "FAILURES_TO_OPEN" apps/api/app/ai/breaker.py`; `grep -n "MAX_SOURCE_IDS" apps/api/app/schemas/ai.py` | `FAILURES_TO_OPEN: Final = 5`; `MAX_SOURCE_IDS = 3` (read to describe the rules; under the strict source rule their values are not stated in the report) |
| `gh run view 45037634127 --log` (provider-failure steps) | `1 passed (6.9s)`; `1 passed (7.4s)` |

## Not run

| Command | Reason |
| --- | --- |
| `make eval PROVIDER=GEMINI …`, `make live-smoke`, any Gemini or embedding call | Not allowed in this run (no live calls); the chapter reports only recorded runs |
| `make check` | This part changes only Markdown documents; the lead runs the checks before the commit |

## Acceptance criteria

| Criterion | Status (verified / not verified) | How |
| --- | --- | --- |
| Every numeric claim in the report and slides appears in the claims check with a linked record (US-148 AC1, TC-397) | verified (draft) for section 5 / review by Junaid pending | Rows 34 to 75 of `docs/final-report-claims-check.md`; every evaluation figure was recomputed from its `run.json` or `scores.json`, every cost and latency figure from `scores.json` and compared with `docs/test-reports/cost-latency-report.md`. TC-397 is a manual review by Junaid, not yet done |
| The presentation fits the time slot in rehearsal and states the Stage 2 position honestly (US-148 AC2) | n/a to this part | Presentation part (Jeel); rehearsal timing pending |
| AI quality, cost or speed claims link to a recorded run or are removed (card objective, NFR-041) | verified (draft) | Section 5 cites a run record for each figure; Gemini retrieval, money cost, end-to-end timing and staging results are stated as not measured |
| Known limitations of the AI path stated (CHK-19) | verified (draft) | §5.6 (Gemini availability 23 of 45, uncovered cases, no Gemini retrieval figure), §5.7 "Not measured", §5.9 |

## Blockers

- none for this draft.

## Proposed decisions

- none.

## Open issues

- Follow-up of the coordinator in RUN-087: the strict source rule (only `eval/results/`, `eval/reports/`, `docs/test-reports/` and CI run links) was applied after the first draft; six rows were removed from the AI claims and the chapter reworded (finding-code count, repair-call maximum, breaker thresholds, SAMPLE guide count, citation cap).

- The MOCK retrieval grounding rate fell from 0.7571 (`20261113T114756Z-retrieval-mock`) to 0.6392 (`20261119T182831Z-retrieval-mock`) and citations saved from 68 to 47. The records show two differences (commit; `embedded=189` against `embedded=227`); the cause has not been investigated.
- `docs/stage2/migration-gate-criteria.md` "Current reference values" still shows the final Gemini run as "not measured: no key in the run environment"; it should cite `20261120T165222Z-gemini` (23 of 45 completed) (owner Manya, IMP-706).
- Blueprint criteria E1 to E7 of the Stage 2 gate are still to be confirmed (Manya).
- No Gemini retrieval record exists; the one attempt ended HTTP 503 and was not re-run.

## Update of RUN-096 (batch H, 25 November 2026; this file existed and is modified)

- Owner: Manya. Branch `fix/RUN-096-batch-h`. Base commit: 5fa8e6d (on `main`). Status: PR_OPEN candidate. 0 points in this run.
- Changed files: `docs/final-report.md` section 5 only (prompt v4 row, the live dataset results, section 5.10); `docs/final-report-claims-check.md` rows 76 to 84, each "pending Junaid review"; this record.
- The sentence "no v4 exists in the repository" was out of date and is removed. Rows 34 to 75 are unchanged.
- Commands: `python3` read of `metrics` and `failures` in the seven IMP-732 `run.json` files; the values are those of the rows. The run checks on the branch head are in the SYNC REPORT of RUN-096.
- Acceptance: every new number has a row (**verified**); the operator's 503 probe is labelled as reported (**verified**); review of the claims check **not verified** — pending (Junaid).
- Proposed decisions: none. Blockers: none.
- Open issue: the chapter still describes the candidate `4fe514c` where it does not say otherwise; Manya brings it to the released commit after SG-7.
