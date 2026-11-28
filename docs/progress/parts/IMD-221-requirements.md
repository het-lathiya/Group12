# IMD-221 · requirements

- Run: RUN-098 (course documents A)
- Owner: Nidhi (Nidhi Chauhan)
- Status: PR_OPEN
- Base commit: 77e52ba
- Points: 0 (IMD-221)
- Changed files: docs/course/01-requirements.md
- Commands: relative-link check over `docs/course/` (script in the run, all links resolve); `make lint` and `make check` not run (operator fast mode; CI covers)
- Acceptance: every class, method, endpoint, table, state and test name in the files was taken from the code or the specification at `77e52ba` (verified by reading the code in the run); facts not in the repository are written "not recorded"
- Blockers: none
- Proposed decisions: none
- Open issues: the spec has no UC IDs (UC-01 to UC-15 are assigned in the document); story sentences are not recorded in the repository; TRACEABILITY_MATRIX lacks FR-141 to FR-145 and 24 card-only story IDs (listed in section 6 of the document)
