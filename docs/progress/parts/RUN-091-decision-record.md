# RUN-091 · decision-record part (IMD-217)

- Part: record IMD-217, the team's answer to PD-725-1 (RUN-090) and the closing of PD-A2-8 (RUN-089) (0 points)
- Run id: RUN-091 (Batch C2, Sprint 7, inserted under IMD-215)
- Owner: Nidhi (Nidhi Chauhan)
- Status: PR_OPEN candidate on `feat/S7-C2-any-city-ai-web`
- Base commit: 667c0d8 (on `main`)
- Traces to: IMD-217; reads Amendment A2 §6.2 ("A failed import leaves earlier places as they were"); keeps IMD-210, IMD-215, IMD-216

## Changed files

- `docs/spec/DECISION_REGISTER.md`: row IMD-217 appended after IMD-216 in the confirmed decisions table, same format, dated 23 November 2026, "decided by: team (via operator Nidhi)".
- `docs/progress/parts/RUN-091-decision-record.md` (this record).

## What IMD-217 says

- **PD-725-1 agreed.** A refresh of an already active live destination that ends `insufficient_data` or `failed` keeps the destination active, with its earlier places and guide chunks. The import state records the failed refresh. Users never lose a working city because of a provider outage. The A2 §6.2 line "A failed import leaves earlier places as they were" is read this way. The code of IMP-725 already behaves like this.
- **PD-A2-8 closed without change.** `LIVE_DAILY_IMPORTS_GLOBAL` stays 50 (operator, 23 November 2026).

PD-IMP-799-2 (from RUN-087) is not recorded and stays open.

## Acceptance

- IMD-217 is in the register's existing format, with the date and "decided by" text of the run prompt: **verified** by reading the row after the edit.
- No code and no amendment text changed in this part: **verified** (`git diff --stat` lists the register, with 1 insertion, and this record only).

## Commands

| Command | Result line |
| --- | --- |
| `git diff --check` | no output (exit 0) |

`make check` and the attribution checks ran once on the branch head. Their result lines are in the SYNC REPORT of RUN-091.

## Proposed decisions (not decided; for the team)

- **PD-IMP-799-2** (from RUN-087) stays open: the SG-7 live smoke has no workflow.

## Blockers and open issues

none
