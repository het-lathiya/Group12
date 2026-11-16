# RUN-079 · prompt v3 evaluation over trips/v1 (MOCK v2, MOCK v3, Gemini v3)

- Commit: all three runs started from a clean evaluation worktree (IMD-176) detached at `main` commit BASE `3a68439`; every record holds `git_commit` `3a6843921ae431e3735b88ba3a687a5080664858`. The worktree held nothing but the new `eval/results/<run id>/` folders afterwards.
- Dataset: `trips/v1`, 15 cases × 3 repeats = 45 attempts per run (dataset hash `8e0bde49…`, the same as baseline-1).
- Metrics version: v2 (`eval/metrics_v2.md`, hash `a1be38b0…` in all three records).
- Prompt version: passed explicitly with `--prompt-version` (IMD-199); each record states `prompt_version_overridden: true`.
- Commands, from `apps/api` of the worktree (shared virtual environment, `PYTHONPATH=.`; the same module that `make eval` runs):

| Run id | Command | Provider · model (adapter) | Prompt version in record | Schemas | Result line |
| --- | --- | --- | --- | --- | --- |
| `20261116T042221Z-mock` | `python -m app.evaluation.run --dataset trips/v1 --provider MOCK --prompt-version v2` | MOCK · `mock-v1` (`mock-1`) | v2 | gr-2 / io-2 | `evaluation 20261116T042221Z-mock: 45 attempts, written to …/eval/results/20261116T042221Z-mock` |
| `20261116T042224Z-mock` | `python -m app.evaluation.run --dataset trips/v1 --provider MOCK --prompt-version v3` | MOCK · `mock-v1` (`mock-1`) | v3 | gr-2 / io-2 | `evaluation 20261116T042224Z-mock: 45 attempts, written to …/eval/results/20261116T042224Z-mock` |
| `20261116T042246Z-gemini` | `python -m app.evaluation.run --dataset trips/v1 --provider GEMINI --prompt-version v3` (key loaded from the untracked env file for this command only) | GEMINI · `gemini-3.5-flash-lite` (`gemini-interactions-1`) | v3 | gr-2 / io-2 | `evaluation 20261116T042246Z-gemini: 45 attempts, written to …/eval/results/20261116T042246Z-gemini` |

Gemini settings were the same as baseline-1 (`20261114T104200Z-gemini`): same model, Interactions API, structured output, thinking level `minimal`, timeout 35 s, 3 repeats. Nothing in the configuration on `main` had changed.

Committed per run: `run.json` and `scores.json`, copied unchanged. As for earlier runs, the `raw/` model outputs are not committed.

## Gemini: baseline-1 (v1) against v3

| Metric | baseline-1 `20261114T104200Z-gemini` (v1, metrics v1) | v3 `20261116T042246Z-gemini` (metrics v2) |
| --- | --- | --- |
| Schema-valid outputs | 44 / 45 | 44 / 45 |
| Outputs with only valid place IDs | 44 / 45 | 44 / 45 |
| Usable outputs | 44 / 45 | 44 / 45 |
| Average daily travel (minutes, reported only) | 92.2 | 112.2 |
| Failures | 1: `trips-v1-010` repeat 2, `schema_violation` | 1: `trips-v1-012` repeat 3, `provider_unavailable` |
| No duplicate places (IMD-181) | not measured (metrics v1) | 41 / 45 (3 answers with duplicates, plus the failed attempt) |
| Duplicate-place items, summed (IMD-181) | not measured | 14: `trips-v1-003` r2 (3), `trips-v1-007` r2 (1), `trips-v1-012` r2 (10) |
| Notes and assumptions with "AI-written" (IMD-180) | not measured | 0 of 564 |

The validator rejected every duplicate item: `rejected_items` equals `duplicate_places` in those three attempts, so the saved plans would hold no repeated place. They still count against the gate because the model wrote them.

## MOCK: v2 against v3

| Metric | v2 `20261116T042221Z-mock` | v3 `20261116T042224Z-mock` |
| --- | --- | --- |
| Schema-valid outputs | 45 / 45 | 45 / 45 |
| Outputs with only valid place IDs | 45 / 45 | 45 / 45 |
| Usable outputs | 45 / 45 | 45 / 45 |
| Average daily travel (minutes) | 126.7 | 126.7 |
| Failures | 0 | 0 |
| Duplicate-place items (IMD-181) | 0 (45 / 45 without) | 0 (45 / 45 without) |
| Notes and assumptions with "AI-written" (IMD-180) | 0 of 552 | 0 of 552 |

MOCK does not read the prompt text, so equal results were expected. These runs show only that the v2 and v3 request path (gr-2 / io-2) runs and scores cleanly from `main`. None of the three runs carries retrieved passages: the evaluation grounds gr-2 requests with no passages and uses lexical ranking (RUN-078 record).

Duplicates and "AI-written" were counted as follows. Duplicates are the `duplicate_places` field of each attempt in `scores.json`. "AI-written" was counted case-insensitively over the item notes and assumptions in the 45 raw outputs of each run.

## IMD-195 gate verdict: NOT MET

| Gate condition | Value | Holds |
| --- | --- | --- |
| Gemini v3 usable ≥ 44/45 | 44/45 | yes |
| Gemini v3 schema-valid ≥ 44/45 | 44/45 | yes |
| Gemini v3 valid IDs ≥ 44/45 | 44/45 | yes |
| Gemini v3 failures ≤ 1 | 1 | yes |
| Gemini v3 duplicate places 0 | 14 items in 3 attempts | **no** |
| Gemini v3 "AI-written" 0 | 0 | yes |
| MOCK v3 schema-valid 45/45 | 45/45 | yes |

The failing condition is duplicate places. itinerary_generate v3 stays inactive, and no prompt or configuration was changed (PD-RUN-079-1).

## What this report does not claim

It covers only these three runs over the 15 trips of dataset v1. Baseline-1 was scored with metrics v1, so it has no duplicate or label counts to compare against. One Gemini run of 45 attempts is a small sample: the difference in average daily travel and in the failure class says nothing reliable about v3. No claim is made about plan quality, retrieval, staging or live use.
