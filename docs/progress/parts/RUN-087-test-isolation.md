# RUN-087 · test-isolation part

- Run id: RUN-087
- Owner: Junaid
- Status: PR_OPEN
- Base commit: 4fe514c
- Branch: chore/S7-D-gate-report
- Points: 0 (maintenance fix found during Sprint 7, no card)

## Problem

With a real `ORS_API_KEY` in a developer's untracked `apps/api/.env` (or shell), `make test-authz` gave `25 passed, 14 skipped, 62 errors`: the routing client read the key through `get_settings()`, called OpenRouteService, and the socket guard refused the call. CI has no `.env` and passed. Reproduced in this run with a dummy shell value: `ORS_API_KEY=dummy-not-a-key make test-authz` gave `============ 25 passed, 14 skipped, 1 warning, 62 errors in 19.16s =============` before the change.

## Change (tests only)

- `apps/api/tests/conftest.py`: new autouse fixture `isolate_local_provider_keys`. For every test not marked `live` it removes `ORS_API_KEY` from the environment and wraps `app.core.config.load_settings` so the accessor `get_settings()` returns an empty ORS key, unless the test sets `ORS_API_KEY` itself; it clears the `get_settings` cache and the routing `get_client` cache before and after the test. Live tests keep their real environment.
- Why not `ORS_API_KEY=""`: `Settings` uses `env_ignore_empty=True`, so an empty value falls back to the `.env` file and the local key would still apply.
- The fixture uses a private `pytest.MonkeyPatch.context()` rather than the shared `monkeypatch` fixture. A first version that shared it changed the teardown order with the socket guard and left the guard patched after `test_tc_035_generate_runs_with_socket_connect_patched_to_raise`, which failed `test_live_test_is_not_blocked_by_the_guard` (2 failed); the private context fixed this.
- No change to app code, the socket guard, the ORS client, CI files or any `.env` file.

## Changed files

- apps/api/tests/conftest.py (modified)
- apps/api/tests/unit/core/test_local_key_isolation.py (created)
- docs/progress/parts/RUN-087-test-isolation.md (created)

## Commands run

| Command | Result line (quoted exactly) |
| --- | --- |
| `ORS_API_KEY=dummy-not-a-key make test-authz` (before the change) | `============ 25 passed, 14 skipped, 1 warning, 62 errors in 19.16s =============` |
| `make test-authz` | `================== 87 passed, 14 skipped, 1 warning in 21.51s ==================` |
| `ORS_API_KEY=dummy-not-a-key make test-authz` | `================== 87 passed, 14 skipped, 1 warning in 21.94s ==================` |
| `make test-api` | `================== 590 passed, 1 warning in 114.81s (0:01:54) ==================` |
| `ORS_API_KEY=dummy-not-a-key make test-api` | `================== 590 passed, 1 warning in 120.38s (0:02:00) ==================` |
| `make test-unit ARGS='-q'` | `1219 passed, 1 warning in 7.83s` |
| `ORS_API_KEY=dummy-not-a-key make test-unit ARGS='-q'` | `1219 passed, 1 warning in 7.75s` |
| `ruff check` and `ruff format --check` on the two test files | `All checks passed!` · `2 files already formatted` |

The full `make check` for the branch is recorded in the pull request and the SYNC report.

## Not run

| Command | Reason |
| --- | --- |
| `make live-smoke` | Live calls are out of scope for this run; live tests are unchanged by design |

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| Non-live tests never depend on, or reach the network because of, a local `ORS_API_KEY` | verified | `test_local_key_isolation.py`: shell variable removed, a key in a local env file is not used (other values from the file still apply), routing client built without the key; proof runs above give the same counts as plain runs with 0 errors |
| A test that sets `ORS_API_KEY` itself keeps it | verified | `test_a_key_the_test_sets_itself_is_kept`; existing `test_get_client_reads_the_settings_once` passes |
| Live tests keep their real environment | verified (by code) | the fixture returns early for tests marked `live`; no live test ran in this run |
| No app-code change | verified | `git diff --stat` touches only `apps/api/tests/` and this record |

## Blockers

none

## Proposed decisions

none

## Open issues

none
