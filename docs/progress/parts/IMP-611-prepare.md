# IMP-611 · prepare

- Run id: RUN-075
- Owner: Junaid (Mohammad Junaid Kureshi), with Krrish (Krrish Kamani) for `findings.md`
- Status: prepared (templates only, 0 points now). The card stays open: the sessions, findings and issues are human work after the real usability session.
- Base commit: a6307c3
- Traces to: IMP-611; US-142; NFR-027; IMD-185

## Files changed

- `docs/acceptance/usability-1/plan.md` (Junaid): goal, set-up, privacy rules, consent wording, task script T1 to T7, observation sheet, after-session steps. Participant codes P1 to P5 only.
- `docs/acceptance/usability-1/findings.md` (Krrish, separate commit): severity scale and an empty finding table (participant code, observation, severity, issue link, owner).
- This record.

## Commands and exact results

| Command | Result |
| --- | --- |
| `grep -ciE 'p[1-5]' docs/acceptance/usability-1/findings.md` (finding rows are empty) | checked by review: the table has header rows only |

## Acceptance

- Five sessions recorded with observed behaviour (US-142 AC1): not verified (human activity, not yet run).
- Top issues exist as backlog items with owners (US-142 AC2): not verified (human activity, not yet run).
- No result is reported that was not observed: verified (both files are templates; no result, participant data or identifying detail is written).

## Blockers, proposed decisions, open issues

- Open: the team runs five sessions on staging in a staging window (IMD-137) and fills `findings.md`; Junaid and Krrish then claim the card's points.
