# IMP-801 · release-notes-draft part (v1.0-mvp release notes draft)

- Card: IMP-801, part "Production deployment, smoke tests, RC tag" (release notes draft only; 0 points in this run)
- Run id: RUN-096 (batch H, Sprint 8 prep)
- Owner: Kirtan (chaudhari kirtan sandipbhai)
- Status: PR_OPEN candidate on `fix/RUN-096-batch-h`
- Base commit: 5fa8e6d (on `main`)
- Traces to: US-147; IMD-46, IMD-65, IMD-200, IMD-215, IMD-220; A2 §1.2, §1.3

## Changed files

- `docs/release-notes/v1.0-mvp.md` (created; it did not exist)
- `docs/progress/parts/IMP-801-release-notes-draft.md` (this record)

## Commands

Documents only. The run checks on the branch head are in the SYNC REPORT of RUN-096.

## Acceptance

- **What ships, what is cut, switch state, limitations, prompt, migration head, upgrade and rollback: verified** by reading against the named sources.
- **Every number has a source: verified** (22 of 45: `final-baseline.md`; 1 of 24: `live-v1-gemini-2026-11-25.md`; `0008`: `health.py`).
- **Production deployment, smoke, tags: not verified** — pending (Kirtan).
- **No workflow edit: verified** by the diff.

## Proposed decisions

none

## Open issues

- Tag, commit, date, switch state and smoke result are filled at IMP-801.

## Blockers

none for the draft
