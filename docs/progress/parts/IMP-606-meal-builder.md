# IMP-606 · meal-builder part

- Part: Meal slots in the request builder and fallback planner (2 points)
- Run id: RUN-075 (Sprint 6 batch A)
- Owner: Manya (Manya Rana)
- Status: PR_OPEN once the lead opens the pull request; committed on `part/g`, not pushed
- Base commit: a6307c3
- Traces to: US-060; FR-083; TC-243, TC-372
- Card steps built: 3 (meal slots in gr-1, meal items must be food places), 4 (fallback lunch or day note), 6 (switch `meal_slots`)

## Changed files

- `apps/api/app/generation/request_builder.py`: `limits.meal_slots` comes from `presets.meal_slots(pace, enabled=…)` (lunch for balanced and busy, none for relaxed or with the switch off); `RequestSettings.meal_slots_enabled` carries the switch; `build` reads `is_enabled(settings, "meal_slots")` once and passes the same count to `retrieval.ranked_shortlist`. The constant `MEAL_SLOTS` is removed.
- `apps/api/app/generation/fallback_planner.py`: the lunch window comes from `presets.MEAL_WINDOWS`; a lunch is planned only when the request has a lunch slot; a day that runs through the lunch window without a meal gets the theme suffix " · No food place found nearby" (within the 80-character theme; a day-level message, never an item note, so `note_origin` stays as it was). With no lunch slot a must-visit food place is an ordinary activity.
- `apps/api/app/validation/output_check.py`: `check_output(..., food_ids=...)` drops a `meal` item whose place is not a food place, with an UNKNOWN_PLACE finding ("A meal must be a food place from the shortlist.") counted in `invalid_ids`: the existing invalid-reference rule, so step 10 counts it as a deterministic repair. `without_meals` turns meal items into activities.
- `apps/api/app/generation/pipeline.py`: `assess` passes the shortlist's food place IDs to `check_output`, and applies `without_meals` when the request has no meal slot (switch off or relaxed pace), so no meal item is saved then.
- `apps/api/app/evaluation/run.py`: the retrieval evaluation's shortlist uses `presets.meal_slots(prefs.pace)` instead of the removed constant.
- `data/fixtures/sampleton/sample_itineraries/two_day_walking.json`, `five_day_local_transport.json`: regenerated with `scripts/build_sample_itineraries.py` (never by hand); three days now carry the no-food note in their theme.
- Tests: `apps/api/tests/unit/generation/test_meal_slots.py` (fallback lunch from a food place inside the window; no food place → day note; switch off → no meal and no note; meal on a non-food place → UNKNOWN_PLACE; `without_meals`), `apps/api/tests/unit/generation/test_request_builder.py` (pace test expects lunch only above six active hours; switch off requests no meal slot), `apps/api/tests/api/test_generations.py` (TC-243 on the SAMPLE trip, a model plan's meals are food places, TC-372 for both modes), and the removed constant replaced in `tests/api/test_rag_retrieval.py` and `tests/unit/ai/test_mock_provider.py`.

## Commands

Run from the worktree root with `PYTHONPATH=$PWD/apps/api`. API and authorization tests used a throwaway local PostgreSQL 16 with pgvector (`travel_test_g` on 127.0.0.1:55432), not a shared database.

- `make test-unit ARGS='-q -k meal'` → `30 passed, 1131 deselected, 1 warning in 1.10s`
- `make test-unit ARGS='-q'` → `1160 passed, 1 warning in 16.59s`
- `make test-api ARGS='-q -k "meal" tests/api/test_generations.py'` → `4 passed, 466 deselected, 1 warning in 3.24s`
- `make test-api ARGS='-q'` → `470 passed, 1 warning in 144.89s (0:02:24)`
- `make test-authz ARGS='-q'` → `47 passed in 22.46s`
- `make test-contract ARGS='-q'` → `91 passed, 2 deselected, 1 warning in 19.46s`
- `make lint` → `All checks passed!`, `229 files already formatted`, ESLint `✖ 1 problem (0 errors, 1 warning)` (existing, another file), `All matched files use Prettier code style!`
- `make typecheck` (mypy) → `Success: no issues found in 122 source files`
- `make imports` → `Contracts: 6 kept, 0 broken.`
- `make openapi-check` → `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date`
- `apps/api/.venv/bin/python scripts/build_sample_itineraries.py --check` → exit 0

Not run: `make e2e` (no Docker on this machine).

## Acceptance criteria

- FR-083 AC1 (TC-243), rule-based plans: **verified** by `test_meal_tc_243_fallback_fills_the_lunch_slot_from_a_food_place`, `test_meal_tc_243_no_food_place_leaves_the_slot_empty_with_a_day_note` and the API test `test_meal_tc_243_every_full_day_has_lunch_from_a_food_place_or_a_note` (SAMPLE trip, three balanced days, each a food-place lunch or the note).
- "With MOCK and the SAMPLE fixture every full day has a lunch item from a food place or an empty-slot note": **verified for the rule-based plan only; not verified for a MOCK model plan.** The MOCK adapter builds its plan in shortlist order as §8.4 fixes it, so a day can have no meal or several food stops; `test_meal_a_model_plan_saves_meals_only_on_food_places` shows that every saved meal is a food place. See PD-RUN-075-G1.
- With `meal_slots` disabled generation still succeeds without meal items (TC-372): **verified** by `test_meal_tc_372_switched_off_generation_succeeds_without_meal_items[ai]` and `[rule_based]`, `test_request_builder_meal_tc_372_switch_off_requests_no_meal_slots`, `test_meal_tc_372_switch_off_inserts_no_meal_and_no_note`.

## Blockers

none

## Proposed decisions

- **PD-RUN-075-G1: the empty-slot note on a model plan.** The day note is safe only on rule-based plans: on a model plan the theme is labelled AI-written as a whole (`theme_origin` is per day), so a code-written note there would be mislabelled. And the MOCK adapter follows §8.4 (shortlist order), so it does not fill lunch the way a compliant model would. Options: (a) amend §8.4 so the MOCK `ok` scenario places one food place at the lunch window when `limits.meal_slots` has lunch (changes three mock unit tests that pin the order); (b) a day-level code message on API-24 (contract change); (c) let the step-10 repair insert a food place into an empty lunch window. Recommendation: (a) for the MOCK criterion, and (c) later if Gemini plans skip lunch in the evaluation.
- **PD-RUN-075-G2: relaxed pace has no lunch slot.** Card step 1's rule ("a day longer than 6 active hours gets a lunch slot") gives relaxed (300 active minutes) no lunch slot; before this part every pace had one. Built as the card says; confirm.

## Open issues

- Evaluation results of new runs differ from earlier records for relaxed cases (no meal slot in the request).
