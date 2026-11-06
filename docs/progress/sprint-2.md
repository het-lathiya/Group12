# Sprint 2 index (week 2): Walking skeleton — gate SG-2

One line per task part of Sprint 2 (task register). Evidence lives in the part records under `docs/progress/parts/`; the gate card IMP-299 compiles this index from them. The Status column comes from the merged pull requests, not from the records' own status lines, which were written before merging.

Compiled by IMP-299 (RUN-044) on 6 November 2026 from the part records and the merged pull requests on `main` at `0b361fc`. Merged dates are UTC. Gate result: see [gates.md, SG-2](gates.md#sg-2-end-of-week-2-walking-skeleton-blueprint-gate-1-imp-299).

| Task | Title | Part | Owner | Points | Run | Pull request | Merged | Status | Part record |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| IMP-201 | Readiness endpoint and structured request logging with request IDs | whole-task | Kirtan | 3 | RUN-029 | #231 | 3 November 2026 | merged | [record](parts/IMP-201-whole-task.md) |
| IMP-202 | Generation record repository and lifecycle helpers (ai_generations) | whole-task | Jeel | 2 | RUN-022 | #209 | 2 November 2026 | merged | [record](parts/IMP-202-whole-task.md) |
| IMP-203 | Trips API: create, list and read a trip with validation | whole-task | Manal | 3 | RUN-018 | #204 | 2 November 2026 | merged | [record](parts/IMP-203-whole-task.md) |
| IMP-204 | Preferences and must-visit places API with mapping to filters and ranking weights | whole-task | Manal | 4 | RUN-020 | #207 | 2 November 2026 | merged | [record](parts/IMP-204-whole-task.md) |
| IMP-205 | Provenance-preserving place import with quality gate, categories and destinations API | import-quality-gate | Malhar (lead) | 4 | RUN-019b | #205 | 2 November 2026 | merged | [record](parts/IMP-205-import-quality-gate.md) |
| IMP-205 | Provenance-preserving place import with quality gate, categories and destinations API | places-api-search | Jeel | 3 | RUN-019b | #205, #206 | 2 November 2026 | merged | [record](parts/IMP-205-places-api-search.md) |
| IMP-206 | Curate and load demo destination 1 | lead-curation | Jeel (lead) | 4 | RUN-040 | #242 | 6 November 2026 | merged; staging load open ([gates.md](gates.md#open-items)) | [record](parts/IMP-206-lead-curation.md) |
| IMP-206 | Curate and load demo destination 1 | hours-prices | Malhar | 4 | RUN-040 | #242 | 6 November 2026 | merged | [record](parts/IMP-206-hours-prices.md) |
| IMP-207 | Mock provider with scenario-based failure injection | whole-task | Manya | 2 | RUN-021 | #208 | 2 November 2026 | merged | [record](parts/IMP-207-whole-task.md) |
| IMP-208 | Provider factory and configuration-based selection | whole-task | Nidhi | 2 | RUN-023 | #210 | 2 November 2026 | merged | [record](parts/IMP-208-whole-task.md) |
| IMP-209 | Distance-based travel-time estimate (pure) | whole-task | Junaid | 2 | RUN-024 | #211 | 2 November 2026 | merged | [record](parts/IMP-209-whole-task.md) |
| IMP-210 | Walking-skeleton generation job: start and poll with MOCK, save a validated plan | whole-task | Het | 1 | RUN-030 | #232 | 3 November 2026 | merged | [record](parts/IMP-210-whole-task.md) |
| IMP-211 | Itinerary read endpoint and latest-itinerary lookup (minimal) | whole-task | Het | 1 | RUN-034 | #236 | 3 November 2026 | merged | [record](parts/IMP-211-whole-task.md) |
| IMP-212 | Trip wizard and preference form | whole-task | Manasvi | 3 | RUN-033 | #235 | 3 November 2026 | merged | [record](parts/IMP-212-whole-task.md) |
| IMP-213 | Generate page with progress and read-only itinerary view (skeleton) | whole-task | Krrish | 1 | RUN-036b | #239 | 5 November 2026 | merged | [record](parts/IMP-213-whole-task.md) |
| IMP-214 | OpenAPI contract v1 export, generated web client and contract check | whole-task | Kirtan | 3 | RUN-026 | #227 | 2 November 2026 | merged; tag `contract-v1` open ([gates.md](gates.md#open-items)) | [record](parts/IMP-214-whole-task.md) |
| IMP-215 | Two-user authorization suite for every owned route | whole-task | Junaid | 3 | RUN-031 | #233 | 3 November 2026 | merged | [record](parts/IMP-215-whole-task.md) |
| IMP-216 | Walking-skeleton end-to-end test and staging deployment | whole-task | Kirtan | 1 | RUN-043 | #246 | 6 November 2026 | merged; staging walk-through open ([gates.md](gates.md#open-items)) | [record](parts/IMP-216-whole-task.md) |
| IMP-217 | AWS staging foundation: RDS PostgreSQL, ECR, SSM, ECS Express services, OIDC deploy role and budget | whole-task | Kirtan | 4 | RUN-041 | #243 | 6 November 2026 | merged; no AWS resource exists yet; live steps open ([gates.md](gates.md#open-items)) | [record](parts/IMP-217-whole-task.md) |
| IMP-218 | Web container and AWS deploy workflows with the release task | deploy-workflows | Junaid (lead) | 2 | RUN-042 | #245 | 6 November 2026 | merged; TC-437, TC-438, staging smoke and CORS open ([gates.md](gates.md#open-items)) | [record](parts/IMP-218-deploy-workflows.md) |
| IMP-218 | Web container and AWS deploy workflows with the release task | web-image | Manasvi | 2 | RUN-042 | #245 | 6 November 2026 | merged; deployment on AWS open ([gates.md](gates.md#open-items)) | [record](parts/IMP-218-web-image.md) |
| IMP-219 | Supabase Auth with an AWS database: auth stub bootstrap and user row mirroring | whole-task | Het | 2 | RUN-028 | #229 | 3 November 2026 | merged | [record](parts/IMP-219-whole-task.md) |
| IMP-311 | RAG store: pgvector, corpus and chunk tables, item citations and retrieval record (migration 0007) | whole-task | Malhar | 3 | RUN-027 | #228 | 2 November 2026 | merged | [record](parts/IMP-311-whole-task.md) |

**Points.** Sprint 2 plans 59 points over 23 parts on 20 cards, plus the gate card IMP-299 (0 points, this run). All 23 parts are merged; none is open or blocked. Five parts have a hosted half that cannot be shown until the AWS set-up runs, listed under the gate's open items. Two cards took a fix after their first merge (below).

## Fix and decision runs (no points)

| Pull request | Title | Merged | Status |
| --- | --- | --- | --- |
| #234 | IMD-117 · screen drafts as design references | 3 November 2026 | merged |
| #237 | IMD-118 · UI design guide and theme tokens | 4 November 2026 | merged |
| #238 | IMD-119 · in-progress conflict names the active generation | 4 November 2026 | merged |
| #240 | IMD-120 · desk-checked seed data and plan for destination 1 | 5 November 2026 | merged |
| #241 | IMP-213 · fix flaky timeout test | 5 November 2026 | merged |
| #244 | IMP-210 · fix job-timeout race | 6 November 2026 | merged |
