# RUN-077 · relaxed-lunch part

- Part: Lunch slot on relaxed full days (0 points; follow-up of IMP-606, decision IMD-189)
- Run id: RUN-077
- Owner: Manya (Manya Rana)
- Status: PR_OPEN once the lead opens the pull request; committed on `part/m`, not pushed
- Base commit: 0e15ae7
- Traces to: IMD-189 (PD-RUN-075-G2 rejected); US-060; FR-083; TC-243, TC-372

## What "full day" means in the code

There is no per-day flag. A request's days all share `limits.day_start`/`limits.day_end` and `limits.meal_slots`, so every planned day is offered the lunch slot. In the rule-based planner (`fallback_planner.plan_rule_based`) the slot is taken when the day's clock reaches the lunch window (12:00 to 14:00, `MEAL_WINDOWS`), and the "No food place found nearby" theme note is written only when the day's last item ends at or after 14:00 (`clock >= LUNCH_TO`). So a "full day" is a day whose plan runs through the lunch window; a day that ends before 14:00 (a short or regenerated day with few places) gets neither a meal nor the note. That IMP-606 rule is unchanged.

## Changed files

- `apps/api/app/generation/presets.py`: `meal_slots(pace, enabled=…)` returns `["lunch"]` at every pace (relaxed included) and `[]` when the `meal_slots` switch is off (IMD-11); an unknown pace still raises `ValueError`. `LUNCH_MIN_ACTIVE_MIN` (the six-active-hours rule) is removed; it had no other caller.
- `apps/api/tests/unit/generation/test_meal_slots.py`: every pace gets lunch; unknown pace rejected; a relaxed full day (3 items, 300 active minutes) gets its lunch from a food place inside the window.
- `apps/api/tests/unit/generation/test_request_builder.py`: the pace test expects `["lunch"]` for every pace.

`request_builder.py`, `fallback_planner.py`, `pipeline.py`, `retrieval.py`, `ai/limits.py` and `evaluation/run.py` read `meal_slots`/`limits.meal_slots` and needed no change: none of them assumed relaxed has no lunch. The SAMPLE itineraries are balanced-pace and unchanged (`build_sample_itineraries.py --check` exit 0).

## Commands

Run from `apps/api` (unit, contract) or the worktree root (`make test-api`). API tests used a throwaway local PostgreSQL 16 with pgvector (`travel_test_m` on 127.0.0.1:55432), not a shared database.

- `.venv/bin/python -m pytest tests/unit/generation -q` → `196 passed in 1.35s`
- `.venv/bin/python -m pytest tests/unit tests/contract -q` → `1278 passed, 2 skipped, 1 warning in 37.81s` (skips: live Gemini smoke without a key)
- `make test-api ARGS='-k "meal or generation or fallback or rag"'` → `186 passed, 378 deselected, 1 warning in 64.65s (0:01:04)`
- `.venv/bin/ruff check app tests` → `All checks passed!`; `.venv/bin/ruff format --check app tests` → `223 files already formatted`
- `.venv/bin/mypy app/generation/presets.py` → `Success: no issues found in 1 source file`
- `scripts/build_sample_itineraries.py --check` → exit 0

Not run: `make e2e` (no Docker on this machine); full `make check` (web side untouched).

## Acceptance criteria

- IMD-189: every full-day plan gets a lunch slot, relaxed pace included: **verified** by `test_meal_imd_189_every_pace_gets_a_lunch_slot[relaxed|balanced|busy]`, `test_request_builder_pace_limits[relaxed-3-300]` and `test_meal_imd_189_a_relaxed_full_day_gets_lunch_from_a_food_place`.
- Switch `meal_slots` off → no slots, no meal, no note (TC-372): **verified** by `test_meal_tc_372_switch_off_plans_no_meal_slots`, `test_request_builder_meal_tc_372_switch_off_requests_no_meal_slots`, `test_meal_tc_372_switch_off_inserts_no_meal_and_no_note` and the API test `test_meal_tc_372_switched_off_generation_succeeds_without_meal_items`.

## Blockers

none

## Proposed decisions

- **PD-RUN-077-M1: reserve lunch time in the relaxed budget.** The rule-based planner does not keep room for the meal in `max_active_minutes_per_day` and cannot wait for the lunch window. With relaxed (300 minutes) and long visits (two 120-minute places) the budget runs out at about 13:15, so the day ends inside the window with neither a meal nor the note (by the rule above it is not a full day). Option: before the meal, an activity must leave room for the shortest food visit, and when nothing else fits before 12:00 the clock waits for the window. This changes balanced and busy plans near their limits too, so it needs a decision. Recommendation: accept if evaluation shows relaxed rule-based days without lunch.

## Open issues

- Evaluation runs with relaxed cases (`eval/datasets/trips/v1`) now request a lunch slot again, so their results differ from RUN-075 records.
