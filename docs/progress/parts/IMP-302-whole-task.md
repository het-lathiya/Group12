# IMP-302 · whole-task part

- Run id: RUN-047 (grouped, IMD-121, with IMP-312 and IMP-305)
- Owner: Kirtan (kirtan-S111)
- Status: PARTIAL run; this part is complete and pushed, no pull request yet
- Base commit: 7974da0
- Branch: feat/IMP-312-305-302-wave2
- Reviewer: Manya (manyarana)
- Traces to: US-041; FR-044; NFR-013, NFR-042; TC-006, TC-007, TC-044, TC-167, TC-168
- Card steps built: 1 to 4

## Changed files

- `apps/api/app/ai/providers/mock.py`: `health_check` answers `down` when `raise_error` is a configuration error. Card step 4 tests MOCK with `raise_error=ProviderAuthError()`, and the mock always answered `ok` before. This file is not in the card's list.
- `apps/api/app/core/health.py`: docstring only, naming `ProviderCheck` as the allow-list.
- `apps/api/tests/api/test_health.py`: TC-006, TC-044, TC-167, TC-168 and cache expiry.
- `apps/api/tests/contract/test_provider_contract.py`: TC-006, TC-007 over every adapter.
- `apps/api/tests/unit/ai/test_mock_provider.py`: the new `health_check` rule.

Steps 1 to 3 were already in place from IMP-201: API-02 reports `checks.provider {name, model_id, status}` with the 60 s cache, API-01 gives the provider name only with no provider call, only the database answers 503, and `ProviderCheck` is an allow-list. This part adds the evidence, so `apps/api/app/ai/factory.py` needed no change. `MIGRATION_HEAD` stays `0007`. Breaker half-open has no path until IMP-401; a `degraded` provider is tested directly.

## Commands and results

| Command | Result line |
| --- | --- |
| `make test-api ARGS='-k health'` | `31 passed, 248 deselected, 1 warning in 5.45s` |
| `make test-contract` | `87 passed, 2 deselected, 1 warning in 4.01s` |
| `make check` (with this commit's tree) | exit 0: unit `578 passed, 1 warning`; contract `87 passed, 2 deselected, 1 warning`; api `279 passed, 1 warning`; authz `29 passed`; web `Tests  80 passed (80)` |

Not run: `/health/ready` on staging (no AWS staging yet).

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-044 AC1: the provider name, model identifier and status are reported (TC-167) | verified | `test_tc_167_*` |
| FR-044 AC2: a failing check reports degraded and non-AI pages still work (TC-168) | verified | `test_tc_168_*`, with MOCK `raise_error=ProviderAuthError()` and GEMINI without a key |
| The health check is cheap: no generation call and no row (TC-006) | verified | `test_tc_006_*` in `test_health.py` and the contract suite |
| Metadata is complete: provider, model_id, adapter_version (TC-007) | verified | `test_tc_007_metadata_names_the_provider_model_and_adapter` |
| No secret in any health response (TC-044) | verified | `test_tc_044_*`, including a provider detail that holds a key |
| With the provider down, API-08 and API-10 answer 200 | verified | `test_tc_168_with_the_provider_down_non_ai_routes_still_answer` |
| Staging `/health/ready` shows provider GEMINI and its status | not verified | No AWS staging yet |

## Blockers

None.

## Proposed decisions

None.

## Open issues

- IMP-401 must report the breaker through `health_check`, so that `down` (open) and `degraded` (half-open) reach `/health/ready`.
