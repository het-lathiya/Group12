# RUN-075 · decision-record

- Run id: RUN-075
- Owner: Nidhi (Nidhi Chauhan)
- Status: done (documentation only, 0 points)
- Base commit: a6307c3
- Decisions: IMD-187 (new), IMD-183 (note added)

## Files changed

- `docs/spec/DECISION_REGISTER.md`: new row IMD-187 after IMD-186 ("`ranking_explain` needs no FEATURES_DISABLED entry: IMP-515 was never built (cut, IMD-186)"), dated 15 November 2026, same reason wording as IMD-180 to IMD-186, owner Nidhi. The IMD-183 row ends with "Amended by IMD-185."
- This record.

## Commands and exact results

| Command | Result |
| --- | --- |
| `grep -c '^| IMD-187 |' docs/spec/DECISION_REGISTER.md` | `1` |
| `grep -c 'Amended by IMD-185' docs/spec/DECISION_REGISTER.md` | `1` |

## Acceptance

- IMD-187 row present in the confirmed-decisions table with the run's wording, date and owner: verified (grep above, diff review).
- IMD-183 row carries "Amended by IMD-185": verified (grep above).

## Blockers, proposed decisions, open issues

None.
