# Final baseline · release-candidate evaluation over trips/v1 and retrieval/v1

IMP-705 (US-131; FR-120, FR-140; NFR-004, NFR-039, NFR-041). Owner: Nidhi. Compared with the first baseline, [`baseline-1.md`](baseline-1.md).

## Candidate and conditions

- Candidate commit: `f75aa949fe306361d2f515ede632504518d19b63` (`f75aa94`), `main` after IMP-701 and IMP-702 merged (card step 1, IMD-202). Every record below holds this `git_commit`.
- Date: 19 November 2026 (UTC times are in each record).
- All runs started from a clean evaluation worktree detached at the candidate commit (IMD-176). After each run its output folder was moved out of that worktree, so the next run started from a clean tree again; `git status --porcelain` was empty after the last move.
- Environment: a Linux cloud container, the shared API virtual environment, proxy variables unset, `AI_PROVIDER=MOCK`. No Gemini key exists in this environment.
- Retrieval database: the compose PostgreSQL 16 with pgvector, migrated to `0007`, seeded with `make seed SEED_DIRS=data/places/ahmedabad` (Sampleton 30 places, Ahmedabad 103 places) and indexed with `make rag-index` using MOCK embeddings (`rag-index: documents=151 chunks=227 embedded=227 inactive=0 warnings=0 errors=0`).

## Dataset (TC-386)

- `trips` v1, 15 cases, 3 repeats, 45 attempts per run. `dataset_sha256` is `8e0bde49e0bd37e0d42a1f558baa2a287a69a0c53d53b8801288ff8c9439b450` in both MOCK records, the same value as in the baseline-1 record [`20261114T104200Z-gemini`](../results/20261114T104200Z-gemini/run.json). The harness checked the `cases.jsonl` hash against `manifest.json` before scoring.
- `retrieval/v1`, 12 queries (6 Sampleton, 6 Ahmedabad), `dataset_sha256` `696b02f9310b30148edb611743cc416a4e8db100e9283e2f43ffc45e6f2ff589`, the same as in the IMP-318 records.

## Prompt version (IMD-199, IMD-200)

The card's command passes no `--prompt-version`, so each frozen trips/v1 request runs the version it names. Both MOCK records state `prompt_version` `v1` and `prompt_version_overridden` `false`, with schemas gr-1 / io-1. This keeps the runs comparable with baseline-1, which also ran v1. The product's active version stays v2 (IMD-200); it was not changed. MOCK does not read the prompt text. The retrieval suite always plans with `itinerary_generate` v2 (its record says so).

## Runs

| Run id | Card step | Command | Provider · model | Result line | Record |
| --- | --- | --- | --- | --- | --- |
| `20261119T182737Z-mock` | 2 (first) | `make eval PROVIDER=MOCK DATASET=trips/v1` | MOCK · `mock-v1` (`mock-1`) | `evaluation 20261119T182737Z-mock: 45 attempts, written to /home/user/wt-S7B-eval-main/eval/results/20261119T182737Z-mock` | [run.json](../results/20261119T182737Z-mock/run.json), [scores.json](../results/20261119T182737Z-mock/scores.json) |
| `20261119T182745Z-mock` | 2 (second) | `make eval PROVIDER=MOCK DATASET=trips/v1` | MOCK · `mock-v1` (`mock-1`) | `evaluation 20261119T182745Z-mock: 45 attempts, written to /home/user/wt-S7B-eval-main/eval/results/20261119T182745Z-mock` | [run.json](../results/20261119T182745Z-mock/run.json), [scores.json](../results/20261119T182745Z-mock/scores.json) |
| none | 3 | `make eval PROVIDER=RULE_BASED DATASET=trips/v1` | rule-based | `rule-based planner not available (IMP-402)`, exit 2, nothing written | none |
| none | 4 | `make eval PROVIDER=GEMINI DATASET=trips/v1` | GEMINI | not run: no key in the run environment | none |
| `20261119T182831Z-retrieval-mock` | 7 (MOCK) | `make eval DATASET=retrieval/v1 ARGS='--suite retrieval'` | MOCK · `mock-v1`, embeddings `mock-embed-v1` | `evaluation 20261119T182831Z-retrieval-mock: 12 queries, written to /home/user/wt-S7B-eval-main/eval/results/20261119T182831Z-retrieval-mock` | [run.json](../results/20261119T182831Z-retrieval-mock/run.json), [report](20261119T182831Z-retrieval-mock.md) |
| none | 7 (GEMINI) | retrieval suite with GEMINI | GEMINI | not run: no key in the run environment | none |

The records are copied unchanged. `raw/` outputs were written and are not committed, as for earlier runs. A search of every output file for `api_key`, `AIza`, `secret`, `password` and `postgres:` found no match.

