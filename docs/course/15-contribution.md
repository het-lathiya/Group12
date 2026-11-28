# Group leader's contribution document

Group 12 · IT314 Software Engineering · Autumn 2026-27

**Group leader: Nidhi Chauhan. Unsigned draft — team confirmation required.**

Snapshot: `origin/main` at `57b620901ff610900ce46c004a27bcae68cc695e`. Captured 2026-11-28T14:39:32.097626+05:30. This report records repository evidence, not assessed marks or self-reported effort.

## Evidence and accounting method

- Roles and owned card/part assignments: TASK_REGISTER and the specification's team role table. Original card IDs are binding; printed part labels shorten the repository-guidance filename.
- Plan: Amendment A1 §10.5 supersedes the older Appendix C totals. Cut extensions remain listed as cut, not delivered; A2/course documentation work has no added points.
- Merged points: sum the allocations on merged rows of the Sprint 1–7 ledgers, plus the separately recorded IMP-399/IMP-499 gate allocations. This measures merged allocations, **not acceptance credit or grades**. Draft Sprint 8 completion is not awarded points here.
- The Sprint 1 ledger expressly withholds credit for account/interview/seed-plan outcomes and marks hosted deployment credit provisional. Those distinctions remain open; a merge does not close human/staging acceptance.
- Commits: exact `git shortlog -sne origin/main`. PR lists below mean PRs containing owned ledger work; the GitHub PR author is often the operator account and does not establish who implemented a part.
- Reviews: `gh pr list --state merged --limit 1000 --json number,author,reviews,url`. Only recorded submitted reviews count; requests, comments and offline review are not inferred.
- Course ownership: protected course index, course-file owner lines and the PR #302 part records. RUN-102 additions are current drafts and are excluded from commits on main.

