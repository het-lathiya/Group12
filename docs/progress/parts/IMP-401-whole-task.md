# IMP-401 · whole-task part

- Run id: RUN-057 (grouped, IMD-121, with IMP-402, IMP-406 and FIX IMD-126)
- Owner: Nidhi (Nidhi9864)
- Status: PR open
- Base commit: 16839a0
- Branch: feat/IMP-401-402-406-generation-reliability
- Reviewer: Manasvi (Manasvi1704)
- Traces to: US-038; FR-047; NFR-004, NFR-006; IMD-27, IMD-44; Amendment A1 (IMD-112)
- Card steps built: 1 to 5

## Changed files

- `apps/api/app/ai/breaker.py` (created): `CircuitBreaker(clock)` with states closed, open, half_open. Opens after 5 consecutive transient failures (timeout, rate limit, unavailable) or at once on `ProviderQuotaExhausted` or `ProviderAuthError`; cool-down 60 s (transient), 15 min (quota), until restart (auth); after the cool-down the next real request is the probe (success closes, failure reopens). `open_reason` is the opening error's `failure_reason`. A bad request neither counts nor resets.
- `apps/api/app/ai/factory.py`: `breaker_for(provider)`, one breaker per provider instance (weak keys, cleared by `reset_provider_cache`); the Gemini adapter is built with the same instance.
- `apps/api/app/ai/providers/gemini.py`: `_with_retries` replaces the embedding-only loop and now also wraps generation: at most `min(1 + GEMINI_MAX_RETRIES, 2)` attempts (`MAX_ATTEMPTS = 2`), only `ProviderTimeout`, `ProviderRateLimited` and `ProviderUnavailable` retried, backoff 1, 2, 4 s ±25 % or `retry_after_s` if longer, no wait that reaches the end of the 70 s allowance, each attempt's timeout `min(GEMINI_TIMEOUT_S, time left)` (the IMP-301 shortcut comment is resolved). Injectable `clock` and `sleep`. `health_check` reports `down` while the breaker is open and `degraded` while half-open.
- `apps/api/app/generation/pipeline.py`: step 7 is skipped while the breaker is open: opened by transient errors → the rule-based plan with that cause in `provider_failure`; opened by quota or auth → `failed` with `provider_quota_exhausted` or `config_error`, no fallback (IMD-44). Each generation records its provider result once, after the retries (an invalid answer counts as the service answering). Mode `rule_based` never consults the breaker. Retrieval's embeddings are never recorded.
- `docs/decisions/gemini-setup.md`: "Retry setting (IMP-401)". The run prompt names `docs/guides/gemini-setup.md`; the file lives in `docs/decisions/` (the adapter's docstring cites that path), so the section was added there.
- Tests: `apps/api/tests/unit/ai/test_retry.py`, `apps/api/tests/unit/ai/test_breaker.py` (created). `apps/api/tests/unit/ai/test_gemini_adapter.py`: its helper now builds the adapter with `GEMINI_MAX_RETRIES=0`, because those tests map single answers and would otherwise wait for a real backoff; `test_gemini_the_sdk_makes_one_attempt_only` keeps its meaning (any second request would be the SDK's). `apps/api/tests/unit/ai/test_gemini_embeddings.py`: `GEMINI_MAX_RETRIES=2` now gives 2 attempts, not 3 (§8.14: no path exceeds two attempts).

## Commands and results

| Command | Result |
| --- | --- |
| `make test-unit ARGS='-k retry'` | `28 passed, 949 deselected, 1 warning` |
| `make test-unit ARGS='-k breaker'` | `19 passed, 958 deselected, 1 warning` |
| `make test-unit` | `977 passed, 1 warning` |
| `make test-web` | `Tests  119 passed (119)` |
| `make lint` | exit 0 |
| `make typecheck` | `Success: no issues found in 112 source files` |
| `make imports` | `Contracts: 6 kept, 0 broken.` |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` |
| `make test-api`, `make test-authz` | not run to a result: no PostgreSQL or Docker on this machine (connection refused on port 5432). Evidence comes from the CI `api` job |

Breaker transitions on the fake clock (`test_breaker.py`): closed → 4 failures still closed → 5th open (`open_reason` = the error's reason) → at 59 s open, at 60 s half_open → probe success closed; failed probe → open again → half_open after another 60 s; quota → open, half_open at 900 s; auth → open after 10 days.

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-047 AC1 / TC-174: five consecutive transient failures open the breaker; an open transient breaker uses the fallback without a provider call | verified | `test_breaker_tc_174_five_transient_failures_then_the_fallback_without_a_provider_call` (MOCK `raise_error=ProviderUnavailable()`, pipeline stand-ins) and `test_breaker_tc_010_opens_after_five_consecutive_transient_failures`. The card's five failures are used; FR-047 AC1's text says three 503s (see PD-IMP-401-1) |
| FR-047 AC2 / TC-175: a quota-opened breaker ends the next AI generation failed / provider_quota_exhausted without a provider call (IMD-44) | verified | `test_breaker_tc_175_a_quota_breaker_fails_the_next_generation_without_a_provider_call`; auth → `config_error` in `test_breaker_an_auth_breaker_fails_with_config_error` |
| TC-009: only transient errors are retried | verified | `test_retry_tc_009_a_transient_error_is_retried_once_then_succeeds` (503, 500, timeout) and `test_retry_tc_009_tc_017_other_errors_are_never_retried` (quota, auth, bad request, malformed, blocked) |
| TC-016: 429 uses bounded backoff | verified | `test_retry_tc_016_a_rate_limit_waits_for_retry_after` (waits 7 s), `test_retry_tc_016_a_retry_after_past_the_allowance_is_not_waited_for` |
| TC-017: quota exhaustion is not retried | verified | the quota case of `test_retry_tc_009_tc_017_other_errors_are_never_retried` |
| TC-018: timeout is enforced | verified | `test_retry_tc_018_each_attempt_gets_at_most_the_time_left`, `test_retry_tc_018_no_attempt_starts_once_the_allowance_is_spent`, `test_retry_tc_018_a_slow_answer_becomes_a_provider_timeout_per_attempt` |
| TC-010: opens and recovers through half-open | verified | `test_breaker_tc_010_recovers_through_half_open`, `test_breaker_tc_010_a_failed_probe_opens_it_again_at_once` |
| No path exceeds two provider attempts or 70 s | verified | `test_retry_no_path_makes_more_than_two_attempts` (GEMINI_MAX_RETRIES 1, 3, 10); the 70 s tests above |
| health_check down while open, degraded while half-open | verified | `test_breaker_health_is_down_while_open_and_degraded_while_half_open`, `test_breaker_the_factory_gives_the_gemini_adapter_its_own_breaker` |
| Embeddings neither counted nor blocked (A1) | verified | `test_breaker_embedding_calls_are_neither_counted_nor_blocked` |
| Routed fix: a repair call passes `wire_schema(output_model)` with retries bounded by the allowance | not verified | No repair call exists on main (preflight 3c): deferred to IMP-502 |

## Blockers

none

## Proposed decisions

- **PD-IMP-401-1: three or five failures.** FR-047 AC1 says "three consecutive 503 responses"; the card, §8.4 and TC-174 say 5. Built with 5 (`FAILURES_TO_OPEN`); the requirement text should be aligned.
- **PD-IMP-401-2: what counts as one failure.** The breaker counts generations (after the adapter's retries), not HTTP attempts, as the card's "5 consecutive provider-failure generations" says. An invalid answer counts as a success (the service answered).

## Open issues

- The repair call (IMP-502) must go through `_with_retries` with the remaining allowance and pass `wire_schema(output_model)` (IMD-136): deferred to IMP-502.
- The breaker is per process and in memory: with several API containers each keeps its own state (accepted by §8.4, "in memory").
