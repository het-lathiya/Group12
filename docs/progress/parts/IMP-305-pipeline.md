# IMP-305 · pipeline part

- Run id: RUN-047 (grouped, IMD-121, with IMP-312 and IMP-302)
- Owner: Nidhi (Nidhi9864)
- Status: PARTIAL run; this part is complete and pushed, no pull request yet
- Base commit: 7974da0
- Branch: feat/IMP-312-305-302-wave2
- Reviewer: Manya (manyarana)
- Traces to: US-049; FR-031; NFR-004, NFR-008, NFR-042; TC-012, TC-133, TC-134, TC-135, TC-151
- Card steps built: 1, 4, 5 and 8

## Changed files

- `apps/api/app/generation/pipeline.py`: `enforce_input_limit`, then `record_settings` with `truncated_count` and the adapter's settings, the provider call, the step 8 hook `output_problem` (IMP-306) and the step 9 hook `recalculate` (IMP-308). Only what `recalculate` returns is saved.
- `apps/api/app/generation/retrieval.py`: `ranked_shortlist` runs `retrieve_candidates` and `rank_shortlist` (steps 3 and 4).
- `apps/api/app/generation/request_builder.py`: `build` takes the ranked shortlist, and `hours_summary` gives the stored hours on the trip's weekdays. This closes two IMP-303 open issues (the first-40-by-name shortlist and the label-only hours).
- `apps/api/app/generation/records.py`: `truncated_count` joins the allowed settings keys.
- `apps/api/app/generation/repository.py`: `record_settings`. `apps/api/app/places/repository.py`: `destination_by_id`, for the ranking area.
- `apps/api/app/ai/providers/base.py`: the docstring lists `app.ai.limits` among the modules that code outside `app/ai/` may use.
- Tests: `tests/unit/generation/test_pipeline.py` (created); `tests/api/test_generations.py`, `tests/unit/generation/test_request_builder.py` (modified). `test_the_request_holds_only_trip_data_and_shortlisted_places` now checks the ranked shortlist instead of the first 40 by name.

`apps/api/app/itinerary/service.py` needs no change: `save_generated_plan` and `repository.complete` already run in one transaction with the replace, the version, `plan_revision + 1` and `plan_stale` false, and the tests below now prove it. The completeness check of step 1 also already answers 422 before the row exists (TC-115, in `generation/service.py`).

## Commands and results

