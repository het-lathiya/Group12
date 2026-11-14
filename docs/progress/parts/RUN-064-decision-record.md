# RUN-064 · decision-record part

- Run id: RUN-064 (grouped: decision-record, then IMP-499 whole-task)
- Owner: Nidhi (Nidhi9864)
- Status: PR open
- Base commit: ec6973a (gate commit of SG-4)
- Branch: feat/IMP-499-sg4-gate
- Traces to: IMD-148 (update), IMD-159 to IMD-166 (team decision of 12–13 November 2026, operator het-lathiya); SG-4 (IMP-499)

## Changed files

- `docs/spec/DECISION_REGISTER.md`: the IMD-148 row gets an "Updated 13 November 2026" note; eight new rows IMD-159 to IMD-166 after IMD-158, in the IMD-137..158 format.
- `docs/progress/parts/RUN-064-decision-record.md`: this record.

None of IMD-159 to IMD-166 was already in the register (`grep` for each ID found no earlier row). `docs/spec/IMPLEMENTATION_SPEC.md` and `docs/spec/TASK_REGISTER.md` are unchanged: none of these decisions names spec text to align. §6.2 already says inactive reference data is "invisible (404)", which IMD-166 applies to unknown destinations.

## Every changed line

| File | Where | Change | Decision |
| --- | --- | --- | --- |
| DECISION_REGISTER.md | IMD-148 row | Appended "**Updated 13 November 2026:** PD-IMP-410-3 is no longer provisional; it was confirmed on staging on 13 November 2026 (a step-1-only trip is shown under Drafts with Continue draft, and Continue draft resumes at step 2, confirmed by the operator)"; source column adds "staging confirmation of 13 November 2026" | IMD-148 |
| DECISION_REGISTER.md | after IMD-158 | IMD-159: malformed `Money.currency` answered "Currency must be a three-letter ISO 4217 code." (PD-RUN-059-1). Code change due | IMD-159 (Kirtan) |
| DECISION_REGISTER.md | after IMD-159 | IMD-160: sample file wrapper around io-1 with `place_ref` (PD-IMP-402-3, details of IMD-145) | IMD-160 (Jeel) |
| DECISION_REGISTER.md | after IMD-160 | IMD-161: fixed retrieval trip frame (PD-IMP-318-1) | IMD-161 (Junaid) |
| DECISION_REGISTER.md | after IMD-161 | IMD-162: empty denominator → null, left out of means (PD-IMP-318-2) | IMD-162 (Junaid) |
| DECISION_REGISTER.md | after IMD-162 | IMD-163: no early API-12; fresh staging account with no trips; API-12 with IMP-602 (PD-IMP-414-1) | IMD-163 (Kirtan, Manal) |
| DECISION_REGISTER.md | after IMD-163 | IMD-164: CI secrets `E2E_STAGING_EMAIL`, `E2E_STAGING_PASSWORD` (PD-IMP-414-2) | IMD-164 (Kirtan) |
| DECISION_REGISTER.md | after IMD-164 | IMD-165: staging differences switch on the staging secrets (PD-IMP-414-3) | IMD-165 (Krrish) |
| DECISION_REGISTER.md | after IMD-165 | IMD-166: API-16 404 `NOT_FOUND` for an unknown destination as for an inactive one (RUN-059) | IMD-166 (Malhar) |

## Commands and results

| Command | Result |
| --- | --- |
| `for n in 148 $(seq 159 166); do grep -c "^\| IMD-$n \|" docs/spec/DECISION_REGISTER.md; done` | `1` for every ID |
| `make lint` | `All checks passed!`; ESLint `✖ 1 problem (0 errors, 1 warning)` (a warning from before this run); `All matched files use Prettier code style!` |

## Acceptance

| Criterion | Status | How |
| --- | --- | --- |
| IMD-148 updated: PD-IMP-410-3 no longer provisional | verified | row text; operator's staging draft check of 13 November 2026 |
| IMD-159 to IMD-166 recorded in the IMD-137..158 format, owners as given | verified | rows in the register; each ID once (command above) |
| No duplicate IMD numbers | verified | same check |
| Named spec text aligned and nothing else | verified | no decision names spec text; `git diff --stat` shows only the register and this record |

## Blockers

None.

## Proposed decisions

None.

## Open issues

- IMD-159 needs a code change in `handle_request_validation_error` (Kirtan); listed in the SG-4 open items.
