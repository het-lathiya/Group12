# Sprint 4 index (week 4): Core itinerary reliability — gate SG-4

One line per task part of Sprint 4 (task register). Evidence lives in the part records under `docs/progress/parts/`; the gate card IMP-499 compiles this index from them. The Status column comes from the merged pull requests, not from the records' own status lines, which were written before merging.

Compiled by IMP-499 (RUN-064) on 14 November 2026 from the part records and the merged pull requests #259 to #273 on `main` at `ec6973a`. Merged dates are UTC. Gate result: see [gates.md, SG-4](gates.md#sg-4-end-of-week-4-core-reliability-blueprint-gate-3-imp-499).

| Task | Title | Part | Owner | Points | Run | Pull request | Merged | Status | Acceptance | Part record |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| IMP-401 | Retries with backoff and circuit breaker in the Gemini adapter | whole-task | Nidhi (lead) | 3 | RUN-057 | #261 | 9 November 2026 | merged | verified, except the repair-call wiring (deferred to IMP-502) | [record](parts/IMP-401-whole-task.md) |
| IMP-402 | Rule-based fallback planner and saved sample itineraries | fallback-planner | Malhar (lead) | 3 | RUN-057 | #261 | 9 November 2026 | merged | verified (API cases in the CI `api` job) | [record](parts/IMP-402-fallback-planner.md) |
| IMP-402 | Rule-based fallback planner and saved sample itineraries | sample-itineraries | Jeel | 2 | RUN-057s | #270 | 12 November 2026 | merged; **Ahmedabad samples open** | verified for Sampleton; FR-036 AC3 for Ahmedabad not verified (waiting for two trip inputs) | [record](parts/IMP-402-sample-itineraries.md) |
| IMP-403 | Provider failure, timeout and quota handling end to end with fallback notice | failure-outcomes | Nidhi (lead) | 2 | RUN-060 | #267 | 12 November 2026 | merged | verified (TC-148, TC-149, TC-150, TC-307, TC-308) | [record](parts/IMP-403-failure-outcomes.md) |
| IMP-403 | Provider failure, timeout and quota handling end to end with fallback notice | fallback-notice | Krrish | 1 | RUN-060 | #267 | 12 November 2026 | merged; wording fixed in RUN-059 (IMD-154) | verified by component tests; screenshots not verified | [record](parts/IMP-403-fallback-notice.md) |
| IMP-404 | Validator: overlaps, travel gaps, missing constraints and invalid references | schedule-rules | Manal (lead) | 4 | RUN-056 | #259 | 9 November 2026 | merged | verified; TC-334 coverage not verified | [record](parts/IMP-404-schedule-rules.md) |
| IMP-404 | Validator: overlaps, travel gaps, missing constraints and invalid references | reference-rules | Junaid | 3 | RUN-056 | #259 | 9 November 2026 | merged | verified; TC-334 coverage not verified (report-only job added in RUN-059) | [record](parts/IMP-404-reference-rules.md) |
| IMP-405 | Structured warnings with suggested fixes, persisted with the plan, warnings panel | persist-warnings | Jeel | 2 | RUN-060 | #267 | 12 November 2026 | merged | verified (TC-193 at service level; API-24 `version_id` is IMP-610) | [record](parts/IMP-405-persist-warnings.md) |
| IMP-405 | Structured warnings with suggested fixes, persisted with the plan, warnings panel | warnings-panel | Manasvi (lead) | 2 | RUN-060 | #267 | 12 November 2026 | merged | verified; 1280/375 px layout not checked visually | [record](parts/IMP-405-warnings-panel.md) |
| IMP-406 | Preserve explicit constraints and must-visit places; label AI-written text | must-visit-constraints | Manya (lead) | 3 | RUN-057 | #261 | 9 November 2026 | merged | verified (API cases in CI); TC-141 shown with the rule-based plan until IMP-502 | [record](parts/IMP-406-must-visit-constraints.md) |
| IMP-406 | Preserve explicit constraints and must-visit places; label AI-written text | ai-text-labels | Krrish | 1 | RUN-057 | #261 | 9 November 2026 | merged | verified by component tests; screenshot evidence not verified | [record](parts/IMP-406-ai-text-labels.md) |
| IMP-407 | Edit transaction core: recalculate and revalidate every edit atomically with plan revision | whole-task | Het (lead) | 5 | RUN-060 | #267 | 12 November 2026 | merged | verified (TC-206, TC-207, TC-312; TC-330 recorded, p95 79 ms locally) | [record](parts/IMP-407-whole-task.md) |
| IMP-408 | Remove an activity and change start time or duration | remove-retime-ops | Het (lead) | 2 | RUN-062 | #268 | 12 November 2026 | merged | verified (TC-200, TC-201, TC-204, TC-205) | [record](parts/IMP-408-remove-retime-ops.md) |
| IMP-408 | Remove an activity and change start time or duration | item-editor | Manasvi | 2 | RUN-062, RUN-063b | #268, #272 | 12 and 13 November 2026 | merged; removal toast and focus fixed in RUN-063b | verified; 44 px targets and screenshots not verified; focus fallback to the previous card or heading has no test | [record](parts/IMP-408-item-editor.md) |
| IMP-409 | Reorder by drag and by keyboard | move-op | Het | 2 | RUN-062 | #268 | 12 November 2026 | merged | verified (TC-199) | [record](parts/IMP-409-move-op.md) |
| IMP-409 | Reorder by drag and by keyboard | move-controls | Manasvi (lead) | 3 | RUN-062 | #268 | 12 November 2026 | merged | verified (TC-198); pointer drag gesture, 44 px targets and screenshots not verified | [record](parts/IMP-409-move-controls.md) |
| IMP-410 | Drafts and reopening the latest saved itinerary | draft-latest-api | Manal (lead) | 2 | RUN-058 | #260 | 9 November 2026 | merged | API cases in the CI `api` job (not run locally by the part) | [record](parts/IMP-410-draft-latest-api.md) |
| IMP-410 | Drafts and reopening the latest saved itinerary | draft-resume-ui | Krrish | 2 | RUN-058, RUN-067 | #260, #273 | 9 and 13 November 2026 | merged; dashboard "New trip" fixed in RUN-067 | verified; draft check on staging by the operator (13 November 2026) | [record](parts/IMP-410-draft-resume-ui.md) |
| IMP-411 | Transport allowance, stay budget and price source labels | budget-labels-api | Manal (lead) | 2 | RUN-058 | #260 | 9 November 2026 | merged | verified (unit); API cases in the CI `api` job | [record](parts/IMP-411-budget-labels-api.md) |
| IMP-411 | Transport allowance, stay budget and price source labels | budget-form-badges | Krrish | 2 | RUN-058 | #260 | 9 November 2026 | merged | verified | [record](parts/IMP-411-budget-form-badges.md) |
| IMP-412 | Loading, empty and error states on every MVP screen | whole-task | Manasvi (lead) | 3 | RUN-058 | #260 | 9 November 2026 | merged | verified, except TC-384 (error-catalogue checklist, Krrish) | [record](parts/IMP-412-whole-task.md) |
| IMP-413 | Evaluation harness (command line) | whole-task | Manya (lead) | 3 | RUN-056 | #259 | 9 November 2026 | merged | verified; numbered blueprint metrics replaced by the three spec counts (IMD-144) | [record](parts/IMP-413-whole-task.md) |
| IMP-318 | Retrieval evaluation: recall, hit rate, citation validity and grounding rate | whole-task | Junaid (lead) | 2 | RUN-061 | #271 | 13 November 2026 | merged | verified (TC-458, two identical MOCK runs); live-embedding numbers need staging | [record](parts/IMP-318-whole-task.md) |
| IMP-414 | End-to-end journey test on staging | journey-staging | Krrish (lead) | 3 | RUN-063, RUN-063b | #272 | 13 November 2026 | merged | TC-369 verified on the local stack in CI ([E2E 43431854989](https://github.com/het-lathiya/Group12/actions/runs/43431854989)); TC-370 on staging not verifiable yet | [record](parts/IMP-414-journey-staging.md) |
| IMP-414 | End-to-end journey test on staging | journey-fixtures-report | Junaid | 2 | RUN-063 | #272 | 13 November 2026 | merged | verified on the local stack in CI; staging reset not verifiable yet (IMD-163) | [record](parts/IMP-414-journey-fixtures-report.md) |

