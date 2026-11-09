# IMP-402 · fallback-planner part

- Run id: RUN-057 (grouped, IMD-121, with IMP-401, IMP-406 and FIX IMD-126)
- Owner: Malhar (Malhar1112-v)
- Status: PR open
- Base commit: 16839a0
- Branch: feat/IMP-401-402-406-generation-reliability
- Reviewer: Manasvi (Manasvi1704)
- Traces to: US-058; FR-036; NFR-006, NFR-007; IMD-22, IMD-43, IMD-131
- Card steps built: 1 to 4 and 6, narrowed by §8.15 and the run prompt

## Preflight findings (run prompt, preflight 3)

- (a) API-22 and API-23: `GenerationStartIn.mode` already accepted `rule_based` in the contract, but `generation/service.py` refused it with 422 (`field mode`, "Rule-based planning is not available yet."). This part enables it; the OpenAPI shape is unchanged. API-23 already returned `fallback_reason` from `validation_summary.provider_failure`.
- (b) Sampleton place IDs are **not** stable across reseeds: `places.id` defaults to `gen_random_uuid()` (migration 0002) and `app/places/import_pipeline.py` builds `Place(**values)` without an `id` (the seed columns start with `external_ref`). A reseed after `make db-reset` gives new IDs. See the IMP-402 sample-itineraries blocker.
- (c) No repair call to the provider exists on main (`repair.py` and `mark_repairing` callers are absent); the repair route is IMP-502.

## Changed files

- `apps/api/app/generation/fallback_planner.py` (created): `plan_rule_based(request) -> ItineraryOutput`, pure and deterministic. Per day it starts at `limits.day_start`; must-visit places first, then the day's `day_hints`, then the rest, each time the nearest place that still fits (ties by shortlist rank); one `food` place becomes the meal once the clock is in 12:00 to 14:00 and only if it starts by 14:00; it stops at `max_items_per_day`, `max_active_minutes_per_day` (visits plus travel) or `day_end`. Travel is the §9.3.5 distance estimate plus its buffer, the arithmetic step 9 repeats. Theme "Day N around <first place>", empty notes (saved as no note, IMD-131), summary "Plan built by rules, without AI." `NoPlanError` when not one item fits. `MODEL_ID = "rule_based_planner_v1"`. It imports nothing from the mock provider or any adapter.
- `apps/api/app/generation/pipeline.py` (wiring): a `Job` holder; `run_fallback` (the planner on the still-active shortlist, then steps 8, 9 and 11 like a model answer); `save` (steps 9 and 11, shared by both outcomes); `end_invalid_output` now runs the fallback with `provider_failure = invalid_output` (no repair before it until IMP-502). Mode `rule_based` (row `model_id = rule_based_planner_v1`) skips retrieval and the provider. A retryable provider error falls back with its `failure_reason` as `provider_failure`; quota and configuration errors still end `failed` (IMD-44). A fallback whose plan is unusable or empty ends `failed` / `unresolved_validation`. The fallback summary keeps the refused answer's step-8 counts (`invalid_ids`, `rejected_items`, `unknown_source_ids`, `kind`); `errors`, `warnings`, `infos` are the saved plan's.
- `apps/api/app/generation/service.py`: API-22 accepts mode `rule_based`; the AI notice is checked for mode `ai` only (§6.4); a rule-based row stores the configured provider name with `model_id = rule_based_planner_v1` (IMD-43). `RULE_BASED_MODEL_ID` now comes from the planner.
- `apps/api/app/itinerary/service.py`: `save_generated_plan(..., origin=)`; `fallback_rule_based` saves items with that origin and no note, and a version of reason `fallback` (§6.4 Complete). This file is in the IMP-406 lane of this run; the change is the one keyword the wiring needs.
- `apps/api/.importlinter`: `app.generation.fallback_planner` added to the pure-domain contract.
- Tests: `apps/api/tests/unit/generation/test_fallback_planner.py` (created); `apps/api/tests/api/test_generations.py` (TC-145, TC-331, a two-run test through the whole pipeline; four tests updated, below); `apps/api/tests/fixtures/pipeline.py` (row `model_id`, `fell_back`, `saved_ids`); `apps/api/tests/unit/generation/test_pipeline.py`, `apps/api/tests/unit/validation/test_output_check.py`, `apps/api/tests/unit/validation/test_injection_cases.py`.

