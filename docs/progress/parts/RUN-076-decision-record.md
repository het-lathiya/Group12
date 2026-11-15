# RUN-076b · decision record

- Run id: RUN-076b
- Owner: Nidhi Chauhan (0 points)
- Status: MERGED-READY
- Base commit: ce2c63d
- Files changed: docs/spec/DECISION_REGISTER.md; docs/spec/IMPLEMENTATION_SPEC.md; this record.
- Commands: preflight `git status --porcelain --untracked-files=no` → empty output; `(cd apps/api && .venv/bin/alembic heads)` → `0007 (head)`.
- Acceptance verified by document comparison: IMD-188 to IMD-192 carry the requested decisions, source, owners and 15 November 2026 date. Only the API-16 query parameter names in §6.6.3 are amended, with the IMD-190 annotation.
- Implementation of Batch C decisions, prompt activation and a recorded evaluation run are outside this batch.
- Blockers: none.
- Proposed decisions: none.
- Open issues: IMD-191's API-35 SG-6 gap remains; Batch C implements the meal and retention decisions.
