# IMP-404 · reference-rules part

- Run id: RUN-056 (grouped, IMD-121, with IMP-404 schedule-rules and IMP-413)
- Owner: Junaid (Junaid-Kureshi)
- Status: PR open
- Base commit: f7f3c51
- Branch: feat/IMP-404-413-validator-eval
- Reviewer: Kirtan (kirtan-S111)
- Traces to: US-064; FR-055; NFR-030
- Card steps built: 5 and the reference half of 6

## Changed files

- `apps/api/app/validation/rules.py`: rules `must_visit_missing`, `unknown_place`, `outside_trip_dates`, added to `RULES` after the schedule rules in the order of the §8.12 table.
- `apps/api/app/validation/README.md`: sections for the three rules with their boundary cases.
- `apps/api/tests/unit/validation/test_rules_references.py` (created).
- `apps/api/tests/unit/validation/test_rules_schedule.py`: its context now holds the test place as active, so the new UNKNOWN_PLACE rule does not fire on the schedule cases.

## Commands and results

| Command | Result |
| --- | --- |
| `make test-unit ARGS='-k rules_references'` | `9 passed, 856 deselected, 1 warning` |
| `make test-unit` | `865 passed, 1 warning` |
| `make test-contract` | `87 passed, 2 deselected, 1 warning` |
| `make test-web` | `Tests  119 passed (119)` |
| `make lint` | exit 0 (`All matched files use Prettier code style!`) |
| `make typecheck` | `Success: no issues found in 107 source files` |
| `make imports` | `Contracts: 6 kept, 0 broken.` |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` |
| `cd apps/api && python -m pytest tests/unit/validation --cov=app/validation --cov-report=term` | not run to a result: `error: unrecognized arguments: --cov=app/validation --cov-report=term` (pytest-cov is not installed; adding it is RUN-059) |
| `make test-api`, `make test-authz` | not run to a result: no PostgreSQL or Docker on this machine (connection refused on port 5432); this part touches no database code. Evidence comes from the CI `api` job |

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-055 AC1: a missing must-visit place gives a finding naming it, with `place_id` set and no item (TC-186, IMD-42) | verified | `test_tc_186_missing_must_visit_names_the_place_with_place_id_and_no_item` |
| FR-055 AC2: an item outside the trip dates is flagged (TC-187 and TC-305) | verified | `test_tc_305_items_on_start_and_end_dates_pass_and_the_day_after_is_outside_trip_dates` |
| Unknown place: inactive, or outside the shortlist in generation (TC-187) | verified | `test_tc_187_inactive_place_is_unknown`, `test_active_place_outside_the_shortlist_is_unknown_in_generation` |
| Items on the trip start and end dates are accepted (TC-305) | verified | as above, and `test_one_day_trip_accepts_day_1_only` |
| Statement coverage of app/validation >= 85 percent (TC-334) | not verified | pytest-cov is not installed; the coverage command is in not_run |

## Blockers

None for this part.

## Proposed decisions

- **PD-IMP-404-4: rule order.** The card says the order is fixed but names none; `RULES` follows the §8.12 table (OVERLAP, TRANSFER_TOO_SHORT, MUST_VISIT_MISSING, UNKNOWN_PLACE, OUTSIDE_TRIP_DATES).
- **PD-IMP-404-5: day numbers a finding cannot hold.** `PlanFinding.day_number` accepts 1 to 14. An item on day 0 or day 15 or later gets `OUTSIDE_TRIP_DATES` with `day_number` null; the day stays in `item_ref` and the message.
- **PD-IMP-404-6: TC-187.** The TC table has no row for TC-187 alone; it is read as "an unknown place reference is flagged", tested with an inactive place.

## Open issues

- TC-334 waits for pytest-cov in CI (RUN-059).
