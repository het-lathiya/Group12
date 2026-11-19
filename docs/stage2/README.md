# Stage 2 readiness package

- Status: Proposed
- Owner: Manya (Manya Rana)
- Date: 19 November 2026
- Card: IMP-706 (US-132). Documents only.

## Position

**Fine-tuning is not part of the eight-week commitment.** Stage 2 is conditional (PD-03): it is not scheduled in weeks 1 to 8, and its go or no-go is not decided in weeks 1 to 8 (OD-13, owner: the team with the supervisor, after the MVP). Nothing in Sprints 1 to 8 depends on it.

**Stage 2 changes no MVP code and does not change `AI_PROVIDER`.** The MVP keeps GEMINI in staging and production and MOCK in local and test (§4.5). The `FINETUNED_MODEL` adapter stays a stub: its constructor and every operation raise `ProviderBadRequest("FINETUNED_MODEL not enabled in Stage 1")` (§8.4, IMD-92), and selecting it stops start-up (FR-043 AC3). `FINETUNED_ENDPOINT_URL`, `FINETUNED_API_KEY` and `FINETUNED_MODEL_NAME` stay empty (§4.5).

**Stage 2 starts only after the gates of [migration-gate-criteria.md](migration-gate-criteria.md) are met and a decision is recorded in `docs/spec/DECISION_REGISTER.md`.** PD-13 also applies: switching the default provider needs the compatibility suite, the evaluation gate, a recorded decision and a rehearsed rollback. An environment variable change alone is not enough.

## Contents

| File | What it holds |
| --- | --- |
| [migration-gate-criteria.md](migration-gate-criteria.md) | Draft gate a candidate model must pass before any provider switch, with every threshold Proposed |
| [data-governance-policy.md](data-governance-policy.md) | What data may and may not be used for training: consent, sources and licences, retention, approval |
| [dataset-schema.md](dataset-schema.md) | Fields of one training example, from the gr-1 input and the io-1 output, as a JSON Schema fragment |
| [data-card-template.md](data-card-template.md) | Template that describes any future training dataset before it is used |

## What this package does not contain

- No training code, export script, training data, fine-tuned adapter or model hosting.
- No claim of any training or fine-tuning result. No Stage 2 model has been trained or evaluated.
- No Stage 2 training store. The specification forbids one in the MVP (§4.1).

## Inputs

- `docs/spec/IMPLEMENTATION_SPEC.md`: §1.3 (Stage 2 out of scope), §2.6 (FR-048, FR-049, FR-121, FR-122 are Stage 2), §4.5, §8.4, §8.16, §8.17; FR-118 AC2; NFR-004, NFR-023, NFR-046.
- `docs/spec/AMENDMENT_A1_AWS_RAG.md`: §6.3 (guide licences), §6.14 (retrieval evaluation).
- `docs/spec/DECISION_REGISTER.md`: PD-03, PD-06, PD-08, PD-09, PD-13, OD-13, OD-17, IMD-92, IMD-176, IMD-195, IMD-200.
- `contracts/ai/gr-1.schema.json` and `contracts/ai/io-1.schema.json`.
- The evaluation baseline: [`eval/reports/baseline-1.md`](../../eval/reports/baseline-1.md) and [`eval/reports/final-baseline.md`](../../eval/reports/final-baseline.md) (IMP-705).

The card names blueprint §18.8, §22 and §33.4. The blueprint is not in the repository. Each place where these documents depend on it says "to be confirmed against blueprint §NN by Manya".
