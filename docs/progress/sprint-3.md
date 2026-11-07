# Sprint 3 index (week 3): Gemini vertical slice — gate SG-3

One line per task part of Sprint 3 (task register). Evidence lives in the part records under `docs/progress/parts/`; the gate card IMP-399 compiles this index from them. The Status column comes from the merged pull requests, not from the records' own status lines, which were written before merging.

Compiled by IMP-399 (RUN-055) on 7 November 2026 from the part records and the merged pull requests #248 to #257 on `main` at `5eaf19f`. Merged dates are UTC. Gate result: see [gates.md, SG-3](gates.md#sg-3-end-of-week-3-gemini-vertical-slice-blueprint-gate-2-imp-399).

| Task | Title | Part | Owner | Points | Run | Pull request | Merged | Status | Part record |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| IMP-301 | Gemini adapter with structured output, error mapping and recorded-response tests | gemini-adapter | Nidhi (lead) | 5 | RUN-046 | #249 | 6 November 2026 | merged | [record](parts/IMP-301-gemini-adapter.md) |
| IMP-301 | Gemini adapter with structured output, error mapping and recorded-response tests | spike-recordings | Manya | 3 | RUN-046 | #249 | 6 November 2026 | merged | [record](parts/IMP-301-spike-recordings.md) |
| IMP-302 | Provider metadata and health in readiness | whole-task | Kirtan | 2 | RUN-047 | #250 | 6 November 2026 | merged | [record](parts/IMP-302-whole-task.md) |
| IMP-303 | Normalized generation request and prompt content and size control | whole-task | Manya | 5 | RUN-046 | #249 | 6 November 2026 | merged | [record](parts/IMP-303-whole-task.md) |
| IMP-304 | Candidate retrieval, hard-constraint filters and ranking | candidate-filters | Malhar (lead) | 4 | RUN-045 | #248 | 6 November 2026 | merged | [record](parts/IMP-304-candidate-filters.md) |
| IMP-304 | Candidate retrieval, hard-constraint filters and ranking | ranking | Jeel | 4 | RUN-045 | #248 | 6 November 2026 | merged | [record](parts/IMP-304-ranking.md) |
| IMP-305 | Full generation pipeline through the active provider with job progress | pipeline | Nidhi (lead) | 4 | RUN-047 | #250 | 6 November 2026 | merged | [record](parts/IMP-305-pipeline.md) |
| IMP-305 | Full generation pipeline through the active provider with job progress | job-progress | Het | 2 | RUN-047 | #250 | 6 November 2026 | merged | [record](parts/IMP-305-job-progress.md) |
| IMP-305 | Full generation pipeline through the active provider with job progress | privacy-progress | Krrish | 2 | RUN-047.2 | #250 | 6 November 2026 | merged | [record](parts/IMP-305-privacy-progress.md) |
| IMP-306 | Output validation: schema and place IDs | output-validation | Manya (lead) | 3 | RUN-048 | #251 | 6 November 2026 | merged; D3 code change due (IMD-126) | [record](parts/IMP-306-output-validation.md) |
| IMP-306 | Output validation: schema and place IDs | injection-cases | Junaid | 2 | RUN-048 | #251 | 6 November 2026 | merged | [record](parts/IMP-306-injection-cases.md) |
| IMP-307 | OpenRouteService client with route cache and fallback | whole-task | Junaid | 3 | RUN-045 | #248 | 6 November 2026 | merged | [record](parts/IMP-307-whole-task.md) |
| IMP-308 | Deterministic recalculation of times, durations and trip cost estimate | budget-costs | Manal (lead) | 5 | RUN-049.2 | #252 | 6 November 2026 | merged | [record](parts/IMP-308-budget-costs.md) |
| IMP-308 | Deterministic recalculation of times, durations and trip cost estimate | schedule | Het | 3 | RUN-049 | #252 | 6 November 2026 | merged | [record](parts/IMP-308-schedule.md) |
| IMP-309 | Day-wise itinerary view with labels | day-view | Manasvi (lead) | 4 | RUN-050 | #253 | 7 November 2026 | merged | [record](parts/IMP-309-day-view.md) |
| IMP-309 | Day-wise itinerary view with labels | read-fields | Het | 1 | RUN-050 | #253 | 7 November 2026 | merged | [record](parts/IMP-309-read-fields.md) |
| IMP-310 | Evaluation dataset version 1 (15 trips) | whole-task | Junaid | 3 | RUN-045 | #248 | 6 November 2026 | merged | [record](parts/IMP-310-whole-task.md) |
| IMP-312 | Embedding operation on ModelProvider: Gemini and deterministic MOCK embeddings | whole-task | Nidhi | 3 | RUN-047 | #250 | 6 November 2026 | merged | [record](parts/IMP-312-whole-task.md) |
| IMP-313 | Corpus ingestion and indexing: place and guide documents, chunking, embedding, `make rag-index` | whole-task | Manal | 3 | RUN-048 | #251 | 6 November 2026 | merged; staging index open ([gates.md](gates.md#open-items-1)) | [record](parts/IMP-313-whole-task.md) |
| IMP-314 | Destination guides for demo destination 1 | guides | Krrish (lead) | 2 | RUN-050 | #253 | 7 November 2026 | merged | [record](parts/IMP-314-guides.md) |
| IMP-314 | Destination guides for demo destination 1 | review | Malhar | 1 | RUN-050 | #253 | 7 November 2026 | merged | [record](parts/IMP-314-review.md) |
| IMP-315 | Hybrid retrieval: semantic place scores and guide passages with lexical fallback | whole-task | Jeel | 3 | RUN-049 | #252 | 6 November 2026 | merged | [record](parts/IMP-315-whole-task.md) |
| IMP-316 | Grounded generation: passages in the request, validated citations, saved sources | grounding | Manya (lead) | 3 | RUN-051 | #254 | 7 November 2026 | merged | [record](parts/IMP-316-grounding.md) |
| IMP-316 | Grounded generation: passages in the request, validated citations, saved sources | saved-sources | Het | 1 | RUN-051 | #254 | 7 November 2026 | merged | [record](parts/IMP-316-saved-sources.md) |
| IMP-317 | Sources on itinerary items | whole-task | Manasvi | 2 | RUN-052 | #255 | 7 November 2026 | merged; D12 code change due (IMD-135) | [record](parts/IMP-317-whole-task.md) |

**Points.** Sprint 3 plans 73 points over 25 parts on 16 cards, plus the gate card IMP-399 (2 points, this run). IMP-311 is listed under Sprint 2, where it merged. All 25 parts are merged; none is open or blocked, and IMP-302 and IMP-310 did not slip. Nothing is shown on AWS staging yet; those criteria move to SG-4 (see the gate's open items).

## Fix and preparation runs (no points)

| Pull request | Title | Run | Merged | Status | Record |
| --- | --- | --- | --- | --- | --- |
| #256 | IMP-301 · wire-schema fix | RUN-053, RUN-053b | 7 November 2026 | merged | [record](parts/IMP-301-wire-schema.md) |
| #257 | SG-3 prep · staging Gemini settings and account facts | RUN-054 | 7 November 2026 | merged | no part record; pull request body |