**Points.** Sprint 4 plans 61 points over 25 parts on 15 cards (IMP-401 to IMP-414 and IMP-318), plus the gate card IMP-499 (2 points, this run). All 25 parts are merged. None is blocked or cut. One story is half-finished: the Ahmedabad half of FR-036 AC3 in IMP-402 sample-itineraries. Staging evidence (TC-370 and the card's staging steps) waits for the staging window of Wednesday 18 November 2026 (IMD-137). The cut-list checkpoint is in [cut-list-checkpoint.md](../decisions/cut-list-checkpoint.md).

## Fix and decision runs (no points)

| Pull request | Title | Run | Owners | Merged | Status | Record |
| --- | --- | --- | --- | --- | --- | --- |
| #269 | RUN-059 · decision record IMD-137..155 and SG-3 fixes | RUN-059 | Nidhi (decision-record), Kirtan (devops-bundle), Het (token-leeway), Malhar (destination-404), Krrish (fallback-wording) | 12 November 2026 | merged | [decision-record](parts/RUN-059-decision-record.md), [devops-bundle](parts/RUN-059-devops-bundle.md), [token-leeway](parts/RUN-059-token-leeway.md), [destination-404](parts/RUN-059-destination-404.md), [fallback-wording](parts/RUN-059-fallback-wording.md) |
| #272 | IMP-408 removal toast and focus fix, inside the IMP-414 pull request | RUN-063b | Manasvi (fix), Krrish (journey hard check) | 13 November 2026 | merged | "Fix RUN-063b" sections of [IMP-408 item-editor](parts/IMP-408-item-editor.md) and [IMP-414 journey-staging](parts/IMP-414-journey-staging.md) |
| #273 | IMP-410 · dashboard New trip fix | RUN-067 | Krrish | 13 November 2026 | merged | "Fix RUN-067" section of [IMP-410 draft-resume-ui](parts/IMP-410-draft-resume-ui.md) |

## Open issues from the part records

| Issue | Card | Owner |
| --- | --- | --- |
| Ahmedabad saved samples (FR-036 AC3), waiting for two trip inputs | IMP-402 | Jeel |
| TC-384 error-catalogue checklist | IMP-412 | Krrish |
| Screenshots on the local stack: fallback and paused-AI notices (#267), AI label beside a source-labelled price (#261), item editor and move controls (#268), WarningsPanel at 1280 and 375 px (#267), dashboard (#273); 44 px targets at 375 px | IMP-403, IMP-405, IMP-406, IMP-408, IMP-409, IMP-410 | Manasvi, Krrish |
| Focus fallback to the previous card or the day heading after a removal has no test | IMP-408 | Krrish (IMP-513) |
| The itinerary page has no totals display; edits update the cached totals only | IMP-408 | note only, IMP-507 |
| Repair call through the retry allowance; TC-141 in mode ai | IMP-401, IMP-406 | Nidhi, Manya (IMP-502) |
| API-12 is a 501 stub; staging reset uses a fresh account (IMD-163) | IMP-414 | Kirtan, Manal (IMP-602) |
| Local `make test-web` flakes under load; CI is the stability signal | RUN-059 fallback-wording | operator (idle-machine run ×10) |
| `infra/aws/02_rds.sh`, `04_ssm.sh`, `06_services.sh` still use `file:///dev/stdin` | RUN-059 devops-bundle | Kirtan |
| IMD-159 code change: domain wording for a malformed `Money.currency` | RUN-059 devops-bundle | Kirtan |
