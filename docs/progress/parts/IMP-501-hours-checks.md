# IMP-501 · hours-checks

- Run id: RUN-069
- Owner: Mohammad Junaid Kureshi (Junaid-Kureshi), 3 points
- Status: implemented; API evidence awaiting CI
- Base commit: 4c6c693
- Steps: 1–3, hours/day-length half of 6–7.

## Files changed

- apps/api/app/validation/rules.py: six-row hours decision list, local wall times, overnight windows, estimated-hour severity; DAY_TOO_LONG reads the common pace accessor.
- apps/api/app/generation/pipeline.py: loads authoritative hours and timezone for step 9.
- apps/api/tests/unit/validation/test_hours.py; test_day_length_budget.py; apps/api/tests/api/test_itinerary.py; this record.
- Minimal extra files: apps/api/app/itinerary/service.py supplies stored hours and day dates to edits/API-32; apps/api/tests/fixtures/pipeline.py supplies the corresponding database-free stand-in; apps/api/tests/unit/validation/test_rules_references.py expands the exact rule-registration assertion. These are required to register and feed the same rules on all three paths.
- validator.py already runs rules.RULES, so no separate registration copy is needed.

## Commands and results

- `make test-unit ARGS='-k hours'`: `29 passed, 1097 deselected, 1 warning in 1.50s`.
- First pace/full runs found an incorrect iterable assumption for PaceLimits; fixed before commit; no test weakened.
- `make test-unit`: `1126 passed, 1 warning in 19.23s`.
- `make imports`: `Contracts: 6 kept, 0 broken.`
- Scoped `ruff check`: `All checks passed!`.
- Not run: `make test-api ARGS='-k validate'`, PostgreSQL unavailable (make db-up failed; no packages installed).

## Acceptance

- Verified FR-052 / TC-180/181: closed, unverified, missing weekday, inside/outside and split intervals; unavailable hours never claim closure.
- Verified TC-301: same-day and previous-weekday overnight visits, previous interval precedes a closed row.
- Verified TC-302: local Monday 00:30 in Asia/Kolkata stays Monday despite UTC being Sunday.
- Verified FR-053 / TC-182/183/303: each pace exactly at and above active minutes and item count; transfers count; messages contain actual and maximum figures.
- API-32 persistence test written, not verified without PostgreSQL. Budget criteria are budget-conflict.

## Proposed decisions / open issues

- No contract or migration change; no new proposed decisions.
- Database verification remains open; pure contexts can omit hours when testing unrelated rules, production always loads them.
