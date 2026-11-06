# IMP-305 · job-progress part

- Run id: RUN-047 (grouped, IMD-121, with IMP-312 and IMP-302)
- Owner: Het (het-lathiya)
- Status: PARTIAL run; this part is complete and pushed, no pull request yet
- Base commit: 7974da0
- Branch: feat/IMP-312-305-302-wave2
- Reviewer: Manya (manyarana)
- Traces to: US-048; FR-024, FR-025; NFR-021, NFR-042; IMD-12, IMD-24, IMD-119; TC-114 to TC-119, TC-309
- Card steps built: 2, 3 and 6

## Changed files

- `apps/api/app/auth/router.py`: API-04 now answers; the 501 placeholder is gone.
- `apps/api/app/auth/service.py`, `repository.py`: `update_profile` accepts only `ai_notice_acknowledged: true`; `ai_notice_acknowledged` answers the gate; `set_ai_notice_ack` writes `profiles.ai_notice_ack_at`. `repository.get` reads with `populate_existing`, so a read after the update sees the new value in the same session.
- `apps/api/app/generation/service.py`: API-22 mode `ai` answers 422 with field `ai_notice` until the notice is acknowledged (IMD-24).
- `apps/api/app/generation/jobs.py`: the routed defect. `_fail_internal` keeps a row that has already ended and returns False, so a timeout after the plan's commit no longer raises `IllegalTransitionError` and no longer logs that the job timed out.
- `apps/api/tests/api/test_generations.py`, `test_me.py`, `test_itinerary.py`; `tests/authz/route_matrix.py` (API-04 joins the two-user suite as `scoped`), `tests/authz/test_ownership.py`.

`apps/api/app/auth/schemas.py` and `apps/api/app/generation/router.py` need no change: `ProfilePatch` already carries the flag, so the contract stands, and API-23 already returns `GenerationOut`. The API-22 router, the semaphore of 2, the one-active-job rule, the IMD-119 details entry and the 150 s reaper were already built by IMP-210 and are now covered by the TC tests below. The rule that needed `service.py` and `repository.py` of `auth` is the layer rule: routers hold no business rules.

## Commands and results

| Command | Result line |
| --- | --- |
| `make test-api ARGS='-k generations'` | `23 passed, 242 deselected, 1 warning in 13.59s` |
| `make test-api ARGS='-k ai_notice'` | `10 passed, 255 deselected, 1 warning in 2.23s` |
| `make test-authz` | `29 passed in 15.58s` |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` |
| `make check` (with this commit's tree) | exit 0: unit `570 passed, 1 warning`; contract `80 passed, 2 deselected, 1 warning`; api `265 passed, 1 warning`; authz `29 passed`; web `Tests  80 passed (80)` |

The regression tests were also run with the fix disabled: `2 failed, 263 deselected`. With the fix: `2 passed, 263 deselected`.

Not run: `make e2e ARGS='journey'`. It cannot pass until the privacy-progress part is built; see the open issues.

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-024 AC1: notice acknowledged, then 202 with a generation id (TC-114) | verified | `test_tc_114_mode_ai_needs_the_ai_notice_then_answers_202` |
| FR-024 AC2: an incomplete trip gives 422 listing missing fields (TC-115) | verified | `test_tc_115_an_incomplete_trip_lists_the_missing_fields` |
| FR-024 AC3: the same request returns the running job (TC-116) | verified | `test_tc_116_same_request_while_active_returns_the_same_generation` |
| A different request answers 409 with the IMD-119 details entry | verified | `test_a_different_request_while_active_is_refused` |
| FR-025 AC1: polling returns the status (TC-117) | verified for queued, running, validating and completed | `test_tc_117_polling_returns_the_status_while_the_job_runs`; `repairing` has no path until repair exists (IMP-401) |
| FR-025 AC2: a failed job gives a reason and a next step (TC-118) | verified | `test_tc_118_a_failed_job_gives_a_reason_and_leaves_the_previous_plan_untouched` |
| FR-025 AC3: a job past the timeout is marked failed (TC-119) | verified | `test_tc_119_the_job_timeout_fails_with_internal_and_says_timed_out` |
| A stale job is closed by the reaper (TC-309) | verified | `test_tc_309_the_reaper_closes_a_job_left_running_and_keeps_the_plan`, `test_api_23_reaps_a_stale_active_generation` |
| Mode ai before the acknowledgement is 422; after it, it starts (IMD-24, NFR-021) | verified | TC-114 test and the `test_ai_notice_*` cases |
| A timeout after the plan commit leaves the completed row (routed defect) | verified | `test_a_timeout_after_the_plan_commit_leaves_the_completed_row` |

## Blockers

None for this part.

## Proposed decisions

- **PD-IMP-305-1: the job timeout stays `asyncio.timeout`.** The card says `asyncio.wait_for`. Both cancel the pipeline at 120 s, and the existing tests and the job already use `asyncio.timeout`, so it is unchanged.
- **PD-IMP-305-2: API-04 refuses other declared fields for now.** `ProfilePatch` declares them, but the card allows only the flag until IMP-601. A body that names one answers 422 and changes nothing, rather than ignoring the field silently.

## Open issues

- **The generate page cannot start a generation until the privacy-progress part lands.** API-22 now refuses mode `ai` without the acknowledgement, and the page does not send it yet, so this part must not merge without that part. `make e2e ARGS='journey'` fails at Generate until then.
