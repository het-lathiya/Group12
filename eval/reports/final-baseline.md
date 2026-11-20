# Final baseline · release-candidate evaluation over trips/v1 and retrieval/v1

IMP-705 (US-131; FR-120, FR-140; NFR-004, NFR-039, NFR-041). Owner: Nidhi. Compared with the first baseline, [`baseline-1.md`](baseline-1.md).

## Candidate and conditions

- Candidate commit: `f75aa949fe306361d2f515ede632504518d19b63` (`f75aa94`), `main` after IMP-701 and IMP-702 merged (card step 1, IMD-202). The MOCK records below hold this `git_commit`.
- Rule-based run (RUN-083b, 20 November 2026, IMD-213): commit `6993197fd059a8d4fee4ab0b7824625cd4f75e33` (`6993197`), the head of `feat/S7-B2-eval-finish` after the harness change. Product code is unchanged between `f75aa94` and this commit apart from the evaluation harness: `git diff --stat f75aa94..HEAD -- apps/api/app` printed `apps/api/app/evaluation/run.py | 92 ++++++++++++++++++++++++++++++++++++------` and `1 file changed, 80 insertions(+), 12 deletions(-)`. The planner, validation, schedule, budget and metric code the scores come from is the candidate's.
- Dates: 19 November 2026 (MOCK, RUN-083) and 20 November 2026 (rule-based, RUN-083b; GEMINI prompt v2, run by the operator, recorded in RUN-083c); UTC times are in each record.
- All runs started from a clean evaluation worktree detached at the candidate commit (IMD-176). After each run its output folder was moved out of that worktree, so the next run started from a clean tree again; `git status --porcelain` was empty after the last move.
- Environment of the MOCK runs: a Linux cloud container, the shared API virtual environment, proxy variables unset, `AI_PROVIDER=MOCK`. No Gemini key exists in this environment.
- Environment of the rule-based run: macOS, a clean worktree `../wt-S7B2-eval` of `6993197` (`git status --porcelain` empty before and after the run, the output folder moved out after it), the API virtual environment of the main checkout linked in. The rule-based path builds no provider and needs no database or key.
- Environment of the GEMINI run (run by the operator, Nidhi, 20 November 2026, 16:52 to 17:00 UTC): the same worktree at `6993197`, `gemini-3.5-flash-lite`, adapter `gemini-interactions-1`, settings as recorded (`api_style` interactions, structured output, thinking level minimal, timeout 35 s). The record's `git_commit` is `6993197…`.
- Retrieval database: the compose PostgreSQL 16 with pgvector, migrated to `0007`, seeded with `make seed SEED_DIRS=data/places/ahmedabad` (Sampleton 30 places, Ahmedabad 103 places) and indexed with `make rag-index` using MOCK embeddings (`rag-index: documents=151 chunks=227 embedded=227 inactive=0 warnings=0 errors=0`).

## Dataset (TC-386)

- `trips` v1, 15 cases, 3 repeats, 45 attempts per run. `dataset_sha256` is `8e0bde49e0bd37e0d42a1f558baa2a287a69a0c53d53b8801288ff8c9439b450` in both MOCK records, the same value as in the baseline-1 record [`20261114T104200Z-gemini`](../results/20261114T104200Z-gemini/run.json). The harness checked the `cases.jsonl` hash against `manifest.json` before scoring.
- `retrieval/v1`, 12 queries (6 Sampleton, 6 Ahmedabad), `dataset_sha256` `696b02f9310b30148edb611743cc416a4e8db100e9283e2f43ffc45e6f2ff589`, the same as in the IMP-318 records.

## Prompt version (IMD-199, IMD-200, IMD-213)

The card's command passes no `--prompt-version`, so each frozen trips/v1 request runs the version it names. Both MOCK records state `prompt_version` `v1` and `prompt_version_overridden` `false`, with schemas gr-1 / io-1. This keeps the runs comparable with baseline-1, which also ran v1. The product's active version stays v2 (IMD-200); it was not changed. MOCK does not read the prompt text. The retrieval suite always plans with `itinerary_generate` v2 (its record says so).

The rule-based planner reads no prompt, so its record states `prompt_version` `not applicable` (IMD-213); it reads the gr-1 request and answers io-1.

IMD-213 (PD-IMP-705-2) sets the final GEMINI run on trips/v1 to the active prompt v2 with `--prompt-version v2`. **baseline-1 used v1, so a final GEMINI v2 figure and baseline-1 compare across prompt versions, not like for like.** The final GEMINI run is [`20261120T165222Z-gemini`](../results/20261120T165222Z-gemini/run.json): `prompt_version` `v2`, `prompt_version_overridden` `true`, schemas gr-2 / io-2 (v2 reads gr-2; the harness grounds each request with no passages, as the pipeline does when retrieval finds nothing).

