# IT314 course documents: index

| Item | Value |
| --- | --- |
| Project | AI Travel Planner (Group 12) |
| Decision | [IMD-221](../spec/DECISION_REGISTER.md) (course deliverables under `docs/course/`, 0 points) |
| Built from | `main` at `77e52ba`, the specification v1.3 with [Amendment A1](../spec/AMENDMENT_A1_AWS_RAG.md) and [Amendment A2](../spec/AMENDMENT_A2_ANY_CITY.md), the registers in `docs/spec/` and the records in `docs/progress/` |
| Precedence | Where a course document and the specification disagree, the specification wins (CLAUDE.md §13) |

## Course rules (IMD-221)

- One file per document, all under `docs/course/`.
- The submission is one ZIP file named `<group_No>.zip`.
- The live URL must work for the whole evaluation period.
- The repository is frozen after 3 December 2026, 23:59 IST.

## Documents

Batch A is produced by RUN-098. Batch B is planned. Its titles are not recorded yet, so the rows say "not recorded" until the batch B run adds them.

| No. | Document | File | Batch | Owner (part) | Status |
| --- | --- | --- | --- | --- | --- |
| 01 | Requirements, use cases and user stories | [01-requirements.md](01-requirements.md) | A | Nidhi | draft (RUN-098) |
| 02 | Sprint details, Sprints 1 to 8 | [02-sprints/](02-sprints/): [sprint-1](02-sprints/sprint-1.md), [sprint-2](02-sprints/sprint-2.md), [sprint-3](02-sprints/sprint-3.md), [sprint-4](02-sprints/sprint-4.md), [sprint-5](02-sprints/sprint-5.md), [sprint-6](02-sprints/sprint-6.md), [sprint-7](02-sprints/sprint-7.md), [sprint-8](02-sprints/sprint-8.md) | A | Malhar (1 to 4), Jeel (5 to 8) | draft (RUN-098) |
| 03 | System design | [03-system-design.md](03-system-design.md) | A | Het | draft (RUN-098) |
| 04 | Object design | [04-object-design.md](04-object-design.md) | A | Manal | draft (RUN-098) |
| 05 | not recorded | not recorded | B | not recorded | planned |
| 06 | not recorded | not recorded | B | not recorded | planned |
| 07 | not recorded | not recorded | B | not recorded | planned |
| 08 | not recorded | not recorded | B | not recorded | planned |
| 09 | not recorded | not recorded | B | not recorded | planned |
| 10 | not recorded | not recorded | B | not recorded | planned |
| 11 | Design diagrams (activity and state) | [11-design-diagrams.md](11-design-diagrams.md) | A | Manal | draft (RUN-098) |
| 12 | Not implemented | [12-not-implemented.md](12-not-implemented.md) | A | Jeel | draft (RUN-098) |
| 13 | UI/UX | [13-ui-ux.md](13-ui-ux.md) | A | Manasvi | draft (RUN-098) |
| 14 | not recorded | not recorded | B | not recorded | planned |
| 15 | not recorded | not recorded | B | not recorded | planned |

## Project documents the course documents use

These were written before the course set. They stay where they are, and the course documents link to them.

| Document | File |
| --- | --- |
| Software requirements specification (IMP-707) | [docs/srs.md](../srs.md) |
| Architecture (IMP-707) | [docs/architecture.md](../architecture.md) |
| API description (IMP-707) | [docs/api.md](../api.md) |
| Test plan (IMP-707) | [docs/test-plan.md](../test-plan.md) |
| Final report draft (IMP-804) | [docs/final-report.md](../final-report.md) |
| Sprint indexes and gates | [docs/progress/](../progress/), [gates.md](../progress/gates.md) |

## How these documents were checked

- Every class, method, endpoint, table, state and test name was taken from the code or the specification at `77e52ba`.
- Where a fact is not in the repository, the document says "not recorded".
- Diagrams are Mermaid blocks, which GitHub renders.
- Relative links were checked with a script in RUN-098. Whether the Mermaid blocks render is recorded in that run's SYNC REPORT.
