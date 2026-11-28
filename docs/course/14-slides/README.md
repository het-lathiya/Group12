# IT314 course presentation draft

Group 12 · IT314 Software Engineering · Autumn 2026-27. Course group leader: **Nidhi**
(RUN-102 assignment); product integration lead remains Kirtan. Jeel owns S1–S5 and Manya S6–S10.
This is the requested IMP-804 draft, not a claim of human completion or a rehearsed presentation.

## Rebuild

Use an external tool environment; no repository dependency manifest or lockfile changes:

```sh
uvx --from python-pptx==1.0.2 python docs/course/14-slides/build_slides.py
```

The script uses `npx @mermaid-js/mermaid-cli@12.2.0`, an installed Chromium browser and
`python-pptx==1.0.2`. Set `PUPPETEER_EXECUTABLE_PATH` if Chromium is not on PATH or in the
Playwright browser cache. The complete Mermaid diagram is extracted from `01-requirements.md`
§4.3; `use-cases.png` preserves it and `use-cases-focus.png` is the labelled traveller-goal
excerpt used on S5. Protected source documents are read only.

`--reuse-diagram` reuses the committed PNGs. `--html <path>` also exports a printable HTML view
from the same slide content; the submission builder prints that view with Chromium. Speaker
notes remain in the PPTX. `slides.json` holds the authored content, source snapshot and recorded
result lines. Build output reloads with python-pptx and verifies titles, speaker notes and placeholders.

## Slide order and sources

| Slide | Exact title | Sources / speaker-note basis |
| --- | --- | --- |
| S1 | Title | `01-requirements.md`, `docs/srs.md` §1; course/year/group from RUN-102 |
| S2 | Group leader and detailed task assignment | Role table in specification; TASK_REGISTER owner/part rows; Nidhi's course leadership from RUN-102; detailed ledger in `15-contribution.md` |
| S3 | Objectives | Requirements FR-007–010, FR-024–076, FR-136–139; IMD-46 exclusions |
| S4 | Milestones | `02-sprints/sprint-1.md` through `sprint-8.md`; progress sprint indexes and gates; SG-7 provisional and SG-8 not run |
| S5 | Use case diagram / user story backlog by sprint | `01-requirements.md` §4.3 and §5. UC IDs are local course identifiers; unrecorded story sentences are not invented |
| S6 | Lessons learnt | RUN-099 mutation setup correction and direct mutant/control check in its part record and raw summary |
| S7 | Achievements | Implemented journey/feature-freeze records; the exact coverage and local mutation summaries from PR #302, pinned below |
| S8 | Mistakes | Security report F-1 and regression evidence; IMP-702 auth-fix record; SG-7 working-agreement audit and pending staging evidence |
| S9 | Rating of software artefacts (0–5) | RUN-102 course scale; every value remains `[team to fill]` |
| S10 | Overall project rating (out of 10) | RUN-102 course scale; value remains `[team to fill]`; Stage 2 remains conditional and not done |

The recorded testing snapshot is Git object `b40b00a54011a5d2120341cd2d2d5569c4b6d0d9`, read
with `git show` from `origin/chore/course-docs-b`; that branch/worktree was not modified.
Coverage was measured at `b3248cf` in
[Course reports 46124142747](https://github.com/het-lathiya/Group12/actions/runs/46124142747).
Mutation values are bounded **local** runs, with the command/result lines in PR #302's
`docs/test-reports/course/mutation-*-summary.txt`; they are not CI mutation results.
`slides.json.testing_evidence` captures those source lines and the branch snapshot.

## Timing and team completion

The course target is five minutes. The notes allocate **300 seconds as a proposed speaking plan**,
not a measured result. The build checks that sum; it cannot verify a human rehearsal fits.

The team must fill/confirm:

- Presenter and hand-offs; run and record a timed rehearsal.
- All S9 artefact ratings and the S10 overall rating, jointly agreed.
- The contribution document's `[team to decide; default equal]` marks line and all signatures.
- TC-397 manual claims review by Junaid, final source/release candidate and open staging evidence.
- Live URL, YouTube link and repository URL in the final submission links sheet.
- Course item 10 is **Source code** (RUN-102 clarification): the selected ref is exported to
  `source/` with git archive, with no PDF; INDEX records the ref and commit. The protected index
  still needs that row added later.
- The later index rows for 14 (this deck) and 15 (contribution MD/PDF); RUN-102 lists those rows
  in the PR body and deliberately does not edit the index.

Local full `make check`/E2E: not run — operator fast mode; CI covers.
