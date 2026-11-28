# IMD-221 · traceability-a2 part (matrix: Amendment A2 and card-only stories)

- Decision: IMD-221 (course documents)
- Part: traceability-a2 (documentation only)
- Run id: RUN-100
- Owner: Malhar
- Status: PR_OPEN candidate on `feat/gemini-fallback-model`
- Base commit: 77e52ba (on `main`)
- Points: 0 (IMD-210 rule)

## What changed

- `docs/spec/TRACEABILITY_MATRIX.md`:
  - The intro names the two hand-added sections.
  - "Amendment A2 rows": 7 rows (FR-141 to FR-145, NFR-051, NFR-052) under C-14. Cards and tests come from A2 §13.2 (TC-460 to TC-491) and §13.3 (ACC-20 to ACC-23, CHK-26). A2 names no stories.
  - "Stories traced only by cards": 24 rows (US-001, US-002, US-004, US-007, US-008, US-026, US-027, US-130, US-132, US-140 to US-153, US-163). Requirements and tests come from each card's "Traces to" and "Tests" in TASK_REGISTER. Status comes from `docs/progress/parts/` and the sprint index.
  - 20 stories are on merged cards. Four are open: US-027 (IMP-603), US-143 (IMP-704), US-150 (IMP-802) and US-151 (IMP-114).

## Commands

| Command | Result line |
| --- | --- |
| ID check (every FR, NFR, US, IMP, TC, ACC, CHK, E2E and C ID in the new sections is grepped as a whole word in IMPLEMENTATION_SPEC, A1, A2 and TASK_REGISTER) | `ids checked: 178, missing: 0` |
| Row count | `A2 rows: 7; story rows: 24` |

## Acceptance

- The A2 rows and the 24 card-only stories are in the matrix, each with its cards, tests and status: verified (row counts above).
- Only existing IDs are used: verified (ID check, 0 missing).
- `docs/course/01-requirements.md` §6 says "resolved by RUN-100", with the counts: verified (RUN-101, after #303 merged; the matrix has 125 unique story IDs, `grep -oE '\bUS-[0-9]+\b' docs/spec/TRACEABILITY_MATRIX.md | sort -u | wc -l`).

## Open issues

- The matrix says it is regenerated, not edited by hand. A regeneration must keep these two sections.

## Proposed decisions

none

## Blockers

none
