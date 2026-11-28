# RUN-105B · D2 failed city import retry

- Owner: Manal Patel; 0 points, follow-up of IMP-725.
- Status: PR candidate on `fix/live-import-retry`.
- Base: `a461804` (`origin/main`).
- Traces: local live report D2; A2 §5, §6.1, §6.2, §7.3; IMD-217; FR-142,
  TC-473, TC-475.

## Change

The existing-destination resolve path refreshes and serialises the queued row before committing.
The import is still submitted after the commit. A refresh after that commit tried to use the
closed request transaction and raised `InvalidRequestError`.

The outbound throttle now records the existing breaker's cooldown deadline. Resolve returns
429 `RATE_LIMITED` during that cooldown, with the existing `error.retry_after_s` and `Retry-After`
header, and leaves the failed row untouched. After the deadline, the same destination queues
again with 202. A2 §6.1 excludes an existing destination from the new-city caps; the regression
tests set both caps to one and still retry the existing city. No per-city cooldown is invented.

Only `_existing` and its import change in `live_service.py`; the other runtime change is in
`livedata/throttle.py`. No API field, code, setting, migration or contract changes.

## Verification

API tests use fake providers and an isolated PostgreSQL 16 / pgvector instance under `/tmp`
(loopback port 55435, test database `travel_test_r105b`). Docker was unavailable; no system
packages or shared development database were changed. Requests wrap the session in
`session.begin()`, as production does; the older API fixture omitted that context.

| Command | Result |
| --- | --- |
| `.venv/bin/pytest tests/api/test_live_import_retry.py tests/api/test_live_destinations.py -q --tb=short` (isolated `TEST_DATABASE_URL`) | `34 passed in 11.17s` |
| `.venv/bin/pytest tests/unit/livedata/test_throttle.py -q` | `67 passed in 0.33s` |
| `.venv/bin/ruff check app tests` | `All checks passed!` |
| `.venv/bin/ruff format --check app/places/live_service.py app/livedata/throttle.py tests/api/test_live_import_retry.py` | `3 files already formatted` |
| `.venv/bin/mypy app` | `Success: no issues found in 139 source files` |
| `make imports` | `Contracts: 7 kept, 0 broken.` |

- Failed → retry → completed with one destination ID: verified with fake places and guides.
- Failed → retry during the 900-second cooldown: verified as 429, including the final fractional
  second rounded up and successful retry after expiry; no import is submitted during cooldown.
- Failed refresh → retry preserves the active destination and its existing places: verified
  (IMD-217).
- Regression strength: temporarily restoring the base `live_service.py` makes the new
  failed-to-completed test fail at line 255 with the reported closed-transaction exception
  (`1 failed in 0.65s`); the fixed file was restored immediately.
- Full requested lint, types and contract checks are recorded with the D4/D6 part on the final
  branch. No live provider call was made.

## Blockers, proposed decisions and open issues

None for D2. Cooldown state is per process, matching A2's existing single-task deployment rule.