## Generation suite: comparison with baseline-1

| Metric | baseline-1 GEMINI [`20261114T104200Z-gemini`](../results/20261114T104200Z-gemini/run.json) (prompt v1, metrics v1) | Final GEMINI | Final MOCK run 1 [`20261119T182737Z-mock`](../results/20261119T182737Z-mock/run.json) (prompt v1, metrics v2) | Final MOCK run 2 [`20261119T182745Z-mock`](../results/20261119T182745Z-mock/run.json) (prompt v1, metrics v2) |
| --- | --- | --- | --- | --- |
| Schema-valid outputs | 44 / 45 | not measured: no key in the run environment | 45 / 45 | 45 / 45 |
| Outputs with only valid place IDs | 44 / 45 | not measured: no key in the run environment | 45 / 45 | 45 / 45 |
| Usable outputs | 44 / 45 | not measured: no key in the run environment | 45 / 45 | 45 / 45 |
| No duplicate places (IMD-181) | not measured (metrics v1) | not measured: no key in the run environment | 45 / 45 | 45 / 45 |
| Average daily travel (minutes) | 92.2 | not measured: no key in the run environment | 126.7 | 126.7 |
| Failures | 1 (`trips-v1-010`, repeat 2, `schema_violation`) | not measured: no key in the run environment | 0 | 0 |

MOCK and GEMINI figures are not comparable as model quality: the MOCK adapter returns fixed answers. The MOCK columns show that the release-candidate pipeline (steps 7 to 9, metrics v2) runs and scores every case without failure.

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

Not measured. `make eval PROVIDER=RULE_BASED DATASET=trips/v1` printed `rule-based planner not available (IMP-402)` and exited 2. The planner exists on `main` (`apps/api/app/generation/fallback_planner.py`), but the harness still refuses the provider (`unavailable()` in `apps/api/app/evaluation/run.py`, PD-IMP-413-2). Connecting the two would change product code, which the feature freeze does not allow (IMD-201). No rule-based figure is reported.

## Retrieval suite (card step 7, FR-140, TC-458)

| Metric (overall, 12 queries) | IMP-318 MOCK [`20261113T114756Z-retrieval-mock`](../results/20261113T114756Z-retrieval-mock/run.json) (commit `1b8d753`) | Final MOCK [`20261119T182831Z-retrieval-mock`](../results/20261119T182831Z-retrieval-mock/run.json) (commit `f75aa94`) | Final GEMINI |
| --- | --- | --- | --- |
| recall@6 | 0.7083 | 0.7083 | not measured: no key in the run environment |
| Place hit rate, vector (top 12) | 0.6667 | 0.6667 | not measured: no key in the run environment |
| Place hit rate, lexical (top 12) | 0.7083 | 0.7083 | not measured: no key in the run environment |
| Citation validity | 1.0 | 1.0 | not measured: no key in the run environment |
| Grounding rate | 0.7571 | 0.6392 | not measured: no key in the run environment |
| Citations saved | 68 | 47 | not measured: no key in the run environment |
| Queries in vector mode | 12 | 12 | not measured: no key in the run environment |

By destination, final MOCK run [`20261119T182831Z-retrieval-mock`](../results/20261119T182831Z-retrieval-mock/run.json):

| Destination | Queries | recall@6 | Place hit rate (vector) | Place hit rate (lexical) | Citation validity | Grounding rate | Citations saved |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ahmedabad | 6 | 0.4167 | 0.3333 | 0.4167 | 1.0 | 0.7083 | 29 |
| sampleton | 6 | 1.0 | 1.0 | 1.0 | 1.0 | 0.5701 | 18 |

These are MOCK embeddings and MOCK answers, so they test the retrieval code path, not semantic retrieval quality. Citation validity is 1.0, as A1 §6.14 requires. The grounding rate and the number of citations saved are lower than in the IMP-318 MOCK record. The conditions differ in two recorded ways: the commit, and the index (the IMP-318 part record quotes `embedded=189` and this run's index printed `embedded=227`, both with 227 chunks). This part did not investigate the cause.

## What this baseline does not claim

- No GEMINI figure exists for the candidate commit: neither suite could run with Gemini because the run environment has no key. The final GEMINI generation and retrieval runs (card steps 4 and 7) remain to be made by Nidhi with the protected staging key, within the daily cap, from a clean worktree at a commit on `main`.
- No rule-based figure exists (see above).
- The numbered metrics 1 to 13 are not computed. Each record states the reason (blueprint §21.4 not in the repository, no dated price table, or Release 2).
- No claim is made about plan quality, accuracy or reliability beyond these runs over trips/v1 and retrieval/v1, for other destinations, other models or prompt versions, or for live use.
