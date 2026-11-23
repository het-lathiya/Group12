# IMD-219 · record-pd-730-1 part (PD-730-1 recorded as agreed)

- Decision: IMD-219 (PD-730-1, from the IMP-730 whole-task record of RUN-092)
- Part: record-pd-730-1 (documentation only; batch F is the decide run for this decision)
- Run id: RUN-093 (batch F, Sprint 7, any-city follow-up)
- Owner: Het
- Status: PR_OPEN candidate on `fix/IMP-730-run-093-followups`
- Base commit: 445080f (on `main`)
- Traces to: A2 §3.4, §13.2 TC-490; IMP-730; ACC-23

## The two tests

Both tests are named in `docs/progress/parts/IMP-730-whole-task.md` (PD-730-1) and in `docs/test-reports/any-city-switch.md`, "The two switch-ON authz failures":

1. `tests/authz/test_ownership.py::test_tc_065_an_unlisted_route_fails_the_check`
2. `tests/authz/test_route_inventory.py::test_inventory_docs_companions_are_only_fastapi_doc_pages`

## Decision number

- The register on `main` has IMD-202 to IMD-211 and IMD-213 to IMD-218, with no IMD-212 row.
- IMD-212 is taken by the PR-broker tooling on the unmerged branch `origin/chore/IMD-212-pr-broker` (commits 878cd7e and 967ca01, both titled "IMD-212 …"). That branch adds no register row, and `docs/progress/sprint-7.md` mentions the number only as "IMD-210 or IMD-212".
- So IMD-212 is left free for that branch, and this decision is **IMD-219**, the next number after IMD-218.

## Changed files

- `docs/spec/DECISION_REGISTER.md`: the IMD-219 row after IMD-218. It records PD-730-1 as agreed by the team through the operator on 24 November 2026:
  - the two tests are deselected in the switch-ON run, in addition to A2 §3.4's four;
  - they pin the OFF route set;
  - their ON counterparts are the any-city contract and authz tests;
  - the switch-OFF run is unchanged.
- `docs/spec/AMENDMENT_A2_ANY_CITY.md` §3.4: one sub-item added under the list of deselected tests. It names both tests and cites IMD-219. Nothing else in A2 changed.
  - Line shift: lines 121 and later move down by one.
  - `git grep` finds no file in the repository that cites an A2 line number, so no reference breaks.
- This record.

`docs/progress/sprint-7.md` was not edited.

## Commands

| Command | Result line |
| --- | --- |
| `git grep -nE 'AMENDMENT_A2_ANY_CITY\.md:[0-9]+\|A2[^\|]{0,25}lines? [0-9]{2,3}'` | no output (no line-number citations of A2) |
| `git branch -a --contains 878cd7e` | `remotes/origin/chore/IMD-212-pr-broker` |
| `make check` on the head | see the SYNC REPORT of RUN-093 |

## Acceptance

- **PD-730-1 recorded as agreed, with the two exact test IDs: verified.** See the IMD-219 row.
- **A2 §3.4 names the two extra deselected tests and cites IMD-219: verified.** It is a one-line diff (`git diff --stat`: 1 insertion).

## Proposed decisions

none

## Open issues

- When `chore/IMD-212-pr-broker` merges, it should add its own IMD-212 row to the register.

## Blockers

none
