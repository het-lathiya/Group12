# RUN-102 · IMP-804 draft · slides S1–S5

Owner: Jeel (`Jeel Fefar`). Base: `bc2b606e504ba167c3c5fad9d992c7500dc9fb44`.

Created `docs/course/14-slides/build_slides.py`, `slides.json`, the PowerPoint draft and the complete
and presentation-excerpt use-case PNGs. The diagram source is read from `01-requirements.md` §4.3;
no source course document is edited. The excerpt retains only existing traveller nodes/edges and
is identified in the notes. Speaker notes cite objectives, sprint themes and actual role/card assignments.
Nidhi is the course group leader under RUN-102; Kirtan remains the integration lead.

Commands:

- `uvx --from python-pptx==1.0.2 python docs/course/14-slides/build_slides.py`:
  `PPTX reload: 5 slides; titles in order; speaker notes present`.
- `uvx --from ruff==0.17.3 ruff check --select E4,E7,E9,F,I,B docs/course/14-slides/build_slides.py`:
  `All checks passed!`; formatter applied. Final `make lint` is recorded by the submission part.
- Mermaid CLI is invoked through npx; python-pptx and Chromium tooling are outside repository
  dependency manifests. Diagram PNG visually inspected; the complete source remains available for zooming.

Acceptance: S1–S5, role assignment and speaker-note sources verified in the reloaded draft.
This commit deliberately contains the first half; Manya adds S6–S10 in the next owner commit.
The five-minute slot is a course target, not a measured rehearsal. TC-397 human review and timed
rehearsal remain pending. Local full `make check`/E2E: not run — operator fast mode; CI covers.
No contracts, migrations or protected files changed. No points claimed for human completion.
