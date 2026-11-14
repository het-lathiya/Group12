# IMP-514 · gemini-baseline part

- Run id: RUN-070 (Sprint 5 batch C)
- Owner: Nidhi (Nidhi Chauhan)
- Status: committed on `feat/S5-C-keyboard-a11y`
- Base commit: 15475eb (the evaluation ran from a clean detached checkout of `main` at this commit, IMD-176)
- Traces to: US-129, US-130; FR-120; NFR-041, NFR-042, NFR-046
- Card steps built: 4 (step 5 not needed: Gemini was available)

## Changed files

- `eval/results/20261114T104200Z-gemini/run.json` (created): the GEMINI run record of dataset trips/v1, `git_commit` 15475eb. As for the earlier records, only `run.json` is committed; `scores.json` and `raw/` were written and not committed.
- `eval/reports/baseline-1.md` (created): dataset size 15, metric values, observed prompt problems and the statement that no claim is made beyond these 15 trips.

## Commands and results

| Command | Result |
| --- | --- |
| `make eval PROVIDER=GEMINI DATASET=trips/v1` (clean detached checkout of 15475eb; key read by the application from the untracked `apps/api/.env`, never printed or passed on a command line) | `evaluation 20261114T104200Z-gemini: 45 attempts, written to .../eval/results/20261114T104200Z-gemini` |
| Secret scan of `run.json`, `scores.json` and `raw/` (`grep -ciE 'api[_-]?key\|AIza'`) | 0 matches |

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| TC-391: eval/results contains a GEMINI run record for dataset v1 | verified | `eval/results/20261114T104200Z-gemini/run.json`: provider GEMINI, model `gemini-3.5-flash-lite`, case_count 15, 45 attempts, 1 failure (`schema_violation`) |
| PR-12: the baseline note states the dataset size and makes no claim beyond it | verified | `eval/reports/baseline-1.md`, sections "Dataset size" and "What this baseline does not claim" |

## Blockers

none

## Proposed decisions

- **PD-IMP-514-3: the label is added by the application, not the model.** The v1 prompt says notes "are labelled AI-written"; Gemini writes "AI-written:" into 492 of 557 notes and 38 of 60 assumptions. The prompt (a new version) should say the application adds the label.
- **PD-IMP-514-4: meal reuse.** 87 meal items reuse a place already in the same plan; decide whether that is allowed and say so in the prompt.

## Open issues

- One `schema_violation` in 45 attempts (`trips-v1-010`, repeat 2); the other repeats of that trip were valid.
