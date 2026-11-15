# RUN-078 · decision-record

- Run id: RUN-078
- Owner: Nidhi Chauhan, 0 points (follow-ups of RUN-077)
- Status: done
- Base commit: b715d26
- Scope: record the planner decisions on the RUN-077 proposed decisions PD-RUN-077-E1, E2, M1, M2 and V1, and amend the MOCK `ok` scenario wording of specification §8.4.

## Files changed

- docs/spec/DECISION_REGISTER.md: rows IMD-195 to IMD-198, same table format, dated 16 November 2026, source "Planner decision under the operator's rule of 14 November 2026 (the planner's recommendation is the final call)".
  - IMD-195 Prompt version in evaluation and v3 activation gate (PD-RUN-077-E1, E2; amends IMD-188). Owner Manya.
  - IMD-196 Lunch reserved in rule-based plans (PD-RUN-077-M1). Owner Manya.
  - IMD-197 MOCK ok scenario wording (PD-RUN-077-M2). Owner Nidhi.
  - IMD-198 One backup with versions off already met (PD-RUN-077-V1). Owner Malhar.
- docs/spec/IMPLEMENTATION_SPEC.md §8.4: only the `ok` row of the `MOCK_PROVIDER_SCENARIO` table changes. It now says the scenario plans lunch from a food place of the shortlist, otherwise an empty meal slot with the note, followed by "(amended by IMD-197)". Nothing else changes.
- docs/progress/parts/RUN-078-decision-record.md: this record.

## Commands and results

- `git diff --stat` on the two specification files: `2 files changed, 5 insertions(+), 1 deletion(-)`
- Documentation only. The batch-wide `make check` is in the batch PR.

## Acceptance

- IMD-195 to IMD-198 are in the register with the given wording, date and owners: verified by reading the diff.
- §8.4 changes only the MOCK ok scenario sentence and cites IMD-197: verified by reading the diff (one line changed).

## Blockers, proposed decisions, open issues

- Blockers: none.
- Proposed decisions: none.
- Open issues: none.
