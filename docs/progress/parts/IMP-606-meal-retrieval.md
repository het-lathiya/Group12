# IMP-606 · meal-retrieval part

- Part: Food places data and meal-slot retrieval; meal-slot display on item cards (3 points)
- Run id: RUN-075 (Sprint 6 batch A)
- Owner: Malhar (Malhar Mer)
- Status: PR_OPEN once the lead opens the pull request; committed on `part/g`, not pushed
- Base commit: a6307c3
- Traces to: US-060; FR-083; TC-243, TC-244, TC-372
- Card steps built: 1 (MEAL_WINDOWS and the lunch rule), 2 (as already built, see below), 5 (meal icon, no rating)

## Changed files

- `apps/api/app/generation/presets.py`: `MEAL_WINDOWS` (breakfast 07:30-09:30, lunch 12:00-14:00, dinner 18:30-20:30; Provisional, IMD-29), `LUNCH_MIN_ACTIVE_MIN = 360` and `meal_slots(pace, *, enabled)`: `["lunch"]` when the pace allows more than six active hours (balanced, busy), `[]` for relaxed (300 minutes) or when the `meal_slots` switch is off. The request builder part (IMP-606 meal-builder) calls it.
- `apps/web/components/itinerary/ItineraryItemCard.tsx`: a meal item's slot pill shows a `Utensils` icon (aria-hidden; the visible text "Meal" stays the accessible label). The card renders no rating field.
- `apps/api/tests/unit/generation/test_meal_slots.py` (created): the constants, the lunch rule per pace, the switch-off case.
- `apps/web/tests/unit/itinerary/ItineraryItemCard.test.tsx`: TC-244 (a meal item shows the icon; a rating smuggled onto the place is not rendered) and no icon on an activity.

Not changed, and why:

- `data/fixtures/sampleton/places.csv`: the SAMPLE fixture already holds six fictional food places (sample-013 to sample-018), four of them open over lunch every day, enough for the lunch slot of the longest SAMPLE trip. Adding rows would change the counts that seed, places, retrieval and RAG-index tests assert for the fixture, for no gain. No real-destination data was touched.
- `apps/api/app/generation/retrieval.py`: `ranked_shortlist` already keeps `num_days × meal_slots_per_day` food places in the shortlist through `ranking.rank_shortlist` (IMP-304), preference-filtered by the hard filters; the meal-builder part passes the count from `presets.meal_slots`.
- `apps/api/app/core/config.py`: `FEATURES_DISABLED` already exists; the switch needs no new setting.

## Commands

Run from the worktree root with `PYTHONPATH=$PWD/apps/api` (the shared virtual environment installs `app` from the main checkout). The database was not needed for this part.

- `make test-unit ARGS='-k meal -q'` → `24 passed, 1131 deselected, 1 warning in 1.32s`
- `make test-web ARGS='tests/unit/itinerary/ItineraryItemCard.test.tsx'` → `Tests  9 passed (9)` (3.4 s wall time)
- `make lint` → `All checks passed!`, `229 files already formatted`, ESLint `✖ 1 problem (0 errors, 1 warning)` (an existing warning in another file), `All matched files use Prettier code style!`
- `make typecheck` → mypy `Success: no issues found in 122 source files`; `tsc --noEmit` exit 0
- `make imports` → `Contracts: 6 kept, 0 broken.`

Not run: `make e2e` (no Docker on this machine), a screenshot of a day with a lunch slot (no dev server in this run).

## Acceptance criteria

- FR-083 AC2, no rating on a food place (TC-244): **verified** by "marks a meal item with a meal icon and shows no rating".
- FR-083 AC1 and the SAMPLE lunch criterion: built and verified in the meal-builder part (request builder, fallback planner, API test).
- TC-372 (switch off): the rule is verified here by `test_meal_tc_372_switch_off_plans_no_meal_slots`; the generation path is verified in the meal-builder part.

## Blockers

none

## Proposed decisions

none

## Open issues

- Card step 2 asks for food places "nearest to each day group"; the shortlist keeps the best-ranked food places (ranking includes distance to the destination centre), not the nearest per day group. Day grouping then places them. Left as built by IMP-304.
- Screenshot evidence of a lunch slot is missing.
