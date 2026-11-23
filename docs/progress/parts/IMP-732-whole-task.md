# IMP-732 · whole-task part (live-city evaluation dataset and MOCK/rule-based report)

- Card: IMP-732 (0 points, Amendment A2 §12 Batch C3)
- Run id: RUN-092 (Batch C3, Sprint 7, inserted under IMD-215)
- Owner: Manya (Manya Rana)
- Status: PR_OPEN candidate on `feat/S7-C3-any-city-verify`
- Base commit: 818c1d8 (on `main`)
- Traces to: TC-489; A2 §6.6; IMD-195, IMD-213

## Changed files

- `eval/datasets/trips/live-v1/cases.jsonl` (created): 8 gr-1 cases for "Liveton (SAMPLE)". They were built from the fake OSM elements through `normalise`, the places service's live column mapping and `request_builder.shortlist_place`. Every price and every opening time is unknown, and the names are OSM-like SAMPLE names (two hostile names in `trips-live-v1-008`).
- `eval/datasets/trips/live-v1/schema.json` (created): a copy of `trips/schema.json` with the id pattern `trips-live-v1-NNN`, version `live-v1` and the live categories. `trips/schema.json` is hashed in the trips/v1 manifest, so it is not edited.
- `eval/datasets/trips/live-v1/manifest.json` (created): counts, file hashes and `set_sha256`.
- `eval/results/20261123T171053Z-mock/`, `…-rule_based/` and `20261123T171127Z-mock/`: the `run.json` and `scores.json` of the three runs.
- `eval/reports/live-v1-2026-11-23.md` (created).
- `.github/workflows/ci.yml`: one step, "Live-city evaluation run (MOCK, trips/live-v1)", added at the end of P3's `any-city` job. The existing jobs are unchanged.

`trips/v1` is not edited.

## Commands

| Command | Result line |
| --- | --- |
| `make eval PROVIDER=MOCK DATASET=trips/live-v1` | evaluation 20261123T171053Z-mock: 24 attempts, written to /Users/nidhi/Group12/eval/results/20261123T171053Z-mock |
| `make eval PROVIDER=RULE_BASED DATASET=trips/live-v1` | evaluation 20261123T171053Z-rule_based: 24 attempts, written to /Users/nidhi/Group12/eval/results/20261123T171053Z-rule_based |
| `make eval DATASET=trips/v1 PROVIDER=MOCK` | evaluation 20261123T171127Z-mock: 45 attempts, written to /Users/nidhi/Group12/eval/results/20261123T171127Z-mock |

## Acceptance

- **The report is committed with its run metadata, and every number comes from `eval/results/` or `eval/reports/`: verified.** Each table row names its file.
- **Validity, the hallucinated-place rate, the unknown-price share and latency: verified.** All attempts were valid and usable, with 0 invalid ids, 100 % unknown-price items, and in-process latency.
- **Citation coverage: not verified.** It is not measurable in the gr-1 generation suite (no passages); the report states this.
- **Comparison with trips/v1: built** (MOCK on the same commit).

## Cut if late

none. Step 5 (one GEMINI run for v4) is not part of this run. The operator runs it in staging window 2.

## Proposed decisions

none

## Open issues

- `HOURS_UNVERIFIED` does not appear in the eval findings, because the eval check has no stored hours rows to compare. The API tests (IMP-727) cover it.
- Citation coverage for live plans needs a gr-2 live dataset with passages: future work.

## Blockers

none
