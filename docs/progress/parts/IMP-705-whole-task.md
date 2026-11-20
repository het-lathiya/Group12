# IMP-705 · whole-task part

- Run ids: RUN-083 (MOCK and retrieval MOCK runs); RUN-083b (rule-based run, IMD-213)
- Owner: Nidhi (Nidhi Chauhan), 1 point; issue #152
- Status: PR_OPEN after RUN-083b. MOCK, retrieval MOCK and rule-based runs recorded and reported; the GEMINI runs were not made, and both reports say why (see Not run)
- Base commit: f75aa949fe306361d2f515ede632504518d19b63 (`main` after IMP-701 and IMP-702 merged, IMD-202); also the candidate commit of every run
- Branch: S7B/eval (batch branch; card branch name `feat/IMP-705-<short>`); RUN-083b: `feat/S7-B2-eval-finish`, base commit `964327f83c73e90f1309e0ecb3e7db82cda471c8`, rule-based run at `6993197` (the harness change of IMD-213 on that branch)
- Traces to: US-131; FR-120, FR-140; NFR-004, NFR-039, NFR-041; TC-386, TC-388 to TC-390, TC-392, TC-393, TC-396, TC-397, TC-458
- Card steps built: 1, 2, 5, 6 and 7 (MOCK). Step 3 and the GEMINI parts of steps 4 and 7 could not run (see Not run).

## Changed files

RUN-083b:

- `eval/results/20261120T155153Z-rule_based/run.json`, `eval/results/20261120T155153Z-rule_based/scores.json` (created): rule-based run, trips/v1
- `eval/reports/final-baseline.md`, `docs/test-reports/cost-latency-report.md`, this file (updated)

RUN-083:

- `eval/results/20261119T182737Z-mock/run.json`, `eval/results/20261119T182737Z-mock/scores.json` (created): first MOCK run, trips/v1
- `eval/results/20261119T182745Z-mock/run.json`, `eval/results/20261119T182745Z-mock/scores.json` (created): second MOCK run, trips/v1
- `eval/results/20261119T182831Z-retrieval-mock/run.json` (created): retrieval suite, MOCK
- `eval/reports/20261119T182831Z-retrieval-mock.md` (created): the report the harness wrote for that run, copied unchanged
- `eval/reports/final-baseline.md` (created)
- `docs/test-reports/cost-latency-report.md` (created)
- `docs/progress/parts/IMP-705-whole-task.md` (created)

The records were copied unchanged from the evaluation outputs. The `raw/` outputs were not committed, as for earlier runs. They are kept outside both worktrees in `/home/user/S7B-eval-runs/<run id>/` in the run container.

## How the runs were made

- Clean worktree `/home/user/wt-S7B-eval-main`, detached at `f75aa94`. `git status --porcelain` was empty before the first run. After each run its output folder (and, for the retrieval run, `eval/reports/<run id>.md`) was moved out, so every run started from a clean tree (IMD-176). The tree was empty again at the end.
- Environment: a Linux cloud container with the shared API virtual environment. `PYTHONPATH` was set to the worktree's `apps/api` so that its own code was imported, the HTTPS and HTTP proxy variables were unset, and `AI_PROVIDER=MOCK`. No Gemini key exists here, and no `.env` file was read.
- Retrieval database: `travel_eval` on the compose PostgreSQL 16 with pgvector, already migrated to `0007` with the auth stub, and empty before seeding.
- Prompt: the commands carry no `--prompt-version`, so trips/v1 runs the version each request names. The records state v1, not overridden (IMD-199). The active product version stays v2 (IMD-200) and was not changed.

## Commands run

