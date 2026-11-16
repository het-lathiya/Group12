# RUN-079 · decision-record part (IMD-199)

- Part: record IMD-199, evaluation default prompt version (0 points)
- Run id: RUN-079
- Owner: Nidhi (Nidhi Chauhan)
- Status: PR_OPEN candidate on `chore/S6-E-v3-eval`
- Base commit: 3a68439 (on `main`)
- Traces to: IMD-199, IMD-195, IMD-188, RUN-078 reading of the default

## Changed files

- `docs/spec/DECISION_REGISTER.md`: row IMD-199 after IMD-198, same format, dated 16 November 2026, planner decision under the operator's rule of 14 November 2026, owner Manya.
- `docs/progress/parts/RUN-079-decision-record.md` (this record).

## Acceptance

- IMD-199 states that without `--prompt-version` each dataset request runs the version it names (trips/v1 → v1), that v2 and v3 runs pass the option explicitly, and that every report states which applied: **verified** by reading the row. It records the behaviour RUN-078 already implemented; no code changed.

## Commands

See `RUN-079-v3-evaluation.md` (the checks ran once for the whole branch).

## Blockers, proposed decisions, open issues

none
