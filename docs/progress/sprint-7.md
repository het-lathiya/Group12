# Sprint 7 index (week 7): Quality and usability — gate SG-7

One line per task part of Sprint 7 (task register). Evidence lives in the part records under `docs/progress/parts/`; the gate card IMP-799 compiles this index from them. The Status column comes from the merged pull requests, not from the records' own status lines, which were written before merging. The Acceptance column is copied from each part record and is not upgraded here.

Compiled by IMP-799 (RUN-087) on 22 November 2026 from the part records and the merged pull requests #287 to #291 on `main` at `4fe514c`, the release-candidate commit. Gate result: see [gates.md, SG-7](gates.md#sg-7-end-of-week-7-release-candidate-and-extension-freeze-imp-799) (**not passed yet, provisional**).

Where a record says its suites were "verified locally", the same suites ran in CI on `main` at `4fe514c`: [CI 45037634091](https://github.com/het-lathiya/Group12/actions/runs/45037634091) (push, success: `lint-types`, `unit`, `guards`, `audit`, `api`; `attribution` skipped on push) and [E2E 45037634127](https://github.com/het-lathiya/Group12/actions/runs/45037634127) (push, success; staging job skipped). That is a suite-level result; this index does not turn a record's "not verified" into "verified" per criterion. No staging, device, screen-reader or usability result exists for Sprint 7.

| Task | Title | Part | Owner | Points | Run | Pull request | Merged | Status | Acceptance (from the part record) | Part record |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| IMP-701 | End-to-end regression suite for all primary scenarios | whole-task | Krrish (lead) | 3 | RUN-081, RUN-081b, RUN-081c, RUN-081d | #287 | 18 November 2026 | merged | three consecutive local `make e2e` runs verified (each `37 skipped`; `82 passed`, retries 0); E2E-01 to E2E-08, TC-369, TC-371 to TC-376 verified locally; floor journey verified locally; a deliberately broken assertion failing in CI not verified (local demo only) | [record](parts/IMP-701-whole-task.md) |
| IMP-702 | Authorization and security test pass | authz-injection | Junaid (lead) | 2 | RUN-081, RUN-081b | #287 | 18 November 2026 | merged | verified locally (CHK-03, CHK-04, TC-344 to TC-351, TC-353 to TC-358, TC-432); TC-347 verified after the F-1 fix; TC-352, TC-433, TC-434, TC-436 and the ECR scan not verified (staging window) | [record](parts/IMP-702-authz-injection.md) |
| IMP-702 | Authorization and security test pass | auth-fixes | Het | 2 | RUN-081b | #287 | 18 November 2026 | merged | F-1 / TC-347 verified (regression failed before the fix and passes after it, IMD-204); staging and production `SUPABASE_URL` not verified | [record](parts/IMP-702-auth-fixes.md) |
| IMP-702 | Authorization and security test pass | headers-secret-scan | Kirtan | 1 | RUN-081 | #287 | 18 November 2026 | merged | TC-351 (CORS) verified; gitleaks configuration review verified; response headers and TC-352 on staging not verified (IMD-205) | [record](parts/IMP-702-headers-secret-scan.md) |
| IMP-703 | Accessibility check on real devices and fixes | prepare | Krrish (lead) | 0 (3 pending) | RUN-083, RUN-083b | #289, #291 | 20 and 22 November 2026 | merged (prepare only); **device and screen-reader sessions pending** | template verified; keyboard and journey axe scans verified locally (`4 passed (31.6s)`, `4 passed (10.8s)`, every axe line `[]`); US-126 AC1 and the severity 1-2 criterion not verified (no session yet) | [record](parts/IMP-703-prepare.md) |
| IMP-704 | Usability session 2 and fixes of the top issues | — | Manasvi (lead), Junaid | 3 (pending) | none | none | — | **not started** (needs IMP-611 session 1) | no part record | none |
| IMP-705 | Final evaluation baseline and cost report | whole-task | Nidhi | 1 | RUN-083, RUN-083b, RUN-083c, RUN-083d | #289, #291 | 20 and 22 November 2026 | merged | FR-120 / TC-390 verified (MOCK ×2, rule-based, GEMINI records); TC-392 verified with a caveat (23 of 45 GEMINI attempts completed); TC-393 verified; TC-458 verified for MOCK, GEMINI not possible (HTTP 503); TC-388 and TC-389 not verified by name | [record](parts/IMP-705-whole-task.md) |
| IMP-706 | Stage 2 readiness package (documents only) | whole-task | Manya | 3 | RUN-083 | #289 | 20 November 2026 | merged; record PARTIAL (blueprint content to confirm) | five files Proposed with owner and date verified (US-132 AC1, CHK-23); US-132 AC2 verified; TC-361 not verified by a test; E1 to E7 not verified (blueprint not in the repository) | [record](parts/IMP-706-whole-task.md) |
| IMP-707 | SRS, architecture, test plan, user guide and deployment guide | srs | Malhar (lead) | 2 | RUN-083 | #289 | 20 November 2026 | merged | step 1 verified for the repository state (18 differences listed); trials of step 6 not verified | [record](parts/IMP-707-srs.md) |
| IMP-707 | SRS, architecture, test plan, user guide and deployment guide | architecture-api | Manal | 1 | RUN-083 | #289 | 20 November 2026 | merged | 13 differences listed for the repository state; comparison with the running deployment not verified | [record](parts/IMP-707-architecture-api.md) |
| IMP-707 | SRS, architecture, test plan, user guide and deployment guide | test-plan | Junaid | 1 | RUN-083 | #289 | 20 November 2026 | merged | step 5 verified; trials of step 6 not verified | [record](parts/IMP-707-test-plan.md) |
| IMP-707 | SRS, architecture, test plan, user guide and deployment guide | user-guide | Jeel | 1 | RUN-083 | #289 | 20 November 2026 | merged; record PARTIAL (16 screenshot placeholders, new-member trial open) | owner and version verified; six differences listed from the code; US-146 AC1 not verified | [record](parts/IMP-707-user-guide.md) |
| IMP-707 | SRS, architecture, test plan, user guide and deployment guide | deployment-guide | Kirtan | 1 | RUN-083 | #289 | 20 November 2026 | merged; record PARTIAL (AWS and Supabase steps and clean-account trial open) | owner and version verified; eight differences listed; US-146 AC2 / CHK-18 not verified | [record](parts/IMP-707-deployment-guide.md) |
| IMP-708 | Natural-language trip intake with confirmation | — | Nidhi (lead), Manya, Manal, Manasvi | 8 | none | none | — | **cut** (IMD-65); `nl_intake` not built | not built (no route, table or screen) | none |
| IMP-709 | "Why this plan" explanations for each day | — | Nidhi (lead), Het, Manya | 5 | none | none | — | **cut** (IMD-65); `day_explain` not built | not built | none |
| IMP-710 | Rain-aware day swapping with the Open-Meteo forecast | — | Manal (lead), Malhar, Krrish | 7 | none | none | — | **cut** (IMD-65); `rain_swap` not built | not built | none |
| IMP-711 | "Today" companion view for trip days | — | Manasvi (lead), Het | 3 | none | none | — | **cut** (IMD-65); `today_view` not built | not built | none |
| IMP-712 | Budget-fit suggestions when a plan is over budget | — | Junaid (lead), Jeel, Krrish | 7 | none | none | — | **cut** (IMD-65); `budget_fit` not built | not built | none |
| IMP-713 | Destination and place context cards from Wikivoyage and Wikipedia | — | Malhar (lead), Jeel, Kirtan | 6 | none | none | — | **cut** (IMD-65); `context_cards` not built | not built | none |
| IMP-799 | Sprint 7 gate SG-7: release candidate | whole-task | Kirtan | 2 (pending) | RUN-087 | this PR | — | **provisional**: not passed yet | see [gates.md, SG-7](gates.md#sg-7-end-of-week-7-release-candidate-and-extension-freeze-imp-799) | [record](parts/IMP-799-whole-task.md) |

**Points.** Sprint 7 plans 62 points on 14 cards. IMP-708 to IMP-713 (36 points) are extensions, cut by IMD-65, so 26 points are in scope. 18 points over 11 parts on 5 cards are merged (IMP-701 3, IMP-702 5, IMP-705 1, IMP-706 3, IMP-707 6); IMP-706 and the IMP-707 user-guide and deployment-guide parts are merged with their human steps still open. Pending: IMP-703 (3 points, earned by the device and screen-reader sessions), IMP-704 (3 points, not started) and the gate card IMP-799 (2 points, provisional).

## Points earned in Sprint 7 per member

From the card points of the task register and the owner of each merged part. Fix and decision runs carry no points.

| Member | Parts | Points |
| --- | --- | --- |
| Krrish | IMP-701 whole-task 3 (IMP-703 3 pending) | 3 |
| Junaid | IMP-702 authz-injection 2, IMP-707 test-plan 1 (IMP-704 part pending) | 3 |
| Manya | IMP-706 whole-task 3 (record PARTIAL) | 3 |
| Het | IMP-702 auth-fixes 2 | 2 |
| Kirtan | IMP-702 headers-secret-scan 1, IMP-707 deployment-guide 1 (record PARTIAL) (IMP-799 2 pending) | 2 |
| Malhar | IMP-707 srs 2 | 2 |
| Nidhi | IMP-705 whole-task 1 | 1 |
| Manal | IMP-707 architecture-api 1 | 1 |
| Jeel | IMP-707 user-guide 1 (record PARTIAL) | 1 |
| Manasvi | none (IMP-704 pending) | 0 |
| **Total** | 11 parts | **18** |

## Integration batches (pull requests)

| Pull request | Title | Commits on `main` | Merged |
| --- | --- | --- | --- |
| #287 | S7-A · IMP-701 e2e regression + IMP-702 security pass | 20 | 18 November 2026 |
| #289 | S7-B · IMP-705/706 evaluation and Stage 2, IMP-707 documents, IMP-703 prepare | 12 | 20 November 2026 |
| #290 | IMD-214 · fix red main: scope the push secret scan | 2 | 20 November 2026 |
| #291 | S7-B2 · IMP-705 final baseline completed, IMP-703 axe results, IMD-213 | 6 | 22 November 2026 |

Two commits reached `main` outside these pull requests with the IMD-208 history rewrite of 18 November 2026: the decision record of IMD-208 and IMD-209 (Nidhi) and `docs/progress/commit-map.md` (Kirtan). Commit IDs quoted in records written before 18 November 2026 are old IDs (IMD-208).

## Fix and decision runs (no points)

| Run | Fix | Owner | Pull request | Decision | Record |
| --- | --- | --- | --- | --- | --- |
| RUN-081 | Decision record IMD-202 (Sprint 7 batch order) | Nidhi | #287 | — | `docs/spec/DECISION_REGISTER.md` |
| RUN-081 | `client.ts` lint warning | Kirtan | #287 | — | commit `chore(web): IMP-214 clear the client.ts lint warning` |
| RUN-081b | Decision record IMD-203 to IMD-205 | Nidhi | #287 | — | `docs/spec/DECISION_REGISTER.md` |
| RUN-081b | Local sign-in rate limit for the E2E suite | Malhar | #287 | IMD-203 | commit `chore(env): IMP-105 raise the local sign-in rate limit for the E2E suite (IMD-203)` |
| RUN-081b | Versions page shows not-found for another user's trip | Jeel | #287 | — | [IMP-701 record](parts/IMP-701-whole-task.md), "Decisions and open issues" |
| RUN-081c | Decision record IMD-206 | Nidhi | #287 | — | `docs/spec/DECISION_REGISTER.md` |
| RUN-081c | Lock toggle name contains its visible label (TC-383) | Krrish | #287 | IMD-206 | commit `fix(itinerary): IMP-506 lock toggle name contains its visible label (TC-383)` |
| RUN-081c | Keyboard-reachable scroll regions in the cost breakdown | Manasvi | #287 | IMD-206 | commit `fix(costs): IMP-507 keyboard-reachable scroll regions in the cost breakdown` |
| RUN-081d | Decision record IMD-207 | Nidhi | #287 | — | `docs/spec/DECISION_REGISTER.md` |
| RUN-081d | Trip navigation fits 360 and 768 px without hiding tabs | Manasvi | #287 | IMD-207 | [IMP-701 record](parts/IMP-701-whole-task.md), "RUN-081d final verification" |
| RUN-083 | Decision record IMD-211 (operator change, main-branch rule) | Nidhi | #289 | — | `docs/spec/DECISION_REGISTER.md` |
| RUN-083 | Semantic similarities compared with a tolerance (IMP-315 test) | Jeel | #289 | — | commit `test(rag): IMP-315 compare semantic similarities with a tolerance` |
| RUN-083 | Separate CI concurrency for pull-request edits | Kirtan | #289 | IMD-183, IMD-184 | [record](parts/FIX-RUN-083-ci-concurrency.md) |
| RUN-083 | IMP-608 itinerary cost-strip triage | Manal | #289 | PD-RUN-083-1 (proposed) | [record](parts/IMP-608-cost-strip-triage.md) |
| — | Push secret scan scoped to the pushed branch (red `main` after #289) | Kirtan (ci), Nidhi (decision) | #290 | IMD-214 | `docs/spec/DECISION_REGISTER.md` |
| RUN-083b | Decision record IMD-213 | Nidhi | #291 | — | `docs/spec/DECISION_REGISTER.md` |
| RUN-083b | Rule-based provider in the evaluation harness | Manya | #291 | IMD-213 | [IMP-705 record](parts/IMP-705-whole-task.md), "RUN-083b" |
| RUN-087 | SG-7 gate record (provisional) | Kirtan | this PR | — | [record](parts/IMP-799-whole-task.md) |

## Decisions of Sprint 7

IMD-202 (Sprint 7 batch order), IMD-203 (local sign-in rate limit and IMP-701 run evidence), IMD-204 (token issuer check), IMD-205 (security headers for TC-352), IMD-206 (provider-failure spec set-up and accessibility defects under the freeze), IMD-207 (app shell layout fix under the freeze), IMD-208 (committer identity on `main`), IMD-209 (merge method from 18 November 2026), IMD-211 (operator change and main-branch rule), IMD-213 (final evaluation: rule-based run and prompt version), IMD-214 (secret scan scope on pushes to `main`). All in `docs/spec/DECISION_REGISTER.md`; the register holds no IMD-210 or IMD-212.

## IMP-707 drafts

The document set of IMP-707, as the five part records list it (all merged in #289):

| Document | Part | Owner | Version (from the document header) |
| --- | --- | --- | --- |
| [`docs/srs.md`](../srs.md) | srs | Malhar | 1.0 (draft for SG-7), 19 November 2026 |
| [`docs/architecture.md`](../architecture.md), [`docs/api.md`](../api.md) | architecture-api | Manal | 1.0 (draft for SG-7), 19 November 2026 (both) |
| [`docs/test-plan.md`](../test-plan.md) | test-plan | Junaid | 1.0 (draft for SG-7), 19 November 2026 |
| [`docs/guides/user-guide.md`](../guides/user-guide.md) | user-guide | Jeel | 0.1, draft of 19 November 2026 |
| [`docs/guides/deployment-guide.md`](../guides/deployment-guide.md) and the "Documentation" section of `README.md` | deployment-guide | Kirtan | 0.1, draft of 19 November 2026 |

Stage 2 package (IMP-706): [`docs/stage2/README.md`](../stage2/README.md), `migration-gate-criteria.md`, `data-governance-policy.md`, `dataset-schema.md`, `data-card-template.md`, each marked Proposed.

**IMP-707 card step 6 outcome** ("A member outside the platform squad follows README setup (time recorded, NFR-032, TC-335) and the deployment guide on a clean account; record the outcome in docs/progress/sprint-7.md"): **pending** (Malhar, card lead; Kirtan for the clean AWS account; due 26 Nov 2026). The user-guide trial of US-146 AC1 ("A new member created a trip and an itinerary from the user guide without help") is **pending** (Jeel; due 26 Nov 2026). No time or outcome is recorded here because none was observed.

## Human results of Sprint 7

| Activity | Card | Owner | Result |
| --- | --- | --- | --- |
| Device sessions (one iOS and one Android phone) and one desktop screen reader (TC-382) | IMP-703 | Junaid (runs), Krrish (records) | pending (Junaid, Krrish) |
| Usability session 1 | IMP-611 | Junaid, Krrish | pending (Junaid, Krrish) |
| Usability session 2 | IMP-704 | Manasvi, Junaid | pending (Manasvi, Junaid) |
| README setup and deployment guide on a clean account | IMP-707 step 6 | Malhar, Kirtan | pending (Malhar, Kirtan) |
| User guide followed by a new member | IMP-707 (US-146 AC1) | Jeel | pending (Jeel) |
| Confirmation of E1 to E7 and other blueprint content | IMP-706 | Manya | pending (Manya) |
| Staging results (deploy of the candidate, smoke, ACC-01 to ACC-18, live smoke, staging security rows) | IMP-799, IMP-702 | Kirtan (Het for the Gemini key) | pending (Kirtan) |

## Sprint 1–7 task status for SG-7

IMP-799 step 1: "Check docs/progress/sprint-1.md to sprint-7.md: every IMP task is done with evidence or listed open with owner and due date." Every card of Sprints 1 to 7 in the task register, one row each. "done" means the card's parts are merged with a part record (or a gate entry) on `main` at `4fe514c`. "done; open item" means merged, with an evidence gap or staging check still open; the gap is listed with owner and due date. Extensions are "cut (IMD-65)", not open. Due dates of 26 Nov 2026 are planner-set where no record gives a date.

Result: **114 cards**: 71 done, 27 done with an open item, 6 open (IMP-113, IMP-114, IMP-603, IMP-611, IMP-703, IMP-704), 9 cut (IMP-515, IMP-612, IMP-613, IMP-708 to IMP-713), 1 this gate (IMP-799).

| Task | Sprint | Title | Type | Status | Evidence | Open item · owner · due |
| --- | --- | --- | --- | --- | --- | --- |
| IMP-101 | 1 | Repository skeleton, toolchain, Makefile, CLAUDE.md and docs/progress folders | CODE | done | [api-pyproject-guard](parts/IMP-101-api-pyproject-guard.md), [repo-tree-makefile](parts/IMP-101-repo-tree-makefile.md) | — |
| IMP-102 | 1 | CI workflow (lint, types, imports, unit, guards, audit), branch protection, PR template, CODEOWNERS | CODE | done | [whole-task](parts/IMP-102-whole-task.md) | — |
| IMP-103 | 1 | Backend skeleton: app factory, typed settings with start-up checks, error envelope, basic GET /health | CODE | done | [whole-task](parts/IMP-103-whole-task.md) | — |
| IMP-104 | 1 | Web skeleton: Next.js app, Tailwind and shadcn/ui, responsive AppShell, query provider, state components | CODE | done | [whole-task](parts/IMP-104-whole-task.md) | — |
| IMP-105 | 1 | Local environments: Supabase CLI stack, docker compose db, .env.example and env templates | CODE | done | [whole-task](parts/IMP-105-whole-task.md) | — |
| IMP-106 | 1 | MVP migrations 0001-0006 through Alembic, ORM models, schema-drift test, test database fixture | CODE | done | [orm-drift-fixture](parts/IMP-106-orm-drift-fixture.md), [sql-migrations](parts/IMP-106-sql-migrations.md) | — |
| IMP-107 | 1 | SAMPLE fixture destination and minimal seed command | CODE | done | [whole-task](parts/IMP-107-whole-task.md) | — |
| IMP-108 | 1 | Backend token verification and CurrentUser dependency, test token helper | CODE | done | [whole-task](parts/IMP-108-whole-task.md) | — |
| IMP-109 | 1 | Sign-up, sign-in, sign-out and AuthGuard with Supabase Auth | CODE | done | [whole-task](parts/IMP-109-whole-task.md) | — |
| IMP-110 | 1 | ModelProvider interface, shared AI schemas gr-1 and io-1, provider error types | CODE | done | [whole-task](parts/IMP-110-whole-task.md) | — |
| IMP-111 | 1 | Versioned prompt-template registry | CODE | done | [whole-task](parts/IMP-111-whole-task.md) | — |
| IMP-112 | 1 | Hello-world deployment to Vercel, Render and Supabase staging with deploy workflows | CODE | done | [whole-task](parts/IMP-112-whole-task.md); local half (#202); the hosted half moved to AWS under Amendment A1 (IMP-217, IMP-218) | — |
| IMP-113 | 1 | Provision accounts, keys and email sender with named owners | HUMAN | **open** | [accounts-secrets-register](parts/IMP-113-accounts-secrets-register.md), [gemini-key-terms](parts/IMP-113-gemini-key-terms.md), [ors-email-sender](parts/IMP-113-ors-email-sender.md); templates merged (#200); `docs/decisions/accounts.md` still reads "template; outcome pending" | account facts (Gemini tier, ORS key and allowance, e-mail sender, AWS plan) · Kirtan, Junaid, Nidhi · 26 Nov 2026 |
| IMP-114 | 1 | Stakeholder interviews round 1 and recorded findings | HUMAN | **open** | PR #288 (open; #201 closed) | interviews round 1 with anonymous notes (US-151) · Junaid, Krrish · 26 Nov 2026 |
| IMP-115 | 1 | Seed-data plan and choice of the two demo destinations | HUMAN | done | [whole-task](parts/IMP-115-whole-task.md); PR #199; IMD-120 | — |
| IMP-199 | 1 | Sprint 1 gate SG-1: runnable skeleton and contracts in place | VERIFY | done | [whole-task](parts/IMP-199-whole-task.md); [gates.md, SG-1](gates.md#sg-1-end-of-week-1-runnable-skeleton-and-contracts-in-place-imp-199) | — |
| IMP-201 | 2 | Readiness endpoint and structured request logging with request IDs | CODE | done | [whole-task](parts/IMP-201-whole-task.md) | — |
| IMP-202 | 2 | Generation record repository and lifecycle helpers (ai_generations) | CODE | done | [whole-task](parts/IMP-202-whole-task.md) | — |
| IMP-203 | 2 | Trips API: create, list and read a trip with validation | CODE | done | [whole-task](parts/IMP-203-whole-task.md) | — |
| IMP-204 | 2 | Preferences and must-visit places API with mapping to filters and ranking weights | CODE | done | [whole-task](parts/IMP-204-whole-task.md) | — |
| IMP-205 | 2 | Provenance-preserving place import with quality gate, categories and destinations API | CODE | done | [import-quality-gate](parts/IMP-205-import-quality-gate.md), [places-api-search](parts/IMP-205-places-api-search.md) | — |
| IMP-206 | 2 | Curate and load demo destination 1 | DATA | done; open item | [hours-prices](parts/IMP-206-hours-prices.md), [lead-curation](parts/IMP-206-lead-curation.md); #242 | load on staging · Kirtan (staging window) · 26 Nov 2026 |
| IMP-207 | 2 | Mock provider with scenario-based failure injection | CODE | done | [whole-task](parts/IMP-207-whole-task.md) | — |
| IMP-208 | 2 | Provider factory and configuration-based selection | CODE | done | [whole-task](parts/IMP-208-whole-task.md) | — |
| IMP-209 | 2 | Distance-based travel-time estimate (pure) | CODE | done | [whole-task](parts/IMP-209-whole-task.md) | — |
| IMP-210 | 2 | Walking-skeleton generation job: start and poll with MOCK, save a validated plan | CODE | done | [whole-task](parts/IMP-210-whole-task.md) | — |
| IMP-211 | 2 | Itinerary read endpoint and latest-itinerary lookup (minimal) | CODE | done | [whole-task](parts/IMP-211-whole-task.md) | — |
| IMP-212 | 2 | Trip wizard and preference form | CODE | done | [whole-task](parts/IMP-212-whole-task.md) | — |
| IMP-213 | 2 | Generate page with progress and read-only itinerary view (skeleton) | CODE | done | [whole-task](parts/IMP-213-whole-task.md) | — |
| IMP-214 | 2 | OpenAPI contract v1 export, generated web client and contract check | CODE | done | [whole-task](parts/IMP-214-whole-task.md); #227; tag `contract-v1` exists | — |
| IMP-215 | 2 | Two-user authorization suite for every owned route | CODE | done | [authz-tokens](parts/IMP-215-authz-tokens.md), [whole-task](parts/IMP-215-whole-task.md) | — |
| IMP-216 | 2 | Walking-skeleton end-to-end test and staging deployment | CODE | done; open item | [whole-task](parts/IMP-216-whole-task.md); #246 | staging walk-through · Kirtan (staging window) · 26 Nov 2026 |
| IMP-217 | 2 | AWS staging foundation: RDS PostgreSQL, ECR, SSM, ECS Express services, OIDC deploy role and budget | CODE | done; open item | [whole-task](parts/IMP-217-whole-task.md); #243; staging deploys run ([44733049430](https://github.com/het-lathiya/Group12/actions/runs/44733049430)) | staging checks TC-438, CORS, IMD-139 alarm output; `infra/aws` stdin scripts · Kirtan (staging window) · 26 Nov 2026 |
| IMP-218 | 2 | Web container and AWS deploy workflows with the release task | CODE | done; open item | [deploy-workflows](parts/IMP-218-deploy-workflows.md), [web-image](parts/IMP-218-web-image.md); #245 | TC-437, TC-438 and smoke on staging · Kirtan (staging window) · 26 Nov 2026 |
| IMP-219 | 2 | Supabase Auth with an AWS database: auth stub bootstrap and user row mirroring | CODE | done | [whole-task](parts/IMP-219-whole-task.md) | — |
| IMP-311 | 2 | RAG store: pgvector, corpus and chunk tables, item citations and retrieval record (migration 0007) | CODE | done | [whole-task](parts/IMP-311-whole-task.md) | — |
| IMP-299 | 2 | Sprint 2 gate SG-2 (blueprint Gate 1): walking skeleton on staging | VERIFY | done | [gates.md, SG-2](gates.md#sg-2-end-of-week-2-walking-skeleton-blueprint-gate-1-imp-299) | — |
| IMP-301 | 3 | Gemini adapter with structured output, error mapping and recorded-response tests | CODE | done | [gemini-adapter](parts/IMP-301-gemini-adapter.md), [spike-recordings](parts/IMP-301-spike-recordings.md), [wire-schema](parts/IMP-301-wire-schema.md) | — |
| IMP-302 | 3 | Provider metadata and health in readiness | CODE | done | [whole-task](parts/IMP-302-whole-task.md) | — |
| IMP-303 | 3 | Normalized generation request and prompt content and size control | CODE | done | [whole-task](parts/IMP-303-whole-task.md) | — |
| IMP-304 | 3 | Candidate retrieval, hard-constraint filters and ranking | CODE | done | [candidate-filters](parts/IMP-304-candidate-filters.md), [ranking](parts/IMP-304-ranking.md) | — |
| IMP-305 | 3 | Full generation pipeline through the active provider with job progress | CODE | done | [job-progress](parts/IMP-305-job-progress.md), [pipeline](parts/IMP-305-pipeline.md), [privacy-progress](parts/IMP-305-privacy-progress.md) | — |
| IMP-306 | 3 | Output validation: schema and place IDs | CODE | done | [injection-cases](parts/IMP-306-injection-cases.md), [output-validation](parts/IMP-306-output-validation.md); #251; D3 fix ([FIX-IMD-126](parts/FIX-IMD-126-outside-trip-drop.md)) | — |
| IMP-307 | 3 | OpenRouteService client with route cache and fallback | CODE | done | [whole-task](parts/IMP-307-whole-task.md) | — |
| IMP-308 | 3 | Deterministic recalculation of times, durations and trip cost estimate | CODE | done | [budget-costs](parts/IMP-308-budget-costs.md), [schedule](parts/IMP-308-schedule.md) | — |
| IMP-309 | 3 | Day-wise itinerary view with labels | CODE | done | [day-view](parts/IMP-309-day-view.md), [read-fields](parts/IMP-309-read-fields.md) | — |
| IMP-310 | 3 | Evaluation dataset version 1 (15 trips) | DATA | done | [whole-task](parts/IMP-310-whole-task.md) | — |
| IMP-312 | 3 | Embedding operation on ModelProvider: Gemini and deterministic MOCK embeddings | CODE | done | [whole-task](parts/IMP-312-whole-task.md) | — |
| IMP-313 | 3 | Corpus ingestion and indexing: place and guide documents, chunking, embedding, `make rag-index` | CODE | done; open item | [whole-task](parts/IMP-313-whole-task.md); #251 | RAG index line on staging · Kirtan (staging window) · 26 Nov 2026 |
| IMP-314 | 3 | Destination guides for demo destination 1 | DATA | done | [guides](parts/IMP-314-guides.md), [review](parts/IMP-314-review.md) | — |
| IMP-315 | 3 | Hybrid retrieval: semantic place scores and guide passages with lexical fallback | CODE | done | [test-robustness](parts/IMP-315-test-robustness.md), [whole-task](parts/IMP-315-whole-task.md) | — |
| IMP-316 | 3 | Grounded generation: passages in the request, validated citations, saved sources | CODE | done | [grounding](parts/IMP-316-grounding.md), [saved-sources](parts/IMP-316-saved-sources.md) | — |
| IMP-317 | 3 | Sources on itinerary items | CODE | done | [whole-task](parts/IMP-317-whole-task.md); #255; D12 fix ([FIX-IMD-135](parts/FIX-IMD-135-date-year.md)) | — |
| IMP-399 | 3 | Sprint 3 gate SG-3 (blueprint Gate 2): first Gemini itinerary on staging | VERIFY | done | [gates.md, SG-3](gates.md#sg-3-end-of-week-3-gemini-vertical-slice-blueprint-gate-2-imp-399) | — |
| IMP-401 | 4 | Retries with backoff and circuit breaker in the Gemini adapter | CODE | done | [whole-task](parts/IMP-401-whole-task.md) | — |
| IMP-402 | 4 | Rule-based fallback planner and saved sample itineraries | CODE | done; open item | [fallback-planner](parts/IMP-402-fallback-planner.md), [sample-itineraries](parts/IMP-402-sample-itineraries.md); #261, #270 | Ahmedabad saved samples (FR-036 AC3) · Jeel · 26 Nov 2026 |
| IMP-403 | 4 | Provider failure, timeout and quota handling end to end with fallback notice | CODE | done; open item | [failure-outcomes](parts/IMP-403-failure-outcomes.md), [fallback-notice](parts/IMP-403-fallback-notice.md); #267 | screenshots (fallback and paused-AI notices) · Krrish · 26 Nov 2026 |
| IMP-404 | 4 | Validator: overlaps, travel gaps, missing constraints and invalid references | CODE | done; open item | [reference-rules](parts/IMP-404-reference-rules.md), [schedule-rules](parts/IMP-404-schedule-rules.md); #259 | TC-334 coverage thresholds (report-only step) · Kirtan · 26 Nov 2026 |
| IMP-405 | 4 | Structured warnings with suggested fixes, persisted with the plan, warnings panel | CODE | done; open item | [persist-warnings](parts/IMP-405-persist-warnings.md), [warnings-panel](parts/IMP-405-warnings-panel.md); #267 | WarningsPanel screenshots at 1280 and 375 px · Manasvi · 26 Nov 2026 |
| IMP-406 | 4 | Preserve explicit constraints and must-visit places; label AI-written text | CODE | done; open item | [ai-text-labels](parts/IMP-406-ai-text-labels.md), [must-visit-constraints](parts/IMP-406-must-visit-constraints.md); #261 | screenshot of the AI label beside a source-labelled price · Krrish · 26 Nov 2026 |
| IMP-407 | 4 | Edit transaction core: recalculate and revalidate every edit atomically with plan revision | CODE | done | [whole-task](parts/IMP-407-whole-task.md) | — |
| IMP-408 | 4 | Remove an activity and change start time or duration | CODE | done; open item | [item-editor](parts/IMP-408-item-editor.md), [remove-retime-ops](parts/IMP-408-remove-retime-ops.md); #268, #272 | item-editor screenshots; 44 px targets at 375 px · Manasvi · 26 Nov 2026 |
| IMP-409 | 4 | Reorder by drag and by keyboard | CODE | done; open item | [move-controls](parts/IMP-409-move-controls.md), [move-op](parts/IMP-409-move-op.md); #268 | move-control screenshots; pointer drag gesture · Manasvi · 26 Nov 2026 |
| IMP-410 | 4 | Drafts and reopening the latest saved itinerary | CODE | done | [draft-latest-api](parts/IMP-410-draft-latest-api.md), [draft-resume-ui](parts/IMP-410-draft-resume-ui.md) | — |
| IMP-411 | 4 | Transport allowance, stay budget and price source labels | CODE | done | [budget-form-badges](parts/IMP-411-budget-form-badges.md), [budget-labels-api](parts/IMP-411-budget-labels-api.md) | — |
| IMP-412 | 4 | Loading, empty and error states on every MVP screen | CODE | done; open item | [whole-task](parts/IMP-412-whole-task.md); #260 | TC-384 error-catalogue checklist · Krrish · 26 Nov 2026 |
| IMP-413 | 4 | Evaluation harness (command line) | CODE | done | [whole-task](parts/IMP-413-whole-task.md) | — |
| IMP-318 | 4 | Retrieval evaluation: recall, hit rate, citation validity and grounding rate | CODE | done; open item | [whole-task](parts/IMP-318-whole-task.md); #271 | live-embedding retrieval figures (the GEMINI retrieval attempt of IMP-705 stopped with HTTP 503) · Junaid, Nidhi · 26 Nov 2026 |
| IMP-414 | 4 | End-to-end journey test on staging | VERIFY | done; open item | [journey-fixtures-report](parts/IMP-414-journey-fixtures-report.md), [journey-staging](parts/IMP-414-journey-staging.md); #272 | TC-370 journey on staging with GEMINI · Kirtan (staging window), Het · 26 Nov 2026 |
| IMP-499 | 4 | Sprint 4 gate SG-4 (blueprint Gate 3) and cut-list checkpoint | VERIFY | done | [whole-task](parts/IMP-499-whole-task.md); [gates.md, SG-4](gates.md#sg-4-end-of-week-4-core-reliability-blueprint-gate-3-imp-499) | — |
| IMP-501 | 5 | Opening-hours check, overpacked days and budget conflicts | CODE | done | [budget-conflict](parts/IMP-501-budget-conflict.md), [hours-checks](parts/IMP-501-hours-checks.md) | — |
| IMP-502 | 5 | Bounded repair with at most one model retry | CODE | done | [whole-task](parts/IMP-502-whole-task.md) | — |
| IMP-503 | 5 | Pace presets and grouping nearby places into days | CODE | done | [pace-control](parts/IMP-503-pace-control.md), [pace-grouping](parts/IMP-503-pace-grouping.md) | — |
| IMP-504 | 5 | Add a user-selected place and reject stale edits | CODE | done | [add-place-api](parts/IMP-504-add-place-api.md), [place-picker](parts/IMP-504-place-picker.md) | — |
| IMP-505 | 5 | Replace an activity with a ranked alternative | CODE | done | [alternatives-dialog](parts/IMP-505-alternatives-dialog.md), [replace-api](parts/IMP-505-replace-api.md) | — |
| IMP-506 | 5 | Lock and unlock items | CODE | done | [lock-api](parts/IMP-506-lock-api.md), [lock-toggle](parts/IMP-506-lock-toggle.md) | — |
| IMP-507 | 5 | Daily and category cost breakdown; estimate labels on every screen | CODE | done; open item | [breakdown-api](parts/IMP-507-breakdown-api.md), [costs-page](parts/IMP-507-costs-page.md); #275, #276 | TC-385 live-stack label review · Manasvi · 26 Nov 2026 |
| IMP-508 | 5 | Map with numbered markers and list fallback | CODE | done; open item | [whole-task](parts/IMP-508-whole-task.md); #275, #277, #278 | OpenFreeMap terms Unverified (`docs/decisions/map-tiles.md`) · Manasvi · 26 Nov 2026 |
| IMP-509 | 5 | Browse places with source labels | CODE | done | [whole-task](parts/IMP-509-whole-task.md) | — |
| IMP-510 | 5 | Edit trip settings and flag a stale plan | CODE | done | [edit-page](parts/IMP-510-edit-page.md), [settings-api](parts/IMP-510-settings-api.md) | — |
| IMP-511 | 5 | Rate limits and daily generation caps | CODE | done; open item | [whole-task](parts/IMP-511-whole-task.md); #276 | provider spending limit "Awaiting validation" (`docs/decisions/provider-spend-limit.md`) · Kirtan · 26 Nov 2026 |
| IMP-512 | 5 | Provider contract test suite for all adapters | CODE | done; open item | [whole-task](parts/IMP-512-whole-task.md); #275 | replace the hand-written Gemini recordings · Junaid · 26 Nov 2026 |
| IMP-513 | 5 | Keyboard and assistive-technology support | CODE | done; open item | [whole-task](parts/IMP-513-whole-task.md); #277, #278 | TC-382 screen-reader pass (with IMP-703) · Krrish · 26 Nov 2026 |
| IMP-514 | 5 | Evaluation run records and first Gemini baseline | DATA | done | [gemini-baseline](parts/IMP-514-gemini-baseline.md), [run-records](parts/IMP-514-run-records.md) | — |
| IMP-515 | 5 | Explain the ranking: "Why this place?" panel | CODE | cut (IMD-65) | IMD-186; `ranking_explain` not built | — |
| IMP-599 | 5 | Sprint 5 gate SG-5 | VERIFY | done | [gates.md, SG-5](gates.md#sg-5-end-of-week-5-trip-management-imp-599) | — |
| IMP-601 | 6 | Profile page and API | CODE | done | [whole-task](parts/IMP-601-whole-task.md) | — |
| IMP-602 | 6 | Trip dashboard with rename, duplicate, archive and delete | CODE | done | [dashboard](parts/IMP-602-dashboard.md), [trip-actions-api](parts/IMP-602-trip-actions-api.md) | — |
| IMP-603 | 6 | Curate and load demo destination 2 | DATA | **open** | no part record; `data/places/` holds only `ahmedabad`; deferred under IMD-201 (no curated files by Thu 19 Nov 2026) | demo destination 2 curated files and load, or a recorded deferral · Junaid, Manya, Kirtan · 26 Nov 2026 |
| IMP-604 | 6 | Search, filters and place detail with labelled facts | CODE | done | [detail-drawer](parts/IMP-604-detail-drawer.md), [filter-bar](parts/IMP-604-filter-bar.md), [search-api](parts/IMP-604-search-api.md) | — |
| IMP-605 | 6 | Saved places (wishlist) | CODE | done | [whole-task](parts/IMP-605-whole-task.md) | — |
| IMP-606 | 6 | Food places and meal slots | CODE | done | [meal-builder](parts/IMP-606-meal-builder.md), [meal-retrieval](parts/IMP-606-meal-retrieval.md) | — |
| IMP-607 | 6 | Regenerate one day around locks and the whole itinerary | CODE | done | [day-scope](parts/IMP-607-day-scope.md), [regen-api](parts/IMP-607-regen-api.md), [regen-controls](parts/IMP-607-regen-controls.md) | — |
| IMP-608 | 6 | Budget alerts and contingency buffer | CODE | done; open item | [alerts-contingency](parts/IMP-608-alerts-contingency.md), [budget-alert](parts/IMP-608-budget-alert.md), [cost-strip-triage](parts/IMP-608-cost-strip-triage.md); #281; cost-strip triage in #289 | itinerary cost strip: decision PD-RUN-083-1 · Manal, Krrish · 26 Nov 2026 |
| IMP-609 | 6 | Final trip summary and print view | CODE | done; open item | [summary-api](parts/IMP-609-summary-api.md), [summary-page](parts/IMP-609-summary-page.md); #281 | manual print preview with screenshot · Krrish · 26 Nov 2026 |
| IMP-610 | 6 | Itinerary versions: save, list and restore | CODE | done; open item | [restore-retention](parts/IMP-610-restore-retention.md), [version-snapshots](parts/IMP-610-version-snapshots.md); #281; foreign-trip fix in #287 | versions page screenshot after a restore · Jeel · 26 Nov 2026 |
| IMP-611 | 6 | Usability session 1 and recorded findings | HUMAN | **open** | [prepare](parts/IMP-611-prepare.md); templates merged (#281); `docs/acceptance/usability-1/findings.md` is an empty template | usability session 1 (five sessions) and findings · Junaid, Krrish · 26 Nov 2026 |
| IMP-612 | 6 | Optimise day order to cut travel time | CODE | cut (IMD-65) | IMD-186; `optimise_order` not built | — |
| IMP-613 | 6 | Packing checklist with AI free-text refinement | CODE | cut (IMD-65) | `packing` not built | — |
| IMP-699 | 6 | Sprint 6 gate SG-6: MVP feature-complete and feature freeze | VERIFY | done | [gates.md, SG-6](gates.md#sg-6-end-of-week-6-mvp-feature-freeze-imp-699) (PR #286) | — |
| IMP-701 | 7 | End-to-end regression suite for all primary scenarios | CODE | done; open item | [whole-task](parts/IMP-701-whole-task.md); #287; [e2e-sprint7.md](../test-reports/e2e-sprint7.md) | deliberately broken assertion shown failing in CI (card criterion 3) · Krrish · 26 Nov 2026 |
| IMP-702 | 7 | Authorization and security test pass | CODE | done; open item | [auth-fixes](parts/IMP-702-auth-fixes.md), [authz-injection](parts/IMP-702-authz-injection.md), [headers-secret-scan](parts/IMP-702-headers-secret-scan.md); #287; [security-sprint7.md](../test-reports/security-sprint7.md) | TC-352, TC-433, TC-434, TC-436, ECR scan; staging and production `SUPABASE_URL` (IMD-204) · Kirtan (staging window) · 26 Nov 2026 |
| IMP-703 | 7 | Accessibility check on real devices and fixes | HUMAN | **open** | [prepare](parts/IMP-703-prepare.md); prepare part merged (#289, #291): template and local axe runs | device and screen-reader sessions (TC-382), findings and fixes · Junaid (runs), Krrish (records) · 26 Nov 2026 |
| IMP-704 | 7 | Usability session 2 and fixes of the top issues | HUMAN | **open** | not started; no part record (needs IMP-611 session 1) | usability session 2 and fixes of the top issues · Manasvi, Junaid · 26 Nov 2026 |
| IMP-705 | 7 | Final evaluation baseline and cost report | DATA | done | [whole-task](parts/IMP-705-whole-task.md); #289, #291; [final-baseline.md](../../eval/reports/final-baseline.md), [cost-latency-report.md](../test-reports/cost-latency-report.md) | — |
| IMP-706 | 7 | Stage 2 readiness package (documents only) | HUMAN | done; open item | [whole-task](parts/IMP-706-whole-task.md); #289; `docs/stage2/` (five files, Proposed) | confirm E1 to E7 and the blueprint-based content · Manya · 26 Nov 2026 |
| IMP-707 | 7 | SRS, architecture, test plan, user guide and deployment guide | HUMAN | done; open item | [architecture-api](parts/IMP-707-architecture-api.md), [deployment-guide](parts/IMP-707-deployment-guide.md), [srs](parts/IMP-707-srs.md), [test-plan](parts/IMP-707-test-plan.md), [user-guide](parts/IMP-707-user-guide.md); #289; drafts listed in [IMP-707 drafts](#imp-707-drafts) | card step 6 trials (README setup and deployment guide on a clean account; user guide by a new member); 16 user-guide screenshots · Malhar (lead), Kirtan, Jeel · 26 Nov 2026 |
| IMP-708 | 7 | Natural-language trip intake with confirmation | CODE | cut (IMD-65) | not built; no route, table or screen | — |
| IMP-709 | 7 | "Why this plan" explanations for each day | CODE | cut (IMD-65) | not built; no route, table or screen | — |
| IMP-710 | 7 | Rain-aware day swapping with the Open-Meteo forecast | CODE | cut (IMD-65) | not built; no route, table or screen | — |
| IMP-711 | 7 | "Today" companion view for trip days | CODE | cut (IMD-65) | not built; no route, table or screen | — |
| IMP-712 | 7 | Budget-fit suggestions when a plan is over budget | CODE | cut (IMD-65) | not built; no route, table or screen | — |
| IMP-713 | 7 | Destination and place context cards from Wikivoyage and Wikipedia | CODE | cut (IMD-65) | not built; no route, table or screen | — |
| IMP-799 | 7 | Sprint 7 gate SG-7: release candidate | VERIFY | this gate (provisional) | [gates.md, SG-7](gates.md#sg-7-end-of-week-7-release-candidate-and-extension-freeze-imp-799) | gate confirmation and tag `v1.0-rc1` · Kirtan · 26 Nov 2026 |

## Proposed decisions for team review

Copied from their source records, not decided here. A separate decision run records the team's choice in `docs/spec/DECISION_REGISTER.md`. None of these IDs is in the register at `4fe514c`.

| ID | Proposal (summary of the source text) | Source |
| --- | --- | --- |
| PD-RUN-083-1 | The itinerary cost strip of §7.5.7 and IMP-608 step 4 is not built in the MVP under the feature freeze (IMD-201). FR-074 and FR-075 are accepted as met on the Costs page; the cost strip, MOD-F06 `CostSummary`, the IMP-608 step 4 wording and the IMP-411 cost-strip screenshot are recorded as a known gap in `deferred.md`, and the SG-6 minor finding is closed as "deferred by decision". Alternative: a planned 0-point screen part (Krrish, Manal reviewing) adds the strip from API-33 values, which needs an explicit exception to IMD-201 | [IMP-608 cost-strip-triage](parts/IMP-608-cost-strip-triage.md) |
| PD-IMP-706-1 | Schema versions of Stage 2 examples: the card names gr-1 / io-1, while the active prompt v2 (IMD-200) uses gr-2 / io-2; decide which pair a Stage 2 training example uses | [IMP-706 whole-task](parts/IMP-706-whole-task.md) |
| PD-IMP-706-2 | TC-361 evidence: no test carries TC-361; either tag an existing security check or record TC-361 as verified by code review in the SG-7 gate | [IMP-706 whole-task](parts/IMP-706-whole-task.md) |
| PD-IMP-707-1 | Record in specification §5.2 and §3.9 that `trip_places` is written by MOD-B03 (`app/trips/repository.py`), as IMD-190 decided for saved places (SRS D-04) | [IMP-707 srs](parts/IMP-707-srs.md) |
| PD-IMP-707-2 | Update specification §6.6.1 API-01 to `{status, version, environment, provider}` and its health-check note from Render to the Express Mode health check | [IMP-707 architecture-api](parts/IMP-707-architecture-api.md) |
| PD-IMP-707-3 | Update specification §13.7 CI matrix to the built `ci.yml` and `e2e.yml` (push to `main` and dispatch, no nightly, IMD-185) | [IMP-707 architecture-api](parts/IMP-707-architecture-api.md) |
| PD-IMP-707-4 | Update specification §13 opening, §13.6 and §13.7 to the built test set-up listed in `docs/test-plan.md` §9 (T-01 to T-06) | [IMP-707 test-plan](parts/IMP-707-test-plan.md) |
| GEMINI v2 availability | The final GEMINI run on trips/v1 with prompt v2 completed 23 of 45 attempts; 22 ended `provider_unavailable` (Gemini service errors, not quota), and cases `trips-v1-002`, `003` and `012` have no completed attempt. The quality figures cover the 23 completed attempts only. The team decides whether this run stands as the final GEMINI baseline or a re-run is made within the daily cap | [final-baseline.md](../../eval/reports/final-baseline.md), run [`20261120T165222Z-gemini`](../../eval/results/20261120T165222Z-gemini/run.json) |
| GEMINI retrieval not possible | The one GEMINI retrieval attempt (20 November 2026) stopped at its first call with `app.ai.errors.ProviderUnavailable: Gemini unavailable: HTTP 503` and wrote no record; it was not re-run. Only MOCK retrieval figures are claimed. The team decides whether a GEMINI retrieval run is needed before the release | [final-baseline.md](../../eval/reports/final-baseline.md), [IMP-705 record](parts/IMP-705-whole-task.md) (RUN-083d) |
| MOCK grounding rate | The MOCK retrieval grounding rate fell from 0.7571 ([`20261113T114756Z-retrieval-mock`](../../eval/reports/20261113T114756Z-retrieval-mock.md), IMP-318, commit `1b8d753`) to 0.6392 ([`20261119T182831Z-retrieval-mock`](../../eval/reports/20261119T182831Z-retrieval-mock.md), commit `f75aa94`), and citations saved from 68 to 47, with recall@6 and both place hit rates unchanged. The commit and the index differ (`embedded=189` against `embedded=227`). The cause was not investigated; the team decides whether to investigate before the release | [final-baseline.md](../../eval/reports/final-baseline.md), [IMP-705 record](parts/IMP-705-whole-task.md) (Open issues) |
| `test_metrics.py` path | The IMP-705 card's test row names `apps/api/tests/unit/evaluation/test_metrics.py` (TC-388, TC-389). That file does not exist (the folder holds `test_dataset.py`, `test_harness.py`, `test_retrieval_metrics.py`, `test_rule_based.py`, `test_run_record.py`), and no test in `apps/api/tests` is tagged TC-388 or TC-389 (checked in RUN-087 with `ls` and `grep`). Decide whether to tag existing tests or correct the card | [IMP-705 record](parts/IMP-705-whole-task.md) (Acceptance criteria, Open issues) |
| PD-IMP-799-1 | ACC-01 to ACC-18 are referenced by the specification (§13.4 and the IMP-799 card) but their scenario names and texts are not in the repository (the blueprint is not in the repository, as the IMP-706 record notes for other sections). `docs/acceptance/rc1.md` therefore lists the IDs with the specification's own cross-references. Decide the source of the scenario texts, or accept the E2E-01 to E2E-09 mapping for the staging re-run | this gate ([rc1.md](../acceptance/rc1.md)) |
| PD-IMP-799-2 | IMP-799 step 3 names `.github/workflows/live-smoke.yml`, which does not exist in the repository, and no card of the task register creates it (`gh run list --workflow live-smoke.yml`: "HTTP 404: workflow live-smoke.yml not found on the default branch"). `make live-smoke` exists (Makefile, `pytest tests/contract -m live`). Decide whether step 3 is met by an operator run of `make live-smoke` with the staging key, or a workflow is added | this gate ([gates.md, SG-7](gates.md#sg-7-end-of-week-7-release-candidate-and-extension-freeze-imp-799)) |
| PD-IMP-799-3 | IMP-799 step 7 asks for each extension switch to be listed in `FEATURES_DISABLED` for staging and production, and IMD-65 says "their switches stay off in `FEATURES_DISABLED`". No repository file lists them: staging takes the repository variable `STAGING_FEATURES_DISABLED` (`infra/aws/env.sh.example` leaves it empty) and production `PRODUCTION_FEATURES_DISABLED`, whose values are not in the repository. Decide whether the nine extension names are set in both variables before the tag, or "not built, off by decision" (as at SG-5 and SG-6, IMD-187) is accepted | this gate ([gates.md, SG-7](gates.md#sg-7-end-of-week-7-release-candidate-and-extension-freeze-imp-799)) |

## Carried-over items

The open items of this gate, with owners and due dates, are in [gates.md, SG-7](gates.md#sg-7-end-of-week-7-release-candidate-and-extension-freeze-imp-799), "Open items". The SG-6 list of unfinished cards, switches and evidence gaps is in [deferred.md](deferred.md); this gate does not change that file. Defects: [`docs/test-reports/defects.md`](../test-reports/defects.md).
