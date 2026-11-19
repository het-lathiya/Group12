# Stage 2 migration-gate criteria (draft)

- Status: Proposed. Every threshold in this document is Proposed.
- Owner: Manya (Manya Rana)
- Date: 19 November 2026
- Card: IMP-706 step 1 (US-132); FR-121 (Stage 2: define the migration gate before testing)

## Purpose

This draft states what a candidate model behind the `FINETUNED_MODEL` adapter would have to show before any decision to switch the default provider away from Gemini. It is written before any Stage 2 test, as FR-121 requires. NFR-046 likewise requires the criteria commit to come before the final scoring commit. Meeting the gate does not switch anything: a recorded decision is still needed (PD-13, OD-13).

## Criteria E1 to E7 of the blueprint

The card asks for criteria E1 to E7 from blueprint §22 and §33.4. The blueprint is not in the repository, so their wording and thresholds cannot be copied here.

| ID | Criterion | Threshold |
| --- | --- | --- |
| E1 | to be confirmed against blueprint §22 and §33.4 by Manya | Proposed: to be confirmed against blueprint §22 and §33.4 by Manya |
| E2 | to be confirmed against blueprint §22 and §33.4 by Manya | Proposed: to be confirmed against blueprint §22 and §33.4 by Manya |
| E3 | to be confirmed against blueprint §22 and §33.4 by Manya | Proposed: to be confirmed against blueprint §22 and §33.4 by Manya |
| E4 | to be confirmed against blueprint §22 and §33.4 by Manya | Proposed: to be confirmed against blueprint §22 and §33.4 by Manya |
| E5 | to be confirmed against blueprint §22 and §33.4 by Manya | Proposed: to be confirmed against blueprint §22 and §33.4 by Manya |
| E6 | to be confirmed against blueprint §22 and §33.4 by Manya | Proposed: to be confirmed against blueprint §22 and §33.4 by Manya |
| E7 | to be confirmed against blueprint §22 and §33.4 by Manya | Proposed: to be confirmed against blueprint §22 and §33.4 by Manya |

Until E1 to E7 are confirmed, the candidate criteria below come only from what the repository defines. When the blueprint is checked, each E criterion is mapped to one or more G rows, or added as a new row.

## Candidate criteria derived from the repository

### Conditions of the comparison

| ID | Condition | Source |
| --- | --- | --- |
| C1 | The candidate and Gemini are evaluated on the same cases: dataset `trips/v1` (`dataset_sha256` `8e0bde49e0bd37e0d42a1f558baa2a287a69a0c53d53b8801288ff8c9439b450`) and `retrieval/v1` (`696b02f9310b30148edb611743cc416a4e8db100e9283e2f43ffc45e6f2ff589`), or a later dataset version both run | Card step 1; FR-118 |
| C2 | Both runs are made on the same day, from a clean worktree at the same commit on `main`, with the same harness (`make eval`), the same metrics version and file hash, the same repeats (3) and the same prompt version | Card step 1; FR-119 AC2; IMD-176; IMD-195 |
| C3 | The Gemini run of that day is the comparison baseline, not an older record | Card step 1 |
| C4 | Quota or rate-limit failures are counted as they are and never re-run | IMD-200 |
| C5 | None of the evaluation cases appears in the training set (FR-118 AC2, TC-284) | FR-118; [data-governance-policy.md](data-governance-policy.md) |

### Gate rows

