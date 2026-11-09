# IMP-404 · schedule-rules part

- Run id: RUN-056 (grouped, IMD-121, with IMP-404 reference-rules and IMP-413)
- Owner: Manal (manalPatel2557)
- Status: PR open
- Base commit: f7f3c51
- Branch: feat/IMP-404-413-validator-eval
- Reviewer: Kirtan (kirtan-S111)
- Traces to: US-061; FR-050, FR-051; NFR-030
- Card steps built: 1, 2, 3, 4 and the schedule half of 6

## Changed files

- `apps/api/app/validation/rules.py` (created): `Finding` (the existing `PlanFinding` of `app/schemas/ai.py`, which already has every field of step 1), `CATALOGUE` with the 13 codes and severities of §8.12, `ValidationContext`, the `PlanDay` and `PlanItem` protocols, the rules `overlap` and `transfer_too_short`, and `RULES`, their fixed order.
- `apps/api/app/validation/validator.py` (created): `validate(plan, ctx) -> list[Finding]`.
- `apps/api/app/validation/README.md` (created): OVERLAP and TRANSFER_TOO_SHORT with their boundary cases.
- `apps/api/.importlinter`: `app.validation.rules` and `app.validation.validator` added to the Pure domain contract, as §4.4 lists them.
- `apps/api/tests/unit/validation/test_rules_schedule.py` (created).
- `apps/api/app/schemas/ai.py`: not changed; `PlanFinding` and `FindingCode` were already there.

## Commands and results

| Command | Result |
| --- | --- |
| `make test-unit ARGS='-k rules_schedule'` | `12 passed, 844 deselected, 1 warning` |
| `make test-unit` | `856 passed, 1 warning` |
| `make test-contract` | `87 passed, 2 deselected, 1 warning` |
| `make test-web` | `Tests  119 passed (119)` |
| `make lint` | exit 0 (`All matched files use Prettier code style!`) |
| `make typecheck` | `Success: no issues found in 107 source files` |
| `make imports` | `Contracts: 6 kept, 0 broken.` |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` |
| `make test-api`, `make test-authz` | not run to a result: no PostgreSQL or Docker on this machine (`connection to server at "127.0.0.1", port 5432 failed: Connection refused`); this part touches no database code. Evidence comes from the CI `api` job |

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-050 AC1: overlap by 15 minutes gives one OVERLAP naming both items (TC-176) | verified | `test_tc_176_overlap_by_15_minutes_names_both_items` |
| FR-050 AC2: back-to-back items give no OVERLAP (TC-177) | verified | `test_tc_177_back_to_back_items_give_no_overlap` |
| Different days are never compared (TC-306) | verified | `test_tc_306_same_clock_time_on_different_days_is_never_compared` |
| FR-051 AC1: 10-minute gap, 30-minute transfer gives TRANSFER_TOO_SHORT with the shortfall (TC-178) | verified | `test_tc_178_10_minute_gap_with_30_minute_transfer_reports_the_shortfall` (25 min short) |
| FR-051 AC2: a fallback estimate is labelled an estimate (TC-179) | verified | `test_tc_179_fallback_estimate_is_labelled_and_takes_the_15_minute_buffer` |
| Statement coverage of app/validation >= 85 percent (TC-334) | not verified | Measured in the reference-rules part |

## Blockers

None for this part.

## Proposed decisions

- **PD-IMP-404-1: travel comes from the plan items.** Step 2 says ctx carries travel times. The rules read `travel_from_prev_min` and `travel_source` from the recalculated items, which step 9 stores (IMP-308), so validation uses exactly the saved travel and never routes. `ValidationContext` has no separate travel table.
- **PD-IMP-404-2: OVERLAP compares neighbours by position.** §9.3.4 says "consecutive items"; an item is compared only with the one before it in position order.
- **PD-IMP-404-3: OUTSIDE_HOURS in the catalogue is `error`.** §8.12 gives "error if hours curated, warning if estimate"; the catalogue holds `error` and the IMP-309 rule passes the severity for estimated hours.

## Open issues

- Pace limits are in `ValidationContext` for IMP-309's DAY_TOO_LONG; no rule here reads them.
- The validator is not yet called by the pipeline or the edit path (IMP-405, IMP-407).
