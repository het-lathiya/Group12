# RUN-077 · prompt v3 MOCK evaluation over trips/v1

- Run ids: `20261115T194621Z-mock` (default settings, `PROMPT_TEMPLATE_VERSION` unset, Settings default v2) and `20261115T194622Z-mock` (`PROMPT_TEMPLATE_VERSION=v3`); records `eval/results/<run id>/run.json`
- Started: 2026-11-15 19:46 UTC, each from a clean working tree (`git status --porcelain` empty) at `main` commit BASE `0e15ae7` (IMD-176); both records hold `git_commit` `0e15ae75d14bd3cf413b95e8b9de3c8a11ff743b`
- Commands, from the repository root:
  1. `make eval PROVIDER=MOCK DATASET=trips/v1` → `evaluation 20261115T194621Z-mock: 45 attempts, written to .../eval/results/20261115T194621Z-mock`
  2. `PROMPT_TEMPLATE_VERSION=v3 make eval PROVIDER=MOCK DATASET=trips/v1` → `evaluation 20261115T194622Z-mock: 45 attempts, written to .../eval/results/20261115T194622Z-mock`
- Provider and model: MOCK, `mock-v1` (adapter `mock-1`)
- Metrics version: v2 (`eval/metrics_v2.md`, hash `a1be38b0…` in both records)

## Prompt version actually used: v1 in both runs

Both records state `prompt_template_id` `itinerary_generate`, `prompt_version` **v1**, input `gr-1`, output `io-1`. The generation suite sends the frozen gr-1 requests of dataset `trips/v1`, and each request names `prompt_version: "v1"` (all 15 cases); the record takes the version from the request (`app/evaluation/run.py`), and the adapters render the template the request names. `PROMPT_TEMPLATE_VERSION` is read only as the default of `registry.load` (the API start-up check and the generation pipeline), not by this suite. **The environment override did not take effect: neither v2 nor v3 was evaluated by these runs.**

## Metric values

| Metric | Run 1 (`…194621Z`, "v2") | Run 2 (`…194622Z`, "v3") |
| --- | --- | --- |
| Prompt version in record | v1 (gr-1 / io-1) | v1 (gr-1 / io-1) |
| Attempts | 45 (15 trips × 3 repeats) | 45 |
| Schema-valid outputs | 45 / 45 | 45 / 45 |
| Outputs with only valid place IDs | 45 / 45 | 45 / 45 |
| Usable outputs | 45 / 45 | 45 / 45 |
| No duplicate places (IMD-181) | 45 / 45 | 45 / 45 |
| Duplicate-place items, summed over attempts (IMD-181) | 0 | 0 |
| Average daily travel (minutes) | 120.8 | 120.8 |
| Failures | 0 | 0 |
| Notes and assumptions containing "AI-written" (IMD-180) | 0 of 558 | 0 of 558 |

The duplicate count is the `duplicate_places` field of each attempt's score; the label count was taken from the 45 raw outputs of each run (item notes and assumptions). The raw outputs of the two runs were byte-identical. As for earlier runs, only `run.json` is committed.

## Reading

The MOCK provider does not read the prompt text: it returns the same scenario output whatever template is named, so equal metrics were expected even if v3 had been sent. These runs show only that the harness, scoring and MOCK outputs are stable at BASE; they say nothing about how v2 or v3 change a real model's answers. An evaluation of v3 needs a dataset whose requests name v3 (gr-2) or a harness option for the prompt version, and a model that reads the prompt (see PD-RUN-077-E1 in `docs/progress/parts/RUN-077-prompt-v3-eval.md`).

## What this report does not claim

It covers only these MOCK runs over the 15 trips of dataset v1. It makes no claim about plan quality, about v2 or v3, about Gemini, or about live use.