| Command | Result line (quoted exactly) |
| --- | --- |
| `make eval PROVIDER=MOCK DATASET=trips/v1` (1, eval worktree) | `evaluation 20261119T182737Z-mock: 45 attempts, written to /home/user/wt-S7B-eval-main/eval/results/20261119T182737Z-mock` |
| `make eval PROVIDER=MOCK DATASET=trips/v1` (2, eval worktree) | `evaluation 20261119T182745Z-mock: 45 attempts, written to /home/user/wt-S7B-eval-main/eval/results/20261119T182745Z-mock` |
| `make eval PROVIDER=RULE_BASED DATASET=trips/v1` (eval worktree) | `rule-based planner not available (IMP-402)` / `make: *** [Makefile:172: eval] Error 2` |
| `make seed SEED_DIRS=data/places/ahmedabad` (eval worktree, `travel_eval`) | `seed sampleton: places inserted 30, updated 0, unchanged 0, deactivated 0` / `seed ahmedabad: places inserted 103, updated 0, unchanged 0, deactivated 0` |
| `make rag-index` (eval worktree, MOCK embeddings) | `rag-index: documents=151 chunks=227 embedded=227 inactive=0 warnings=0 errors=0` |
| `make eval DATASET=retrieval/v1 ARGS='--suite retrieval'` (eval worktree) | `evaluation 20261119T182831Z-retrieval-mock: 12 queries, written to /home/user/wt-S7B-eval-main/eval/results/20261119T182831Z-retrieval-mock` |
| Comparison of the two MOCK records (Python, parsed JSON) | `metrics identical: True`; scores equal except `latency_ms` |
| `diff -r 20261119T182737Z-mock/raw 20261119T182745Z-mock/raw` | no output (identical) |
| `grep -rliE 'api[_-]?key\|AIza\|secret\|password\|postgres:'` over all outputs | no match |
| `make test-unit ARGS='-k evaluation'` (part worktree) | `80 passed, 1130 deselected, 1 warning in 3.56s` |

## RUN-083b (20 November 2026)

- IMD-213 approved PD-IMP-705-1 and PD-IMP-705-2. Manya's harness change (`feat(eval): IMD-213 rule-based provider in the evaluation harness`) connects `--provider RULE_BASED` to `generation/fallback_planner.py`; no planner code, contract or migration changed.
- Clean worktree `/Users/nidhi/wt-S7B2-eval` of `6993197`, the main checkout's API virtual environment linked in (excluded locally, so `git status --porcelain` stayed empty). The output folder was moved to `/Users/nidhi/S7B2-eval-runs/` after the run; `run.json` and `scores.json` were copied unchanged, `raw/` was not committed.
- The Gemini key could not be checked: the run's permission rules block every command that reads `apps/api/.env`, and settings read `.env` from the working directory, so the key could not be confirmed or supplied to the worktree. No live call was made, so the daily cap is untouched.

| Command | Result line (quoted exactly) |
| --- | --- |
| `make test-unit ARGS='-k evaluation'` (after the harness change) | `85 passed, 1130 deselected, 1 warning in 1.74s` |
| `make eval PROVIDER=RULE_BASED DATASET=trips/v1` (eval worktree) | `evaluation 20261120T155153Z-rule_based: 45 attempts, written to /Users/nidhi/wt-S7B2-eval/eval/results/20261120T155153Z-rule_based` |
| `git diff --stat f75aa94..HEAD -- apps/api/app` | `apps/api/app/evaluation/run.py \| 92 ++++++++++++++++++++++++++++++++++++------` / `1 file changed, 80 insertions(+), 12 deletions(-)` |
| `grep -rliE 'api[_-]?key\|AIza\|secret\|password\|postgres:'` over the run output | no match |

| Not run (RUN-083b) | Reason |
| --- | --- |
| `make eval PROVIDER=GEMINI DATASET=trips/v1 ARGS='--prompt-version v2'` (card step 4, TC-392, IMD-213) | not run: the key could not be confirmed or supplied (permission rules block reading `apps/api/.env`) |
| `make eval DATASET=retrieval/v1 PROVIDER=GEMINI ARGS='--suite retrieval'` (card step 7, FR-140) | not run: same reason |

## Not run (RUN-083)

| Command | Reason |
| --- | --- |
| `make eval PROVIDER=GEMINI DATASET=trips/v1` (card step 4, TC-392) | not run: no key in the run environment. Nidhi runs it with the protected staging key within the daily cap |
| Retrieval suite with GEMINI (card step 7) | not run: no key in the run environment |
| Rule-based planner through the harness (card step 3, TC-393) | the harness refuses `RULE_BASED` (exit 2 above): `fallback_planner.py` exists, but `evaluation/run.py` was never connected to it (PD-IMP-413-2). Connecting them is a product code change, not allowed under the feature freeze (IMD-201) |
| `make check` | not run in this part: the part adds only records and documents (no code, contract or migration) |

## Acceptance criteria

