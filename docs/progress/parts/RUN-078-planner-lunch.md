# RUN-078 · planner-lunch part

- Part: L1, lunch room in rule-based full days (0 points; follow-up of IMP-606 and PD-RUN-077-M1, decision IMD-196)
- Run id: RUN-078
- Owner: Manya (Manya Rana)
- Status: PR_OPEN once the lead opens the pull request; committed on `part/planner-lunch`, not pushed
- Base commit: b715d26
- Traces to: IMD-196, IMD-189, IMD-181; US-060; FR-083; TC-243, TC-372

## What changed

In `fallback_planner.plan_rule_based`, while a day with a lunch slot has had no meal and the clock is not past the lunch window, a visit that is not a must-visit is taken only if it leaves room in `max_active_minutes_per_day` for the shortest food visit still on the shortlist. When that reservation leaves nothing to add (or the lunch window is reached and no food place fits), the slot is given up: the day carries on filling as before and its theme ends with " · No food place found nearby" (the same note text). The clock never waits for the window, because step 9 (`schedule.recalculate`) packs items without gaps and would move a waited-for meal out of the window.

Unchanged: must-visit places (and food places) are exempt from the reservation; with no food place left the reservation is 0; uniqueness within the plan (IMD-181) is untouched (`remaining` is still shared across days); with the `meal_slots` switch off there is no slot, no reservation and no note. All 15 SAMPLE trips of `eval/datasets/trips/v1` (relaxed, balanced and busy) give byte-identical plans before and after the change (one-off comparison of `plan_rule_based(...).model_dump_json()` per case).

## Changed files

- `apps/api/app/generation/fallback_planner.py`: lunch reservation and the give-up path; the note is also written when the slot was given up before 14:00.
- `apps/api/tests/unit/generation/test_meal_slots.py`: four IMD-196 tests (relaxed long visits get lunch; relaxed day with no room keeps its visits and gets the note, with and without a food place; balanced and busy keep the same visits plus the meal; switch off reserves nothing).
- `docs/spec/DECISION_REGISTER.md`: not changed in this part; the IMD-196 row comes from the batch decision record (RUN-078-decision-record).
- `docs/progress/parts/RUN-078-planner-lunch.md`: this record.

## Commands

Run from `apps/api` with the shared venv and `PYTHONPATH=.` (`app` resolved to the worktree).

- `pytest tests/unit/generation/test_meal_slots.py -q` → `22 passed in 0.06s`
- same file `-k imd_196` against the old planner → `3 failed, 5 passed, 14 deselected in 0.08s` (the three relaxed cases fail before the fix)
- `pytest tests/unit -q` → `1199 passed, 1 warning in 19.07s`
- `pytest tests/contract -q` → `91 passed, 2 skipped, 1 warning in 19.42s` (skips: live Gemini smoke without a key)
- `ruff check` on the two changed Python files → `All checks passed!`; `ruff format --check` → `2 files already formatted`
- `mypy app` → `Success: no issues found in 123 source files`
- `lint-imports --config .importlinter` → `Contracts: 6 kept, 0 broken.`
- `scripts/build_sample_itineraries.py --check` → exit 0

Not run: `make test-api` (needs PostgreSQL; `tests/api/test_generations.py` has the rule-based meal and no-food cases, TC-243/TC-372, and should be run in CI); `make e2e` (no Docker); web checks (web untouched).

## Acceptance criteria

- Relaxed full day of long visits gets lunch or the note: **verified** by `test_meal_imd_196_relaxed_long_visits_keep_room_for_lunch` and `test_meal_imd_196_relaxed_day_with_no_room_for_lunch_says_so[True|False]`.
- Balanced and busy unchanged when lunch already fits: **verified** by `test_meal_imd_196_balanced_and_busy_days_unchanged_when_lunch_fits[balanced|busy]`, the existing `test_meal_tc_243_*` tests and the identical plans of the 15 SAMPLE trips.
- Switch off → no slot and no reservation (TC-372): **verified** by `test_meal_imd_196_switch_off_reserves_nothing[relaxed|balanced|busy]` and `test_meal_tc_372_switch_off_inserts_no_meal_and_no_note`.
- Must-visit behaviour and uniqueness kept: **verified** by the existing `test_fallback_planner.py` cases (must-visit left out and reported, unique places, pace limits on the SAMPLE trips), all passing.

## Blockers

none

## Proposed decisions

none

## Open issues

- The reservation uses the food visit's duration only, not the walk to it; when the walk tips the meal over the limit, the slot is given up with the note rather than filled.
