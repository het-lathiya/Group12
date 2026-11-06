# IMP-307 · whole-task part

- Run id: RUN-045 (grouped, IMD-121, with IMP-304, IMP-307 and IMP-310)
- Owner: Junaid (Junaid-Kureshi)
- Status: PR_OPEN
- Base commit: 4f20bfc
- Branch: feat/IMP-304-307-310-wave1
- Reviewer: Manal (manalPatel2557)
- Traces to: US-087; FR-078; NFR-010, NFR-038; TC-234, TC-235, TC-341, and the TC-236, TC-237 path
- Card steps built: 1 to 5

## Changed files

- `apps/api/app/routing/client.py` (created): `OrsClient.route(origin, target, mode)`.
  - It posts to `/v2/directions/{profile}/json`, with the key in the `Authorization` header and one attempt.
  - It returns minutes (rounded up) and metres.
  - A timeout, a connection error, a 4xx or 5xx, an answer without a route or a missing key raises `RoutingUnavailable`.
  - It holds the in-process daily counter and the WARNING at 80 percent. `get_client()` gives one client per process.
- `apps/api/app/routing/cache.py` (created): `RouteCacheRepository.get` (`expires_at > now`) and `upsert`, `ROUTE_TTL` 30 days (Provisional), `FALLBACK_TTL` 1 day.
- `apps/api/app/routing/service.py`: `RoutingService.travel` (cache, then ORS then cache, then the IMP-209 estimate cached for 1 day). `travel_time` keeps its signature and is the estimate step.
- `apps/api/app/core/config.py`, `.env.example`: `ORS_DAILY_ALLOWANCE` (default 2000, Unverified until IMP-113).
- `apps/api/.importlinter`: the `routing-isolation` contract (§4.4).
- `apps/api/tests/fixtures/provider_recordings/ors/` (created): format fixtures with a README. They are not live recordings; replace them once the ORS key exists (IMP-113).
- `apps/api/tests/unit/routing/test_routing_service.py` (created), `apps/api/tests/api/test_route_cache.py` (created, the real table).

## Log lines from the tests

From `tests/unit/routing/test_routing_service.py` with `log_cli` at INFO. These come from the tests, not the local stack:

```text
INFO app.routing.service route from routing service mode=walking
INFO app.routing.service route cache hit mode=walking travel_source=routing_api
INFO app.routing.service route fallback mode=walking reason=no key
INFO app.routing.service route cache hit mode=walking travel_source=fallback_estimate
WARNING app.routing.client routing near daily quota calls=4 allowance=5
```

## Commands and results

| Command | Result line |
| --- | --- |
| `make test-unit ARGS='-k routing'` | `41 passed, 426 deselected, 1 warning in 0.90s` |
| `make test-api ARGS='-k route_cache'` | `4 passed, 246 deselected, 1 warning in 1.20s` |
| `make lint` | `All checks passed!` (ruff); `All matched files use Prettier code style!` |
| `make typecheck` | `Success: no issues found in 89 source files` |
| `make imports` | `Contracts: 5 kept, 0 broken.` |
| `make test` (via `make check`, `TEST_DATABASE_URL` = the §4.7 default on `pgvector/pgvector:pg16`) | unit `467 passed, 1 warning`; contract `35 passed, 1 warning`; api `250 passed, 1 warning`; authz `28 passed`; web `Tests  80 passed (80)` |
| `make check` | exit 0 (`openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date`) |

Not run: `make e2e` (no journey changes). The local-stack log was not taken; no ORS key exists, and no live call was made.

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| A route is cached for reuse (FR-078 AC1, TC-234) | verified | `test_tc_234_a_route_is_estimated_from_ors_and_cached`, `test_a_stored_route_is_read_back_and_expires` |
| The second request for a pair makes no HTTP call (FR-078 AC2, TC-235) | verified | `test_tc_235_a_cached_pair_makes_no_http_call` |
| With ORS failing or no key the estimate is returned with `fallback_estimate` (TC-236, TC-237 path) | verified | `test_ors_failure_falls_back_to_the_labelled_estimate` (seven failure shapes), `test_no_key_falls_back_without_any_http_call` |
| The near-quota warning is logged at the threshold (TC-341, review) | verified by test; review pending | `test_tc_341_the_near_quota_warning_is_logged_once_at_80_percent` |
| Log excerpt of cache hit and fallback on the local stack | not verified | The test log lines above are given instead |
| Behaviour against the real ORS service | not verified | No key; the fixtures follow the documented format only |

## Blockers

None.

## Proposed decisions

- **PD-IMP-307-1: new environment variable.** `ORS_DAILY_ALLOWANCE` is not in §4.5. The run asked for the allowance as a setting. The default 2,000 is the free Directions quota of §10. §4.5 and the A1 service environment list need the name once the team decides.
- **PD-IMP-307-2: same place twice.** `route_cache` has `CHECK (from_place_id <> to_place_id)`, so `travel` returns the 0-minute estimate for one place without calling ORS or writing the cache. The insert would otherwise fail and abort the transaction.
- **PD-IMP-307-3: test file.** §9.3.5 and §10 name `tests/unit/routing/test_client.py`; the card names `test_routing_service.py`. The card is followed.
- **PD-IMP-307-4: an active estimate blocks ORS for up to a day.** The lookup order puts the cache first, so a cached estimate is used until it expires, and only then can a routing result replace it.

## Open issues

- The counter is per process, so several API tasks each count their own calls and the warning can come late. It also starts again on a restart. A shared count would need a table or service, so a decision first.
- IMP-308 is the first caller: it builds `RoutingService(RouteCacheRepository(session), get_client())`.
- `get_client()` reads the settings once per process.