Tests whose expected result changed with the specified behaviour (not weakened; each still asserts the refused answer is never saved): an unknown place, a malformed or schema-violating answer and an inactive place now end `completed` / `fallback_rule_based` with `fallback_reason invalid_output` instead of `failed` / `invalid_output` (§8.3 table). TC-118 now uses the MOCK `quota` scenario, which still fails, because a timeout falls back. The "rule_based mode is refused" case of the unknown-fields test became an unknown mode.

## Commands and results

| Command | Result |
| --- | --- |
| `make test-unit ARGS='-k fallback'` | `75 passed, 866 deselected, 1 warning` |
| `make test-unit` | `941 passed, 1 warning` |
| `make test-web` | `Tests  119 passed (119)` |
| `make lint` | exit 0 |
| `make typecheck` | exit 0 (`Success: no issues found in 112 source files`) |
| `make imports` | `Contracts: 6 kept, 0 broken.` |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` |
| `make test-api ARGS='-k fallback'` | not run to a result: no PostgreSQL or Docker on this machine (`connection to server at "127.0.0.1", port 5432 failed: Connection refused`). Evidence comes from the CI `api` job |

A probe of all 15 SAMPLE cases of `eval/datasets/trips/v1` (planner, then `schedule.recalculate` with the distance estimate, then `validate()`) gave no finding of any severity; the parametrised unit tests assert the same for error findings.

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-036 AC1 / TC-145: unavailable provider → labelled rule-based plan saved | verified (unit); API not verified locally | `test_fallback_after_an_unavailable_provider_saves_the_labelled_plan`; `test_tc_145_fallback_an_unavailable_provider_saves_a_labelled_rule_based_plan` runs in CI |
| FR-036 AC2 / TC-146: two runs identical | verified | `test_fallback_tc_146_two_runs_give_identical_plans` (15 cases); `test_fallback_mode_rule_based_twice_gives_the_same_plan` in CI |
| No error-level finding on the SAMPLE trips | verified | `test_fallback_plans_have_no_error_finding_on_the_sample_trips` (15 cases, merged `validate()`) |
| Unplaceable must-visit place reported as MUST_VISIT_MISSING | verified | `test_fallback_leaves_out_a_must_visit_place_that_cannot_fit_and_the_validator_reports_it` (reported by `validate()`; saving the finding is IMP-406 must-visit-constraints) |
| TC-331 / IMD-43: model_id rules | verified (unit); API not verified locally | `test_fallback_mode_rule_based_makes_no_model_call`; `test_tc_331_fallback_mode_rule_based_is_recorded_as_rule_based_planner_v1` and TC-145's `model_id mock-v1` run in CI |
| Fallback items save no note; never an AI badge | verified (unit); API in CI | `test_fallback_text_comes_from_templates_and_items_have_no_note`; TC-145 asserts `note_origin none` and `theme_origin none` |
| No shared function with the mock provider (step 6) | verified | `test_fallback_shares_no_code_with_the_mock_provider` |

## Blockers

none

## Proposed decisions

- **PD-IMP-402-1: hours not checked by the planner.** The CLOSED_ON_DAY and OUTSIDE_HOURS rules (IMP-309) are not on main, so `validate()` cannot flag hours and the planner does not read `hours_summary`. Retrieval already drops places closed on every trip day. When IMP-309 lands, the planner should skip a place on a day its rule would flag.
- **PD-IMP-402-2: active minutes.** The planner counts visit minutes plus travel against `max_active_minutes_per_day`; DAY_TOO_LONG (IMP-309) has no definition on main yet. Counting travel is the stricter reading.

## Open issues

- IMP-403 owns `outcomes.resolve`; this part maps the outcomes inline in `pipeline.py` (retryable → fallback with its cause; quota and configuration → failed; invalid output → fallback). IMP-403 can move that mapping into `outcomes.py` without changing behaviour.
- The evaluation harness still exits 2 for `--provider RULE_BASED` (PD-IMP-413-2); `app/evaluation/**` is outside this run.
- Day grouping is the simple nearest-neighbour fill; IMP-503 replaces it with the clustering.
