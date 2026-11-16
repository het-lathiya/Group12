# Sprint 6 index (week 6): MVP-S features and feature freeze — gate SG-6

One line per task part of Sprint 6 (task register). Evidence lives in the part records under `docs/progress/parts/`; the gate card IMP-699 compiles this index from them. The Status column comes from the merged pull requests, not from the records' own status lines, which were written before merging. The Acceptance column is copied from each part record and is not upgraded here.

Compiled by IMP-699 (RUN-080) on 16 November 2026 from the part records and the merged pull requests #281 to #285 on `main` at `fd7ae14`. Gate result: see [gates.md, SG-6](gates.md#sg-6-end-of-week-6-mvp-feature-freeze-imp-699).

Where a record says its API or browser cases were "awaiting CI" or "not run", the API cases are part of the CI `api` job, which passed on `main` at `fd7ae14` ([CI 43806482129](https://github.com/het-lathiya/Group12/actions/runs/43806482129), push, success), and TC-376 and the floor journey TC-372 ran in the gate's E2E dispatches ([gates.md](gates.md#sg-6-end-of-week-6-mvp-feature-freeze-imp-699), rows 2b and 2c). That is a suite-level result; this index does not turn a record's "not verified" into "verified" per criterion.

| Task | Title | Part | Owner | Points | Run | Pull request | Merged | Status | Acceptance (from the part record) | Part record |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| IMP-601 | Profile page and API | whole-task | Het (lead) | 2 | RUN-075 | #281 | 15 November 2026 | merged | implemented; API and component tests pass locally (FR-004 AC1 to AC3, TC-060 to TC-062) | [record](parts/IMP-601-whole-task.md) |
| IMP-602 | Trip dashboard with rename, duplicate, archive and delete | trip-actions-api | Manal (lead) | 6 | RUN-075 | #281 | 15 November 2026 | merged | implemented; API, authz and component tests pass locally | [record](parts/IMP-602-trip-actions-api.md) |
| IMP-602 | Trip dashboard with rename, duplicate, archive and delete | dashboard | Manasvi | 2 | RUN-075 | #281 | 15 November 2026 | merged | implemented; component tests pass locally | [record](parts/IMP-602-dashboard.md) |
| IMP-603 | Curate and load demo destination 2 | — | Junaid (lead), Manya, Kirtan | 5 | none | none | — | **waiting for data** (members' curated files due Thu 19 November 2026, IMD-201) | not started; no part record | none |
| IMP-604 | Search, filters and place detail with labelled facts | search-api | Malhar (lead) | 4 | RUN-075 | #281 | 15 November 2026 | merged | verified by API and unit tests in the part run (API-16 parameters per IMD-190) | [record](parts/IMP-604-search-api.md) |
| IMP-604 | Search, filters and place detail with labelled facts | filter-bar | Manasvi | 2 | RUN-075 | #281 | 15 November 2026 | merged | verified by component tests (URL filter state) | [record](parts/IMP-604-filter-bar.md) |
| IMP-604 | Search, filters and place detail with labelled facts | detail-drawer | Jeel | 1 | RUN-075 | #281 | 15 November 2026 | merged | verified by component tests (labelled facts) | [record](parts/IMP-604-detail-drawer.md) |
| IMP-605 | Saved places (wishlist) | whole-task | Jeel (lead) | 3 | RUN-075 | #281 | 15 November 2026 | merged | verified (API, component); `wishlist` off → 404 and hidden UI verified; TC-372 not verified in the part run (shown by the gate floor run) | [record](parts/IMP-605-whole-task.md) |
| IMP-606 | Food places and meal slots | meal-retrieval | Malhar (lead) | 3 | RUN-075 | #281 | 15 November 2026 | merged | verified by unit and API tests (food places, meal-slot retrieval) | [record](parts/IMP-606-meal-retrieval.md) |
| IMP-606 | Food places and meal slots | meal-builder | Manya | 2 | RUN-075 | #281 | 15 November 2026 | merged | lunch per full day verified for the rule-based plan; not verified for a MOCK model plan in the part run (fixed in RUN-077, IMD-189) | [record](parts/IMP-606-meal-builder.md) |
| IMP-607 | Regenerate one day around locks and the whole itinerary | regen-api | Het (lead) | 4 | RUN-076 | #282 | 15 November 2026 | merged | verified by the real-database suites (snapshot on start, idempotency, scope, ownership, stale revision, caps, merge, switch-off); TC-376 awaited CI (passed in [E2E 43807014448](https://github.com/het-lathiya/Group12/actions/runs/43807014448)) | [record](parts/IMP-607-regen-api.md) |
| IMP-607 | Regenerate one day around locks and the whole itinerary | day-scope | Nidhi | 4 | RUN-076 | #282 | 15 November 2026 | merged | verified (day-scoped request and pipeline scope) | [record](parts/IMP-607-day-scope.md) |
| IMP-607 | Regenerate one day around locks and the whole itinerary | regen-controls | Krrish | 2 | RUN-076 | #282 | 15 November 2026 | merged | component tests verified; TC-376 browser run awaited CI (passed in [E2E 43807014448](https://github.com/het-lathiya/Group12/actions/runs/43807014448), step "Run itinerary editing and restore") | [record](parts/IMP-607-regen-controls.md) |
| IMP-608 | Budget alerts and contingency buffer | alerts-contingency | Manal (lead) | 2 | RUN-075 | #281 | 15 November 2026 | merged | verified by unit and API tests | [record](parts/IMP-608-alerts-contingency.md) |
| IMP-608 | Budget alerts and contingency buffer | budget-alert | Krrish | 2 | RUN-075 | #281 | 15 November 2026 | merged | component verified; both switches off (TC-372) not verified in the part run; banner in the itinerary cost strip not verified (no cost strip on the itinerary page) | [record](parts/IMP-608-budget-alert.md) |
| IMP-609 | Final trip summary and print view | summary-api | Het | 1 | RUN-075 | #281 | 15 November 2026 | merged | verified by API tests (API-35; no new fields, IMD-191) | [record](parts/IMP-609-summary-api.md) |
| IMP-609 | Final trip summary and print view | summary-page | Krrish (lead) | 2 | RUN-075 | #281 | 15 November 2026 | merged | page-break classes verified by component test; manual print preview with screenshot not verified | [record](parts/IMP-609-summary-page.md) |
| IMP-610 | Itinerary versions: save, list and restore | version-snapshots | Jeel (lead) | 6 | RUN-075 | #281 | 15 November 2026 | merged | verified (snapshots, list, save; `versions` off → 404 at API level); floor E2E and versions-page screenshot not verified in the part run | [record](parts/IMP-610-version-snapshots.md) |
| IMP-610 | Itinerary versions: save, list and restore | restore-retention | Malhar | 2 | RUN-075 | #281 | 15 November 2026 | merged | verified (restore transaction, retention); one backup with `versions` off shown by the RUN-077 test (IMD-198) | [record](parts/IMP-610-restore-retention.md) |
| IMP-611 | Usability session 1 and recorded findings | prepare | Junaid (lead), Krrish | 3 (pending) | RUN-075 | #281 | 15 November 2026 | **templates merged; session pending** (IMD-201) | US-142 AC1, AC2 not verified (human activity, not yet run) | [record](parts/IMP-611-prepare.md) |
| IMP-612 | Optimise day order to cut travel time | — | Het (lead), Junaid, Manasvi | 8 | none | none | — | **cut** (IMD-65, IMD-186); `optimise_order` off by decision | not built (no route, no screen) | none |
| IMP-613 | Packing checklist with AI free-text refinement | — | Kirtan (lead), Nidhi, Manya | 9 | none | none | — | **cut** (IMD-65); `packing` off by decision | not built (no route, no table, no screen) | none |

**Points.** Sprint 6 plans 75 points on 13 cards. IMP-612 (8) and IMP-613 (9) are extensions, cut by IMD-65 (IMP-612 also IMD-186), so 58 points are in scope. 50 points over 19 parts on 9 cards are merged. Pending: IMP-603 (5 points, waits for the members' curated files until Thu 19 November 2026; otherwise destination 2 is deferred and the points stay pending, IMD-201) and IMP-611 (3 points, the session runs on staging in or right after the staging window, IMD-201). Gate card IMP-699: 0 points.

## Points earned in Sprint 6 per member

From the card points of the task register and the owner of each merged part. Fix and decision runs carry no points.

| Member | Parts | Points |
| --- | --- | --- |
| Jeel | IMP-604 detail-drawer 1, IMP-605 whole-task 3, IMP-610 version-snapshots 6 | 10 |
| Malhar | IMP-604 search-api 4, IMP-606 meal-retrieval 3, IMP-610 restore-retention 2 | 9 |
| Manal | IMP-602 trip-actions-api 6, IMP-608 alerts-contingency 2 | 8 |
| Het | IMP-601 whole-task 2, IMP-607 regen-api 4, IMP-609 summary-api 1 | 7 |
| Krrish | IMP-607 regen-controls 2, IMP-608 budget-alert 2, IMP-609 summary-page 2 (IMP-611 findings template pending with the card) | 6 |
| Manasvi | IMP-602 dashboard 2, IMP-604 filter-bar 2 | 4 |
| Nidhi | IMP-607 day-scope 4 | 4 |
| Manya | IMP-606 meal-builder 2 (IMP-603 part pending) | 2 |
| Junaid | none merged with points (IMP-611 and IMP-603 pending) | 0 |
| Kirtan | none (IMP-603 part pending; IMP-613 cut; IMP-699 is 0 points) | 0 |
| **Total** | 19 parts | **50** |

## Integration batches (pull requests)

All merged by the operator account with Rebase and merge; CI success on every head (see the audit in [gates.md](gates.md#sg-6-end-of-week-6-mvp-feature-freeze-imp-699)).

| Pull request | Title | Commits on `main` | Merged |
| --- | --- | --- | --- |
| #281 | Sprint 6 · Batch A · trips, places, versions, meals, budget alerts, summary, profile | 25 | 15 November 2026 |
| #282 | Sprint 6 · Batch B · regenerate day and whole itinerary, decisions IMD-188 to 192 | 9 | 15 November 2026 |
| #283 | Sprint 6 · Batch C · meals in MOCK and relaxed plans, prompt v3 evaluation, one backup, journey flake, IMD-193/194 | 6 | 15 November 2026 |
| #284 | Sprint 6 · Batch D · eval prompt version, lunch in rule-based days, IMD-195 to 198 | 3 | 16 November 2026 |
| #285 | Sprint 6 · prompt v3 evaluation from main, IMD-199 | 3 | 16 November 2026 |

## Fix and decision runs (no points)

| Run | Fix | Owner | Pull request | Decision | Record |
| --- | --- | --- | --- | --- | --- |
| RUN-075 | Decision record IMD-187 and the IMD-183 amendment note | Nidhi | #281 | IMD-187 | [record](parts/RUN-075-decision-record.md) |
| RUN-075 | Destructive Button hover contrast (PD-RUN-071b-1) | Manasvi | #281 | IMD-183 | [record](parts/RUN-075-hover-contrast.md) |
| RUN-075 | itinerary_generate v3 (label and unique-place rules; v2 stays active) and metrics v2 | Manya | #281 | IMD-180, IMD-181, IMD-188 | [record](parts/RUN-075-prompt-v2.md) |
| RUN-076 | Decision record IMD-188 to IMD-192 and the §6.6.3 amendment | Nidhi | #282 | — | [record](parts/RUN-076-decision-record.md) |
| RUN-077 | Decision record IMD-193 and IMD-194 | Nidhi | #283 | — | [record](parts/RUN-077-decision-record.md) |
| RUN-077 | Lunch slot on relaxed full days | Manya | #283 | IMD-189 | [record](parts/RUN-077-relaxed-lunch.md) |
| RUN-077 | MOCK ok scenario plans meal slots | Nidhi | #283 | IMD-189 | [record](parts/RUN-077-mock-meals.md) |
| RUN-077 | One backup when `versions` is off (test only) | Malhar | #283 | IMD-191, IMD-198 | [record](parts/RUN-077-one-backup.md) |
| RUN-077 | Journey waits for the enabled Open latest button | Krrish | #283 | — | [record](parts/RUN-077-journey-flake.md) |
| RUN-077 | Prompt v3 MOCK evaluation (v3 not activated) | Manya | #283 | PD-RUN-077-E1 → IMD-195 | [record](parts/RUN-077-prompt-v3-eval.md) |
| RUN-078 | Decision record IMD-195 to IMD-198 and the §8.4 MOCK wording | Nidhi | #284 | — | [record](parts/RUN-078-decision-record.md) |
| RUN-078 | Evaluation prompt-version option and version in reports | Manya | #284 | IMD-195 | [record](parts/RUN-078-eval-prompt-version.md) |
| RUN-078 | Lunch reserved in rule-based full days | Manya | #284 | IMD-196 | [record](parts/RUN-078-planner-lunch.md) |
| RUN-079 | Decision record IMD-199 | Nidhi | #285 | — | [record](parts/RUN-079-decision-record.md) |
| RUN-079 | Prompt v3 on MOCK and one Gemini run from `main`: IMD-195 gate not met (14 duplicate-place items in 3 of 45 attempts) | Manya | #285 | IMD-200 | [record](parts/RUN-079-v3-evaluation.md) |
| RUN-080 | Decision record IMD-200 and IMD-201 | Nidhi | this PR | — | `docs/spec/DECISION_REGISTER.md` |
| RUN-080 | E2E `features_disabled` input for the floor journey (TC-372) | Kirtan | this PR | — | [gates.md, SG-6](gates.md#sg-6-end-of-week-6-mvp-feature-freeze-imp-699) |

## Decisions of Sprint 6

IMD-187 (`ranking_explain` needs no switch entry), IMD-188 (prompt v3 added, v2 active; metrics v2), IMD-189 (meal slots in MOCK and on relaxed days), IMD-190 (API-16 parameters, saved places), IMD-191 (versions and summary), IMD-192 (duplicate status, profile currency), IMD-193 (CI-only failures after push), IMD-194 (tracking issues), IMD-195 (prompt version in evaluation, v3 activation gate), IMD-196 (lunch reserved in rule-based plans), IMD-197 (MOCK ok wording), IMD-198 (one backup already met), IMD-199 (evaluation default prompt version), IMD-200 (v3 stays inactive), IMD-201 (SG-6 passes with listed gaps; feature freeze). All in `docs/spec/DECISION_REGISTER.md`.

## Carried-over items

See [deferred.md](deferred.md) for the full list with owners, reasons and due dates.

## Requirement coverage (SG-6 step 1)

Generated in RUN-080 from `docs/spec/TRACEABILITY_MATRIX.md` (tasks and tests) and §2.2 of the specification (release). "Done" means every task the matrix names for the requirement has a part record on `main` at `fd7ae14` and its tests are in the suites that passed in CI ([CI 43806482129](https://github.com/het-lathiya/Group12/actions/runs/43806482129)) and in the gate's `make check`. Result: **88 of 88 MVP and MVP-S requirements Done (63 MVP, 25 MVP-S), 0 cut, 0 gap.** Three requirements also name a Sprint 7 card (IMP-703 accessibility on real devices, IMP-705 final evaluation); their Sprint 1 to 5 tasks are done. No MVP cut-list switch is applied (IMD-167, IMD-201), so no requirement is "switched off by decision".

| FR | Release | Feature | Tasks (part records on `main`) | Tests (matrix) | Sprint | Status |
| --- | --- | --- | --- | --- | --- | --- |
| FR-001 | MVP-S | F-01 | IMP-109 | TC-051, TC-052, TC-053 (+2) | 1 | Done |
| FR-002 | MVP-S | F-01 | IMP-109 | TC-054, TC-055, TC-056 (+1) | 1 | Done |
| FR-003 | MVP | F-01 | IMP-108 | TC-057, TC-058, TC-059 (+3) | 1 | Done |
| FR-004 | MVP-S | F-01 | IMP-601 | TC-060, TC-061, TC-062 | 6 | Done |
| FR-005 | MVP | F-01 | IMP-215 | TC-063, TC-064, TC-065 (+4) | 2 | Done |
| FR-007 | MVP | F-02 | IMP-203, IMP-212 | TC-068, TC-069, TC-070 (+2) | 2 | Done |
| FR-008 | MVP | F-02 | IMP-203, IMP-212 | TC-071, TC-072, TC-073 | 2 | Done |
| FR-009 | MVP-S | F-03 | IMP-204, IMP-212 | TC-074, TC-075, TC-076 | 2 | Done |
| FR-010 | MVP-S | F-03 | IMP-204 | TC-077, TC-078, TC-079 | 2 | Done |
| FR-011 | MVP-S | F-02, F-03 | IMP-510 | TC-080, TC-081 | 5 | Done |
| FR-012 | MVP-S | F-04 | IMP-602 | TC-082, TC-083, TC-084 (+3) | 6 | Done |
| FR-013 | MVP | F-51 | IMP-410 | TC-085, TC-086 | 4 | Done |
| FR-014 | MVP | F-54 | IMP-410 | TC-087, TC-088 | 4 | Done |
| FR-015 | MVP-S | F-52 | IMP-602 | TC-089, TC-090, TC-091 (+1) | 6 | Done |
| FR-016 | MVP-S | F-05, F-42 | IMP-509 | TC-092, TC-093, TC-094 | 5 | Done |
| FR-017 | MVP-S | F-06 | IMP-604 | TC-095, TC-096, TC-097 | 6 | Done |
| FR-018 | MVP-S | F-05, F-23, C-08 | IMP-604 | TC-098, TC-099, TC-100 | 6 | Done |
| FR-019 | MVP-S | F-42 | IMP-205 | TC-101, TC-102 | 2 | Done |
| FR-020 | MVP-S | F-08 | IMP-605 | TC-103, TC-104, TC-105 (+1) | 6 | Done |
| FR-022 | MVP | F-05, C-08 | IMP-205 | TC-108, TC-109, TC-110 | 2 | Done |
| FR-023 | MVP | F-05 | IMP-205 | TC-111, TC-112, TC-113 | 2 | Done |
| FR-024 | MVP | F-09 | IMP-210, IMP-213, IMP-305 | TC-114, TC-115, TC-116 (+2) | 2 | Done |
| FR-025 | MVP | F-09 | IMP-210, IMP-213, IMP-305 | TC-117, TC-118, TC-119 (+1) | 2 | Done |
| FR-026 | MVP | F-09, F-03 | IMP-303 | TC-028, TC-120, TC-121 (+1) | 3 | Done |
| FR-027 | MVP | F-09, F-10 | IMP-304 | TC-123, TC-124, TC-125 | 3 | Done |
| FR-028 | MVP | F-09, F-10 | IMP-304 | TC-126, TC-127, TC-128 | 3 | Done |
| FR-029 | MVP-S | F-16 | IMP-503 | TC-129, TC-130 | 5 | Done |
| FR-030 | MVP | F-36 | IMP-503 | TC-131, TC-132 | 5 | Done |
| FR-031 | MVP | F-09, C-07 | IMP-305 | TC-003, TC-036, TC-133 (+4) | 3 | Done |
| FR-032 | MVP | C-07 | IMP-306 | TC-011, TC-022, TC-023 (+5) | 3 | Done |
| FR-033 | MVP | F-09, F-10, F-18 | IMP-308 | TC-139, TC-140 | 3 | Done |
| FR-034 | MVP | F-10 | IMP-406 | TC-141, TC-142 | 4 | Done |
| FR-035 | MVP-S | C-08 | IMP-406 | TC-143, TC-144 | 4 | Done |
| FR-036 | MVP | F-09 | IMP-402 | TC-145, TC-146, TC-147 (+4) | 4 | Done |
| FR-037 | MVP | F-09 | IMP-403 | TC-005, TC-017, TC-148 (+6) | 4 | Done |
| FR-038 | MVP | F-09 | IMP-202, IMP-210 | TC-004, TC-012, TC-024 (+7) | 2 | Done |
| FR-039 | MVP | F-09 | IMP-303 | TC-014, TC-027, TC-154 (+1) | 3 | Done |
| FR-040 | MVP | F-09 | IMP-110, IMP-512 | TC-001, TC-002, TC-003 (+6) | 1 | Done |
| FR-041 | MVP | F-09, C-07 | IMP-301 | TC-004, TC-009, TC-013 (+18) | 3 | Done |
| FR-042 | MVP | F-09 | IMP-207 | TC-033, TC-034, TC-035 (+3) | 2 | Done |
| FR-043 | MVP | F-09 | IMP-208 | TC-013, TC-037, TC-042 (+4) | 2 | Done |
| FR-044 | MVP | F-09 | IMP-302 | TC-006, TC-007, TC-044 (+2) | 3 | Done |
| FR-045 | MVP | F-09 | IMP-111 | TC-026, TC-169, TC-170 | 1 | Done |
| FR-046 | MVP | F-09 | IMP-511 | TC-171, TC-172, TC-173 (+3) | 5 | Done |
| FR-047 | MVP | F-09 | IMP-401 | TC-009, TC-010, TC-016 (+2) | 4 | Done |
| FR-050 | MVP | C-09 | IMP-404 | TC-176, TC-177, TC-306 (+1) | 4 | Done |
| FR-051 | MVP | F-37, C-09 | IMP-404 | TC-178, TC-179, TC-317 | 4 | Done |
| FR-052 | MVP | C-09 | IMP-501 | TC-180, TC-181, TC-301 (+1) | 5 | Done |
| FR-053 | MVP | F-17, F-37 | IMP-501 | TC-182, TC-183, TC-303 | 5 | Done |
| FR-054 | MVP | C-09, F-17 | IMP-501 | TC-184, TC-185, TC-304 | 5 | Done |
| FR-055 | MVP | C-09 | IMP-404 | TC-186, TC-187, TC-305 | 4 | Done |
| FR-056 | MVP | F-17 | IMP-405 | TC-188, TC-189 | 4 | Done |
| FR-057 | MVP-S | C-10 | IMP-502 | TC-011, TC-190, TC-191 (+2) | 5 | Done |
| FR-058 | MVP | C-09, C-10 | IMP-405 | TC-193, TC-194 | 4 | Done |
| FR-059 | MVP | F-09, F-50 | IMP-211, IMP-309 | TC-195, TC-196, TC-329 (+1) | 2 | Done |
| FR-060 | MVP | F-12 | IMP-409 | TC-197, TC-198, TC-199 (+1) | 4 | Done |
| FR-061 | MVP | F-12 | IMP-408 | TC-200, TC-201 | 4 | Done |
| FR-062 | MVP | F-13, F-11 | IMP-504 | TC-202, TC-203 | 5 | Done |
| FR-063 | MVP | F-11 | IMP-408 | TC-204, TC-205 | 4 | Done |
| FR-064 | MVP | F-11 | IMP-407 | TC-206, TC-207, TC-312 (+2) | 4 | Done |
| FR-065 | MVP-S | F-14 | IMP-505 | TC-208, TC-209, TC-210 (+1) | 5 | Done |
| FR-066 | MVP-S | C-02 | IMP-506 | TC-211, TC-212, TC-313 (+2) | 5 | Done |
| FR-067 | MVP-S | F-15, C-02 | IMP-607 | TC-213, TC-214, TC-313 (+2) | 6 | Done |
| FR-068 | MVP-S | F-15 | IMP-607 | TC-215, TC-216 | 6 | Done |
| FR-069 | MVP | F-11 | IMP-504 | TC-217, TC-318, TC-325 (+1) | 5 | Done |
| FR-071 | MVP | F-18 | IMP-308 | TC-221, TC-222, TC-295 (+8) | 3 | Done |
| FR-072 | MVP | F-18 | IMP-411 | TC-223, TC-224 | 4 | Done |
| FR-073 | MVP | F-19 | IMP-507 | TC-225, TC-226, TC-300 | 5 | Done |
| FR-074 | MVP-S | F-20 | IMP-608 | TC-227, TC-228, TC-372 | 6 | Done |
| FR-075 | MVP-S | F-22 | IMP-608 | TC-229, TC-230, TC-298 (+2) | 6 | Done |
| FR-076 | MVP | F-23, C-08 | IMP-411 | TC-231, TC-232, TC-299 (+2) | 4 | Done |
| FR-078 | MVP | F-34 | IMP-307 | TC-234, TC-235, TC-341 | 3 | Done |
| FR-079 | MVP | F-34 | IMP-209 | TC-236, TC-237, TC-317 | 2 | Done |
| FR-080 | MVP-S | F-35 | IMP-508 | TC-238, TC-239, TC-240 | 5 | Done |
| FR-083 | MVP-S | F-40 | IMP-606 | TC-243, TC-244, TC-372 | 6 | Done |
| FR-094 | MVP | F-50 | IMP-609 | TC-254, TC-255, TC-369 (+1) | 6 | Done |
| FR-095 | MVP-S | C-11 | IMP-610 | TC-256, TC-257, TC-318 (+3) | 6 | Done |
| FR-114 | MVP | C-12 | IMP-104, IMP-703 | TC-278, TC-328, TC-339 (+1) | 1 | Done; follow-up card IMP-703 pending is Sprint 7 |
| FR-115 | MVP | C-12 | IMP-513, IMP-703 | TC-279, TC-280, TC-374 (+2) | 5 | Done; follow-up card IMP-703 pending is Sprint 7 |
| FR-116 | MVP | C-12 | IMP-412 | TC-281, TC-384 | 4 | Done |
| FR-117 | MVP | C-08, F-23 | IMP-507 | TC-282, TC-385 | 5 | Done |
| FR-118 | MVP | F-09, C-07 | IMP-310 | TC-283, TC-284, TC-386 (+1) | 3 | Done |
| FR-119 | MVP | F-09, C-07 | IMP-413 | TC-041, TC-285, TC-286 (+5) | 4 | Done |
| FR-120 | MVP | F-09 | IMP-514, IMP-705 | TC-287, TC-390, TC-391 (+1) | 5 | Done; follow-up card IMP-705 pending is Sprint 7 |
| FR-123 | MVP | F-09 | IMP-103, IMP-112, IMP-201, IMP-217, IMP-218 | TC-288, TC-289, TC-342 | 1 | Done |
| FR-124 | MVP | — | IMP-103, IMP-105 | TC-042, TC-043, TC-290 (+7) | 1 | Done |
| FR-125 | MVP | — | IMP-201 | TC-292, TC-293, TC-342 (+2) | 2 | Done |
| FR-126 | MVP | — | IMP-511 | TC-294, TC-353 | 5 | Done |
