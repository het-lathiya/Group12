# IMP-733 · rc-switch-readiness part (IMD-220 and the any-city readiness audit)

- Card: IMP-733 (0 points, Amendment A2 §12 Batch C3); the decide run for CHK-26
- Part: rc-switch-readiness (documents only; no code, test, contract, migration, workflow or infra change)
- Run id: RUN-095 (Sprint 7, any-city follow-up)
- Owner: Nidhi (Nidhi Chauhan)
- Status: PR_OPEN candidate on `chore/IMP-733-rc-switch-readiness`
- Base commit: 07b4395 (on `main`)
- Traces to: IMD-220, IMD-210, IMD-215 to IMD-219, CHK-26, ACC-20 to ACC-23, TC-491, PD-AC-2; A2 §1.3, §2, §3.2, §7, §13.3

## Changed files

- `docs/spec/DECISION_REGISTER.md`: the IMD-220 row after IMD-219. The number was free: no file on any remote branch holds `IMD-220` before this run.
- `docs/spec/AMENDMENT_A2_ANY_CITY.md`: §3.2, the Production row only (allowed for this run).
- `docs/acceptance/any-city.md`: one line added under CHK-26, the switch state of the release candidate.
- `docs/test-reports/any-city-readiness.md` (created): the audit, seven sections.
- This record.

## Commands

| Command | Result line |
| --- | --- |
| `make lint` | `All checks passed!`, `269 files already formatted`, `All matched files use Prettier code style!` |
| `make typecheck` | `Success: no issues found in 139 source files`, `✓ Types generated successfully` |
| `make imports` | `Contracts: 7 kept, 0 broken.` |
| `make openapi-check` | `openapi-check: contracts/, apps/web/lib/api/schema.d.ts and apps/web/lib/api/any-city-schema.d.ts are up to date` |
| `make test` (exit 0): test-unit | `1851 passed, 1 warning in 8.87s` |
| test-contract | `99 passed, 2 deselected, 1 warning in 20.01s` |
| test-api | `680 passed, 1 warning in 139.31s (0:02:19)` |
| test-authz | `91 passed, 14 skipped, 1 warning in 24.28s` |
| test-web | `Test Files  50 passed (50)`, `Tests  364 passed (364)` |
| `git diff --check` | no output (exit 0) |

Not run, by the run prompt: `make eval`, `make live-smoke`, any live import, any command that reaches Nominatim, Overpass, MediaWiki or Gemini. `make e2e` was not run: no journey is touched.

## Acceptance

- **IMD-220 recorded with (a) to (e): verified** by reading the row.
- **A2 §3.2 Production row updated, nothing else in A2: verified** (`git diff --numstat`: 1 line added, 1 removed).
- **The audit has the seven sections, each claim with a citation or "not verified": verified** by a read-through; every cited file exists (a script looked each up in `git ls-files`), and 14 cited lines were opened again as a spot check. Not every line number was re-opened.
- **The local check uses only commands that exist: verified** against the Makefile and `app/places/live_import.py`; what does not exist is listed there. It was **not executed**, so the expected results are marked not verified.
- **No live call made: verified** (only the commands above, `git` and `gh` were run).

## Proposed decisions

Each is a proposed fix of a severity-1 or -2 gap (audit section 7), with its owner:

- **PD-733-G1** (Kirtan): add the A2 §7.2 values to `api.staging.json.tmpl`.
- **PD-733-G2** (Kirtan): agree the team contact for `WIKI_USER_AGENT`.
- **PD-733-G3** (Junaid): read the Nominatim policy and the OSM credit wording and record the dates, before any real call.
- **PD-733-G4** (Kirtan): write the staging procedure for ACC-22 (MOCK timeout and back, with no release task in between).
- **PD-733-G5** (Kirtan): create the production templates, or record the production values another way, before IMP-801.
- **PD-733-G6** (team, then Krrish): decide what "every live page" means in IMD-220 (c); if A2 §10 governs, add the attribution to the summary page and the trip form.
- **PD-733-G7** (operator, Kirtan): run the local check, then TC-491 on staging.
- **PD-733-G8** (Manal): treat an Overpass answer with an error note as a failed import, and allow a forced re-import.
- **PD-733-G9** (Nidhi): a way to embed a live city's missing chunks later.
- **PD-733-G10** (Manal): check the guide page's coordinates against the city.
- **PD-733-G11** (Manal): run the start-up checks in the import CLI.
- **PD-733-G12** (Kirtan, Manal): measure memory and time of a large import; size the task if needed.
- **PD-733-G13** (Kirtan, Nidhi): put the exact one-off task command in the runbook.
- **PD-733-G14** (operator for the team): name the small town.

## Open issues

- The audit's severity-3 gaps G15 to G22 have no proposed decision.
- IMD-220 (c) does not repeat the IMD-215 cutoff; the register row says it still applies to the staging window (b).
- `docs/guides/any-city-staging.md` and `docs/final-report.md` still call PD-AC-2 proposed; they are not in this part's files (G22).
- PR #299 (IMP-732 gemini-v4-result) shows no review on GitHub and is merged; CLAUDE.md §11 asks for one approval.

## Blockers

none for this part