| Command | Result line |
| --- | --- |
| `make test-unit ARGS='-k pipeline'` | `6 passed, 571 deselected, 1 warning in 1.61s` |
| `make test-api ARGS='-k generations'` | `26 passed, 242 deselected, 1 warning in 18.70s` |
| `AI_PROVIDER=MOCK make test-api ARGS='-k generations'` | `26 passed, 242 deselected, 1 warning in 18.61s` |
| `make check` (with this commit's tree) | exit 0: unit `577 passed, 1 warning`; contract `80 passed, 2 deselected, 1 warning`; api `268 passed, 1 warning`; authz `29 passed`; web `Tests  80 passed (80)` |

The recorded Gemini `ok` fixture runs in both suites: `test_tc_133_the_recorded_gemini_answer_goes_through_every_step` and `test_the_recorded_gemini_answer_runs_the_whole_pipeline`. The second injects the adapter through the factory's `get_model_provider` and swaps the fixture's two SAMPLE place IDs for IDs the rendered request carried.

Not run: `make live-smoke` (no key, by instruction) and `make e2e` (see the open issue in `IMP-305-job-progress.md`).

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-031 AC1: GEMINI returns schema-valid JSON, on the recorded fixture (TC-133) | verified | `test_tc_133_*`. The fixture is hand-written, not a live recording (see the fixture README) |
| FR-031 AC2: MOCK makes no network call (TC-134) | verified | `test_tc_134_tc_162_mock_generation_completes_with_no_network_call` |
| FR-031 AC3: an ID outside the shortlist is rejected before saving (TC-135) | verified | `test_tc_135_an_id_outside_the_shortlist_is_rejected_before_saving` |
| A crash between items and version leaves the previous plan intact (NFR-008) | verified | `test_a_crash_between_items_and_version_leaves_the_previous_plan_intact` |
| Each completed job writes one row with provider, model_id and prompt_version (TC-012, TC-151) | verified | `test_tc_012_tc_151_*` |
| Save: replace, version `generation`, `plan_revision + 1`, `plan_stale` false | verified | `test_a_second_generation_replaces_the_plan_and_clears_plan_stale` |
| `truncated_count` is recorded in `generation_settings` | verified | `test_pipeline_records_how_many_places_the_input_limit_removed`, TC-012 test |
| Items saved with origin model and note_origin ai | verified | `test_the_recorded_gemini_answer_runs_the_whole_pipeline` |
| Times and costs come from recalculation, never from model fields | not verified | Step 9 is the pass-through hook this run asked for: times are still the model's and costs are null until IMP-308 |
| Staging: API-23 JSON at each status | not verified | No AWS staging yet. The local MOCK JSON is below |

## API-23 at each status (local MOCK run)

From a throwaway test on the migrated test database, reading API-23 at each status of one job, then a second job with scenario `timeout` for `failed`. The test was not committed. `repairing` has no path until IMP-401.

`queued`:

```json
{"id": "5e667b35-906d-49a6-8bfb-5e548307e71e", "trip_id": "0de1c1e4-09df-4c8d-a6ff-0805d0fcf9aa", "scope": "full", "day_number": null, "mode": "ai", "status": "queued", "outcome": null, "failure_reason": null, "failure_message": null, "next_action": null, "fallback_reason": null, "provider": "MOCK", "model_id": "mock-v1", "prompt_version": "v1", "repair_attempts": 0, "deterministic_repairs": 0, "validation_summary": {"errors": 0, "warnings": 0, "infos": 0}, "latency_ms": null, "itinerary_version_id": null, "plan_revision": null, "created_at": "2026-11-06T16:34:36.905020Z", "completed_at": null, "retrieval_mode": null, "embedding_model_id": null, "retrieval_ms": null}
```

`running`:

```json
{"id": "5e667b35-906d-49a6-8bfb-5e548307e71e", "trip_id": "0de1c1e4-09df-4c8d-a6ff-0805d0fcf9aa", "scope": "full", "day_number": null, "mode": "ai", "status": "running", "outcome": null, "failure_reason": null, "failure_message": null, "next_action": null, "fallback_reason": null, "provider": "MOCK", "model_id": "mock-v1", "prompt_version": "v1", "repair_attempts": 0, "deterministic_repairs": 0, "validation_summary": {"errors": 0, "warnings": 0, "infos": 0}, "latency_ms": null, "itinerary_version_id": null, "plan_revision": null, "created_at": "2026-11-06T16:34:36.905020Z", "completed_at": null, "retrieval_mode": null, "embedding_model_id": null, "retrieval_ms": null}
```

`validating`:

```json
{"id": "5e667b35-906d-49a6-8bfb-5e548307e71e", "trip_id": "0de1c1e4-09df-4c8d-a6ff-0805d0fcf9aa", "scope": "full", "day_number": null, "mode": "ai", "status": "validating", "outcome": null, "failure_reason": null, "failure_message": null, "next_action": null, "fallback_reason": null, "provider": "MOCK", "model_id": "mock-v1", "prompt_version": "v1", "repair_attempts": 0, "deterministic_repairs": 0, "validation_summary": {"errors": 0, "warnings": 0, "infos": 0}, "latency_ms": null, "itinerary_version_id": null, "plan_revision": null, "created_at": "2026-11-06T16:34:36.905020Z", "completed_at": null, "retrieval_mode": null, "embedding_model_id": null, "retrieval_ms": null}
```

`completed`:

```json
{"id": "5e667b35-906d-49a6-8bfb-5e548307e71e", "trip_id": "0de1c1e4-09df-4c8d-a6ff-0805d0fcf9aa", "scope": "full", "day_number": null, "mode": "ai", "status": "completed", "outcome": "model", "failure_reason": null, "failure_message": null, "next_action": null, "fallback_reason": null, "provider": "MOCK", "model_id": "mock-v1", "prompt_version": "v1", "repair_attempts": 0, "deterministic_repairs": 0, "validation_summary": {"errors": 0, "warnings": 0, "infos": 0}, "latency_ms": 129, "itinerary_version_id": "822f8da2-34d4-4a4e-90b7-7a0a442b8e51", "plan_revision": 1, "created_at": "2026-11-06T16:34:36.905020Z", "completed_at": "2026-11-06T16:34:36.905020Z", "retrieval_mode": null, "embedding_model_id": null, "retrieval_ms": null}
```

`failed`:

```json
{"id": "3a951498-7fd9-435e-bd94-a5e62e7a1136", "trip_id": "0de1c1e4-09df-4c8d-a6ff-0805d0fcf9aa", "scope": "full", "day_number": null, "mode": "ai", "status": "failed", "outcome": "failed", "failure_reason": "provider_timeout", "failure_message": "The AI service did not return a usable plan.", "next_action": "retry_rule_based", "fallback_reason": null, "provider": "MOCK", "model_id": "mock-v1", "prompt_version": "v1", "repair_attempts": 0, "deterministic_repairs": 0, "validation_summary": {"errors": 0, "warnings": 0, "infos": 0}, "latency_ms": 50, "itinerary_version_id": null, "plan_revision": null, "created_at": "2026-11-06T16:34:36.905020Z", "completed_at": "2026-11-06T16:34:36.905020Z", "retrieval_mode": null, "embedding_model_id": null, "retrieval_ms": null}
```

## Blockers

None for this part.

## Proposed decisions

- **PD-IMP-305-3: the provider stays a parameter of `pipeline.run`.** The card writes `pipeline.run(generation_id)` and `factory.get_provider()`. API-22 already resolves the provider through the factory's dependency and hands it to the job, which is how tests inject one, so the signature is unchanged.
- **PD-IMP-305-4: extend the §8.3 module list.** `app.ai.limits` is not among the modules §8.3 allows outside `app/ai/`. The pipeline must call it, so the docstring of `base.py` lists it and §8.3 needs the same line (raised in `IMP-303-whole-task.md`).
- **PD-IMP-305-5: `generation_settings` is read with `getattr`.** As PD-IMP-301-2 proposed, until `ProviderResult` has the field. MOCK has no such property, so its row holds only `truncated_count`.

## Open issues

- A trip whose prompt cannot fit `AI_MAX_INPUT_TOKENS` ends `failed` with `config_error`, as PD-IMP-303-5 implies.
- A must-visit place's `conflict_note` from retrieval does not reach the request: gr-1 has no field for it. IMP-306 or the warnings work must pick it up.
- `day_hints` stays empty until the grouping card.
