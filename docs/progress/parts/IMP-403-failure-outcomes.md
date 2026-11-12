# IMP-403 · failure-outcomes part

- Run id: RUN-060 (grouped, IMD-121, with IMP-405 and IMP-407)
- Owner: Nidhi (Nidhi9864)
- Status: PR open
- Base commit: 84d1973
- Branch: feat/IMP-403-405-407-failures-warnings-edits
- Reviewer: Kirtan (kirtan-S111)
- Traces to: US-059; FR-037; NFR-006, NFR-007, NFR-024; IMD-22, IMD-27, IMD-44, IMD-131
- Card steps built: 1, 2, 3, 5, and the API side of step 4 (the message mapping). The web side of step 4 is the fallback-notice part.

## What main already had

IMP-401 and IMP-402 (RUN-057) already sent transient errors and an open transient breaker to the rule-based plan, and failed quota and configuration errors. That logic was spread across `if` branches in `pipeline.run`. This part puts it in one table and reuses the IMP-401 breaker (`factory.breaker_for`) and the IMP-402 planner (`fallback_planner.plan_rule_based`, through `pipeline.run_fallback`) unchanged.

## Changed files

- `apps/api/app/generation/outcomes.py` (created, pure): `Outcome(kind, reason)`, `resolve(error)`, `resolve_open_breaker(open_reason)` and the constants `INVALID_OUTPUT`, `UNRESOLVED` (for IMP-502's "unusable after repair") and `INTERNAL`. The outcome table:
  - transient errors after retries, or a breaker opened by them → fallback with that cause;
  - ProviderInvalidOutput or a step-8 refusal → fallback `invalid_output`;
  - QuotaExhausted, or a breaker opened by quota → failed `provider_quota_exhausted`;
  - AuthError or BadRequest, or a breaker opened by auth → failed `config_error`;
  - an unclassified ProviderError or any other exception → failed `internal`.

  `MESSAGES` (moved from `service.FAILURE_TEXT`) maps each failure_reason to the §6.4 `failure_message` and `next_action` (the user message key of step 4). The text is fixed and never comes from the error (NFR-024).
- `apps/api/app/generation/pipeline.py`: the open-breaker branch and the `ProviderError` branch call `end_with(job, request, outcome, metadata)`, which either runs the rule-based plan (`run_fallback`, cause in `validation_summary.provider_failure`, failure_reason null) or fails the row and writes nothing to the itinerary tables. `end_invalid_output` takes its cause from `outcomes.INVALID_OUTPUT`. The module docstring records the reserve and the failure path.
- `apps/api/app/generation/service.py`: API-23 reads `outcomes.MESSAGES`.
- `apps/api/tests/api/test_generation_failures.py` (created): 30 cases, listed below.

Step 2, the 15 s reserve: the fallback runs inside the job's 120 s `asyncio.timeout` (jobs.py), after the provider's 70 s allowance, so it gets the 15 s reserve of §8.2 plus any unused time. No second timer was added. If the fallback raises (a planner bug, say), the exception reaches the job runner, which ends the row `failed` / `internal`. A rule-based plan that cannot be built (NoPlanError) or is unusable ends `failed` / `unresolved_validation`, as §6.4 says. Both paths are tested.

Fallback items save no note (IMD-131): unchanged, asserted in every fallback test (`origin fallback_rule_based`, `note` null).

## Commands and results

PostgreSQL: a throwaway PostgreSQL 16.2 with pgvector on 127.0.0.1:55432 (scratch directory, `TEST_DATABASE_URL` set for the run).

| Command | Result |
| --- | --- |
| `make test-api ARGS='-k generation_failures'` | `30 passed, 374 deselected, 1 warning` |
| `make test-api` | `404 passed, 1 warning` |
| `make test-authz` | `37 passed` |
| `make test-unit` | `1006 passed, 1 warning` |
| `make test-web` | `Tests  151 passed (151)` |
| `make lint` | exit 0 |
| `make typecheck` | `Success: no issues found in 116 source files` (web `tsc` clean) |
| `make imports` | `Contracts: 6 kept, 0 broken.` |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` |

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-037 AC1 / TC-148: a timeout (after the adapter's retries) falls back | verified | `test_tc_148_tc_307_...[timeout]`, `[rate_limited]`, `[unavailable]`, `[invalid_json]`; open transient breaker: `test_generation_failures_a_breaker_opened_by_timeouts_falls_back_without_a_call`. The adapter's own retry count is TC-016/TC-018 in `test_retry.py` (IMP-401) |
| FR-037 AC2 / TC-149: quota exhaustion pauses AI and offers rule-based | verified | `test_tc_149_..._quota_and_config_errors_end_failed_with_no_plan[quota]` ("AI generation is paused for today.", `retry_rule_based`); `test_tc_149_..._after_quota_the_rule_based_option_builds_a_plan` (the breaker stays open, the next AI request fails the same way, and mode rule_based completes) |
| FR-037 AC3 / TC-150: trip data unchanged after any failure | verified | `test_tc_150_tc_308_..._leave_the_earlier_plan_unchanged[quota, auth]` (revision, days, items, warnings and versions identical); the `[quota, auth, unclassified]` cases on a trip without a plan |
| TC-005, TC-017: each vendor failure maps to one shared type and failure_reason | verified | `test_tc_005_tc_017_generation_failures_map_to_one_outcome` (9 cases), `..._every_shared_error_type_has_a_message_and_a_db_reason`, `..._an_open_breaker_keeps_a_quota_or_auth_cause` |
| TC-307: an invented place ID leads to the fallback plan | verified | `test_tc_148_tc_307_...[unknown_place]` |
| TC-308: an outage leaves the trip unchanged | verified | `test_tc_308_..._an_outage_keeps_the_trip_preferences_and_versions` (preferences and earlier versions byte-identical; the fallback adds one labelled revision) |
| The fallback itself failing ends failed internal | verified | `test_generation_failures_a_failing_fallback_ends_failed_internal` |
| NFR-024: no vendor text in API-23 or logs | verified | `test_nfr_024_generation_failures_show_and_log_no_vendor_text[fallback, failed]` (vendor text in the error message; absent from the API-23 body and the captured logs at DEBUG) |

## Blockers

none

## Proposed decisions

none

## Open issues

- `UNRESOLVED` is defined for IMP-502 (the repair call), which is the first code that can produce "unusable after repair"; nothing emits it yet.
- Screenshots of the notices on the local stack are part 5's evidence and are added on staging after deploy.