| ID | Criterion | Measure (from the run record) | Proposed threshold | Source |
| --- | --- | --- | --- | --- |
| G1 | Schema-valid outputs | `counts.schema_valid` k / n | Proposed: not lower than the Gemini run of the same day | §8.11; metrics v2 |
| G2 | Only shortlist place IDs | `counts.place_ids_valid` k / n | Proposed: not lower than the Gemini run of the same day | §8.11; PD-14 |
| G3 | Usable plans | `counts.usable` k / n | Proposed: not lower than the Gemini run of the same day | §8.12 |
| G4 | No repeated places | `counts.no_duplicate_places` k / n | Proposed: n / n (no duplicate place in any attempt) | IMD-181; IMD-195 uses "duplicate places 0" for prompt activation |
| G5 | Failed attempts | `failures` count | Proposed: not more than the Gemini run of the same day | FR-120 |
| G6 | Citation validity (retrieval suite) | `metrics.overall.citation_validity` | Proposed: 1.0 | A1 §6.14 ("must be 1.0") |
| G7 | Grounding rate and recall@6 (retrieval suite) | `metrics.overall.grounding_rate`, `recall_at_6` | Proposed: not lower than the Gemini run of the same day | A1 §6.14; FR-140 |
| G8 | Generation time | p95 of end-to-end generation time on staging (`ai_generations` rows) | Proposed: at most 90 s for trips up to 7 days | NFR-004 (itself proposed in the specification) |
| G9 | Provider compatibility | The shared provider contract suite (IMP-512, `make test-contract`) passes for the new adapter with recorded responses | Proposed: all cases pass | PD-13 ("compatibility suite"); FR-040 |
| G10 | Rollback rehearsal | On staging, set `AI_PROVIDER` back to GEMINI, then run `make smoke` and one generation; record the time taken and the result | Proposed: rehearsed once and recorded before the decision | PD-13 ("rehearsed rollback"); card step 1 |
| G11 | No user data in training | Data card overlap and source checks; TC-361 | Proposed: 0 user-derived records (NFR-023); 0 evaluation cases in the training set | NFR-023; PD-09; FR-118 AC2 |
| G12 | Model output as training data | Recorded terms review | Proposed: none used unless a recorded terms review permits it | OD-17 |

Average daily travel (`avg_daily_travel_min`) is reported in each run but is not a gate row. Earlier reports also treat it as reported only (`eval/reports/RUN-079-prompt-v3.md`). The numbered metrics 1 to 13 are not computed by the harness (blueprint §21.4 is not in the repository). If E1 to E7 depend on them, their definitions must be added as a new metrics version before any scoring.

## Current reference values

These recorded values show where the comparison stands today. They are not thresholds.

| Measure | Gemini baseline-1 [`20261114T104200Z-gemini`](../../eval/results/20261114T104200Z-gemini/run.json) (prompt v1, metrics v1) | Final Gemini run of IMP-705 | MOCK at the release candidate [`20261119T182737Z-mock`](../../eval/results/20261119T182737Z-mock/run.json) |
| --- | --- | --- | --- |
| Schema-valid | 44 / 45 | not measured: no key in the run environment | 45 / 45 |
| Valid place IDs | 44 / 45 | not measured: no key in the run environment | 45 / 45 |
| Usable | 44 / 45 | not measured: no key in the run environment | 45 / 45 |
| No duplicate places | not measured (metrics v1) | not measured: no key in the run environment | 45 / 45 |
| Failures | 1 | not measured: no key in the run environment | 0 |

Source: [`eval/reports/final-baseline.md`](../../eval/reports/final-baseline.md). MOCK returns fixed answers, so it is not a quality reference for a trained model.

## Procedure (Proposed)

1. Commit the confirmed criteria (E1 to E7 mapped to G rows) and their thresholds before any Stage 2 scoring (FR-121, NFR-046).
2. Complete the data card ([data-card-template.md](data-card-template.md)) and have the dataset approved under [data-governance-policy.md](data-governance-policy.md).
3. On one day and one commit on `main`, run the Gemini and candidate evaluations under C1 to C5.
4. Write a report that cites each figure's run record (NFR-041).
5. Rehearse the rollback (G10).
6. The team with the supervisor records the go or no-go in `docs/spec/DECISION_REGISTER.md` (OD-13, PD-13). Until then `AI_PROVIDER` does not change.
