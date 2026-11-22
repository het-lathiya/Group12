# Known defects (SG-7, IMP-799)

The IMP-799 card lists this file as "modify", but it did not exist before this gate; RUN-087 creates it. Later gates update this file instead of starting a new one.

Compiled by IMP-799 (RUN-087) on 22 November 2026 at the candidate `4fe514c`, from the gate records ([gates.md](../progress/gates.md), SG-5 and SG-6 known defects and open items), the Sprint 7 test reports in this folder and the part records. Only defects that a record shows are listed, each with its source. `gh issue list --state open --label bug` returned no issue; the open issues found by searching "defect" are the IMP-802 planning cards (#180, #182, #183), not defects.

Severity per IMD-41 (specification §13): 1 = journey blocked or data exposed; 2 = a requirement fails with no workaround; 3 = a feature fails with a workaround; 4 = cosmetic. Severity 1 and 2 block a gate.

## Severity-1 check (CHK-22)

**No open severity-1 defect is shown by any record** at `4fe514c`, and no open severity-2 defect either. This covers the local and CI scope only: no staging re-run (ACC-01 to ACC-18), device or screen-reader session (IMP-703) or usability session (IMP-611, IMP-704) has produced results yet, so those may still add defects.

## Open defects

| ID | Defect | Severity | Owner | Status | Source |
| --- | --- | --- | --- | --- | --- |
| D-01 | Gemini generations on staging end `failed` / `config_error` (SG-4 operator run of 13 November 2026); no later staging run is recorded | major, staging only (recorded at SG-5 and SG-6 as "would be 2 if staging were in scope") | Kirtan, Het | open; check in the staging window (due 26 Nov 2026) | [gates.md, SG-6 known defects](../progress/gates.md#sg-6-end-of-week-6-mvp-feature-freeze-imp-699) |
| D-02 | Under the active prompt v2 the model repeats places: in the final GEMINI v2 run, 19 of 23 completed attempts had no duplicate places (8 duplicate items in total, rejected by the output check, which shortens plans) | 3 | Manya, Nidhi | open; v3 is not activated (IMD-200) | [gates.md, SG-6](../progress/gates.md#sg-6-end-of-week-6-mvp-feature-freeze-imp-699); [final-baseline.md](../../eval/reports/final-baseline.md) (`20261120T165222Z-gemini`) |
| D-03 | No budget alert in the itinerary cost strip: the itinerary page has no cost strip (§7.5.7); the alert shows on the Costs page | 3 | Krrish, Manal | open; PD-RUN-083-1 proposes deferral by decision | [IMP-608 cost-strip-triage](../progress/parts/IMP-608-cost-strip-triage.md); [gates.md, SG-6](../progress/gates.md#sg-6-end-of-week-6-mvp-feature-freeze-imp-699) |
| D-04 | TC-385 live-stack label review and screenshots not done | 4 (evidence gap) | Manasvi | open | [gates.md, SG-6](../progress/gates.md#sg-6-end-of-week-6-mvp-feature-freeze-imp-699); [label-review.md](label-review.md) |
| D-05 | Provider spending limit is "Awaiting validation" | minor (risk; no defect observed) | Kirtan | open | [gates.md, SG-6](../progress/gates.md#sg-6-end-of-week-6-mvp-feature-freeze-imp-699); `docs/decisions/provider-spend-limit.md` |
| D-06 | CI: a pull-request edit should not cancel a code run; the concurrency fix of RUN-083 is verified by parsing only, not yet observed on GitHub | 4 | Kirtan | open | [gates.md, SG-6](../progress/gates.md#sg-6-end-of-week-6-mvp-feature-freeze-imp-699); [FIX-RUN-083 ci-concurrency](../progress/parts/FIX-RUN-083-ci-concurrency.md) |

## Reported differences not yet triaged (no severity in the record)

The IMP-707 drafts list differences between documented and built behaviour. Two of them are named in their record as possible defect cards; neither has a severity yet.

| ID | Difference | Owner of the record | Source |
| --- | --- | --- | --- |
| T-01 | `/trips/<id>/edit` exists but no screen links to it | Jeel | [IMP-707 user-guide](../progress/parts/IMP-707-user-guide.md), difference 1 |
| T-02 | The out-of-date banner's **Regenerate** opens the generate page, where the API refuses a new generation for a trip that already has a plan; **Regenerate all** on the itinerary page is the working path | Jeel | [IMP-707 user-guide](../progress/parts/IMP-707-user-guide.md), difference 2 |
| T-03 | `infra/aws/02_rds.sh`, `04_ssm.sh` and `06_services.sh` still pipe into `--cli-input-json file:///dev/stdin`, which AWS CLI v2 does not read (to be confirmed by Kirtan) | Kirtan | [IMP-707 deployment-guide](../progress/parts/IMP-707-deployment-guide.md), difference 3 |
| T-04 | `aws-setup.md` §13 (TC-434) reads `services[0].taskDefinition`, which Express Mode leaves empty | Kirtan | [IMP-707 deployment-guide](../progress/parts/IMP-707-deployment-guide.md), difference 4 |

## Fixed in Sprint 7

| Defect | Severity (from the record) | Owner | Fix | Source |
| --- | --- | --- | --- | --- |
| F-1: a correctly signed token from a foreign issuer was accepted (TC-347 not met) | 3 | Het | issuer check (IMD-204), merged in #287; regression failed before and passes after | [security-sprint7.md](security-sprint7.md), [IMP-702 auth-fixes](../progress/parts/IMP-702-auth-fixes.md) |
| App shell trip navigation overflowed at 360 and 768 px (`smoke.spec.ts`, `auth.spec.ts` TC-054/TC-056) | not recorded | Manasvi | responsive layout fix (IMD-207), merged in #287 | [IMP-701 record](../progress/parts/IMP-701-whole-task.md), [e2e-sprint7.md](e2e-sprint7.md) |
| Lock toggle accessible name did not contain its visible label (TC-383) | not recorded (axe finding, IMD-206) | Krrish | merged in #287 | IMD-206; [sprint-7.md](../progress/sprint-7.md) fix runs |
| Cost-breakdown scroll regions not keyboard-reachable | not recorded (axe finding, IMD-206) | Manasvi | merged in #287 | IMD-206; [sprint-7.md](../progress/sprint-7.md) fix runs |
| Versions page of another user's trip did not show "Trip not found" | not recorded | Jeel | merged in #287; `ownership.spec.ts` passes | [IMP-701 record](../progress/parts/IMP-701-whole-task.md) |
| Red `main` after #289: the push secret scan read a side branch | not recorded | Kirtan | scan scoped to the pushed branch (IMD-214), #290 | `docs/spec/DECISION_REGISTER.md` IMD-214 |

The spec-level failures F-E1 to F-E3 of the E2E suite were test defects, fixed in RUN-081c ([e2e-sprint7.md](e2e-sprint7.md)).

## Other findings (no severity assigned)

- CI `audit` job on `4fe514c` ([CI 45037634091](https://github.com/het-lathiya/Group12/actions/runs/45037634091)): npm audit `11 moderate severity vulnerabilities` (none critical, the step passed); the report-only pip-audit of the virtual environment's own installer printed `Found 12 known vulnerabilities in 1 package`. The API dependencies: `No known vulnerabilities found`.
- Final GEMINI v2 evaluation: 22 of 45 attempts ended `provider_unavailable` (Gemini service errors, not quota), and the GEMINI retrieval attempt stopped with HTTP 503 ([final-baseline.md](../../eval/reports/final-baseline.md)). These are provider availability findings, not product defects.
