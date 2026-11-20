# IMP-705 · whole-task part

- Run ids: RUN-083 (MOCK and retrieval MOCK runs); RUN-083b (rule-based run, IMD-213); RUN-083c (GEMINI prompt v2 run, run by the operator, committed and reported); RUN-083d (GEMINI retrieval attempt recorded)
- Owner: Nidhi (Nidhi Chauhan), 1 point; issue #152
- Status after RUN-083c: PR_OPEN. MOCK, retrieval MOCK, rule-based and GEMINI prompt v2 records committed and reported; GEMINI retrieval attempted and not possible, HTTP 503 (see RUN-083d). Status after RUN-083b: PR_OPEN. MOCK, retrieval MOCK and rule-based runs recorded and reported; the GEMINI runs were not made, and both reports say why (see Not run)
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
| `make eval DATASET=retrieval/v1 PROVIDER=GEMINI ARGS='--suite retrieval'` (card step 7, FR-140) | not run in RUN-083b; later attempted on 20 November 2026 (run by the operator), stopped with HTTP 503 at its first call, no record written, not re-run (see RUN-083d) |

## RUN-083c (20 November 2026)

- Branch `feat/S7-B2-eval-finish` at `41b521d` before this run; base `origin/main` `964327f`. No code changed in this run.
- The operator (Nidhi) ran the GEMINI evaluations herself in the evaluation worktree `/Users/nidhi/wt-S7B2-eval` at `6993197`. This run made no live call and read no `.env` file. `run.json` and `scores.json` of the committed run were copied unchanged (`cmp` reported no difference). `raw/` was not committed, as for earlier runs. The secret guard (`grep -rIlE 'AIza[0-9A-Za-z_-]{10,}|api_key"?\s*[:=]\s*"?[A-Za-z0-9]'`) over the run folder, `raw/` included, printed nothing. `test -e /Users/nidhi/wt-S7B2-eval/apps/api/.env` printed `ABSENT`.

| Command | Run by | Result (as recorded in the run folder) |
| --- | --- | --- |
| `make eval PROVIDER=GEMINI DATASET=trips/v1 ARGS='--prompt-version v2'`, attempt 1 | run by the operator | `20261120T163036Z-gemini`: 45 × `config_error` (the operator reports the old key was rejected, HTTP 401). Not committed; kept in `/Users/nidhi/S7B2-failed-runs/` |
| same, attempt 2 | run by the operator | `20261120T164419Z-gemini`: 45 × `config_error` (`GEMINI_MODEL_ID` still held the `.env.example` placeholder, which the record names as `model_id`). Not committed; kept in `/Users/nidhi/S7B2-failed-runs/` |
| same, attempt 3 | run by the operator | `20261120T165222Z-gemini` (committed): provider GEMINI, model `gemini-3.5-flash-lite`, prompt `itinerary_generate` v2 (`prompt_version_overridden` true), gr-2 / io-2, dataset trips v1 (`dataset_sha256` `8e0bde49…`), `git_commit` `6993197…`, metrics v2. 45 attempts: 23 completed, 22 `provider_unavailable`. The printed result line was not kept |
| `make eval DATASET=retrieval/v1 PROVIDER=GEMINI ARGS='--suite retrieval'` | run by the operator | `app.ai.errors.ProviderUnavailable: Gemini unavailable: HTTP 503` / `make: *** [Makefile:172: eval] Error 1`; no record written; not re-run (see RUN-083d) |

Figures of `20261120T165222Z-gemini`, read from its `run.json` and `scores.json`:

- Availability: 23 / 45 completed; 22 `provider_unavailable`, spread through the run (Gemini service errors, not quota); 12 of 15 cases have at least one completed attempt (none for `trips-v1-002`, `003`, `012`).
- Quality over the 23 completed attempts only: schema-valid 23 / 23, valid IDs 23 / 23, usable 23 / 23, no duplicates 19 / 23, average daily travel 119.4 min.
- All 23 completed attempts carry input and output tokens (input 1471 to 4984, output 314 to 1957). Every completed answer has item notes and none has the rule-based summary, so this is model output, not the fallback planner.
- Latency over the completed attempts: min 1775, median 6608, mean 7471.6, p95 12699, max 19999 ms.

| Command (RUN-083c) | Result line (quoted exactly) |
| --- | --- |
| `make test-unit ARGS='-k evaluation'` | `85 passed, 1130 deselected, 1 warning in 1.64s` |
| `make check` | exit 0: `All checks passed!`; `Success: no issues found in 123 source files`; `Contracts: 6 kept, 0 broken.`; `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date`; `1215 passed, 1 warning in 8.84s`; `91 passed, 2 deselected, 1 warning in 18.48s`; `590 passed, 1 warning in 113.48s (0:01:53)`; `87 passed, 14 skipped, 1 warning in 22.17s`; `Test Files  43 passed (43)`; `Tests  288 passed (288)` |

Acceptance after RUN-083c:

| Criterion | Status | How |
| --- | --- | --- |
| FR-120 / TC-390: run records for MOCK (two), rule-based (one) and GEMINI (one) with dataset version, provider, model id, prompt and schema versions and commit SHA | verified | `20261119T182737Z-mock`, `20261119T182745Z-mock`, `20261120T155153Z-rule_based`, `20261120T165222Z-gemini`: each holds every listed field |
| TC-392: final GEMINI run on trips/v1 with prompt v2 (IMD-213) | verified, with a caveat | `20261120T165222Z-gemini` ran prompt v2 once to completion of the run, but only 23 of 45 attempts completed (22 `provider_unavailable`). Quality figures are over the completed attempts only, and both reports say so |
| US-131 AC1 / AC2, NFR-041: every figure cites a run record | verified | `eval/reports/final-baseline.md` and `docs/test-reports/cost-latency-report.md`: every GEMINI figure names `20261120T165222Z-gemini` |
| FR-140 / TC-458 retrieval metrics with GEMINI | not possible (HTTP 503), no figure claimed | the one attempt stopped at its first call with HTTP 503 and wrote no record (RUN-083d) |

Blockers after RUN-083c: none (the GEMINI retrieval attempt is recorded in RUN-083d).

## RUN-083d (20 November 2026)

Docs correction; no code, figure or record changed. Fact from the operator (no record folder exists):

- Command: `make eval DATASET=retrieval/v1 PROVIDER=GEMINI ARGS='--suite retrieval'`, run by the operator once on 20 November 2026 at about 23:10 IST in `/Users/nidhi/wt-S7B2-eval` at commit `6993197`, with `GEMINI_EMBEDDING_MODEL_ID=gemini-embedding-2`.
- Result: it stopped at its first call with `app.ai.errors.ProviderUnavailable: Gemini unavailable: HTTP 503` / `make: *** [Makefile:172: eval] Error 1`, and wrote no results folder.
- Cause: a Gemini service error (HTTP 503), not quota and not a missing key. It was not re-run (rule 16, minimum live calls).
- Effect: the card asks for GEMINI retrieval metrics "if possible" (TC-458). GEMINI retrieval was not possible, so only the MOCK retrieval figures (`20261119T182831Z-retrieval-mock`) are claimed. The card criterion is verified (MOCK reported with record; GEMINI attempted, not possible: HTTP 503).

| Command (RUN-083d) | Result line (quoted exactly) |
| --- | --- |
| `make lint` | exit 0: `All checks passed!`; `All matched files use Prettier code style!` |
| `make test-unit ARGS='-k evaluation'` | `85 passed, 1130 deselected, 1 warning in 1.51s` |

## Not run (RUN-083)

| Command | Reason |
| --- | --- |
| `make eval PROVIDER=GEMINI DATASET=trips/v1` (card step 4, TC-392) | not run: no key in the run environment. Nidhi runs it with the protected staging key within the daily cap |
| Retrieval suite with GEMINI (card step 7) | not run in RUN-083: no key in the run environment; later attempted on 20 November 2026 (run by the operator), stopped with HTTP 503 at its first call, no record written, not re-run (see RUN-083d) |
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
| The retrieval metrics of FR-140 are reported for MOCK and, if possible, GEMINI, each with a run record (TC-458) | verified (MOCK reported with record; GEMINI attempted, not possible: HTTP 503) | `20261119T182831Z-retrieval-mock`: recall@6, place hit rate (vector and lexical), citation validity and grounding rate in final-baseline.md. GEMINI: one attempt on 20 November 2026 stopped with HTTP 503 and wrote no record (RUN-083d) |
| Step 1 / TC-386: candidate SHA recorded; dataset unchanged | verified | `f75aa94…` in every record; `dataset_sha256` `8e0bde49…` equals baseline-1's, and the harness checked the manifest hash |
| Step 2 / ACC-14: two MOCK runs give identical metrics | verified | The `metrics` objects are equal; raw outputs identical |
| Card test command `make test-unit ARGS='-k evaluation'` (TC-388, TC-389) | command passed; TC-388 and TC-389 not verified by name | `80 passed, 1130 deselected, 1 warning in 3.56s`. The card names `tests/unit/evaluation/test_metrics.py`, which does not exist. The selection ran `test_dataset.py`, `test_harness.py`, `test_retrieval_metrics.py` and `test_run_record.py`; no test in `apps/api/tests` is tagged TC-388 or TC-389 |

## Blockers

- None open. (Resolved: the GEMINI trips run is `20261120T165222Z-gemini`, RUN-083c; the GEMINI retrieval attempt stopped with HTTP 503 and is recorded in RUN-083d.)
- Resolved in RUN-083b: the rule-based run (IMD-213).

## Proposed decisions

Both decided by IMD-213 (20 November 2026).

- **PD-IMP-705-1: rule-based provider in the harness.** Allow a hardening change under IMD-201 that connects `--provider RULE_BASED` in `apps/api/app/evaluation/run.py` to `generation/fallback_planner.py`, with a unit test, so that TC-393 can run; otherwise record TC-393 as not met for the MVP. Owner: the evaluation module owner.
- **PD-IMP-705-2: prompt version of the final GEMINI run.** The card command runs trips/v1 with v1 (IMD-199), which is comparable with baseline-1 but is not the active v2. Decide whether Nidhi's final GEMINI run uses the card command as written (v1) or adds `ARGS='--prompt-version v2'` to measure the active version (one more run against the daily cap).

## Open issues

- The retrieval MOCK grounding rate (0.6392) and citations saved (47) are lower than in the IMP-318 MOCK records (0.7571, 68), with recall@6 and place hit rates unchanged. The commit and the index differ (IMP-318 quotes `embedded=189`, this run `embedded=227`). The cause was not investigated in this part.
- The card names `apps/api/tests/unit/evaluation/test_metrics.py`, which does not exist in the repository, and no test is tagged TC-388 or TC-389.