| Criterion | Status (verified / not verified) | How |
| --- | --- | --- |
| Run records for MOCK (two), rule-based (one) and GEMINI (one) exist with dataset version, provider, model id, prompt and schema versions and commit SHA (FR-120, TC-390) | verified for MOCK and rule-based; GEMINI not verified | The two MOCK records (`git_commit` `f75aa94…`) and `20261120T155153Z-rule_based` (provider `RULE_BASED`, model `rule-based`, prompt version `not applicable`, gr-1 / io-1, dataset v1, `git_commit` `6993197…`) hold every listed field. No GEMINI record: not run in RUN-083 (no key) or RUN-083b (key not confirmed) |
| TC-393: the rule-based planner is measured through the same harness and metric code | verified | `20261120T155153Z-rule_based`: 45 / 45 schema-valid, valid IDs, usable and no duplicates, average daily travel 86.2 min, 0 failures; unit tests `tests/unit/evaluation/test_rule_based.py` (same metric code, no provider call, complete record) |
| TC-392: final GEMINI run on trips/v1 (prompt v2, IMD-213) | not verified | not run in RUN-083b: the key could not be confirmed or supplied; final-baseline.md says so and claims no GEMINI figure |
| final-baseline.md compares with the first baseline and every figure cites a run record (US-131 AC1, TC-397) | verified | `eval/reports/final-baseline.md`: comparison table against `20261114T104200Z-gemini`; every figure sits in a row or column that links its `run.json` |
| The cost and latency report contains no number without a run record (US-131 AC2, NFR-041) | verified | `docs/test-reports/cost-latency-report.md`: each figure names its `scores.json` (now with the rule-based run); everything else says "not measured" or "not applicable" |
| If the Gemini run could not be made (key, quota), the report says so and no Gemini figure is claimed | verified | Both reports mark every candidate GEMINI figure not measured, with the RUN-083 and RUN-083b reasons. The cost report quotes the earlier `20261116T042246Z-gemini` record only as a labelled earlier run, not as a candidate figure |
| The retrieval metrics of FR-140 are reported for MOCK and, if possible, GEMINI, each with a run record (TC-458) | verified (MOCK); GEMINI not verified | `20261119T182831Z-retrieval-mock`: recall@6, place hit rate (vector and lexical), citation validity and grounding rate in final-baseline.md. GEMINI: no key |
| Step 1 / TC-386: candidate SHA recorded; dataset unchanged | verified | `f75aa94…` in every record; `dataset_sha256` `8e0bde49…` equals baseline-1's, and the harness checked the manifest hash |
| Step 2 / ACC-14: two MOCK runs give identical metrics | verified | The `metrics` objects are equal; raw outputs identical |
| Card test command `make test-unit ARGS='-k evaluation'` (TC-388, TC-389) | command passed; TC-388 and TC-389 not verified by name | `80 passed, 1130 deselected, 1 warning in 3.56s`. The card names `tests/unit/evaluation/test_metrics.py`, which does not exist. The selection ran `test_dataset.py`, `test_harness.py`, `test_retrieval_metrics.py` and `test_run_record.py`; no test in `apps/api/tests` is tagged TC-388 or TC-389 |

## Blockers

- GEMINI runs (card steps 4 and 7) were not made in RUN-083 (no key) or RUN-083b (key not confirmed). If they are made later, once each with the key (rule 16), their records and figures are added in a follow-up.
- Resolved in RUN-083b: the rule-based run (IMD-213).

## Proposed decisions

Both decided by IMD-213 (20 November 2026).

- **PD-IMP-705-1: rule-based provider in the harness.** Allow a hardening change under IMD-201 that connects `--provider RULE_BASED` in `apps/api/app/evaluation/run.py` to `generation/fallback_planner.py`, with a unit test, so that TC-393 can run; otherwise record TC-393 as not met for the MVP. Owner: the evaluation module owner.
- **PD-IMP-705-2: prompt version of the final GEMINI run.** The card command runs trips/v1 with v1 (IMD-199), which is comparable with baseline-1 but is not the active v2. Decide whether Nidhi's final GEMINI run uses the card command as written (v1) or adds `ARGS='--prompt-version v2'` to measure the active version (one more run against the daily cap).

## Open issues

- The retrieval MOCK grounding rate (0.6392) and citations saved (47) are lower than in the IMP-318 MOCK records (0.7571, 68), with recall@6 and place hit rates unchanged. The commit and the index differ (IMP-318 quotes `embedded=189`, this run `embedded=227`). The cause was not investigated in this part.
- The card names `apps/api/tests/unit/evaluation/test_metrics.py`, which does not exist in the repository, and no test is tagged TC-388 or TC-389.