## Runs

| Run id | Card step | Command | Provider · model | Result line | Record |
| --- | --- | --- | --- | --- | --- |
| `20261119T182737Z-mock` | 2 (first) | `make eval PROVIDER=MOCK DATASET=trips/v1` | MOCK · `mock-v1` (`mock-1`) | `evaluation 20261119T182737Z-mock: 45 attempts, written to /home/user/wt-S7B-eval-main/eval/results/20261119T182737Z-mock` | [run.json](../results/20261119T182737Z-mock/run.json), [scores.json](../results/20261119T182737Z-mock/scores.json) |
| `20261119T182745Z-mock` | 2 (second) | `make eval PROVIDER=MOCK DATASET=trips/v1` | MOCK · `mock-v1` (`mock-1`) | `evaluation 20261119T182745Z-mock: 45 attempts, written to /home/user/wt-S7B-eval-main/eval/results/20261119T182745Z-mock` | [run.json](../results/20261119T182745Z-mock/run.json), [scores.json](../results/20261119T182745Z-mock/scores.json) |
| none (RUN-083) | 3 | `make eval PROVIDER=RULE_BASED DATASET=trips/v1` | rule-based | `rule-based planner not available (IMP-402)`, exit 2, nothing written (superseded by the next row) | none |
| `20261120T155153Z-rule_based` | 3 (RUN-083b, IMD-213) | `make eval PROVIDER=RULE_BASED DATASET=trips/v1` | RULE_BASED · `rule-based` (`rule_based_planner_v1`) | `evaluation 20261120T155153Z-rule_based: 45 attempts, written to /Users/nidhi/wt-S7B2-eval/eval/results/20261120T155153Z-rule_based` | [run.json](../results/20261120T155153Z-rule_based/run.json), [scores.json](../results/20261120T155153Z-rule_based/scores.json) |
| `20261120T165222Z-gemini` | 4 (run by the operator; IMD-213) | `make eval PROVIDER=GEMINI DATASET=trips/v1 ARGS='--prompt-version v2'` | GEMINI · `gemini-3.5-flash-lite` | the printed line was not kept; the record shows 45 attempts, 23 completed and 22 `provider_unavailable` | [run.json](../results/20261120T165222Z-gemini/run.json), [scores.json](../results/20261120T165222Z-gemini/scores.json) |
| `20261119T182831Z-retrieval-mock` | 7 (MOCK) | `make eval DATASET=retrieval/v1 ARGS='--suite retrieval'` | MOCK · `mock-v1`, embeddings `mock-embed-v1` | `evaluation 20261119T182831Z-retrieval-mock: 12 queries, written to /home/user/wt-S7B-eval-main/eval/results/20261119T182831Z-retrieval-mock` | [run.json](../results/20261119T182831Z-retrieval-mock/run.json), [report](20261119T182831Z-retrieval-mock.md) |
| none | 7 (GEMINI) | `make eval DATASET=retrieval/v1 PROVIDER=GEMINI ARGS='--suite retrieval'` | GEMINI | no record: no GEMINI retrieval run folder exists after `20261120T165222Z-gemini` in the evaluation worktree | none |

Two earlier operator attempts at step 4 failed in every attempt and are not committed or used: `20261120T163036Z-gemini` (45 × `config_error`; the operator reports the old key was rejected with HTTP 401) and `20261120T164419Z-gemini` (45 × `config_error`; `GEMINI_MODEL_ID` still held the `.env.example` placeholder). Both records name that placeholder as `model_id`. Neither was re-run (rule 16).

The records are copied unchanged. `raw/` outputs were written and are not committed, as for earlier runs. A search of every output file for `api_key`, `AIza`, `secret`, `password` and `postgres:` found no match.

## Generation suite: comparison with baseline-1

