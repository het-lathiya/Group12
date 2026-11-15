# Sprint 5 index (week 5): Core trip management — gate SG-5

One line per task part of Sprint 5 (task register). Evidence lives in the part records under `docs/progress/parts/`; the gate card IMP-599 compiles this index from them. The Status column comes from the merged pull requests, not from the records' own status lines, which were written before merging. The Acceptance column is copied from each part record and is not upgraded here.

Compiled by IMP-599 on 15 November 2026 from the part records and the merged pull requests #275 to #279 on `main` at `43a4240`. All five were merged on 14 November 2026 (UTC). Gate result: see [gates.md, SG-5](gates.md#sg-5-end-of-week-5-trip-management-imp-599).

Where a record says its API or database cases were "written, not run" or "awaiting CI", those cases are part of the CI `api` job, which passed on the merged heads and on `main` at `43a4240` ([CI 43601520229](https://github.com/het-lathiya/Group12/actions/runs/43601520229), push, all of `lint-types`, `unit`, `guards`, `audit`, `api` success). That is a suite-level result; this index does not turn a record's "not verified" into "verified" per criterion.

| Task | Title | Part | Owner | Points | Run | Pull request | Merged | Status | Acceptance (from the part record) | Part record |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| IMP-501 | Opening-hours check, overpacked days and budget conflicts | hours-checks | Junaid (lead) | 3 | RUN-069 | #276 | 14 November 2026 | merged | verified by unit tests (FR-052, TC-180, TC-181, TC-301, TC-302, FR-053, TC-182, TC-183, TC-303); API-32 persistence test written, not verified in the part run (no PostgreSQL) | [record](parts/IMP-501-hours-checks.md) |
| IMP-501 | Opening-hours check, overpacked days and budget conflicts | budget-conflict | Manal | 2 | RUN-069 | #276 | 14 November 2026 | merged | verified (FR-054, TC-184, TC-185, TC-304, COST_INCOMPLETE, ESTIMATE_USED); database-backed evidence not verified in the part run | [record](parts/IMP-501-budget-conflict.md) |
| IMP-502 | Bounded repair with at most one model retry | whole-task | Nidhi (lead) | 5 | RUN-068 | #275 | 14 November 2026 | merged | verified (unit and API: FR-057 AC1 to AC3, TC-190 to TC-192, TC-011, TC-313 repair part); completion evidence "API-23 JSON of a model_repaired generation, make check green" not verified | [record](parts/IMP-502-whole-task.md) |
| IMP-503 | Pace presets and grouping nearby places into days | pace-grouping | Manya (lead) | 6 | RUN-068 | #275 | 14 November 2026 | merged | verified (TC-129, TC-130 at unit level, TC-131, TC-132, FR-030 AC2); `make check` not verified in the part run | [record](parts/IMP-503-pace-grouping.md) |
| IMP-503 | Pace presets and grouping nearby places into days | pace-control | Manasvi | 1 | RUN-069 | #276 | 14 November 2026 | merged | verified (saved default, changed pace, API-14 body); stale-plan journey after generation waits for CI and IMP-607 | [record](parts/IMP-503-pace-control.md) |
| IMP-504 | Add a user-selected place and reject stale edits | add-place-api | Het (lead) | 3 | RUN-068 | #275 | 14 November 2026 | merged | verified in the integration fix run (TC-202, TC-203, TC-217); day 0 answers 422 VALIDATION_ERROR, not INVALID_EDIT (PD-IMP-504-2) | [record](parts/IMP-504-add-place-api.md) |
| IMP-504 | Add a user-selected place and reject stale edits | place-picker | Malhar | 2 | RUN-069 | #276 | 14 November 2026 | merged | verified by component tests (FR-062, FR-069, undo); screenshots and E2E not verified | [record](parts/IMP-504-place-picker.md) |
| IMP-505 | Replace an activity with a ranked alternative | replace-api | Het (lead) | 3 | RUN-068 | #275 | 14 November 2026 | merged | verified in the integration fix run (TC-208, TC-209, TC-210, TC-372 API side, stale 409); ranking order verified by unit test | [record](parts/IMP-505-replace-api.md) |
| IMP-505 | Replace an activity with a ranked alternative | alternatives-dialog | Krrish | 2 | RUN-069 | #276 | 14 November 2026 | merged | verified by component tests; API cases left to CI; screenshot not verified | [record](parts/IMP-505-alternatives-dialog.md) |
| IMP-506 | Lock and unlock items | lock-api | Het (lead) | 2 | RUN-069 | #276 | 14 November 2026 | merged | TC-313 repair verified; TC-211, TC-212 API, must-visit save, flag floor and owner-scoped loading not verified in the part run (tests written for CI) | [record](parts/IMP-506-lock-api.md) |
| IMP-506 | Lock and unlock items | lock-toggle | Krrish | 1 | RUN-069 | #276 | 14 November 2026 | merged | verified by component tests (keyboard, aria-pressed, switch off); screenshot not verified | [record](parts/IMP-506-lock-toggle.md) |
| IMP-507 | Daily and category cost breakdown; estimate labels on every screen | breakdown-api | Manal (lead) | 3 | RUN-068 | #275 | 14 November 2026 | merged | verified (TC-225, TC-300, API-33 fields unchanged); TC-226 API test not verified in the part run | [record](parts/IMP-507-breakdown-api.md) |
| IMP-507 | Daily and category cost breakdown; estimate labels on every screen | costs-page | Manasvi | 2 | RUN-069 | #276 | 14 November 2026 | merged | verified (TC-282, TC-226 component path); TC-385 live-stack label review and screenshots not verified | [record](parts/IMP-507-costs-page.md) |
| IMP-508 | Map with numbered markers and list fallback | whole-task | Manasvi (lead) | 5 | RUN-068, RUN-070, RUN-070b, RUN-071b | #275, #277, #278 | 14 November 2026 | merged; map worker fixed in RUN-071b | verified at component level (TC-238, TC-239, TC-240); RUN-071b worker fix verified by unit test and a local build; map spec in CI was pending in the record (passed later in [E2E 43597245631](https://github.com/het-lathiya/Group12/actions/runs/43597245631) and [43600301340](https://github.com/het-lathiya/Group12/actions/runs/43600301340), step "Run the map specs"); screenshots not taken; OpenFreeMap terms Unverified | [record](parts/IMP-508-whole-task.md) |
| IMP-509 | Browse places with source labels | whole-task | Jeel (lead) | 3 | RUN-068 | #275 | 14 November 2026 | merged | verified on the web side (TC-092, TC-093, TC-094); API cases (limit 51, other destination, 401) not verified in the part run | [record](parts/IMP-509-whole-task.md) |
| IMP-510 | Edit trip settings and flag a stale plan | settings-api | Manal (lead) | 1 | RUN-068 | #275 | 14 November 2026 | merged | TC-080, TC-081, step 6 and ownership not verified in the part run (tests written for CI); draft behaviour (IMD-148) verified | [record](parts/IMP-510-settings-api.md) |
| IMP-510 | Edit trip settings and flag a stale plan | edit-page | Krrish | 1 | RUN-069 | #276 | 14 November 2026 | merged | verified by component tests (edit mode, stale banner); screenshot not verified; API-31 regeneration is IMP-607 | [record](parts/IMP-510-edit-page.md) |
| IMP-511 | Rate limits and daily generation caps | whole-task | Kirtan (lead) | 5 | RUN-069 | #276 | 14 November 2026 | merged | verified by unit tests (TC-294, cap boundary, reset time); API cases TC-171, TC-172, TC-173, TC-310, TC-311, TC-353 not verified in the part run; provider spending limit Awaiting validation | [record](parts/IMP-511-whole-task.md) |
| IMP-512 | Provider contract test suite for all adapters | whole-task | Junaid (lead) | 3 | RUN-068 | #275 | 14 November 2026 | merged | verified (TC-156 to TC-158, TC-001 to TC-005, TC-008 at contract level, no network); Gemini recordings are still hand-written fixtures | [record](parts/IMP-512-whole-task.md) |
| IMP-513 | Keyboard and assistive-technology support | whole-task | Krrish (lead) | 3 | RUN-070, RUN-070b, RUN-071, RUN-071c | #277, #278 | 14 November 2026 | merged; contrast and focus fixed in RUN-071 and RUN-071c | unit parts verified (TC-280, focus fallback, below 768 px); TC-279, TC-374, TC-383 marked not verified in the record (E2E deferred; the journey later passed in [E2E 43600301340](https://github.com/het-lathiya/Group12/actions/runs/43600301340)); TC-382 belongs to IMP-703 | [record](parts/IMP-513-whole-task.md) |
| IMP-514 | Evaluation run records and first Gemini baseline | run-records | Manya (lead) | 2 | RUN-068 | #275, #276 | 14 November 2026 | merged | verified (TC-287, TC-390, no key or prompt body); MOCK run in CI not verified in the record | [record](parts/IMP-514-run-records.md) |
| IMP-514 | Evaluation run records and first Gemini baseline | gemini-baseline | Nidhi | 1 | RUN-070 | #277 | 14 November 2026 | merged | verified (TC-391: GEMINI run record, dataset `trips` v1, 15 cases × 3 repeats, git commit `15475eb`; PR-12: [baseline-1.md](../../eval/reports/baseline-1.md), usable outputs 44 / 45) | [record](parts/IMP-514-gemini-baseline.md) |
| IMP-515 | Explain the ranking: "Why this place?" panel | — | Jeel (lead), Krrish | 4 | none | none | — | **cut** (IMD-65, IMD-186); `ranking_explain` off | not built; counts as satisfied for the gate (§11.2) | none |

**Points.** Sprint 5 plans 63 points on 15 cards. IMP-515 (4 points: Jeel 2, Krrish 2) is an extension, cut by IMD-65 and IMD-186, so 59 points over 22 parts on 14 cards are in scope, plus the gate card IMP-599 (0 points). All 22 parts are merged. None is blocked. Staging evidence waits for the staging window of Wednesday 18 November 2026 (IMD-137, IMD-186).

## Points earned in Sprint 5 per member

From the card points of the task register and the owner of each merged part. Fix runs carry no points.

| Member | Parts | Points |
| --- | --- | --- |
| Het | IMP-504 add-place-api 3, IMP-505 replace-api 3, IMP-506 lock-api 2 | 8 |
| Manya | IMP-503 pace-grouping 6, IMP-514 run-records 2 | 8 |
| Manasvi | IMP-503 pace-control 1, IMP-507 costs-page 2, IMP-508 whole-task 5 | 8 |
| Krrish | IMP-505 alternatives-dialog 2, IMP-506 lock-toggle 1, IMP-510 edit-page 1, IMP-513 whole-task 3 | 7 |
| Junaid | IMP-501 hours-checks 3, IMP-512 whole-task 3 | 6 |
| Manal | IMP-501 budget-conflict 2, IMP-507 breakdown-api 3, IMP-510 settings-api 1 | 6 |
| Nidhi | IMP-502 whole-task 5, IMP-514 gemini-baseline 1 | 6 |
| Kirtan | IMP-511 whole-task 5 (IMP-599 is 0 points) | 5 |
| Jeel | IMP-509 whole-task 3 (IMP-515 part cut) | 3 |
| Malhar | IMP-504 place-picker 2 | 2 |
| **Total** | 22 parts | **59** |

## Integration batches (pull requests)

| Pull request | Title | Commits on `main` | Merged |
| --- | --- | --- | --- |
| #275 | S5 batch A · IMP-502, 503, 504, 505, 507, 508, 509, 510, 512, 514 | `c29cd47` to `4c6c693` (15) | 14 November 2026 |
| #276 | S5 batch B · IMP-501, 503, 504, 505, 506, 507, 510, 511, 514 | `2bf1bfe` to `15475eb` (17) | 14 November 2026 |
| #277 | S5 batch C · IMP-513, IMP-514 baseline, IMD-173, PD-RUN-069-1 | `e7bbfec` to `aec7caa` (6) | 14 November 2026 |
| #278 | S5 follow-up · map spec in E2E, axe targets, dashboard contrast | `a9c3adc` to `a72d07a` (7) | 14 November 2026 |
| #279 | S5 fixes · commit before response, CI edit scope, IMD-177 to IMD-184 | `c5ab3b5` to `43a4240` (3) | 14 November 2026 |

## Fix and decision runs (no points)

| Run | Fix | Owner | Commit | Pull request | Decision | Record |
| --- | --- | --- | --- | --- | --- | --- |
| RUN-070 | MOCK default proposal fits curated hours (PD-RUN-069-1) | Nidhi | `e7bbfec` | #277 | IMD-177 | [PD-RUN-069-1](parts/PD-RUN-069-1-mock-happy-path.md) |
| RUN-070 | Tile-abort fallback and attribution E2E (IMD-173) | Manasvi | `61c5003` | #277 | IMD-173 | "RUN-070" section of [IMP-508](parts/IMP-508-whole-task.md) |
| RUN-070b | OpenStreetMap credit in the map panel (PD-RUN-070-1); map list fallback names | Manasvi | `aec7caa` | #277 | IMD-179 | "RUN-070b" section of [IMP-508](parts/IMP-508-whole-task.md) |
| RUN-070b | Warning severity headings (PD-IMP-513-1) and journey focus step | Krrish | `736da4d` | #277 | IMD-178 | "RUN-070b" section of [IMP-513](parts/IMP-513-whole-task.md) |
| RUN-071 | Map spec runs in the E2E workflow (PD-RUN-070b-1) | Kirtan | `a9c3adc` | #278 | IMD-179 | [PD-RUN-070b-1](parts/PD-RUN-070b-1-e2e-map.md) |
| RUN-071 | Axe logs rule, impact, page and targets on every attempt (PD-RUN-070b-2) | Krrish | `4e0c232` | #278 | IMD-179 | "RUN-071" section of [IMP-513](parts/IMP-513-whole-task.md) |
| RUN-071 | Dashboard "Open latest" colour contrast during the enable fade | Krrish | `864c78f` | #278 | IMD-178 | "RUN-071 contrast" section of [IMP-513](parts/IMP-513-whole-task.md) |
| RUN-071b | Map worker loads in the production build (PD-RUN-071-2) | Manasvi | `05706e8` | #278 | IMD-182 | "RUN-071b" section of [IMP-508](parts/IMP-508-whole-task.md) |
| RUN-071b | Shared Button animates colours only, never opacity (PD-RUN-071-1; IMP-104 file) | Manasvi | `06af2f7` | #278 | IMD-182 | "RUN-071b button" section of [IMP-513](parts/IMP-513-whole-task.md) |
| RUN-071c | Focus returns to the moved item's controls after they render | Krrish | `ab94cd5` | #278 | IMD-178 | "RUN-071c" section of [IMP-513](parts/IMP-513-whole-task.md) |
| RUN-071c | E2E runs by manual dispatch only (no push or nightly trigger) | Kirtan | `a72d07a` | #278 | IMD-183 | "RUN-071c" section of [PD-RUN-070b-1](parts/PD-RUN-070b-1-e2e-map.md) |
| RUN-072 | Write transactions commit before the response is sent (PD-RUN-071c-1); `make test-api` `466 passed`, `make test-authz` `47 passed` in the part run | Het | `74e001c` | #279 | IMD-184 | [PD-RUN-071c-1](parts/PD-RUN-071c-1-commit-before-response.md) |
| RUN-072 | A pull-request edit re-runs only the attribution job (verified locally; not yet observed at runtime) | Kirtan | `43a4240` | #279 | IMD-184 | "RUN-072" section of [PD-RUN-070b-1](parts/PD-RUN-070b-1-e2e-map.md) |
| RUN-072 | Decision record IMD-177 to IMD-184 | Nidhi | `c5ab3b5` | #279 | — | `docs/spec/DECISION_REGISTER.md` |

Also in #276: IMD-159 plain-language currency error (`5f53777`, Kirtan), an SG-4 open item.

## Carried-over items

| Item | Card | Owner | Due |
| --- | --- | --- | --- |
| Staging GEMINI journey with all Sprint 5 functions, `make smoke` on staging, timeout fallback on staging (IMD-33), generation cap on staging | IMP-599 | Kirtan, Het (Gemini key) | Wed 18 November 2026 (IMD-186) |
| Gemini `config_error` on staging | IMP-599 | Kirtan, Het | Wed 18 November 2026 |
| Destructive button hover contrast about 4.40:1 (PD-RUN-071b-1) | IMP-513 / IMP-104 | Manasvi | Sprint 6 (IMD-183) |
| Prompt v2: the application supplies the "AI-written" label; a place appears at most once in a generated plan (meal stops included) | IMP-514 findings | Manya, Nidhi | Sprint 6 (IMD-180, IMD-181) |
| TC-385 live-stack label review and screenshots | IMP-507 | Manasvi | no date set |
| Provider spending limit (Awaiting validation) | IMP-511 | Kirtan | no date set |
| A pull-request edit runs only attribution: observe at runtime | RUN-072 | Kirtan | next pull-request edit |
| Screenshots on the local stack: place picker, alternatives dialog, lock toggle, trip edit page, costs page, map and list fallback | IMP-504, IMP-505, IMP-506, IMP-507, IMP-508, IMP-510 | Malhar, Krrish, Manasvi | no date set |
| OpenFreeMap terms Unverified (`docs/decisions/map-tiles.md`) | IMP-508 | Manasvi | no date set |
| Gemini recordings are hand-written fixtures; replace with scrubbed live recordings | IMP-512 | Junaid | no date set |
| TC-382 manual screen-reader pass | IMP-703 | Krrish | Sprint 7 (IMP-703) |
| Regeneration (API-31) behind the stale-plan banner | IMP-607 | Het (lead), Nidhi, Krrish | Sprint 6 |

## Cut

- IMP-515 "Why this place?" (extension): cut by IMD-65 and IMD-186; the switch `ranking_explain` is off by decision. API-63 and the panel are not built. `ranking_explain` is not yet in the `FEATURES_DISABLED` default (empty in `apps/api/app/core/config.py` and `.env.example`); see the SG-5 entry in [gates.md](gates.md).
