# IMP-804 · presentation-outline part

- Run id: RUN-087
- Owner: Jeel (part "Presentation slides")
- Status: PR_OPEN (draft outline; the slides file, the rehearsal and the claims-check review are pending)
- Base commit: 4fe514c (`4fe514cfa015f0b9ebd87c4a96c7daa04a4a2958`, `main`, the SG-7 release-candidate commit)
- Branch: chore/S7-D-gate-report (batch branch of RUN-087; card branch name `feat/IMP-804-<part>`)
- Traces to: US-148 (AC1, AC2); NFR-041; TC-397
- Card step built: 3 (prepare the presentation), as an outline only, drafted from the final report under step 4. The presentation file itself (the slides) is pending (Jeel); this record covers the outline.

## Changed files

- `docs/presentation/outline.md` (created): slide-by-slide outline (title, problem, users, features shipped, demo flow pointer, architecture, AI and evaluation, testing, limitations, Stage 2, team), each with on-slide bullets, speaker notes and a target slot time "to be measured in rehearsal (Jeel)"
- `docs/final-report-claims-check.md` (modified by the lead from this part's text): section "Presentation outline (docs/presentation/outline.md)" with rows O1 to O28, one per numeric claim of the outline, each pointing to the report section and the claims-check row of its source
- `docs/progress/parts/IMP-804-presentation-outline.md` (created)

## Sources used

`docs/final-report.md` (sections 1 to 4 and 6 to 10) and its section 5 (AI chapter), with their claims-check rows 1 to 75. No figure was taken from any other file. Non-numeric content: `docs/srs.md` §2.2 (user classes), `docs/guides/user-guide.md` (journey sections), `docs/spec/TASK_REGISTER.md` (IMP-801 and IMP-804 owners) and the specification's Appendix C (member areas, without point totals).

## Commands run

All read only, 22 November 2026, in the main checkout at `4fe514c`. No test, evaluation or model call was run.

| Command | Result line (quoted exactly) |
| --- | --- |
| `stat -f %m` on `docs/final-report.md`, `docs/final-report-claims-check.md` and the AI chapter files, polled until none had changed for 3 minutes | `stable age=191` (the outline was then rebuilt from the pruned report) |
| `grep -F` of every outline figure, as written in the report, against `docs/final-report.md`, and of each cited row number against `docs/final-report-claims-check.md` | all figures `OK`; no cited row missing |
| `ls docs/demo` | `ls: /Users/nidhi/Group12/docs/demo: No such file or directory` |

## Not run

| Command | Reason |
| --- | --- |
| Rehearsal of the presentation against the slot | Human activity; pending (Jeel) |
| `make check` | This part changes only Markdown documents; the lead runs the checks before the commit |

## Acceptance criteria

| Criterion | Status (verified / not verified) | How |
| --- | --- | --- |
| The presentation fits the time slot in rehearsal (US-148 AC2) | not verified — pending (Jeel) | No slides file and no rehearsal yet; the slot length and every slide's slot time are marked "pending (Jeel)" and "to be measured in rehearsal (Jeel)" |
| The presentation states the Stage 2 position honestly (US-148 AC2) | verified (draft) | Slide 10 "Stage 2: conditional and not done" states that Stage 2 is conditional and not done, that the `FINETUNED_MODEL` adapter is a stub, that the readiness package is Proposed with no training code, data or result, and that no model has been trained or evaluated (report sections 5.8 and 9) |
| Every numeric claim in the slides appears in the claims check with a linked record (US-148 AC1, TC-397) | verified (draft); review by Junaid pending | Each number in the outline has a row O1 to O28 that names its report section and source row; the check was repeated after the report stopped changing. The manual review (TC-397) is Junaid's |

## Blockers

None for the outline. The slides file depends on Jeel; the demo slide points to IMP-801 (demo script and backup video, Kirtan and Nidhi), which is pending.

## Proposed decisions

None.

## Open issues

- Slides file in `docs/presentation/` (format to be chosen by Jeel), built from this outline: pending (Jeel), due 26 November 2026.
- Slot length and rehearsal timing: pending (Jeel), due 26 November 2026.
- Demo script, rehearsal log and backup video: IMP-801, pending (Kirtan, Nidhi); `docs/demo/` does not exist.
- Ahmedabad saved sample itineraries (FR-036 AC3), used by the demo: pending (Jeel).
- If a figure in the final report changes, the outline and rows O1 to O28 change in the same change.