| Metric | baseline-1 GEMINI [`20261114T104200Z-gemini`](../results/20261114T104200Z-gemini/run.json) (prompt v1, metrics v1) | Final GEMINI [`20261120T165222Z-gemini`](../results/20261120T165222Z-gemini/run.json) (prompt v2, metrics v2; quality figures over the 23 completed attempts) | Final MOCK run 1 [`20261119T182737Z-mock`](../results/20261119T182737Z-mock/run.json) (prompt v1, metrics v2) | Final MOCK run 2 [`20261119T182745Z-mock`](../results/20261119T182745Z-mock/run.json) (prompt v1, metrics v2) | Rule-based [`20261120T155153Z-rule_based`](../results/20261120T155153Z-rule_based/run.json) (no prompt, metrics v2) |
| --- | --- | --- | --- | --- | --- |
| Schema-valid outputs | 44 / 45 | 23 / 23 completed (23 / 45 in the record) | 45 / 45 | 45 / 45 | 45 / 45 |
| Outputs with only valid place IDs | 44 / 45 | 23 / 23 completed (23 / 45 in the record) | 45 / 45 | 45 / 45 | 45 / 45 |
| Usable outputs | 44 / 45 | 23 / 23 completed (23 / 45 in the record) | 45 / 45 | 45 / 45 | 45 / 45 |
| No duplicate places (IMD-181) | not measured (metrics v1) | 19 / 23 completed (19 / 45 in the record) | 45 / 45 | 45 / 45 | 45 / 45 |
| Average daily travel (minutes) | 92.2 | 119.4 (completed attempts only; failed attempts have no plan) | 126.7 | 126.7 | 86.2 |
| Failures | 1 (`trips-v1-010`, repeat 2, `schema_violation`) | 22 / 45 `provider_unavailable` (availability: 23 / 45 completed) | 0 | 0 | 0 |

MOCK and GEMINI figures are not comparable as model quality: the MOCK adapter returns fixed answers. The MOCK columns show that the release-candidate pipeline (steps 7 to 9, metrics v2) runs and scores every case without failure. The rule-based column is the production fallback planner answering each request in place of a model, scored by the same output check, schedule, validator, budget engine and metric code (IMD-213).

### Final GEMINI run, prompt v2 (card step 4, TC-392)

From [`20261120T165222Z-gemini`](../results/20261120T165222Z-gemini/run.json) and its [scores.json](../results/20261120T165222Z-gemini/scores.json):

- **Availability:** 23 of 45 attempts completed; 22 ended in `provider_unavailable` (Gemini service errors, not quota), spread through the run: `trips-v1-001` r1 r3, `002` r1 to r3, `003` r1 to r3, `004` r1 r2, `005` r1 r2, `006` r3, `007` r3, `010` r2 r3, `011` r3, `012` r1 to r3, `014` r1 r3. Cases `002`, `003` and `012` have no completed attempt, so 12 of the 15 cases are covered. A failed attempt has no latency or tokens.
- **Quality, over the 23 completed attempts only:** schema-valid 23 / 23, only valid place IDs 23 / 23 (0 invalid IDs), usable 23 / 23, no duplicate places 19 / 23 (8 duplicate items in total, and 8 items rejected by the output check), average daily travel 119.4 minutes. Finding codes: `COST_INCOMPLETE` 7, `BUDGET_NEAR` 1. The record's own counts use n = 45 (for example `schema_valid` 23 / 45), because a failed attempt counts as not schema-valid.
- **Real model output:** all 23 completed attempts carry input and output tokens (input 1471 to 4984, output 314 to 1957 per attempt), and every completed answer has item notes and a model summary, none the rule-based planner's summary. The harness never runs the fallback planner after a provider failure.
- **Comparison with baseline-1 (v1):** across prompt versions (see Prompt version) and over different attempt sets (baseline-1: 45 attempts of 15 cases; final: 23 attempts of 12 cases). Among completed attempts the v2 run had no schema failure (baseline-1: 1), and its average daily travel is 119.4 against 92.2. No conclusion about v2 against v1 is drawn from these two runs.

The most recent recorded GEMINI run is [`20261116T042246Z-gemini`](../results/20261116T042246Z-gemini/run.json) (RUN-079, commit `3a68439`, prompt v3, which is not active under IMD-200). It is not a release-candidate run and is not used as the final GEMINI baseline; [`RUN-079-prompt-v3.md`](RUN-079-prompt-v3.md) reports it.

### Earlier MOCK records of the same dataset and prompt

| Record | Commit | Metrics version | Schema-valid | Valid IDs | Usable | No duplicates | Average daily travel (min) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [`20261114T064139Z-mock`](../results/20261114T064139Z-mock/run.json) | `4c6c693` | v1 | 45 / 45 | 45 / 45 | 45 / 45 | not measured (v1) | 160.8 | 0 |
| [`20261115T194622Z-mock`](../results/20261115T194622Z-mock/run.json) | `0e15ae7` | v2 | 45 / 45 | 45 / 45 | 45 / 45 | 45 / 45 | 120.8 | 0 |
| [`20261119T182737Z-mock`](../results/20261119T182737Z-mock/run.json) | `f75aa94` | v2 | 45 / 45 | 45 / 45 | 45 / 45 | 45 / 45 | 126.7 | 0 |

The commit IDs of earlier records, in this table and elsewhere in this report, are those written at run time, before the IMD-208 history rewrite. `docs/progress/commit-map.md` maps the old IDs of `main` commits to new ones. The average daily travel of the MOCK plans changed between these commits. This part did not investigate why.