Sources: [task register](../spec/TASK_REGISTER.md), [A1 points](../spec/AMENDMENT_A1_AWS_RAG.md#105-points-supersedes-the-totals-of-the-team-contribution-plan-v2-and-imd-56-imd-65), [sprint ledgers](../progress/), [gates](../progress/gates.md), [frozen evidence](15-contribution-evidence.json).

## Summary

| Member | Plan | Merged allocated points | Commits on main | Recorded submitted reviews |
| --- | --- | --- | --- | --- |
| Nidhi (group leader) | 40 | 38 | 69 | 0 |
| Kirtan | 41 | 32 | 81 | 1 |
| Manal | 40 | 40 | 37 | 0 |
| Het | 40 | 40 | 60 | 0 |
| Junaid | 41 | 32 | 36 | 0 |
| Malhar | 41 | 39 | 49 | 0 |
| Jeel | 40 | 38 | 42 | 0 |
| Manya | 40 | 37 | 34 | 0 |
| Manasvi | 41 | 38 | 47 | 0 |
| Krrish | 39 | 34 | 57 | 0 |
| Total | 403 | 368 | 512 | 1 |

The query returned 98 merged PRs and 1 submitted review record(s). The recorded approval is Kirtan (`kirtan-S111`) on [PR #2](https://github.com/het-lathiya/Group12/pull/2). Other members have no submitted review in this queried dataset; this does not establish absence of offline review.

Sprint 1 credited values (including the ledger's provisional hosted-deployment credit): Nidhi 5; Kirtan 9; Manal 2; Het 3; Junaid 0; Malhar 4; Jeel 4; Manya 2; Manasvi 5; Krrish 4. See the original ledger before interpreting them as accepted points.

## Nidhi — Nidhi Chauhan

**Role:** AI Engineer (Provider Layer and Generation Pipeline). Course group leader under RUN-102.

**Plan / merged allocations:** 40 / 38. **Commits on main:** 69 (`Nidhi Chauhan <202401128@dau.ac.in>`).

**Cards and parts owned (task register; ownership does not by itself mean completed):**

| Card | Assigned part | Main evidence |
| --- | --- | --- |
| IMP-110 | whole task | [ledger](../progress/sprint-1.md) |
| IMP-113 | Gemini API key, generation model ID, embedding model ID and data-use terms | [ledger](../progress/sprint-1.md) |
| IMP-208 | whole task | [ledger](../progress/sprint-2.md) |
| IMP-301 | Gemini adapter: structured output, error mapping | [ledger](../progress/sprint-3.md) |
| IMP-305 | Full generation pipeline through the active provider | [ledger](../progress/sprint-3.md) |
| IMP-312 | whole task | [ledger](../progress/sprint-3.md) |
| IMP-399 | whole task | [ledger](../progress/sprint-3.md) |
| IMP-401 | whole task | [ledger](../progress/sprint-4.md) |
| IMP-403 | Failure, timeout and quota outcomes end to end | [ledger](../progress/sprint-4.md) |
| IMP-502 | whole task | [ledger](../progress/sprint-5.md) |
| IMP-514 | First Gemini baseline report | [ledger](../progress/sprint-5.md) |
| IMP-607 | Regenerate one day around locks (request scope, pipeline) | [ledger](../progress/sprint-6.md) |
| IMP-705 | whole task | [ledger](../progress/sprint-7.md) |
| IMP-801 | Demo script and backup video | [record](../progress/parts/IMP-801-demo-script-draft.md), [record](../progress/parts/IMP-801-release-notes-draft.md) |
| IMP-802 | AI pipeline defect fixes | No merged ledger row/part record located; human completion remains unverified |

Cut assignments (not built): IMP-613, IMP-708, IMP-709.

**Main PR references for owned merged work:** [#195](https://github.com/het-lathiya/Group12/pull/195), [#200](https://github.com/het-lathiya/Group12/pull/200), [#210](https://github.com/het-lathiya/Group12/pull/210), [#249](https://github.com/het-lathiya/Group12/pull/249), [#250](https://github.com/het-lathiya/Group12/pull/250), [#261](https://github.com/het-lathiya/Group12/pull/261), [#267](https://github.com/het-lathiya/Group12/pull/267), [#275](https://github.com/het-lathiya/Group12/pull/275), [#277](https://github.com/het-lathiya/Group12/pull/277), [#282](https://github.com/het-lathiya/Group12/pull/282), [#289](https://github.com/het-lathiya/Group12/pull/289), [#291](https://github.com/het-lathiya/Group12/pull/291).

**Review activity:** 0 submitted review record(s) in the merged-PR query. Requests/offline activity are not counted.

**Course documents / submission work:** 01-requirements.md (main); 15-contribution.md/PDF (RUN-102 draft).

## Kirtan — chaudhari kirtan sandipbhai

**Role:** DevOps Engineer and Integration Lead.

**Plan / merged allocations:** 41 / 32. **Commits on main:** 81 (`chaudhari kirtan sandipbhai <chaudharikirtan03@gmail.com>`).

**Cards and parts owned (task register; ownership does not by itself mean completed):**

| Card | Assigned part | Main evidence |
| --- | --- | --- |
| IMP-101 | Repo tree, Makefile, toolchain pins, repository guidance, progress folders | [ledger](../progress/sprint-1.md) |
| IMP-102 | whole task | [ledger](../progress/sprint-1.md) |
| IMP-112 | whole task | [ledger](../progress/sprint-1.md) |
| IMP-113 | GitHub, AWS account (Free plan, MFA, budget owner) and auth-only Supabase project, secrets register | [ledger](../progress/sprint-1.md) |
| IMP-199 | whole task | [record](../progress/parts/IMP-199-whole-task.md) |
| IMP-201 | whole task | [ledger](../progress/sprint-2.md) |
| IMP-214 | whole task | [ledger](../progress/sprint-2.md) |
| IMP-216 | whole task | [ledger](../progress/sprint-2.md) |
| IMP-217 | whole task | [ledger](../progress/sprint-2.md) |
| IMP-299 | whole task | No merged ledger row/part record located; human completion remains unverified |
| IMP-302 | whole task | [ledger](../progress/sprint-3.md) |
| IMP-499 | whole task | [ledger](../progress/sprint-4.md) |
| IMP-511 | whole task | [ledger](../progress/sprint-5.md) |
| IMP-599 | whole task | No merged ledger row/part record located; human completion remains unverified |
| IMP-603 | Load destination 2 into staging and production; run the quality report | No merged ledger row/part record located; human completion remains unverified |
| IMP-699 | whole task | No merged ledger row/part record located; human completion remains unverified |
| IMP-702 | Security headers and secret-scan review | [ledger](../progress/sprint-7.md) |
| IMP-707 | Deployment guide | [ledger](../progress/sprint-7.md) |
| IMP-799 | whole task | [record](../progress/parts/IMP-799-whole-task.md) |
| IMP-801 | Production deployment, smoke tests, RC tag | [record](../progress/parts/IMP-801-demo-script-draft.md), [record](../progress/parts/IMP-801-release-notes-draft.md) |
| IMP-802 | Deployment and configuration fixes | No merged ledger row/part record located; human completion remains unverified |
| IMP-899 | whole task | No merged ledger row/part record located; human completion remains unverified |

Cut assignments (not built): IMP-613, IMP-713.

**Main PR references for owned merged work:** [#1](https://github.com/het-lathiya/Group12/pull/1), [#3](https://github.com/het-lathiya/Group12/pull/3), [#200](https://github.com/het-lathiya/Group12/pull/200), [#202](https://github.com/het-lathiya/Group12/pull/202), [#227](https://github.com/het-lathiya/Group12/pull/227), [#231](https://github.com/het-lathiya/Group12/pull/231), [#243](https://github.com/het-lathiya/Group12/pull/243), [#246](https://github.com/het-lathiya/Group12/pull/246), [#250](https://github.com/het-lathiya/Group12/pull/250), [#276](https://github.com/het-lathiya/Group12/pull/276), [#287](https://github.com/het-lathiya/Group12/pull/287), [#289](https://github.com/het-lathiya/Group12/pull/289).

**Review activity:** 1 submitted review record(s) in the merged-PR query. Approved PR #2; no additional review inferred.

**Course documents / submission work:** Coverage workflow (PR #302); submission ZIP builder (RUN-102); no authored numbered course prose at the snapshot.

## Manal — Manal Patel

**Role:** Backend Engineer (Core API and Budget).

**Plan / merged allocations:** 40 / 40. **Commits on main:** 37 (`Manal Patel <manalvg2557@gmail.com>`).

**Cards and parts owned (task register; ownership does not by itself mean completed):**

| Card | Assigned part | Main evidence |
| --- | --- | --- |
| IMP-103 | whole task | [ledger](../progress/sprint-1.md) |
| IMP-203 | whole task | [ledger](../progress/sprint-2.md) |
| IMP-204 | whole task | [ledger](../progress/sprint-2.md) |
| IMP-308 | Budget engine and costs API (money in minor units) | [ledger](../progress/sprint-3.md) |
| IMP-313 | whole task | [ledger](../progress/sprint-3.md) |
| IMP-404 | Validator rules: overlaps, travel gaps | [ledger](../progress/sprint-4.md) |
| IMP-410 | Draft trips and latest-itinerary reopening API | [ledger](../progress/sprint-4.md) |
| IMP-411 | Transport allowance, stay budget, price source labels API | [ledger](../progress/sprint-4.md) |
| IMP-501 | Budget conflict check | [ledger](../progress/sprint-5.md) |
| IMP-507 | Daily and category cost breakdown API | [ledger](../progress/sprint-5.md) |
| IMP-510 | Edit trip settings and stale-plan flag | [ledger](../progress/sprint-5.md) |
| IMP-602 | Rename, duplicate, archive, delete trip API; TripActionsMenu wired to the new endpoints | [ledger](../progress/sprint-6.md) |
| IMP-608 | Budget alerts and contingency buffer | [ledger](../progress/sprint-6.md) |
| IMP-707 | Architecture and API documentation | [ledger](../progress/sprint-7.md) |

Cut assignments (not built): IMP-708, IMP-710.

**Main PR references for owned merged work:** [#190](https://github.com/het-lathiya/Group12/pull/190), [#204](https://github.com/het-lathiya/Group12/pull/204), [#207](https://github.com/het-lathiya/Group12/pull/207), [#251](https://github.com/het-lathiya/Group12/pull/251), [#252](https://github.com/het-lathiya/Group12/pull/252), [#259](https://github.com/het-lathiya/Group12/pull/259), [#260](https://github.com/het-lathiya/Group12/pull/260), [#275](https://github.com/het-lathiya/Group12/pull/275), [#276](https://github.com/het-lathiya/Group12/pull/276), [#281](https://github.com/het-lathiya/Group12/pull/281), [#289](https://github.com/het-lathiya/Group12/pull/289).

**Review activity:** 0 submitted review record(s) in the merged-PR query. Requests/offline activity are not counted.

**Course documents / submission work:** 04-object-design.md; 11-design-diagrams.md (main).

## Het — Het Lathiya

**Role:** Backend Engineer (Auth, Generation Jobs and Itinerary Editing).

**Plan / merged allocations:** 40 / 40. **Commits on main:** 60 (`Het Lathiya <lathiyahet3942@gmail.com>`).

**Cards and parts owned (task register; ownership does not by itself mean completed):**

| Card | Assigned part | Main evidence |
| --- | --- | --- |
| IMP-101 | API pyproject (ruff, mypy, pytest) and test socket guard | [ledger](../progress/sprint-1.md) |
| IMP-108 | whole task | [ledger](../progress/sprint-1.md) |
| IMP-210 | whole task | [ledger](../progress/sprint-2.md) |
| IMP-211 | whole task | [ledger](../progress/sprint-2.md) |
| IMP-219 | whole task | [ledger](../progress/sprint-2.md) |
| IMP-305 | Job progress states, generation router, privacy-notice flag (API-04) | [ledger](../progress/sprint-3.md) |
| IMP-308 | Schedule recalculation of times and durations | [ledger](../progress/sprint-3.md) |
| IMP-309 | Itinerary read schema and service fields | [ledger](../progress/sprint-3.md) |
| IMP-316 | Save validated citations on items and return `sources[]` in API-24 | [ledger](../progress/sprint-3.md) |
| IMP-407 | whole task | [ledger](../progress/sprint-4.md) |
| IMP-408 | Remove and retime edit operations | [ledger](../progress/sprint-4.md) |
| IMP-409 | Move/reorder edit operation | [ledger](../progress/sprint-4.md) |
| IMP-504 | Add-place edit and stale-edit rejection | [ledger](../progress/sprint-5.md) |
| IMP-505 | Replace edit with ranked alternatives | [ledger](../progress/sprint-5.md) |
| IMP-506 | Lock/unlock and locks respected by repair | [ledger](../progress/sprint-5.md) |
| IMP-601 | whole task | [ledger](../progress/sprint-6.md) |
| IMP-607 | Merge regenerated day and whole-itinerary regeneration API | [ledger](../progress/sprint-6.md) |
| IMP-609 | Summary API | [ledger](../progress/sprint-6.md) |
| IMP-702 | Auth and ownership fixes found by the pass | [ledger](../progress/sprint-7.md) |

Cut assignments (not built): IMP-612, IMP-709, IMP-711.

**Main PR references for owned merged work:** [#2](https://github.com/het-lathiya/Group12/pull/2), [#196](https://github.com/het-lathiya/Group12/pull/196), [#229](https://github.com/het-lathiya/Group12/pull/229), [#232](https://github.com/het-lathiya/Group12/pull/232), [#236](https://github.com/het-lathiya/Group12/pull/236), [#250](https://github.com/het-lathiya/Group12/pull/250), [#252](https://github.com/het-lathiya/Group12/pull/252), [#253](https://github.com/het-lathiya/Group12/pull/253), [#254](https://github.com/het-lathiya/Group12/pull/254), [#267](https://github.com/het-lathiya/Group12/pull/267), [#268](https://github.com/het-lathiya/Group12/pull/268), [#275](https://github.com/het-lathiya/Group12/pull/275), [#276](https://github.com/het-lathiya/Group12/pull/276), [#281](https://github.com/het-lathiya/Group12/pull/281), [#282](https://github.com/het-lathiya/Group12/pull/282), [#287](https://github.com/het-lathiya/Group12/pull/287).

**Review activity:** 0 submitted review record(s) in the merged-PR query. Requests/offline activity are not counted.

**Course documents / submission work:** Course index; 03-system-design.md (main).

## Junaid — Mohammad Junaid Kureshi

**Role:** Backend and QA Engineer (Routing, Validation and Security Testing).

**Plan / merged allocations:** 41 / 32. **Commits on main:** 36 (`Mohammad Junaid Kureshi <junaid29707@gmail.com>`).

**Cards and parts owned (task register; ownership does not by itself mean completed):**

| Card | Assigned part | Main evidence |
| --- | --- | --- |
| IMP-113 | OpenRouteService key and email sender | [ledger](../progress/sprint-1.md) |
| IMP-114 | Run stakeholder interviews round 1 | No merged ledger row/part record located; human completion remains unverified |
| IMP-209 | whole task | [ledger](../progress/sprint-2.md) |
| IMP-215 | whole task | [ledger](../progress/sprint-2.md) |
| IMP-218 | AWS deploy workflows, release task and deployed smoke checks | [ledger](../progress/sprint-2.md) |
| IMP-306 | Prompt-injection test cases | [ledger](../progress/sprint-3.md) |
| IMP-307 | whole task | [ledger](../progress/sprint-3.md) |
| IMP-310 | whole task | [ledger](../progress/sprint-3.md) |
| IMP-404 | Validator rules: missing constraints, invalid references | [ledger](../progress/sprint-4.md) |
| IMP-318 | whole task | [ledger](../progress/sprint-4.md) |
| IMP-414 | Journey test fixtures, test report | [ledger](../progress/sprint-4.md) |
| IMP-501 | Opening-hours and overpacked-day checks | [ledger](../progress/sprint-5.md) |
| IMP-512 | whole task | [ledger](../progress/sprint-5.md) |
| IMP-603 | Opening hours and prices for destination 2, with sources | No merged ledger row/part record located; human completion remains unverified |
| IMP-611 | Run usability session 1 | [record](../progress/parts/IMP-611-prepare.md) |
| IMP-702 | Authorization suite re-run and injection corpus | [ledger](../progress/sprint-7.md) |
| IMP-704 | Session notes and retest | No merged ledger row/part record located; human completion remains unverified |
| IMP-707 | Test plan | [ledger](../progress/sprint-7.md) |
| IMP-802 | Triage rehearsal defects and add regression tests | No merged ledger row/part record located; human completion remains unverified |

Cut assignments (not built): IMP-612, IMP-712.

**Main PR references for owned merged work:** [#200](https://github.com/het-lathiya/Group12/pull/200), [#211](https://github.com/het-lathiya/Group12/pull/211), [#233](https://github.com/het-lathiya/Group12/pull/233), [#245](https://github.com/het-lathiya/Group12/pull/245), [#248](https://github.com/het-lathiya/Group12/pull/248), [#251](https://github.com/het-lathiya/Group12/pull/251), [#259](https://github.com/het-lathiya/Group12/pull/259), [#271](https://github.com/het-lathiya/Group12/pull/271), [#272](https://github.com/het-lathiya/Group12/pull/272), [#275](https://github.com/het-lathiya/Group12/pull/275), [#276](https://github.com/het-lathiya/Group12/pull/276), [#287](https://github.com/het-lathiya/Group12/pull/287), [#289](https://github.com/het-lathiya/Group12/pull/289).

**Review activity:** 0 submitted review record(s) in the merged-PR query. Requests/offline activity are not counted.

**Course documents / submission work:** 05-unit-testing.md; 06-system-testing.md (main; PR #302).

## Malhar — Malhar Mer

**Role:** Database Engineer (Migrations, Places Data and Fallback Planner).

**Plan / merged allocations:** 41 / 39. **Commits on main:** 49 (`Malhar Mer <mermalhar32@gmail.com>`).

**Cards and parts owned (task register; ownership does not by itself mean completed):**

| Card | Assigned part | Main evidence |
| --- | --- | --- |
| IMP-105 | whole task | [ledger](../progress/sprint-1.md) |
| IMP-106 | SQL migrations 0001-0006 through Alembic, constraints and indexes | [ledger](../progress/sprint-1.md) |
| IMP-115 | whole task | [ledger](../progress/sprint-1.md) |
| IMP-205 | Place import pipeline with provenance and quality gate, category vocabulary | [ledger](../progress/sprint-2.md) |
| IMP-206 | Opening hours and prices with sources | [ledger](../progress/sprint-2.md) |
| IMP-311 | whole task | [ledger](../progress/sprint-2.md) |
| IMP-304 | Candidate retrieval query and hard-constraint filters | [ledger](../progress/sprint-3.md) |
| IMP-314 | Source and licence review, strict quality-gate run and quality report | [ledger](../progress/sprint-3.md) |
| IMP-402 | Rule-based fallback planner | [ledger](../progress/sprint-4.md) |
| IMP-504 | PlacePicker (uses the place search API) | [ledger](../progress/sprint-5.md) |
| IMP-604 | Search and filter queries, place detail API, indexes | [ledger](../progress/sprint-6.md) |
| IMP-606 | Food places data and meal-slot retrieval; meal-slot display on item cards | [ledger](../progress/sprint-6.md) |
| IMP-610 | Restore transaction and retention | [ledger](../progress/sprint-6.md) |
| IMP-707 | SRS and data model section | [ledger](../progress/sprint-7.md) |
| IMP-803 | Pre-demo checklist: database reset and fallback drill | [record](../progress/parts/IMP-803-checklist-data-accounts.md), [record](../progress/parts/IMP-803-checklist-db-fallback.md) |
| IMP-804 | Final report: data and architecture chapters | [record](../progress/parts/IMP-804-presentation-outline.md), [record](../progress/parts/IMP-804-report-ai-chapter.md), [record](../progress/parts/IMP-804-report-data-architecture.md) |

Cut assignments (not built): IMP-710, IMP-713.

**Main PR references for owned merged work:** [#191](https://github.com/het-lathiya/Group12/pull/191), [#193](https://github.com/het-lathiya/Group12/pull/193), [#199](https://github.com/het-lathiya/Group12/pull/199), [#205](https://github.com/het-lathiya/Group12/pull/205), [#228](https://github.com/het-lathiya/Group12/pull/228), [#242](https://github.com/het-lathiya/Group12/pull/242), [#248](https://github.com/het-lathiya/Group12/pull/248), [#253](https://github.com/het-lathiya/Group12/pull/253), [#261](https://github.com/het-lathiya/Group12/pull/261), [#276](https://github.com/het-lathiya/Group12/pull/276), [#281](https://github.com/het-lathiya/Group12/pull/281), [#289](https://github.com/het-lathiya/Group12/pull/289).

**Review activity:** 0 submitted review record(s) in the merged-PR query. Requests/offline activity are not counted.

**Course documents / submission work:** 02-sprints/sprint-1.md through sprint-4.md (main).

## Jeel — Jeel Fefar

**Role:** Database and Data Engineer (ORM, Places API and Ranking).

**Plan / merged allocations:** 40 / 38. **Commits on main:** 42 (`Jeel Fefar <jeelfefar487@gmail.com>`).

**Cards and parts owned (task register; ownership does not by itself mean completed):**

| Card | Assigned part | Main evidence |
| --- | --- | --- |
| IMP-106 | ORM models, schema-drift test, test database fixture | [ledger](../progress/sprint-1.md) |
| IMP-107 | whole task | [ledger](../progress/sprint-1.md) |
| IMP-202 | whole task | [ledger](../progress/sprint-2.md) |
| IMP-205 | Places repository, destinations/categories API, basic place search (API-16) | [ledger](../progress/sprint-2.md) |
| IMP-206 | Lead curation of destination 1, load and quality report | [ledger](../progress/sprint-2.md) |
| IMP-304 | Scoring and ranking of the shortlist (preference weights) | [ledger](../progress/sprint-3.md) |
| IMP-315 | whole task | [ledger](../progress/sprint-3.md) |
| IMP-402 | Saved sample itineraries (data) | [ledger](../progress/sprint-4.md) |
| IMP-405 | Persist structured warnings and suggested fixes with the plan | [ledger](../progress/sprint-4.md) |
| IMP-509 | whole task | [ledger](../progress/sprint-5.md) |
| IMP-604 | PlaceDetailDrawer with labelled facts | [ledger](../progress/sprint-6.md) |
| IMP-605 | whole task | [ledger](../progress/sprint-6.md) |
| IMP-610 | Version snapshots (snap-1): save, list, restore; versions page and VersionList | [ledger](../progress/sprint-6.md) |
| IMP-707 | User guide | [ledger](../progress/sprint-7.md) |
| IMP-803 | Pre-demo checklist: data, accounts, sample itineraries | [record](../progress/parts/IMP-803-checklist-data-accounts.md), [record](../progress/parts/IMP-803-checklist-db-fallback.md) |
| IMP-804 | Presentation slides | [record](../progress/parts/IMP-804-presentation-outline.md), [record](../progress/parts/IMP-804-report-ai-chapter.md), [record](../progress/parts/IMP-804-report-data-architecture.md) |

Cut assignments (not built): IMP-515, IMP-712, IMP-713.

**Main PR references for owned merged work:** [#193](https://github.com/het-lathiya/Group12/pull/193), [#197](https://github.com/het-lathiya/Group12/pull/197), [#205](https://github.com/het-lathiya/Group12/pull/205), [#206](https://github.com/het-lathiya/Group12/pull/206), [#209](https://github.com/het-lathiya/Group12/pull/209), [#242](https://github.com/het-lathiya/Group12/pull/242), [#248](https://github.com/het-lathiya/Group12/pull/248), [#252](https://github.com/het-lathiya/Group12/pull/252), [#267](https://github.com/het-lathiya/Group12/pull/267), [#270](https://github.com/het-lathiya/Group12/pull/270), [#275](https://github.com/het-lathiya/Group12/pull/275), [#281](https://github.com/het-lathiya/Group12/pull/281), [#289](https://github.com/het-lathiya/Group12/pull/289).

**Review activity:** 0 submitted review record(s) in the merged-PR query. Requests/offline activity are not counted.

**Course documents / submission work:** 02-sprints/sprint-5.md through sprint-8.md; 12-not-implemented.md (main); slides S1–S5 (RUN-102 draft).

## Manya — Manya Rana

**Role:** AI/ML Engineer (Prompt Engineering, Validation and Evaluation).

**Plan / merged allocations:** 40 / 37. **Commits on main:** 34 (`Manya Rana <manyarana06@gmail.com>`).

**Cards and parts owned (task register; ownership does not by itself mean completed):**

| Card | Assigned part | Main evidence |
| --- | --- | --- |
| IMP-111 | whole task | [ledger](../progress/sprint-1.md) |
| IMP-207 | whole task | [ledger](../progress/sprint-2.md) |
| IMP-301 | API-style spike (OD-14) and recorded-response tests | [ledger](../progress/sprint-3.md) |
| IMP-303 | whole task | [ledger](../progress/sprint-3.md) |
| IMP-306 | Output validation: io-1 schema and place-ID check | [ledger](../progress/sprint-3.md) |
| IMP-316 | gr-2 and io-2 schemas, template v2, passage size control, citation check, retrieval fields on the generation record, MOCK citations | [ledger](../progress/sprint-3.md) |
| IMP-406 | Keep must-visit places and explicit constraints in the pipeline | [ledger](../progress/sprint-4.md) |
| IMP-413 | whole task | [ledger](../progress/sprint-4.md) |
| IMP-503 | Pace presets and grouping nearby places into days | [ledger](../progress/sprint-5.md) |
| IMP-514 | Evaluation run records | [ledger](../progress/sprint-5.md) |
| IMP-603 | Curate a share of destination 2 places and verify sources | No merged ledger row/part record located; human completion remains unverified |
| IMP-606 | Meal slots in the request builder and fallback planner | [ledger](../progress/sprint-6.md) |
| IMP-706 | whole task | [ledger](../progress/sprint-7.md) |
| IMP-804 | Final report: AI chapter | [record](../progress/parts/IMP-804-presentation-outline.md), [record](../progress/parts/IMP-804-report-ai-chapter.md), [record](../progress/parts/IMP-804-report-data-architecture.md) |

Cut assignments (not built): IMP-613, IMP-708, IMP-709.

**Main PR references for owned merged work:** [#198](https://github.com/het-lathiya/Group12/pull/198), [#208](https://github.com/het-lathiya/Group12/pull/208), [#249](https://github.com/het-lathiya/Group12/pull/249), [#251](https://github.com/het-lathiya/Group12/pull/251), [#254](https://github.com/het-lathiya/Group12/pull/254), [#259](https://github.com/het-lathiya/Group12/pull/259), [#261](https://github.com/het-lathiya/Group12/pull/261), [#275](https://github.com/het-lathiya/Group12/pull/275), [#276](https://github.com/het-lathiya/Group12/pull/276), [#281](https://github.com/het-lathiya/Group12/pull/281), [#289](https://github.com/het-lathiya/Group12/pull/289).

**Review activity:** 0 submitted review record(s) in the merged-PR query. Requests/offline activity are not counted.

**Course documents / submission work:** 08-mutation-testing.md (main; PR #302); slides S6–S10 (RUN-102 draft).

## Manasvi — Manasvi Rathore

**Role:** Frontend Engineer (Web App Lead).

**Plan / merged allocations:** 41 / 38. **Commits on main:** 47 (`Manasvi Rathore <202301108@dau.ac.in>`).

**Cards and parts owned (task register; ownership does not by itself mean completed):**

| Card | Assigned part | Main evidence |
| --- | --- | --- |
| IMP-104 | whole task | [ledger](../progress/sprint-1.md) |
| IMP-212 | whole task | [ledger](../progress/sprint-2.md) |
| IMP-218 | Web production image: standalone Next.js Dockerfile and local compose service | [ledger](../progress/sprint-2.md) |
| IMP-309 | Day-wise itinerary view, SourceBadge and AiBadge labels | [ledger](../progress/sprint-3.md) |
| IMP-317 | whole task | [ledger](../progress/sprint-3.md) |
| IMP-405 | WarningsPanel | [ledger](../progress/sprint-4.md) |
| IMP-408 | ItemEditor | [ledger](../progress/sprint-4.md) |
| IMP-409 | Drag-and-drop and keyboard MoveControls (dnd-kit) | [ledger](../progress/sprint-4.md) |
| IMP-412 | whole task | [ledger](../progress/sprint-4.md) |
| IMP-503 | Pace control in the preference form | [ledger](../progress/sprint-5.md) |
| IMP-507 | Costs page and CostBreakdown | [ledger](../progress/sprint-5.md) |
| IMP-508 | whole task | [ledger](../progress/sprint-5.md) |
| IMP-602 | Dashboard and TripCard | [ledger](../progress/sprint-6.md) |
| IMP-604 | PlaceFilterBar | [ledger](../progress/sprint-6.md) |
| IMP-704 | Usability session 2 and top-issue fixes | No merged ledger row/part record located; human completion remains unverified |
| IMP-802 | Frontend defect fixes | No merged ledger row/part record located; human completion remains unverified |

Cut assignments (not built): IMP-612, IMP-708, IMP-711.

**Main PR references for owned merged work:** [#192](https://github.com/het-lathiya/Group12/pull/192), [#235](https://github.com/het-lathiya/Group12/pull/235), [#245](https://github.com/het-lathiya/Group12/pull/245), [#253](https://github.com/het-lathiya/Group12/pull/253), [#255](https://github.com/het-lathiya/Group12/pull/255), [#260](https://github.com/het-lathiya/Group12/pull/260), [#267](https://github.com/het-lathiya/Group12/pull/267), [#268](https://github.com/het-lathiya/Group12/pull/268), [#272](https://github.com/het-lathiya/Group12/pull/272), [#275](https://github.com/het-lathiya/Group12/pull/275), [#276](https://github.com/het-lathiya/Group12/pull/276), [#277](https://github.com/het-lathiya/Group12/pull/277), [#278](https://github.com/het-lathiya/Group12/pull/278), [#281](https://github.com/het-lathiya/Group12/pull/281).

**Review activity:** 0 submitted review record(s) in the merged-PR query. Requests/offline activity are not counted.

**Course documents / submission work:** 13-ui-ux.md (main).

## Krrish — Krrish Kamani

**Role:** Frontend and QA Engineer (Accessibility and End-to-End Testing).

**Plan / merged allocations:** 39 / 34. **Commits on main:** 57 (`Krrish Kamani <krrishkamani51@gmail.com>`).

**Cards and parts owned (task register; ownership does not by itself mean completed):**

| Card | Assigned part | Main evidence |
| --- | --- | --- |
| IMP-109 | whole task | [ledger](../progress/sprint-1.md) |
| IMP-114 | Interview guide and recorded findings | No merged ledger row/part record located; human completion remains unverified |
| IMP-213 | whole task | [ledger](../progress/sprint-2.md) |
| IMP-305 | Privacy notice and live progress on the generate page | [ledger](../progress/sprint-3.md) |
| IMP-314 | Research and write the destination 1 guide documents with sources | [ledger](../progress/sprint-3.md) |
| IMP-403 | FallbackNotice on the generate page | [ledger](../progress/sprint-4.md) |
| IMP-406 | AI-written text labels on item cards | [ledger](../progress/sprint-4.md) |
| IMP-410 | Draft resume in wizard and dashboard | [ledger](../progress/sprint-4.md) |
| IMP-411 | BudgetSettingsForm and SourceBadge variants | [ledger](../progress/sprint-4.md) |
| IMP-414 | E2E journey test on staging | [ledger](../progress/sprint-4.md) |
| IMP-505 | AlternativesDialog | [ledger](../progress/sprint-5.md) |
| IMP-506 | Lock toggle on item cards | [ledger](../progress/sprint-5.md) |
| IMP-510 | Trip edit page and StalePlanBanner | [ledger](../progress/sprint-5.md) |
| IMP-513 | whole task | [ledger](../progress/sprint-5.md) |
| IMP-607 | Regenerate controls in DayColumn | [ledger](../progress/sprint-6.md) |
| IMP-608 | BudgetAlert component | [ledger](../progress/sprint-6.md) |
| IMP-609 | Summary page and print layout | [ledger](../progress/sprint-6.md) |
| IMP-611 | Record findings | [record](../progress/parts/IMP-611-prepare.md) |
| IMP-701 | whole task | [ledger](../progress/sprint-7.md) |
| IMP-703 | whole task | [ledger](../progress/sprint-7.md) |

Cut assignments (not built): IMP-515, IMP-710, IMP-712.

**Main PR references for owned merged work:** [#194](https://github.com/het-lathiya/Group12/pull/194), [#239](https://github.com/het-lathiya/Group12/pull/239), [#250](https://github.com/het-lathiya/Group12/pull/250), [#253](https://github.com/het-lathiya/Group12/pull/253), [#260](https://github.com/het-lathiya/Group12/pull/260), [#261](https://github.com/het-lathiya/Group12/pull/261), [#267](https://github.com/het-lathiya/Group12/pull/267), [#272](https://github.com/het-lathiya/Group12/pull/272), [#273](https://github.com/het-lathiya/Group12/pull/273), [#276](https://github.com/het-lathiya/Group12/pull/276), [#277](https://github.com/het-lathiya/Group12/pull/277), [#278](https://github.com/het-lathiya/Group12/pull/278), [#281](https://github.com/het-lathiya/Group12/pull/281), [#282](https://github.com/het-lathiya/Group12/pull/282), [#287](https://github.com/het-lathiya/Group12/pull/287), [#289](https://github.com/het-lathiya/Group12/pull/289), [#291](https://github.com/het-lathiya/Group12/pull/291).

**Review activity:** 0 submitted review record(s) in the merged-PR query. Requests/offline activity are not counted.

**Course documents / submission work:** 07-gui-testing.md; 09-non-functional-testing.md (main; PR #302).

## Proposed marks distribution

**[team to decide; default equal]**

The team must agree this line. Commit counts, merged allocations and draft documentation do not automatically assign marks. No signatures have been supplied.

## Signatures

| Member | Signature | Date |
| --- | --- | --- |
| Nidhi Chauhan | ____________________ | __________ |
| chaudhari kirtan sandipbhai | ____________________ | __________ |
| Manal Patel | ____________________ | __________ |
| Het Lathiya | ____________________ | __________ |
| Mohammad Junaid Kureshi | ____________________ | __________ |
| Malhar Mer | ____________________ | __________ |
| Jeel Fefar | ____________________ | __________ |
| Manya Rana | ____________________ | __________ |
| Manasvi Rathore | ____________________ | __________ |
| Krrish Kamani | ____________________ | __________ |
| Group leader confirmation — Nidhi Chauhan | ____________________ | __________ |

## Rebuild and print

Refresh evidence with `python3 scripts/build_contribution.py --refresh` (requires git and gh); ordinary rebuild uses the committed evidence snapshot. Export with the external-tool command in the RUN-102 contribution part record. The PDF is unsigned and retains the same team-decision placeholders.
