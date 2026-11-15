# RUN-077 · mock-meals part

- Part: MOCK "ok" scenario plans meal slots (0 points; follow-up of IMP-606, decision IMD-189, PD-RUN-075-G1 option a)
- Run id: RUN-077
- Owner: Nidhi (Nidhi Chauhan)
- Status: PR_OPEN once the lead opens the pull request; committed on `part/m` on top of the relaxed-lunch part, not pushed
- Base commit: 0e15ae7
- Traces to: IMD-189, IMD-181, IMD-180; US-060; FR-083; TC-243, TC-372; §8.4 (MOCK ok behaviour)

## Changed files

- `apps/api/app/ai/providers/mock.py`: with `"lunch"` in `limits.meal_slots`, the `ok` plan takes a food place only as the day's meal: when the clock is in the lunch window (12:00 to 14:00) the first remaining food place in shortlist order that fits (day end, active minutes, opening hours) and starts by 14:00 becomes a `meal` item; a must-visit food place may come at any time and is then the meal; at most one meal per day, and a place is planned at most once in the plan (IMD-181). A day that runs through the window without a meal ends its theme with " · No food place found nearby" (within 80 characters), the convention of the rule-based planner. Notes and themes still start with "SAMPLE" and never contain the "AI-written" label (IMD-180). The fit check moves into `_fit`, item building into `_item`. With the `meal_slots` switch off (empty `limits.meal_slots`) the plan is unchanged from before: shortlist order, food places marked `meal`, which the pipeline turns into activities. The lunch window and the note are repeated as constants because the mock imports no planning module (an existing unit test forbids it); a new test keeps them equal to the fallback planner's.
- `apps/api/tests/unit/ai/test_mock_provider.py`: three order/timing tests now set `meal_slots` to `[]` to keep pinning the shortlist-order rule; new tests: lunch from a food place listed first in the shortlist (planned in the window, not at 09:00), one meal per day with no reused place, no food place → no meal and the day note (no "AI-written" text), and the constants match the fallback planner.

No fixture, sample itinerary or API test needed a change (`build_sample_itineraries.py --check` exit 0; the SAMPLE trip test `test_the_ok_answer_for_the_sample_trip_needs_no_repair_and_fits_the_hours` passes for all seven start weekdays).

## Commands

Run from `apps/api` (unit, contract, lint) or the worktree root (`make`). API and authorization tests used a throwaway local PostgreSQL 16 with pgvector (`travel_test_m` on 127.0.0.1:55432), not a shared database.

- `.venv/bin/python -m pytest tests/unit/ai/test_mock_provider.py -q` → `47 passed in 0.39s` (after the last test edit; first run of the new code: `2 failed, 41 passed`, the two order tests fixed as above)
- `.venv/bin/python -m pytest tests/unit tests/contract -q` → `1282 passed, 2 skipped, 1 warning in 39.77s` (skips: live Gemini tests without a key)
- `make test-api` → `564 passed, 1 warning in 185.95s (0:03:05)`
- `make test-authz ARGS='-q'` → `71 passed in 36.54s`
- `.venv/bin/ruff check app tests` → `All checks passed!`; `.venv/bin/ruff format --check app tests` → `223 files already formatted`
- `.venv/bin/mypy app` → `Success: no issues found in 123 source files`
- `.venv/bin/lint-imports --config .importlinter` → `Contracts: 6 kept, 0 broken.`
- `scripts/build_sample_itineraries.py --check` → exit 0

Not run: `make e2e` (no Docker on this machine); `make eval` (no new evaluation run recorded).

## Acceptance criteria

- IMP-606 AC1 on MOCK model plans ("every full day has a lunch item from a food place or an empty-slot note"): **verified** at unit level by `test_imd_189_ok_plans_the_lunch_slot_from_a_food_place` and `test_imd_189_without_a_food_place_the_lunch_slot_stays_empty_with_the_day_note`; the API suite with MOCK ok passes.
- Place uniqueness within the plan (IMD-181): **verified** by `test_imd_189_ok_plans_one_meal_per_day_and_reuses_no_place` and the uniqueness assertion in the lunch test.
- No "AI-written" label written by the mock (IMD-180): **verified** by the no-food-place test.
- Switch off → plan as before, no meal kept (TC-372): **verified** by the order tests with `meal_slots=[]` and the API test `test_meal_tc_372_switched_off_generation_succeeds_without_meal_items[ai]`.

## Blockers

none

## Proposed decisions

- **PD-RUN-077-M2: amend the §8.4 ok-scenario line.** §8.4 says the ok plan takes candidates in shortlist order; with a lunch slot the mock now holds food places for the lunch window (IMD-189 decided the behaviour, the specification line still needs the wording). Proposed text: "with a lunch slot, a food place is planned only as the day's meal inside the lunch window, else the day says No food place found nearby".

## Open issues

- On a model plan the day note sits in the model-written theme, so the theme is labelled AI-written as a whole (PD-RUN-075-G1); here that is the MOCK's SAMPLE theme, as a real model would write it.
- Committed evaluation results (`eval/results/*-mock/run.json`) were produced by the earlier mock and are not regenerated; a new MOCK evaluation run will differ.