### Reproducibility (card step 2, ACC-14)

- The `metrics` objects of [`20261119T182737Z-mock`](../results/20261119T182737Z-mock/run.json) and [`20261119T182745Z-mock`](../results/20261119T182745Z-mock/run.json) are identical (compared as parsed JSON: equal). Every other field of the two records is equal except `run_id`, `started_at` and `ended_at`.
- The two `scores.json` files are equal in every field except `latency_ms`.
- The 45 `raw/` outputs of the two runs are identical (`diff -r` printed nothing).

### Rule-based planner (card step 3, TC-393)

In RUN-083 the harness refused `RULE_BASED`. IMD-213 approved connecting it (PD-IMP-705-1) as a hardening change under IMD-201: `--provider RULE_BASED` now answers each request with `generation/fallback_planner.plan_rule_based` and scores it with the same code; no provider is built and no planner code changed.

From [`20261120T155153Z-rule_based`](../results/20261120T155153Z-rule_based/run.json) (45 attempts, 15 cases, 3 repeats; `failures` `[]`):

- Schema-valid, valid place IDs, usable and no duplicate places: 45 / 45 each.
- Average daily travel: 86.2 minutes.
- Findings: `COST_INCOMPLETE` in 15 of 45 attempts (cases `trips-v1-003`, `007`, `012`, `014`, `015`, every repeat); no other finding code. Budget status `none` in 45 of 45 attempts.
- Tokens: null in 45 of 45 attempts (no model). Planner run time is in [`docs/test-reports/cost-latency-report.md`](../../docs/test-reports/cost-latency-report.md).
- The planner is deterministic, so the three repeats of a case give the same plan; the record does not show plan quality beyond these counts.

## Retrieval suite (card step 7, FR-140, TC-458)

| Metric (overall, 12 queries) | IMP-318 MOCK [`20261113T114756Z-retrieval-mock`](../results/20261113T114756Z-retrieval-mock/run.json) (commit `1b8d753`) | Final MOCK [`20261119T182831Z-retrieval-mock`](../results/20261119T182831Z-retrieval-mock/run.json) (commit `f75aa94`) | Final GEMINI (no record) |
| --- | --- | --- | --- |
| recall@6 | 0.7083 | 0.7083 | not measured: no GEMINI retrieval run record |
| Place hit rate, vector (top 12) | 0.6667 | 0.6667 | not measured: no GEMINI retrieval run record |
| Place hit rate, lexical (top 12) | 0.7083 | 0.7083 | not measured: no GEMINI retrieval run record |
| Citation validity | 1.0 | 1.0 | not measured: no GEMINI retrieval run record |
| Grounding rate | 0.7571 | 0.6392 | not measured: no GEMINI retrieval run record |
| Citations saved | 68 | 47 | not measured: no GEMINI retrieval run record |
| Queries in vector mode | 12 | 12 | not measured: no GEMINI retrieval run record |

By destination, final MOCK run [`20261119T182831Z-retrieval-mock`](../results/20261119T182831Z-retrieval-mock/run.json):

| Destination | Queries | recall@6 | Place hit rate (vector) | Place hit rate (lexical) | Citation validity | Grounding rate | Citations saved |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ahmedabad | 6 | 0.4167 | 0.3333 | 0.4167 | 1.0 | 0.7083 | 29 |
| sampleton | 6 | 1.0 | 1.0 | 1.0 | 1.0 | 0.5701 | 18 |

These are MOCK embeddings and MOCK answers, so they test the retrieval code path, not semantic retrieval quality. Citation validity is 1.0, as A1 §6.14 requires. The grounding rate and the number of citations saved are lower than in the IMP-318 MOCK record. The conditions differ in two recorded ways: the commit, and the index (the IMP-318 part record quotes `embedded=189` and this run's index printed `embedded=227`, both with 227 chunks). This part did not investigate the cause.

## What this baseline does not claim

- The final GEMINI generation figures cover 23 of 45 attempts (12 of 15 cases); 22 attempts failed with `provider_unavailable`. They say nothing about the three cases with no completed attempt (`trips-v1-002`, `003`, `012`) and are not a reliability figure for Gemini.
- No GEMINI retrieval figure exists: there is no GEMINI retrieval run record (card step 7 for GEMINI is not done).
- The rule-based figures are of the fallback planner answering in place of a model through the harness, not of the product's fallback rate (the harness runs no repair or fallback after a model answer).
- The numbered metrics 1 to 13 are not computed. Each record states the reason (blueprint §21.4 not in the repository, no dated price table, or Release 2).
- No claim is made about plan quality, accuracy or reliability beyond these runs over trips/v1 and retrieval/v1, for other destinations, other models or prompt versions, or for live use.
