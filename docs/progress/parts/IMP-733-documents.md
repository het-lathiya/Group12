# IMP-733 · documents part (acceptance sheet, staging runbook, user guide, report chapter)

- Card: IMP-733 Documents: acceptance record, guides, report addendum and environment (Amendment A2 §12 Batch C3; 0 points)
- Part: documents (lead). The environment documentation is Kirtan's part (`IMP-733-environment.md`).
- Run id: RUN-092 (Batch C3, Sprint 7, inserted under IMD-215)
- Owner: Nidhi (Nidhi Chauhan)
- Status: PR_OPEN candidate on `feat/S7-C3-any-city-verify`
- Base commit: 818c1d8 (on `main`)
- Traces to: ACC-20 to ACC-23, CHK-26; TC-491; IMD-210, IMD-215 to IMD-218; PD-AC-2

## Changed files

- `docs/acceptance/any-city.md` (created): the ACC-20 to ACC-23 sheet, all "pending (Kirtan staging window, 28 Nov)", with supporting tests; the CHK-26 table, with the switch state "to be recorded at the cutoff".
- `docs/guides/any-city-staging.md` (created): the pre-import runbook (`python -m app.places.live_import --query "<city>"`, demo cities Jaipur, Udaipur, Mumbai and one small town, PD-AC-2 still proposed), what to record (TC-491), and rollback.
- `docs/guides/user-guide.md`: a new section 13, "Any city (live data)", with the A2 §9.1 states and copy, the §9.2 labels and the live-data limits. Earlier sections are not renumbered.
- `docs/final-report.md`: a new section 11, "Any-city mode", covering the decisions, what was built, the cut list, evidence, pending items and the switch state "to be recorded at the cutoff".
- `docs/final-report-claims-check.md`: rows A1 to A3 for every number of section 11.

## Acceptance

- Every number in the new chapter is in the claims check, with its RUN-092 source: **verified** by reading section 11 against rows A1 to A3.
- The acceptance rows are pending and name the staging window: **verified**.
- No guide prose for a real destination was written: **verified** (this part adds documentation only).

## Commands

| Command | Result line |
| --- | --- |
| `git diff --check` | no output (exit 0) |

## Proposed decisions

none (PD-AC-2, the demo cities, stays proposed)

## Open issues

- The switch state and the ACC rows are filled in after the cutoff and the staging window.

## Blockers

none
